"""Sprint-16 TG-5：分层验证 runner（fail-closed + 三态预算闸门）。

按 VERIFY_META.tier 分层执行 verify/ 下的脚本：
  offline = 零网络零 key（CI/本地默认）
  gui     = 需前后端 + Playwright
  network = 真实 API e2e（**花钱**，受预算上限约束）

语义（调研 run-2026-09-12-tech-research-047 采纳）：
  ① **fail-closed**：任一层任一脚本失败 → 整体 FAIL（非零退出，不"部分通过"）；
  ② **预算闸门**：启动前按 VERIFY_META.est_cost_cny 求上界，超上限 → **拒绝启动**（退出码 3，不静默降级）；
  ③ **三态记账**：本轮实际花费 = 由账本/价表核对；runner 自身不臆测花费——network 档记 `cost_status=unknown`
     并提示用真实用量回填（下一轮夜间套件遇到 unknown 会拒绝放行，见 scripts/scheduled-tasks.py）；
  ④ 上限与周期一律可配置：`--budget-cny` > env `PAPERQA_NIGHTLY_BUDGET_CNY` > 默认 10（D3 约束：不得写死）。

用法：
  .venv\\Scripts\\python.exe verify\\run_suite.py --tier offline
  .venv\\Scripts\\python.exe verify\\run_suite.py --tier network --budget-cny 10
  .venv\\Scripts\\python.exe verify\\run_suite.py --tier offline --verify-dir <fixture> --json <out>
"""
from __future__ import annotations
VERIFY_META = {'features': 'TG-5 分层 runner：offline/gui/network 分层 + fail-closed + 三态预算闸门（上限可配置）', 'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0, 'routes': [], 'requires': []}

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from verify.verify_matrix import collect  # noqa: E402

SELF_NAMES = {"run_suite.py"}
DEFAULT_BUDGET_CNY = 10.0
REFUSE_EXIT = 3


def budget_from(args) -> float:
    """上限优先级：CLI > env PAPERQA_NIGHTLY_BUDGET_CNY > 默认 10（可配置，不写死常量语义）。"""
    if args.budget_cny is not None:
        return float(args.budget_cny)
    raw = os.environ.get("PAPERQA_NIGHTLY_BUDGET_CNY")
    if raw:
        try:
            return float(raw)
        except ValueError:
            print(f"WARN: PAPERQA_NIGHTLY_BUDGET_CNY 非法（{raw!r}）→ 回落默认 {DEFAULT_BUDGET_CNY}")
    return DEFAULT_BUDGET_CNY


def select(verify_dir: Path, tier: str, only: list[str] | None) -> list[tuple[Path, dict]]:
    try:
        entries = collect(verify_dir)
    except SystemExit as exc:  # 元数据缺失/非法 → fail-closed 且给出可执行提示
        print(f"FAIL: 脚本元数据校验未通过，runner 拒绝启动（fail-closed）：{exc}")
        print("提示：TG-2 规则要求每个 verify 脚本带 VERIFY_META 头部；修复后重跑 `verify_matrix.py derive`。")
        raise SystemExit(2) from exc
    picked = [
        (p, m)
        for p, m in entries
        if m.get("tier") == tier and p.name not in SELF_NAMES and (not only or p.name in only)
    ]
    return sorted(picked, key=lambda pm: pm[0].name)


def run_one(path: Path, meta: dict, timeout_s: int) -> tuple[int, float]:
    if path.suffix == ".py":
        cmd = [sys.executable, str(path)]
    elif path.suffix == ".mjs":
        cmd = ["node", str(path)]
    else:
        return 127, 0.0
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), timeout=timeout_s, check=False)
        return proc.returncode, round(time.perf_counter() - t0, 2)
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {timeout_s}s")
        return 124, round(time.perf_counter() - t0, 2)


def main() -> int:
    ap = argparse.ArgumentParser(description="分层验证 runner（TG-5）")
    ap.add_argument("--tier", default="offline", choices=["offline", "gui", "network"])
    ap.add_argument("--budget-cny", dest="budget_cny", type=float, default=None,
                    help="本轮花费上限（CNY）；缺省读 env PAPERQA_NIGHTLY_BUDGET_CNY，再缺省 10")
    ap.add_argument("--verify-dir", default=str(ROOT / "verify"))
    ap.add_argument("--scripts", default="", help="只跑这些脚本（逗号分隔文件名）")
    ap.add_argument("--json", default="", help="结果 JSON 落盘路径")
    ap.add_argument("--dry-run", action="store_true", help="只列将执行的脚本与预估花费，不执行")
    args = ap.parse_args()

    verify_dir = Path(args.verify_dir)
    if not verify_dir.is_absolute():
        verify_dir = (ROOT / verify_dir).resolve()
    only = [s.strip() for s in args.scripts.split(",") if s.strip()] or None

    picked = select(verify_dir, args.tier, only)
    est_cost = round(sum(float(m.get("est_cost_cny") or 0) for _, m in picked), 4)
    budget = budget_from(args)
    started = time.time()
    summary: dict = {
        "tier": args.tier,
        "verify_dir": str(verify_dir),
        "budget_cny": budget,
        "est_cost_cny": est_cost,
        "cost_measured_cny": None,
        "cost_status": "not_applicable" if args.tier != "network" else "unknown",
        "started_at": started,
        "scripts": [],
        "status": "unknown",
    }

    print(f"== run_suite tier={args.tier} scripts={len(picked)} est_cost={est_cost} CNY budget={budget} CNY ==")
    if args.tier == "gui":
        print("NOTE: gui 档需要后端 8787 + 前端 5173 已启动（并用 Playwright）；请先确认端口空闲/服务在线，否则本档必然失败。")
    for p, m in picked:
        print(f"  - {p.name} (est {m.get('est_seconds')}s / {m.get('est_cost_cny')} CNY)")

    if est_cost > budget:
        # 三态之"超限"：直接拒绝启动（fail-closed，不降级、不部分执行）
        summary["status"] = "refused_budget"
        summary["finished_at"] = time.time()
        print(f"REFUSED: 预估花费 {est_cost} CNY 超过上限 {budget} CNY → 拒绝启动（fail-closed）。"
              f"如需放行请调高 --budget-cny 或 env PAPERQA_NIGHTLY_BUDGET_CNY。")
        _write_json(args.json, summary)
        return REFUSE_EXIT

    if args.dry_run:
        summary["status"] = "dry_run"
        summary["finished_at"] = time.time()
        print("DRY-RUN: 未执行任何脚本。")
        _write_json(args.json, summary)
        return 0

    failed: list[str] = []
    for p, m in picked:
        timeout_s = int((m.get("est_seconds") or 60) * 4 + 60)
        print(f"--- {p.name} ---", flush=True)
        code, secs = run_one(p, m, timeout_s)
        summary["scripts"].append({"name": p.name, "exit": code, "seconds": secs})
        print(f"--- {p.name}: exit={code} ({secs}s) ---", flush=True)
        if code != 0:
            failed.append(p.name)

    summary["finished_at"] = time.time()
    summary["status"] = "failed" if failed else "ok"
    summary["failed_scripts"] = failed
    _write_json(args.json, summary)

    if failed:
        print(f"\nSUITE FAILED ({len(failed)}/{len(picked)}): {', '.join(failed)}")
        return 1
    print(f"\nSUITE PASSED ({len(picked)} scripts)")
    if args.tier == "network":
        print("NOTE: network 档实际花费需按账本核对后回填（cost_status=unknown）；"
              "未回填时下一轮夜间套件将拒绝放行（三态闸门）。")
    return 0


def _write_json(path_str: str, data: dict) -> None:
    if not path_str:
        return
    p = Path(path_str)
    if not p.is_absolute():
        p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)
    print(f"summary → {p}")


if __name__ == "__main__":
    sys.exit(main())
