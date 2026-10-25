"""TG-10：**多轮次 agent 的账本记录**回归（用户 2026-09-21 疑虑驱动）。

背景：同一 run 被追加多轮复核时，账本只留首轮（run-053：53 秒 / 12800 字符，实际 5 轮约 4h53m），
因为 `finish` 的状态机拒绝 `succeeded→succeeded` → 看板严重低估时长与产出，且**看不出被中断过**。

覆盖（离线，用 `AGENT_OPS_DIR` 重定向到临时目录，不碰真实账本）：
  ① register → finish(succeeded) 基线；② 终态 run 仍可 `round` 追加（追加式更新，不改首轮语义）；
  ③ `rounds[0]` 保留首轮快照（ended_at/output_chars）；④ `rounds_count` 与 `output_chars` 累加；
  ⑤ `ended_at` 前移 → `list` 的 dur 反映**累计**时长而非首轮；⑥ `round --interrupted` 同时记中断事件；
  ⑦ 独立 `interrupt` 子命令写入 原因/影响/来源；⑧ `list` 展示 rounds/dur/int；⑨ 不存在的 run → 非零退出；
  ⑩ run 状态不被 `round` 改动（仍是 succeeded）。

Run: .venv\\Scripts\\python.exe verify\\verify_ledger_rounds.py
"""
from __future__ import annotations
VERIFY_META = {'features': 'TG-10 账本多轮次记录：round 追加（终态可用）/首轮快照保留/产出累加/累计时长/中断事件（round --interrupted 与 interrupt）/list 展示/非法 run 拒绝（离线）', 'tier': 'offline', 'providers': [], 'est_seconds': 8, 'est_cost_cny': 0, 'routes': [], 'requires': ['none']}

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "scripts" / "agent-ops.py"
PY = sys.executable
PASSED = 0

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def run(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run([PY, str(OPS), *args], cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, check=False)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        env = {**os.environ, "AGENT_OPS_DIR": td}
        reg = Path(td) / "runtime" / "registry.json"  # 账本路径 = <AGENT_OPS_DIR>/runtime/registry.json
        run_id = "run-2026-09-21-multi-round-demo"
        spec = str(ROOT / "agents" / "functions" / "code-review.md")

        # TG-11 闸门（Sprint-17）：评审类 run 必须声明 scope 来源；本脚本是合成 fixture，走显式偏离声明
        res = run(["register", "--run-id", run_id, "--role", "code-review", "--spec", spec, "--start",
                   "--deviation", "verify_ledger_rounds 合成 fixture（无真实评审范围）"], env)
        ok("① register 成功", res.returncode == 0 and reg.exists(), (res.stdout or res.stderr).strip()[:80])
        # R-001（G3）夹具声明（父代理 2026-09-26 授权的第三文件改动，仅此一处）：
        # 本条 `register --start` 与 `finish` 紧邻、落在**同一秒** ⇒ `zero_duration`，
        # 时长对它是**非测量**（本脚本断的是 rounds 追加/首轮快照/产出累加，不是时长）
        # ⇒ 显式 `--allow-degenerate` + 具名理由；**不是**放宽守卫
        # （守卫的拒绝路径由 verify_agentops.py 的 UC-24 三条反向对照真跑）。
        res = run(["finish", run_id, "--status", "succeeded", "--output-chars", "12800",
                   "--allow-degenerate", "--degenerate-reason",
                   "fixture: 同秒收尾，非真实测量（R-001）"], env)
        ok("① finish(succeeded) 成功", res.returncode == 0, (res.stdout or "").strip()[:80])
        base = json.loads(reg.read_text(encoding="utf-8"))["runs"][0]
        base_end, base_out = base["ended_at"], base["output_chars"]
        ok("① 基线：终态 run、rounds_count 未设置", base["status"] == "succeeded" and not base.get("rounds_count"),
           f"status={base['status']} rounds={base.get('rounds_count')}")

        time.sleep(1.1)  # 让 ISO 秒级时间戳可区分
        res = run(["round", run_id, "--note", "Round 2：复核修复版", "--output-chars", "5000"], env)
        ok("② 终态 run 仍可追加轮次（追加式，不报状态机错）", res.returncode == 0, (res.stdout or res.stderr).strip()[:100])
        r = json.loads(reg.read_text(encoding="utf-8"))["runs"][0]
        ok("③ 首轮快照保留在 rounds[0]",
           (r.get("rounds") or [{}])[0].get("output_chars") == base_out
           and (r.get("rounds") or [{}])[0].get("ended_at") == base_end,
           json.dumps((r.get("rounds") or [{}])[0], ensure_ascii=False)[:120])
        ok("④ rounds_count=2 且产出累加（12800+5000=17800）",
           r.get("rounds_count") == 2 and r.get("output_chars") == 17800,
           f"rounds={r.get('rounds_count')} out={r.get('output_chars')}")
        ok("④ 第 2 轮 note 落账", (r.get("rounds") or [{}])[1].get("note", "").startswith("Round 2"),
           str((r.get("rounds") or [{}])[1].get("note"))[:40])
        ok("⑤ ended_at 前移（累计时长 > 首轮 53 秒量级）", r["ended_at"] > base_end, f"{base_end} → {r['ended_at']}")
        ok("⑩ round 不改 run 状态", r["status"] == "succeeded", r["status"])

        time.sleep(1.1)
        res = run(["round", run_id, "--note", "Round 3：被中断（端口争用）", "--output-chars", "0", "--interrupted",
                   "--impact", "该轮评审顺延至下一轮补做"], env)
        r = json.loads(reg.read_text(encoding="utf-8"))["runs"][0]
        ok("⑥ round --interrupted 同时记中断事件",
           res.returncode == 0 and r.get("interruptions_count") == 1
           and (r.get("interruptions") or [{}])[0].get("impact", "").startswith("该轮评审顺延"),
           json.dumps((r.get("interruptions") or [{}])[0], ensure_ascii=False)[:140])

        res = run(["interrupt", run_id, "--reason", "误杀其派生进程树 3 次", "--impact", "验证中断并自动重试",
                   "--by", "main-agent"], env)
        r = json.loads(reg.read_text(encoding="utf-8"))["runs"][0]
        ok("⑦ interrupt 子命令写入原因/影响/来源",
           res.returncode == 0 and r.get("interruptions_count") == 2
           and (r.get("interruptions") or [{}])[1].get("reason") == "误杀其派生进程树 3 次"
           and (r.get("interruptions") or [{}])[1].get("by") == "main-agent",
           json.dumps((r.get("interruptions") or [{}])[1], ensure_ascii=False)[:140])

        res = run(["list"], env)
        line = next((ln for ln in (res.stdout or "").splitlines() if run_id in ln), "")
        ok("⑧ list 展示 rounds/dur/int", "rounds=3" in line and "dur=" in line and "int=2" in line, line.strip()[:140])

        res = run(["round", "run-不存在", "--note", "x"], env)
        ok("⑨ 不存在的 run → 非零退出", res.returncode != 0, f"exit={res.returncode}")

        # ⑪/⑫（2026-09-21 关闭三查·二查 windows major）：`round`/`interrupt` **未持 registry 锁**，
        # 且 `_save_registry` 是非原子 `write_text`（截断 + 写入）→ 并发下账本可被截断/丢更新。
        # 反向对照：⑪ 检查装饰器接线（确定性），⑫ 用 6 个并发 round 检查实际无丢失（行为面）。
        import importlib.util as _ilu

        _spec = _ilu.spec_from_file_location("agent_ops_mod", OPS)
        _ao = _ilu.module_from_spec(_spec)
        assert _spec.loader is not None
        _spec.loader.exec_module(_ao)
        ok("⑪ round/interrupt 走加锁路径（装饰器接线可自检）",
           hasattr(_ao.cmd_round, "__wrapped__") and hasattr(_ao.cmd_interrupt, "__wrapped__"),
           f"round={getattr(_ao.cmd_round, '__wrapped__', None)} interrupt={getattr(_ao.cmd_interrupt, '__wrapped__', None)}")

        base_rounds = json.loads(reg.read_text(encoding="utf-8"))["runs"][0].get("rounds_count")
        conc = [subprocess.Popen([PY, str(OPS), "round", run_id, "--note", f"并发轮次 {i}", "--output-chars", "10"],
                                 cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
                for i in range(6)]
        for p in conc:
            p.wait(timeout=60)
        after = json.loads(reg.read_text(encoding="utf-8"))["runs"][0]
        ok("⑫ 6 个并发 round 无丢失更新（rounds_count = 基线 + 6，账本仍是合法 JSON）",
           after.get("rounds_count") == int(base_rounds) + 6,
           f"base={base_rounds} after={after.get('rounds_count')}")

    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
