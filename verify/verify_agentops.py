"""Sprint-8 A-UC 用例断言（可复现）：验证 agent-ops CLI 实现遵循调研结论。

覆盖用例：UC-1 spec frontmatter 校验 / UC-2 source 块远程引用回退 / UC-3 账本状态机 /
UC-4 成本估算（价表 + chars/4 兜底 + pending_price）/ UC-5 报告输出模板解析 /
UC-7 防双写完整性校验 / UC-9 自报上下文与成本覆盖 / UC-10 价表派生 /
UC-11 fetch-spec sha256 命中/失配（M10）/ UC-12 账本并发锁无丢失更新（M10）/
UC-13 fetch-prices 解析与合并优先级（M9）/ UC-14 评审类 run 的 scope 来源闸门（TG-11）。

运行：.venv\\Scripts\\python.exe verify\\verify_agentops.py（纯离线，隔离到临时 AGENT_OPS_DIR）
"""

from __future__ import annotations
VERIFY_META = {'features': 'AgentOps 账本 CLI 用例断言 UC-1~UC-14（离线；UC-11/12=M10，UC-13=M9，UC-14=TG-11 scope 来源闸门）', 'tier': 'offline', 'providers': [], 'est_seconds': 10, 'est_cost_cny': 0, 'routes': [], 'requires': ['none']}

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts" / "agent-ops.py"
FUNCTIONS = ROOT / "agents" / "functions"

sys.path.insert(0, str(ROOT))

from verify.agent_policy import load_policy  # noqa: E402

# TG-15：角色集合**不再在本文件复制一份**（原先这里写死 {"code-review","doc-audit"}，与
# agent-ops.py 的 `_REVIEW_ROLES`、verify_close_readiness.py 的 `CLOSE_ROLES` 三处并存 →
# 加角色要改三处）。现在统一从政策数据读：spec frontmatter 的 `scope_required`。
_POLICY = load_policy()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0


def run(args: list[str], env: dict, check: bool = False, raw: bool = False) -> subprocess.CompletedProcess:
    """跑一次 CLI。

    TG-11 闸门生效后，评审类 `register` 必须声明 scope 来源；合成 fixture 不涉及真实评审范围，
    因此默认自动补 `--scope-source self-chosen --deviation <fixture 说明>`。
    **反向对照/负向用例必须用 `raw=True`**（否则闸门被 helper 掩盖，断言恒真）。
    评审类集合来自 `agents/functions/*.md` 的 `scope_required`（TG-15：不再在本文件写死角色名）。
    """
    if (not raw and args and args[0] == "register" and "--scope-source" not in args
            and "--deviation" not in args and args[args.index("--role") + 1] in _POLICY.review_roles):
        args = [*args, "--scope-source", "self-chosen", "--deviation", "verify_agentops 合成 fixture（无真实评审范围）"]
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

        # UC-11（M10）：fetch-spec sha256 命中/失配——成功路径受 SSRF 防护无法离线走网络，
        # 比对逻辑已抽为 _match_sha256 纯函数，进程内断言两分支
        import importlib.util
        spec = importlib.util.spec_from_file_location("agent_ops", CLI)
        ao = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(ao)
        ok("UC-11 sha256 命中", ao._match_sha256("remote-body", ao._sha256("remote-body")) is True)
        ok("UC-11 sha256 失配", ao._match_sha256("remote-body", "abc") is False)

        # UC-12（M10）：账本并发锁——6 个进程并发 register，无 last-writer-wins 丢失更新
        procs = [
            subprocess.Popen(
                [sys.executable, str(CLI), "register", "--role", f"conc-{i}", "--task", "t",
                 "--spec", "code-review@1.0.0", "--start"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding="utf-8", errors="replace", env=base_env,
            )
            for i in range(6)
        ]
        outs = [p.communicate(timeout=60)[0] for p in procs]
        ok("UC-12 并发 register 全部成功",
           all(p.returncode == 0 for p in procs),
           "; ".join(o.strip()[-60:] for o in outs if "registered" not in o))
        data12 = json.loads(registry.read_text(encoding="utf-8"))
        conc = [r for r in data12["runs"] if r["role"].startswith("conc-")]
        ok("UC-12 无丢失更新（6/6 在账）", len(conc) == 6, f"found {len(conc)}")
        r = run(["list"], base_env, check=True)
        ok("UC-12 并发后完整性有效", r.returncode == 0, "list 加载通过完整性校验")

        # UC-13（M9）：fetch-prices 解析器（deepseek 表格 / openrouter JSON）+ 合并与优先级
        spec_fp = importlib.util.spec_from_file_location("fetch_prices", ROOT / "scripts" / "fetch-prices.py")
        fp = importlib.util.module_from_spec(spec_fp)
        assert spec_fp.loader is not None
        spec_fp.loader.exec_module(fp)
        deepseek_html = (
            '<table><tr><td colspan="3" style="text-align:center">MODEL</td>'
            "<td>deepseek-v4-flash</td><td>deepseek-v4-pro</td><td>deepseek-v4-flash-vision-exp</td></tr>"
            '<tr><td rowspan="6">PRICING</td><td rowspan="2">1M INPUT TOKENS<br>(CACHE HIT)</td>'
            "<td>OFF-PEAK</td><td>$0.007</td><td>$0.022</td><td>$0.007</td></tr>"
            "<tr><td>PEAK</td><td>$0.014</td><td>$0.044</td><td>$0.014</td></tr>"
            '<tr><td rowspan="2">1M INPUT TOKENS<br>(CACHE MISS)</td>'
            "<td>OFF-PEAK</td><td>$0.22</td><td>$0.66</td><td>$0.22</td></tr>"
            "<tr><td>PEAK</td><td>$0.44</td><td>$1.32</td><td>$0.44</td></tr>"
            '<tr><td rowspan="2">1M OUTPUT TOKENS</td>'
            "<td>OFF-PEAK</td><td>$0.66</td><td>$1.98</td><td>$0.66</td></tr>"
            "<tr><td>PEAK</td><td>$1.32</td><td>$3.96</td><td>$1.32</td></tr></table>Concurrency 10"
        )
        ds = fp.parse_deepseek(deepseek_html)

        # ⑬（2026-09-21 关闭三查·二查 windows major）：重定向逐跳复检必须挂在 **HTTPRedirectHandler** 上。
        # 旧实现 `class _SafeRedirectHandler(urllib.request.HTTPSHandler)` —— `redirect_request` 定义在
        # `HTTPRedirectHandler` 上，HTTPSHandler 子类的该方法**从不被 urllib 调用** = 死代码，
        # 而 `build_opener` 仍会挂默认重定向处理器 → 白名单可被一次 302 绕过（SSRF 面）。
        import urllib.request as _ur

        _opener = _ur.build_opener(fp._SafeRedirectHandler())
        ok("⑬ fetch-prices 的重定向复检挂在 HTTPRedirectHandler 上（非死代码），且是 opener 实际使用的处理器",
           issubclass(fp._SafeRedirectHandler, _ur.HTTPRedirectHandler)
           and any(isinstance(h, fp._SafeRedirectHandler) for h in _opener.handlers),
           f"mro={[c.__name__ for c in fp._SafeRedirectHandler.__mro__[:3]]}")

        ok("UC-13 deepseek 表格解析（PEAK 口径）",
           "deepseek-v4-flash" in ds
           and abs(ds["deepseek-v4-flash"]["input_cost_per_token"] - 4.4e-7) < 1e-12
           and abs(ds["deepseek-v4-flash"]["output_cost_per_token"] - 1.32e-6) < 1e-12,
           f"flash={ds.get('deepseek-v4-flash')}")
        orjson = '{"data":[{"id":"openai/gpt-4o-mini","pricing":{"prompt":"1.5e-7","completion":"6e-7"}}]}'
        orr = fp.parse_openrouter(orjson)
        ok("UC-13 openrouter JSON 解析",
           "openai/gpt-4o-mini" in orr
           and abs(orr["openai/gpt-4o-mini"]["input_cost_per_token"] - 1.5e-7) < 1e-15,
           f"orr={orr}")
        dsh_html = ('<tr><td><p>qwen-omni-turbo</p><blockquote><p>eq</p></blockquote></td>'
                    '<td><p>International</p></td><td><p>Non-Thinking mode</p></td>'
                    '<td><p>$0.07</p></td><td><p>$4.44</p></td><td><p>$0.21</p></td></tr>')
        dsc = fp.parse_dashscope(dsh_html)
        ok("UC-13 dashscope 行解析",
           "qwen-omni-turbo" in dsc
           and abs(dsc["qwen-omni-turbo"]["input_cost_per_token"] - 7e-8) < 1e-12
           and abs(dsc["qwen-omni-turbo"]["output_cost_per_token"] - 4.44e-6) < 1e-12,
           f"dsc={dsc}")
        merged = fp.merge(
            {"auto": {"a": {"input_cost_per_token": 1e-6}}, "manual": {"m": None}, "meta": {"fx_usd_cny": 7.2}},
            {"deepseek": {"models": {"deepseek-v4-flash": ds["deepseek-v4-flash"]}}},
        )
        ok("UC-13 merge 保留 auto/manual/meta 且新增 scraped",
           merged["auto"]["a"]["input_cost_per_token"] == 1e-6 and "m" in merged["manual"]
           and merged["meta"]["fx_usd_cny"] == 7.2
           and "deepseek-v4-flash" in merged["scraped"]["deepseek"]["models"],
           "merge 结构")
        # 优先级：manual 非 null 覆盖 scraped；manual null → scraped 兜底（进程内重载 module 以改 AGENT_OPS_DIR）
        os.environ["AGENT_OPS_DIR"] = str(tmp)
        spec_ao2 = importlib.util.spec_from_file_location("agent_ops2", CLI)
        ao2 = importlib.util.module_from_spec(spec_ao2)
        assert spec_ao2.loader is not None
        spec_ao2.loader.exec_module(ao2)
        prices13 = {
            "auto": {}, "manual": {"m": None, "wins": {"input_cost_per_token": 9e-9}},
            "scraped": {"deepseek": {"models": {"m": {"input_cost_per_token": 1e-9}, "wins": {"input_cost_per_token": 1e-9}}}},
            "meta": {},
        }
        (tmp / "runtime" / "prices.json").write_text(json.dumps(prices13, ensure_ascii=False), encoding="utf-8")
        ok("UC-13 manual 非 null 覆盖 scraped",
           ao2._prices_for("wins")["input_cost_per_token"] == 9e-9, "manual wins")
        ok("UC-13 manual null → scraped 兜底",
           ao2._prices_for("m") is not None and ao2._prices_for("m")["input_cost_per_token"] == 1e-9,
           "scraped fallback")

        # UC-14（TG-11，Sprint-17）：评审类 run 的 scope 来源闸门（fail-closed，机器可验）
        # 反向对照：本块断言在**未修复**实现上必须不成立（旧 CLI 无 --scope-source/--deviation 参数）
        r = run(["register", "--role", "code-review", "--task", "nc", "--spec", "code-review@1.0.0"],
                base_env, raw=True)
        ok("UC-14 评审 run 无 scope 来源 → 拒绝（fail-closed）",
           r.returncode != 0 and "scope" in (r.stdout + r.stderr), (r.stdout + r.stderr).strip()[:80])
        r = run(["register", "--role", "code-review", "--task", "nc", "--spec", "code-review@1.0.0",
                 "--scope-source", "impact-assessment:run-does-not-exist"], base_env, raw=True)
        ok("UC-14 引用不存在的〇查 run → 拒绝",
           r.returncode != 0 and "不存在" in (r.stdout + r.stderr), (r.stdout + r.stderr).strip()[:80])
        r = run(["register", "--role", "code-review", "--task", "nc", "--spec", "code-review@1.0.0",
                 "--scope-source", "self-chosen", "--deviation", "太短"], base_env, raw=True)
        ok("UC-14 偏离理由过短 → 拒绝",
           r.returncode != 0 and "过短" in (r.stdout + r.stderr), (r.stdout + r.stderr).strip()[:80])
        run(["register", "--role", "impact-assessment", "--task", "kickoff", "--spec", "impact-assessment@1.4.2",
             "--run-id", "run-uc14-kickoff"], base_env, check=True)
        r = run(["register", "--role", "code-review", "--task", "ok", "--spec", "code-review@1.0.0",
                 "--run-id", "run-uc14-review",
                 "--scope-source", "impact-assessment:run-uc14-kickoff"], base_env, raw=True)
        ok("UC-14 引用真实〇查 run → 放行", r.returncode == 0 and "registered" in r.stdout,
           (r.stdout + r.stderr).strip()[:60])
        e14 = next(x for x in json.loads(registry.read_text(encoding="utf-8"))["runs"]
                   if x["run_id"] == "run-uc14-review")
        ok("UC-14 scope 来源落库（可机验）", e14.get("scope_source") == "impact-assessment:run-uc14-kickoff",
           f"scope_source={e14.get('scope_source')}")
        r = run(["register", "--role", "code-review", "--task", "self", "--spec", "code-review@1.0.0",
                 "--run-id", "run-uc14-self",
                 "--deviation", "复现用户报告的按钮缺陷，只需看单个组件"], base_env, raw=True)
        ok("UC-14 自选范围 + 偏离理由 → 放行", r.returncode == 0, (r.stdout + r.stderr).strip()[:80])
        e14b = next(x for x in json.loads(registry.read_text(encoding="utf-8"))["runs"]
                    if x["run_id"] == "run-uc14-self")
        ok("UC-14 自选范围留痕（self-chosen + 中文理由不被转码）",
           e14b.get("scope_source") == "self-chosen" and "按钮缺陷" in (e14b.get("scope_deviation") or ""),
           f"source={e14b.get('scope_source')} dev={e14b.get('scope_deviation')}")
        r = run(["register", "--role", "tech-research", "--task", "tr", "--spec", "tech-research@1.0.0",
                 "--run-id", "run-uc14-research"], base_env, raw=True)
        ok("UC-14 非评审 role 不强制 scope 来源（防假红）", r.returncode == 0, (r.stdout + r.stderr).strip()[:80])

        # UC-15（TG-15，Sprint-17 D2）：闸门政策**数据驱动**——角色集合/阈值来自数据文件，
        # 不是代码常量。反向对照：在仓库 spec 目录里临时新增一个声明 `scope_required: true` 的角色，
        # **不改任何代码**，CLI 必须立刻要求它声明 scope；把声明改成 false 后必须立刻放行。
        # 这同时证明"删声明绕不过去"（缺声明是报错，不是放行，见数据源完备性自检）。
        extra_spec = FUNCTIONS / "tg15-probe-role.md"
        try:
            extra_spec.write_text(
                '---\nname: tg15-probe-role\ndescription: TG-15 数据驱动探针角色\n'
                'version: "1.0.0"\nscope_required: true\ncoverage_window: self\n---\n\n# probe\n',
                encoding="utf-8")
            r = run(["register", "--role", "tg15-probe-role", "--task", "probe",
                     "--spec", "tg15-probe-role@1.0.0"], base_env, raw=True)
            ok("UC-15 新增角色只改数据（spec 声明 scope_required: true）→ 立刻被要求声明 scope",
               r.returncode != 0 and "scope" in (r.stdout + r.stderr), (r.stdout + r.stderr).strip()[:80])

            extra_spec.write_text(
                '---\nname: tg15-probe-role\ndescription: TG-15 数据驱动探针角色\n'
                'version: "1.0.0"\nscope_required: false\ncoverage_window: none\n---\n\n# probe\n',
                encoding="utf-8")
            r = run(["register", "--role", "tg15-probe-role", "--task", "probe", "--run-id", "run-uc15-probe",
                     "--spec", "tg15-probe-role@1.0.0"], base_env, raw=True)
            ok("UC-15 同一角色改声明为 scope_required: false → 立刻放行（政策生效路径 = 数据）",
               r.returncode == 0, (r.stdout + r.stderr).strip()[:80])

            e15 = next(x for x in json.loads(registry.read_text(encoding="utf-8"))["runs"]
                       if x["run_id"] == "run-uc15-probe")
            ok("UC-15 覆盖窗口随角色声明落库（coverage_window=none）",
               e15.get("coverage_window") == "none", f"coverage_window={e15.get('coverage_window')}")
            ok("UC-15 锚点自动化：register/finish 由 CLI 记 coverage_anchor，无需人抄",
               bool(e15.get("coverage_anchor")), f"coverage_anchor={(e15.get('coverage_anchor') or '')[:8]}")
        finally:
            extra_spec.unlink(missing_ok=True)

        # UC-16（TG-15）：数据源**缺声明**不是"不需要"，而是 fail-closed 报错（删声明绕不过闸门）
        probe_spec = FUNCTIONS / "tg15-undeclared-role.md"
        try:
            probe_spec.write_text(
                '---\nname: tg15-undeclared-role\ndescription: 缺 scope_required 声明\n'
                'version: "1.0.0"\n---\n\n# probe\n', encoding="utf-8")
            r = run(["list"], base_env, raw=True)
            ok("UC-16 spec 缺 scope_required → CLI fail-closed（POLICY-ERROR，不静默放行）",
               r.returncode != 0 and "POLICY-ERROR" in (r.stdout + r.stderr),
               (r.stdout + r.stderr).strip()[:100])
        finally:
            probe_spec.unlink(missing_ok=True)

        r = run(["list"], base_env, raw=True)
        ok("UC-16 移除缺声明 spec 后恢复正常（证明上一条失败来自数据缺口本身）",
           r.returncode == 0, (r.stdout + r.stderr).strip()[:80])


        # UC-17（审核 F1/N5）：coverage_anchor 必须**规范化**为完整 sha，无法解析则 fail-closed
        head_full = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                   capture_output=True, text=True, encoding="utf-8").stdout.strip()
        head_short = head_full[:8]
        run(["register", "--role", "impact-assessment", "--task", "anchor", "--spec", "impact-assessment@1.4.4",
             "--run-id", "run-uc17-short", "--coverage-anchor", head_short], base_env, check=True)
        e17 = next(x for x in json.loads(registry.read_text(encoding="utf-8"))["runs"]
                   if x["run_id"] == "run-uc17-short")
        ok("UC-17 短 sha 锚点被规范化为完整 40 位", e17.get("coverage_anchor") == head_full,
           f"anchor={str(e17.get('coverage_anchor'))[:12]}… ({len(str(e17.get('coverage_anchor')))} chars)")
        r = run(["register", "--role", "impact-assessment", "--task", "anchor", "--spec", "impact-assessment@1.4.4",
                 "--run-id", "run-uc17-bad", "--coverage-anchor", "deadbeefdeadbeef"], base_env, raw=True)
        ok("UC-17 无法解析的锚点 → 拒绝（fail-closed，不静默存坏值）",
           r.returncode != 0 and "COVERAGE-ANCHOR-ERROR" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:70])
        r = run(["set-anchor", "run-uc17-short", "--anchor", head_short, "--reason", "太短"], base_env, raw=True)
        ok("UC-17 回填缺理由（<10 字符）→ 拒绝", r.returncode != 0 and "理由" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:70])
        r = run(["set-anchor", "run-uc17-short", "--anchor", head_short,
                 "--reason", "审核 F1：短 sha 使覆盖窗口被静默丢弃，回填为完整 sha"], base_env, raw=True)
        e17b = next(x for x in json.loads(registry.read_text(encoding="utf-8"))["runs"]
                    if x["run_id"] == "run-uc17-short")
        ok("UC-17 受控回填成功且留痕（anchor_backfills）",
           r.returncode == 0 and e17b.get("coverage_anchor") == head_full
           and len(e17b.get("anchor_backfills") or []) == 1,
           f"backfills={len(e17b.get('anchor_backfills') or [])}")

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
