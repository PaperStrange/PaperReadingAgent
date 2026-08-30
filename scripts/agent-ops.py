"""AgentOps 账本 CLI（Sprint-8 A-LEDGER，US-8.4）。

职责：子代理 run 的登记/状态流转/成本估算，全部落在**文件真相源**：
  agents/runtime/registry.json          # 账本（append + 完整性校验，防手改双写 UC-7）
  agents/runtime/prices.json            # 价表（litellm 价表派生 + 人工覆盖段 UC-10）
  agents/runs/<run_id>/<role>.report.md # 报告存档（memory 浏览入口）

约束：纯 Python 标准库（UC-11），不依赖 DSH 或仓库外工具；任何编排方（DSH/CI/IDE）都可调用。

用法：
  python scripts/agent-ops.py register --role R --task T --spec "S@v" [--model M] [--start]
      [--input-chars N] [--context-input-tokens N] [--context-max-tokens N]
  python scripts/agent-ops.py update <run_id> --status running
      [--usage-in N --usage-out N --usage-cache-read N --usage-cache-write N]
  python scripts/agent-ops.py finish <run_id> --status succeeded|failed|cancelled
      [--output-chars N] [--result-file PATH] [--cost-override X] [--estimate-mode chars]
  python scripts/agent-ops.py list [--status S] [--role R] [--limit N]
  python scripts/agent-ops.py validate-spec <file.md>
  python scripts/agent-ops.py fetch-spec <file.md> [--offline]
  python scripts/agent-ops.py parse-report <file.md>
  python scripts/agent-ops.py prices-derive

状态机（UC-3）：queued -> running -> succeeded|failed|cancelled；非法流转拒绝。
成本估算（UC-4）：cost = usage x prices.json 单价（含 cache 分列）；无 usage 时按
  input_chars/4、output_chars/4 兜底并标 estimated=true；价表缺该模型 → pending_price。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# AGENT_OPS_DIR 环境变量可重定向账本根（verify 脚本用临时目录隔离；默认 agents）
_AGENTS_BASE = Path(os.environ.get("AGENT_OPS_DIR", str(REPO_ROOT / "agents")))
RUNTIME_DIR = _AGENTS_BASE / "runtime"
REGISTRY_PATH = RUNTIME_DIR / "registry.json"
PRICES_PATH = RUNTIME_DIR / "prices.json"
RUNS_DIR = _AGENTS_BASE / "runs"

_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled"}
_TERMINAL = {"succeeded", "failed", "cancelled"}
_TRANSITIONS = {
    "queued": {"running"},
    "running": _TERMINAL,
}
_CHARS_PER_TOKEN = 4.0  # UC-4 兜底：无 token 上报时 tokens ≈ chars/4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        # review 修正（Sprint-8 三查）：存在但缺 integrity 键 = 手造文件 → 拒绝
        if not data.get("integrity"):
            raise SystemExit("registry.json 缺少完整性字段：疑似手工创建（防双写）。请用 agent-ops CLI 写入。")
    else:
        data = {"version": 1, "runs": []}
    # UC-7：加载时校验完整性（手改即拒，防双写）——必须在任何变更前检查
    if data.get("integrity") and _integrity(data) != data["integrity"]:
        raise SystemExit("registry.json 完整性校验失败：疑似被手工修改（防双写）。请用 agent-ops CLI 写入。")
    return data


def _integrity(data: dict) -> str:
    return _sha256(json.dumps(data["runs"], ensure_ascii=False, sort_keys=True))


def _save_registry(data: dict) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    data["integrity"] = _integrity(data)
    REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_run(data: dict, run_id: str) -> dict:
    for r in data["runs"]:
        if r["run_id"] == run_id:
            return r
    raise SystemExit(f"run {run_id} 不存在")


def _load_prices() -> dict:
    if PRICES_PATH.exists():
        return json.loads(PRICES_PATH.read_text(encoding="utf-8"))
    return {"auto": {}, "manual": {}}


def _prices_for(model: str) -> dict | None:
    """review 修正（Sprint-8 三查）：manual 非 null 时**覆盖** auto（README 契约），auto 为兜底。"""
    p = _load_prices()
    manual = p.get("manual", {}).get(model)
    if manual:  # 非 null 的人工价优先
        return manual
    return p.get("auto", {}).get(model)


def _fx_usd_cny() -> float:
    """用户决策（2026-08-30）：价格以 RMB 计。价表单价为 USD/token，按 meta.fx_usd_cny 换算（可人工覆盖）。"""
    try:
        return float(_load_prices().get("meta", {}).get("fx_usd_cny", 7.2))
    except (TypeError, ValueError):
        return 7.2


def _estimate_cost(entry: dict) -> dict:
    """UC-4：usage x 价表；无 usage 用 chars/4 兜底；无价表标 pending_price。
    输出单位 = CNY（USD 单价 × meta.fx_usd_cny 换算，用户决策 2026-08-30）。"""
    usage = entry.get("usage") or {}
    model = entry.get("model") or ""
    prices = _prices_for(model)
    if not prices:
        return {"total": None, "currency": "CNY", "estimated": True, "pending_price": True, "model": model}
    cost = {
        "input": (usage.get("input_tokens") or 0) * (prices.get("input_cost_per_token") or 0),
        "output": (usage.get("output_tokens") or 0) * (prices.get("output_cost_per_token") or 0),
        "cache_read": (usage.get("cache_read_tokens") or 0) * (prices.get("cache_read_input_token_cost") or 0),
        "cache_write": (usage.get("cache_write_tokens") or 0) * (prices.get("cache_creation_input_token_cost") or 0),
    }
    estimated = False
    if not any(usage.values()):
        ic = entry.get("input_chars") or 0
        oc = entry.get("output_chars") or 0
        cost["input"] = (ic / _CHARS_PER_TOKEN) * (prices.get("input_cost_per_token") or 0)
        cost["output"] = (oc / _CHARS_PER_TOKEN) * (prices.get("output_cost_per_token") or 0)
        estimated = True
    fx = _fx_usd_cny()
    # review 修正（Sprint-9 三查 P1）：分项同样 ×fx 转 CNY，保证分项之和 = total（此前分项仍为 USD、对象级却标 CNY，口径不一致）
    cny = {k: round(v * fx, 8) for k, v in cost.items()}
    return {**cny, "total": round(sum(cny.values()), 8), "currency": "CNY",
            "estimated": estimated, "pending_price": False, "model": model}


def cmd_register(args: argparse.Namespace) -> None:
    data = _load_registry()
    # review 修正（Sprint-8 三查）：显式 run_id 查重（_find_run 只命中第一条）
    if any(r["run_id"] == args.run_id for r in data["runs"]):
        raise SystemExit(f"run_id {args.run_id} 已存在，请更换")
    run_id = args.run_id or f"run-{_now()[:10]}-{args.role}-{len(data['runs']) + 1:03d}"
    # review 修正（Sprint-9 三查 P2）：run-id 将成为 runs/ 下的目录名，限字符集防路径穿越
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise SystemExit(f"run_id 含非法字符（仅允许字母数字 . _ -）：{run_id!r}")
    entry = {
        "run_id": run_id,
        "task_id": args.task or "",
        "role": args.role,
        "spec_source": args.spec,
        "model": args.model or "",
        "status": "running" if args.start else "queued",
        "started_at": _now() if args.start else None,
        "ended_at": None,
        "input_chars": args.input_chars or 0,
        "output_chars": 0,
        "usage": {},
        "context_occupancy": {
            "input_tokens": args.context_input_tokens or 0,
            "max_context": args.context_max_tokens or 0,
            "ratio": round((args.context_input_tokens / args.context_max_tokens), 4)
            if args.context_input_tokens and args.context_max_tokens else 0.0,
        },
        "cost_est": {"total": None, "currency": "CNY", "estimated": True},
        "result_files": [],
        "tags": {},
        "error": None,
    }
    data["runs"].append(entry)
    _save_registry(data)
    print(f"registered {run_id} (status={entry['status']})")


def _apply_usage(r: dict, args: argparse.Namespace) -> None:
    usage = r.setdefault("usage", {})
    for key, val in (("usage_in", "input_tokens"), ("usage_out", "output_tokens"),
                     ("usage_cache_read", "cache_read_tokens"), ("usage_cache_write", "cache_write_tokens")):
        v = getattr(args, key)
        if v is not None:
            usage[val] = v


def cmd_update(args: argparse.Namespace) -> None:
    data = _load_registry()
    r = _find_run(data, args.run_id)
    if args.status:
        # review 修正（Sprint-8 三查）：update 只能进入 running；终态一律走 finish
        # （否则 update --status succeeded 会产出 ended_at/cost_est 缺失的畸形行）
        if args.status != "running":
            raise SystemExit("update 只允许 --status running；终态请用 finish 子命令")
        allowed = _TRANSITIONS.get(r["status"], set())
        if args.status not in allowed:
            raise SystemExit(f"非法流转 {r['status']} -> {args.status}（允许：{sorted(allowed) or '无'}）")
        r["status"] = args.status
        if not r["started_at"]:
            r["started_at"] = _now()
    _apply_usage(r, args)
    _save_registry(data)
    print(f"updated {args.run_id} (status={r['status']})")


def cmd_finish(args: argparse.Namespace) -> None:
    data = _load_registry()
    r = _find_run(data, args.run_id)
    if args.status not in _TERMINAL:
        raise SystemExit(f"finish 需要终态：{sorted(_TERMINAL)}")
    # review 修正（Sprint-8 三查）：finish 仅允许 running -> terminal（queued 先 update running）
    if r["status"] != "running":
        raise SystemExit(f"非法流转 {r['status']} -> {args.status}（finish 仅允许 running -> terminal）")
    r["status"] = args.status
    r["ended_at"] = _now()
    if args.output_chars is not None:
        r["output_chars"] = args.output_chars
    if args.error:
        r["error"] = args.error
    _apply_usage(r, args)
    if args.result_file:
        rel = Path(args.result_file)
        r["result_files"] = [str(rel)]
        if rel.exists():
            RUNS_DIR.mkdir(parents=True, exist_ok=True)
            dest = RUNS_DIR / r["run_id"] / f"{r['role']}.report.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(rel.read_text(encoding="utf-8"), encoding="utf-8")
            # review 修正（Sprint-8 三查）：基准用 _AGENTS_BASE（AGENT_OPS_DIR 重定向时不再崩溃）
            r["result_files"] = [str(dest.relative_to(_AGENTS_BASE))]
    if args.cost_override is not None:
        r["cost_est"] = {"total": args.cost_override, "currency": "CNY", "estimated": False, "override": True}
    else:
        r["cost_est"] = _estimate_cost(r)
    _save_registry(data)
    print(f"finished {args.run_id} -> {r['status']} (cost_est={r['cost_est']})")


def cmd_list(args: argparse.Namespace) -> None:
    data = _load_registry()
    rows = data["runs"]
    if args.status:
        rows = [r for r in rows if r["status"] == args.status]
    if args.role:
        rows = [r for r in rows if r["role"] == args.role]
    if args.limit:
        rows = rows[-args.limit:]
    for r in rows:
        print(f"{r['run_id']:30s} {r['role']:20s} {r['status']:10s} "
              f"cost={r.get('cost_est', {}).get('total')} spec={r['spec_source']}")
    print(f"--- {len(rows)} runs ---")


def cmd_validate_spec(args: argparse.Namespace) -> None:
    """UC-1：spec frontmatter 必填 name(=文件名)+description+version；source 块字段合法。"""
    p = Path(args.spec_file)
    text = p.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        raise SystemExit("FAIL: 缺少 YAML frontmatter")
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    for field in ("name", "description", "version"):
        if not fm.get(field):
            raise SystemExit(f"FAIL: 缺少必填字段 {field}")
    if fm["name"] != p.stem:
        raise SystemExit(f"FAIL: name={fm['name']!r} 与文件名 {p.stem} 不一致")
    if "source" in fm:
        for f in ("url", "ref", "sha256", "fallback"):
            if f not in fm:
                raise SystemExit(f"FAIL: source 块缺 {f}")
    print(f"PASS: {p.name} frontmatter 合法（name={fm['name']} v{fm['version']}）")


def cmd_fetch_spec(args: argparse.Namespace) -> None:
    """UC-2：依 source 块远程拉取（锁 ref + sha256 校验）；--offline 或失败 → 回退本地并告警。"""
    p = Path(args.spec_file)
    text = p.read_text(encoding="utf-8")
    m = re.search(r"^source:\s*\n(?:^\s+(\w+):\s*(.+)$\s*)+", text, re.M)
    if not m:
        print(f"no source block in {p.name}; using local spec")
        return
    src = {
        k.strip(): v.strip().strip('"').strip("'")
        for k, v in (re.findall(r"^  (\w+):\s*(.+)$", m.group(0), re.M))
    }
    url = src.get("url", "")
    want_sha = src.get("sha256", "")
    if args.offline or not url:
        print(f"WARN: offline/无 url → 回退本地 spec {p.name}")
        return
    # review 修正（Sprint-8 三查）：SSRF 防护——仅 http/https + 拒绝私网/回环/链路本地/保留地址
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        print(f"WARN: 非法 scheme {parsed.scheme!r} → 回退本地 spec {p.name}")
        return
    try:
        import ipaddress

        host = parsed.hostname or ""
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            print(f"WARN: 目标地址 {host} 为私网/保留地址（SSRF 防护）→ 回退本地 spec {p.name}")
            return
    except ValueError:
        pass  # 域名形式：交给 DNS 解析（不额外校验）
    ref = src.get("ref", "")
    fetch_url = url.replace("{ref}", ref) if "{ref}" in url else url
    if "{ref}" not in url and ref:
        print(f"NOTE: ref={ref!r} 为声明性锁定（URL 未含 {{ref}} 占位），以 sha256 校验为准")
    try:
        req = urllib.request.Request(fetch_url, headers={"User-Agent": "agent-ops"})
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            remote = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: 拉取失败（{type(exc).__name__}: {exc}）→ 回退本地 spec {p.name}")
        return
    if _sha256(remote) != want_sha:
        print(f"WARN: sha256 校验不符 → 回退本地 spec {p.name}")
        return
    print(f"OK: remote spec fetched & verified ({fetch_url} @ {ref or '?'})")


def cmd_parse_report(args: argparse.Namespace) -> None:
    """UC-5：解析 spec 输出模板（`- critical <位置>：<问题>` 行）为结构化 JSON。

    review 修正（Sprint-8 三查）：位置以**首个全角冒号**切分（ASCII `:` 保留在 where 内，
    使 `engine.py:202` 这类 file:line 位置不被截断）。
    """
    p = Path(args.report_file)
    items = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*(?:\*|-)\s*\**(critical|major|minor|nit)\**[ \t]+([^：]+)[：]\s*(.+)$", line, re.I)
        if m:
            items.append({"level": m.group(1).lower(), "where": m.group(2).strip(), "text": m.group(3).strip()})
    print(json.dumps(items, ensure_ascii=False, indent=2))
    print(f"--- parsed {len(items)} findings ---")


def _derive_prices(args: argparse.Namespace | None = None) -> None:
    """UC-10：从 litellm 捆绑价表派生 prices.json（人工覆盖段保留）。"""
    prices = _load_prices()
    auto = {}
    litellm_json = None
    for base in [Path(p) for p in sys.path if p]:
        cand = base / "litellm" / "model_prices_and_context_window_backup.json"
        if cand.exists():
            litellm_json = cand
            break
    if litellm_json:
        table = json.loads(litellm_json.read_text(encoding="utf-8"))
        for model in ("gpt-4o-mini", "text-embedding-3-large"):
            src = table.get(model, {})
            auto[model] = {k: src.get(k) for k in
                           ("max_input_tokens", "input_cost_per_token", "output_cost_per_token",
                            "cache_read_input_token_cost", "cache_creation_input_token_cost")}
    else:
        print("WARN: 未找到 litellm 价表，仅保留人工覆盖段")
    out = {"auto": auto, "manual": prices.get("manual", {}),
           "meta": prices.get("meta", {"currency": "USD", "fx_usd_cny": 7.2})}
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    PRICES_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"prices.json 已派生：auto={sorted(auto)} manual={sorted(out['manual'])}")


def main() -> int:
    # review 修正（Sprint-8 三查）：跨 IDE 承诺——Windows 非 UTF-8 终端打印中文不乱码/不崩
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    ap = argparse.ArgumentParser(description="AgentOps 账本 CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("register")
    p.add_argument("--role", required=True)
    p.add_argument("--task", default="")
    p.add_argument("--spec", required=True)
    p.add_argument("--model", default="")
    p.add_argument("--start", action="store_true")
    p.add_argument("--input-chars", type=int)
    p.add_argument("--context-input-tokens", type=int)
    p.add_argument("--context-max-tokens", type=int)
    p.add_argument("--run-id", default="")

    p = sub.add_parser("update")
    p.add_argument("run_id")
    p.add_argument("--status", choices=["running"])  # 终态一律走 finish（三查修正）
    p.add_argument("--usage-in", type=int)
    p.add_argument("--usage-out", type=int)
    p.add_argument("--usage-cache-read", type=int)
    p.add_argument("--usage-cache-write", type=int)

    p = sub.add_parser("finish")
    p.add_argument("run_id")
    p.add_argument("--status", required=True, choices=sorted(_TERMINAL))
    p.add_argument("--output-chars", type=int)
    p.add_argument("--result-file")
    p.add_argument("--cost-override", type=float)
    p.add_argument("--error", default="")
    p.add_argument("--usage-in", type=int)
    p.add_argument("--usage-out", type=int)
    p.add_argument("--usage-cache-read", type=int)
    p.add_argument("--usage-cache-write", type=int)

    p = sub.add_parser("list")
    p.add_argument("--status")
    p.add_argument("--role")
    p.add_argument("--limit", type=int)

    p = sub.add_parser("validate-spec")
    p.add_argument("spec_file")
    p = sub.add_parser("fetch-spec")
    p.add_argument("spec_file")
    p.add_argument("--offline", action="store_true")
    p = sub.add_parser("parse-report")
    p.add_argument("report_file")
    sub.add_parser("prices-derive")

    args = ap.parse_args()
    {
        "register": cmd_register, "update": cmd_update, "finish": cmd_finish,
        "list": cmd_list, "validate-spec": cmd_validate_spec, "fetch-spec": cmd_fetch_spec,
        "parse-report": cmd_parse_report, "prices-derive": _derive_prices,
    }[args.cmd](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
