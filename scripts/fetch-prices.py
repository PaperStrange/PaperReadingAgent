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


class _SafeRedirectHandler(urllib.request.HTTPSHandler):
    """重定向逐跳复检：任一跳落到非 https 或白名单外域名 → 抛错（拒绝跟随）。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _host_allowed(newurl):
            raise ValueError(f"redirect to non-allowlisted target: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(url: str, timeout: int = 30) -> str:
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


def parse_deepseek(html: str) -> dict:
    """deepseek 官方定价表：MODEL 表头 3 模型 × 6 价格行（hit/miss/output × off-peak/peak）。
    取 **PEAK**（保守口径：预算上限决策用上界）。价格单位 USD/1M tokens。
    注：HTML 正则解析有脆性，靠 `_valid` 边界兜底（越界模型整体跳过，fail-safe）。"""
    m = re.search(r"MODEL</td>(?:<td>(.*?)</td>){3}", html, re.S)
    if not m:
        return {}
    # 注意：表头 MODEL 单元格带 colspan，不会被 <td> 精确匹配，findall 结果即 3 个模型名
    models = re.findall(r"<td>([^<]+)</td>", m.group(0))
    sec = html[html.find("PRICING"):]
    sec = sec[: sec.find("Concurrency") if "Concurrency" in sec else len(sec)]
    amounts = [float(x) for x in re.findall(r"\$(\d+(?:\.\d+)?)", sec)]
    if len(amounts) < 18 or len(models) != 3:
        return {}
    out = {}
    for j, name in enumerate(models):
        hit_peak = _per1m(amounts, 3 + j)    # cache hit PEAK
        miss_peak = _per1m(amounts, 9 + j)   # cache miss PEAK
        out_peak = _per1m(amounts, 15 + j)   # output PEAK
        e = _entry(miss_peak, out_peak, hit_peak, miss_peak)
        if all(_valid(x) for x in (e["input_cost_per_token"], e["output_cost_per_token"],
                                   e["cache_read_input_token_cost"], e["cache_creation_input_token_cost"])):
            out[name] = e
    return out


def parse_dashscope(html: str) -> dict:
    """阿里云百炼定价页：每模型一行（<p>模型名</p> + International + mode + N 个 $ 价格格）。
    取行内第 1 个 $ = input、第 2 个 $ = output（USD/1M tokens）；只有一个价格格（如
    embedding 模型）时 output 复用 input。解析失败/越界 → 该模型跳过。"""
    out: dict[str, dict] = {}
    targets = ["qwen-omni-turbo", "qwen3-max", "text-embedding-v3"]
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
    """scraped 段合并：auto/manual/meta 原样保留；scraped 更新 + 记录抓取时间与来源。"""
    out = dict(existing)
    old = out.get("scraped") or {}
    merged = dict(old)
    merged.update(scraped)
    out["scraped"] = merged
    meta = dict(out.get("meta") or {})
    meta["scraped_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta["scraped_sources"] = SOURCES
    out["meta"] = meta
    return out


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
    for prov, url in SOURCES.items():
        try:
            text = _fetch(url)
            got = parsers[prov](text)
            print(f"[{prov}] fetched {len(text)} bytes -> {len(got)} models {sorted(got)}")
            if got:
                scraped[prov] = {"models": got}
        except Exception as exc:  # noqa: BLE001
            print(f"[{prov}] FAIL: {type(exc).__name__}: {exc}")

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
    sys.exit(main())
