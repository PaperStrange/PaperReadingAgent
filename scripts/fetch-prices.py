"""M9（2026-08-31）：从 provider 官网**固定 URL** 抓取单价 → 更新 `agents/runtime/prices.json`。

设计：
- 纯 Python 标准库（与 agent-ops 同约束），三个固定来源：
  deepseek 官方文档定价页 / 阿里云百炼（dashscope）定价页 / OpenRouter 模型 JSON API。
- 价格写入 `prices.json` 的 **scraped** 段（新增）；查找优先级 manual（人工覆盖，非 null 优先）
  > scraped > auto（litellm 派生）——manual 永远不被抓取覆盖。
- `--check`：只抓取+解析+打印校验结果，不写盘；`--apply`：仅把**通过校验**的 provider 写入。
- 定时机制：本卡先落地手动/脚本入口；两周一次自动调度与 F-AC8（provider_config 定时更新）
  共用调度底座（见 docs/iteration/pre-research/2026-08-31-domain-governance.MD §6）。

运行：.venv\\Scripts\\python.exe scripts\\fetch-prices.py --check|--apply
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_BASE = Path(os.environ.get("AGENT_OPS_DIR", str(REPO_ROOT / "agents")))
PRICES_PATH = AGENTS_BASE / "runtime" / "prices.json"

# TG-8②：离线开关（唯一实现与政策数据见 verify/outbound_guard.py + agents/policy.json::offline_switch）。
# `scripts/**` 与 `verify/**` 共用同一份实现是**刻意的**：三个外呼脚本各写一份"离线判断"
# 就等于三份会漂移的政策（§6 政策数据化）。
sys.path.insert(0, str(REPO_ROOT))

from verify.outbound_guard import OfflineRefused, refuse_exit_code, refuse_if_offline  # noqa: E402


@contextlib.contextmanager
def _prices_lock():
    """价表互斥锁——与 scripts/agent-ops.py `_prices_lock` 同模式（保持同步）：
    prices-derive 与 fetch-prices --apply 对同一 prices.json 做 load→merge→save，须同锁。"""
    PRICES_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_path = PRICES_PATH.parent / ".prices.lock"
    with open(lock_path, "w") as fh:
        try:
            if os.name == "nt":
                msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        except OSError:
            raise SystemExit(f"锁获取超时：{lock_path} 被另一进程占用——稍后重试") from None
        try:
            yield
        finally:
            if os.name == "nt":
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

SOURCES = {
    "deepseek": "https://api-docs.deepseek.com/quick_start/pricing",
    "dashscope": "https://www.alibabacloud.com/help/en/model-studio/model-pricing",
    "openrouter": "https://openrouter.ai/api/v1/models",
}

# 抓取目标模型（scraped 键 = 账本里出现的模型名）
OPENROUTER_MODELS = [
    "deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-v4-flash-vision-exp", "qwen/qwen-omni-turbo", "qwen/qwen3-max",
    "openai/gpt-4o-mini", "openai/text-embedding-3-large", "openai/text-embedding-3-small",
]

# 校验边界：单价（USD/token）必须在 (0, 0.02] 区间，防解析错位
_PRICE_BOUND = 0.02
# 响应体上限（OpenRouter 全模型表可达数 MB；防异常大响应）
_MAX_BYTES = 20 * 1024 * 1024
# 允许域（后缀匹配）：重定向目标与源域都必须在白名单内（035：逐跳复检）
_ALLOW_DOMAINS = ("deepseek.com", "alibabacloud.com", "openrouter.ai")


def _host_allowed(url: str) -> bool:
    from urllib.parse import urlparse

    p = urlparse(url)
    if p.scheme != "https":
        return False
    host = (p.hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in _ALLOW_DOMAINS)


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """重定向逐跳复检：任一跳落到非 https 或白名单外域名 → 抛错（拒绝跟随）。

    2026-09-21 关闭三查·二查 major：原实现继承的是 `HTTPSHandler`，而 `redirect_request` 定义在
    `HTTPRedirectHandler` 上 → 本方法**从不被 urllib 调用**（死代码），`build_opener` 仍会挂默认
    重定向处理器，白名单可被一次 302 绕过。基类必须是 `HTTPRedirectHandler`（`refresh-providers.py:63`
    的同类实现一直是正确写法，可直接对照）。
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _host_allowed(newurl):
            raise ValueError(f"redirect to non-allowlisted target: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(url: str, timeout: int = 30) -> str:
    # TG-8②：**发请求之前**先过离线开关——命中即抛 `OfflineRefused`（点名来源与目标 URL）。
    # 放在白名单校验之前：拒绝原因必须是"开关开着"，而不是被后面的校验分支改写。
    refuse_if_offline(url)
    if not _host_allowed(url):
        raise ValueError(f"non-allowlisted source: {url}")
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    req = urllib.request.Request(url, headers={"User-Agent": "agent-ops/fetch-prices"})
    with opener.open(req, timeout=timeout) as resp:  # noqa: S310
        length = resp.headers.get("Content-Length")
        if length and int(length) > _MAX_BYTES:
            raise ValueError(f"response too large ({length} bytes > {_MAX_BYTES})")
        body = resp.read(_MAX_BYTES + 1)
        if len(body) > _MAX_BYTES:
            raise ValueError("response exceeded size cap")
        return body.decode("utf-8", errors="replace")


def _valid(p: float) -> bool:
    return 0 < p <= _PRICE_BOUND


def _entry(inp: float, out: float, cache_read: float, cache_create: float) -> dict:
    return {
        "input_cost_per_token": inp,
        "output_cost_per_token": out,
        "cache_read_input_token_cost": cache_read,
        "cache_creation_input_token_cost": cache_create,
    }


def _per1m(amounts: list[float], i: int) -> float:
    """USD/1M → USD/token，round(10) 去浮点噪声（035）。"""
    return round(amounts[i] / 1e6, 10)


def _ds_cell_text(inner: str) -> str:
    """单元格 → 规整文本（去标签、去 `&nbsp;`/不换行空格、压空白）。"""
    text = _DS_TAGS.sub(" ", inner).replace("&nbsp;", " ")
    return " ".join(text.replace("\u00a0", " ").split())


# -------- deepseek 表：形状常量（TG-20 行 15）
# 官方页现行表：2 模型 / 每模型 6 个金额。旧实现要求"`MODEL</td>` 后恰好 3 个模型名 +
# 至少 18 个 `$`"，于是恒返回 `{}`、抓取**静默失效**（spec §4 红字 B）。
# 这里不再对模型数设上限：模型数由表头行动态读出；金额同时吃 `$`（英文页）与
# `元`（中文页＝**唯一 CNY 来源**，该页一个 `$` 都没有）。
_DS_CELLS = re.compile(r"<t[dh]\b([^>]*)>(.*?)</t[dh]>", re.S)
_DS_ROWS = re.compile(r"<tr\b.*?</tr>", re.S)
_DS_TAGS = re.compile(r"<[^>]+>")
_DS_AMOUNT = re.compile(r"^\$?\d+(?:\.\d+)?(?:元)?$")
_DS_CNY = 7.2  # 缺省 fx（与 meta.fx_usd_cny 同源）；只用于把 CNY 原值换算成 USD/token
# 资源行标签 → `_entry()` 位置（页面顺序：缓存命中 / 缓存未命中 / 输出）。
# 匹配**只在这些标签格里做**（不是整行子串）：实测踩过的坑——"MAX OUTPUT / 输出长度"
# 属性行含 `OUTPUT`，整行子串匹配会把它当成输出价格块的开头。
_DS_RESOURCES = (
    (("CACHE HIT", "缓存命中"), "cache_read"),
    (("CACHE MISS", "缓存未命中"), "input"),
    (("1M OUTPUT", "百万tokens输出", "百万 tokens 输出"), "output"),
)
_DS_PEAK_LABELS = ("PEAK", "高峰时段")
_DS_OFF_LABELS = ("OFF-PEAK", "空闲时段")
# 表头里的脚注角标（页面写 `deepseek-flash (1)`；是脚注不是模型名的一部分）
_DS_FOOTNOTE = re.compile(r"\s*[(（]\s*\d+\s*[)）]\s*$")

# deepseek 的档位方案元数据（**代码是唯一真源**，每次抓取随 payload 一起写回）：
# 选档代码 `agent-ops.peak_windows_from_prices` 只读 `_peak_windows`/`_tier_timezone`，
# 故它们必须是**解析器产出**而不是人手补在 JSON 里——否则下一次 `--apply` 就会把
# 选档依据抹掉（见 `merge()`）。窗口文本逐字取自官网脚注（中英两页同构）。
_DS_TIMEZONE = "Asia/Shanghai"
_DS_URL_CNY = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing"
_DS_PEAK_WINDOWS = [
    {"days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "start": "09:00", "end": "12:00"},
    {"days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "start": "14:00", "end": "18:00"},
]
_DS_WINDOWS_VERBATIM = (
    "空闲时段价格为高峰时段价格的一半。北京时间周一至周五（不含中国法定节假日）"
    "9:00 - 12:00、14:00 - 18:00 为高峰时段；其余时段，"
    "包括周末及中国法定节假日全天均为空闲时段。"
)
_DS_WINDOWS_UTC_VERBATIM = (
    "Peak hours are 01:00 - 04:00 and 06:00 - 10:00 UTC, Monday through Friday, "
    "excluding Chinese public holidays. All other hours are off-peak, including "
    "weekends and Chinese public holidays in full."
)
_DS_FLAT_POLICY = (
    "每个模型仍保留 4 个扁平 *_cost_per_token 键（现有消费方只读这些键）。"
    "它们镜像 _tiers.peak（高峰口径＝预算保守上界），**不是**单一价，也不知道时段；"
    "run 档位已知时必须改用 _tiers.<tier>。"
    "见 docs/iteration/phases/agents-infra/2026-09-26-price-tier-spec.MD"
)
_DS_UNMAPPED = (
    "官方两表都没有『缓存写入 / cache creation』单价行；沿用本仓既有映射 "
    "cache_creation_input_token_cost := cache-miss input 单价（写入即一次 miss）"
)
_DS_CONVERSION = (
    "usd_per_token = round(cny_per_1m / meta.fx_usd_cny / 1e6, 10)"
    " with fx_usd_cny = 7.2"
)


def _provider_meta(prov: str) -> dict:
    """解析器随抓取一并写回的 provider 级元数据（当前只有 deepseek 有档位方案）。"""
    if prov != "deepseek":
        return {}
    return {
        "_tier_scheme": "two_tier",
        "_tier_timezone": _DS_TIMEZONE,
        "_peak_windows": [dict(w) for w in _DS_PEAK_WINDOWS],
        "_peak_windows_verbatim": _DS_WINDOWS_VERBATIM,
        "_peak_windows_utc_verbatim": _DS_WINDOWS_UTC_VERBATIM,
        "_sources": {"cny": _DS_URL_CNY, "usd_display": SOURCES["deepseek"]},
        "_unit_in_source": "CNY per 1M tokens",
        "_unit_in_this_file": "USD per token",
        "_conversion": _DS_CONVERSION,
        "_flat_key_policy": _DS_FLAT_POLICY,
        "_unmapped_official_field": _DS_UNMAPPED,
        "_fetched_at_mode": "fetch-prices.py --apply（本机 HTTP 抓取；时刻为 UTC）",
    }


def _ds_cells(row: str) -> list[tuple[str, bool]]:
    """一行 → `[(文本, 是否 rowspan 格)]`（区间标签格是 `rowspan`，不是数据格）。"""
    return [(_ds_cell_text(inner), "rowspan" in attrs)
            for attrs, inner in _DS_CELLS.findall(row)]


def _ds_amount(cell: str) -> float | None:
    """金额格 → 数值；非金额格 → None。

    两种官方写法都认：`$0.006`（英文页 USD/1M）与 `0.02元`（中文页 CNY/1M）。
    中文页**一个 `$` 都没有**——旧解析器按美元抓，故对中文页恒得 0 个金额。
    """
    text = cell.strip()
    if not _DS_AMOUNT.match(text):
        return None
    try:
        return float(text.lstrip("$").removesuffix("元"))
    except ValueError:
        return None


def _ds_tier(cell: str) -> str | None:
    """格文本 → `peak` / `off_peak`；都认不出 → None。

    英文页用 `PEAK`/`OFF-PEAK`，中文页用 `高峰时段`/`空闲时段`——两者都**逐行**出现，
    故按行内标签走，不依赖列位与 rowspan 继承。
    """
    text = cell.upper()
    if any(lab in text for lab in _DS_OFF_LABELS):
        return "off_peak"
    if any(lab in text for lab in _DS_PEAK_LABELS):
        return "peak"
    return None


def _ds_resource(cell: str | None) -> str | None:
    """格文本 → 资源键（`cache_read`/`input`/`output`）；都不是 → None。"""
    if not cell:
        return None
    for labels, key in _DS_RESOURCES:
        if any(lab in cell for lab in labels):
            return key
    return None


def _ds_block_resource(cells: list[tuple[str, bool]]) -> str | None:
    """行内第一个 `rowspan` 标签格 → 资源键（是价格块的首行）。"""
    for text, is_span in cells:
        if is_span:
            res = _ds_resource(text)
            if res:
                return res
    return None


def _ds_model_names(html: str) -> list[str]:
    """表头行（首格为 `MODEL`／中文页 `模型`）的模型名——**模型数由此读出，不写死 3**。

    末尾脚注角标（页面写 `deepseek-flash (1)`）要去掉：模型名是价表的键，
    带角标会与账本里的模型名对不上（实测：不去角标则 `deepseek-flash (1)` 查不到价）。
    """
    for row in _DS_ROWS.findall(html):
        cells = _ds_cells(row)
        if not cells or cells[0][0].strip().upper() not in ("MODEL", "模型"):
            continue
        return [clean for clean in (_DS_FOOTNOTE.sub("", text).strip()
                                    for text, _ in cells[1:]) if clean]
    return []


def parse_deepseek(html: str) -> dict:
    """deepseek 官方定价表 → `{模型名: _entry(...)}`，**统一换算成 USD/token**。

    形状（2026-09-26 实测两页同构，按 `<tr>` 平铺）：`MODEL | 模型名 × N`；价格表
    **每资源两行**（`空闲时段/OFF-PEAK` 在前、`高峰时段/PEAK` 在后），区间标签在行内，
    模型名只在表头出现、数据行按列位对齐。
    口径：`_tiers.peak` = 保守上界，同时抓到空闲行 ⇒ 两个基准一起更新
    （旧实现按固定下标只取 peak 三项，档位是后来人工补进 JSON 的）。
    单位：英文页 `$` = USD/1M 直接用；中文页 `元` = CNY/1M，按 `_DS_CNY` 换算
    （与 `meta.fx_usd_cny` 同口径；父代理 2026-09-26 裁定"维持 ¥ ÷ fx_usd_cny"）。
    边界：模型名/列数对不上，或价格越界 ⇒ 该模型整体跳过（fail-safe，不写坏数据）。
    """
    models = _ds_model_names(html)
    if not models:
        return {}
    ncol = len(models)
    found: dict[str, dict[str, dict[str, list[float]]]] = {m: {} for m in models}
    resource: str | None = None
    for row in _DS_ROWS.findall(html):
        cells = _ds_cells(row)
        if not cells:
            continue
        label = next((x for x in (_ds_tier(text) for text, _ in cells) if x), None)
        amounts = [v for v in (_ds_amount(text) for text, _ in cells) if v is not None]
        # 价格块首行同时带「资源标签格」与「档位格」——故资源识别必须在这一支里也做：
        # 漏了它就会整块收集不到（实测：`found` 全空 ⇒ 仍然返回 `{}`）。
        res = _ds_block_resource(cells)
        if res:
            resource = res
        if amounts:
            if label and resource and len(amounts) >= ncol:
                for i, name in enumerate(models):
                    slot = found[name].setdefault(resource, {}).setdefault(label, [])
                    slot.append(amounts[i])
    scale = 1.0 / _DS_CNY if "元" in html else 1.0
    out: dict[str, dict] = {}
    for name in models:
        per_res = found.get(name) or {}
        if set(per_res) != {"input", "output", "cache_read"}:
            continue  # 三个资源行没认全 ⇒ 不猜（宁缺勿错）
        if any(len(v) != 1 for res in per_res.values() for v in res.values()):
            continue  # 同一「资源×档」抓到多值（页面变了/解析错位）⇒ 跳过
        if any("peak" not in blk or "off_peak" not in blk for blk in per_res.values()):
            continue  # 只有一排（页面回到单档形状）⇒ 不编造另一个档
        # 每资源取「高峰值 / 空闲值」；换算常量只写一处（cache-write 沿用 miss 单价）
        pk = {r: per_res[r]["peak"][0] * scale for r in per_res}
        off = {r: per_res[r]["off_peak"][0] * scale for r in per_res}
        peak_row = _entry(_per1m([pk["input"]], 0), _per1m([pk["output"]], 0),
                          _per1m([pk["cache_read"]], 0), _per1m([pk["input"]], 0))
        off_row = _entry(_per1m([off["input"]], 0), _per1m([off["output"]], 0),
                         _per1m([off["cache_read"]], 0), _per1m([off["input"]], 0))
        entry = dict(peak_row, _tiers={"peak": peak_row, "off_peak": off_row})
        flat = tuple(entry[k] for k in ("input_cost_per_token", "output_cost_per_token",
                                        "cache_read_input_token_cost",
                                        "cache_creation_input_token_cost"))
        if all(_valid(x) for x in flat):
            out[name] = entry
    return out
def parse_dashscope(html: str) -> dict:
    """阿里云百炼定价页：每模型一行（<p>模型名</p> + International + mode + N 个 $ 价格格）。
    取行内第 1 个 $ = input、第 2 个 $ = output（USD/1M tokens）；只有一个价格格（如
    embedding 模型）时 output 复用 input。解析失败/越界 → 该模型跳过。"""
    out: dict[str, dict] = {}
    targets = ["qwen-omni-turbo", "qwen3.5-omni-plus", "qwen3-max", "text-embedding-v3", "text-embedding-v4"]
    for token in targets:
        m = re.search(r"<p>\s*" + re.escape(token) + r"\s*</p>.*?</tr>", html, re.S)
        if not m:
            continue
        amounts = [float(x) for x in re.findall(r"\$(\d+(?:\.\d+)?)", m.group(0))]
        if not amounts:
            continue
        inp = round(amounts[0] / 1e6, 10)
        outp = round((amounts[1] / 1e6) if len(amounts) > 1 else inp, 10)
        if _valid(inp) and _valid(outp):
            out[token] = _entry(inp, outp, 0.0, inp)
    return out


def parse_openrouter(text: str) -> dict:
    """OpenRouter /api/v1/models JSON：pricing.prompt/completion 即 USD/token。"""
    out: dict[str, dict] = {}
    try:
        data = json.loads(text).get("data", [])
    except json.JSONDecodeError:
        return out
    for item in data:
        name = item.get("id", "")
        if name not in OPENROUTER_MODELS:
            continue
        p = item.get("pricing", {}) or {}
        inp = round(float(p.get("prompt") or 0), 10)
        outp = round(float(p.get("completion") or 0), 10)
        if _valid(inp) and _valid(outp):
            out[name] = _entry(inp, outp, 0.0, inp)
    return out


def merge(existing: dict, scraped: dict) -> dict:
    """scraped 段合并：auto/manual/meta 原样保留；scraped 更新 + 记录抓取时间与来源。

    **按 provider 整段替换，但先并回"解析器不产出的元数据键"**（`_conversion` /
    `_flat_key_policy` / `_aliases` 等）：旧实现是裸 `dict.update`，抓一次就把人手补的
    口径说明**静默抹掉**——而其中 `_peak_windows` 是选档代码的真源
    （`agent-ops.peak_windows_from_prices`）：丢了它，夜间 run 又按高峰计
    （本卡要修的 2 倍高估**原样复发**，且没有任何报错）。解析器产出的键优先。
    """
    out = dict(existing)
    old = out.get("scraped") or {}
    merged = dict(old)
    for prov, payload in scraped.items():
        prev = old.get(prov)
        prev = prev if isinstance(prev, dict) else {}
        carried = {k: v for k, v in prev.items() if k not in payload}
        merged[prov] = {**carried, **payload}
    out["scraped"] = merged
    meta = dict(out.get("meta") or {})
    meta["scraped_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta["scraped_sources"] = SOURCES
    out["meta"] = meta
    return out


# ------------------------------------------ 判据：抓空 / 价表陈旧必须出声（行 15）
# 起因（spec §4 红字 B，实测）：解析器要求"3 模型 + 至少 18 个 `$`"而官网是"2 模型 /
# 12 个金额（中文页 0 个 `$`）"⇒ 恒返回 `{}`、`--apply` 因此**不覆盖**旧价：fail-safe
# 没写坏数据，但**安静地永远返回空**——没人知道价表已经停在 2026-09-20 的截面。
# 故本条把"安静"去掉：抓空 = 点名 WARN（`--check` 下升格 FAIL）；过旧 = 显式 WARN。
_STALE_DAYS = 45  # 本仓刷新约定 = 两周一次（agents/README.md:48）；45 天 = 漏两次以上


def _stale_days(existing: dict) -> float | None:
    """价表 `meta.scraped_at` 距现在的天数；缺失/不可解析 → None（判不出来就不猜）。"""
    raw = (existing.get("meta") or {}).get("scraped_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        stamp = datetime.fromisoformat(raw.strip())
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - stamp).total_seconds() / 86400.0


def judge_scrape(results: dict[str, int], existing: dict, *, strict: bool) -> int:
    """抓取结果与价表截面判据；返回退出码（0 = 出声但可继续，非 0 = FAIL）。

    `results` = `{provider: 解析出的模型数}`（**每个来源都必须有键**，包括 0）。
    `strict`（`--check`）= 把"应有模型却没抓到"升格为 FAIL：`--check` 是**只看结果**的
    模式，它红掉才是"抓取真的坏了"的可见出口（`--apply` 保持 fail-safe 不写坏数据）。
    """
    if not results:
        print("FAIL: 一个来源都没有抓到 —— 抓取链路整体失效")
        return 1
    empty = sorted(p for p, n in results.items() if n == 0)
    if empty:
        print(f"WARN: 解析结果为空的来源 {empty} —— 本次**不会**覆盖它们的旧价"
              "（价表会静默停在旧截面，请人工核对页面形状是否又变了）")
    days = _stale_days(existing)
    if days is None:
        print("WARN: 价表 meta.scraped_at 缺失/不可解析 —— 判不出截面新旧（≠ 很新）")
    elif days > _STALE_DAYS:
        print(f"WARN: 价表截面已过旧：meta.scraped_at 距现在 {days:.1f} 天 "
              f"(> {_STALE_DAYS}) —— 抓取长期无效时成本估算会一直用旧单价")
    if args_strict_fail(strict, empty):
        print(f"FAIL: --check 模式下解析为空的来源 {empty} 视为失效"
              "（--apply 仍是 fail-safe：不覆盖旧价）")
        return 1
    return 0


def args_strict_fail(strict: bool, empty: list[str]) -> bool:
    """`--check` + 抓空 ⇒ FAIL（纯函数，便于反向对照直接驱动）。"""
    return bool(strict and empty)


def _load() -> dict:
    if PRICES_PATH.exists():
        return json.loads(PRICES_PATH.read_text(encoding="utf-8"))
    return {"auto": {}, "manual": {}, "meta": {"currency": "USD", "fx_usd_cny": 7.2}}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    parsers = {"deepseek": parse_deepseek, "dashscope": parse_dashscope, "openrouter": parse_openrouter}
    scraped: dict[str, dict] = {}
    counts: dict[str, int] = {}
    for prov, url in SOURCES.items():
        try:
            refuse_if_offline(url)  # TG-8②：开关开启 → 在任何网络动作之前拒绝（含 DNS/连接）
            text = _fetch(url)
            got = parsers[prov](text)
            counts[prov] = len(got)
            print(f"[{prov}] fetched {len(text)} bytes -> {len(got)} models {sorted(got)}")
            if got:
                scraped[prov] = {"models": got, **_provider_meta(prov)}
        except OfflineRefused:
            # **不吞**：本分支把"开关拒绝"与"网络抖动"分开——前者必须让整条命令以政策退出码结束
            # （"拒绝"不是"抓取失败"，写成 FAIL 会让读日志的人以为再试一次就好了）。
            raise
        except Exception as exc:  # noqa: BLE001
            counts[prov] = 0
            print(f"[{prov}] FAIL: {type(exc).__name__}: {exc}")

    rc = judge_scrape(counts, _load(), strict=args.check)
    if rc != 0 and not args.apply:
        return rc

    if args.apply:
        with _prices_lock():  # 035：与 agent-ops prices-derive 互斥（read-merge-write 全程持锁）
            existing = _load()
            merged = merge(existing, scraped)
            PRICES_PATH.parent.mkdir(parents=True, exist_ok=True)
            PRICES_PATH.write_bytes(json.dumps(merged, ensure_ascii=False, indent=2).encode("utf-8"))
        print(f"[written] {PRICES_PATH}（scraped providers: {sorted(scraped)}）")
        return 0
    print("--check 模式：未写盘。确认数字无误后运行 --apply")
    return 0


if __name__ == "__main__":
    # TG-8②：离线拒绝必须变成**明确的退出码**（政策 `offline_switch.refuse_exit_code`）。
    # `OfflineRefused` 继承 BaseException，故上面的 `except Exception` 兜底不会把它降级成
    # "抓取失败→继续跑"；这里才是唯一收口点。
    try:
        sys.exit(main())
    except OfflineRefused as exc:
        print(f"OFFLINE-REFUSED: {exc}")
        sys.exit(refuse_exit_code())
