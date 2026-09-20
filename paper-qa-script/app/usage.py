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
- 线程安全（锁）；回调节点若被 `app.engine.prune_litellm_callbacks()` 裁掉，
  `ensure_installed()` 会重新挂上（prune 后也会调用它）。
"""
from __future__ import annotations

import asyncio
import copy
import json
import threading
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


def cost_cny(by_model: dict[str, dict]) -> dict:
    """按模型明细算成本（USD→CNY）。

    返回 {cost_cny, partial_cost_cny, unpriced_models, fx_usd_cny}：
    - 全部模型都有价 → `cost_cny` = 总额；
    - 有模型缺价 → `cost_cny=None`（**不臆测**）、`partial_cost_cny` 给已计价部分、`unpriced_models` 点名。
    """
    partial = 0.0
    unpriced: list[str] = []
    for model, t in sorted((by_model or {}).items()):
        price = price_for(model)
        if not price:
            unpriced.append(model)
            continue
        pin = float(price.get("input_cost_per_token") or 0.0)
        pout = float(price.get("output_cost_per_token") or 0.0)
        partial += float(t.get("prompt_tokens") or 0) * pin
        partial += float(t.get("completion_tokens") or 0) * pout
    fx = fx_usd_cny()
    partial_cny = round(partial * fx, 6)
    return {
        "cost_cny": None if unpriced else partial_cny,
        "partial_cost_cny": partial_cny,
        "unpriced_models": unpriced,
        "fx_usd_cny": fx,
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


def _record(model: str, prompt: int, completion: int, total: int, reported: str = "") -> None:
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


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def record_response(response: Any, model_hint: str = "") -> None:
    """从 litellm 响应里防御式提取 usage（对象或 dict 皆可；无 usage 就记 0 次调用也不抛）。"""
    if response is None:
        return
    usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
    if isinstance(response, dict):
        reported = str(response.get("model") or "")
    else:
        reported = str(getattr(response, "model", "") or "")
    key, raw = _resolve_key(reported, model_hint)
    if usage is None:
        _record(key, 0, 0, 0, raw)
        return
    if isinstance(usage, dict):
        prompt = _as_int(usage.get("prompt_tokens") or usage.get("input_tokens"))
        completion = _as_int(usage.get("completion_tokens") or usage.get("output_tokens"))
        total = _as_int(usage.get("total_tokens"))
    else:
        prompt = _as_int(getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None))
        completion = _as_int(getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None))
        total = _as_int(getattr(usage, "total_tokens", None))
    _record(key, prompt, completion, total, raw)


# ---------------------------------------------------------------- litellm 回调
def hook_success(kwargs: Any = None, completion_response: Any = None, start_time: Any = None, end_time: Any = None) -> None:
    """litellm 同步回调（签名遵循 litellm 自定义回调约定）。"""
    hint = ""
    try:
        hint = str((kwargs or {}).get("model") or "")
    except Exception:
        hint = ""
    try:
        record_response(completion_response, hint)
    except Exception:
        pass


async def hook_success_async(kwargs: Any = None, completion_response: Any = None, start_time: Any = None, end_time: Any = None) -> None:
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
    snap["cost"] = cost_cny(snap.get("by_model") or {})
    return snap


def delta(before: dict) -> dict:
    """`before`（早先的 snapshot）→ 当前的增量，字段与 snapshot 对齐。"""
    now = snapshot()
    by_model: dict[str, dict] = {}
    for model, t in (now.get("by_model") or {}).items():
        b = ((before or {}).get("by_model") or {}).get(model) or {}
        item = {k: int(t.get(k) or 0) - int(b.get(k) or 0) for k in ("calls", "prompt_tokens", "completion_tokens", "total_tokens")}
        if any(item.values()):
            by_model[model] = item
    out = {
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
    out["cost"] = cost_cny(by_model)
    return out


def reset() -> None:
    """清零（测试与独立进程复用）。"""
    with _LOCK:
        _TOTALS.update({"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "by_model": {}})
