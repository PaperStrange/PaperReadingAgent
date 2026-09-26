"""Sprint-8 A-UC 用例断言（可复现）：验证 agent-ops CLI 实现遵循调研结论。

覆盖用例：UC-1 spec frontmatter 校验 / UC-2 source 块远程引用回退 / UC-3 账本状态机 /
UC-4 成本估算（价表 + chars/4 兜底 + pending_price）/ UC-5 报告输出模板解析 /
UC-7 防双写完整性校验 / UC-9 自报上下文与成本覆盖 / UC-10 价表派生 /
UC-11 fetch-spec sha256 命中/失配（M10）/ UC-12 账本并发锁无丢失更新（M10）/
UC-13 fetch-prices 解析与合并优先级（M9）/ UC-14 评审类 run 的 scope 来源闸门（TG-11）/
UC-19（TG-8②）离线开关：
开关开启 → 三个外呼入口（fetch-spec / fetch-prices / provider 刷新）
在**发请求之前**拒绝并点名（rc=政策退出码）；开关关闭 → 不误拒；取值拼错 → fail-closed；
env 优先于政策 `enabled`；HF 离线变量按开关注入；脚本侧(verify/)与后端侧(app/)结论一致。

运行：.venv\\Scripts\\python.exe verify\\verify_agentops.py（纯离线，隔离到临时 AGENT_OPS_DIR）

**F1（2026-09-25）本脚本不再往仓库里写任何文件**：UC-15/UC-16 要用"临时新增一个角色 spec"来
证明闸门是数据驱动的，旧实现把探针直接写进**真实**
`agents/functions/` 并靠 `finally` 删除——
后果有两个，都实测过：① 两个并行实例互相
clobber（一方删掉另一方正在用的探针 → 两边都 rc=1，
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
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts" / "agent-ops.py"
FUNCTIONS = ROOT / "agents" / "functions"

# F1：探针 spec 的文件名（旧实现在**仓库** `agents/functions/` 下创建它们）。集中在此，
# 便于"启动即清理历史遗留 + 收尾断言从未创建"两处共用同一份字面量。
PROBE_SPECS = ("tg15-probe-role.md", "tg15-undeclared-role.md")

# R-001（G3）：`finish` 的写入口 fail-closed 落库后，**同秒收尾**的夹具会被
# （正确地）拒绝（`_now()` 秒级截断 ⇒ `started_at == ended_at` ⇒ `zero_duration`）。
# 本文件的合成夹具断的是**别的**判据（流转/价表/字节/EOL/窗口/留痕），
# 时长对它们**本无意义** ⇒ 逐条显式传下面这组参数，即"显式记账为非测量"，
# **不是**为了让夹具变绿而放宽守卫：守卫的拒绝路径由 UC-24 三条反向对照真跑。
DEGEN_FIXTURE_REASON = "fixture: 同秒收尾，非真实测量（R-001）"
DEGEN_FIXTURE_ARGS = ("--allow-degenerate", "--degenerate-reason", DEGEN_FIXTURE_REASON)

# UC-20（行 16）选档夹具用的**固定时刻**（UTC 写法；UTC+8 = Asia/Shanghai）；
# 2026-09-28 是周一：
#   OFF  = 00:30Z→00:35Z = 08:30→08:35 CST → 高峰前（空闲）；
#   PEAK = 02:00Z→02:05Z = 10:00→10:05 CST → 上午高峰窗口内；
#   SPAN = 03:00Z→05:00Z = 11:00→13:00 CST → 前 1h 高峰 + 后 1h 空闲（§3.3 跨档）。
# 固定值而不是 `now()`：判据必须**可复跑**（用当前时刻的闸门会在白天自己变红）。
_SH = timezone(timedelta(hours=8))
ISO_OFF_PEAK = "2026-09-28T00:30:00+00:00"
ISO_OFF_END = "2026-09-28T00:35:00+00:00"
ISO_PEAK = "2026-09-28T02:00:00+00:00"
ISO_PEAK_END = "2026-09-28T02:05:00+00:00"
ISO_SPAN_START = "2026-09-28T03:00:00+00:00"
ISO_SPAN_END = "2026-09-28T05:00:00+00:00"

sys.path.insert(0, str(ROOT))

from verify.agent_policy import ENV_POLICY, Attribution, load_policy  # noqa: E402

# TG-15：角色集合**不再在本文件复制一份**（原先这里写死 {"code-review","doc-audit"}，与
# agent-ops.py 的 `_REVIEW_ROLES`、verify_close_readiness.py 的 `CLOSE_ROLES` 三处并存 →
# 加角色要改三处）。现在统一从政策数据读：spec frontmatter 的 `scope_required`。
_POLICY = load_policy()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0

# 台账 E1 / 行 7：归一化是**生产逻辑**，本文件是写入侧的真入口测试
# （`register --sprint` / `set-sprint`）。一致性向量表在 spec（唯一权威），
# 与读取侧 `verify_close_readiness.py` 解析**同一张表**——两侧不共用实现、
# 只共用输入与期望值，这样"判据不导入被测实现"与"两侧同输入同输出"同时成立。
SPRINT_VECTOR_SPEC = ROOT / ("docs/iteration/phases/testing-governance/"
                             "2026-09-26-sprint-id-normalization-spec.MD")


def _vec_value(cell: str) -> object:
    """向量表哨兵 → Python 值：`(null)` → None、`(empty)` → 空串。"""
    if cell == "(null)":
        return None
    return "" if cell == "(empty)" else cell


def _spec_vector(section: str) -> list[tuple[str, object, object]]:
    """从 spec 解析 `(id, 输入, 期望值)`；列位由**表头行**定位。

    读不到 → 抛（调用方判 FAIL）：判据未被触发时**不得**当通过。
    """
    lines = SPRINT_VECTOR_SPEC.read_text(encoding="utf-8").splitlines()
    hits = [i for i, line in enumerate(lines) if section in line]
    if not hits:
        raise AssertionError(f"向量表缺该节：{section}")
    rows: list[list[str]] = []
    for line in lines[hits[0] + 1:]:
        line = line.strip()
        if not line.startswith("|"):
            if rows:
                break
            continue
        if line.endswith("|"):
            rows.append([c.strip() for c in line[1:-1].split("|")])
    head = [c.strip("`") for c in rows[0]]
    i_id, i_in, i_want = (head.index(k) for k in ("id", "输入", "期望值"))
    return [(c[i_id].strip("`"), _vec_value(c[i_in].strip("`")),
             _vec_value(c[i_want].strip("`")))
            for c in rows[1:] if set("".join(c)) - set("-: ")]


def run(args: list[str], env: dict, check: bool = False, raw: bool = False) -> subprocess.CompletedProcess:
    """跑一次 CLI。

    TG-11 闸门生效后，评审类 `register` 必须声明 scope 来源；
    合成 fixture 不涉及真实评审范围，
    因此默认自动补 `--scope-source self-chosen --deviation <fixture 说明>`。
    **反向对照/负向用例必须用 `raw=True`**（否则闸门被 helper 掩盖，断言恒真）。
    评审类集合来自 `agents/functions/*.md` 的 `scope_required`（TG-15：
    不再在本文件写死角色名）。
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


def price_shape_problems(frozen: dict, real: dict) -> list[str]:
    """冻结副本解析结果 ↔ 真实价表模型的**形状契约**（纯函数，反向对照直接驱动）。

    判据只有三条，都是"改了一边没改另一边"**必然**踩到的：
      * 模型集（名字＋个数）——页面换模型/改列数时两侧立刻分叉；
      * 每模型的两档键都在（`_tiers.peak` / `_tiers.off_peak`）——掉档位即分叉；
      * 两档的四键**键集**相同。
    值只比一条**本仓不变量**：扁平键 == `_tiers.peak`（镜像高峰）。
    官方单价本身不比——它随调价变，比它等于把闸门变成"价格没变"的哨兵。

    别名条目（真实价表里的 `_alias_of`，如 `deepseek-v4-flash`）**不参与**：
    页面不会列出别名，把它们算进"模型集"就是把本仓的别名约定当成官方形状。
    """
    problems: list[str] = []
    real = {k: v for k, v in real.items()
            if not (isinstance(v, dict) and v.get("_alias_of"))}
    if set(frozen) != set(real):
        problems.append(f"模型集不同：副本={sorted(frozen)} 真实={sorted(real)}")
    for name in sorted(set(frozen) & set(real)):
        tiers, ftiers = real[name].get("_tiers"), frozen[name].get("_tiers")
        if not isinstance(tiers, dict) or not isinstance(ftiers, dict):
            got = f"副本={type(ftiers).__name__} 真实={type(tiers).__name__}"
            problems.append(f"{name}: 缺 _tiers（{got}）")
            continue
        if set(tiers) != set(ftiers):
            problems.append(f"{name}: 档位键不同 副本={sorted(ftiers)}"
                            f" 真实={sorted(tiers)}")
            continue
        for tier in sorted(tiers):
            if set(tiers[tier]) != set(ftiers[tier]):
                problems.append(f"{name}.{tier}: 四键集不同 副本={sorted(ftiers[tier])}"
                                f" 真实={sorted(tiers[tier])}")
        cost_keys = ("input_cost_per_token", "output_cost_per_token",
                     "cache_read_input_token_cost", "cache_creation_input_token_cost")
        flat = {k: real[name].get(k) for k in cost_keys}
        if any(v is not None for v in flat.values()) and flat != tiers.get("peak"):
            problems.append(f"{name}: 扁平键未镜像 _tiers.peak（本仓不变量）")
    return problems


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
    # ---- F1：spec 目录整体重定向到 %TEMP%（本脚本从此不往仓库写文件）
    # -------------------
    # 旧实现：UC-15/UC-16 直接把探针 spec 写在 `agents/functions/`（真实仓库目录），
    # 靠 `finally` 删。
    # 实测后果：① 两个并行实例共享同一个可变文件 → 互相 clobber（两边都 rc=1）；
    # ② 运行期间工作区被污染（`git status` 非空）。修法不是"换个文件名"，
    # 而是**换掉 spec 根**：
    # 政策装载的 spec_dir 由 `agents/policy.json::spec_dir` 决定，而政策文件本身可用
    # `PAPERQA_AGENT_POLICY` 重定向（TG-15 的既有能力）。故：
    # ① 复制真实 spec 到 %TEMP%（角色集合必须与真实仓库一致，
    # 否则 UC-3/4/9/14 会找不到角色）；
    # ② 写一份临时政策 JSON：**只改 spec_dir**，
    # 其余键逐字取自真实政策（`_POLICY.policy_file`）；
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
        # 探针隔离的**前置断言**：
        # 政策确实指向临时 spec 目录（否则下面的 UC-15/16 会退回写仓库，
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
        # R-001 夹具①（非测量）：UC-3 断的是"queued→running→终态"的**流转**与
        # output_chars；本 run 的 update/finish 落在同一秒 ⇒ 时长本无意义。
        run(["finish", run_id, "--status", "succeeded", "--output-chars", "2000",
             *DEGEN_FIXTURE_ARGS], base_env, check=True)
        # R-001：本条**不传** flag——它断的是"终态再 finish 被状态机拒"，
        # 在守卫之前就退出（断言的是 `非法流转`，不是退化文案）。
        r = run(["finish", run_id, "--status", "failed"], base_env)
        ok("UC-3 终态再 finish 拒绝", r.returncode != 0 and "非法流转" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:60])
        r = run(["update", run_id, "--status", "running"], base_env)
        ok("UC-3 终态再 running 拒绝", r.returncode != 0 and "非法流转" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:60])

        # UC-4：usage×价表精确值（gpt-4o-mini: in=1.5e-7, out=6e-7；
        # USD 0.00135 × fx 7.2 = CNY 0.00972）
        run(["register", "--role", "code-review", "--task", "branch:main", "--spec", "code-review@1.0.0",
             "--model", "gpt-4o-mini", "--start"], base_env, check=True)
        data = json.loads(registry.read_text(encoding="utf-8"))
        run2 = data["runs"][1]["run_id"]
        # R-001 夹具②（非测量）：UC-4 断的是**价表算术**（usage × 单价 × fx），
        # 本 run 是 `register --start` 后同秒收尾 ⇒ 时长不是被测对象。
        run(["finish", run2, "--status", "succeeded", "--usage-in", "1000", "--usage-out", "2000",
             "--output-chars", "100", *DEGEN_FIXTURE_ARGS], base_env, check=True)
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
        # R-001 夹具③（非测量）：断的是 chars/4 兜底成本，时长与本判据无关。
        run(["finish", run3, "--status", "succeeded", "--output-chars", "4000",
             *DEGEN_FIXTURE_ARGS], base_env, check=True)
        cost3 = json.loads(registry.read_text(encoding="utf-8"))["runs"][2]["cost_est"]
        ok("UC-4 chars/4 兜底（CNY）", cost3["estimated"] and abs(cost3["total"] - 0.0054) < 1e-9,
           f"total={cost3['total']} estimated={cost3['estimated']}（期望 0.0054）")

        # UC-4：pending_price（deepseek-v4-flash 无价）
        run(["register", "--role", "code-review", "--task", "pr:1", "--spec", "code-review@1.0.0",
             "--model", "deepseek-v4-flash", "--start"], base_env, check=True)
        run4 = json.loads(registry.read_text(encoding="utf-8"))["runs"][3]["run_id"]
        # R-001 夹具④（非测量）：断的是无价模型的 `pending_price` 标记，时长无关。
        run(["finish", run4, "--status", "succeeded", *DEGEN_FIXTURE_ARGS],
            base_env, check=True)
        cost4 = json.loads(registry.read_text(encoding="utf-8"))["runs"][3]["cost_est"]
        ok("UC-4 pending_price", cost4.get("pending_price") is True, f"cost_est={cost4}")

        # 三查修正回归：manual 非 null 时覆盖 auto（人工价
        # in=1e-6/out=2e-6 → USD 0.005 × 7.2 = CNY
        # 0.036）
        p = json.loads((runtime / "prices.json").read_text(encoding="utf-8"))
        p["manual"]["gpt-4o-mini"] = {"input_cost_per_token": 1e-6, "output_cost_per_token": 2e-6}
        (runtime / "prices.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
        run(["register", "--role", "code-review", "--task", "pr:2", "--spec", "code-review@1.0.0",
             "--model", "gpt-4o-mini", "--start"], base_env, check=True)
        run6 = json.loads(registry.read_text(encoding="utf-8"))["runs"][4]["run_id"]
        # R-001 夹具⑤（非测量）：断的是"人工价覆盖 auto"（0.036 CNY），时长无关。
        run(["finish", run6, "--status", "succeeded", "--usage-in", "1000", "--usage-out", "2000",
             *DEGEN_FIXTURE_ARGS],
            base_env, check=True)
        cost6 = json.loads(registry.read_text(encoding="utf-8"))["runs"][4]["cost_est"]
        ok("三查修正 manual 覆盖 auto（CNY）", abs(cost6["total"] - 0.036) < 1e-9, f"total={cost6['total']}（期望 0.036）")

        # 三查修正：update 只允许 running；finish 只允许 running→terminal
        run(["register", "--role", "code-review", "--task", "x", "--spec", "code-review@1.0.0"],
            base_env, check=True)
        runX = json.loads(registry.read_text(encoding="utf-8"))["runs"][5]["run_id"]
        r = run(["update", runX, "--status", "succeeded"], base_env)
        ok("三查修正 update 终态拒绝", r.returncode != 0, (r.stdout + r.stderr).strip()[:60])
        # R-001：本条**不传** flag——它断的是"queued 直接 finish 必须被状态机拒"
        # （断言文案含 `running`），在守卫之前就退出，退化标记根本没被算出来。
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
        # R-001 夹具⑥（非测量）：断的是上下文占用 ratio 与 `--cost-override` 落账，
        # 本 run 是 `register --start` 后同秒收尾 ⇒ 时长不是被测对象。
        run(["finish", run5, "--status", "succeeded", "--cost-override", "0.5",
             *DEGEN_FIXTURE_ARGS], base_env, check=True)
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

        # UC-11（M10）：fetch-spec
        # sha256 命中/失配——成功路径受 SSRF 防护无法离线走网络，
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

        # UC-13（M9 / TG-20 行 15+16）：fetch-prices 解析器（deepseek / openrouter）
        # + 合并与优先级 + **价表形状契约**（台账 E9：这段 HTML 是旧表形状的冻结副本）
        spec_fp = importlib.util.spec_from_file_location("fetch_prices", ROOT / "scripts" / "fetch-prices.py")
        fp = importlib.util.module_from_spec(spec_fp)
        assert spec_fp.loader is not None
        spec_fp.loader.exec_module(fp)
        # 冻结副本 = **现行官网表形状**（2 模型 / 每资源两档 / 12 金额，`<tr>` 平铺）：
        # 旧副本是"3 模型 + 18 个 `$`"，而 2026-09-26 起官网是 2 模型 / 12 金额 ⇒ 解析器
        # 恒返回 `{}`（红字 B）。副本不改就等于"闸门全绿而解析器已换成永不命中的那个"。
        deepseek_html = (
            '<table><tr><td colspan="3">MODEL</td>'
            "<td>deepseek-flash (1)</td><td>deepseek-v4-pro</td></tr>"
            '<tr><td rowspan="6">PRICING (2)</td>'
            '<td rowspan="2">1M INPUT TOKENS (CACHE HIT)</td>'
            "<td>OFF-PEAK</td><td>$0.003</td><td>$0.022</td></tr>"
            "<tr><td>PEAK</td><td>$0.006</td><td>$0.044</td></tr>"
            '<tr><td rowspan="2">1M INPUT TOKENS (CACHE MISS)</td>'
            "<td>OFF-PEAK</td><td>$0.15</td><td>$0.66</td></tr>"
            "<tr><td>PEAK</td><td>$0.3</td><td>$1.32</td></tr>"
            '<tr><td rowspan="2">1M OUTPUT TOKENS</td>'
            "<td>OFF-PEAK</td><td>$0.6</td><td>$1.98</td></tr>"
            "<tr><td>PEAK</td><td>$1.2</td><td>$3.96</td></tr></table>Concurrency 10"
        )
        ds = fp.parse_deepseek(deepseek_html)

        # ⑬（2026-09-21 关闭三查·二查 windows major）：
        # 重定向逐跳复检必须挂在 **HTTPRedirectHandler** 上。
        # 旧实现 `class _SafeRedirectHandler(urllib.request.HTTPSHandler)
        # ` —— `redirect_request` 定义在
        # `HTTPRedirectHandler` 上，
        # HTTPSHandler 子类的该方法**从不被 urllib 调用** = 死代码，
        # 而 `build_opener` 仍会挂默认重定向处理器 → 白名单可被一次 302 绕过（SSRF 面）
        # 。
        import urllib.request as _ur

        _opener = _ur.build_opener(fp._SafeRedirectHandler())
        ok("⑬ fetch-prices 的重定向复检挂在 HTTPRedirectHandler 上（非死代码），且是 opener 实际使用的处理器",
           issubclass(fp._SafeRedirectHandler, _ur.HTTPRedirectHandler)
           and any(isinstance(h, fp._SafeRedirectHandler) for h in _opener.handlers),
           f"mro={[c.__name__ for c in fp._SafeRedirectHandler.__mro__[:3]]}")

        # 期望值 = 冻结副本页面的**产品价格**（USD/1M → USD/token，round 10）：
        # 0.3/1e6=3e-7、1.2/1e6=1.2e-6、0.006/1e6=6e-9、0.15/1e6=1.5e-7、0.6/1e6=6e-7。
        # 这些字面量是**防"改副本不改解析器"**的锚点：换了列序/列数这里立刻红。
        dsfl = ds.get("deepseek-flash", {})
        ok("UC-13 deepseek 表格解析（2 模型 / 12 金额，模型数动态读出）",
           sorted(ds) == ["deepseek-flash", "deepseek-v4-pro"],
           f"models={sorted(ds)}")
        ok("UC-13 PEAK 列（cache-miss input=3e-7、output=1.2e-6、cache-hit=6e-9）",
           abs(dsfl.get("input_cost_per_token", 0) - 3e-7) < 1e-12
           and abs(dsfl.get("output_cost_per_token", 0) - 1.2e-6) < 1e-12
           and abs(dsfl.get("cache_read_input_token_cost", 0) - 6e-9) < 1e-12,
           f"flash={dsfl}")
        ok("UC-13 OFF-PEAK 列（off=peak/2）",
           abs(dsfl["_tiers"]["off_peak"]["input_cost_per_token"] - 1.5e-7) < 1e-12
           and abs(dsfl["_tiers"]["off_peak"]["output_cost_per_token"] - 6e-7) < 1e-12,
           f"off={dsfl.get('_tiers', {}).get('off_peak')}")
        dspeak = dsfl.get("_tiers", {}).get("peak", {})
        ok("UC-13 同页同时抓出两档（旧实现只留 peak 三项，档位靠人手补）",
           dspeak.get("input_cost_per_token") == dsfl.get("input_cost_per_token")
           and sorted(dsfl.get("_tiers", {})) == ["off_peak", "peak"],
           f"tiers={sorted(dsfl.get('_tiers', {}))}")
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
            {"deepseek": {"models": {"deepseek-flash": ds["deepseek-flash"]}}},
        )
        ok("UC-13 merge 保留 auto/manual/meta 且新增 scraped",
           merged["auto"]["a"]["input_cost_per_token"] == 1e-6 and "m" in merged["manual"]
           and merged["meta"]["fx_usd_cny"] == 7.2
           and "deepseek-flash" in merged["scraped"]["deepseek"]["models"],
           "merge 结构")
        # 解析器不产出的元数据键必须**并回**（否则抓一次就抹掉选档依据 `_peak_windows`）
        old_prov = {"models": {"old": {"input_cost_per_token": 1e-9}},
                    "_peak_windows": [{"days": ["Mon"]}],
                    "_flat_key_policy": "keep me"}
        kept = fp.merge({"scraped": {"deepseek": old_prov}},
                        {"deepseek": {"models": {"n": {}}}})
        kept_ds = kept["scraped"]["deepseek"]
        ok("UC-13 merge 并回解析器不产出的元数据（`_peak_windows` 不会被抓取抹掉）",
           kept_ds.get("_peak_windows") == old_prov["_peak_windows"]
           and kept_ds.get("_flat_key_policy") == "keep me"
           and "n" in kept_ds["models"],
           f"keys={sorted(kept_ds)}")

        # UC-13b（**台账 E9 的入场券**）：冻结副本的**形状契约**——它产出的形状必须与
        # 仓库真实价表一致，否则"改了真表而冻结副本没改"就是全绿而口径已分叉。
        prices_path = ROOT / "agents" / "runtime" / "prices.json"
        real = json.loads(prices_path.read_text(encoding="utf-8"))
        real_deepseek = (real.get("scraped") or {}).get("deepseek") or {}
        real_ds = real_deepseek.get("models") or {}
        if not real_ds:
            raise AssertionError("判据未被触发：真实价表缺 scraped.deepseek.models")
        ok("E9 冻结副本形状 == 真实价表形状（模型名/模型数/档位键逐项）",
           price_shape_problems(ds, real_ds) == [],
           f"副本={sorted(ds)} 真实={sorted(real_ds)}")
        win_ok = bool(real_deepseek.get("_peak_windows")
                      and real_deepseek.get("_tier_timezone"))
        ok("E9 真实价表的两档窗口元数据在（选档代码的真源）", win_ok,
           "scraped.deepseek._peak_windows / _tier_timezone")
        # 反向对照：**前置条件必须真的发生**——先把"真表形状"打散成旧表形状，
        # 证明契约确实会 FAIL 并点名（不是只会说 PASS）。判不出差异 ⇒ 本条不作数。
        drifted = {k: v for k, v in real_ds.items() if k != "deepseek-v4-pro"}
        drifted["deepseek-flash"] = {k: v for k, v in real_ds["deepseek-flash"].items()
                                     if k != "_tiers"}
        hit = price_shape_problems(ds, drifted)
        ok("E9 反向对照：真表被改成旧形状（少一个模型 + 掉档位键）⇒ 契约 FAIL 并点名",
           hit and "模型集不同" in hit[0] and any("_tiers" in p for p in hit),
           f"problems={hit}")
        # 优先级：manual 非 null 覆盖 scraped；
        # manual null → scraped 兜底（进程内重载 module 以改
        # AGENT_OPS_DIR）
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

        # UC-20（TG-20 行 16）：**按 run 自身时间戳选档**（spec §3）。三条反证 +
        # 一条"真入口"（真实账本行），每条都**先断言前置条件确实发生**（机制案例 26）。
        # 夹具价表：四键价 + 两档（off = peak/2）。期望值全部由它推出，不手抄。
        pk = {"input_cost_per_token": 2.5e-7, "output_cost_per_token": 1e-6,
              "cache_read_input_token_cost": 5e-9,
              "cache_creation_input_token_cost": 2.5e-7}
        off = {"input_cost_per_token": 1.25e-7, "output_cost_per_token": 5e-7,
               "cache_read_input_token_cost": 2.5e-9,
               "cache_creation_input_token_cost": 1.25e-7}
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        tier_prices = {
            "meta": {"fx_usd_cny": 7.2},
            "scraped": {"deepseek": {
                "_tier_scheme": "two_tier",
                "_tier_timezone": "Asia/Shanghai",
                "_peak_windows": [
                    {"days": weekdays, "start": "09:00", "end": "12:00"},
                    {"days": weekdays, "start": "14:00", "end": "18:00"},
                ],
                "models": {"deepseek-v4-flash": {
                    "max_input_tokens": 128000, **pk,
                    "_tiers": {"peak": pk, "off_peak": off},
                }},
            }},
        }
        tier_root = tmp / "tier"
        (tier_root / "runtime").mkdir(parents=True, exist_ok=True)
        tier_prices_path = tier_root / "runtime" / "prices.json"
        tier_prices_path.write_text(json.dumps(tier_prices, ensure_ascii=False),
                                    encoding="utf-8")
        tier_env = {**base_env, "AGENT_OPS_DIR": str(tier_root)}
        os.environ["AGENT_OPS_DIR"] = str(tier_root)

        spec_ao_tier_mod = importlib.util.spec_from_file_location("agent_ops3", CLI)
        ao_tier_mod = importlib.util.module_from_spec(spec_ao_tier_mod)
        assert spec_ao_tier_mod.loader is not None
        spec_ao_tier_mod.loader.exec_module(ao_tier_mod)
        tier = ao_tier_mod.peak_windows_from_prices(tier_prices)
        ok("UC-20 前置①：选档窗口元数据来自价表（不是代码里写死）",
           tier is not None and tier[1] == "Asia/Shanghai" and len(tier[0]) == 2,
           f"windows={tier}")

        # 反证①：**空闲时段**的 run ⇒ 必须按 off_peak 计价，且前置条件（时间戳确实落在
        # 窗口外）先被断言——落在窗口内的话这条不作数。
        off_row = {"model": "deepseek-v4-flash", "usage": {"input_tokens": 1000},
                   "started_at": ISO_OFF_PEAK, "ended_at": ISO_OFF_END}
        off_at = ao_tier_mod._parse_ts(ISO_OFF_PEAK)
        assert off_at is not None
        off_cst = off_at.astimezone(_SH).strftime("%a %H:%M")
        ok("UC-20 反证①前置：该 run 的时间戳**确实落在空闲窗口内**",
           ao_tier_mod.is_peak_at(off_at, tier[0], tier[1]) is False
           and ao_tier_mod.peak_frac_for(off_row, tier[0], tier[1]) == 0.0,
           f"{ISO_OFF_PEAK[11:16]}Z → UTC+8 {off_cst} 非高峰")
        off_cost = ao_tier_mod._estimate_cost(off_row)
        ok("UC-20 反证①：空闲时段 run 按 off_peak 计价（1e3 × 1.25e-7 × 7.2 = 9e-4）",
           off_cost.get("tier") == "off_peak" and abs(off_cost["total"] - 9e-4) < 1e-12,
           f"tier={off_cost.get('tier')} total={off_cost['total']}"
           f"（高峰价会是 {2 * off_cost['total']}）")

        # 反证②：**时间戳缺失** ⇒ 按高峰计 + `tier_assumed`（不得静默挑便宜的档）
        no_ts = ao_tier_mod._estimate_cost({"model": "deepseek-v4-flash",
                                    "usage": {"input_tokens": 1000},
                                    "started_at": None, "ended_at": None})
        ok("UC-20 反证②：时间戳缺失 ⇒ peak 计价 1.8e-3 **且** 带 tier_assumed",
           no_ts.get("tier") == "peak" and no_ts.get("tier_assumed") is True
           and abs(no_ts["total"] - 1.8e-3) < 1e-12,
           f"tier={no_ts.get('tier')} assumed={no_ts.get('tier_assumed')}"
           f" total={no_ts['total']}")
        ok("UC-20 反证②前置：缺时间戳时**不会**被算成空闲（若被算成空闲则本条不作数）",
           no_ts["total"] == 2 * off_cost["total"] and no_ts.get("peak_frac") is None,
           f"peak={no_ts['total']} off={off_cost['total']}")

        # 反证③：跨档 run（周一 11:00→13:00 CST）= 高峰 1h + 空闲 1h ⇒ §3.3 时间加权
        span = {"model": "deepseek-v4-flash", "usage": {"input_tokens": 1000},
                "started_at": ISO_SPAN_START, "ended_at": ISO_SPAN_END}
        ok("UC-20 反证③前置：该 run **确实跨越**档位边界（peak_frac=0.5，不是 0 或 1）",
           ao_tier_mod.peak_frac_for(span, tier[0], tier[1]) == 0.5,
           f"peak_frac={ao_tier_mod.peak_frac_for(span, tier[0], tier[1])}")
        span_cost = ao_tier_mod._estimate_cost(span)
        ok("UC-20 反证③：跨档按时间加权（0.5×1.8e-3 + 0.5×9e-4 = 1.35e-3，§3.3 一致）",
           span_cost.get("tier") == "mixed" and span_cost.get("peak_frac") == 0.5
           and abs(span_cost["total"] - 1.35e-3) < 1e-12,
           f"tier={span_cost.get('tier')} frac={span_cost.get('peak_frac')}"
           f" total={span_cost['total']}")

        # 真入口：**真实账本行**（含其真实历史时间戳，逐字取自 registry.json）走同一条
        # `_estimate_cost`——这条就是"夜间不再按高峰计费"的机器判据（同一行、同一 usage，
        # 旧代码按扁平高峰键 = 2 倍）。CLI 侧的可见性另在交付回执里用真 run 演示。
        reg_path = ROOT / "agents" / "runtime" / "registry.json"
        real_reg = json.loads(reg_path.read_text(encoding="utf-8"))
        ref_rows = [x for x in real_reg.get("runs", [])
                    if x.get("model") and x.get("started_at")
                    and x.get("ended_at") and x.get("usage")]
        win = (tier[0], tier[1])

        def frac_of(row: dict) -> float | None:
            """该 run 的高峰时间占比（None = 端点缺失/退化）。"""
            return ao_tier_mod.peak_frac_for(row, win[0], win[1])

        ref = next((x for x in ref_rows if frac_of(x) == 0.0), None)
        if ref is None:
            raise AssertionError("判据未被触发：真实账本缺'时间戳落在空闲窗口'的 run"
                                 f"（可判定 {len(ref_rows)} 条）⇒ 真入口判据不作数")
        gold = ao_tier_mod._estimate_cost(ref)
        # 高峰口径 = 旧行为（扁平键镜像高峰）：用同一价表算出**对照量**，不手抄数字
        peak_cost = ao_tier_mod._estimate_cost({**ref, "started_at": ISO_PEAK,
                                        "ended_at": ISO_PEAK_END})
        ok("UC-20 真入口前置：该真实 run 的时间戳**确实落在空闲窗口内**",
           ao_tier_mod.peak_frac_for(ref, tier[0], tier[1]) == 0.0,
           f"{ref['run_id']} started_at={ref['started_at']}")
        peak_total = peak_cost["total"]
        ok("UC-20 真入口：真实账本行按 off_peak 计价（对照：同一行按高峰口径是 2 倍）",
           gold.get("tier") == "off_peak"
           and abs(gold["total"] * 2 - peak_total) < 1e-12,
           f"{ref['run_id']} off={gold['total']} peak={peak_total} "
           f"usage={ref.get('usage')}")
        del ref, peak_cost, peak_total, ref_rows, real_reg

        # E9 的**主判据**（红字 A）：派生**不得丢档**——白名单若不同步，`prices-derive`
        # 一跑档位就没了，而"我这次写对了"不是判据。反向对照：把注册表摘掉（= 白名单不
        # 同步的等价物）后同一断言必须 FAIL——先证明它咬得住，再说它绿。
        tpath = tmp / "tier" / "runtime" / "prices.json"
        r = run(["prices-derive"], tier_env, check=True)
        after = json.loads(tpath.read_text(encoding="utf-8"))
        prov = (after.get("scraped") or {}).get("deepseek") or {}
        prov_keys = ("_tier_scheme", "_tier_timezone", "_peak_windows")
        model_keys = ("_tiers",)
        models_of = (prov.get("models") or {})
        flash_tiers = (models_of.get("deepseek-v4-flash") or {}).get("_tiers") or {}
        flash_keys = sorted((models_of.get("deepseek-v4-flash") or {}))
        ok("E9 派生后档位仍在（provider 元数据 + 模型 `_tiers` 一个不少）",
           all(k in prov for k in prov_keys)
           and all(k in flash_keys for k in model_keys),
           f"派生后 provider keys={sorted(prov)} model keys={flash_keys}")
        ok("E9 派生后模型档位未被重建抹掉（`_tiers.off_peak` 逐键相等）",
           (models_of.get("deepseek-v4-flash") or {}).get("_tiers") ==
           tier_prices["scraped"]["deepseek"]["models"]["deepseek-v4-flash"]["_tiers"],
           f"off_peak={flash_tiers.get('off_peak')}")
        ok("E9 派生后选档仍可用（`peak_windows_from_prices` 读得到窗口）",
           ao_tier_mod.peak_windows_from_prices(after) is not None,
           f"keys={sorted(prov)}")
        # 反向对照前置：真造出"白名单不同步"的实现（临时副本，**不动仓库文件**）。
        # 摘掉 `_tiers, _tier_scheme` 这一行 ⇒ 等价于"多档落地时没同步白名单"。
        # 判据的**作用域**要写准：它管 `auto` 段的重建。`scraped` 段是整段带过的，
        # 故先证明"档位一旦落到 `auto` 就被白名单决定生死"，再证明"白名单摘掉即丢档"。
        clone = tmp / "clone"
        (clone / "scripts").mkdir(parents=True, exist_ok=True)
        src_txt = CLI.read_text(encoding="utf-8")
        # 用正则匹配（不写死缩进/折行）：重排白名单时这条反向对照必须**还能造出前置**，
        # 否则它会以"判据未被触发"红掉——那正是本仓"夹具随被测代码漂移"的形态。
        pat = re.compile(r'^[ \t]*"cache_creation_input_token_cost",'
                         r' "_tiers", "_tier_scheme"\)[ \t]*$', re.M)
        hits = pat.findall(src_txt)
        if len(hits) != 1:
            raise AssertionError(f"判据未被触发：白名单声明行命中 {len(hits)} 次")
        clone_cli = clone / "scripts" / "agent-ops.py"
        clone_cli.write_text(pat.sub(")", src_txt), encoding="utf-8")

        def derive_with(cli_path: Path) -> subprocess.CompletedProcess:
            """跑一次 `prices-derive`（副本 REPO_ROOT 在 %TEMP% ⇒ 显式 PYTHONPATH）。"""
            env = {**tier_env, "PYTHONPATH": str(ROOT)}
            return subprocess.run([sys.executable, str(cli_path), "prices-derive"],
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", env=env)

        # `auto` 段是**从 litellm 表重建**的，故用 litellm 里确有的模型（`gpt-4o-mini`）
        # 承载档位：在它的 `auto` 条目上挂一份 `_tiers`，再看派生后它还在不在。
        # 这正是红字 A 说的形态——"把 deepseek 价移到 auto 段即丢档"。
        src_flash = tier_prices["scraped"]["deepseek"]["models"]["deepseek-v4-flash"]
        seed_entry = {k: v for k, v in src_flash.items() if k != "max_input_tokens"}
        tier_seed = dict(seed_entry["_tiers"])
        seeded = json.loads(tpath.read_text(encoding="utf-8"))
        seeded["auto"] = {**seeded.get("auto", {}),
                          "gpt-4o-mini": {**seed_entry, "_tiers": tier_seed}}
        tpath.write_text(json.dumps(seeded, ensure_ascii=False), encoding="utf-8")
        auto_now = lambda: (json.loads(tpath.read_text(encoding="utf-8")).get("auto")  # noqa: E731
                            or {}).get("gpt-4o-mini") or {}
        r_bad = derive_with(clone_cli)
        bad_auto = auto_now()
        bad_out = (r_bad.stdout + r_bad.stderr).strip()[-80:]
        ok("E9 反向对照：白名单不同步 ⇒ `auto` 段的档位**真被丢弃**（前置条件发生）",
           r_bad.returncode == 0 and bad_auto.get("input_cost_per_token") is not None
           and "_tiers" not in bad_auto,
           f"rc={r_bad.returncode} auto 键={sorted(bad_auto)} out={bad_out}")
        tpath.write_text(json.dumps(seeded, ensure_ascii=False), encoding="utf-8")
        r_good = derive_with(CLI)
        good_auto = auto_now()
        # 白名单的**作用域**（实测）：它决定 `auto` 段**有哪些键**，值取自 litellm 表。
        # litellm 表没有 `_tiers` ⇒ 这里只能是 `None`（键被保住、值取不到）。
        # ⇒ 红字 A 的修法只能作用在 `scraped` 段；`auto` 段承载档位需另供真源。
        ok("E9 对照：同步白名单 ⇒ `auto` 段**保留 `_tiers` 键**（值取自 litellm）",
           r_good.returncode == 0 and "_tiers" in good_auto
           and good_auto["_tiers"] is None,
           f"rc={r_good.returncode} auto keys={sorted(good_auto)}")

        run(["prices-derive"], tier_env, check=True)  # 恢复夹具（不留半态给后续用例）

        # UC-14（TG-11，Sprint-17）：评审类 run 的 scope 来源闸门（fail-closed，
        # 机器可验）
        # 反向对照：本块断言在**未修复**实现上必须不成立（旧 CLI
        # 无 --scope-source/--deviation 参数）
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

        # UC-15（TG-15，Sprint-17 D2）：
        # 闸门政策**数据驱动**——角色集合/阈值来自数据文件，
        # 不是代码常量。反向对照：在 spec 目录里临时新增一个声明 `scope_required:
        # true` 的角色，
        # **不改任何代码**，CLI 必须立刻要求它声明 scope；
        # 把声明改成 false 后必须立刻放行。
        # 这同时证明"删声明绕不过去"（缺声明是报错，不是放行，见数据源完备性自检）。
        # **F1：探针写在 `specs_dir`（%TEMP%）
        # 而不是仓库 `agents/functions/`**——见文件头与 main() 开头。
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

        # UC-16（TG-15）：数据源**缺声明**不是"不需要"，
        # 而是 fail-closed 报错（删声明绕不过闸门）
        # **F1：同样写在 `specs_dir`（%TEMP%）**——旧实现把它写进仓库，
        # 是并行的第二个 clobber 源。
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


        # UC-17（审核 F1/N5）：coverage_anchor 必须**规范化**为完整 sha，
        # 无法解析则 fail-closed
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

        # UC-18（审核 N10）：`finish
        # --result-file` **不得改写报告换行**（LF → CRLF 静默改写）
        # 原实现 `dest.write_text(rel.read_text(encoding="utf-8"), encoding="utf-8")`：
        # 读侧做
        # universal-newline 转换、写侧把 `\n` 落成 `os.linesep`（Windows=CRLF）→ 仓库基线的 LF
        # 报告被静默改成 CRLF（实测 35721 B → 35913 B / 192 行）。
        # 归档步骤最不该动产物字节。
        for tag, eol in (("lf", "\n"), ("crlf", "\r\n")):
            rid = f"run-uc18-{tag}"
            run(["register", "--role", "impact-assessment", "--task", f"eol-{tag}", "--spec",
                 "impact-assessment@1.4.4", "--run-id", rid], base_env, check=True)
            run(["update", rid, "--status", "running"], base_env, check=True)
            report = tmp / f"uc18-{tag}.report.md"
            report.write_bytes("".join(f"| 行 {i} | {tag} 报告正文 |{eol}" for i in range(120))
                               .encode("utf-8"))
            # R-001 夹具⑦（非测量）：断的是归档**按字节**复制（LF/CRLF 不被改写）；
            # 本 run 的 register/update/finish 同秒 ⇒ 时长不是被测对象。
            run(["finish", rid, "--status", "succeeded", "--result-file", str(report),
                 *DEGEN_FIXTURE_ARGS],
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
        # `run-2026-09-24-doc-audit-066`（账本）↔ `run-2026-09-25-doc-audit-066`（目录）
        # 。
        # 历史例外写在数据文件（agents/policy/run-dir-exceptions.json）
        # 并**必须注明理由**。
        # **账本不存在 ≠ 账本有问题**（C5，2026-09-25 CI run #207 实测）：
        # `agents/runtime/registry.json` 被
        # `.gitignore` 忽略 ⇒ **CI 的全新 checkout 必然没有它**，
        # 连 `agents/runs/` 也不存在。
        # 旧实现直接 `read_text` ⇒ `FileNotFoundError` ⇒ 整个 offline 套件
        # 在 CI 恒红（实测 run #207 第 7 步：`SUITE FAILED (1/24): verify_agentops.py`）
        # 。
        # 现按 `verify_ledger_measurement.py` / `verify_close_readiness.py` 的同一口径：
        # **缺账本 → 显式 SKIP（理由上屏，且不打印 PASS——"跳过"不得冒充"通过"）**；
        # **存在但坏 → 照旧 fail-closed**（下面读文件/解析失败会真抛）。
        real_registry = ROOT / "agents" / "runtime" / "registry.json"
        if not real_registry.is_file():
            print(f"SKIP[ledger-absent] M-g 账本 run_id ↔ agents/runs/* 目录名一致性："
                  f"{real_registry} 不存在（fresh clone；registry.json 被 .gitignore 忽略）"
                  f"→ 该判据只在本机/有账本的环境执行。**本行不是 PASS**。")
        else:
            real_ledger = json.loads(real_registry.read_text(encoding="utf-8"))
            ledger_ids = {str(r.get("run_id") or "") for r in real_ledger.get("runs", [])}
            exc_file = ROOT / "agents" / "policy" / "run-dir-exceptions.json"
            exc = json.loads(exc_file.read_text(encoding="utf-8")) if exc_file.is_file() else {}
            exc_items = exc.get("exceptions") or []
            no_reason = [str(e.get("dir")) for e in exc_items if not str(e.get("reason") or "").strip()]
            ok("M-g 例外白名单每一条都写了理由（白名单不是静音开关）", not no_reason,
               f"缺理由：{no_reason[:3]}")
            exc_dirs = {str(e.get("dir")) for e in exc_items}
            runs_root = ROOT / "agents" / "runs"
            real_dirs = {p.name for p in runs_root.iterdir() if p.is_dir()} if runs_root.is_dir() else set()
            orphan_dirs = sorted(real_dirs - ledger_ids - exc_dirs)
            ok("M-g 账本 id ↔ 目录名一致：agents/runs/* 目录名都能在账本里找到同名 run（例外已在数据文件登记）",
               not orphan_dirs, f"对不上账本且无例外登记的目录：{orphan_dirs[:5]}")
            stale_exc = sorted(exc_dirs & ledger_ids)
            ok("M-g 例外白名单只减不增：登记过的例外若已在账本里有同名 run → 必须删除该例外",
               not stale_exc, f"已不再需要的例外：{stale_exc[:5]}")

        # UC-19（TG-8②）：**离线开关**——一个开关关掉全部外呼，
        # 且在**发起请求之前**拒绝并点名。
        # 判据（卡文）：开关开启 →
        # 每个被禁止的外呼入口 rc≠0 且点名原因（不是靠网络超时）；
        #              开关关闭 → 允许（或按设计）。
        # 反向对照（§6"倒过来试试"）：
        # 以下每条的对照分支都断言"**没有**出现 OFFLINE-REFUSED"，
        # 即不能只证明"开关开着会拒绝"，
        # 还要证明"关着不会无故拒绝"（否则闸门可能是恒拒绝）。
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

        # ②配置面：政策 `enabled=true`（env 未设）
        # 同样生效——证明"开关可配置"不只 env 一条路
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

        # ④两侧实现一致（app/offline_guard.py 与 verify/outbound_guard.py）：
        # 同一 env 取值同结论
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

        # ⑤政策**不可读/非法** → 产品侧按**离线**处理（M4，三查 finding major-4）。
        #   原实现把"文件缺失/坏 JSON"折成 `{}`，`bool({}.get("enabled"))` = False
        #   = **在线** ⇒ 开关自己的数据不可读时，产品静默回到"全部外呼放行"——
        #   正是政策明文要消灭的"静默变成永远在线"。判据可核：不看超时，直接看
        #   **判定值**（`switch_state()[0] is True`）、来源说明是否点名了政策问题，
        #   以及 `refuse_if_offline()` 是否**真的**拒绝。
        #   逐态断言（5 态）+ 反向对照（合法政策 + 开关关闭 → 在线），防"恒拒绝"也能过。
        #   实现说明：用**内存替身**（只实现 `read_text()`）替代写临时文件——既不多一个
        # 写盘落点（`verify_artifact_paths.py` 的动态目标棘轮按文件设上限），
        # 也不留产物；
        # `load_policy_file()` 走的仍是同一条读取路径（含 OSError / JSONDecodeError）。
        class PolicyProbe:
            """政策文件替身：`body` 或 `exc`（二选一），不落盘。"""

            def __init__(self, body: str = "", exc: Exception | None = None) -> None:
                self.body, self.exc = body, exc

            def read_text(self, encoding: str = "utf-8") -> str:
                if self.exc is not None:
                    raise self.exc
                return self.body

        real_app_policy = ag.POLICY
        os.environ.pop(env_name, None)  # 本块只考政策文件这一路：env 未设
        bad_switch_json = json.dumps({"offline_switch": "yes"})
        invalid_policy_states = [
            ("文件不存在", PolicyProbe(exc=FileNotFoundError("policy.json"))),
            ("坏 JSON", PolicyProbe("{not json")),
            ("顶层是 null", PolicyProbe("null")),
            ("顶层是数组（类型错）", PolicyProbe('["not", "an", "object"]')),
            ("offline_switch 不是对象", PolicyProbe(bad_switch_json)),
        ]
        for label, probe in invalid_policy_states:
            ag.POLICY = probe
            off_state, off_why = ag.switch_state()
            refused = False
            try:
                ag.refuse_if_offline("uc19 政策不可读探针")
            except ag.OfflineRefused:
                refused = True
            ok(f"UC-19⑤ 政策{label} → 产品侧判定**离线**且点名原因（并真的拒绝外呼）",
               off_state is True and "policy.json" in off_why and "离线" in off_why
               and refused,
               f"offline={off_state} why={off_why[:100]} refused={refused}")

        valid_switch = {**_POLICY.policy_file["offline_switch"], "enabled": False}
        ag.POLICY = PolicyProbe(json.dumps(
            {**_POLICY.policy_file, "offline_switch": valid_switch},
            ensure_ascii=False, indent=2))
        on_state, on_why = ag.switch_state()
        allowed = True
        try:
            ag.refuse_if_offline("uc19 合法在线探针")
        except ag.OfflineRefused:
            allowed = False
        ok("UC-19⑤ 反向对照：合法政策 + 开关关闭（env 未设）→ 产品侧**在线**放行"
           "（证明上面 5 态不是恒拒绝）",
           on_state is False and allowed and "offline_switch.enabled" in on_why,
           f"offline={on_state} why={on_why} allowed={allowed}")
        ag.POLICY = real_app_policy

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
        # R-001 夹具⑧（非测量）：UC-20 三条 run 断的是 window/produced_only 判据翻转，
        # 三条都是 register→update→finish 同秒收尾 ⇒ 时长不是被测对象。
        run(["finish", "run-uc20-produced", "--status", "succeeded",
             "--covers-through", head_full20, *DEGEN_FIXTURE_ARGS], base_env, check=True)

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
             "--covers-through", head_full20, *DEGEN_FIXTURE_ARGS], base_env, check=True)
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
             "--covers-through", head_full20, *DEGEN_FIXTURE_ARGS], base_env, check=True)
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

        # UC-22（TG-19 M-A 收尾）：Sprint 身份的**显式登记 + 受控回填**。
        # 判定域按 `sprint` 字段派生 ⇒ 身份写错会让该 run 静默掉进**别的** Sprint 的域；
        # 而"新函数插在装饰器与它的函数之间"会让 `@_with_registry_lock` 挂错对象
        # （2026-09-25 实测：`register` 因此**丢掉账本锁**、`_norm_sprint` 反而拿到锁并
        # 在 `cmd_set_sprint` 内自锁超时）⇒ 本 UC 同时断言"写命令仍在锁内"。
        run(["register", "--role", "impact-assessment", "--task", "uc22-sprint-id",
             "--spec", "impact-assessment@1.4.4", "--run-id", "run-uc22-sprint",
             "--sprint", "Sprint-18"], base_env, check=True)

        def _row22(rid: str = "run-uc22-sprint") -> dict:
            data = json.loads(registry.read_text(encoding="utf-8"))
            return next(x for x in data["runs"] if x["run_id"] == rid)

        ok("UC-22 register --sprint 归一化：'Sprint-18' → '18'（与闸门同口径：纯编号）",
           _row22().get("sprint") == "18", f"sprint={_row22().get('sprint')!r}")
        r = run(["register", "--role", "impact-assessment", "--task", "bad",
                 "--spec", "impact-assessment@1.4.4", "--run-id", "run-uc22-bad",
                 "--sprint", "abc"], base_env, raw=True)
        present = {x["run_id"] for x in json.loads(registry.read_text(encoding="utf-8"))["runs"]}
        ok("UC-22 反向对照：非法身份（abc）→ 拒绝且不留半条 run（fail-closed）",
           r.returncode != 0 and "SPRINT-ID-ERROR" in (r.stdout + r.stderr)
           and "run-uc22-bad" not in present, f"rc={r.returncode}")
        r = run(["set-sprint", "run-uc22-sprint", "--sprint", "19",
                 "--reason", "UC-22：判定域派生所需的身份回填（受控、带理由）"],
                base_env, raw=True)
        marks = _row22().get("sprint_backfills") or []
        ok("UC-22 set-sprint 回填成功 + 四件套留痕（field/from/to/reason/by）",
           r.returncode == 0 and _row22().get("sprint") == "19" and len(marks) == 1
           and {"field", "from", "to", "reason", "by"} <= set(marks[-1]),
           f"rc={r.returncode} sprint={_row22().get('sprint')!r} marks={len(marks)}")
        r = run(["set-sprint", "run-uc22-sprint", "--sprint", "Sprint-19",
                 "--reason", "UC-22：同值必须无操作（不得追加假留痕）"],
                base_env, raw=True)
        ok("UC-22 幂等/防假痕：同值 = 无操作（报『无变化』且留痕条数不变）",
           r.returncode == 0 and "无变化" in r.stdout
           and len(_row22().get("sprint_backfills") or []) == 1,
           f"rc={r.returncode} marks={len(_row22().get('sprint_backfills') or [])}")
        r = run(["set-sprint", "run-uc22-sprint", "--sprint", "20",
                 "--reason", "short"], base_env, raw=True)
        ok("UC-22 反向对照：过短 --reason → 拒绝（回填必须带可核理由）",
           r.returncode != 0, f"rc={r.returncode}")
        probe = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util;spec=importlib.util.spec_from_file_location("
             "'a','scripts/agent-ops.py');m=importlib.util.module_from_spec(spec);"
             "spec.loader.exec_module(m);"
             "print(','.join(n for n in ('cmd_register','cmd_set_sprint','cmd_update',"
             "'cmd_finish','cmd_set_scope','cmd_set_anchor','cmd_round',"
             "'cmd_set_result_files','cmd_interrupt') "
             "if not hasattr(getattr(m,n),'__wrapped__')))"],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
        ok("UC-22 锁覆盖：写命令必须仍在 `@_with_registry_lock` 内（装饰器不得被挤开）",
           probe.stdout.strip() == "",
           f"未加锁={probe.stdout.strip()!r} rc={probe.returncode}")

        # ---- 台账 E1 / 行 7：写入侧真入口对一致性向量的结论 ------------------
        # 向量表在 spec（与读取侧同一张表）。本块把每个输入喂给**真 CLI**
        # （`set-sprint`），断言"接受/拒绝 + 落库值"逐条与规范期望一致。
        # 为什么必须在这里：判定域由读取侧按同一口径派生，写入侧若与它分叉，
        # 就是台账 E1 反证列的形态（写进去的读不出来）——闸门侧自比查不出这一条。
        vector = _spec_vector("### 4.1 表 A")
        reason_e1 = "E1 向量：真 CLI 接受后落库值必须逐字节等于规范期望值"
        run(["register", "--role", "impact-assessment", "--task", "e1-sprint-vector",
             "--spec", "impact-assessment@1.4.4", "--run-id", "run-e1-vector"],
            base_env, check=True)

        def _sprint_of() -> object:
            data = json.loads(registry.read_text(encoding="utf-8"))
            row = next(x for x in data["runs"] if x["run_id"] == "run-e1-vector")
            return row.get("sprint")

        # 变量名必须**全文件唯一**：`verify_artifact_paths.py` 的写盘目标分解器
        # 按**名字**收集 `Assign`（不分作用域），同名多处赋值会分解失败 ⇒
        # 该文件"动态目标"计数 +1（本块曾用 `bad`，与 UC-1 的 `bad` 撞名而踩中）。
        sprint_bad: list[str] = []
        accepts = rejects = 0
        sprint_before: object = _sprint_of()
        for rid, raw, want in vector:
            # 拒绝分支的不变式是"**落库值不被改动**"——不是"落库值为空"：
            # 前一条合法向量可能已经写过值，拿 `is None` 判会把正常拒绝误报成改动。
            r = run(["set-sprint", "run-e1-vector", "--sprint", str(raw),
                     "--reason", f"E1 一致性向量 {rid}：真入口结论比对"],
                    base_env, raw=True)
            blob = r.stdout + r.stderr
            got = _sprint_of()
            if want is None:
                rejects += 1
                if r.returncode == 0 or "SPRINT-ID-ERROR" not in blob:
                    sprint_bad.append(f"{rid}: 期望拒绝，rc={r.returncode}")
                elif got != sprint_before:
                    sprint_bad.append(f"{rid}: 拒绝却改动了落库值"
                                      f" {sprint_before!r} -> {got!r}")
            else:
                accepts += 1
                if r.returncode != 0:
                    sprint_bad.append(f"{rid}: 期望接受，rc={r.returncode} "
                                      f"{blob.strip()[:40]}")
                elif got != want:
                    sprint_bad.append(f"{rid}: 落库 {got!r} != 期望 {want!r}")
            sprint_before = got
        ok(reason_e1, not sprint_bad,
           f"{len(vector)} 行 bad={sprint_bad[:2] or '[]'}")
        # 前置条件：两个分支都**真的**被走到（造不出反例就是判据没被触发）。
        ok("E1 向量：接受与拒绝两个分支都真被走到（否则本次结论不作数）",
           accepts > 0 and rejects > 0, f"接受 {accepts} 例 / 拒绝 {rejects} 例")

        # UC-23（P1 独立复核整改）：`result_files` 的**受控回填**。
        # 病根（2026-09-25 实测事故）：`finish --result-file` 是收尾**当时**唯一写入口，
        # 而 `verify_ledger_measurement.py` 对**终态评审类 run** 严格判
        # `[missing_result_files_review]`；漏带 `--result-file` 之后 `finish`
        # 拒绝二次收尾
        # （`succeeded -> succeeded` 非法流转——这条 fail-closed 是对的）
        # ⇒ 该问题**不可修**
        # = 永久红。复核 run-083 正是这样（结论在报告里、账本里却没有产物）。
        run(["register", "--role", "code-review", "--task", "uc23-result-files",
             "--spec", "code-review@1.0.0", "--run-id", "run-uc23-review"],
            base_env, check=True)
        run(["update", "run-uc23-review", "--status", "running"],
            base_env, check=True)
        # R-001 夹具⑨（非测量）：断的是"漏带 --result-file 的终态评审 run 可受控回填"，
        # 本 run 的 register/update/finish 同秒 ⇒ 时长不是被测对象。
        run(["finish", "run-uc23-review", "--status", "succeeded",
             "--output-chars", "1200", *DEGEN_FIXTURE_ARGS],
            base_env, check=True)

        def _row23() -> dict:
            data = json.loads(registry.read_text(encoding="utf-8"))
            return next(x for x in data["runs"] if x["run_id"] == "run-uc23-review")

        rep23 = tmp / "runs" / "run-uc23-review" / "code-review.report.md"
        rep23.parent.mkdir(parents=True, exist_ok=True)
        rep23.write_text("# UC-23 复核报告\n\n- **major** 示例\n", encoding="utf-8")
        rel23 = "runs/run-uc23-review/code-review.report.md"
        ok("UC-23 前置：复现病根——漏带 --result-file 的终态评审 run"
           "（result_files 为空）",
           _row23().get("result_files") == [] and (tmp / rel23).is_file(),
           f"result_files={_row23().get('result_files')!r}")
        r = run(["set-result-files", "run-uc23-review", "--file", rel23,
                 "--reason", "UC-23：复核产物漏归档——按 agents 根相对路径补登（可核）"],
                base_env, raw=True)
        marks23 = _row23().get("result_files_backfills") or []
        ok("UC-23 受控回填成功 + 六件套留痕（at/field/from/to/reason/by）",
           r.returncode == 0 and _row23().get("result_files") == [rel23]
           and len(marks23) == 1
           and {"at", "field", "from", "to", "reason", "by"} <= set(marks23[-1])
           and marks23[-1].get("from") == [] and marks23[-1].get("to") == [rel23],
           f"rc={r.returncode} marks={len(marks23)}")
        r = run(["set-result-files", "run-uc23-review", "--file", rel23,
                 "--reason", "UC-23：同值必须无操作（不得追加假留痕）"],
                base_env, raw=True)
        ok("UC-23 幂等/防假痕：同值 = 无操作（报『无变化』且留痕条数不变）",
           r.returncode == 0 and "无变化" in (r.stdout + r.stderr)
           and len(_row23().get("result_files_backfills") or []) == 1,
           f"rc={r.returncode} "
           f"marks={len(_row23().get('result_files_backfills') or [])}")
        r = run(["set-result-files", "run-uc23-review",
                 "--file", "runs/run-uc23-review/does-not-exist.md",
                 "--reason", "UC-23 反向对照：不存在的产物必须被拒"
                             "（账本不得指向空气）"],
                base_env, raw=True)
        ok("UC-23 反向对照：产物不存在 → 拒绝且**不改库**（路径必须可核，fail-closed）",
           r.returncode != 0 and "RESULT-FILE-ERROR" in (r.stdout + r.stderr)
           and _row23().get("result_files") == [rel23],
           f"rc={r.returncode} out={(r.stdout + r.stderr).strip()[:60]}")
        r = run(["set-result-files", "run-uc23-review", "--file", rel23,
                 "--reason", "short"], base_env, raw=True)
        ok("UC-23 反向对照：过短 --reason → 拒绝（回填必须带可核理由）",
           r.returncode != 0, f"rc={r.returncode}")
        r = run(["set-result-files", "run-uc23-review",
                 "--file", "verify/verify_agentops.py",
                 "--reason", "UC-23 反向对照：只认 agents 根口径，仓库根路径不得混入"],
                base_env, raw=True)
        ok("UC-23 反向对照：仓库根相对路径 → 拒绝（**同一个字段不得有两种读法**）",
           r.returncode != 0 and "RESULT-FILE-ERROR" in (r.stdout + r.stderr),
           f"rc={r.returncode}")

        # UC-24（R-001 / G3）：`finish` 写入口 **fail-closed**——退化时间戳不得写成终态。
        # 病根：`register` 漏 `--start` ⇒ `update`(running) 与 `finish` 落在**同一秒**
        # ⇒ `zero_duration`，"未测得"被写成"零耗时"。三条都**真跑 CLI 子进程**：
        #   ① 不带 `--allow-degenerate` ⇒ 拒（文案含 FINISH-ERROR）且**账本未动**；
        #   ② 带 flag + ≥10 字符理由 ⇒ 允许（账本按 declared/null 记，不冒充测量值）；
        #   ③ 带 flag + <10 字符理由 ⇒ **仍拒**（逃生口必须具名）。
        # 夹具确定性：`_now()` 秒级截断，"同秒"不是必然事件（实测 update+finish
        # 约 0.11+0.15 s ⇒ 12 次里命中 10 次）。故先 `_uc24_align()` 等"秒刚翻"，
        # 未命中就换新 run 重测（有界 3 轮）——重试只补偿"没造出退化态"，
        # **不放宽判据**：命中后仍逐条断言 rc / 文案 / 账本行。
        def _uc24_row(rid: str) -> dict:
            data = json.loads(registry.read_text(encoding="utf-8"))
            return next(x for x in data["runs"] if x["run_id"] == rid)

        def _uc24_align() -> None:
            """等到"秒刚翻"再开跑（把 update+finish 压进同一自然秒的窗口最大化）。"""
            import time as _t
            while _t.time() % 1 > 0.03:
                _t.sleep(0.004)

        def _uc24_attempt(rid: str,
                          extra: list[str],
                          probe=None) -> tuple[subprocess.CompletedProcess, dict]:
            """造一条"同秒收尾"的 run：`register` → `update` → `finish`。

            `register` **不带** `--start`，由 `update` 记起点——这正是 CLI 的正常流程
            （R-001 已更正"update 应拒绝空 started_at"那条错处方），
            所以本夹具复现的是**真实**病根，不是人为注入的时间戳。
            `probe` 在 `finish` **之前**调用（行 17 用来取"拒前"目录清单）。
            """
            run(["register", "--role", "impact-assessment", "--task", "uc24-degenerate",
                 "--spec", "impact-assessment@1.4.4",
                 "--run-id", rid], base_env, check=True)
            _uc24_align()
            run(["update", rid, "--status", "running"], base_env, check=True)
            if probe is not None:
                probe(rid)
            proc = run(["finish", rid, "--status", "succeeded", "--output-chars", "10",
                        *extra], base_env, raw=True)
            return proc, _uc24_row(rid)

        def _uc24_loop(prefix: str, extra: list[str], want: str,
                       probe=None) -> tuple[subprocess.CompletedProcess, dict]:
            """有界重试到"这一轮真的落在退化态"；`want` = `reject` / `allow`。"""
            last = (None, {})
            for i in (1, 2, 3):
                proc, row = _uc24_attempt(f"{prefix}-{i}", extra, probe)
                last = (proc, row)
                hit = (proc.returncode != 0 if want == "reject"
                       else proc.returncode == 0 and bool(row.get("measurement_flags")))
                if hit:
                    return proc, row
                print(f"INFO[UC-24] {prefix}-{i} 跨秒未命中退化"
                      f"（rc={proc.returncode} flags={row.get('measurement_flags')}）"
                      "→ 换新 run 重测（判据不放宽）")
            return last

        proc24, row24 = _uc24_loop("run-uc24-nofg", [], "reject")
        out24 = proc24.stdout + proc24.stderr
        ok("UC-24 反向对照①：退化收尾**不带** flag → 拒绝（非零退出 + FINISH-ERROR）",
           proc24.returncode != 0 and "FINISH-ERROR" in out24
           and "zero_duration" in out24,
           f"rc={proc24.returncode} out={out24.strip()[:64]}")
        ok("UC-24 反向对照①：文案给出**两条**修法（受控回填 / 具名记账）",
           "set-started-at" in out24 and "--allow-degenerate" in out24
           and "--degenerate-reason" in out24,
           f"尾部={out24.strip()[-56:]}")
        ok("UC-24 反向对照①：拒绝 = **账本未动**（该 run 仍 running、无 ended_at）",
           row24.get("status") == "running" and not row24.get("ended_at"),
           f"status={row24.get('status')!r} ended_at={row24.get('ended_at')!r}")
        reason24 = "probe: 同秒收尾，非真实测量（R-001）"
        proc24b, row24b = _uc24_loop("run-uc24-allow",
                                     ["--allow-degenerate",
                                      "--degenerate-reason", reason24], "allow")
        ok("UC-24 正向对照②：flag + ≥10 字符理由 → 写库成功，且该行确为退化态",
           proc24b.returncode == 0 and row24b.get("status") == "succeeded"
           and row24b.get("measurement_flags") == ["zero_duration"],
           f"rc={proc24b.returncode} flags={row24b.get('measurement_flags')}")
        ok("UC-24 正向对照②：放行 ≠ 冒充测量（`declared` + `dur_minutes=None`）",
           row24b.get("measurement_source") == "declared"
           and row24b.get("dur_minutes") is None,
           f"src={row24b.get('measurement_source')} dur={row24b.get('dur_minutes')}")
        ok("UC-24 正向对照②：具名理由在 stdout 可见"
           "（行 18 起**同时**落账本，上屏仍保留）",
           reason24 in (proc24b.stdout + proc24b.stderr),
           f"out={(proc24b.stdout + proc24b.stderr).strip()[-56:]}")
        # 行 18（2026-09-27 改）：理由**同时落账本**——此前只上屏，事后读账本只有
        # `declared`+退化标记+null，"为什么不可测"查不到（唯一的解释留在终端输出里）。
        ok("UC-24 正向对照②（行 18）：具名理由**落账本**"
           " `degenerate_reason`（逐字等于所传理由）",
           row24b.get("degenerate_reason") == reason24,
           f"degenerate_reason={row24b.get('degenerate_reason')!r}")
        # 口径配对：`degenerate_reason` ↔ `measurement_flags` 必须**逐行配对**
        # （两份事实来自同一次写入；「有标记无理由」正是行 18 的缺口形态）。
        # 前置：整本夹具账本里确实存在带退化标记的行（否则本条不作数）。
        data24 = json.loads(registry.read_text(encoding="utf-8"))
        paired24 = [(x.get("run_id"), bool(x.get("measurement_flags")),
                     bool(str(x.get("degenerate_reason") or "").strip()))
                    for x in data24["runs"]]
        unpaired24 = [p for p in paired24 if p[1] != p[2]]
        ok("UC-24（行 18）：夹具账本里 `degenerate_reason`"
           " ↔ `measurement_flags` 逐行配对"
           "（前置：确有带退化标记的行；无「有标记无理由」，也无「无标记却有理由」）",
           not unpaired24 and any(p[1] for p in paired24),
           f"不配对={unpaired24[:3]} 带标记行数={sum(1 for p in paired24 if p[1])}")

        # 行 17（2026-09-27 改）：守卫拒绝路径**不得留孤儿产物**。
        # 旧序是"先按字节复制 `--result-file`、后守卫"
        # ⇒ 被拒后 `runs/<id>/` 多一份产物、
        # 而账本行仍是 `running`（两边互相矛盾）。反证 = **拒前/拒后目录清单逐项相等**。
        def _uc24_listing(rid: str) -> list[str]:
            d = tmp / "runs" / rid
            if not d.is_dir():
                return []
            return sorted(str(p.relative_to(d)) for p in d.rglob("*"))

        report24 = tmp / "uc24-rejected.report.md"
        report24.write_bytes("| 列 | 值 |\n| a | b |\n".encode("utf-8"))
        seen24: dict[str, list[str]] = {}
        proc24d, row24d = _uc24_loop(
            "run-uc24-orphan", ["--result-file", str(report24)], "reject",
            probe=lambda rid: seen24.__setitem__(rid, _uc24_listing(rid)))
        rid24d = str(row24d.get("run_id") or "")
        out24d = proc24d.stdout + proc24d.stderr
        ok("UC-24 反向对照④（行 17）前置：该轮**确实是守卫拒绝**"
           "（FINISH-ERROR + zero_duration）",
           proc24d.returncode != 0 and "FINISH-ERROR" in out24d
           and "zero_duration" in out24d,
           f"rc={proc24d.returncode} out={out24d.strip()[:56]}")
        ok("UC-24 反向对照④（行 17）：被拒后 `runs/<id>/` **不得新增产物**"
           "（拒前清单 == 拒后清单 == 空；账本行仍是 running）",
           seen24.get(rid24d) == [] and _uc24_listing(rid24d) == []
           and row24d.get("status") == "running",
           f"runs/{rid24d}/ 拒前={seen24.get(rid24d)} 拒后={_uc24_listing(rid24d)}"
           f" status={row24d.get('status')!r}")
        proc24c, row24c = _uc24_loop("run-uc24-short",
                                     ["--allow-degenerate",
                                      "--degenerate-reason", "太短"], "reject")
        out24c = proc24c.stdout + proc24c.stderr
        ok("UC-24 反向对照③：flag + 理由 <10 字符 → **仍拒**（FINISH-ERROR）",
           proc24c.returncode != 0 and "FINISH-ERROR" in out24c
           and "10" in out24c,
           f"rc={proc24c.returncode} out={out24c.strip()[:64]}")
        ok("UC-24 反向对照③：仍拒 = 账本未动（该 run 仍 running）",
           row24c.get("status") == "running" and not row24c.get("ended_at"),
           f"status={row24c.get('status')!r} ended_at={row24c.get('ended_at')!r}")

        # UC-25（复盘行 19）：**受控撤回**——误登记 run 的唯一合法删除路径。
        # 病根：账本原先只能加不能减（手改被 UC-7 的完整性校验拒；`set-started-at` 回填
        # 时间戳 = 伪造测量值，父代理已否决）
        # ⇒ 误登记永久污染判定域（实例：探针 `097`~`099`）。
        # 判据四条，缺一条就不是受控撤回：理由 ≥10 字符 / 留痕 / 只认显式点名的单条 id /
        # `--evidence` 必须存在；产物移入隔离区（删行不销毁现场）。
        rid25 = "run-uc25-misregistered"

        def _uc25_files(d: Path) -> list[str]:
            if not d.is_dir():
                return []
            return sorted(str(p.relative_to(d)) for p in d.rglob("*"))

        def _uc25_row(rid: str) -> dict | None:
            data = json.loads(registry.read_text(encoding="utf-8"))
            return next((x for x in data["runs"] if x["run_id"] == rid), None)

        def _uc25_retr() -> list[dict]:
            data = json.loads(registry.read_text(encoding="utf-8"))
            return data.get("retractions") or []

        run(["register", "--role", "impact-assessment", "--task", "uc25-misregistered",
             "--spec", "impact-assessment@1.4.4", "--run-id", rid25],
            base_env, check=True)
        run(["update", rid25, "--status", "running"], base_env, check=True)
        rep25 = tmp / "uc25.report.md"
        rep25.write_bytes("| 探针产物 | 内容 |\n| 097 | 误登记样本 |\n".encode("utf-8"))
        run(["finish", rid25, "--status", "succeeded", "--output-chars", "10",
             "--result-file", str(rep25), *DEGEN_FIXTURE_ARGS], base_env, check=True)
        dir25 = tmp / "runs" / rid25
        ok("UC-25 前置：该 run 已登记为终态、产物已落 `runs/<id>/`"
           "（撤回的判据必须真的被触发，否则不作数）",
           dir25.is_dir() and bool(_uc25_files(dir25)),
           f"runs/{rid25}/={_uc25_files(dir25)}")

        reason25 = "探针误写入生产账本（UC-25 夹具）：正确形态是隔离账本"
        for tag, argv25, want in (
            ("通配/批量 id", ["run-uc25-*", "--reason", reason25,
                              "--evidence", str(rep25)], "RETRACT-ERROR"),
            ("过短理由", [rid25, "--reason", "太短", "--evidence", str(rep25)],
             "RETRACT-ERROR"),
            ("证据路径不存在", [rid25, "--reason", reason25,
                                "--evidence", str(tmp / "no-such-evidence.md")],
             "RETRACT-ERROR"),
            ("账本里不存在的 run", ["run-uc25-not-registered", "--reason", reason25,
                                    "--evidence", str(rep25)], "不存在"),
        ):
            r = run(["retract", *argv25], base_env, raw=True)
            blob25 = r.stdout + r.stderr
            ok(f"UC-25 反向对照：{tag} → 拒绝且**账本未动 / 产物未动**",
               r.returncode != 0 and want in blob25
               and _uc25_row(rid25) is not None and _uc25_retr() == []
               and dir25.is_dir(),
               f"rc={r.returncode} out={blob25.strip()[:56]}")

        r = run(["retract", rid25, "--reason", reason25,
                 "--evidence", str(rep25)], base_env, raw=True)
        ok("UC-25 正向：理由齐全 + 证据存在 + 显式点名 → 撤回成功（rc=0）",
           r.returncode == 0,
           f"rc={r.returncode} out={(r.stdout + r.stderr).strip()[:56]}")
        ok("UC-25 正向：账本行已删、**留痕**在 `retractions[]`"
           "（run_id/reason/evidence/at/by/"
           "status_at_retraction/quarantine 七字段齐）",
           _uc25_row(rid25) is None and len(_uc25_retr()) == 1
           and not [k for k, v in _uc25_retr()[0].items()
                    if not str(v or "").strip()]
           and set(_uc25_retr()[0]) >= {"at", "by", "run_id", "reason", "evidence",
                                        "status_at_retraction", "quarantine"}
           and _uc25_retr()[0]["reason"] == reason25
           and _uc25_retr()[0]["evidence"] == str(rep25),
           f"retractions={_uc25_retr()}")
        q25 = tmp / str(_uc25_retr()[0].get("quarantine") or "")
        moved25 = q25 / "impact-assessment.report.md"
        same_bytes25 = moved25.is_file() and moved25.read_bytes() == rep25.read_bytes()
        ok("UC-25 正向：产物**移入隔离区**"
           "（`runs/<id>/` 不再有它，隔离区拿到逐字节相同的报告）",
           not dir25.exists() and q25.is_dir() and same_bytes25,
           f"quarantine={q25} 报告字节一致={same_bytes25}")
        r = run(["retract", rid25, "--reason", reason25, "--evidence", str(rep25)],
                base_env, raw=True)
        ok("UC-25 反向对照：同一 run 再撤回一次 → 拒绝（不重复留痕、不做假痕）",
           r.returncode != 0 and "已撤回" in (r.stdout + r.stderr)
           and len(_uc25_retr()) == 1,
           f"rc={r.returncode} retractions={len(_uc25_retr())}")

        # 引用链保护：被其余 run 的 `scope_source` 引用的 run 不得撤回
        # （删了它，引用者的 C2 判据会指向不存在的对象 = 把误登记换成真缺陷）。
        run(["register", "--role", "impact-assessment", "--task", "uc25-cited",
             "--spec", "impact-assessment@1.4.4", "--run-id", "run-uc25-cited"],
            base_env, check=True)
        run(["update", "run-uc25-cited", "--status", "running"], base_env, check=True)
        run(["finish", "run-uc25-cited", "--status", "succeeded",
             "--output-chars", "10",
             *DEGEN_FIXTURE_ARGS], base_env, check=True)
        run(["register", "--role", "code-review", "--task", "uc25-citer",
             "--spec", "code-review@1.0.0", "--run-id", "run-uc25-citer",
             "--scope-source", "impact-assessment:run-uc25-cited"],
            base_env, check=True)
        ok("UC-25 前置：账本里确有 run 的 scope_source 引用了待撤回者",
           "impact-assessment:run-uc25-cited"
           in json.dumps(_uc25_row("run-uc25-citer") or {}, ensure_ascii=False),
           f"citer={_uc25_row('run-uc25-citer')}")
        r = run(["retract", "run-uc25-cited", "--reason", reason25,
                 "--evidence", str(rep25)],
                base_env, raw=True)
        ok("UC-25 反向对照：被 `scope_source` 引用的 run → 拒绝撤回"
           "（引用链不得被撤回打断）",
           r.returncode != 0 and "引用" in (r.stdout + r.stderr)
           and _uc25_row("run-uc25-cited") is not None,
           f"rc={r.returncode} out={(r.stdout + r.stderr).strip()[:56]}")

        # UC-7：手改 registry → CLI 下一次写入拒绝
        data = json.loads(registry.read_text(encoding="utf-8"))
        data["runs"][0]["output_chars"] = 999999  # 手改
        registry.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        r = run(["register", "--role", "code-review", "--task", "x", "--spec", "code-review@1.0.0"], base_env)
        ok("UC-7 防双写", r.returncode != 0 and "完整性校验" in (r.stdout + r.stderr),
           (r.stdout + r.stderr).strip()[:80])

        # F1 收尾断言：整轮跑完，
        # 仓库的 spec 目录**一个探针文件都没有**（且内容与运行前逐字节相同）。
        # 判据取"文件系统事实"，不是"我记得 unlink 过"——旧实现正是靠这句记忆，
        # 而它在并行下不成立。
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
