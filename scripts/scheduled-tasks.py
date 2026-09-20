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
SUITE_RESULT = ROOT / "verify" / "suite_result.json"  # Retro ③：suite 实测成本回填源
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
        "cmd": [PY, str(ROOT / "verify" / "run_suite.py"), "--tier", "network", "--json", str(SUITE_RESULT)],
        "budgeted": True,
        "desc": "夜间全量联网套件（fail-closed，受预算上限约束；成本按实测自动回填）",
    },
    "providers": {
        "interval_days": 14,
        "cmd": [PY, str(ROOT / "scripts" / "refresh-providers.py"), "--fetch", "--apply"],
        "budgeted": False,
        "desc": "provider 官网调研刷新（F-AC8：抓取 + M16 归档 + proposal；模型名变更需人工确认）",
    },
}


def _suite_measured_cost(path: Path, since: float | None = None) -> float | None:
    """读 suite 结果里的**实测**成本（Retro ③）。

    三重门槛（复核 round-4 major#2 加固）：
    ① `cost_status == "measured"`（suite 内部已保证"所有脚本都回报了可换算成本"）；
    ② 金额是数值；
    ③ `since` 给定时要求结果的 `finished_at` **不早于**本轮开始时间——否则本轮 suite 在重写
       结果前就崩了/被杀，会把**上一轮**的 measured 当成本轮实测（并顺带放行闸门）。
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if data.get("cost_status") != "measured":
        return None
    if since is not None:
        try:
            if float(data.get("finished_at") or 0.0) < float(since):
                return None
        except (TypeError, ValueError):
            return None
    try:
        return float(data.get("cost_measured_cny"))
    except (TypeError, ValueError):
        return None


def state_path(cli_path: str = "") -> Path:
    if cli_path:
        p = Path(cli_path)
        return p if p.is_absolute() else ROOT / p
    env = os.environ.get("PAPERQA_SCHEDULE_STATE")
    if env:
        p = Path(env)
        return p if p.is_absolute() else ROOT / p
    return DEFAULT_STATE


class StateUnreadable(RuntimeError):
    """状态文件存在但无法解析。

    TG-7（2026-09-20 走查实证）：修复前 `load_state` 吞掉异常返回默认空状态 → 损坏/带 BOM 的状态
    文件会让 `last_run` 与成本三态被**静默重置**，三态预算闸门因此被绕过（fail-open）。
    现在解析失败一律 fail-closed：抛本异常，由 main 以退出码 2 拒绝执行。
    """


def load_state(p: Path) -> dict:
    """读状态文件（fail-closed）。

    - 文件**不存在** → 全新状态（首次运行是合法场景）；
    - 文件存在但**解析失败** → 抛 `StateUnreadable`，并把损坏文件另存为 `<name>.corrupt`；
    - 编码用 `utf-8-sig`：容忍 BOM（Windows PowerShell 5.1 的 `Set-Content -Encoding utf8`
      会写 BOM），不把这种常见编码伪影误判为损坏。
    """
    if not p.exists():
        return {"schema": 1, "config": {"budget_cny": 10.0, "interval_days": {}}, "tasks": {}}

    def _keep_corrupt() -> None:
        try:
            p.with_name(p.name + ".corrupt").write_text(
                p.read_text(encoding="utf-8", errors="replace"), encoding="utf-8"
            )
        except Exception:
            pass

    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        _keep_corrupt()
        raise StateUnreadable(f"{p}（{type(exc).__name__}: {exc}）") from exc
    if not isinstance(data, dict):
        _keep_corrupt()
        raise StateUnreadable(f"{p}（顶层不是 JSON 对象，而是 {type(data).__name__}）")
    tasks = data.get("tasks")
    if tasks is not None and not isinstance(tasks, dict):
        raise StateUnreadable(f"{p}（tasks 字段不是 JSON 对象）")
    return data


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
    try:
        state = load_state(sp)
    except StateUnreadable as exc:
        print(f"STATE-ERROR: 状态文件无法解析 → 拒绝执行（fail-closed；避免静默重置 last_run 与成本三态）：{exc}")
        print(f"处理建议：检查/修复该文件（损坏副本已另存为 {sp.name}.corrupt）；"
              f"确认要丢弃历史状态时，先把原文件移走或删除，再重跑本命令。")
        return 2

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
        cap = budget_cny(state)
        rec["last_cost_cny"] = float(args.record_cost)
        rec["last_cost_cap_cny"] = cap
        rec["last_cost_status"] = "measured" if float(args.record_cost) <= cap else "over_budget"
        rec["cost_measured_at"] = time.time()
        save_state(sp, state)
        if rec["last_cost_status"] == "over_budget":
            print(f"OK: {task} 实际花费已回填 {args.record_cost} CNY —— **超过上限 {cap} CNY** → cost_status=over_budget，"
                  f"下一轮夜间套件将拒绝放行（确认后可 `--force` 覆盖或调高上限）。")
        else:
            print(f"OK: {task} 实际花费已回填 {args.record_cost} CNY（上限 {cap}）→ cost_status=measured，下一轮放行。")
        return 0

    if not args.task:
        print("请指定 --task（或 --list）")
        return 2

    spec = TASKS[args.task]
    due, why = is_due(args.task, state)
    if args.check_due and not args.force and not due:
        print(f"SKIP: {args.task} {why}")
        return 0

    # 三态成本闸门（fail-closed；code-review 050 major 修复）：
    #   ① over_budget → 拒绝（除非 --force 显式覆盖）；
    #   ② unknown（上一轮成功但未回填）→ 拒绝；
    #   ③ unknown 且上一轮**失败/中断** → 放行重试（避免"失败一次永久停摆且不自愈"的静默停摆）。
    rec = (state.get("tasks") or {}).get(args.task) or {}
    if spec["budgeted"]:
        status = rec.get("last_cost_status")
        last_status = str(rec.get("last_status") or "")
        blocked_reason = ""
        if status == "over_budget":
            blocked_reason = (f"上一轮实测花费 {rec.get('last_cost_cny')} CNY 超过上限 {budget_cny(state)} CNY"
                              f"（cost_status=over_budget）")
        elif status == "unknown" and not last_status.startswith("failed"):
            blocked_reason = "上一轮实际花费未回填（cost_status=unknown）"
        if blocked_reason and not args.force:
            rec["last_blocked_at"] = time.time()
            rec["last_blocked_reason"] = blocked_reason
            state.setdefault("tasks", {})[args.task] = rec
            save_state(sp, state)
            print(f"REFUSED: {args.task} {blocked_reason} → 拒绝放行（fail-closed）。"
                  f"回填：`--task {args.task} --record-cost <CNY>`；确认要跑：`--force`。")
            return REFUSE_EXIT
        if blocked_reason and args.force:
            print(f"OVERRIDE: {args.task} {blocked_reason} → --force 覆盖，本轮放行（已记录）。")

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

    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    secs = round(time.perf_counter() - t0, 2)
    entry = state.setdefault("tasks", {}).setdefault(args.task, {})
    entry["last_run"] = time.time()
    entry["last_duration_s"] = secs
    entry["last_status"] = "ok" if proc.returncode == 0 else f"failed:{proc.returncode}"
    if spec["budgeted"]:
        # Retro ③（2026-09-20）：优先用 suite 的**实测**成本自动回填；拿不到完整且**本轮新鲜**的实测才保持 unknown
        measured = _suite_measured_cost(SUITE_RESULT, since=t0) if proc.returncode == 0 else None
        cap = budget_cny(state)
        if measured is None:
            entry["last_cost_status"] = "unknown"
            entry["last_cost_cny"] = None
            entry["last_cost_note"] = (
                "本轮未取得可采信的实测成本（suite 未成功重写结果 JSON / 脚本未回报用量 / 价表缺单价）"
                "→ 保持 unknown（未测量不放行），需 `--record-cost` 人工回填"
            )
        else:
            entry["last_cost_cny"] = measured
            entry["last_cost_cap_cny"] = cap
            entry["last_cost_status"] = "measured" if measured <= cap else "over_budget"
            entry["cost_measured_at"] = time.time()
            entry["last_cost_note"] = "由 verify/suite_result.json 的实测成本自动回填（Retro ③；finished_at ≥ 本轮 t0）"
    save_state(sp, state)
    cost_s = entry.get("last_cost_status", "-")
    print(f"DONE: {args.task} exit={proc.returncode} ({secs}s)；cost_status={cost_s}"
          + (f" 实测 {entry.get('last_cost_cny')} CNY" if entry.get("last_cost_cny") is not None else "")
          + f"；state → {sp}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
