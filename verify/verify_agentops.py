"""Sprint-8 A-UC 用例断言（可复现）：验证 agent-ops CLI 实现遵循调研结论。

覆盖用例：UC-1 spec frontmatter 校验 / UC-2 source 块远程引用回退 / UC-3 账本状态机 /
UC-4 成本估算（价表 + chars/4 兜底 + pending_price）/ UC-5 报告输出模板解析 /
UC-7 防双写完整性校验 / UC-9 自报上下文与成本覆盖 / UC-10 价表派生 /
UC-11 fetch-spec sha256 命中/失配（M10）/ UC-12 账本并发锁无丢失更新（M10）/
UC-13 fetch-prices 解析与合并优先级（M9）/ UC-14 评审类 run 的 scope 来源闸门（TG-11）/
UC-19（TG-8②）离线开关：开关开启 → 三个外呼入口（fetch-spec / fetch-prices / provider 刷新）
在**发请求之前**拒绝并点名（rc=政策退出码）；开关关闭 → 不误拒；取值拼错 → fail-closed；
env 优先于政策 `enabled`；HF 离线变量按开关注入；脚本侧(verify/)与后端侧(app/)结论一致。

运行：.venv\\Scripts\\python.exe verify\\verify_agentops.py（纯离线，隔离到临时 AGENT_OPS_DIR）

**F1（2026-09-25）本脚本不再往仓库里写任何文件**：UC-15/UC-16 要用"临时新增一个角色 spec"来
证明闸门是数据驱动的，旧实现把探针直接写进**真实** `agents/functions/` 并靠 `finally` 删除——
后果有两个，都实测过：① 两个并行实例互相 clobber（一方删掉另一方正在用的探针 → 两边都 rc=1，
套件因此偶发红，正是 `TG-8` 记的"失败脚本在 verify_agentops 与 verify_local_dir 之间漂移"）；
② 每次运行都往工作区写文件，`git status` 不再干净（测试污染仓库）。
现改为：把 spec 目录**整体重定向到 %TEMP%**——复制真实 spec 到临时目录，写一份只改
`spec_dir` 字段（其余键逐字相同）的临时政策 JSON，用 `PAPERQA_AGENT_POLICY` 注入子进程。
探针只落在临时目录，且本文件断言仓库路径**从未**被创建。
"""

from __future__ import annotations
VERIFY_META = {'features': 'AgentOps 账本 CLI 用例断言 UC-1~UC-19（离线；UC-11/12=M10，UC-13=M9，UC-14=TG-11 scope 来源闸门，UC-15/16 探针 spec 隔离到 %TEMP% 不污染仓库，UC-19=TG-8 离线开关：三入口拒绝+反向对照+配置面+两侧一致）', 'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 20, 'routes': [], 'requires': ['none']}

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts" / "agent-ops.py"
FUNCTIONS = ROOT / "agents" / "functions"

# F1：探针 spec 的文件名（旧实现在**仓库** `agents/functions/` 下创建它们）。集中在此，
# 便于"启动即清理历史遗留 + 收尾断言从未创建"两处共用同一份字面量。
PROBE_SPECS = ("tg15-probe-role.md", "tg15-undeclared-role.md")

sys.path.insert(0, str(ROOT))

from verify.agent_policy import ENV_POLICY, Attribution, load_policy  # noqa: E402

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


def _window_problems(run: dict) -> list[str]:
    """对**单个账本行**跑一遍关闭闸门的窗口结构判据
    （B2 的反向对照用真实判据，不另写一份）。

    为什么复用而不是重写：`[C3-窗口] 不是完整 40 位 sha` 这条判据的语义只在
    `Attribution.window_problems()` 里；测试若自己写一遍"长度不等于 40"，就变成
    "验得过的口径"与"闸门判的口径"两套——正是 TG-15 要消灭的形态。
    这里用最小 `Attribution`（order 只含 run 自己的两个端点）驱动同一条方法。
    """
    from verify.agent_policy import CoverageWindow, order_index

    windows = []
    for key in ("coverage_anchor", "covers_through"):
        value = str(run.get(key) or "").strip()
        if value:
            windows.append(CoverageWindow(run_id=str(run.get("run_id") or "?"),
                                          role=str(run.get("role") or ""),
                                          anchor=value, through=value, from_run=True))
    order = order_index([w.anchor for w in windows] + [w.through for w in windows])
    att = Attribution(anchor=windows[0].anchor if windows else "", head="",
                      shas=[], order=order, windows=windows, exceptions=[],
                      root=None, policy=_POLICY)
    return [p for p in att.window_problems() if "不是完整 40 位" in p]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="verify_agentops_"))
    # ---- F1：spec 目录整体重定向到 %TEMP%（本脚本从此不往仓库写文件） -------------------
    # 旧实现：UC-15/UC-16 直接把探针 spec 写在 `agents/functions/`（真实仓库目录），靠 `finally` 删。
    # 实测后果：① 两个并行实例共享同一个可变文件 → 互相 clobber（两边都 rc=1）；
    # ② 运行期间工作区被污染（`git status` 非空）。修法不是"换个文件名"，而是**换掉 spec 根**：
    # 政策装载的 spec_dir 由 `agents/policy.json::spec_dir` 决定，而政策文件本身可用
    # `PAPERQA_AGENT_POLICY` 重定向（TG-15 的既有能力）。故：
    #   ① 复制真实 spec 到 %TEMP%（角色集合必须与真实仓库一致，否则 UC-3/4/9/14 会找不到角色）；
    #   ② 写一份临时政策 JSON：**只改 spec_dir**，其余键逐字取自真实政策（`_POLICY.policy_file`）；
    #   ③ 把 `PAPERQA_AGENT_POLICY` 注入每个 CLI 子进程。
    specs_dir = tmp / "specs"
    specs_dir.mkdir()
    for src in sorted(FUNCTIONS.glob("*.md")):
        shutil.copy2(src, specs_dir / src.name)
    temp_policy = tmp / "policy.json"
    temp_policy.write_text(
        json.dumps({**_POLICY.policy_file, "spec_dir": specs_dir.as_posix()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # 历史遗留（旧版本跑挂/被中断时留下）：仓库里若还有探针文件，先清掉——它不该存在。
    for name in PROBE_SPECS:
        (FUNCTIONS / name).unlink(missing_ok=True)
    base_env = {**os.environ, "AGENT_OPS_DIR": str(tmp), "PYTHONUTF8": "1",
                ENV_POLICY: str(temp_policy)}
    runtime = tmp / "runtime"
    registry = runtime / "registry.json"
    try:
        # 探针隔离的**前置断言**：政策确实指向临时 spec 目录（否则下面的 UC-15/16 会退回写仓库，
        # 而且失败形态是"静默写进真实目录"——正是本修复要消灭的东西）。
        ok("F1 政策已重定向：spec_dir 指向 %TEMP%，且与真实政策只差 spec_dir 一个键",
           _POLICY.policy_file.get("spec_dir") != (specs_dir.as_posix())
           and {k: v for k, v in json.loads(temp_policy.read_text(encoding="utf-8")).items()
                if k != "spec_dir"} == {k: v for k, v in _POLICY.policy_file.items() if k != "spec_dir"}
           and Path(tempfile.gettempdir()).resolve() in specs_dir.resolve().parents,
           f"specs_dir={specs_dir}（真实 spec_dir={_POLICY.policy_file.get('spec_dir')!r}）")
        ok("F1 spec 副本齐全（临时目录 == 真实 agents/functions 的角色集）",
           {p.name for p in specs_dir.glob("*.md")} == {p.name for p in FUNCTIONS.glob("*.md")}
           and bool(specs_dir.glob("*.md")),
           f"{len(list(specs_dir.glob('*.md')))} 份")

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
        # 不是代码常量。反向对照：在 spec 目录里临时新增一个声明 `scope_required: true` 的角色，
        # **不改任何代码**，CLI 必须立刻要求它声明 scope；把声明改成 false 后必须立刻放行。
        # 这同时证明"删声明绕不过去"（缺声明是报错，不是放行，见数据源完备性自检）。
        # **F1：探针写在 `specs_dir`（%TEMP%）而不是仓库 `agents/functions/`**——见文件头与 main() 开头。
        extra_spec = specs_dir / PROBE_SPECS[0]
        try:
            extra_spec.write_text(
                '---\nname: tg15-probe-role\ndescription: TG-15 数据驱动探针角色\n'
                'version: "1.0.0"\nscope_required: true\ncoverage_window: self\n---\n\n# probe\n',
                encoding="utf-8")
            ok("F1 UC-15 探针落在 %TEMP%（仓库 agents/functions/ 绝不出现探针文件）",
               extra_spec.is_file() and not (FUNCTIONS / PROBE_SPECS[0]).exists()
               and Path(tempfile.gettempdir()).resolve() in extra_spec.resolve().parents,
               f"probe={extra_spec}；仓库路径存在={ (FUNCTIONS / PROBE_SPECS[0]).exists() }")
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
        # **F1：同样写在 `specs_dir`（%TEMP%）**——旧实现把它写进仓库，是并行的第二个 clobber 源。
        probe_spec = specs_dir / PROBE_SPECS[1]
        try:
            probe_spec.write_text(
                '---\nname: tg15-undeclared-role\ndescription: 缺 scope_required 声明\n'
                'version: "1.0.0"\n---\n\n# probe\n', encoding="utf-8")
            ok("F1 UC-16 探针落在 %TEMP%（仓库路径未被创建）",
               probe_spec.is_file() and not (FUNCTIONS / PROBE_SPECS[1]).exists(),
               f"probe={probe_spec}")
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
        # 行为变更（B2，2026-09-25）：这一条**本来就是同值**（`register` 已把 head_short
        # 规范化成 head_full），故现在正确地判为"无变化"——旧实现会追加一条**假留痕**，
        # 下面 UC-17b 逐条断言新语义。这里先立一条真实存在的回填（换成一个不同的端点），
        # 再验证"成功 + 留痕"这条判据本身仍然成立。
        ok("UC-17 同值 --anchor 回填 = 无变化、不留痕（B2 起不再产生假留痕）",
           r.returncode == 0 and "无变化" in (r.stdout + r.stderr)
           and not (e17b.get("anchor_backfills") or []),
           f"rc={r.returncode} backfills={len(e17b.get('anchor_backfills') or [])}")
        prev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD~1"],
                              capture_output=True, text=True,
                              encoding="utf-8").stdout.strip()
        r = run(["set-anchor", "run-uc17-short", "--anchor", prev,
                 "--reason", "UC-17：verify 受控回填成功路径（改成一个不同的端点）"],
                base_env, raw=True)
        e17b = next(x for x in json.loads(registry.read_text(encoding="utf-8"))["runs"]
                    if x["run_id"] == "run-uc17-short")
        ok("UC-17 受控回填成功且留痕（anchor_backfills，记明 field）",
           r.returncode == 0 and e17b.get("coverage_anchor") == prev
           and len(e17b.get("anchor_backfills") or []) == 1
           and e17b["anchor_backfills"][0].get("field") == "coverage_anchor",
           f"backfills={len(e17b.get('anchor_backfills') or [])}")

        # UC-17b（B2）：**空操作不得假装回填过**。同值重复回填时，旧实现照样追加一条
        # `anchor_backfills`，于是"谁在什么时候动过这个窗口"的留痕里会混进
        # **没动过**的记录（假留痕比无留痕更坏：审计据此以为窗口被改过）。
        # 现改为：值无变化 → 不改库、不追加留痕、显式报"无变化"
        # （上面的 UC-17 已实测这一条）。
        def _backfills() -> list[dict]:
            data = json.loads(registry.read_text(encoding="utf-8"))
            row = next(x for x in data["runs"]
                       if x["run_id"] == "run-uc17-short")
            return row.get("anchor_backfills") or []

        n_before = len(_backfills())
        r = run(["set-anchor", "run-uc17-short", "--anchor", prev,
                 "--reason", "UC-17b：同值重复回填必须是无操作（不得追加假留痕）"],
                base_env, raw=True)
        n_after = len(_backfills())
        ok("UC-17b 同值回填 = 无操作：rc=0、显式报「无变化」、"
           "**不**追加 anchor_backfills",
           r.returncode == 0 and "无变化" in (r.stdout + r.stderr)
           and n_after == n_before,
           f"rc={r.returncode} backfills {n_before}->{n_after}")

        # UC-17c（B2）：`--covers-through` 与 `--anchor` 必须**同构**受理同一族缺陷
        # （短 sha 让 `CoverageWindow.covers()` 恒 False ⇒ 窗口被静默丢弃）。此前只有
        # `--anchor` 有回填口，`covers_through` 短 sha 报的问题**不可修** = 永久红。
        r = run(["set-anchor", "run-uc17-short",
                 "--reason", "UC-17c：两个端点都不给"], base_env, raw=True)
        ok("UC-17c 两个端点都不给 → 拒绝（否则是「什么都没做但报成功」）",
           r.returncode != 0 and "至少要给" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:70])
        r = run(["set-anchor", "run-uc17-short",
                 "--covers-through", "deadbeefdeadbeef",
                 "--reason", "UC-17c：无法解析的 covers_through 必须 fail-closed"],
                base_env, raw=True)
        ok("UC-17c 无法解析的 --covers-through → 拒绝"
           "（COVERAGE-ANCHOR-ERROR，不静默存坏值）",
           r.returncode != 0 and "COVERAGE-ANCHOR-ERROR" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:70])
        r = run(["set-anchor", "run-uc17-short",
                 "--covers-through", head_short, "--reason", "太短"],
                base_env, raw=True)
        ok("UC-17c --covers-through 回填缺理由（<10 字符）→ 拒绝",
           r.returncode != 0 and "理由" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:70])
        r = run(["set-anchor", "run-uc17-short",
                 "--covers-through", head_short,
                 "--reason", "B2：短 sha 的 covers_through 会让窗口被静默丢弃，"
                             "回填为完整 sha"],
                base_env, raw=True)
        e17d = next(x for x in json.loads(registry.read_text(encoding="utf-8"))["runs"]
                    if x["run_id"] == "run-uc17-short")
        recs = e17d.get("anchor_backfills") or []
        ok("UC-17c 短 sha 的 --covers-through 被规范化为完整 40 位并留痕（记明 field）",
           r.returncode == 0 and e17d.get("covers_through") == head_full
           and bool(recs) and recs[-1].get("field") == "covers_through"
           and recs[-1].get("to") == head_full,
           f"covers_through={str(e17d.get('covers_through'))[:12]}… "
           f"field={recs[-1].get('field') if recs else None}")
        ok("UC-17c 回填后该窗口不再被判「不是完整 40 位 sha」（闸门与账本同口径）",
           not [p for p in _window_problems(e17d) if "不是完整 40 位" in p],
           f"problems={_window_problems(e17d)}")

        # UC-18（审核 N10）：`finish --result-file` **不得改写报告换行**（LF → CRLF 静默改写）
        # 原实现 `dest.write_text(rel.read_text(encoding="utf-8"), encoding="utf-8")`：读侧做
        # universal-newline 转换、写侧把 `\n` 落成 `os.linesep`（Windows=CRLF）→ 仓库基线的 LF
        # 报告被静默改成 CRLF（实测 35721 B → 35913 B / 192 行）。归档步骤最不该动产物字节。
        for tag, eol in (("lf", "\n"), ("crlf", "\r\n")):
            rid = f"run-uc18-{tag}"
            run(["register", "--role", "impact-assessment", "--task", f"eol-{tag}", "--spec",
                 "impact-assessment@1.4.4", "--run-id", rid], base_env, check=True)
            run(["update", rid, "--status", "running"], base_env, check=True)
            report = tmp / f"uc18-{tag}.report.md"
            report.write_bytes("".join(f"| 行 {i} | {tag} 报告正文 |{eol}" for i in range(120))
                               .encode("utf-8"))
            run(["finish", rid, "--status", "succeeded", "--result-file", str(report)],
                base_env, check=True)
            dest = tmp / "runs" / rid / "impact-assessment.report.md"
            src_bytes, dst_bytes = report.read_bytes(), dest.read_bytes()
            if tag == "lf":
                ok("UC-18 LF 报告经 finish --result-file 后 CRLF 计数为 0（LF 不被静默改写）",
                   dst_bytes.count(b"\r\n") == 0, f"CRLF={dst_bytes.count(b'\r\n')} 行")
                ok("UC-18 LF 报告字节数不变（内容逐字节一致）", dst_bytes == src_bytes,
                   f"{len(src_bytes)} B → {len(dst_bytes)} B")
            else:
                ok("UC-18 CRLF 报告仍保持 CRLF（不反向破坏：源是 CRLF 就存 CRLF）",
                   dst_bytes.count(b"\r\n") == 120 and dst_bytes == src_bytes,
                   f"CRLF={dst_bytes.count(b'\r\n')} 行，{len(src_bytes)} B → {len(dst_bytes)} B")

        # A5（审核 M-g）：账本 run_id ↔ `agents/runs/*` 目录名一致性
        # 背景：`register` 自动 run-id 用 UTC 日期、目录/文档用 UTC+8 → 实测
        # `run-2026-09-24-doc-audit-066`（账本）↔ `run-2026-09-25-doc-audit-066`（目录）。
        # 历史例外写在数据文件（agents/policy/run-dir-exceptions.json）并**必须注明理由**。
        real_ledger = json.loads((ROOT / "agents" / "runtime" / "registry.json")
                                 .read_text(encoding="utf-8"))
        ledger_ids = {str(r.get("run_id") or "") for r in real_ledger.get("runs", [])}
        exc_file = ROOT / "agents" / "policy" / "run-dir-exceptions.json"
        exc = json.loads(exc_file.read_text(encoding="utf-8")) if exc_file.is_file() else {}
        exc_items = exc.get("exceptions") or []
        no_reason = [str(e.get("dir")) for e in exc_items if not str(e.get("reason") or "").strip()]
        ok("M-g 例外白名单每一条都写了理由（白名单不是静音开关）", not no_reason,
           f"缺理由：{no_reason[:3]}")
        exc_dirs = {str(e.get("dir")) for e in exc_items}
        real_dirs = {p.name for p in (ROOT / "agents" / "runs").iterdir() if p.is_dir()}
        orphan_dirs = sorted(real_dirs - ledger_ids - exc_dirs)
        ok("M-g 账本 id ↔ 目录名一致：agents/runs/* 目录名都能在账本里找到同名 run（例外已在数据文件登记）",
           not orphan_dirs, f"对不上账本且无例外登记的目录：{orphan_dirs[:5]}")
        stale_exc = sorted(exc_dirs & ledger_ids)
        ok("M-g 例外白名单只减不增：登记过的例外若已在账本里有同名 run → 必须删除该例外",
           not stale_exc, f"已不再需要的例外：{stale_exc[:5]}")

        # UC-19（TG-8②）：**离线开关**——一个开关关掉全部外呼，且在**发起请求之前**拒绝并点名。
        # 判据（卡文）：开关开启 → 每个被禁止的外呼入口 rc≠0 且点名原因（不是靠网络超时）；
        #              开关关闭 → 允许（或按设计）。
        # 反向对照（§6"倒过来试试"）：以下每条的对照分支都断言"**没有**出现 OFFLINE-REFUSED"，
        # 即不能只证明"开关开着会拒绝"，还要证明"关着不会无故拒绝"（否则闸门可能是恒拒绝）。
        offline_mod = importlib.util.spec_from_file_location(
            "offline_guard", ROOT / "verify" / "outbound_guard.py")
        og = importlib.util.module_from_spec(offline_mod)
        assert offline_mod.loader is not None
        offline_mod.loader.exec_module(og)
        sw = _POLICY.offline_switch
        env_name = str(sw["env_var"])
        refuse_code = int(sw["refuse_exit_code"])

        ok("UC-19 开关政策完备：env 名 / 真值表 / 拒绝退出码 / 拒绝文案都来自政策数据",
           bool(env_name) and bool(sw.get("env_true_values")) and bool(sw.get("env_false_values"))
           and refuse_code > 0 and "{target}" in str(sw.get("refusal_reason") or ""),
           f"env={env_name} true={sw.get('env_true_values')} code={refuse_code}")

        stub = tmp / "uc19-remote-spec.md"
        stub.write_text(
            "---\nname: uc19-remote\ndescription: x\nversion: '1.0.0'\n"
            "source:\n  url: https://example.invalid/nope.md\n  ref: v1\n  sha256: abc\n---\nbody\n",
            encoding="utf-8")

        on_env = {**base_env, env_name: "1"}
        r_on = run(["fetch-spec", str(stub)], on_env)
        out_on = r_on.stdout + r_on.stderr
        ok("UC-19 开关开启 → fetch-spec 外呼被**拒绝**且点名（rc=政策退出码，非超时）",
           r_on.returncode == refuse_code and "OFFLINE-REFUSED" in out_on
           and env_name in out_on and "example.invalid" in out_on,
           f"rc={r_on.returncode}（期望 {refuse_code}）out={out_on.strip()[:110]}")

        fp = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "fetch-prices.py"), "--check"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=on_env, check=False)
        out_fp = fp.stdout + fp.stderr
        ok("UC-19 开关开启 → fetch-prices（价格刷新）拒绝全部来源并 rc=政策退出码",
           fp.returncode == refuse_code and out_fp.count("OFFLINE-REFUSED") >= 1
           and "api-docs.deepseek.com" in out_fp,
           f"rc={fp.returncode} out={out_fp.strip().splitlines()[:1]}")

        off_env = {**base_env, env_name: "0"}
        r_fp_off = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "fetch-prices.py"), "--check"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=off_env, check=False)
        out_fp_off = r_fp_off.stdout + r_fp_off.stderr
        ok("UC-19 反向对照：开关关闭 → 同一入口**不再**被开关拒绝（按设计继续尝试抓取）",
           "OFFLINE-REFUSED" not in out_fp_off and "[deepseek]" in out_fp_off,
           f"rc={r_fp_off.returncode} out={out_fp_off.strip().splitlines()[:1]}")

        r_spec_off = run(["fetch-spec", str(stub)], off_env)
        out_spec_off = r_spec_off.stdout + r_spec_off.stderr
        ok("UC-19 反向对照：开关关闭 → fetch-spec 走既有降级路径（不误报离线拒绝）",
           "OFFLINE-REFUSED" not in out_spec_off and ("回退本地" in out_spec_off or "WARN" in out_spec_off),
           f"rc={r_spec_off.returncode} out={out_spec_off.strip()[:110]}")

        r_bad = run(["fetch-spec", str(stub)], {**base_env, env_name: "flase"})
        out_bad = r_bad.stdout + r_bad.stderr
        ok("UC-19 开关取值拼错（flase）→ fail-closed 报错，**不静默当成关闭**",
           r_bad.returncode != 0 and "合法开关取值" in out_bad,
           f"rc={r_bad.returncode} out={out_bad.strip().splitlines()[-1][:110]}")

        # ②配置面：政策 `enabled=true`（env 未设）同样生效——证明"开关可配置"不只 env 一条路
        temp_policy_off = tmp / "policy-offline.json"
        temp_policy_off.write_text(json.dumps(
            {**_POLICY.policy_file,
             "offline_switch": {**_POLICY.policy_file["offline_switch"], "enabled": True}},
            ensure_ascii=False, indent=2), encoding="utf-8")
        r_pol = run(["fetch-spec", str(stub)], {**base_env, ENV_POLICY: str(temp_policy_off),
                                                env_name: "0"})
        out_pol = r_pol.stdout + r_pol.stderr
        ok("UC-19 env=0 覆盖政策 enabled=true → 放行（**优先级 env > 政策**，可核）",
           "OFFLINE-REFUSED" not in out_pol, f"rc={r_pol.returncode} out={out_pol.strip()[:80]}")
        # 未设 env 时：同一份政策（enabled=true）→ 拒绝，且来源点名政策键
        env_no_switch = {k: v for k, v in base_env.items() if k != env_name}
        r_pol2 = run(["fetch-spec", str(stub)], {**env_no_switch, ENV_POLICY: str(temp_policy_off)})
        out_pol2 = r_pol2.stdout + r_pol2.stderr
        ok("UC-19 配置面生效：未设 env 时政策 enabled=true → 拒绝且来源点名 `offline_switch.enabled`",
           r_pol2.returncode == refuse_code and "OFFLINE-REFUSED" in out_pol2
           and "offline_switch.enabled" in out_pol2,
           f"rc={r_pol2.returncode} out={out_pol2.strip().splitlines()[-1][:130]}")

        # ③HF 离线变量注入（TG-8 正文 ③）：开启时注入、关闭时不注入（不改变既有行为）
        probe_env = dict(base_env)
        probe_env.pop(env_name, None)
        hf_on = {k: v for k, v in (sw.get("hf_offline_env") or {}).items() if not str(k).startswith("_")}
        injected = og.apply_env(probe_env) if og.offline_enabled() else {}
        ok("UC-19 开关关闭时**不注入** HF 离线变量（既有行为不变）", injected == {}, f"injected={injected}")
        os.environ[env_name] = "1"
        try:
            injected_on = og.apply_env(dict(probe_env))
        finally:
            os.environ.pop(env_name, None)
        ok("UC-19 开关开启时注入政策声明的 HF 离线变量（消除 HEAD 重试阻塞）",
           injected_on == hf_on and bool(hf_on), f"injected={injected_on}（政策 {hf_on}）")

        # ④两侧实现一致（app/offline_guard.py 与 verify/outbound_guard.py）：同一 env 取值同结论
        app_guard_spec = importlib.util.spec_from_file_location(
            "app_offline_guard", ROOT / "paper-qa-script" / "app" / "offline_guard.py")
        ag = importlib.util.module_from_spec(app_guard_spec)
        assert app_guard_spec.loader is not None
        app_guard_spec.loader.exec_module(ag)
        os.environ[env_name] = "1"
        try:
            same = ag.switch_state()[0] is True and og.offline_enabled() is True
        finally:
            os.environ.pop(env_name, None)
        os.environ[env_name] = "0"
        try:
            same = same and ag.switch_state()[0] is False and og.offline_enabled() is False
        finally:
            os.environ.pop(env_name, None)
        ok("UC-19 运行时两侧（脚本侧 verify/ + 后端侧 app/）对同一开关给出一致结论", same,
           f"app={ag.switch_state()}")

        # UC-20（D0-3(a)/TG-17⑤）：**产出型 run 的逐条标注**——实现类工作补登记挂评审
        # role 时，
        # 其覆盖窗口恒为空区间，B3 会判"内容评审类空窗口 FAIL"。对产出型 run
        # 报这条是结构性假红，
        # 修法是把它"不承担内容覆盖"落成**账本数据**（不是放宽判据，也不是回填
        # covers_through 伪造覆盖）。
        # 断言覆盖：成功路径 + 留痕 + 四条拒绝路径 + 幂等（不留假痕）+ 撤回 +
        # 窗口判据随之翻转。
        head_full20 = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                     capture_output=True, text=True,
                                     encoding="utf-8").stdout.strip()
        run(["register", "--role", "code-review", "--task", "uc20-produced-only",
             "--spec", "code-review@1.2.2", "--run-id", "run-uc20-produced",
             "--coverage-anchor", head_full20,
             "--scope-source", "self-chosen", "--deviation", 
                 "实现类工作补登记（UC-20 fixture）"],
            base_env, check=True)
        run(["update", "run-uc20-produced", "--status", "running"], base_env, check=True
            )
        run(["finish", "run-uc20-produced", "--status", "succeeded",
             "--covers-through", head_full20], base_env, check=True)

        def _row20(rid: str = "run-uc20-produced") -> dict:
            data = json.loads(registry.read_text(encoding="utf-8"))
            return next(x for x in data["runs"] if x["run_id"] == rid)

        def _empty_window_problems(row: dict) -> list[str]:
            """复用**真实判据**（账本行 → 窗口 → `window_problems`），不另写判据。"""
            from verify.agent_policy import (Attribution, coverage_windows_from_runs,
                                             order_index)
            anchor = str(row.get("coverage_anchor") or "")
            att = Attribution(anchor=anchor, head="", shas=[],
                              order=order_index([anchor]),
                              windows=coverage_windows_from_runs([row]),
                              exceptions=[], root=None, policy=_POLICY)
            return [p for p in att.window_problems() if "空区间" in p]

        ok("UC-20 前置：未标注的内容评审 run 空窗口 → FAIL（这是标注要消掉的判据）",
           bool(_empty_window_problems(_row20())),
           f"problems={_empty_window_problems(_row20())[:1]}")

        reason20 = ("TG-13 类实现工作：口径定义 + 闸门 + 反向对照，"
                    "补登记挂 code-review role，非内容评审")
        r = run(["mark-produced", "run-uc20-produced", "--reason", reason20],
                base_env, raw=True)
        row20 = _row20()
        marks20 = row20.get("produced_only_marks") or []
        ok("UC-20 标注成功：账本写入 produced_only=True + 理由 + 留痕数组（逐条列名）",
           r.returncode == 0 and row20.get("produced_only") is True
           and row20.get("produced_only_reason") == reason20
           and len(marks20) == 1 and marks20[0].get("action") == "mark"
           and marks20[0].get("reason") == reason20 and str(marks20[0].get("by") or ""),
           f"rc={r.returncode} marks={len(marks20)}")
        ok("UC-20 正向对照：标注后该 run 的空窗口**不再判问题**（判据随账本数据翻转）",
           _empty_window_problems(_row20()) == [],
           f"problems={_empty_window_problems(_row20())}")
        r = run(["list", "--role", "code-review"], base_env, raw=True)
        ok("UC-20 可见性：`list` 对该 run 打出 `produced(!)`（豁免不得静默生效）",
           "produced(!)" in (r.stdout + r.stderr),
           f"out={r.stdout.strip().splitlines()[-2][-60:]}")

        r = run(["mark-produced", "run-uc20-produced", "--reason", "太短"],
                base_env, raw=True)
        ok("UC-20 反向对照：缺/过短 `--reason` → 拒绝（标注必须带可核理由）",
           r.returncode != 0 and "理由" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:70])
        r = run(["mark-produced", "run-does-not-exist", "--reason", reason20],
                base_env, raw=True)
        ok("UC-20 反向对照：不存在的 run → 拒绝（不得凭空造一条标注）",
           r.returncode != 0, (r.stdout + r.stderr).strip()[:70])
        run(["register", "--role", "impact-assessment", "--task", "uc20-nonreview",
             "--spec", "impact-assessment@1.4.4", "--run-id", "run-uc20-nonreview",
             "--coverage-anchor", head_full20], base_env, check=True)
        run(["update", "run-uc20-nonreview", "--status", "running"], base_env, check=
            True)
        run(["finish", "run-uc20-nonreview", "--status", "succeeded",
             "--covers-through", head_full20], base_env, check=True)
        r = run(["mark-produced", "run-uc20-nonreview", "--reason", reason20],
                base_env, raw=True)
        ok("UC-20 反向对照：非评审类 role → 拒绝（语义是「评审 role 但不做内容评审」）",
           r.returncode != 0 and "COVERAGE-PRODUCED-ERROR" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:80])
        prev20 = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD~1"],
                                capture_output=True, text=True,
                                encoding="utf-8").stdout.strip()
        run(["register", "--role", "code-review", "--task", "uc20-nonempty",
             "--spec", "code-review@1.2.2", "--run-id", "run-uc20-nonempty",
             "--coverage-anchor", prev20, "--scope-source", "self-chosen",
             "--deviation", "窗口非空（UC-20 fixture）"], base_env, check=True)
        run(["update", "run-uc20-nonempty", "--status", "running"], base_env, check=True
            )
        run(["finish", "run-uc20-nonempty", "--status", "succeeded",
             "--covers-through", head_full20], base_env, check=True)
        r = run(["mark-produced", "run-uc20-nonempty", "--reason", reason20],
                base_env, raw=True)
        ok("UC-20 反向对照：窗口**非空**的 run → 拒绝（标注与账本事实矛盾）",
           r.returncode != 0 and "空区间" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:80])

        n_before20 = len(_row20().get("produced_only_marks") or [])
        r = run(["mark-produced", "run-uc20-produced",
                 "--reason", "UC-20：重复标注应无操作（同值不得追加假留痕）"],
                base_env, raw=True)
        n_after20 = len(_row20().get("produced_only_marks") or [])
        ok("UC-20 幂等/防假痕：重复标注 = 无操作（rc=0、报「无变化」、**不**追加留痕）",
           r.returncode == 0 and "无变化" in (r.stdout + r.stderr)
           and n_after20 == n_before20,
           f"rc={r.returncode} marks {n_before20}->{n_after20}")

        r = run(["mark-produced", "run-uc20-produced", "--undo",
                 "--reason", "UC-20：撤回标注后判据必须恢复（不可撤回的写入是坑）"],
                base_env, raw=True)
        row20b = _row20()
        ok("UC-20 撤回（--undo）：produced_only 复位、留痕保留、空窗口判据**重新 FAIL**"
            ,
           r.returncode == 0 and row20b.get("produced_only") is False
           and (row20b.get("produced_only_marks") or [])[-1].get("action") == "unmark"
           and str(row20b.get("produced_only_reason") or "") == ""
           and bool(_empty_window_problems(row20b)),
           f"rc={r.returncode} marks={len(row20b.get('produced_only_marks') or [])} "
           f"problems={_empty_window_problems(row20b)[:1]}")

        # UC-7：手改 registry → CLI 下一次写入拒绝
        data = json.loads(registry.read_text(encoding="utf-8"))
        data["runs"][0]["output_chars"] = 999999  # 手改
        registry.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        r = run(["register", "--role", "code-review", "--task", "x", "--spec", "code-review@1.0.0"], base_env)
        ok("UC-7 防双写", r.returncode != 0 and "完整性校验" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:80])

        # F1 收尾断言：整轮跑完，仓库的 spec 目录**一个探针文件都没有**（且内容与运行前逐字节相同）。
        # 判据取"文件系统事实"，不是"我记得 unlink 过"——旧实现正是靠这句记忆，而它在并行下不成立。
        repo_probes = [name for name in PROBE_SPECS if (FUNCTIONS / name).exists()]
        ok("F1 全程零仓库污染：agents/functions/ 下没有任何探针 spec（并行安全的前提）",
           not repo_probes, f"残留={repo_probes}")
        ok("F1 真实 spec 未被改动（临时目录只读复制）",
           {p.name: p.read_bytes() for p in specs_dir.glob("*.md")}
           == {p.name: p.read_bytes() for p in FUNCTIONS.glob("*.md")},
           f"{len(list(FUNCTIONS.glob('*.md')))} 份逐字节一致")

        print(f"\nALL PASS ({PASSED} assertions)")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
