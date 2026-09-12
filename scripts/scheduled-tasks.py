"""Sprint-16 TG-5：定时任务单一入口（跨平台，可手动 / 可被进程内调度 / 可注册系统任务计划）。

设计依据（调研 run-2026-09-12-tech-research-047）：
  - 本地桌面应用后端并非长驻 → **不依赖进程内触发器的"错过补偿"**，改用显式 **due 判定 + last_run 落盘**：
    错过不丢失（下次检查补跑一次）、不重复轰炸（一轮只跑一次）、可手动 `--force`。
  - **三态成本闸门（fail-closed）**：预算制任务（nightly-suite）在上一轮 `last_cost_status=unknown`
    （未按账本回填实际花费）时**拒绝放行**；"未超预算"绝不从"未测量"推断。回填：`--record-cost <CNY>`。

任务：
  prices         → scripts/fetch-prices.py --apply（M9 价表抓取；默认每 7 天）
  nightly-suite  → verify/run_suite.py --tier network（夜间全量联网套件；默认每 7 天；受预算上限约束）
  providers      → scripts/refresh-providers.py --apply（F-AC8 官网调研刷新；默认每 14 天）

配置（一律可配置，不写死；优先级 CLI > env > state.config > 默认）：
  env: PAPERQA_NIGHTLY_BUDGET_CNY / PAPERQA_SCHEDULE_STATE / PAPERQA_SCHEDULE_<TASK>_DAYS
  state: agents/runtime/schedule.json（gitignore，本地运行时状态）

用法：
  .venv\\Scripts\\python.exe scripts\\scheduled-tasks.py --list
  .venv\\Scripts\\python.exe scripts\\scheduled-tasks.py --task nightly-suite --check-due [--dry-run]
  .venv\\Scripts\\python.exe scripts\\scheduled-tasks.py --task prices --force
  .venv\\Scripts\\python.exe scripts\\scheduled-tasks.py --task nightly-suite --record-cost 3.42
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_STATE = ROOT / "agents" / "runtime" / "schedule.json"
REFUSE_EXIT = 4
UNAVAILABLE_EXIT = 5

TASKS: dict[str, dict] = {
    "prices": {
        "interval_days": 7,
        "cmd": [PY, str(ROOT / "scripts" / "fetch-prices.py"), "--apply"],
        "budgeted": False,
        "desc": "价表抓取（M9，官网固定 URL）",
    },
    "nightly-suite": {
        "interval_days": 7,
        "cmd": [PY, str(ROOT / "verify" / "run_suite.py"), "--tier", "network"],
        "budgeted": True,
        "desc": "夜间全量联网套件（fail-closed，受预算上限约束）",
    },
    "providers": {
        "interval_days": 14,
        "cmd": [PY, str(ROOT / "scripts" / "refresh-providers.py"), "--fetch", "--apply"],
        "budgeted": False,
        "desc": "provider 官网调研刷新（F-AC8：抓取 + M16 归档 + proposal；模型名变更需人工确认）",
    },
}


def state_path(cli_path: str = "") -> Path:
    if cli_path:
        p = Path(cli_path)
        return p if p.is_absolute() else ROOT / p
    env = os.environ.get("PAPERQA_SCHEDULE_STATE")
    if env:
        p = Path(env)
        return p if p.is_absolute() else ROOT / p
    return DEFAULT_STATE


def load_state(p: Path) -> dict:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"schema": 1, "config": {"budget_cny": 10.0, "interval_days": {}}, "tasks": {}}


def save_state(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def interval_days(task: str, state: dict) -> float:
    env = os.environ.get(f"PAPERQA_SCHEDULE_{task.upper().replace('-', '_')}_DAYS")
    if env:
        try:
            return float(env)
        except ValueError:
            print(f"WARN: PAPERQA_SCHEDULE_{task.upper().replace('-', '_')}_DAYS 非法（{env!r}）→ 用配置值")
    cfg = (state.get("config") or {}).get("interval_days") or {}
    if task in cfg:
        return float(cfg[task])
    return float(TASKS[task]["interval_days"])


def budget_cny(state: dict) -> float:
    env = os.environ.get("PAPERQA_NIGHTLY_BUDGET_CNY")
    if env:
        try:
            return float(env)
        except ValueError:
            print(f"WARN: PAPERQA_NIGHTLY_BUDGET_CNY 非法（{env!r}）→ 用配置值")
    return float((state.get("config") or {}).get("budget_cny") or 10.0)


def is_due(task: str, state: dict, now: float | None = None) -> tuple[bool, str]:
    now = now or time.time()
    rec = (state.get("tasks") or {}).get(task) or {}
    last = rec.get("last_run")
    if not last:
        return True, "从未运行"
    days = interval_days(task, state)
    due_at = float(last) + days * 86400
    if now >= due_at:
        return True, f"已到期（上次 {time.strftime('%Y-%m-%d %H:%M', time.localtime(float(last)))}，间隔 {days:g} 天）"
    remain = (due_at - now) / 86400
    return False, f"未到期（剩 {remain:.2f} 天，间隔 {days:g} 天）"


def main() -> int:
    ap = argparse.ArgumentParser(description="定时任务入口（TG-5，due 判定 + 三态成本闸门）")
    ap.add_argument("--task", choices=sorted(TASKS), default="")
    ap.add_argument("--check-due", action="store_true", help="按间隔判定是否到期；未到期则跳过")
    ap.add_argument("--force", action="store_true", help="忽略 due，直接执行")
    ap.add_argument("--list", action="store_true", help="列出任务、间隔与上次运行")
    ap.add_argument("--dry-run", action="store_true", help="只报告将要做什么，不执行、不写状态")
    ap.add_argument("--record-cost", type=float, default=None, help="回填上一轮实际花费（CNY，解除 unknown）")
    ap.add_argument("--state", default="", help="状态文件路径（默认 env PAPERQA_SCHEDULE_STATE 或 agents/runtime/schedule.json）")
    args = ap.parse_args()

    sp = state_path(args.state)
    state = load_state(sp)

    if args.list:
        print(f"state: {sp}")
        print(f"budget_cny: {budget_cny(state)}")
        for name, spec in sorted(TASKS.items()):
            rec = (state.get("tasks") or {}).get(name) or {}
            due, why = is_due(name, state)
            last = rec.get("last_run")
            last_s = time.strftime("%Y-%m-%d %H:%M", time.localtime(float(last))) if last else "从未"
            cost = rec.get("last_cost_cny")
            cost_s = "unknown" if rec.get("last_cost_status") == "unknown" else (f"{cost} CNY" if cost is not None else "-")
            print(f"  {name:14s} 间隔 {interval_days(name, state):>4g} 天 | 上次 {last_s} | 花费 {cost_s} | due={due}（{why}）| {spec['desc']}")
        return 0

    if args.record_cost is not None:
        task = args.task or "nightly-suite"
        rec = state.setdefault("tasks", {}).setdefault(task, {})
        rec["last_cost_cny"] = float(args.record_cost)
        rec["last_cost_status"] = "measured"
        rec["cost_measured_at"] = time.time()
        save_state(sp, state)
        print(f"OK: {task} 实际花费已回填 {args.record_cost} CNY（cost_status=measured）→ 下一轮夜间套件放行。")
        return 0

    if not args.task:
        print("请指定 --task（或 --list）")
        return 2

    spec = TASKS[args.task]
    due, why = is_due(args.task, state)
    if args.check_due and not args.force and not due:
        print(f"SKIP: {args.task} {why}")
        return 0

    # 三态成本闸门：预算制任务在上一轮花费未测量时拒绝放行（fail-closed）
    rec = (state.get("tasks") or {}).get(args.task) or {}
    if spec["budgeted"] and rec.get("last_cost_status") == "unknown":
        print(f"REFUSED: {args.task} 上一轮实际花费未回填（cost_status=unknown）→ 拒绝放行（fail-closed）。"
              f"请先 `--task {args.task} --record-cost <CNY>` 回填账本实际花费。")
        return REFUSE_EXIT

    if args.task == "providers" and not Path(spec["cmd"][1]).exists():
        print(f"UNAVAILABLE: {args.task} 实现尚未就绪（{spec['cmd'][1]} 由 F-AC8 交付）→ 记 skipped。")
        if not args.dry_run:
            state.setdefault("tasks", {}).setdefault(args.task, {})["last_status"] = "unavailable"
            save_state(sp, state)
        return UNAVAILABLE_EXIT

    cmd = list(spec["cmd"])
    if spec["budgeted"]:
        cmd += ["--budget-cny", str(budget_cny(state))]
    print(f"RUN: {' '.join(cmd)}（{why}）")
    if args.dry_run:
        print("DRY-RUN: 未执行、未写状态。")
        return 0

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    secs = round(time.perf_counter() - t0, 2)
    entry = state.setdefault("tasks", {}).setdefault(args.task, {})
    entry["last_run"] = time.time()
    entry["last_duration_s"] = secs
    entry["last_status"] = "ok" if proc.returncode == 0 else f"failed:{proc.returncode}"
    if spec["budgeted"]:
        # runner 自身不臆测花费：执行完标记 unknown，待按账本回填（三态之"未测量"）
        entry["last_cost_status"] = "unknown"
        entry["last_cost_cny"] = None
    save_state(sp, state)
    print(f"DONE: {args.task} exit={proc.returncode} ({secs}s)；state → {sp}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
