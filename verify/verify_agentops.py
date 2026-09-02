"""Sprint-8 A-UC 用例断言（可复现）：验证 agent-ops CLI 实现遵循调研结论。

覆盖用例：UC-1 spec frontmatter 校验 / UC-2 source 块远程引用回退 / UC-3 账本状态机 /
UC-4 成本估算（价表 + chars/4 兜底 + pending_price）/ UC-5 报告输出模板解析 /
UC-7 防双写完整性校验 / UC-9 自报上下文与成本覆盖 / UC-10 价表派生。

运行：.venv\\Scripts\\python.exe verify\\verify_agentops.py（纯离线，隔离到临时 AGENT_OPS_DIR）
"""

from __future__ import annotations
VERIFY_META = {'features': 'AgentOps 账本 CLI 用例断言 UC-1~UC-10（离线）', 'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0, 'routes': [], 'requires': ['none']}

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts" / "agent-ops.py"
FUNCTIONS = ROOT / "agents" / "functions"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0


def run(args: list[str], env: dict, check: bool = False) -> subprocess.CompletedProcess:
    r = subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    if check and r.returncode != 0:
        raise AssertionError(f"cmd {' '.join(args)} failed: {r.stdout} {r.stderr}")
    return r


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="verify_agentops_"))
    base_env = {**os.environ, "AGENT_OPS_DIR": str(tmp), "PYTHONUTF8": "1"}
    runtime = tmp / "runtime"
    registry = runtime / "registry.json"
    try:
        # UC-10 前置：人工覆盖段先就位（deepseek 模型无价 → pending_price 场景）
        runtime.mkdir(parents=True)
        (runtime / "prices.json").write_text(
            json.dumps({"auto": {}, "manual": {"deepseek-v4-flash": None}}, ensure_ascii=False),
            encoding="utf-8",
        )
        run(["prices-derive"], base_env, check=True)
        prices = json.loads((runtime / "prices.json").read_text(encoding="utf-8"))
        ok("UC-10 价表派生", "gpt-4o-mini" in prices["auto"] and "text-embedding-3-large" in prices["auto"],
           "auto 提取 gpt-4o-mini/text-embedding-3-large")
        ok("UC-10 人工覆盖段保留", "deepseek-v4-flash" in prices["manual"], "manual 段不被派生覆盖")

        # UC-1：真实 spec 全部合法；坏 spec 拒绝
        for f in sorted(FUNCTIONS.glob("*.md")):
            r = run(["validate-spec", str(f)], base_env)
            ok(f"UC-1 validate-spec {f.name}", r.returncode == 0 and "PASS" in r.stdout, r.stdout.strip()[:60])
        bad = tmp / "bad.md"
        bad.write_text("---\nname: bad\ndescription: x\n---\nbody\n", encoding="utf-8")  # 缺 version
        r = run(["validate-spec", str(bad)], base_env)
        ok("UC-1 缺 version 拒绝", r.returncode != 0 and "version" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:60])

        # UC-2：source 块远程拉取失败 → 回退本地并告警（bogus URL + --offline）
        src = tmp / "remote-spec.md"
        src.write_text(
            "---\nname: remote-spec\ndescription: x\nversion: '1.0.0'\n"
            "source:\n  url: http://127.0.0.1:9/nope.md\n  ref: v1\n  sha256: abc\n  fallback: local.md\n---\nbody\n",
            encoding="utf-8",
        )
        r = run(["fetch-spec", str(src)], base_env, check=True)
        ok("UC-2 拉取失败回退", "回退本地" in r.stdout, r.stdout.strip()[:80])
        r = run(["fetch-spec", str(src), "--offline"], base_env, check=True)
        ok("UC-2 --offline 回退", "回退本地" in r.stdout, r.stdout.strip()[:80])

        # UC-3：状态机（queued→running→succeeded；非法流转拒绝）
        run(["register", "--role", "code-review", "--task", "branch:windows", "--spec", "code-review@1.0.0",
             "--model", "gpt-4o-mini"], base_env, check=True)
        r = run(["list"], base_env, check=True)
        run_id = json.loads(registry.read_text(encoding="utf-8"))["runs"][0]["run_id"]
        run(["update", run_id, "--status", "running"], base_env, check=True)
        r = run(["update", run_id, "--status", "queued"], base_env)
        ok("UC-3 非法流转 running→queued 拒绝", r.returncode != 0, (r.stdout + r.stderr).strip()[:60])
        run(["finish", run_id, "--status", "succeeded", "--output-chars", "2000"], base_env, check=True)
        r = run(["finish", run_id, "--status", "failed"], base_env)
        ok("UC-3 终态再 finish 拒绝", r.returncode != 0 and "非法流转" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:60])
        r = run(["update", run_id, "--status", "running"], base_env)
        ok("UC-3 终态再 running 拒绝", r.returncode != 0 and "非法流转" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:60])

        # UC-4：usage×价表精确值（gpt-4o-mini: in=1.5e-7, out=6e-7；USD 0.00135 × fx 7.2 = CNY 0.00972）
        run(["register", "--role", "code-review", "--task", "branch:main", "--spec", "code-review@1.0.0",
             "--model", "gpt-4o-mini", "--start"], base_env, check=True)
        data = json.loads(registry.read_text(encoding="utf-8"))
        run2 = data["runs"][1]["run_id"]
        run(["finish", run2, "--status", "succeeded", "--usage-in", "1000", "--usage-out", "2000",
             "--output-chars", "100"], base_env, check=True)
        cost = json.loads(registry.read_text(encoding="utf-8"))["runs"][1]["cost_est"]
        ok("UC-4 价表精确值（CNY）", abs(cost["total"] - 0.00972) < 1e-9 and not cost["estimated"]
           and cost["currency"] == "CNY",
           f"total={cost['total']}（期望 0.00972）")
        # review 修正（Sprint-9 三查 P1）：分项同为 CNY（×fx），且分项之和 = total
        ok("UC-4 分项 CNY（input/output）",
           abs(cost["input"] - 0.00108) < 1e-9 and abs(cost["output"] - 0.00864) < 1e-9
           and abs(cost["input"] + cost["output"] - cost["total"]) < 1e-9,
           f"input={cost['input']} output={cost['output']} total={cost['total']}")

        # UC-4：chars/4 兜底 + estimated（USD 0.00075 × 7.2 = CNY 0.0054）
        run(["register", "--role", "doc-audit", "--task", "docs", "--spec", "doc-audit@1.0.0",
             "--model", "gpt-4o-mini", "--input-chars", "4000", "--start"], base_env, check=True)
        run3 = json.loads(registry.read_text(encoding="utf-8"))["runs"][2]["run_id"]
        run(["finish", run3, "--status", "succeeded", "--output-chars", "4000"], base_env, check=True)
        cost3 = json.loads(registry.read_text(encoding="utf-8"))["runs"][2]["cost_est"]
        ok("UC-4 chars/4 兜底（CNY）", cost3["estimated"] and abs(cost3["total"] - 0.0054) < 1e-9,
           f"total={cost3['total']} estimated={cost3['estimated']}（期望 0.0054）")

        # UC-4：pending_price（deepseek-v4-flash 无价）
        run(["register", "--role", "code-review", "--task", "pr:1", "--spec", "code-review@1.0.0",
             "--model", "deepseek-v4-flash", "--start"], base_env, check=True)
        run4 = json.loads(registry.read_text(encoding="utf-8"))["runs"][3]["run_id"]
        run(["finish", run4, "--status", "succeeded"], base_env, check=True)
        cost4 = json.loads(registry.read_text(encoding="utf-8"))["runs"][3]["cost_est"]
        ok("UC-4 pending_price", cost4.get("pending_price") is True, f"cost_est={cost4}")

        # 三查修正回归：manual 非 null 时覆盖 auto（人工价 in=1e-6/out=2e-6 → USD 0.005 × 7.2 = CNY 0.036）
        p = json.loads((runtime / "prices.json").read_text(encoding="utf-8"))
        p["manual"]["gpt-4o-mini"] = {"input_cost_per_token": 1e-6, "output_cost_per_token": 2e-6}
        (runtime / "prices.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
        run(["register", "--role", "code-review", "--task", "pr:2", "--spec", "code-review@1.0.0",
             "--model", "gpt-4o-mini", "--start"], base_env, check=True)
        run6 = json.loads(registry.read_text(encoding="utf-8"))["runs"][4]["run_id"]
        run(["finish", run6, "--status", "succeeded", "--usage-in", "1000", "--usage-out", "2000"],
            base_env, check=True)
        cost6 = json.loads(registry.read_text(encoding="utf-8"))["runs"][4]["cost_est"]
        ok("三查修正 manual 覆盖 auto（CNY）", abs(cost6["total"] - 0.036) < 1e-9, f"total={cost6['total']}（期望 0.036）")

        # 三查修正：update 只允许 running；finish 只允许 running→terminal
        run(["register", "--role", "code-review", "--task", "x", "--spec", "code-review@1.0.0"],
            base_env, check=True)
        runX = json.loads(registry.read_text(encoding="utf-8"))["runs"][5]["run_id"]
        r = run(["update", runX, "--status", "succeeded"], base_env)
        ok("三查修正 update 终态拒绝", r.returncode != 0, (r.stdout + r.stderr).strip()[:60])
        r = run(["finish", runX, "--status", "succeeded"], base_env)
        ok("三查修正 queued→finish 拒绝", r.returncode != 0 and "running" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:60])

        # 三查修正：SSRF 防护（保留地址拒绝）
        ssrf = tmp / "ssrf-spec.md"
        ssrf.write_text(
            "---\nname: ssrf-spec\ndescription: x\nversion: '1.0.0'\n"
            "source:\n  url: http://169.254.169.254/x\n  ref: v1\n  sha256: abc\n  fallback: local.md\n---\nbody\n",
            encoding="utf-8",
        )
        r = run(["fetch-spec", str(ssrf)], base_env, check=True)
        ok("三查修正 SSRF 拒绝", "SSRF" in r.stdout, r.stdout.strip()[:80])

        # 三查修正：run-id 查重
        r = run(["register", "--role", "code-review", "--task", "y", "--spec", "code-review@1.0.0",
                 "--run-id", run6], base_env)
        ok("三查修正 run-id 查重", r.returncode != 0 and "已存在" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:60])

        # review 修正（Sprint-9 三查 P2）：run-id 字符集校验（将成为 runs/ 下目录名）
        r = run(["register", "--role", "code-review", "--task", "z", "--spec", "code-review@1.0.0",
                 "--run-id", "../evil"], base_env)
        ok("三查修正 run-id 字符集", r.returncode != 0 and "非法字符" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:60])

        # UC-9：上下文占用 ratio + 成本覆盖
        run(["register", "--role", "code-review", "--task", "branch:windows", "--spec", "code-review@1.0.0",
             "--model", "gpt-4o-mini", "--context-input-tokens", "1000", "--context-max-tokens", "8000",
             "--start"], base_env, check=True)
        run5 = json.loads(registry.read_text(encoding="utf-8"))["runs"][6]["run_id"]
        run(["finish", run5, "--status", "succeeded", "--cost-override", "0.5"], base_env, check=True)
        e5 = json.loads(registry.read_text(encoding="utf-8"))["runs"][6]
        ok("UC-9 上下文 ratio", e5["context_occupancy"]["ratio"] == 0.125, f"ratio={e5['context_occupancy']['ratio']}")
        ok("UC-9 成本覆盖", e5["cost_est"]["total"] == 0.5 and e5["cost_est"].get("override") is True,
           f"cost={e5['cost_est']}")

        # UC-5：报告输出模板解析（critical/major/minor/nit）
        rep = tmp / "sample-report.md"
        rep.write_text(
            "# code-review 报告\n"
            "- critical engine.py:202：污染环境变量。建议：移除写回。是否本轮必修：是\n"
            "- major app.py:10：竞态。建议：加锁。是否本轮必修：否\n"
            "- minor a.py:1：样式。建议：统一。是否本轮必修：否\n"
            "- nit b.py:2：注释。建议：改写。是否本轮必修：否\n",
            encoding="utf-8",
        )
        r = run(["parse-report", str(rep)], base_env, check=True)
        parsed = json.loads(r.stdout.split("---")[0])
        levels = [x["level"] for x in parsed]
        ok("UC-5 报告解析", levels == ["critical", "major", "minor", "nit"], f"levels={levels}")
        ok("UC-5 file:line 位置保留", parsed[0]["where"] == "engine.py:202", f"where={parsed[0]['where']}")

        # UC-7：手改 registry → CLI 下一次写入拒绝
        data = json.loads(registry.read_text(encoding="utf-8"))
        data["runs"][0]["output_chars"] = 999999  # 手改
        registry.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        r = run(["register", "--role", "code-review", "--task", "x", "--spec", "code-review@1.0.0"], base_env)
        ok("UC-7 防双写", r.returncode != 0 and "完整性校验" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:80])

        print(f"\nALL PASS ({PASSED} assertions)")
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
