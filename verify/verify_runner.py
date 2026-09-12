"""Sprint-16 TG-5（验收③）：分层 runner + 定时底座 + 三态预算闸门。

全部用**合成 fixture**验证（不跑真实套件，秒级、零成本）：
  ① offline 档全绿 → 退出 0、summary.status=ok
  ② 注入失败脚本 → 退出非 0（fail-closed，不"部分通过"）且 summary 点名失败脚本
  ③ 预估花费 25 > 上限 10 → **拒绝启动**（退出 3、status=refused_budget、脚本未被执行）
  ④ 上限经 env PAPERQA_NIGHTLY_BUDGET_CNY=30 覆盖 → 放行（证明上限可配置，非写死）
  ⑤ 定时底座：未到期 --check-due → SKIP（不执行）
  ⑥ 已到期（上次 8 天前 / 间隔 7 天）→ RUN
  ⑦ 三态闸门：预算制任务上一轮 cost_status=unknown → **拒绝放行**（退出 4）
  ⑧ --record-cost 回填实际花费 → 闸门解除（再次 due → RUN）
  ⑨ providers 实现未就绪（F-AC8 未交付时）→ UNAVAILABLE（退出 5），不静默假成功

Run: .venv\\Scripts\\python.exe verify\\verify_runner.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'TG-5 分层 runner + 定时底座：offline/gui/network 分层 + fail-closed + 三态预算闸门 + due 判定 + 成本回填', 'tier': 'offline', 'providers': [], 'est_seconds': 60, 'est_cost_cny': 0, 'routes': [], 'requires': []}

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PY = sys.executable
RUN_SUITE = ROOT / "verify" / "run_suite.py"
SCHED = ROOT / "scripts" / "scheduled-tasks.py"
PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def run(cmd: list[str], env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(env_extra or {})
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, check=False)


def write_fixture(d: Path, name: str, tier: str, cost: float, exit_code: int, marker: Path | None) -> None:
    marker_line = f'    Path(r"{marker}").write_text("ran", encoding="utf-8")\n' if marker else ""
    (d / name).write_text(
        "from pathlib import Path\n"
        f"VERIFY_META = {{'features': 'fixture {name}', 'tier': '{tier}', 'providers': [], "
        f"'est_seconds': 1, 'est_cost_cny': {cost}, 'routes': [], 'requires': []}}\n\n"
        "def main():\n"
        f"{marker_line}"
        f"    return {exit_code}\n\n"
        "if __name__ == '__main__':\n"
        "    import sys\n"
        "    sys.exit(main())\n",
        encoding="utf-8",
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="verify_runner_"))
    fixture = tmp / "fixture"
    fixture.mkdir()
    marker_pass = tmp / "pass.marker"
    marker_cost = tmp / "cost.marker"
    state = tmp / "schedule.json"

    write_fixture(fixture, "verify_fake_pass.py", "offline", 0, 0, marker_pass)
    write_fixture(fixture, "verify_fake_fail.py", "offline", 0, 2, None)
    write_fixture(fixture, "verify_fake_cost.py", "network", 25, 0, marker_cost)

    # ① offline 档全绿
    res = run([PY, str(RUN_SUITE), "--tier", "offline", "--verify-dir", str(fixture),
               "--scripts", "verify_fake_pass.py", "--json", str(tmp / "r1.json")])
    s1 = json.loads((tmp / "r1.json").read_text(encoding="utf-8"))
    ok("① offline 档全绿 → 退出 0 且 status=ok", res.returncode == 0 and s1.get("status") == "ok",
       f"exit={res.returncode} status={s1.get('status')}")
    ok("① 被执行的脚本有记录", [x["name"] for x in s1.get("scripts") or []] == ["verify_fake_pass.py"],
       json.dumps(s1.get("scripts"), ensure_ascii=False))

    # ② fail-closed：注入失败脚本
    res = run([PY, str(RUN_SUITE), "--tier", "offline", "--verify-dir", str(fixture), "--json", str(tmp / "r2.json")])
    s2 = json.loads((tmp / "r2.json").read_text(encoding="utf-8"))
    ok("② 任一脚本失败 → 退出非 0（fail-closed）", res.returncode != 0, f"exit={res.returncode}")
    ok("② 失败脚本被点名", s2.get("failed_scripts") == ["verify_fake_fail.py"] and s2.get("status") == "failed",
       json.dumps({"failed": s2.get("failed_scripts"), "status": s2.get("status")}, ensure_ascii=False))

    # ③ 预算闸门：25 > 10 → 拒绝启动且未执行
    res = run([PY, str(RUN_SUITE), "--tier", "network", "--verify-dir", str(fixture),
               "--budget-cny", "10", "--json", str(tmp / "r3.json")])
    s3 = json.loads((tmp / "r3.json").read_text(encoding="utf-8"))
    ok("③ 预估超限 → 拒绝启动（退出 3 / refused_budget）",
       res.returncode == 3 and s3.get("status") == "refused_budget",
       f"exit={res.returncode} status={s3.get('status')}")
    ok("③ 拒绝时未执行任何脚本", not marker_cost.exists() and (s3.get("scripts") or []) == [],
       f"marker={marker_cost.exists()}")

    # ④ 上限可配置：env 覆盖 → 放行
    res = run([PY, str(RUN_SUITE), "--tier", "network", "--verify-dir", str(fixture), "--json", str(tmp / "r4.json")],
              env_extra={"PAPERQA_NIGHTLY_BUDGET_CNY": "30"})
    s4 = json.loads((tmp / "r4.json").read_text(encoding="utf-8"))
    ok("④ env 上限覆盖生效（30 ≥ 25 → 放行、执行）",
       res.returncode == 0 and s4.get("status") == "ok" and marker_cost.exists(),
       f"exit={res.returncode} status={s4.get('status')} marker={marker_cost.exists()}")
    ok("④ network 档花费状态记 unknown（待账本回填）", s4.get("cost_status") == "unknown",
       str(s4.get("cost_status")))

    # ⑤ 未到期 → SKIP
    state.write_text(json.dumps({"schema": 1, "config": {"interval_days": {"prices": 7}}, "tasks": {"prices": {"last_run": time.time(), "last_status": "ok"}}}, ensure_ascii=False), encoding="utf-8")
    res = run([PY, str(SCHED), "--task", "prices", "--check-due", "--dry-run", "--state", str(state)])
    ok("⑤ 未到期 → SKIP（退出 0 且不执行）", res.returncode == 0 and "SKIP" in res.stdout, (res.stdout or "").strip()[:120])

    # ⑥ 已到期 → RUN
    state.write_text(json.dumps({"schema": 1, "config": {"interval_days": {"prices": 7}}, "tasks": {"prices": {"last_run": time.time() - 8 * 86400}}}, ensure_ascii=False), encoding="utf-8")
    res = run([PY, str(SCHED), "--task", "prices", "--check-due", "--dry-run", "--state", str(state)])
    ok("⑥ 已到期 → RUN（dry-run 报告将执行）", res.returncode == 0 and "RUN" in res.stdout, (res.stdout or "").strip()[:140])

    # ⑦ 三态闸门：上一轮花费未测量 → 拒绝放行
    state.write_text(json.dumps({"schema": 1, "tasks": {"nightly-suite": {"last_run": time.time() - 8 * 86400, "last_cost_status": "unknown"}}}, ensure_ascii=False), encoding="utf-8")
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--check-due", "--dry-run", "--state", str(state)])
    ok("⑦ cost_status=unknown → 拒绝放行（退出 4，fail-closed）",
       res.returncode == 4 and "REFUSED" in res.stdout, f"exit={res.returncode} out={(res.stdout or '').strip()[:140]}")

    # ⑧ 回填实际花费 → 闸门解除
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--record-cost", "3.5", "--state", str(state)])
    ok("⑧ --record-cost 回填成功（退出 0）", res.returncode == 0, (res.stdout or "").strip()[:120])
    st = json.loads(state.read_text(encoding="utf-8"))
    ok("⑧ 状态记 measured + 金额", st["tasks"]["nightly-suite"].get("last_cost_status") == "measured"
       and st["tasks"]["nightly-suite"].get("last_cost_cny") == 3.5, json.dumps(st["tasks"]["nightly-suite"], ensure_ascii=False))
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--check-due", "--dry-run", "--state", str(state)])
    ok("⑧ 闸门解除后 due 检查放行（RUN）", res.returncode == 0 and "RUN" in res.stdout, (res.stdout or "").strip()[:140])

    # ⑨ providers 未就绪（F-AC8 未交付时）→ UNAVAILABLE，不假成功
    if not (ROOT / "scripts" / "refresh-providers.py").exists():
        state.write_text(json.dumps({"schema": 1, "tasks": {}}, ensure_ascii=False), encoding="utf-8")
        res = run([PY, str(SCHED), "--task", "providers", "--force", "--state", str(state)])
        ok("⑨ providers 实现未就绪 → UNAVAILABLE（退出 5）", res.returncode == 5 and "UNAVAILABLE" in res.stdout,
           f"exit={res.returncode} out={(res.stdout or '').strip()[:120]}")
    else:
        print("SKIP: ⑨ providers 实现已存在（F-AC8 已交付），跳过未就绪断言")

    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
