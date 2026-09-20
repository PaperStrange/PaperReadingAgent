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
  ⑩ TG-7（走查实证）：状态文件损坏/结构非法 → **拒绝执行**（退出 2，不静默重置 last_run 与成本三态）；
    带 BOM 的合法状态仍被读取（`utf-8-sig`），不误判为损坏
  ⑪ Retro ③：实测成本链路——脚本经 `PAPERQA_SUITE_METRICS` 回报用量 → suite 聚合出
    `cost_measured_cny`；**只有全部脚本都给出可换算成本**才转 `measured`，否则保持 `unknown`；
    **空账（calls=0）不得被当成 measured**；自动回填要求结果 JSON 的 `finished_at` 不早于本轮 t0
  ⑫ 自动回填的新鲜度门槛（fresh 采信 / stale·缺 finished_at·非 measured 不采信）
  ⑬ **预估安全系数可配置**：`--est-factor` > env `PAPERQA_EST_SAFETY_FACTOR` > 默认 1.3；
    非法/非正值回落默认（不放松闸门）

Run: .venv\\Scripts\\python.exe verify\\verify_runner.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'TG-5 分层 runner + 定时底座：offline/gui/network 分层 + fail-closed + 三态预算闸门 + due 判定 + 成本回填 + 状态文件 fail-closed（TG-7）', 'tier': 'offline', 'providers': [], 'est_seconds': 60, 'est_cost_cny': 0, 'routes': [], 'requires': []}

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


def write_fixture(
    d: Path,
    name: str,
    tier: str,
    cost: float,
    exit_code: int,
    marker: Path | None,
    metric_cny: float | None = None,
    unpriced: str = "",
    calls: int = 1,
) -> None:
    marker_line = f'    Path(r"{marker}").write_text("ran", encoding="utf-8")\n' if marker else ""
    metric_line = ""
    if metric_cny is not None or unpriced:
        rec = {
            "script": name,
            "calls": calls,
            "total_tokens": 10,
            "cost_cny": metric_cny,
            "unpriced_models": [unpriced] if unpriced else [],
        }
        metric_line = (
            "    import json as _json, os as _os\n"
            "    _mp = _os.environ.get('PAPERQA_SUITE_METRICS')\n"
            "    if _mp:\n"
            f"        open(_mp, 'a', encoding='utf-8').write(_json.dumps({rec!r}) + '\\n')\n"
        )
    (d / name).write_text(
        "from pathlib import Path\n"
        f"VERIFY_META = {{'features': 'fixture {name}', 'tier': '{tier}', 'providers': [], "
        f"'est_seconds': 1, 'est_cost_cny': {cost}, 'routes': [], 'requires': []}}\n\n"
        "def main():\n"
        f"{marker_line}"
        f"{metric_line}"
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
    # est=20：× 默认系数 1.3 = 26 → ③（上限 10）拒绝、④（env 上限 30）放行，两个断言语义同时成立
    write_fixture(fixture, "verify_fake_cost.py", "network", 20, 0, marker_cost)

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

    # ⑨ 预算参数契约（code-review 050 minor：⑨ 原先在 F-AC8 交付后恒 SKIP，未覆盖"--budget-cny 是否真的注入"）
    state.write_text(json.dumps({"schema": 1, "tasks": {}}, ensure_ascii=False), encoding="utf-8")
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--force", "--dry-run", "--state", str(state)])
    out9 = (res.stdout or "") + (res.stderr or "")
    ok("⑨ scheduled-tasks → run_suite 注入 --budget-cny（闸门接线契约）",
       res.returncode == 0 and "--budget-cny" in out9 and "run_suite.py" in out9,
       out9.strip()[-160:])
    # ⑨b over_budget 语义（code-review 050 major）：回填超上限 → 拒绝放行；--force 可覆盖
    state.write_text(json.dumps({"schema": 1, "config": {"budget_cny": 10}, "tasks": {}}, ensure_ascii=False), encoding="utf-8")
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--record-cost", "999", "--state", str(state)])
    st9 = json.loads(state.read_text(encoding="utf-8"))["tasks"]["nightly-suite"]
    ok("⑨b 回填超上限 → cost_status=over_budget", res.returncode == 0 and st9.get("last_cost_status") == "over_budget",
       json.dumps(st9, ensure_ascii=False))
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--check-due", "--dry-run", "--state", str(state)])
    ok("⑨b over_budget → 拒绝放行（退出 4）且记录 blocked 原因",
       res.returncode == 4 and "REFUSED" in res.stdout,
       f"exit={res.returncode} out={(res.stdout or '').strip()[:120]}")
    st9b = json.loads(state.read_text(encoding="utf-8"))["tasks"]["nightly-suite"]
    ok("⑨b REFUSED 写入 last_blocked_at/last_blocked_reason",
       bool(st9b.get("last_blocked_at")) and bool(st9b.get("last_blocked_reason")),
       json.dumps({k: st9b.get(k) for k in ("last_blocked_at", "last_blocked_reason")}, ensure_ascii=False))
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--check-due", "--dry-run", "--force", "--state", str(state)])
    ok("⑨b --force 可显式覆盖 over_budget", res.returncode == 0 and "OVERRIDE" in res.stdout,
       (res.stdout or "").strip()[:140])
    # ⑨c 失败后自愈（code-review 050 major）：unknown + 上一轮 failed → 允许重试，不静默停摆
    state.write_text(json.dumps({"schema": 1, "tasks": {"nightly-suite": {
        "last_run": time.time() - 8 * 86400, "last_cost_status": "unknown", "last_status": "failed:1"}}}, ensure_ascii=False), encoding="utf-8")
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--check-due", "--dry-run", "--state", str(state)])
    ok("⑨c unknown + 上轮失败 → 放行重试（不自愈则永久停摆）", res.returncode == 0 and "RUN" in res.stdout,
       f"exit={res.returncode} out={(res.stdout or '').strip()[:140]}")

    # ⑩ TG-7（2026-09-20 走查实证）：状态文件不可解析必须 **fail-closed**，不得静默回落默认状态
    #    （修复前 load_state 吞异常返回空状态 → last_run 与成本三态被静默重置 → 预算闸门被绕过）
    state.write_text('{"schema": 1, "tasks": {"nightly-suite": {"last_run": 1', encoding="utf-8")  # 截断 JSON
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--check-due", "--dry-run", "--state", str(state)])
    corrupt = state.with_name(state.name + ".corrupt")
    ok("⑩a 状态文件损坏 → 拒绝执行（退出 2，无 due 判定、无 RUN）",
       res.returncode == 2 and "STATE-ERROR" in res.stdout and "RUN" not in res.stdout,
       f"exit={res.returncode} out={(res.stdout or '').strip()[:120]}")
    ok("⑩a 损坏文件另存 .corrupt 副本（供人工检查）",
       corrupt.exists() and corrupt.read_text(encoding="utf-8").startswith('{"schema"'),
       f"corrupt={corrupt.exists()}")
    # ⑩b BOM 容忍：PowerShell 5.1 `Set-Content -Encoding utf8` 会写 BOM，属常见编码伪影而非损坏
    state.write_text(json.dumps({"schema": 1, "tasks": {"nightly-suite": {
        "last_run": time.time() - 8 * 86400, "last_cost_status": "unknown"}}}, ensure_ascii=False), encoding="utf-8-sig")
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--check-due", "--dry-run", "--state", str(state)])
    ok("⑩b 带 BOM 的合法状态仍被读取（退出 4 REFUSED，且不判损坏）",
       res.returncode == 4 and "REFUSED" in res.stdout and "STATE-ERROR" not in res.stdout,
       f"exit={res.returncode} out={(res.stdout or '').strip()[:120]}")
    # ⑩c 结构非法（顶层非对象）同样 fail-closed
    state.write_text("[]", encoding="utf-8")
    res = run([PY, str(SCHED), "--task", "nightly-suite", "--check-due", "--dry-run", "--state", str(state)])
    ok("⑩c 顶层非 JSON 对象 → 拒绝执行（退出 2）",
       res.returncode == 2 and "STATE-ERROR" in res.stdout,
       f"exit={res.returncode} out={(res.stdout or '').strip()[:120]}")

    # ⑪ Retro ③（2026-09-20）：实测成本链路——脚本回报用量 → suite 聚合 → 三态判定
    priced = tmp / "fixture_priced"
    priced.mkdir()
    write_fixture(priced, "verify_fake_priced.py", "network", 0.2, 0, None, metric_cny=0.5)
    res = run([PY, str(RUN_SUITE), "--tier", "network", "--verify-dir", str(priced), "--json", str(tmp / "r11.json")])
    s11 = json.loads((tmp / "r11.json").read_text(encoding="utf-8"))
    ok("⑪a 全部脚本回报可换算成本 → cost_status=measured 且金额被聚合",
       res.returncode == 0 and s11.get("cost_status") == "measured" and s11.get("cost_measured_cny") == 0.5,
       f"exit={res.returncode} status={s11.get('cost_status')} cost={s11.get('cost_measured_cny')}")

    unpriced = tmp / "fixture_unpriced"
    unpriced.mkdir()
    write_fixture(unpriced, "verify_fake_unpriced.py", "network", 0.2, 0, None, unpriced="mystery-model")
    res = run([PY, str(RUN_SUITE), "--tier", "network", "--verify-dir", str(unpriced), "--json", str(tmp / "r11b.json")])
    s11b = json.loads((tmp / "r11b.json").read_text(encoding="utf-8"))
    ok("⑪b 缺价模型 → cost_status 保持 unknown（不臆测）且点名模型",
       s11b.get("cost_status") == "unknown" and s11b.get("cost_unpriced_models") == ["mystery-model"],
       f"status={s11b.get('cost_status')} unpriced={s11b.get('cost_unpriced_models')}")

    # ⑪c 复核 round-4 major：**空账**（脚本回报了数值成本但 calls=0，即回调尚未落地）不得被当成 measured
    nodata = tmp / "fixture_nodata"
    nodata.mkdir()
    write_fixture(nodata, "verify_fake_nodata.py", "network", 0.2, 0, None, metric_cny=0.0, calls=0)
    res = run([PY, str(RUN_SUITE), "--tier", "network", "--verify-dir", str(nodata), "--json", str(tmp / "r11c.json")])
    s11c = json.loads((tmp / "r11c.json").read_text(encoding="utf-8"))
    ok("⑪c 空账（calls=0 却报数值成本）→ 保持 unknown（防闸门被误推 measured）",
       s11c.get("cost_status") == "unknown" and s11c.get("cost_no_data_scripts") == ["verify_fake_nodata.py"],
       f"status={s11c.get('cost_status')} no_data={s11c.get('cost_no_data_scripts')}")

    # ⑫ 复核 round-4 major#2：自动回填的**新鲜度绑定**（陈旧/缺 finished_at 的结果不得被采信）
    import importlib.util

    spec_m = importlib.util.spec_from_file_location("sched_mod", SCHED)
    assert spec_m and spec_m.loader
    sched_mod = importlib.util.module_from_spec(spec_m)
    spec_m.loader.exec_module(sched_mod)
    now = time.time()
    cases = [
        ("fresh", {"cost_status": "measured", "cost_measured_cny": 1.25, "finished_at": now}, now - 60, 1.25),
        ("stale", {"cost_status": "measured", "cost_measured_cny": 9.99, "finished_at": now - 3600}, now - 60, None),
        ("no_finished_at", {"cost_status": "measured", "cost_measured_cny": 2.0}, now - 60, None),
        ("not_measured", {"cost_status": "unknown", "cost_measured_cny": 3.0, "finished_at": now}, now - 60, None),
    ]
    for name, payload, since, expect in cases:
        p = tmp / f"sched_case_{name}.json"
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        got = sched_mod._suite_measured_cost(p, since=since)
        ok(f"⑫ {name} → {'采信' if expect is not None else '不采信'}",
           got == expect, f"got={got} expect={expect}")

    # ⑬ 预估安全系数**可配置**（2026-09-21 用户口径：实测值 × 系数 = 预检上界，系数不写死）
    res = run([PY, str(RUN_SUITE), "--tier", "network", "--verify-dir", str(fixture), "--json", str(tmp / "r13.json"),
               "--budget-cny", "10", "--est-factor", "0.1"])
    s13 = json.loads((tmp / "r13.json").read_text(encoding="utf-8"))
    ok("⑬a CLI --est-factor 生效（20 × 0.1 = 2 ≤ 10 → 放行并执行）",
       res.returncode == 0 and s13.get("est_safety_factor") == 0.1 and s13.get("est_cost_cny") == 2.0
       and marker_cost.exists(),
       f"exit={res.returncode} factor={s13.get('est_safety_factor')} est={s13.get('est_cost_cny')}")
    marker_cost.unlink(missing_ok=True)
    res = run([PY, str(RUN_SUITE), "--tier", "network", "--verify-dir", str(fixture), "--json", str(tmp / "r13b.json")],
              env_extra={"PAPERQA_EST_SAFETY_FACTOR": "0.1"})
    s13b = json.loads((tmp / "r13b.json").read_text(encoding="utf-8"))
    ok("⑬b env PAPERQA_EST_SAFETY_FACTOR 生效（优先级低于 CLI）",
       res.returncode == 0 and s13b.get("est_safety_factor") == 0.1 and s13b.get("est_cost_cny_raw") == 20.0,
       f"exit={res.returncode} factor={s13b.get('est_safety_factor')} raw={s13b.get('est_cost_cny_raw')}")
    res = run([PY, str(RUN_SUITE), "--tier", "network", "--verify-dir", str(fixture), "--json", str(tmp / "r13c.json"),
               "--budget-cny", "10", "--est-factor", "-1"])
    s13c = json.loads((tmp / "r13c.json").read_text(encoding="utf-8"))
    ok("⑬c 非法系数（负值）→ 回落默认 1.3（fail-closed 不放松闸门）",
       res.returncode == 3 and s13c.get("est_safety_factor") == 1.3 and s13c.get("status") == "refused_budget",
       f"exit={res.returncode} factor={s13c.get('est_safety_factor')} status={s13c.get('status')}")

    print(f"\nALL PASS ({PASSED} assertions)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
