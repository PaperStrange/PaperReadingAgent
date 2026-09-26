"""Token 用量采集与成本换算（Sprint-16 Retro 行动项 ③，2026-09-20 落地）。

动机：联网 verify/e2e 与夜间套件此前只有 `VERIFY_META.est_cost_cny` 的**估算上界**，
TG-5 的三态预算闸门因此长期停在 `unknown`（需人工 `--record-cost` 回填，否则夜间套件被拒放行）。
本模块从 litellm 回调采集**真实 token 用量**，按本地价表（`agents/runtime/prices.json`，M9 抓取 +
`fx_usd_cny`）换算 CNY，形成链路：

    litellm 回调 → 进程累计 → step 输出 output["usage"] / GET /api/usage
                 → verify 脚本打印 MEASURED_* → run_suite 汇总 → scheduled-tasks 自动回填

口径（重要）：
- **token 是实测值**（litellm `usage`），**成本是换算值**；
- 价表缺该模型 → `cost_cny=None` 且列入 `unpriced_models`，**绝不臆测单价**；
- **计费键优先取"能定价的名字"**：litellm 响应里的模型名常是上游别名（请求
  `openai/deepseek-v4-flash` → 响应 `deepseek-flash`），故按"请求名 → 响应名"取第一个有价者，
  原始回报名留在 `by_model[...].reported_as` 供追溯；
- **按时段选档**（TG-20 行 20）：按**该次调用自己**的起止时刻选档（litellm 回调的第 3/4
  个位置参数就是它），跨档按墙钟时间加权；时间戳拿不到 ⇒ 按高峰计 ＋ 标 `tier_assumed`；
  档位结论落在 `cost.by_tier` / `cost.tier_by_model`（可审计）。
  真源 = `docs/iteration/phases/agents-infra/2026-09-26-price-tier-spec.MD` §3；
- 线程安全（锁）；回调节点若被 `app.engine.prune_litellm_callbacks()` 裁掉，
  `ensure_installed()` 会重新挂上（prune 后也会调用它）。
"""
from __future__ import annotations

import asyncio
import copy
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_TOTALS: dict[str, Any] = {
    "calls": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "by_model": {},
}
_PRICES_CACHE: tuple[float, dict] | None = None


# ---------------------------------------------------------------- 价表（只读）
def prices_path() -> Path:
    """仓库根/agents/runtime/prices.json（app/usage.py → parents[2] = 仓库根）。"""
    return Path(__file__).resolve().parents[2] / "agents" / "runtime" / "prices.json"


def load_prices() -> dict:
    """读价表（按 mtime 缓存；读失败 → 空表，成本一律算 None）。"""
    global _PRICES_CACHE
    p = prices_path()
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return {}
    if _PRICES_CACHE and _PRICES_CACHE[0] == mtime:
        return _PRICES_CACHE[1]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    _PRICES_CACHE = (mtime, data)
    return data


def _model_candidates(model: str) -> list[str]:
    """模型名归一化候选：`openai/deepseek-v4-flash` → 也试 `deepseek-v4-flash`；去 `openrouter/` 前缀。"""
    m = (model or "").strip()
    out = [m]
    for prefix in ("openai/", "azure/", "openrouter/", "dashscope/", "deepseek/"):
        if m.startswith(prefix):
            out.append(m[len(prefix):])
    if "/" in m:
        out.append(m.split("/", 1)[1])
    seen: list[str] = []
    for x in out:
        if x and x not in seen:
            seen.append(x)
    return seen


def price_for(model: str) -> dict | None:
    """查单价：先 `scraped.*.models.<name>`，再 `auto.<name>`；找不到 → None（不猜）。"""
    prices = load_prices()
    cands = _model_candidates(model)
    scraped = (prices.get("scraped") or {})
    for prov in scraped.values():
        models = (prov or {}).get("models") or {}
        for name in cands:
            if name in models and models[name]:
                return models[name]
    auto = prices.get("auto") or {}
    for name in cands:
        if name in auto and auto[name]:
            return auto[name]
    return None


def fx_usd_cny() -> float:
    try:
        return float(((load_prices().get("meta") or {}).get("fx_usd_cny")) or 7.2)
    except (TypeError, ValueError):
        return 7.2


# ----------------------------------------- 价表多档：按调用时刻选档（TG-20 行 20）
# 真源 = docs/iteration/phases/agents-infra/2026-09-26-price-tier-spec.MD（§3）。
# 参考实现 = scripts/agent-ops.py 的 peak_windows_from_prices / is_peak_at /
# peak_frac_for / _tier_prices（TG-20 行 16 落地）。本模块**镜像同一口径**，不
# import 它：那是 CLI 脚本（文件名带连字符、模块级即拉 argparse 与账本路径常量），
# app/ 不能依赖它。两边的选档窗口取自**同一份数据**
# （价表 `scraped.<provider>._peak_windows`），都不在代码里写死。
_TIER_PEAK = "peak"
_TIER_OFF = "off_peak"
_TIER_MIXED = "mixed"
_TIER_FLAT = "flat"
_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
# 档位桶的键：前三个是**实测**次数/token，后两个是按高峰权重分摊的 token（§3.3）。
_BUCKET_KEYS = ("calls", "prompt_tokens", "completion_tokens",
                "peak_prompt_tokens", "peak_completion_tokens")
_TIER_TOTALS: dict[str, Any] = {"tier_by_model": {}, "tier_assumed_calls": 0}


def peak_windows() -> tuple[list, str] | None:
    """价表里的 `(_peak_windows, 时区名)`；无该元数据 ⇒ None（= 不按档计价）。

    与 `agent-ops.peak_windows_from_prices` 同序：第一个"窗口非空"的 `scraped.*` 命中
    即返回，时区缺省 `Asia/Shanghai`。
    """
    for prov in (load_prices().get("scraped") or {}).values():
        if not isinstance(prov, dict):
            continue
        windows = prov.get("_peak_windows")
        if isinstance(windows, list) and windows:
            return windows, str(prov.get("_tier_timezone") or "Asia/Shanghai")
    return None


def _hm_minutes(text: object) -> int | None:
    """`"09:00"` → 540；非法 → None（fail-closed，绝不当成 0）。"""
    if not isinstance(text, str) or ":" not in text:
        return None
    try:
        hh, mm = (int(x) for x in text.split(":", 1))
    except ValueError:
        return None
    return hh * 60 + mm if 0 <= hh <= 24 and 0 <= mm < 60 else None


def _window_index(windows: list) -> dict[str, list[tuple[int, int]]] | None:
    """窗口清单 → `{星期键: [(起, 止) 分钟]}`；形状非法 → None（读不出来 ⇒ 按高峰）。"""
    index: dict[str, list[tuple[int, int]]] = {}
    for win in windows:
        if not isinstance(win, dict):
            return None
        start, end = _hm_minutes(win.get("start")), _hm_minutes(win.get("end"))
        days = win.get("days")
        if start is None or end is None or not isinstance(days, list) or not days:
            return None
        if not set(days) <= set(_WEEKDAYS):
            return None
        for day in days:
            index.setdefault(day, []).append((start, end))
    return index


def is_peak_at(stamp: datetime, windows: list, tzname: str) -> bool:
    """该时刻是否落在高峰窗口（**左闭右开**：09:00 整算高峰、12:00 整算空闲）。

    窗口读不出来 ⇒ True（fail-closed：宁可高估，不许静默变便宜）。
    """
    from zoneinfo import ZoneInfo

    local = stamp.astimezone(ZoneInfo(tzname))
    index = _window_index(windows)
    if index is None:
        return True
    minutes = local.hour * 60 + local.minute
    windows_of_day = index.get(_WEEKDAYS[local.weekday()], [])
    return any(lo <= minutes < hi for lo, hi in windows_of_day)


def _peak_seconds(start: datetime, end: datetime, windows: list, tzname: str) -> float:
    """与高峰窗口重叠的墙钟秒数（按分钟切步，与 `agent-ops` 同精度）。"""
    hit = 0.0
    cursor = start
    while cursor < end:
        nxt = min(cursor + timedelta(minutes=1), end)
        if is_peak_at(cursor, windows, tzname):
            hit += (nxt - cursor).total_seconds()
        cursor = nxt
    return hit


def _as_instant(value: object) -> datetime | None:
    """调用时刻 → 带时区的 datetime；拿不到 ⇒ None（按 §3.2 的"时间戳缺失"处理）。

    **为什么朴素值按本机时区解释**：litellm 回调传的是 `datetime.now()` 的朴素本地时间
    （实测 `datetime(2026, 9, 27, 2, 1, 50, 58794)`：本机 UTC+9 的 02:01 = UTC 17:01）。
    若照 `agent-ops._parse_ts` 把朴素值当 UTC，本机 UTC+9 的 01:00 调用会被当成
    09:00 CST 判成高峰 —— 档位整体错一个小时。故这里用 `astimezone()`（朴素 = 本机墙钟）
    贴回时区。
    """
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.astimezone()
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.astimezone()
    return None


def peak_frac(start: object, end: object, windows: list, tzname: str) -> float | None:
    """调用窗口 `[start, end]` 的高峰时间占比；`None` = 端点缺失/不可解析/时钟退化。

    三种情形必须分开（同 `agent-ops.peak_frac_for`，口径不分叉）：
      * 任一端拿不到 ⇒ `None`（调用方按高峰计 ＋ 打 `tier_assumed`，§3.2）；
      * `end == start`（同刻/零长度调用）⇒ **按起点那一刻判档**（0.0 或 1.0）——
        这是"这次调用落在哪一档"，**不是**"时间戳缺失"；
      * `end < start`（时钟退化）⇒ `None`（负时长排不出区间）。
    """
    t0, t1 = _as_instant(start), _as_instant(end)
    if t0 is None or t1 is None:
        return None
    if t1 == t0:
        return 1.0 if is_peak_at(t0, windows, tzname) else 0.0
    if t1 < t0:
        return None
    total = (t1 - t0).total_seconds()
    return round(_peak_seconds(t0, t1, windows, tzname) / total, 6)


def _tiered(prices: dict, tier: str) -> dict | None:
    """`_tiers.<tier>` 四键齐全才认（缺键 = 数据不全 ⇒ 退回扁平键，不静默补 0）。"""
    tiers = prices.get("_tiers")
    block = tiers.get(tier) if isinstance(tiers, dict) else None
    if not isinstance(block, dict):
        return None
    keys = ("input_cost_per_token", "output_cost_per_token",
            "cache_read_input_token_cost", "cache_creation_input_token_cost")
    return block if all(k in block for k in keys) else None


def _blend(a: dict, b: dict, frac_a: float) -> dict:
    """逐键线性混合（`frac_a` = 取 a 档的占比）——§3.3 的 `usage × [frac×价]`。"""
    return {k: (a.get(k) or 0) * frac_a + (b.get(k) or 0) * (1 - frac_a) for k in a}


def tier_prices(prices: dict, frac: float | None) -> tuple[dict, str, float | None]:
    """`(计费四键价, 档位标签, peak_frac)`——与 `agent-ops._tier_prices` 逐分支同义。

    无 `_tiers` ⇒ 扁平键原样 ＋ `flat`（该模型就是单档，**不**假装分过档）；
    `frac` 为 None ⇒ 高峰档 ＋ `peak`（调用方据此打 `tier_assumed`，§3.2 的保守方向）；
    否则 §3.3：`peak_frac` ∈ (0,1) 时逐键时间加权并标 `mixed`。
    """
    peak, off = _tiered(prices, _TIER_PEAK), _tiered(prices, _TIER_OFF)
    if peak is None or off is None:
        return prices, _TIER_FLAT, None
    if frac is None:
        return peak, _TIER_PEAK, None
    if frac >= 1.0:
        return peak, _TIER_PEAK, frac
    if frac <= 0.0:
        return off, _TIER_OFF, frac
    return _blend(peak, off, frac), _TIER_MIXED, frac


def _tier_plan(model: str, start: object, end: object) -> tuple[str, float, bool]:
    """该次调用的 `(档位标签, 高峰权重, 是否 tier_assumed)`。

    高峰权重 = 这次调用的 token 里**按高峰价计**的比例（§3.3）；`flat` 用扁平键
    （= 高峰镜像）故权重 1.0 与之一致。`tier_assumed` 只在"有档位数据但时间戳拿不到"
    时置位（与 `agent-ops._estimate_cost` 同条件：单档模型不假装分过档）。
    """
    price = price_for(model)
    windows = peak_windows()
    if not price or not windows:
        return _TIER_FLAT, 1.0, False
    frac = peak_frac(start, end, windows[0], windows[1])
    _, label, kept = tier_prices(price, frac)
    return label, (1.0 if kept is None else kept), label != _TIER_FLAT and kept is None


def _empty_bucket() -> dict:
    """空档位桶：实测次数/token ＋ 按高峰权重分摊的 token（金额在 `cost_cny` 现算）。"""
    return {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
            "peak_prompt_tokens": 0.0, "peak_completion_tokens": 0.0}


def _record_tier(model: str, prompt: int, completion: int,
                 label: str, weight: float, assumed: bool) -> None:
    """把一次调用记进 `(模型, 档位)` 桶（**调用方须持有 `_LOCK`**）。"""
    slot = _TIER_TOTALS["tier_by_model"].setdefault(model or "unknown", {})
    bucket = slot.setdefault(label, _empty_bucket())
    pin, pout = max(0, prompt), max(0, completion)
    bucket["calls"] += 1
    bucket["prompt_tokens"] += pin
    bucket["completion_tokens"] += pout
    bucket["peak_prompt_tokens"] = round(bucket["peak_prompt_tokens"] + pin * weight, 6)
    bucket["peak_completion_tokens"] = round(
        bucket["peak_completion_tokens"] + pout * weight, 6)
    if assumed:
        _TIER_TOTALS["tier_assumed_calls"] += 1


def _bucket_usd(price: dict, bucket: dict) -> float:
    """一个桶的美金金额 = `高峰价 × 高峰加权 token ＋ 空闲价 × 其余`（§3.3）。

    纯高峰桶（权重 1）退化为高峰价、纯空闲桶（权重 0）退化为空闲价，一条式子覆盖三档。
    价表无完整 `_tiers`（或没有选档窗口）⇒ 扁平键（= 高峰镜像）。**金额在这里由价表现值
    算出**：桶里只存测量量，改价表不会悄悄改历史读数。
    """
    p = float(bucket.get("prompt_tokens") or 0)
    c = float(bucket.get("completion_tokens") or 0)
    peak, off = _tiered(price, _TIER_PEAK), _tiered(price, _TIER_OFF)
    if peak is None or off is None or peak_windows() is None:
        pin = float(price.get("input_cost_per_token") or 0.0)
        pout = float(price.get("output_cost_per_token") or 0.0)
        return p * pin + c * pout
    # 夹一下：浮点累加可能让加权量比总量多半位，别让它变成负的空闲部分
    fp = min(float(bucket.get("peak_prompt_tokens") or 0), p)
    fc = min(float(bucket.get("peak_completion_tokens") or 0), c)
    return (fp * float(peak.get("input_cost_per_token") or 0.0)
            + (p - fp) * float(off.get("input_cost_per_token") or 0.0)
            + fc * float(peak.get("output_cost_per_token") or 0.0)
            + (c - fc) * float(off.get("output_cost_per_token") or 0.0))


def cost_cny(by_model: dict[str, dict], tiered: dict | None = None) -> dict:
    """按模型明细算成本（USD→CNY）。

    `tiered` = `{"tier_by_model": {模型: {档位: 桶}}, "tier_assumed_calls": n}`
    （`snapshot()`/`delta()` 传它）⇒ **每次调用按它自己时刻选的档**计价；不传（或某模型
    没有桶）⇒ 退回扁平键，供"只有 token、没有时刻"的直接调用。

    原口径不变：
    - 全部模型都有价 → `cost_cny` = 总额；
    - 有模型缺价 → `cost_cny=None`（**不臆测**）、`partial_cost_cny` 给已计价部分、
      `unpriced_models` 点名；
    - **空账（一条调用都没记到）→ `cost_cny=None` + `no_data=True`**（复核 round-4
      major：空账绝不能算成 `0.0`，否则"回调还没落地"会被下游当成"已测且花费为 0"，
      把三态闸门从 unknown 误推到 measured 并低估金额）。

    行 20 新增三键（可审计"用了哪一档"）：
    - `by_tier`：全局档位聚合（只含可计价部分，`Σ usd × fx == partial_cost_cny`）；
    - `tier_by_model`：逐模型 × 档位明细（缺价模型也在，`usd=None`）；
    - `tier_assumed_calls`：时间戳拿不到 ⇒ 按高峰计的调用数（§3.2 的可见标记）。
    """
    buckets_by_model = (tiered or {}).get("tier_by_model") or {}
    names = sorted(set(by_model or {}) | set(buckets_by_model))
    partial = 0.0
    unpriced: list[str] = []
    priced = 0
    by_tier: dict[str, dict] = {}
    tier_by_model: dict[str, dict] = {}
    for model in names:
        price = price_for(model)
        detail: dict[str, dict] = {}
        for label, bucket in sorted((buckets_by_model.get(model) or {}).items()):
            usd = None if not price else round(_bucket_usd(price, bucket), 12)
            detail[label] = {**bucket, "usd": usd}
            if usd is None:
                continue
            agg = by_tier.setdefault(label, {**_empty_bucket(), "usd": 0.0})
            for key in _BUCKET_KEYS:
                agg[key] += bucket.get(key) or 0
            agg["usd"] = round(agg["usd"] + usd, 12)
            partial += usd
        if detail:
            tier_by_model[model] = detail
        if not price:
            unpriced.append(model)
            continue
        priced += 1
        if not detail:
            # 没有档位桶（只给 token 的直接调用）：旧口径 = 扁平键
            t = (by_model or {}).get(model) or {}
            pin = float(price.get("input_cost_per_token") or 0.0)
            pout = float(price.get("output_cost_per_token") or 0.0)
            partial += float(t.get("prompt_tokens") or 0) * pin
            partial += float(t.get("completion_tokens") or 0) * pout
    fx = fx_usd_cny()
    partial_cny = round(partial * fx, 6)
    empty = not names
    return {
        "cost_cny": None if (unpriced or empty) else partial_cny,
        "partial_cost_cny": partial_cny,
        "unpriced_models": unpriced,
        "no_data": empty,
        "fx_usd_cny": fx,
        "priced_models": priced,
        "by_tier": by_tier,
        "tier_by_model": tier_by_model,
        "tier_assumed_calls": int((tiered or {}).get("tier_assumed_calls") or 0),
    }


# ---------------------------------------------------------------- 累计器
def _resolve_key(reported: str, requested: str = "") -> tuple[str, str]:
    """返回 (计费键, 原始回报名)。

    起因（2026-09-20 实测）：litellm 回报的**响应模型名常是上游别名**（例如请求
    `openai/deepseek-v4-flash`，响应里是 `deepseek-flash`），直接用响应名查价表会算不出成本。
    口径：**优先取"能定价的那个名字"**（先看请求名，再看响应名）；两者都无价 →
    用响应名并列入 `unpriced_models`（不猜别名、不臆测单价）。原始回报名保留在 `reported_as`。
    """
    reported = (reported or "").strip()
    requested = (requested or "").strip()
    for cand in (requested, reported):
        if cand and price_for(cand):
            return cand, reported
    return (reported or requested or "unknown"), reported


def _record(model: str, prompt: int, completion: int, total: int, reported: str = "",
            tier: tuple[str, float, bool] | None = None) -> None:
    label, weight, assumed = tier or (_TIER_FLAT, 1.0, False)
    with _LOCK:
        _TOTALS["calls"] += 1
        _TOTALS["prompt_tokens"] += max(0, prompt)
        _TOTALS["completion_tokens"] += max(0, completion)
        _TOTALS["total_tokens"] += max(0, total or (prompt + completion))
        slot = _TOTALS["by_model"].setdefault(model or "unknown", {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        slot["calls"] += 1
        slot["prompt_tokens"] += max(0, prompt)
        slot["completion_tokens"] += max(0, completion)
        slot["total_tokens"] += max(0, total or (prompt + completion))
        if reported and reported != model:
            names = slot.setdefault("reported_as", [])
            if reported not in names:
                names.append(reported)
        _record_tier(model, prompt, completion, label, weight, assumed)


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def record_response(response: Any, model_hint: str = "", start_time: Any = None,
                    end_time: Any = None) -> None:
    """从 litellm 响应里防御式提取 usage（对象/dict 皆可；无 usage 就不记账、不抛）。

    `start_time`/`end_time` = **该次调用自己**的起止时刻（litellm 把回调的第 3/4 个
    位置参数设为它们；实测是 `datetime.now()` 的朴素本地时间）。两者一起决定这次调用
    按哪一档计价（§3.1／§3.3）；拿不到就按高峰计 ＋ 打 `tier_assumed`（§3.2）。
    **不允许**用"读账那一刻"顶替：那是"给整段贴一个结束时刻的标签"，§3.3 明列的反面
    （会把夜间 token 按高峰算）。
    """
    if response is None:
        return
    usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
    if isinstance(response, dict):
        reported = str(response.get("model") or "")
    else:
        reported = str(getattr(response, "model", "") or "")
    key, raw = _resolve_key(reported, model_hint)
    if usage is None:
        # 2026-09-21 关闭三查·二查 major（教训 1.61）：**无 usage 的响应不得记 0 次调用**。
        # 旧实现 `_record(key, 0, 0, 0, raw)` 会让 `by_model` 非空 → `cost_cny` 算成 0.0 且 `no_data=False`
        # → 经 `e2e_common.report_usage` → `run_suite`（`calls>0` 即判 measured）→ `scheduled-tasks` 自动回填，
        # 即"回调未落地"被当成"已测且花费 0"——正是 3-LEARNED 1.54「未测量 ≠ 未超预算」禁止的口径。
        # 无 usage = 无数据：保持空账，由上游如实判 `cost_cny=None` + `no_data=True`。
        return
    if isinstance(usage, dict):
        prompt = _as_int(usage.get("prompt_tokens") or usage.get("input_tokens"))
        completion = _as_int(usage.get("completion_tokens") or usage.get("output_tokens"))
        total = _as_int(usage.get("total_tokens"))
    else:
        prompt = _as_int(getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None))
        completion = _as_int(getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None))
        total = _as_int(getattr(usage, "total_tokens", None))
    # 选档在锁外算（读价表要 stat 文件），只把结论带进临界区
    _record(key, prompt, completion, total, raw, _tier_plan(key, start_time, end_time))


# ---------------------------------------------------------------- litellm 回调
def hook_success(kwargs: Any = None, completion_response: Any = None,
                 start_time: Any = None, end_time: Any = None) -> None:
    """litellm 同步回调（签名遵循自定义回调约定：`(kwargs, response, start, end)`）。

    litellm 是**按位置**调进来的（`CustomLogger.log_event` →
    `callback_func(kwargs, response_obj, start_time, end_time)`），故这四个形参的名字
    与顺序都是契约：`start_time`/`end_time` 即该次调用自己的起止时刻 —— 选档输入。
    """
    hint = ""
    try:
        hint = str((kwargs or {}).get("model") or "")
    except Exception:
        hint = ""
    try:
        record_response(completion_response, hint, start_time, end_time)
    except Exception:
        pass


async def hook_success_async(kwargs: Any = None, completion_response: Any = None,
                             start_time: Any = None, end_time: Any = None) -> None:
    """litellm 异步回调（paperqa 走 `acompletion`，异步列表需要 async 回调）。"""
    await asyncio.sleep(0)  # 让出控制权，保持真异步语义
    hook_success(kwargs, completion_response, start_time, end_time)


def ensure_installed() -> bool:
    """把回调挂到 litellm（幂等）。返回是否成功挂载（litellm 不可用/异常 → False，不抛）。"""
    try:
        import litellm
    except Exception:
        return False
    ok = False
    for attr, fn in (("success_callback", hook_success), ("_async_success_callback", hook_success_async)):
        try:
            items = list(getattr(litellm, attr, None) or [])
            if not any(x is fn for x in items):
                items.append(fn)
                setattr(litellm, attr, items)
            ok = True
        except Exception:
            pass
    return ok


# ---------------------------------------------------------------- 快照/增量
def snapshot() -> dict:
    """累计快照（含成本换算）；`delta()`/`step` 输出都用它。"""
    with _LOCK:
        snap = copy.deepcopy(_TOTALS)
        tiered = copy.deepcopy(_TIER_TOTALS)
    snap["cost"] = cost_cny(snap.get("by_model") or {}, tiered)
    return snap


def _tier_delta(before: dict | None, now: dict) -> dict:
    """两份快照的档位桶增量（逐模型 × 逐档相减；零桶丢掉；金额由 `cost_cny` 现算）。

    只有**测量量**参与相减（`usd` 是 `cost_cny` 现算的，不进增量），故窗口内的金额仍由
    当前价表算出，不会把上一段窗口的钱带进来。
    """
    b_cost = ((before or {}).get("cost") or {})
    n_cost = (now.get("cost") or {})
    b_models = b_cost.get("tier_by_model") or {}
    out: dict[str, dict] = {}
    for model, labels in (n_cost.get("tier_by_model") or {}).items():
        for label, bucket in labels.items():
            base = (b_models.get(model) or {}).get(label) or {}
            item = {k: (bucket.get(k) or 0) - (base.get(k) or 0) for k in _BUCKET_KEYS}
            if any(item.values()):
                out.setdefault(model, {})[label] = item
    assumed = int(n_cost.get("tier_assumed_calls") or 0)
    assumed -= int(b_cost.get("tier_assumed_calls") or 0)
    return {"tier_by_model": out, "tier_assumed_calls": max(0, assumed)}


def delta(before: dict, scope: str = "process") -> dict:
    """`before`（早先的 snapshot）→ 当前的增量，字段与 snapshot 对齐。

    **范围口径（复核 round-4 minor）**：这是**进程级时间窗**增量，不做请求/会话隔离——
    8787 长驻且可能同时服务多会话时，逐步 `output["usage"]` 会把并发的他人调用算进来（偏高）。
    字段 `scope` 显式标注该口径；需要精确归属时应改 contextvars 按请求记账（候选卡）。
    """
    now = snapshot()
    by_model: dict[str, dict] = {}
    for model, t in (now.get("by_model") or {}).items():
        b = ((before or {}).get("by_model") or {}).get(model) or {}
        item = {k: int(t.get(k) or 0) - int(b.get(k) or 0) for k in ("calls", "prompt_tokens", "completion_tokens", "total_tokens")}
        if any(item.values()):
            by_model[model] = item
    out = {
        "scope": scope,
        "calls": int(now.get("calls") or 0) - int((before or {}).get("calls") or 0),
        "prompt_tokens": int(now.get("prompt_tokens") or 0) - int((before or {}).get("prompt_tokens") or 0),
        "completion_tokens": int(now.get("completion_tokens") or 0) - int((before or {}).get("completion_tokens") or 0),
        "total_tokens": int(now.get("total_tokens") or 0) - int((before or {}).get("total_tokens") or 0),
        "by_model": by_model,
        "cumulative": {
            "calls": now.get("calls"),
            "prompt_tokens": now.get("prompt_tokens"),
            "completion_tokens": now.get("completion_tokens"),
            "total_tokens": now.get("total_tokens"),
        },
    }
    out["cost"] = cost_cny(by_model, _tier_delta(before, now))
    return out


def settle(quiet_s: float = 0.4, max_s: float = 3.0, poll_s: float = 0.05) -> dict:
    """等待"在途"用量落地后再取快照（复核 round-4 major 的对策之一）。

    litellm 的成功回调是**异步派发**的（复核用离线 `mock_response` 实测：调用返回时计数仍为 0，
    约 1.5s 后才可见），因此"调用刚结束就读账"会漏掉尾部用量。本函数轮询到计数在 `quiet_s`
    内不再增长为止，或达到 `max_s` 上限（有界等待，绝不无限挂）。
    """
    deadline = time.monotonic() + max(0.0, max_s)
    last = snapshot()
    stable_since = time.monotonic()
    while True:
        time.sleep(max(0.01, poll_s))
        t = time.monotonic()
        cur = snapshot()
        if (cur["calls"], cur["total_tokens"]) != (last["calls"], last["total_tokens"]):
            last, stable_since = cur, t
            # 2026-09-21 关闭三查·二查 major（教训 1.61）：**增长分支也必须受 deadline 约束**。
            # 旧实现此处直接 `continue`，跳过了下面的 `t >= deadline` → 只要持续有流量就永不返回
            # （复核实测 >115s；本仓回归 ⑨ 在有界断言下实测 `alive=True elapsed=2.00s`）。
            # `/api/run_step` 每步收尾都会调用本函数，故这等于请求路径可被挂死。
            if t >= deadline:
                return last
            continue
        if t - stable_since >= quiet_s or t >= deadline:
            return last


def reset() -> None:
    """清零（测试与独立进程复用）。"""
    with _LOCK:
        _TOTALS.update({"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "by_model": {}})
        _TIER_TOTALS.update({"tier_by_model": {}, "tier_assumed_calls": 0})
