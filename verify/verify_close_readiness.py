"""TG-15：关闭前置闸门（offline）——**三条不变式 + 数据驱动**，替换原先的按角色硬编码判据。

历史（为什么改）：
TG-11 ③b 版本把判据写成"按角色名逐条判断"——`CLOSE_ROLES` 写死 4 个角色、
二查必须含 `windows`/`main`、
〇查必须早于二查……**每加一个步骤/角色/分支都要改这个文件**，
而"改代码"本身没有任何闸门在守（`TG-15` 卡的起因）。TG-15 之后：

    C1 声明完备：**本次关闭窗口内**凡产出评审结论的 run 必须有 scope 声明
                 （外部引用 或 自选理由，且理由长度 ≥
                 `agents/policy.json::scope_min_deviation_chars`）；
                 窗口起点取自**账本侧**（`ledger_close_window`），
                 窗口之前的 run 属历史、不产生问题
    C2 指涉可核：任何外部引用必须解析到"存在且可用"的对象；
    运行数据里的每个 role 必须能落到 spec
    C3 覆盖闭环：`git rev-list <锚点>..<HEAD>` 的**每个提交**必须有归属

需求来源（**只有两个**，本文件不再有角色名单）：

    agents/fanout.json :: sprint_close_pipeline   →
    哪些关闭步骤/role/target 必填（`close_ledger`/`close_targets`）
    agents/functions/<role>.md frontmatter        → `scope_required`（谁必须声明 scope）
    、`coverage_window`
    agents/policy.json                            → 阈值与开关（偏离理由长度、
    覆盖例外表路径、doc-only 规则）

C3-T 例外表（用户 2026-09-23 选型 + 对"表过期"的担心）：覆盖**默认由 run 数据计算**
（run 自动记录的 `coverage_anchor`/`covers_through`），例外表**只登记例外**、sha 钉死；
**表落后 = 默认 FAIL 并逐条点名未归属 sha**（失效方向反转：不静默变绿）。

用法：
    .venv\\Scripts\\python.exe
    verify\\verify_close_readiness.py                    # 自检（合成 fixture，
    含反向对照）
    .venv\\Scripts\\python.exe verify\\verify_close_readiness.py --sprint <文件>     # 真数据（关闭时）
    .venv\\Scripts\\python.exe verify\\verify_close_readiness.py --sprint <文件> --no-coverage
                                                                                  # 覆盖
                                                                                  # 检查
                                                                                  需 git
                                                                                  历史，
                                                                                  CI
                                                                                  可关

**为什么默认只跑自检**：Sprint 未关闭时真数据模式必然 FAIL（正确的 fail-closed 语义），
但会让 offline 套件长期变红。故套件跑自检；
关闭时由主代理跑 `--sprint` 并把输出写进 Sprint §9。

§9 结构化 run 表格式（供本脚本解析，`1-WORKFLOW.MD` §4.2）：
    | run_id | role | target | scope_source | coverage | deviation |

**窗口起点必须有上界**（2026-09-25 独立复核 finding 2，major）：窗口起点 = 作用域步骤
（`close_gate.scope_ref_step`）最新 run 的 `started_at`，但"最新"**不再无条件成立**——
未来时间戳、晚于整条流水线、被更早的 run 引用，三条任一成立即**具名报问题并弃用该起点**
（判定域退回全域 = 宁可多报，不静默收窄）。见 `scope_window_problems`：窗口是 C1 与 §9
linkage 的判定域，**定义判定域的东西必须自己受判**——否则"追加一条更晚的作用域 run"就能
把当期缺口挤出检查范围。

**机读证据行**（TG-6：只在**成功路径**打印，失败/SKIP 不打印）：
`EVIDENCE: verify_close_readiness.py assertions=N rc=0`（自检模式 N = 实跑的 `ok()
` 断言数；
real-data 模式 N = 实际执行过的判据条数，由各判据自身登记）。

**退出码**：0=通过；1=检出违规/自检断言未通过（逐条点名）；2=fail-closed 无法判定
（Sprint 文档不存在、政策/覆盖例外表非法，或**断言被 `-O`/`PYTHONOPTIMIZE=1` 剥离**）；
**4=domain-unavailable**（M-A，`TG-19`）：**判定域无法由被判定物派生**——
Sprint 身份推不出、该 Sprint 在账本里没有作用域 run、或窗口被次序判据弃用。
退出码 4 时**不产出判定结论**：findings 即使上屏也只作**诊断**
（前面有 `[domain-fallback]` 标记），不得被当成"本期有几项不合格"。
"""

from __future__ import annotations
VERIFY_META = {'features': 'TG-15 关闭前置闸门：C1 声明完备 / C2 指涉可核（含 A-M13 的"全账本 role 必有 spec"封闭世界）/ C3 覆盖闭环（锚点→域右端每提交有归属），需求全来自 fanout.json + spec frontmatter；含变异用例自 fanout 自动生成的反向对照；M-A（TG-19）：判定域必须由**被判定物**派生（Sprint 身份 + 该 Sprint 的作用域 run + 该 Sprint 的最后一条覆盖 run 作右端），域不可派生时退出码 4（domain-unavailable）且不产出结论；A-M13④：§9 在飞宽限内只提示不判（口径同 ledger_measurement.in_flight）', 'tier': 'offline', 'providers': [], 'est_seconds': 15, 'est_cost_cny': 0, 'routes': [], 'requires': ['none']}

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import (  # noqa: E402
    ENV_POLICY,
    Attribution,
    PolicyError,
    _is_ancestor,
    attribution,
    coverage_windows_from_runs,
    head_sha,
    load_coverage_exceptions,
    load_policy,
    parse_frontmatter,
)
from verify.agent_policy import Policy as AgentPolicy  # noqa: E402  （类型注解用；避免与下方局部名冲突）

# `-O` / `PYTHONOPTIMIZE=1` 下 `assert` 被**整条剥离**：判据不会执行，
# 而输出仍然像"跑过了"。
# 两道防线：① 这一层直接拒绝在断言被剥离时给出结论（fail-closed，退出码 2）；② `ok()
# ` 内部
# 不再用裸 `assert`。① 保证没人能拿"静默空转"的运行当证据，
# ② 保证单条判据即使被别处调用也咬得住。
if not __debug__:  # pragma: no cover —— 只在 -O/PYTHONOPTIMIZE 下触发
    print("CLOSE-READINESS-ERROR: 断言被剥离（python -O / PYTHONOPTIMIZE=1）⇒ 本闸门的判据不会执行，"
          "拒绝输出任何结论（fail-closed，退出码 2）。请用不带 -O 的解释器运行："
          ".venv\\Scripts\\python.exe verify\\verify_close_readiness.py", file=sys.stderr)
    raise SystemExit(2)

ROW_SPLIT = re.compile(r"(?<!\\)\|")
ANCHOR_RE = re.compile(r"\**三查锚点\**\s*[:：]\s*`?([0-9a-fA-F]{7,40})`?")
TABLE_HEADER = "| run_id | role | target | scope_source | coverage | deviation |"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0
CRITERIA_EXECUTED = 0
# M-A（TG-19）：判定域无法由被判定物派生时的**专属退出码**——
# 它必须与"检出违规(1)"和"无法判定(2)"区分开：前者问"本期有几项不合格"，
# 本码的含义是"**本轮没有产生任何判定**"。
DOMAIN_UNAVAILABLE_EXIT = 4
# M-B（`TG-19` 反空转不变式）：本轮**是否走了 SKIP 档**。SKIP 不是成功 ⇒
# 不打印机读证据行（`EVIDENCE:` 只属于"判据真的跑过且通过"），见 `main()`。
_RUN_STATE: dict[str, bool] = {"skipped": False}


def ok(name: str, cond: bool, detail: str = "") -> None:
    """断言一条判据。**不用裸 `assert`**（`-O` 会把裸 assert 整条删掉，判据静默消失）。"""
    global PASSED
    if not cond:
        raise AssertionError(f"{name} FAIL: {detail}")
    PASSED += 1
    print(f"PASS: {name} {detail}")


def _criterion() -> None:
    """登记"这条判据真的执行过"。

    real-data 模式不做 `ok()` 自检断言（它把问题列成清单逐条打印），故 `EVIDENCE:` 行的
    `assertions=` 只能由判据自身登记——手写常量会随判据增删漂移，而"漂移的读数"正是本仓
    反复出现的教训。判据函数每次被调用即登记一次（自检里会被调用很多次，故自检模式用的是
    `PASSED`，两种模式各自如实）。
    """
    global CRITERIA_EXECUTED
    CRITERIA_EXECUTED += 1


def warn(name: str, detail: str = "") -> None:
    print(f"WARN: {name} {detail}")


def registry_path() -> Path:
    base = Path(os.environ.get("AGENT_OPS_DIR", str(ROOT / "agents")))
    return base / "runtime" / "registry.json"


def load_runs(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("runs", [])


def parse_sprint(doc: str) -> dict:
    """解析 §9 结构化 run 表 + 三查锚点（容错：表格列数 ≥5 且首列以 run- 开头）。

    N9②（2026-09-25 独立复核实测）：原实现要求 `line.startswith("|")`，
    于是**缩进的表格行被静默丢弃**——行首留缩进是合法 Markdown
    （表格块可以缩在列表项/引用里），"§9 里明明登记了这一行"与
    "闸门看到的表里没有它"会同时成立：被校验方无法靠写文档满足判据，
    闸门也不给原因。现按 `line.lstrip()` 判首字符。

    **仍然结构非法**的 run 行（首列是 `run-…` 但列数 <5，例如缺尾管道 /
    少了整列）不再静默丢，而是收进 `malformed` 由 `check_linkage` 点名
    ——"丢行"正是 N8 一族（空集/缺失 = PASS）的形态：丢了它就等于没登记，
    而"没登记"必须由闸门说出来，不能靠人猜。
    """
    rows: list[dict] = []
    malformed: list[dict] = []
    for lineno, raw in enumerate(doc.splitlines(), 1):
        line = raw.lstrip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in ROW_SPLIT.split(line)[1:-1]]
        if not cells or not cells[0].startswith("run-"):
            continue  # 表头 / 分隔行 / 占位行（首列不是 run-…）→ 本就不是 run 行
        if len(cells) < 5:
            malformed.append({"line": lineno, "cells": len(cells), "text": raw.strip()})
            continue
        rows.append({
            "run_id": cells[0], "role": cells[1], "target": cells[2],
            "scope_source": cells[3], "coverage": cells[4],
            "deviation": cells[5] if len(cells) > 5 else "",
        })
    m = ANCHOR_RE.search(doc)
    return {"rows": rows, "malformed": malformed, "anchor": m.group(1) if m else None}


def _spec_of(policy: AgentPolicy, role: str) -> dict:
    spec = policy.specs.get(role)
    return parse_frontmatter(spec.path) if spec else {}


def exact_target(run: dict) -> str:
    """run 声明的 target（= `task_id`），**精确**取值口径（N3）。

    N3（2026-09-25 二查）实测：判据原是 `target in task_id` 的**子串**匹配，于是
    `branch:windows-backup`、`OLD-working-tree-JUNK`、`branch:mainline` **全部 PASS**——
    "只要包含就算满足"让 target 失去判据意义（一个被改名的分支 / 一个被拼接的旧目录名
    都能冒充关闭要件）。现改为**精确相等**：target 是声明值，不是模式。
    """
    return str(run.get("task_id") or "").strip()


def _ts(value: object) -> datetime | None:
    """账本时间戳 → **带时区**的 `datetime`（解析不了 → `None`，不猜）。

    为什么不用纯字典序（本模块其他地方的既有口径）：字典序只在"全部带同一个 `+00:00` 偏移"
    时才等于时间序，而"未来时间戳"这条判据要拿它跟 `now()` 比——混入别的偏移就会比错方向。
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _before(earlier: str, later: str) -> bool:
    """`earlier` 是否严格早于 `later`（能解析就按时刻比，解析不了退回字典序）。"""
    left, right = _ts(earlier), _ts(later)
    if left is not None and right is not None:
        return left < right
    return earlier < later


def close_step_order(policy: AgentPolicy) -> tuple[str, int, set[str], set[str]]:
    """从**数据**取关闭步骤的次序：`(作用域步骤名, 它的 order, 它的 role 集, 后续步骤的 role 集)`。

    真源 = `policy.close_ledger_steps`（由 `fanout.json::
    sprint_close_pipeline` 的 `order` 排序而来）
    ——本文件里**没有**角色名单、没有步骤名常量。作用域步骤缺席（政策拼错）时由
    `Policy.close_gate` 在装载期就 fail-closed，这里只做防御性返回。
    """
    wanted = str(policy.close_gate.get("scope_ref_step") or "").strip()
    scope_steps = [s for s in policy.close_ledger_steps if s.step == wanted]
    if not scope_steps:
        return wanted, -1, set(), set()
    order = min(s.order for s in scope_steps)
    scope_roles = {s.role for s in scope_steps}
    later_roles = {s.role for s in policy.close_ledger_steps if s.order > order} - scope_roles
    return wanted, order, scope_roles, later_roles


SPRINT_ID_RE = re.compile(r"[Ss]print[-\s]?0*(\d+)")


def _norm_sprint(value: object) -> str | None:
    """把 Sprint 标识归一成**纯编号字符串**。

    例：`"Sprint-18"` / `"18"` / `"018"` → `"18"`。
    """
    text = str(value or "").strip()
    if not text:
        return None
    m = SPRINT_ID_RE.search(text)
    if m is None:
        m = re.fullmatch(r"0*(\d+)", text)
    return m.group(1) if m else None


def sprint_identity_of_doc(path: Path | str) -> str | None:
    """**被判定物**（Sprint 文档）自带的 Sprint 身份（M-A：域必须由被判定物派生）。

    取文件名里的 `sprint-<N>`（本仓一律如此命名，如 `2026-09-21-sprint-17.md`）；
    文件名给不出身份 → `None`（调用方 fail-closed 报 `domain-unavailable`，**不猜**）。
    """
    return _norm_sprint(Path(path).stem)


def run_sprint_identity(run: dict) -> str | None:
    """账本 run 的 Sprint 身份：优先**显式字段** `sprint`（`register --sprint` 写入），
    否则从 `task_id` 派生（legacy 兼容：本仓历史关闭 run 的 `task_id`
    一律含 `Sprint-<N>`）。

    派生不出 → `None`。这类 run **不得被当成"别的 Sprint"排除**（那等于静默丢数据），
    调用方按 fail-closed **保留**它们，并把条数上屏。
    """
    explicit = _norm_sprint(run.get("sprint"))
    return explicit if explicit else _norm_sprint(run.get("task_id"))


def domain_runs(runs: list[dict], sprint_id: str | None) -> tuple[list[dict], int]:
    """本次判定的**域** = `(域内 run, 身份不可派生的 run 条数)`。

    `sprint_id is None` ⇒ 返回全部（调用方在此之前已按 `domain-unavailable` 收口，
    这里只做防御性返回）。身份不可派生的 run **保留**（fail-closed：宁多勿少），
    但**计数上屏**，避免把"收窄"做成静默动作。
    """
    if sprint_id is None:
        return list(runs), 0
    kept: list[dict] = []
    unknown = 0
    for r in runs:
        ident = run_sprint_identity(r)
        if ident is None:
            unknown += 1
            kept.append(r)
        elif ident == sprint_id:
            kept.append(r)
    return kept, unknown


def _contributes_coverage(policy: AgentPolicy | None, run: dict) -> bool:
    """该 run 是否**承担内容覆盖**——只有承担者才有资格界定域右端（M-A）。

    实测事故（2026-09-25，`A-M13` 的 `implementation` 首跑）：`coverage_window: none` 的 run
    在 `finish` 时会自动记下 `covers_through = 登记时 HEAD` ⇒ 那是一个**空窗口**，却因为
    "域内最新一条"把 G2 的域右端拉到它自己那一刻。**空窗口不是覆盖声明，不能当边界用**。

    三类排除（都是数据驱动）：
      * `produced_only: true`（已如实标注为"不承担内容覆盖"）；
      * spec 声明 `coverage_window: none`（实现类等）；
      * **作用域类 role**（`close_gate.scope_ref_step` 那一步的 role）：按 B3 语义它只在
        T0 界定本次关闭覆盖哪些变更，本身不承担内容覆盖。
    """
    if run.get("produced_only") is True:
        return False
    if policy is None:
        return True
    role = str(run.get("role") or "")
    if str(_spec_of(policy, role).get("coverage_window") or "").strip() == "none":
        return False
    _step, _order, scope_roles, _later = close_step_order(policy)
    return role not in scope_roles


def domain_right_boundary(
        runs: list[dict], *,
        policy: AgentPolicy | None = None,
        root: Path | None = None) -> tuple[str | None, str | None, list[str]]:
    """域的**右端** = `(sha, 定义它的 run_id, 具名问题)`：域内**覆盖最远**那条 run 的
    `covers_through`。

    为什么右端必须取自域内（M-A 的第二半，2026-09-25 实测）：
    C3 的判据是"锚点→HEAD 每个提交有归属"，而 `HEAD` 是**移动靶** ⇒ 下一个 Sprint 的提交
    会掉进本 Sprint 的判据里（G2 开工当天的提交就会被算成 Sprint-17 的"未归属提交"）。
    域既然由被判定物派生，右端就必须由**该 Sprint 自己的记录**界定。

    **按覆盖远近，不按登记时间**（2026-09-25 独立复核 `run-…083` major）：
    原实现取"`started_at` 最新那条" ⇒ **后登记一条覆盖更少的 run** 就能把 C3 的判定域
    静默缩小（`_contributes_coverage` 只保证"它承担覆盖"，不保证"它覆盖得更远"）。
    现按**祖先关系**取最远者：`X` 更远 ⇔ `X.covers_through` 是
    `Y.covers_through` 的后代；
    **不可比（分叉）⇒ 具名问题**（fail-closed，不猜谁更远）。
    `root is None`（夹具/无 git）⇒ 退回"登记时间最新"并**在问题里点名该口径**，
    自检仍可跑。
    """
    cands: list[dict] = []
    for r in runs:
        if not _contributes_coverage(policy, r):
            continue
        if re.fullmatch(r"[0-9a-fA-F]{40}", str(r.get("covers_through") or "").strip()):
            cands.append(r)
    if not cands:
        return None, None, []
    if root is None:
        latest = max(cands, key=lambda r: str(r.get("started_at") or ""))
        return (str(latest["covers_through"]), str(latest.get("run_id") or "?"),
                ["[域右端] 无 git 根可比（夹具模式）⇒ 按**登记时间最新**取右端；"
                 "真数据模式会做祖先比较"])
    best = cands[0]
    problems: list[str] = []
    for cand in cands[1:]:
        a = str(best["covers_through"])
        b = str(cand["covers_through"])
        if a == b:
            continue
        if _is_ancestor(root, a, b):
            best = cand
        elif not _is_ancestor(root, b, a):
            problems.append(
                f"[域右端] {best.get('run_id')} 的 covers_through {a[:10]} 与 "
                f"{cand.get('run_id')} 的 {b[:10]} **不可比**（互不为祖先）"
                f"⇒ 域右端无法判定"
                f"（fail-closed：不猜哪个更远；查这两条 run 是否分属不同血统）")
    return str(best["covers_through"]), str(best.get("run_id") or "?"), problems


def scope_step_runs(policy: AgentPolicy, runs: list[dict], *,
                    sprint_id: str | None = None) -> list[dict]:
    """作用域步骤的**全部候选 run**（role + target 过滤，target 口径同 N3：精确匹配）。

    `sprint_id` 非空时**再按 Sprint 身份过滤**（M-A）：作用域 run 必须属于**被判定物**
    那个 Sprint——这是"跨 Sprint 窗口翻转"（G2 kickoff 〇查一登记就把 Sprint-17 的窗口
    顶掉）的根治点。身份不可派生的 run **保留**（fail-closed）。
    """
    wanted_step = str(policy.close_gate.get("scope_ref_step") or "").strip()
    if not wanted_step:
        return []
    candidates: list[dict] = []
    for step in policy.close_ledger_steps:
        if step.step != wanted_step:
            continue
        bucket = [r for r in runs if str(r.get("role") or "") == step.role]
        if step.targets:
            wanted_targets = set(step.targets)
            bucket = [r for r in bucket if exact_target(r) in wanted_targets]
        candidates += bucket
    if sprint_id is not None:
        # 显式身份**优先于**无身份：有"本 Sprint"的候选时，绝不把无身份的 run 混进来
        # （否则一条 task_id 为空的历史 run 会冒充本期作用域 run——实测：run-…-065
        # 的 `task_id` 为空，曾把 Sprint-16 的窗口判成不可用）。只有当**一个带身份的
        # 候选都没有**时，才回退到无身份候选（fail-closed：宁可算进来，也不要"因为
        # 没写身份就当作本期没跑过"）。
        identified = [r for r in candidates if run_sprint_identity(r) == sprint_id]
        if identified:
            return identified
        return [r for r in candidates if run_sprint_identity(r) is None]
    return candidates


def scope_window_problems(policy: AgentPolicy, runs: list[dict], candidate: dict, *,
                          sprint_id: str | None = None) -> list[str]:
    """候选作用域 run 能否当"本次关闭的起点"——**次序/时序**判据，违反即返回**具名问题**。

    为什么必须有上界（2026-09-25 独立复核 finding 2，major）：
    原实现取"作用域步骤**最新**的
    那条 run"且**没有上界**，于是往账本里追加一条更晚的作用域 run，
    窗口起点就被抬到它那一刻
    ⇒ 本次关闭的全部流水线 run 落到窗口之外 ⇒ C1 与 §9 linkage **静默失明**（实测：
    追加一条
    `2026-09-25T04:30` 的 run 后，同一份"漏登记最早一行"的 §9 从 FAIL 2 项变成 PASS 0 项；
    `2099-01-01` 也被照单全收）。**判定域被谁定义，就必须由谁守。**

    三条判据（全部 **fail-closed**：报问题 + **弃用该窗口**，退回家域 = 宁可多报）：

      ① **不得在未来**：`started_at > now()` 的时间戳把全部当期 run 挤出窗口，
      等价静默放行；
      ② **不得晚于整条流水线**：候选晚于**全部**后续步骤 run（且这些 run 确实存在）
      ⇒ 它不可能
         是"本次关闭的起点"——它之前流水线已经跑完，之后一条都没有。次序由数据给（步骤
         `order` + role），不是写死的角色名；
      ③ **引用它的 run 不得比它更早**：`scope_source` 引用了候选 run 的后续步骤 run，其
         `started_at` 早于被引用者 ⇒ 引用不可能成立（数据被改过），窗口不可采信。

    ②的口径说明（**与复核建议的字面口径有一处有意分歧，已标注**）：
    字面上"晚于任何后续步骤
    的**最早** run 即违规"在本仓数据上**恒真**——窗口的全部意义就是把**上一个 Sprint** 的
    后续步骤 run 排除在外（真数据里它们在窗口起点之前有几十条），故那条字面判据会把正常
    收窄判成违规、并让窗口退回全域（C1 立刻多出 34 条历史噪音，正是 D1 要治的失效）。
    本实现取"**不得晚于整条流水线**"：它精确命中复核的注入形态（追加一条更晚的 run 后，
    后续步骤 run 全部落在它之前、之后一条没有），
    而在真数据上零误报（当期 run 都在它之后）。
    """
    problems: list[str] = []
    rid = str(candidate.get("run_id") or "?")
    started = str(candidate.get("started_at") or "")
    started_dt = _ts(started)
    if started_dt is None:
        problems.append(f"[窗口] 作用域 run {rid} 的 started_at={started!r} 无法解析成时间戳 ⇒ "
                        f"起点不可推导（不猜；判定域退回全域，宁可多报也不静默收窄）")
        return problems
    now = datetime.now(timezone.utc)
    if started_dt > now:
        problems.append(
            f"[窗口/未来] 作用域 run {rid} 的 started_at={started} **晚于现在**"
            f"（{now.isoformat(timespec='seconds')}）⇒ 不得作为本次关闭的起点"
            f"（未来时间戳会把全部当期 run 挤出窗口 = 静默放行）")
    _step, _order, _scope_roles, later_roles = close_step_order(policy)
    later = [r for r in runs if str(r.get("role") or "") in later_roles]
    if sprint_id is not None:
        # M-A：次序判据只在**同一 Sprint** 内比较。两类 run 的处理**故意不对称**：
        #   * 候选作用域 run：身份不可派生的**保留**（fail-closed——它可能就是本期的，
        #     排除它等于"换个 task_id 就能让窗口消失"）；
        #   * 比较用的后续步骤 run：身份不可派生的**排除**（它无法被归属到本期的流水线，
        #     留着它会让**每个新 Sprint 的 kickoff 〇查**都被判"晚于整条流水线"——
        #     实测：Sprint-18 的 081 登记后，账本里 34 条历史后续步骤 run 全在它之前，
        #     于是域被判不可用；这不是事故，是新 Sprint 的正常开局）。
        later = [r for r in later if run_sprint_identity(r) == sprint_id]
    earlier = [r for r in later if _before(str(r.get("started_at") or ""), started)]
    after = [r for r in later if _before(started, str(r.get("started_at") or ""))]
    if earlier and not after:
        oldest = min((str(r.get("started_at") or "") for r in earlier))
        problems.append(
            f"[窗口/次序] 作用域步骤 run {rid}（started_at={started}）**晚于后续步骤的全部 run**："
            f"后续步骤 role={sorted(later_roles)} 共 {len(earlier)} 条 run 全在它之前（最早 {oldest}），"
            f"之后一条都没有 ⇒ 它不可能是本次关闭的起点，以它为窗口起点会把整条流水线挤出判定域"
            f"（C1/§9 linkage 静默失明）。窗口弃用 ⇒ 判定域退回全域（宁可多报，不静默收窄）")
    for run in later:
        source = str(run.get("scope_source") or "").strip()
        cited = next((p for p in policy.scope_ref_sources if source.startswith(p)), None)
        if cited is None or source[len(cited):].strip() != rid:
            continue
        if _before(str(run.get("started_at") or ""), started):
            problems.append(
                f"[窗口/次序] {run.get('run_id')} 的 scope_source 引用了作用域 run {rid}，"
                f"但它的 started_at={run.get('started_at')} **早于**被引用者（{started}）⇒ "
                f"引用不可能成立（数据被改过），窗口起点不可采信")
    return problems


def scope_step_run(policy: AgentPolicy, runs: list[dict], *,
                   sprint_id: str | None = None) -> dict | None:
    """本次关闭的**作用域 run** = 作用域步骤
    （`close_gate.scope_ref_step`，本仓 = `scope`）在账本里**最新的**那条 run
    ——**只做筛选，不做次序判定**（次序判定见 `scope_window_problems`）。

    为什么"最新"：关闭流水线的每一步一个 Sprint 只跑一次；同 role 更早的 run
    属于上一个 Sprint 的关闭（本仓实测：`lessons-learned` 的 058 是 **Sprint-16**
    关闭补跑的那条），不应被本 Sprint 的 §9 要求，也不应定义本 Sprint 的窗口。

    **M-A（`TG-19`，2026-09-25）**：`sprint_id` 非空时，"最新"只在**同一 Sprint** 的
    候选里取——原口径是"全账本最新一条"，于是**下一个 Sprint 的 kickoff 〇查一登记，
    上一个 Sprint 的窗口就被顶掉**（实测：Sprint-17 的关闭读数由 1 项变 99 项，其中
    98 项假红）。域由**被判定物**派生，而不是由"账本里最后发生了什么"派生。

    `step.targets` 非空时按 target **精确匹配**过滤（口径同 N3；本仓 `scope` 步无
    targets，故实际不过滤——但判据不能建立在"当前数据刚好没有 targets"上）。
    没有 run、或最新 run 没有 `started_at` → 返回 None（调用方 fail-closed）。
    """
    candidates = scope_step_runs(policy, runs, sprint_id=sprint_id)
    if not candidates:
        return None
    latest = max(candidates, key=lambda r: str(r.get("started_at") or ""))
    return latest if str(latest.get("started_at") or "") else None


def derive_close_window(policy: AgentPolicy, runs: list[dict], *,
                        sprint_id: str | None = None) -> tuple[str | None, list[str]]:
    """窗口起点 + **弃用原因**（`(started_at | None, problems)`）。

    问题非空 ⇒ 起点为 `None`（判定域退回全域，fail-closed）；
    作用域 run 缺席同样返回 `None`
    且**不报问题**（"缺 run"由 `check_requirements` 按 `fanout.json` 逐条点名，两处不重复报）。

    `sprint_id` 非空 ⇒ 候选作用域 run 只在**同一 Sprint** 内挑（M-A），次序判据也只在
    同一 Sprint 内比较；"该 Sprint 根本没有作用域 run"由调用方（`run_real_data`）按
    `domain-unavailable` 收口，本函数仍只负责起点推导。
    """
    _criterion()
    candidate = scope_step_run(policy, runs, sprint_id=sprint_id)
    if candidate is None:
        return None, []
    problems = scope_window_problems(policy, runs, candidate, sprint_id=sprint_id)
    if problems:
        return None, problems
    return str(candidate.get("started_at")), []


def ledger_close_window(policy: AgentPolicy, runs: list[dict]) -> str | None:
    """从**账本侧**推导本次关闭窗口的起点
    = **本次关闭的作用域 run 的 `started_at`**（B1）。

    为什么不能取自 §9 自己（二查实测的绕过路径）：原实现是
    `window_start = min(§9 各行的 started_at)`，
    于是**删掉 §9 里最早的几行**就把窗口整体抬高，
    落在窗口之前、账本里真实存在的 run 全部退出 `scoped` → "账本有 run 但 §9 未登记"一条都不报
    → 闸门 PASS。**被校验的文档不得定义自己的校验窗口。**

    为什么是"本次关闭的作用域 run"，而不是"各必填步骤最新 run 的最小 `started_at`"
    （B1 改前）：
    改前口径取的是**跨步骤**的最小值，于是一个**与本次关闭无关的历史步骤 run**
    就能把窗口拉到它自己那一刻——真数据实测：`lessons-learned` 的 058
    （Sprint-16 关闭补跑的收尾 run）把窗口起点定到 `2026-09-20T17:34:57`，
    而本 Sprint 的作用域 run 是 `2026-09-25T…`
    ⇒ 窗口被拉宽约 4 天，中间的历史 run 被拖进 C1/§9 判定域、当期缺口反而被淹没。
    **"窗口有多宽"必须由"本次关闭从哪一刻开始"决定，而那一刻的定义者只能是作用域
    步骤**——它是关闭流水线的第 1 步
    （`fanout.json::sprint_close_pipeline` 的 `order`），语义就是
    "界定本次关闭覆盖哪些变更"。作用域 run 缺席时**不退回**旧口径：返回 None 让调用方
    fail-closed（不过滤 = 全域），宁可多报也不静默收窄。

    **同一个窗口供两处使用**（一处推导、两处消费，避免两套口径）：
      * `check_linkage`：窗口内每个 close/review role 的 run 必须登记在
        §9 表里（双向比对）；
      * `check_c1`（D1，2026-09-25 用户裁定）：C1 的判定域 = 窗口内的 run；
        窗口之前的历史 run（`TG-11` 之前的记录里根本没有 `scope_source`
        字段，且账本有完整性哈希、不可回填）**不产生问题**——否则真数据上
        恒有 34 条"永久 FAIL"，闸门退化成人人无视的噪音。
        窗口不可推导（返回 None）时**不过滤**（= 全域）：这是 fail-closed
        方向，宁可多报也不静默收窄。

    **收窄不等于放宽**（B1 的反向对照，见自检 B1a/B1b）：窗口内的当期缺口仍逐条 FAIL；
    窗口外**另有**一条独立的兜底判据——`check_requirements` 按 `fanout.json` 的必填步骤
    检查"本次关闭的流水线是否真的跑过"，它**不看窗口**。因此"作用域 run 之后没有跑过
    二查/lessons"这件事不会因为窗口收窄而消失（否则收窄就成了静默放行）。

    比较口径：`started_at` 按**字符串字典序**比较（与 N6 的区间比对同口径）。
    账本写入的时间戳统一带 `+00:00` 偏移时字典序 = 时间序；该前提由账本自身
    保证（`agent-ops register` 用 UTC ISO 串），混入别的偏移会让本函数失去
    意义——故这里不做时区归一化，而是明确记录口径。

    **上界（2026-09-25 独立复核 finding 2）**：本函数只取 `derive_close_window` 的起点；
    候选 run 若违反次序/时序判据（未来时间戳、晚于整条流水线、被更早的 run 引用），
    `derive_close_window` 会**弃用**该起点并返回具名问题（见 `scope_window_problems`），
    本函数随之返回 `None` ⇒ 调用方不过滤（全域）。"取最新一条"**不再是无条件的**。
    """
    return derive_close_window(policy, runs)[0]


# --------------------------------------------------------------------- 判据

def check_requirements(policy: AgentPolicy, runs: list[dict], *,
                       window_start: str | None = None) -> list[str]:
    """需求侧（数据驱动）：关闭流水线的必填步骤 / role / target 是否都真的跑过。

    原先这些判据是 `if role == "code-review": 必须有 windows 和 main` 这样的代码；
    现在**从 `fanout.json` 推导**——加减步骤/分支只改数据。

    `window_start` 非空 ⇒ 只认**窗口内**的 run（M-A）：域是按 Sprint 收窄的，若这里仍
    认全域，一个**身份不可派生的历史 run**（例如多年前的同 role run）就能冒充"本期步骤
    跑过了"——那是把"收窄"做成了"放行"。默认 `None` 保持历史调用口径（自检 fixture 用）。
    """
    _criterion()
    problems: list[str] = []
    if window_start is not None:
        runs = [r for r in runs
                if str(r.get("started_at") or "") >= window_start]
    by_role: dict[str, list[dict]] = {}
    for r in runs:
        by_role.setdefault(str(r.get("role") or ""), []).append(r)

    for step in policy.close_ledger_steps:
        bucket = by_role.get(step.role) or []
        if not bucket:
            problems.append(f"[C1/需求] 关闭流水线步骤 {step.order}:{step.step} 缺 run（role={step.role}）")
            continue
        for target in step.targets:
            if not any(exact_target(r) == target for r in bucket):
                problems.append(
                    f"[C1/需求] 步骤 {step.order}:{step.step} 缺 target={target!r} 的 run"
                    f"（target 判据为**精确匹配**，子串不算；已有 task_id："
                    f"{[str(r.get('task_id')) for r in bucket][:3]}）")

    # 〇查必须先于二查：顺序来自数据（scope_ref_step 指向的第一步 vs 其余步骤），
    # 不是写死的角色名
    ref_step_name = str(policy.close_gate.get("scope_ref_step") or "")
    ref_steps = [s for s in policy.close_ledger_steps if s.step == ref_step_name]
    if ref_steps:
        ref_roles = {s.role for s in ref_steps}
        later_roles = {s.role for s in policy.close_ledger_steps if s.role not in ref_roles}
        early = [str(r.get("started_at") or "") for r in runs if r.get("role") in ref_roles]
        late = [str(r.get("started_at") or "") for r in runs if r.get("role") in later_roles]
        if early and late:
            if not all(early):
                problems.append(f"[C1/需求] {sorted(ref_roles)} 的 run 缺 started_at，无法判定先后")
            elif min(early) >= min(late):
                problems.append(
                    f"[C1/需求] 范围评估步骤（{sorted(ref_roles)}）未早于后续步骤（{sorted(later_roles)}）："
                    f"{min(early)} >= {min(late)}")
    return problems


def check_c1(policy: AgentPolicy, runs: list[dict],
             window_start: str | None = None) -> list[str]:
    """C1 声明完备：**本次关闭窗口内**凡**产出评审结论**的 run
    （spec 声明 `scope_required: true`）必须有 scope 声明，
    且自选理由长度不得低于政策阈值。

    判定域为什么必须收窄（D1，2026-09-25 用户裁定；`TG-17` ② 的落地）：
    原实现遍历**全部**账本 run。真数据实测
    （`--sprint docs/iteration/sprint/2026-09-21-sprint-17.md`）：
    68 条 run 里 34 条被判"无 scope 声明"，而这 34 条**全部**是
    `TG-11` 之前的记录（当时 run 结构里没有 `scope_source` 字段），
    且账本有完整性哈希 ⇒ **不可回填** ⇒ 判据变成"无论怎么填文档都
    FAIL 34 条"的永久噪音：闸门长期红着，人就不再看它，同一屏里真正的
    当期缺口也跟着失效（"狼来了"式失效，TG-17 ② 的原话）。
    现判定域 = 窗口内（窗口起点取自**账本侧**，见 `ledger_close_window`），
    窗口之前的历史 run 不卷入。

    **窗口必须来自账本、不能来自被校验的 §9**：否则"把 §9 写窄一点"
    就能把当期缺口挤出判定域，收窄就从"去噪"变成"静默放行"。
    窗口不可推导时 `window_start is None` → **不过滤**（fail-closed）。

    `scope_min_deviation_chars`（N9③）：此前该政策值**只在 fixture 里
    出现**、真判据从不执行 ⇒ "`--deviation` 写 1 个字"能过闸门，而
    `agent-ops register` 会当场拒绝它——"登记时验得过、闸门读不到"
    正是 TG-15 要消灭的两套口径。现两侧同源（都由政策提供阈值）。

    **阈值的适用面与 `register` 逐字对齐**：长度下限只在**自选范围**
    （`scope_source == "self-chosen"`，或来源为空而只给了 deviation
    ——`register` 落库时正是把它写成 `self-chosen`）这条路径上执行；
    来源是合法引用（`impact-assessment:<run_id>`）时 deviation 只是
    附注，`register` 不校验其长度，闸门**也不得**改判（否则会出现
    "登记合法、闸门判红"的假红——与"读得到就该验得过"同源）。
    """
    problems: list[str] = []
    min_chars = policy.scope_min_deviation_chars
    domain = ("全域（窗口不可推导）" if window_start is None
              else f"本次关闭窗口 started_at >= {window_start}")
    for r in runs:
        role = str(r.get("role") or "")
        if role not in policy.review_roles:
            continue
        started = str(r.get("started_at") or "")
        # 窗口之前的 run = 历史（不产生问题）。注意 `started_at` 缺失时**不豁免**：
        # 无法定位就先按当期判（fail-closed），不拿"字段缺失"换免检。
        if window_start is not None and started and started < window_start:
            continue
        source = str(r.get("scope_source") or "").strip()
        deviation = str(r.get("scope_deviation") or "").strip()
        rid = r.get("run_id")
        # `register` 把"无名来源 + 给了理由"落库为 `self-chosen`，故两者同属自选范围路径
        self_chosen = source == "self-chosen" or (not source and bool(deviation))
        if not source and not deviation:
            problems.append(f"[C1] {rid}（role={role}）产出评审结论但未声明 "
                            f"scope 来源，也无自选范围理由（判定域：{domain}）")
        elif self_chosen and not deviation:
            problems.append(f"[C1] {rid} 自选范围但未声明 deviation"
                            f"（判定域：{domain}）")
        elif self_chosen and len(deviation) < min_chars:
            problems.append(f"[C1] {rid}（role={role}）的 scope_deviation 仅 "
                            f"{len(deviation)} 字符，低于政策 "
                            f"scope_min_deviation_chars={min_chars} ⇒ 不构成"
                            f"可核范围理由（同一阈值由 agent-ops register "
                            f"执行；判定域：{domain}）")
    return problems


def check_c2(policy: AgentPolicy, runs: list[dict], *,
             ledger: list[dict] | None = None) -> list[str]:
    """C2 指涉可核：外部引用解析到"存在且可用"的对象；
    运行数据 role 必须能落到 spec（不认角色名）。

    `ledger` 非空 ⇒ "引用对象**是否存在**"按**全账本**判定（M-A）：
    判定域是按 Sprint 收窄的，而被引用的对象天然可能属于上一个 Sprint
    （本期 〇查完全可以沿用上一期的 scope 承担者）。
    拿域内名单查存在性，会把**合法的跨期引用**判成"指向不存在的对象"——实测：Sprint-16 与
    Sprint-18 的域里都因此各多出 1 条假红（072/081 引用 069）。**收窄判定域不等于收窄
    "存在性"的判据范围**：前者问"本期该谁被要求"，后者问"这个名字在账本里有没有"。
    """
    _criterion()
    problems: list[str] = []
    by_id = {r.get("run_id"): r for r in (ledger if ledger is not None else runs)}
    for r in runs:
        source = str(r.get("scope_source") or "").strip()
        if not source or source == "self-chosen":
            continue
        for prefix in policy.scope_ref_sources:
            if not source.startswith(prefix):
                continue
            ref = source[len(prefix):].strip()
            target = by_id.get(ref)
            if target is None:
                problems.append(f"[C2] {r.get('run_id')} 的 scope 来源指向不存在的对象：{ref!r}")
                break
            if target.get("status") in set(policy._data("ledger_status")["non_credible"]):
                problems.append(f"[C2] {r.get('run_id')} 引用的 {ref} 状态为 {target.get('status')}，"
                                f"其 scope 不可采信")
            if target.get("role") not in policy.specs:
                problems.append(f"[C2] 被引用的 {ref} 的 role={target.get('role')!r} 没有对应 spec")
            break
        else:
            problems.append(f"[C2] {r.get('run_id')} 的 scope_source={source!r} 不匹配任何已知引用前缀"
                            f"{list(policy.scope_ref_sources)}（既非引用也非 self-chosen）")
    # 封闭世界（A-M13 ②）：**账本里出现过的每个 role 都必须有 spec**。
    # 与 C1/C3 不同，这条判据**按全账本**判定（`ledger`）：判定域可以按 Sprint 收窄，
    # 但"这个角色名有没有 spec"是关于**整个账本**的事实——只看域内会把域外的野角色漏掉。
    unresolved = policy.unresolved_roles(
        str(r.get("role") or "") for r in (ledger if ledger is not None else runs))
    for role in unresolved:
        problems.append(f"[C2] 账本出现无 spec 的 role={role!r}（新增角色必须建 "
                        f"{policy.spec_dir.name}/<role>.md 并声明 scope_required）")
    return problems


def _in_flight_grace_minutes(policy: AgentPolicy) -> float | None:
    """§9 登记的**在飞宽限**（分钟）——`A-M13` ④：口径与 `ledger_measurement.in_flight`
    的 `terminal_writeback_grace_minutes` **同一取值来源**（不得各写一个数）。

    为什么需要：主代理是**边跑边登记** §9 的，于是"账本有 run、§9 还没写"在任何一次
    复核 run 刚登记时**必然出现**——把它当缺陷就是与工作流互斥的结构性假红（同
    `terminal_not_written_back` 的成因）。宽限内只提示（`INFO`，不计缺陷），超期照旧逐条 FAIL。
    """
    try:
        lm = policy._data("ledger_measurement") or {}
        value = (lm.get("in_flight") or {}).get("terminal_writeback_grace_minutes")
        return float(value) if value is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def check_linkage(policy: AgentPolicy, sprint: dict, runs: list[dict],
                  window_start: str | None = None) -> list[str]:
    """§9 结构化表 ↔ 账本**双向**一致（防"写了没跑"/"跑了没写"）。

    **窗口起点取自账本侧**（`ledger_close_window`），不取自被校验的 §9 文档——
    否则"删掉 §9 里最早的几行"就能把窗口抬高、
    把早期 run 挤出检查范围（N6 实测的绕过路径）。
    文档侧只参与**区间比对**：§9 最早一行不得晚于账本窗口起点。

    `window_start` 由 `evaluate()` 统一推导后传入（与 `check_c1` 同一个窗口；
    单独调用时传 None 则本函数自行推导，语义相同）。
    `sprint["malformed"]`（首列 `run-…` 但列数 <5 的行）逐条点名：这些行**等于没登记**，
    静默丢掉它们会让"登记了"与"闸门认了"两件事悄悄分叉（N8 一族）。
    """
    _criterion()
    problems: list[str] = []
    by_id = {r.get("run_id"): r for r in runs}
    ledger_roles = {s.role for s in policy.close_ledger_steps} | policy.review_roles
    table_ids = {row["run_id"] for row in sprint["rows"]}

    for row in sprint.get("malformed") or []:
        problems.append(
            f"[linkage] §9 表行结构非法（第 {row['line']} 行："
            f"{row['cells']} 列 < 5）：{row['text'][:70]}"
            f" → 该行被忽略 = 该 run 未登记")

    if window_start is None:
        window_start = ledger_close_window(policy, runs)
    scoped = [r for r in runs if r.get("role") in ledger_roles
              and (window_start is None or str(r.get("started_at") or "") >= window_start)]

    for rid in sorted(table_ids - set(by_id)):
        problems.append(f"[linkage] §9 写了 run 但账本无记录：{rid}")
    grace = _in_flight_grace_minutes(policy)
    now_epoch = datetime.now(timezone.utc).timestamp()
    for r in scoped:
        if r.get("run_id") in table_ids:
            continue
        rid = r.get("run_id")
        started = _ts(str(r.get("started_at") or ""))
        age_min = (now_epoch - started.timestamp()) / 60 if started else None
        if grace is not None and age_min is not None and 0 <= age_min < grace:
            # A-M13 ④：在飞宽限内只提示（不计缺陷）——"刚登记、§9 还没写"是工作流的常态，
            # 不是缺口；超期仍逐条 FAIL（宽限不是豁免）。
            print(f"INFO[linkage-in-flight] {rid} 登记 {age_min:.0f} 分钟前、"
                  f"§9 run 表尚未登记 ⇒ 宽限 {grace:.0f} 分钟内只提示不判"
                  f"（口径同 ledger_measurement.in_flight）")
            continue
        if age_min is not None and age_min < 0:
            # 2026-09-25 独立复核 `run-…083` major：宽限**没有下界**时，
            # 一条 `started_at` 在未来的 run（`age_min` 为负）会**永久**落在宽限内
            # ⇒ 它的 §9 登记要求被无限期豁免。
            problems.append(
                f"[linkage/未来] {rid} 的 started_at="
                f"{r.get('started_at')!r} **晚于现在**"
                f"（{age_min:.0f} 分钟）⇒ 未来的 run 不适用在飞宽限（宽限是给"
                f"刚登记、§9 还没写的当期 run），照旧要求登记")
            continue
        problems.append(f"[linkage] 账本有 run 但 §9 run 表未登记：{rid}")

    # 区间比对（窗口**不得取自被校验文档自身**）：§9 最早一行晚于账本窗口起点 = 有人在用
    # "少写几行"缩小窗口。逐条点名在上面，这里给出窗口级结论（便于一眼看出是区间问题）。
    doc_starts = [str(by_id[row["run_id"]].get("started_at") or "")
                  for row in sprint["rows"] if row["run_id"] in by_id]
    doc_starts = [s for s in doc_starts if s]
    if window_start and doc_starts and min(doc_starts) > window_start:
        problems.append(
            f"[linkage/区间] §9 run 表最早一行（{min(doc_starts)}）晚于**账本侧**关闭窗口起点"
            f"（{window_start}）→ 有账本 run 落在 §9 区间之外未登记（窗口起点不得取自被校验文档自身）")
    return problems


def check_c3(policy: AgentPolicy, sprint: dict, runs: list[dict], att: Attribution,
             right_end: str | None = None) -> list[str]:
    """C3 覆盖闭环：锚点存在、每个提交有归属、且与 §9 声明的覆盖口径一致。"""
    _criterion()
    problems: list[str] = []
    if not sprint.get("anchor"):
        problems.append("[C3] 未声明三查锚点（`三查锚点: <sha>`）→ 无法判定三查是否失效")
        return problems

    # **空区间 ≠ 通过**（2026-09-23 二查 critical 实测）：
    # 锚点 == HEAD 时 `rev_list` 为空集，
    # 于是 unowned 必为空、闸门打出"覆盖闭环 ✔"——而事实是一个提交都没受检。
    if att.empty_interval():
        problems.append(
            "（C3）锚点→HEAD 之间**没有任何提交受检**（锚点 == HEAD？）→ 覆盖闭环未被验证，"
            "不得视为通过。关闭锚点应指向**二查实际覆盖到的最后一个提交**，"
            "若确无新提交则该 Sprint 无需覆盖检查，请显式写明理由而不是留空区间")
    problems += [f"[C3-窗口] {p}" for p in att.window_problems()]
    problems += [f"[C3-T] {p}" for p in att.exception_problems()]

    globs = tuple((policy.close_gate.get("coverage") or {}).get("doc_only_globs") or ())
    unowned = att.unowned(globs)
    if unowned:
        # 失效方向反转（用户 P2 关切）：表没跟上 → 默认 FAIL 并**逐条点名**
        # 右端标签（M-A）：`right_end` 非空时判据的上界来自**域内**最后一条覆盖 run，
        # 不是仓库 HEAD——消息里必须说清是哪一个，否则读者会以为"HEAD 之后也检了"。
        right_label = f"{right_end[:8]}（域右端）" if right_end else "HEAD"
        problems.append(
            f"[C3] 锚点 {sprint['anchor'][:8]}→{right_label} 有 "
            f"{len(unowned)} 个提交无归属（run 窗口/例外表/doc-only 都不覆盖）："
            + ", ".join(s[:10] for s in unowned[:8])
            + (" …" if len(unowned) > 8 else ""))

    # §9 行声明的覆盖范围必须与账本一致（防"文档写了覆盖、账本没有窗口"）。
    # N6（2026-09-25 二查）：
    # 原先**只比对 `scope_source`** → §9 把 role/target 写错也 PASS。
    # role/target 是 §9 表的定位字段：写错整行的指向就错了（gate 会去查另一个 run），
    # 因此三者一并比对（"-"/空 = 该格未填，不比对）。
    by_id = {r.get("run_id"): r for r in runs}
    for row in sprint["rows"]:
        run = by_id.get(row["run_id"])
        if run is None:
            continue
        for field in ("scope_source", "role", "target"):
            declared = str(row.get(field) or "").strip()
            if declared in {"-", ""}:
                continue
            actual = exact_target(run) if field == "target" else str(run.get(field) or "").strip()
            if declared != actual:
                problems.append(f"[C3] §9 表 {row['run_id']} 的 {field}={declared!r} "
                                f"与账本 {actual!r} 不一致（定位字段写错 = 指向了另一个对象）")
    return problems


def evaluate(policy: AgentPolicy, sprint: dict, runs: list[dict], *,
             att: Attribution | None = None, check_coverage: bool = True,
             sprint_id: str | None = None, right_end: str | None = None,
             ledger: list[dict] | None = None) -> list[str]:
    """返回失败原因列表（空 = 通过）。三条不变式 + 需求（全部数据驱动）。

    **关闭窗口只推导一次**：C1 的判定域（D1）与 §9↔账本的区间比对（N6）
    必须用**同一个**窗口，两处各推一次＝两套口径，而口径分叉正是本卡要治的
    形态（"工具一个口径、闸门另一个口径"）。

    **窗口的上界问题（finding 2）也在这里收口**：`derive_close_window` 一并返回"起点被弃用"
    的具名问题（未来时间戳 / 晚于整条流水线 / 被更早的 run 引用）——**判定域退回全域**，
    既报出问题、又不静默收窄。
    """
    problems: list[str] = []
    window_start, window_problems = derive_close_window(
        policy, runs, sprint_id=sprint_id)
    problems += window_problems
    problems += check_requirements(policy, runs, window_start=window_start)
    problems += check_c1(policy, runs, window_start)
    problems += check_c2(policy, runs, ledger=ledger)
    problems += check_linkage(policy, sprint, runs, window_start)
    if check_coverage:
        if att is None:
            problems.append("[C3] 覆盖检查已启用但未提供归属计算结果（内部错误）")
        else:
            problems += check_c3(policy, sprint, runs, att, right_end=right_end)
    return problems


# ---------------------------------------
# ---------------- 自检 fixture（合成政策 + 合成历史）

FIXTURE_POLICY = {
    "version": 1,
    "spec_glob": "*.md",
    "spec_dir": "specs",
    "scope_min_deviation_chars": 10,
    "scope_ref_sources": ["impact-assessment:"],
    "lint_paths": ["verify"],
    "archive_role_prefix": "tech-research",
    # 状态机政策（真源 agents/policy.json::ledger_status）；fixture 也必须齐全，
    # 否则 load_policy 的"死键/缺键"自检会把 fixture 自己判死。
    "ledger_status": {
        "all": ["queued", "running", "succeeded", "failed", "cancelled"],
        "terminal": ["succeeded", "failed", "cancelled"],
        "transitions": {"queued": ["running"], "running": ["succeeded", "failed", "cancelled"]},
        "non_credible": ["failed", "cancelled"],
    },
    # A-M13 ④（§9 在飞宽限）：与真政策同键同名——宽限判据必须能被自检打到，
    # 否则"宽限内只提示"这条在 fixture 里永远走不到（假绿）。
    "ledger_measurement": {"in_flight": {"terminal_writeback_grace_minutes": 120}},
    "close_gate": {
        "scope_ref_step": "scope",
        "coverage": {"exceptions_file": "coverage-exceptions.json",
                     "doc_only_globs": ["docs/**"],
                     # B3：作用域类 run 不承担内容覆盖的语义说明。fixture 也必须齐全——
                     # 真实政策缺它时 `Policy.close_gate` 直接 fail-closed（"读不到"不得
                     # 静默等于"没这条语义"），fixture 自然要同口径。
                     "scope_run_window": "fixture：作用域类 run 不承担内容覆盖，"
                                         "空窗口不判问题"},
    },
}

FIXTURE_FANOUT = {
    "version": 6,
    "planning_pipeline": [],
    "sprint_close_pipeline": [
        {"order": 1, "step": "scope", "role": "impact-assessment", "spec": "impact-assessment",
         "task": {"change_set": "auto"}, "executor": "subagent",
         "close_ledger": True, "close_targets": []},
        {"order": 2, "step": "doc-audit", "role": "doc-audit", "spec": "doc-audit",
         "task": {"target": "working-tree"}, "executor": "subagent",
         "close_ledger": True, "close_targets": ["working-tree"]},
        {"order": 3, "step": "code-review", "role": "code-review", "spec": "code-review",
         "tasks": [{"target": "branch:windows"}, {"target": "branch:main"}], "executor": "subagent",
         "close_ledger": True, "close_targets": ["branch:windows", "branch:main"]},
        {"order": 4, "step": "lessons", "role": "lessons-learned", "spec": "lessons-learned",
         "task": {"sprint_doc": "auto"}, "executor": "subagent",
         "close_ledger": True, "close_targets": []},
        {"order": 5, "step": "workspace-check", "role": "workspace-check", "spec": "workspace-check",
         "condition": "always", "executor": "main-agent",
         "close_ledger": False, "close_targets": []},
    ],
}

# role -> scope_required（合成 spec frontmatter 的内容）
FIXTURE_SPECS = {
    "impact-assessment": False,
    "doc-audit": True,
    "code-review": True,
    "lessons-learned": False,
    "workspace-check": False,
    # **评审类但不在关闭流水线里**的角色：真账本里就有这样的历史 run
    # （`run-2026-09-02-agent-onboarding-review-036`，正是 D1 之前被永久
    # 点名的 34 条之一）。D1 的判定域反向对照用它：既落在 C1 的管辖
    # （`scope_required: true`），又不参与关闭步骤的"〇查必须早于后续步骤"
    # 次序判据（那是 `check_requirements` 的另一条判据，本卡不动它——
    # 它的口径是"全域"，加一条早期 run 会改它的结论，与本卡无关）。
    "agent-onboarding-review": True,
}

SHA_A, SHA_B, SHA_C, SHA_D = "a" * 40, "b" * 40, "c" * 40, "d" * 40
SHA_E = "e" * 40
HISTORY = [SHA_D, SHA_C, SHA_B, SHA_A]  # 新 → 旧


def _write_fixture_policy(tmp: Path) -> tuple[Path, Path]:
    (tmp / "specs").mkdir(parents=True, exist_ok=True)
    for role, scope_required in FIXTURE_SPECS.items():
        window = "none" if role == "workspace-check" else "self"
        (tmp / "specs" / f"{role}.md").write_text(
            "---\n"
            f"name: {role}\n"
            f"description: fixture role {role}\n"
            'version: "1.0.0"\n'
            f"scope_required: {'true' if scope_required else 'false'}\n"
            f"coverage_window: {window}\n"
            "---\n\n# fixture\n", encoding="utf-8")
    policy_path = tmp / "policy.json"
    fanout_path = tmp / "fanout.json"
    policy_path.write_text(json.dumps(FIXTURE_POLICY), encoding="utf-8")
    fanout_path.write_text(json.dumps(FIXTURE_FANOUT), encoding="utf-8")
    return policy_path, fanout_path


def _load_fixture_policy(tmp: Path) -> AgentPolicy:
    policy_path, fanout_path = _write_fixture_policy(tmp)
    return load_policy(root=tmp, spec_dir=tmp / "specs", policy_path=policy_path, fanout_path=fanout_path)


def _fixture_policy_path(tmp: Path) -> Path:
    """fixture 政策的**实际路径**。

    `load_policy` 的优先级是 `env > 参数 > root/agents/policy.json`——因此当
    `PAPERQA_AGENT_POLICY` 被设成一份**别处的**政策时（套件里就会这样：各闸门用 env
    注入自己的 fixture），显式传 `tmp/"policy.json"` 会被 env 覆盖掉，结果"测的是别的
    政策"。本函数让自检与 `load_policy` **同口径**取环境变量，避免这条静默分叉。
    """
    return Path(os.environ.get(ENV_POLICY, str(tmp / "policy.json")))


def _run(rid: str, role: str, task: str, started: str, scope="", dev=None,
         anchor: str = SHA_A, through: str = SHA_D) -> dict:
    return {"run_id": rid, "role": role, "task_id": task, "started_at": started,
            "status": "succeeded", "scope_source": scope, "scope_deviation": dev,
            "coverage_anchor": anchor, "covers_through": through, "coverage_window": "self"}


def _rows(runs: list[dict]) -> list[dict]:
    """账本 run → §9 表行（`-` = 该格未填，与 `_doc` 同口径）。"""
    return [{"run_id": r["run_id"], "role": r["role"], "target": r["task_id"],
             "scope_source": r.get("scope_source") or "-", "coverage": "core",
             "deviation": r.get("scope_deviation") or "-"} for r in runs]


def _doc(rows: list[dict], anchor: str | None) -> str:
    lines = ["# Sprint 示例", "", "## 9. 关闭三查记录（结构化 run 表）", "",
             TABLE_HEADER, "|---|---|---|---|---|---|"]
    for row in rows:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            row["run_id"], row["role"], row.get("target", "-"),
            row.get("scope_source", "-"), row.get("coverage", "-"), row.get("deviation", "-")))
    if anchor:
        lines += ["", f"三查锚点: `{anchor}`"]
    return "\n".join(lines)


def _fixture_runs() -> list[dict]:
    all_cover = dict(anchor=SHA_A, through=SHA_D)
    return [
        _run("run-k-001", "impact-assessment", "planned", "2026-09-21T01:00:00+00:00", **all_cover),
        _run("run-d-002", "doc-audit", "working-tree", "2026-09-21T02:00:00+00:00",
             "impact-assessment:run-k-001", **all_cover),
        _run("run-c-003", "code-review", "branch:windows", "2026-09-21T02:10:00+00:00",
             "impact-assessment:run-k-001", **all_cover),
        _run("run-c-004", "code-review", "branch:main", "2026-09-21T02:20:00+00:00",
             "impact-assessment:run-k-001", **all_cover),
        _run("run-l-005", "lessons-learned", "sprint", "2026-09-21T03:00:00+00:00", **all_cover),
    ]


def _fixture_attribution(runs: list[dict], *, exceptions: list[dict] | None = None,
                         unowned_extra: bool = False, policy: AgentPolicy | None = None) -> Attribution:
    """合成历史：锚点 = SHA_A（最旧），HEAD = SHA_D（最新），中间 SHA_B/SHA_C（新→旧 D,C,B,A）。

    覆盖窗口 (SHA_A, SHA_D] 覆盖 B、C、D 三个提交。
    `unowned_extra=True` 时改写 run 的窗口
    使它们只覆盖到 SHA_C —— 于是 SHA_D（HEAD 本身）无归属，
    模拟"覆盖表/窗口落后于 HEAD"。
    """
    shas = [SHA_B, SHA_C, SHA_D]
    order = {SHA_D: 0, SHA_C: 1, SHA_B: 2, SHA_A: 3}
    windows = coverage_windows_from_runs(runs, policy)
    if unowned_extra:
        # HEAD 之后的收尾提交（本例即 SHA_D）没有任何 run 覆盖到：锚点→HEAD 覆盖未闭环
        windows = [type(w)(run_id=w.run_id, role=w.role, anchor=SHA_A, through=SHA_C,
                          from_run=True) for w in windows]
    return Attribution(anchor=SHA_A, head=SHA_D, shas=shas, order=order,
                       windows=windows, exceptions=list(exceptions or []), root=None,
                       policy=policy)


# 自检期 fixture policy（由 `_selfcheck` 赋值为真实 fixture policy）。
# **必须传给 `Attribution`**：B3 的空窗口语义要按 run 类别判定，而"类别"来自
# `close_gate.scope_ref_step` + spec frontmatter（数据），不是代码常量。
_FIXTURE_POLICY: AgentPolicy | None = None


def _att(runs: list[dict], *, exceptions: list[dict] | None = None,
         unowned_extra: bool = False,
         policy: AgentPolicy | None = None) -> Attribution:
    """`_fixture_attribution` 的自检包装：默认带上 fixture 政策
    （B3 需要它判 run 类别）。"""
    return _fixture_attribution(
        runs, exceptions=exceptions, unowned_extra=unowned_extra,
        policy=policy if policy is not None else _FIXTURE_POLICY)


def _windows(runs: list[dict]):
    from verify.agent_policy import coverage_windows_from_runs

    return coverage_windows_from_runs(runs)


# --------------------------------------------------------------------- 入口

def run_real_data(sprint_file: Path, check_coverage: bool) -> int:
    path = Path(sprint_file)
    if not path.exists():
        print(f"CLOSE-READINESS-ERROR: Sprint 文档不存在：{path}（fail-closed，不静默放行）")
        return 2
    try:
        policy = load_policy()
    except PolicyError as exc:
        print(f"CLOSE-READINESS-ERROR: {exc}")
        return 2
    runs = load_runs(registry_path())
    sprint = parse_sprint(path.read_text(encoding="utf-8"))

    # **账本不存在 ≠ 账本有问题**（C4，2026-09-25 关闭期实测）：
    # `agents/runtime/registry.json`
    # 被 `.gitignore` 忽略 ⇒ **CI 的全新 checkout 必然没有它**。
    # 此时 C1/需求（"流水线步骤跑过没有"）、
    # linkage（账本↔§9 双向一致）与 C3 覆盖归属**都无从判定**——它们的数据源就是账本。
    # 旧行为是把"没有数据"判成"数据不合格"（实测 10 项 FAIL：
    # 4 条"缺 run" + 6 条"§9 写了但账本无记录"），
    # 于是**推上去那一刻 windows 的必需检查恒红**，而修法只能是伪造账本。
    # 现按 `verify_ledger_measurement.py`（code-review-072 critical）的同一口径处理：
    # **缺账本 → 显式 SKIP（理由上屏、rc=0）**；
    # **账本存在但坏 → 照旧 fail-closed**（下见 evaluate 前的解析）。
    ledger_path = registry_path()
    ledger_missing = not ledger_path.is_file()
    if ledger_missing:
        _RUN_STATE["skipped"] = True
        print(f"SKIP[ledger-absent] 账本不存在：{ledger_path}")
        print("  → C1/需求、linkage、C3 覆盖归属**本环境无从判定**（它们的数据源就是账本；"
              "`registry.json` 被 .gitignore 忽略 ⇒ 全新 checkout 没有它是正常状态）。")
        print("  本环境仍然校验**不依赖账本的部分**：Sprint 文档可解析、§9 run 表结构合法、"
              "三查锚点已声明且形态合法。完整关闭判定是**本机/关闭期动作**（须在有账本的环境跑）。")
        if not sprint.get("anchor"):
            print("CLOSE-READINESS FAIL（1 项）：")
            print("  - [C3] 本 Sprint 文档未声明三查锚点（`三查锚点: <sha>`）——该判据不依赖账本")
            return 1
        for row in sprint.get("malformed") or []:
            print("CLOSE-READINESS FAIL（1 项）：")
            print(f"  - [linkage] §9 表行结构非法（第 {row['line']} 行）：{row['text'][:60]}")
            return 1
        print(f"CLOSE-READINESS SKIP（账本缺失档，**不是通过**）：{path.name}"
              f"（run 表 {len(sprint['rows'])} 行，"
              f"锚点 {str(sprint.get('anchor'))[:8]}；账本相关判据未执行）")
        return 0

    # ---- M-A（`TG-19`）：**判定域必须由被判定物派生** ------------------------------
    # 原口径：作用域 run 取"全账本最新一条"，于是下一个 Sprint 的 kickoff 〇查一登记，
    # 上一个 Sprint 的窗口就被顶掉（2026-09-25 实测：
    # Sprint-17 的关闭读数由 1 项变 99 项，
    # 其中 98 项是假红）。现在：域 = **本文档所属 Sprint** 的 run。
    sprint_id = sprint_identity_of_doc(path)
    if sprint_id is None:
        print(f"DOMAIN-UNAVAILABLE：无法从被判定物派生 Sprint 身份"
              f"（文件名 {path.name!r} 里没有 `sprint-<N>`）"
              f"⇒ 不产出判定结论（退出码 {DOMAIN_UNAVAILABLE_EXIT}）。")
        print("  → 域必须由被判定物派生；派生不出时 fail-closed，"
              "**不得**退回全域，也不得把全域 findings 当成结论。")
        return DOMAIN_UNAVAILABLE_EXIT
    domain, unknown_ident = domain_runs(runs, sprint_id)
    candidate = scope_step_run(policy, domain, sprint_id=sprint_id)
    if candidate is None:
        print(f"DOMAIN-UNAVAILABLE：账本里找不到 **Sprint-{sprint_id}** 的作用域 run"
              f"（step={str(policy.close_gate.get('scope_ref_step'))!r}）"
              f"⇒ 不产出判定结论（退出码 {DOMAIN_UNAVAILABLE_EXIT}）。")
        print("  → 语义：本 Sprint 的关闭流水线**还没开始**"
              "（或作用域 run 的 `task_id` 里没有 `Sprint-<N>`、"
              "也未写显式 `sprint` 字段）。")
        return DOMAIN_UNAVAILABLE_EXIT
    window_start, window_problems = derive_close_window(
        policy, domain, sprint_id=sprint_id)
    # 无身份的 run 只在**该 Sprint 的窗口内**才算本期（M-A 的第二道过滤）：
    # 身份过滤解决"别的 Sprint 的 run 混进来"，
    # 窗口过滤解决"身份不可派生的陈旧 run 混进来"
    # ——后者实测会让 Sprint-18 的域里出现 Sprint-17 的 code-review（其 scope_source 指向
    # 不在域内的 069 ⇒ C2 报"指向不存在的对象"，纯属跨期串味）。
    if window_start is not None:
        domain = [r for r in domain
                  if run_sprint_identity(r) is not None
                  or str(r.get("started_at") or "") >= window_start]
    print(f"[domain] Sprint-{sprint_id}；域内 run {len(domain)} 条"
          f"（其中**身份不可派生、按 fail-closed 保留** {unknown_ident} 条——"
          f"该计数是**全账本**里无 Sprint 身份的 run 数，不是域内子集；"
          f"二查 run-…-087 minor 7：旧文案把两个数并列成『域内 8 条（保留 23 "
          f"条）』自相矛盾）"
          f"；作用域 run = {candidate.get('run_id')}；窗口起点 = {window_start}")
    if window_problems:
        print(f"DOMAIN-UNAVAILABLE：Sprint-{sprint_id} 的窗口被次序/时序判据弃用"
              f"⇒ 不产出判定结论（退出码 {DOMAIN_UNAVAILABLE_EXIT}）：")
        for p in window_problems:
            print(f"  - {p}")
        return DOMAIN_UNAVAILABLE_EXIT

    right_problems: list[str] = []
    att = None
    right_end: str | None = None
    if check_coverage:
        anchor = sprint.get("anchor") or ""
        right_end, right_run, right_problems = domain_right_boundary(
            domain, policy=policy, root=ROOT)
        right_end = right_end or None
        head = right_end or head_sha(ROOT)
        print(f"[domain] 右端 = {head[:12]}…"
              + (f"（由域内**覆盖最远**的 run {right_run} 的 covers_through 界定；"
                 f"其后提交属下一个 Sprint，不进入本期 C3）" if right_end else
                 "（域内没有任何覆盖窗口 ⇒ 退回仓库 HEAD）"))
        for note in right_problems:
            print(f"  {note}")
        exceptions: list[dict] = []
        cov = (policy.close_gate.get("coverage") or {})
        exc_file = cov.get("exceptions_file")
        if exc_file:
            try:
                exceptions = load_coverage_exceptions(ROOT / str(exc_file))
            except PolicyError as exc:
                print(f"CLOSE-READINESS-ERROR: {exc}")
                return 2
        att = attribution(ROOT, anchor, head, domain, exceptions, policy=policy)

    problems = [*right_problems, *evaluate(policy, sprint, domain, att=att,
                                           check_coverage=check_coverage,
                                           sprint_id=sprint_id, right_end=right_end,
                                           ledger=runs)]
    # D0-3(a)：已标注的"产出型 run"**逐条打印**——它让一条判据对该 run 失效，
    # 若只存在于账本 JSON 里，关闭报告就会"看着全绿"而无人知道有豁免在生效。
    notes = att.produced_only_notes() if att is not None else []
    for note in notes:
        print(
            f"NOTE[produced_only] {note}（该 run 不承担内容覆盖；未归属提交仍一条不少）"
            )
    if problems:
        print(f"CLOSE-READINESS FAIL（{len(problems)} 项）：")
        for p in problems:
            print(f"  - {p}")
        if att is not None and att.shas:
            print("\n覆盖明细（run 窗口 / 例外 / doc-only / UNOWNED）：")
            globs = tuple((policy.close_gate.get("coverage") or {}).get("doc_only_globs") or ())
            for line in att.report_lines(globs, limit=20):
                print("  " + line)
        return 1
    print(f"CLOSE-READINESS PASS：{path.name}（run 表 {len(sprint['rows'])} 行，"
          f"锚点 {(sprint.get('anchor') or '')[:8]}"
          f"，覆盖提交 {len(att.shas) if att else 0}"
          f"，产出型标注 {len(notes)}）")
    return 0


def _selfcheck() -> int:
    import tempfile

    global _FIXTURE_POLICY

    tmp = Path(tempfile.mkdtemp(prefix="verify_close_readiness_"))
    policy = _load_fixture_policy(tmp)
    _FIXTURE_POLICY = policy  # `_att()` 默认带上它（B3 按 run 类别判空窗口）
    runs = _fixture_runs()
    good = parse_sprint(_doc([
        {"run_id": r["run_id"], "role": r["role"], "target": r["task_id"],
         "scope_source": r.get("scope_source") or "-",
         "coverage": "core", "deviation": r.get("scope_deviation") or "-"} for r in runs],
        SHA_A))

    ok("自检 ⓪ 数据源完备（fanout 步骤 role 都有 spec + 全部显式声明 scope_required + 无死键）",
       policy.closure_problems() == [], f"problems={policy.closure_problems()[:2]}")
    ok("自检 ① 合规场景 + 覆盖闭环 → PASS",
       evaluate(policy, good, runs, att=_att(runs)) == [], "problems=[]")

    # ---- 变异用例：**从 fanout.json 自动生成**（不逐场景手写）----------------
    for step in policy.close_ledger_steps:
        mutant = [r for r in runs if r.get("role") != step.role]
        rows = [row for row in good["rows"] if row["role"] != step.role]
        p = evaluate(policy, parse_sprint(_doc(rows, SHA_A)), mutant, att=_att(mutant))
        ok(f"变异（自动生成）① 抽掉步骤 {step.order}:{step.step}（role={step.role}）→ FAIL",
           any("缺 run" in x for x in p), f"problems={p[:1]}")

    for role, targets in policy.role_targets().items():
        for target in targets:
            # 关键：**该 role 仍有别的 run**（这里造一个其它 target 的诱饵 run），
            # 否则报的是
            # "缺 run（role）"而不是 target 级判据——两种失效形态必须能被测试分别命中。
            decoy = _run(f"run-decoy-{role}", role, "decoy-scan", "2026-09-21T01:30:00+00:00",
                         "impact-assessment:run-k-001")
            mutant = [r for r in runs
                      if not (r.get("role") == role and target in str(r.get("task_id") or ""))]
            mutant = [*mutant, decoy]
            rows = [{"run_id": r["run_id"], "role": r["role"], "target": r["task_id"],
                     "scope_source": r.get("scope_source") or "-", "coverage": "core",
                     "deviation": r.get("scope_deviation") or "-"}
                    for r in mutant]
            p = evaluate(policy, parse_sprint(_doc(rows, SHA_A)), mutant,
                         att=_att(mutant))
            ok(f"变异（自动生成）② 抽掉 {role} 的 target={target!r}（保留同 role 诱饵 run）→ FAIL",
               any(f"缺 target={target!r}" in x for x in p), f"problems={p[:1]}")

    # ---- 三条不变式各自的反向对照 ----------------------------------------
    mutant = [dict(r, scope_source="", scope_deviation=None) if r["role"] == "code-review" else r
              for r in runs]
    p = evaluate(policy, good, mutant, att=_att(mutant))
    ok("C1 反向对照：评审类 run 去掉 scope 声明 → FAIL",
       any(x.startswith("[C1]") for x in p), f"problems={p[:1]}")

    # ---- D1（2026-09-25 用户裁定）：C1 判定域 = **本次关闭窗口** --------------
    # 窗口起点取自账本侧。原实现遍历全账本 ⇒ 真数据恒 FAIL 34 条（`TG-11`
    # 之前的记录没有 `scope_source` 字段，且账本有完整性哈希、不可回填）
    # ⇒ 闸门退化成人人无视的噪音。收窄必须**不放松**：
    # 窗口内缺声明仍 FAIL、窗口外缺声明不报、窗口不可推导时不过滤。
    hist = _run("run-hist-900", "agent-onboarding-review", "onboarding-scan",
                "2026-09-20T22:00:00+00:00", scope="", dev=None)
    hist_runs = [*runs, hist]
    p = evaluate(policy, parse_sprint(_doc(_rows(hist_runs), SHA_A)), hist_runs,
                 att=_att(hist_runs))
    ok("D1 反向对照 a：窗口**之前**的评审 run 缺 scope 声明 → 不报告"
       "（历史不卷入；整条闸门仍 PASS）",
       p == [], f"problems={p[:2]}")

    # ---- B1（2026-09-25）：关闭窗口起点 = **本次关闭的作用域 run** ------------
    # 改前口径 = "各必填步骤最新 run 的 started_at 最小值"，于是一个与本次关闭无关的
    # 历史步骤 run 就能把窗口拉到它自己那一刻（真数据实测：Sprint-16 补跑的 lessons 058
    # 把窗口定到 4 天前），中间的历史 run 被拖进判定域、当期缺口被淹没。
    # 新口径只认"作用域步骤（close_gate.scope_ref_step）最新 run"那一刻。
    scope_role = next(s.role for s in policy.steps
                      if s.step == policy.close_gate["scope_ref_step"])
    ok("B1 正向对照：窗口起点 = **作用域步骤**最新 run 的 started_at"
       "（不是跨步骤最小值）",
       ledger_close_window(policy, runs) == "2026-09-21T01:00:00+00:00",
       f"window={ledger_close_window(policy, runs)}"
       f"（作用域 run=run-k-001 / 最早的非作用域 run=02:00）")

    # 反向对照 a：**把作用域 run 拿掉**——旧口径仍会从"其余步骤最新 run 的最小值"
    # 编出一个窗口（于是闸门照常跑、看起来一切正常），
    # 新口径必须返回 None ⇒ 调用方不过滤（fail-closed）。
    no_scope = [r for r in runs if r.get("role") != scope_role]
    ok("B1 反向对照 a：作用域 run 缺席 → 窗口不可推导（None，fail-closed 不过滤），"
       "**不退回**旧口径编窗口",
       ledger_close_window(policy, no_scope) is None
       and check_c1(policy, no_scope, ledger_close_window(policy, no_scope)) == [],
       f"window={ledger_close_window(policy, no_scope)}")

    # 反向对照 b：同 role 更早的 run 出现时，窗口仍取**最新**那条（不取最小值）。
    # 若实现退回"跨步骤/全 role 最小值"，这一条会立刻把窗口拉到 2026-09-20——
    # 那正是 B1 改前在真数据上发生的事（lessons 058 把窗口拖到 4 天前）。
    draggy = [*runs,
              _run("run-drag-903", scope_role, "decoy", "2026-09-20T00:00:00+00:00")]
    ok("B1 反向对照 b：同 role 更早的 run 出现时，窗口仍取**最新**那条"
       "（不取最小值）",
       ledger_close_window(policy, draggy) == "2026-09-21T01:00:00+00:00",
       f"window={ledger_close_window(policy, draggy)}")

    # ---- B4（2026-09-25 独立复核 finding 2）：窗口起点必须有**上界** ------------
    # 复核实测：往账本追加**一条**更晚的作用域 run，窗口起点就从 2026-09-21T01:00 抬到
    # 2026-09-25T04:30，
    # 本次关闭的 5 条流水线 run 全部落到窗口外 ⇒ C1/linkage **静默失明**
    # （同一份"漏登记最早一行"的 §9：注入前 FAIL 2 项 → 注入后 PASS 0 项）；
    # `2099-01-01` 也照收。
    # 判据 = ①不得在未来 ②不得晚于整条流水线 ③引用它的 run 不得比它更早；
    # 违反即**弃用起点**
    # 并具名报问题（判定域退回全域 = 宁可多报，不静默收窄）。
    late_scope = _run("run-k-late", scope_role, "planned", "2026-09-25T04:30:00+00:00")
    injected = [*runs, late_scope]
    window_inj, window_problems_inj = derive_close_window(policy, injected)
    rows_missing = [row for row in good["rows"] if row["run_id"] != "run-k-001"]
    doc_missing = parse_sprint(_doc(rows_missing, SHA_A))
    p_blind_before = evaluate(policy, doc_missing, runs, att=_att(runs))
    p_blind_after = evaluate(policy, doc_missing, injected, att=_att(injected))
    ok("B4 反向对照 a（复核的注入形态）：追加一条更晚的作用域 run（2026-09-25T04:30）"
       "→ 起点被**弃用**（None，不过滤）并具名报问题，**不静默抬高窗口**",
       window_inj is None
       and any("窗口/次序" in x and "run-k-late" in x for x in window_problems_inj)
       and ledger_close_window(policy, injected) is None,
       f"window={window_inj} problems={window_problems_inj[:1]}")
    ok("B4 反向对照 a′：同一注入**不得**让「漏登记最早一行」的 §9 由 FAIL 变 PASS"
       "（失明方向必须被堵死：注入前 FAIL → 注入后仍 FAIL）",
       p_blind_before != [] and p_blind_after != []
       and any("run-k-001" in x for x in p_blind_after),
       f"注入前 {len(p_blind_before)} 项 → 注入后 {len(p_blind_after)} 项"
       f"（旧实现：2 项 → 0 项；注入后仍点名 run-k-001="
       f"{any('run-k-001' in x for x in p_blind_after)}）")

    far_scope = _run("run-k-2099", scope_role, "planned", "2099-01-01T00:00:00+00:00")
    window_far, window_problems_far = derive_close_window(policy, [*runs, far_scope])
    ok("B4 反向对照 b：未来时间戳（2099-01-01）的作用域 run → 具名 FAIL 且起点被弃用",
       window_far is None and any("窗口/未来" in x and "run-k-2099" in x for x in window_problems_far),
       f"window={window_far} problems={window_problems_far[:1]}")

    # ③ 引用它的 run 不得比它更早：把一条后续步骤 run 的 started_at 改到被引用者之前
    # （引用不可能成立于"被引用者还没登记"的时刻）→ 起点不可采信。
    # 用**合规候选**（run-k-001）+ 只改引用者时间，隔离出 ③ 单独命中（② 不参与）。
    cited_early = [dict(r, started_at="2026-09-21T00:30:00+00:00",
                        scope_source="impact-assessment:run-k-001") if r["run_id"] == "run-d-002" else r
                   for r in runs]
    window_cited, window_problems_cited = derive_close_window(policy, cited_early)
    ok("B4 反向对照 c：后续步骤 run 引用作用域 run 却比它更早（引用不可能成立）→ 具名 FAIL",
       window_cited is None and len(window_problems_cited) == 1
       and any("早于" in x and "run-d-002" in x for x in window_problems_cited),
       f"window={window_cited} problems={window_problems_cited}")

    # 正向：合规 fixture（作用域 run 在最前、其余步骤在它之后）→ 同一实现**零误报**、
    # 窗口不变。
    ok("B4 正向对照：合规 fixture（作用域 run 在前、其余步骤在它之后）→ 无问题、窗口与 B1 一致"
       "（上界不制造假红）",
       derive_close_window(policy, runs) == ("2026-09-21T01:00:00+00:00", [])
       and evaluate(policy, good, runs, att=_att(runs)) == [],
       f"derive={derive_close_window(policy, runs)}")

    # 正向：作用域 run 之后**还没跑**任何后续步骤（关闭刚开工）时，
    # 不得因为"之后一条都没有"
    # 而误判——此时"整条流水线"并不存在，判定域不该被弃用。
    fresh = [_run("run-k-fresh", scope_role, "planned", "2026-09-21T01:00:00+00:00")]
    fresh_doc = parse_sprint(_doc(_rows(fresh), SHA_A))
    ok("B4 正向对照 b：账本里只有作用域 run、后续步骤一条都没跑（关闭刚开工）"
       "→ 窗口仍可推导（不把「还没跑」误判成「流水线在它之前」）",
       derive_close_window(policy, fresh)[0] == "2026-09-21T01:00:00+00:00",
       f"derive={derive_close_window(policy, fresh)} "
       f"｜（该状态下「缺后续步骤 run」由 check_requirements 另行点名："
       f"{len(evaluate(policy, fresh_doc, fresh, att=None, check_coverage=False))} 项）")

    # 反向对照 c：非作用域步骤的 run **再早**也不得定义窗口（旧口径正是被这条拖走的）
    earliest_other = min(str(r["started_at"]) for r in runs
                         if r.get("role") != scope_role)
    ok(f"B1 反向对照 c：非作用域步骤最早 run（{earliest_other}）**不得**定义窗口起点"
       f"（旧口径 = min 跨步骤 ⇒ 正是这条把真数据窗口拖到 4 天前）",
       ledger_close_window(policy, runs) != earliest_other,
       f"window={ledger_close_window(policy, runs)}")

    # 反向对照 d（政策侧）：`scope_ref_step` 拼错 = 窗口恒不可推导
    # ⇒ 判定域静默退回全域。故 `Policy.close_gate` 必须**装载即 fail-closed**，
    # 不能等闸门报出来。
    bad_fanout = tmp / "fanout-bad-scope-step.json"
    bad_steps = [dict(FIXTURE_FANOUT["sprint_close_pipeline"][0], step="scpoe"),
                 *FIXTURE_FANOUT["sprint_close_pipeline"][1:]]
    bad_fanout.write_text(json.dumps(
        {**FIXTURE_FANOUT, "sprint_close_pipeline": bad_steps},
        ensure_ascii=False), encoding="utf-8")
    try:
        load_policy(root=tmp, spec_dir=tmp / "specs",
                    policy_path=_fixture_policy_path(tmp), fanout_path=bad_fanout)
        ok("B1 反向对照 d：close_gate.scope_ref_step 拼错 → 装载即 fail-closed", False,
           "未抛 PolicyError（窗口会静默退回全域）")
    except PolicyError as exc:
        ok("B1 反向对照 d：close_gate.scope_ref_step 拼错 → 装载即 fail-closed"
           "（不静默退回全域判定）",
           "scope_ref_step" in str(exc), str(exc)[:110])
    bad_fanout.unlink()

    # ---- B3（2026-09-25）：空窗口按 run 类别分语义 ---------------------------
    # 作用域类 run（本 fixture = impact-assessment，「跑完即登记」⇒ 窗口恒为 (X, X]）
    # **不承担内容覆盖** ⇒ 空区间不判问题；内容评审类（code-review/doc-audit）声称覆盖
    # 内容却贡献 0 覆盖 ⇒ 仍判 FAIL 并给修复指引。
    from verify.agent_policy import CoverageWindow, order_index

    def _window_problems_for(role: str, anchor: str) -> list[str]:
        w = CoverageWindow(run_id=f"run-b3-{role}", role=role, anchor=anchor,
                           through=anchor, from_run=True)
        att = Attribution(anchor=anchor, head=anchor, shas=[],
                          order=order_index([anchor]),
                          windows=[w], exceptions=[], root=None, policy=policy)
        return att.window_problems()

    ok("B3 正向对照：作用域类 run（impact-assessment, 跑完即登记）的空窗口"
       " → **不判问题**（它不承担内容覆盖）",
       _window_problems_for("impact-assessment", SHA_A) == [],
       f"problems={_window_problems_for('impact-assessment', SHA_A)}")
    for content_role in sorted(policy.review_roles):
        probs = _window_problems_for(content_role, SHA_A)
        ok(f"B3 反向对照：内容评审类 run（{content_role}）的空窗口"
           f" → 仍 FAIL 且给修复指引",
           any("空区间" in x and "set-anchor" in x and content_role in x
               for x in probs),
           f"problems={probs[:1]}")

    # 语义必须由**数据**驱动、而不是按 role 名写死：换一份把 scope_ref_step 指到别的
    # 步骤的政策，同一 role 的判定必须翻转（"作用域类"是政策说的，不是代码认名字）。
    other_step = next(s.step for s in policy.close_ledger_steps if s.step != "scope")
    other_role = next(s.role for s in policy.close_ledger_steps if s.step == other_step)
    flipped_file = tmp / "policy-flip-scope-step.json"
    flipped_file.write_text(json.dumps(
        {**FIXTURE_POLICY,
         "close_gate": {**FIXTURE_POLICY["close_gate"], "scope_ref_step": other_step}},
        ensure_ascii=False), encoding="utf-8")
    pol_flip = load_policy(root=tmp, spec_dir=tmp / "specs", policy_path=flipped_file,
                           fanout_path=tmp / "fanout.json")
    w = CoverageWindow(run_id="run-b3-flip", role=other_role, anchor=SHA_A,
                       through=SHA_A, from_run=True)
    att_flip = Attribution(anchor=SHA_A, head=SHA_A, shas=[],
                           order=order_index([SHA_A]),
                           windows=[w], exceptions=[], root=None, policy=pol_flip)
    ok(f"B3 反向对照（数据驱动）：把 scope_ref_step 改指 {other_step!r} → 同一 role "
       f"({other_role}) 的空窗口**转为不判问题**（作用是政策给的，不是代码认角色名）",
       att_flip.window_problems() == [], f"problems={att_flip.window_problems()[:1]}")

    # ---- TG-17 G2 条目 1（2026-09-25 D4）：**倒挂窗口**必须具名 ------------------
    # 形态：`covers_through` 比 `coverage_anchor` **更早**（序号更大）⇒ `covers()` 恒
    # False，
    # 而两个端点都是完整 40 位 sha、又都在序号表内 ⇒ "短 sha"与"锚点/上界不在范围内"
    # 三条旧判据**一条都不报**，窗口静默贡献 0 覆盖。
    # 只可能由 `set-anchor` 的受控回填造成（`register`/`finish`
    # 的自动记录产不出该形态）。
    # order_index([B, A]) ⇒ B 序号 0（更新）、A 序号 1
    inv_late, inv_early = SHA_B, SHA_A
    order_inv = order_index([inv_late, inv_early])

    def _inverted_problems(role: str) -> list[str]:
        w_inv = CoverageWindow(run_id=f"run-inv-{role}", role=role,
                               anchor=inv_late, through=inv_early, from_run=True)
        att_inv = Attribution(anchor=inv_late, head=inv_late, shas=[inv_early],
                              order=order_inv, windows=[w_inv],
                              exceptions=[], root=None, policy=policy)
        return att_inv.window_problems()

    ok("TG-17① 反向对照 a：**倒挂窗口**（covers_through 早于 coverage_anchor）"
       "⇒ 具名问题且给修复指引（旧判据一条都不报 ⇒ 静默 0 覆盖）",
       any("倒挂" in x and "set-anchor" in x and "恒 False" in x
           for x in _inverted_problems("code-review")),
       f"problems={_inverted_problems('code-review')[:1]}")
    ok("TG-17① 反向对照 b：倒挂**不按 run 类别豁免**（与『短 sha』同族：数据自相矛盾，"
       "不是覆盖声称问题）——作用域类 role 与内容评审类都必须被判",
       bool(_inverted_problems(other_role))
       and all(any("倒挂" in x for x in _inverted_problems(r))
               for r in sorted(policy.review_roles)),
       f"scope_role={_inverted_problems(other_role)[:1]}")
    # 正向对照：正常窗口（两个端点都在表内且上界不早于锚点）不得误报。
    order_ok = order_index([inv_late, inv_early])
    w_ok = CoverageWindow(run_id="run-inv-ok", role="code-review", anchor=inv_early,
                          through=inv_late, from_run=True)
    att_ok = Attribution(anchor=inv_early, head=inv_late, shas=[inv_late],
                         order=order_ok, windows=[w_ok],
                         exceptions=[], root=None, policy=policy)
    ok("TG-17① 正向对照：同两个端点**方向正确**时零问题（防假红）",
       not any("倒挂" in x for x in att_ok.window_problems()),
       f"problems={att_ok.window_problems()[:1]}")

    # ---- B5（2026-09-25 修复验证复核 BLOCKER）：
    # 左端点是**开区间** ⇒ "锚点比文档锚点更老"的窗口
    # 必须照常覆盖；旧实现要求两个端点都在序号表里 ⇒ 实测 14/14 窗口全失效、`(三查锚点,
    # HEAD]`
    # 这个规范窗口根本无法表达（第一个锚点后提交对任何窗口都不可归属）。
    # 三条对照钉住新口径。
    SHA_OLD = "aaaa1111" + "0" * 32  # 代表"更老、不在序号表内"的锚点
    SHA_ODD = "bbbb2222" + "0" * 32  # 代表"与本次历史无关"的锚点
    SHA_OLD2 = "cccc3333" + "0" * 32  # 代表"更老、不在序号表内"的**上界**（历史 run 的形态）
    order_b5 = order_index([SHA_B, SHA_A])  # SHA_B 最新、SHA_A 次之
    w_older = CoverageWindow(run_id="run-b5-older", role=other_role, anchor=SHA_OLD,
                             through=SHA_B, from_run=True)
    att_older = Attribution(anchor=SHA_A, head=SHA_B, shas=[SHA_A], order=order_b5,
                            windows=[w_older], exceptions=[], root=None, policy=policy,
                            older_anchors={SHA_OLD})
    ok("B5 正向对照：窗口锚点**证明为更老**（祖先关系已判过）→ 照常覆盖区间内提交"
       "（左端点是开区间，锚点不必落在序号表内）",
       att_older.owner(SHA_A, ()) == "run:run-b5-older"
       and att_older.owner(SHA_B, ()) == "run:run-b5-older",
       f"owner(A)={att_older.owner(SHA_A, ())} owner(B)={att_older.owner(SHA_B, ())}")
    w_odd = CoverageWindow(run_id="run-b5-odd", role=other_role, anchor=SHA_ODD,
                           through=SHA_B, from_run=True)
    att_odd = Attribution(anchor=SHA_A, head=SHA_B, shas=[SHA_A], order=order_b5,
                          windows=[w_odd], exceptions=[], root=None, policy=policy)
    ok("B5 反向对照 a：锚点**无法证明更老**（与本次历史无关 / shallow 历史）→ 不覆盖（fail-closed），"
       "且 `window_problems()` **逐条点名**（不再静默丢弃）",
       att_odd.owner(SHA_A, ()) is None
       and any("证明不了" in p and "run-b5-odd" in p for p in att_odd.window_problems()),
       f"owner={att_odd.owner(SHA_A, ())} problems={att_odd.window_problems()[:1]}")
    w_scope_odd = CoverageWindow(run_id="run-b5-scope", role=scope_role, anchor=SHA_ODD,
                                 through=SHA_B, from_run=True)
    att_scope_odd = Attribution(anchor=SHA_A, head=SHA_B, shas=[SHA_A], order=order_b5,
                                windows=[w_scope_odd], exceptions=[], root=None, policy=policy)
    ok("B5 反向对照 b：**作用域类** run 的窗口即使对不上历史也**不点名**"
       "（它不承担内容覆盖，报它是结构性假红）",
       att_scope_odd.window_problems() == [], f"problems={att_scope_odd.window_problems()[:1]}")
    # B5 反向对照 c（2026-09-25 修复验证复核 finding，**回归修复的对照**）：
    # 第一版 `_is_ancestor` 只 `except Exception`，而 `git()
    # ` 抛的 `PolicyError` 是 `SystemExit`
    # 子类 ⇒ 捕获不到 ⇒ "判不了"变成**整闸门硬中止**（POLICY-ERROR、无报告），
    # 且上一条点名分支
    # 沦为死代码。本对照**直接打真实函数 + 真实仓库**（不是注入 older_anchors）：
    # 一个无法解析的 sha 必须返回 False（交由上层点名），**不得抛错**。
    ok("B5 反向对照 c：`_is_ancestor` 对**无法解析的锚点**必须返回 False 而**不得抛错**"
       "（否则整闸门中止、点名分支成死代码）",
       _is_ancestor(ROOT, "deadbeef" * 5, head_sha(ROOT)) is False, "bogus sha → False")
    # B5 反向对照 d（自查发现的**假阳性回归**）：
    # 窗口**两个端点都证明为更老** = 该窗口整体落在本次
    # 关闭窗口**之前**（历史 run 的正常形态：063/064/065/066/067…）
    # ⇒ 贡献 0 覆盖是**预期**、
    # **不得点名**。上界判据第一版只判锚点、上界一律点名 ⇒ 实测 12 项假阳性。
    w_hist = CoverageWindow(run_id="run-b5-hist", role=other_role, anchor=SHA_OLD,
                            through=SHA_OLD2, from_run=True)
    att_hist = Attribution(anchor=SHA_A, head=SHA_B, shas=[SHA_A], order=order_b5,
                           windows=[w_hist], exceptions=[], root=None, policy=policy,
                           older_anchors={SHA_OLD}, older_throughs={SHA_OLD2})
    ok("B5 反向对照 d：窗口两端点**都早于**文档锚点（历史 run）→ 不点名且不贡献覆盖"
       "（否则历史窗口会被整片误报）",
       att_hist.window_problems() == [] and att_hist.owner(SHA_A, ()) is None,
       f"problems={att_hist.window_problems()[:1]} owner={att_hist.owner(SHA_A, ())}")

    # 短 sha 是**另一族**缺陷，与 run 类别无关：作用域类 run 也必须判（否则"跑完即登记"
    # 之外还会多一条"短 sha 免检"的后门）。
    short_scope = CoverageWindow(run_id="run-b3-short", role=scope_role, anchor=SHA_A,
                                 through=SHA_A[:8], from_run=True)
    att_short = Attribution(anchor=SHA_A, head=SHA_A, shas=[],
                            order=order_index([SHA_A]),
                            windows=[short_scope], exceptions=[], root=None,
                            policy=policy)
    ok("B3 正向对照：作用域类 run 的**短 sha** 仍判问题（空区间豁免不扩到短 sha 缺陷）",
       any("不是完整 40 位" in x for x in att_short.window_problems()),
       f"problems={att_short.window_problems()[:1]}")

    # ---- D0-3(a)（2026-09-25）：产出型 run 的**逐条标注** ---------------------------
    # 背景（`TG-17` ⑤）：账本原先没有实现类 role ⇒ 实现类工作补登记挂评审 role
    # （实测 run-…-code-review-068），其窗口恒为空区间 ⇒ B3 判"内容评审类空窗口 FAIL"。
    # 对**产出型** run 报这一条是结构性假红（它没有内容覆盖的声称可违反）。
    # 修法不是放宽判据，而是把"它不是内容评审"落成**账本数据**：`agent-ops
    # mark-produced`
    # 逐条列名 + 必带理由 + 留痕数组。这里锁死三条边界：
    #   ① 未标注的内容评审类 run 空窗口 **仍 FAIL**（收窄只由账本数据触发）；
    #   ② 标注后不再报，且**必须被逐条打印**（豁免不得静默生效）；
    #   ③ 短 sha **不因标注豁免**（标注只管"空区间"这一条判据）。
    def _att_for_row(row: dict) -> Attribution:
        """用**真实入口**（账本行 → `window_problems`）判定，
        不另写一份"长度相等就算空"的判据（那是两套口径）。

        `order_index` 取自上面 B3 块的同名导入（模块层面不再重复导入：那会被 ruff 判
        F811 重定义 + F401 未使用——本仓 B 级硬闸门为 0，不允许为方便留 import）。
        """
        windows = coverage_windows_from_runs([row], policy)
        return Attribution(anchor=str(row.get("coverage_anchor") or ""), head="", shas=[
            ],
                           order=order_index([str(row.get("coverage_anchor") or "")]),
                           windows=windows, exceptions=[], root=None, policy=policy)

    produced_row = {
        "run_id": "run-produced-910", "role": "code-review", "status": "succeeded",
        "coverage_anchor": SHA_A, "covers_through": SHA_A, "coverage_window": "self",
        "scope_source": "self-chosen", "scope_deviation": "实现类工作补登记（fixture）",
    }
    probs = _att_for_row(produced_row).window_problems()
    ok("D0-3(a) 反向对照 a：**未标注**的内容评审类 run 空窗口 → 仍 FAIL"
       "（豁免只由账本数据触发，不由「忘了传字段」触发）",
       any("空区间" in x for x in probs), f"problems={probs[:1]}")

    marked_row = {**produced_row, "produced_only": True,
                  "produced_only_reason": "实现类工作（TG-13 口径+闸门），非内容评审"}
    att_marked = _att_for_row(marked_row)
    ok("D0-3(a) 正向对照：已标注 `produced_only` 的 run 空窗口 → 不再判问题",
       att_marked.window_problems() == [], 
           f"problems={att_marked.window_problems()[:1]}")
    ok("D0-3(a) 可见性：已标注的 run 被 `produced_only_notes()` 逐条打印"
       "（豁免必须看得见，否则关闭报告会\"看着全绿\"而无人知情）",
       any("run-produced-910" in n and "produced_only" in n
           for n in att_marked.produced_only_notes()),
       f"notes={att_marked.produced_only_notes()[:1]}")

    short_marked_row = {**marked_row, "covers_through": SHA_A[:8]}
    ok("D0-3(a) 反向对照 b：**短 sha 不因标注豁免**（标注只跳过\"空区间\"一条判据，"
       "不构成通用放行）",
       any("不是完整 40 位" in x for x in _att_for_row(short_marked_row).window_problems
           ()),
       f"problems={_att_for_row(short_marked_row).window_problems()[:1]}")

    inwin = _run("run-hist-901", "agent-onboarding-review", "onboarding-scan",
                 "2026-09-21T02:30:00+00:00", scope="", dev=None)
    inwin_runs = [*runs, inwin]
    p = evaluate(policy, parse_sprint(_doc(_rows(inwin_runs), SHA_A)), inwin_runs,
                 att=_att(inwin_runs))
    ok("D1 反向对照 b：窗口**之内**的评审 run 缺 scope 声明 → FAIL 且点名"
       "该 run（收窄 ≠ 放宽）",
       any(x.startswith("[C1]") and "run-hist-901" in x for x in p)
       and [x for x in p if not x.startswith("[C1]")] == [], f"problems={p[:2]}")

    orphan = [_run("run-orphan-902", "agent-onboarding-review", "onboarding-scan",
                   "2026-09-01T00:00:00+00:00", scope="", dev=None)]
    p = check_c1(policy, orphan, ledger_close_window(policy, orphan))
    ok("D1 反向对照 c：账本里没有任何关闭步骤 run（窗口不可推导）→ 不过滤，"
       "仍 FAIL（fail-closed）",
       ledger_close_window(policy, orphan) is None
       and any("run-orphan-902" in x for x in p),
       f"window={ledger_close_window(policy, orphan)} problems={p[:1]}")

    # ---- D2（N9③）：C1 必须**执行**政策的 deviation 阈值 --------------------
    dev_short = "短理由"
    short = [dict(r, scope_source="self-chosen", scope_deviation=dev_short)
             if r["run_id"] == "run-c-003" else r for r in runs]
    p = check_c1(policy, short, ledger_close_window(policy, short))
    ok(f"D2 反向对照：self-chosen 的 deviation 短于政策阈值"
       f"（{len(dev_short)} < {policy.scope_min_deviation_chars} 字符）"
       f"→ FAIL 且点名 run-c-003",
       any("run-c-003" in x and "scope_min_deviation_chars" in x for x in p),
       f"problems={p[:1]}")

    exact = [dict(r, scope_source="self-chosen",
                  scope_deviation="合" * policy.scope_min_deviation_chars)
             if r["run_id"] == "run-c-003" else r for r in runs]
    p = check_c1(policy, exact, ledger_close_window(policy, exact))
    ok("D2 正向对照：deviation 长度**恰等于**政策阈值 → 不报（阈值是下界）",
       p == [], f"problems={p[:1]}")

    # 阈值适用面必须与 `agent-ops register` 逐字对齐：来源是**合法引用**时
    # deviation 只是附注，register 不校验其长度 ⇒ 闸门也不得判红（否则是假红）。
    ref_short = [dict(r, scope_deviation=dev_short)
                 if r["run_id"] == "run-c-003" else r for r in runs]
    p = check_c1(policy, ref_short, ledger_close_window(policy, ref_short))
    ok("D2 正向对照：有合法引用来源时 deviation 短 → **不报**"
       "（与 register 同口径，防假红）",
       p == [], f"problems={p[:1]}")

    # 阈值必须真的来自**政策数据**：把 fixture 政策的阈值改成 `dev_short` 的长度，
    # 同一份输入必须转为通过——否则说明阈值是代码常量、政策只是摆设。
    relaxed_file = tmp / "policy-relaxed.json"
    relaxed_policy = dict(FIXTURE_POLICY, scope_min_deviation_chars=len(dev_short))
    relaxed_file.write_text(json.dumps(relaxed_policy), encoding="utf-8")
    pol_relaxed = load_policy(root=tmp, spec_dir=tmp / "specs",
                              policy_path=relaxed_file,
                              fanout_path=tmp / "fanout.json")
    ok("D2 反向对照（数据驱动）：阈值改为 = 实际长度 → 同一输入不再 FAIL"
       "（值来自政策，非代码常量）",
       check_c1(pol_relaxed, short, ledger_close_window(pol_relaxed, short)) == [],
       f"threshold={pol_relaxed.scope_min_deviation_chars}")

    # ---- D2（N9②）：`parse_sprint` 容忍缩进；非法 run 行不静默丢 ------------
    base_doc = _doc(good["rows"], SHA_A)
    indented = "\n".join(("  " + ln if ln.startswith("|") else ln)
                         for ln in base_doc.splitlines())
    ok("D2 反向对照：缩进的 §9 表格行不得被丢弃"
       "（原 `startswith('|')` 会把整表看成空表）",
       len(parse_sprint(indented)["rows"]) == len(good["rows"]) == len(runs),
       f"rows={len(parse_sprint(indented)['rows'])} 期望={len(runs)}")
    ok("D2 正向对照：缩进不改变锚点解析（缩进前后 anchor 一致）",
       parse_sprint(indented)["anchor"] == good["anchor"] == SHA_A,
       f"anchor={parse_sprint(indented)['anchor']}")

    bad_doc = base_doc + "\n| run-bad-999 | code-review |\n"
    sp_bad = parse_sprint(bad_doc)
    p = evaluate(policy, sp_bad, runs, att=_att(runs))
    ok("D2 反向对照：结构非法的 run 行（列数 <5）→ 逐条点名，不再静默丢",
       len(sp_bad["malformed"]) == 1 and len(sp_bad["rows"]) == len(runs)
       and any("表行结构非法" in x and "run-bad-999" in x for x in p),
       f"malformed={sp_bad['malformed']}")

    mutant = [dict(r, scope_source="impact-assessment:run-ghost-999") if r["role"] == "code-review" else r
              for r in runs]
    p = evaluate(policy, good, mutant, att=_att(mutant))
    ok("C2 反向对照：引用不存在的 run（幻影引用）→ FAIL",
       any("不存在的对象" in x for x in p), f"problems={p[:1]}")

    ghost_role = [*runs, _run("run-x-900", "no-such-role", "t", "2026-09-21T05:00:00+00:00")]
    p = evaluate(policy, good, ghost_role, att=_att(ghost_role))
    ok("C2 反向对照：账本出现无 spec 的 role（不认角色名）→ FAIL",
       any("无 spec 的 role" in x for x in p), f"problems={p[:1]}")

    # ---- spec 缺声明：封闭世界**是运行时不变量**（防"删声明即绕过 C1"）---------
    # 注意：TG-15 起该检查在 `load_policy()` 里直接抛 PolicyError（而不是"返回一个完好的
    # Policy、再让某个自检报出来"）——否则普通命令会带着缺口照常运行，
    # 而缺口正是绕过入口。
    (tmp / "specs" / "sneaky-role.md").write_text(
        '---\nname: sneaky-role\ndescription: 未声明 scope_required\nversion: "1.0.0"\n---\n',
        encoding="utf-8")
    try:
        _load_fixture_policy(tmp)
        ok("C1 反向对照：spec 缺 scope_required → 装载即 fail-closed", False, "未抛 PolicyError")
    except PolicyError as exc:
        ok("C1 反向对照：spec 缺 scope_required → 装载即 fail-closed（删声明绕不过 C1）",
           "未声明 scope_required" in str(exc), str(exc)[:110])

    # 迁移期口子必须**显式开启**、
    # 且拿掉后立刻回到 fail-closed（否则它就是"永久绕过开关"）
    os.environ["PAPERQA_POLICY_ALLOW_UNDECLARED"] = "1"
    try:
        relaxed = _load_fixture_policy(tmp)
        ok("迁移期口子：显式设 PAPERQA_POLICY_ALLOW_UNDECLARED=1 才放行，且缺口仍被逐条列出",
           any("未声明" in p for p in relaxed.closure_problems()),
           f"problems={relaxed.closure_problems()[:1]}")
    finally:
        os.environ.pop("PAPERQA_POLICY_ALLOW_UNDECLARED", None)
    (tmp / "specs" / "sneaky-role.md").unlink()
    try:
        _load_fixture_policy(tmp)
        ok("迁移完成、移除口子后恢复 fail-closed（口子不是常开开关）", True, "")
    except PolicyError as exc:
        ok("迁移完成、移除口子后恢复 fail-closed（口子不是常开开关）", False, f"仍抛错：{exc}")


    # ---- C3 反向对照 ------------------------------------------------------
    p = evaluate(policy, parse_sprint(_doc(good["rows"], None)), runs,
                 att=_att(runs))
    ok("C3 反向对照：未声明三查锚点 → FAIL", any("未声明三查锚点" in x for x in p), f"problems={p[:1]}")

    p = evaluate(policy, good, runs, att=_att(runs, unowned_extra=True))
    ok("C3 反向对照：锚点→HEAD 有未归属提交（窗口/表落后于 HEAD）→ FAIL 且点名 sha",
       any("无归属" in x and SHA_D[:10] in x for x in p), f"problems={p[:1]}")

    bad_exc = [{"sha": SHA_E, "class": "DOC-ONLY", "reason": "ok"},
               {"sha": "f" * 8, "class": "DOC-ONLY", "reason": "短 sha"}]
    p = evaluate(policy, good, runs, att=_att(runs, exceptions=bad_exc))
    ok("C3-T 反向对照：例外表短 sha → FAIL（例外必须 sha 钉死）",
       any("不是完整 40 位" in x for x in p), f"problems={p[:2]}")

    bad_exc = [{"sha": SHA_E, "class": "DOC-ONLY", "reason": "ok"},
               {"sha": "*" * 40, "class": "DOC-ONLY", "reason": "通配"}]
    p = evaluate(policy, good, runs, att=_att(runs, exceptions=bad_exc))
    ok("C3-T 反向对照：例外表含通配 sha → FAIL（禁止模式匹配未来提交）",
       any("含通配" in x for x in p), f"problems={p[:2]}")

    bad_exc = [{"sha": SHA_E, "class": "DOC-ONLY", "reason": ""}]
    p = evaluate(policy, good, runs, att=_att(runs, exceptions=bad_exc))
    ok("C3-T 反向对照：例外缺 reason → FAIL", any("缺 reason" in x for x in p), f"problems={p[:1]}")

    # ---- linkage 反向对照 -------------------------------------------------
    ghost = parse_sprint(_doc(good["rows"] + [{"run_id": "run-ghost-999", "role": "code-review",
                                               "target": "branch:main", "scope_source": "-",
                                               "coverage": "core", "deviation": "-"}], SHA_A))
    p = evaluate(policy, ghost, runs, att=_att(runs))
    ok("linkage 反向对照：§9 写了 run 但账本无记录 → FAIL",
       any("账本无记录" in x for x in p), f"problems={p[:1]}")

    # ---- N3 反向对照：target 判据必须是**精确匹配**（子串匹配 = 改名即可冒充）
    # ---------
    for tampered, expected_target in (("branch:windows-backup", "branch:windows"),
                                      ("branch:mainline", "branch:main"),
                                      ("OLD-working-tree-JUNK", "working-tree")):
        mutant = [dict(r, task_id=tampered) if exact_target(r) == expected_target else r for r in runs]
        rows = [{"run_id": r["run_id"], "role": r["role"], "target": r["task_id"],
                 "scope_source": r.get("scope_source") or "-", "coverage": "core",
                 "deviation": r.get("scope_deviation") or "-"} for r in mutant]
        p = evaluate(policy, parse_sprint(_doc(rows, SHA_A)), mutant, att=_att(mutant))
        ok(f"N3 反向对照：task_id={tampered!r} 不得冒充 target={expected_target!r}（精确匹配，子串不算）→ FAIL",
           any(f"缺 target={expected_target!r}" in x for x in p), f"problems={p[:1]}")

    # ---- N6a 反向对照：**删掉 §9 里最早的两行**不得让窗口抬高（窗口取自账本侧）-------
    p = evaluate(policy, parse_sprint(_doc(good["rows"][2:], SHA_A)), runs,
                 att=_att(runs))
    ok("N6 反向对照 a：§9 删掉最早两行 → 仍 FAIL（账本有 run 未登记 + 区间比对）",
       any("账本有 run 但 §9 run 表未登记" in x and "run-k-001" in x for x in p)
       and any("linkage/区间" in x for x in p), f"problems={p[:2]}")
    p = evaluate(policy, parse_sprint(_doc(good["rows"], SHA_A)), runs, att=_att(runs))
    ok("N6 正向对照：§9 行齐全时窗口比对不误报（好输入 rc=0）", p == [], f"problems={p[:1]}")

    # ---- N6b 反向对照：§9 的 role / target 写错 → FAIL（原先只比对 scope_source）
    # ------
    for field, bad in (("role", "doc-audit"), ("target", "branch:production")):
        rows = [dict(r) for r in good["rows"]]
        rows[2] = {**rows[2], field: bad}
        p = evaluate(policy, parse_sprint(_doc(rows, SHA_A)), runs, att=_att(runs))
        ok(f"N6 反向对照 b：§9 第 3 行 {field} 写错（{bad!r}）→ FAIL（role/target 一并比对）",
           any(f"{field}={bad!r} 与账本" in x for x in p), f"problems={p[:1]}")

    # ---- M-A（`TG-19`）：判定域必须由**被判定物**派生 -----------------------------
    ok("M-A 身份解析 a：`2026-09-21-sprint-17.md` → '17'",
       sprint_identity_of_doc("docs/iteration/sprint/2026-09-21-sprint-17.md") == "17")
    ok("M-A 身份解析 b：文件名给不出身份 → None（不猜，由调用方报 domain-unavailable）",
       sprint_identity_of_doc("docs/iteration/sprint/notes.md") is None)
    ok("M-A 身份解析 c：run 的显式 `sprint` 字段**优先于** task_id",
       run_sprint_identity({"sprint": "018", "task_id": "Sprint-7 close"}) == "18")
    ok("M-A 身份解析 d：无显式字段时从 task_id 派生（legacy 兼容；派生不出 → None）",
       run_sprint_identity({"task_id": "sprint-9-close"}) == "9"
       and run_sprint_identity({"task_id": "cleanup"}) is None)

    # **原始事故复现**（2026-09-25：G2 的 kickoff 〇查一登记，Sprint-17 的关闭读数
    # 由 1 项变 99 项，其中 98 项假红）——注入形态 = "在流水线之后追加一条**下一个
    # Sprint** 的作用域 run"。M-A 之后：上一个 Sprint 的窗口与问题清单**一字不变**。
    s16 = [
        _run("run-k-101", "impact-assessment", "Sprint-16 close scope",
             "2026-09-20T01:00:00+00:00"),
        _run("run-d-102", "doc-audit", "working-tree", "2026-09-20T02:00:00+00:00",
             "impact-assessment:run-k-101"),
        _run("run-c-103", "code-review", "branch:windows", "2026-09-20T02:10:00+00:00",
             "impact-assessment:run-k-101"),
        _run("run-c-104", "code-review", "branch:main", "2026-09-20T02:20:00+00:00",
             "impact-assessment:run-k-101"),
        _run("run-l-105", "lessons-learned", "sprint", "2026-09-20T03:00:00+00:00"),
    ]
    before_w = derive_close_window(policy, s16, sprint_id="16")
    injected = s16 + [_run("run-k-106", "impact-assessment", "Sprint-17 close scope",
                           "2026-09-20T04:00:00+00:00")]
    after_w = derive_close_window(policy, injected, sprint_id="16")
    ok("M-A 反向对照①（**原始事故复现**）：追加下一个 Sprint 的 kickoff 〇查 → "
       "上一个 Sprint 的窗口一字不变",
       before_w == after_w and before_w[0] == "2026-09-20T01:00:00+00:00",
       f"before={before_w} after={after_w}")
    ok("M-A 反向对照①b：同一条注入在**它自己的** Sprint 上仍是合法起点",
       derive_close_window(policy, injected, sprint_id="17")[0]
       == "2026-09-20T04:00:00+00:00")

    p = evaluate(policy, parse_sprint(_doc(_rows(s16[:1]), SHA_A)), s16[:1], att=None,
                 check_coverage=False, sprint_id="16")
    ok("M-A 反向对照②：本期流水线未跑 → 逐条点名缺 run（**不是** PASS）",
       sum("缺 run" in x for x in p) >= 3, f"problems={p[:3]}")
    ok("M-A 反向对照③：该 Sprint 根本没有作用域 run → 起点 None"
       "（fail-closed，不退化成全域）",
       derive_close_window(policy, s16, sprint_id="99")[0] is None)

    mixed = s16 + [_run("run-k-107", "impact-assessment", "cleanup",
                        "2026-09-20T05:00:00+00:00")]
    ok("M-A 反向对照④：无身份的**更晚**作用域 run 不得顶掉本期",
       derive_close_window(policy, mixed, sprint_id="16")[0]
       == "2026-09-20T01:00:00+00:00")
    ok("M-A 反向对照④b：一个带身份的候选都没有时，才回退到无身份候选",
       derive_close_window(policy, [_run("run-k-108", "impact-assessment", "cleanup",
                                         "2026-09-20T06:00:00+00:00")],
                           sprint_id="16")[0] == "2026-09-20T06:00:00+00:00")
    right, right_run, right_notes = domain_right_boundary(s16)
    ok("M-A 域右端 a：夹具模式（无 git 根）按**登记时间最新**取右端，并点明该口径",
       right == SHA_D and right_run == "run-l-105" and len(right_notes) == 1,
       f"right={right} run={right_run} "
       f"notes={right_notes[:1]}")
    tweaked = [*s16[:4], {**s16[4], "covers_through": SHA_C}]
    ok("M-A 域右端 b：夹具模式下仍按登记时间（**真数据模式改为按祖先远近**——见 d/e）",
       domain_right_boundary(tweaked)[0] == SHA_C)
    ok("M-A 域右端 c：域内没有任何合法覆盖窗口 → None（调用方退回仓库 HEAD）",
       domain_right_boundary([{"run_id": "x", "covers_through": ""}])[0] is None)
    # ---- 2026-09-25 独立复核 `run-…083` 的两条 major：
    # 域右端与在飞宽限的边界 ----------
    # 域右端 d：**按覆盖远近**（真 git 祖先），不按登记时间——
    # HEAD~1 那条 run 登记得更晚，
    # 但它覆盖得更近 ⇒ 必须选 HEAD 那条（原实现会选"更晚登记"的，静默缩小判定域）。
    import subprocess as _sp  # noqa: PLC0415 —— 只为取两个**真实**提交做反例
    _head = _sp.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True, encoding="utf-8").stdout.strip()
    _parent = _sp.run(["git", "-C", str(ROOT), "rev-parse", "HEAD~1"],
                      capture_output=True,
                      text=True, encoding="utf-8").stdout.strip()
    near_late = {"run_id": "run-right-near", "role": "code-review",
                 "covers_through": _parent,
                 "started_at": "2099-01-02T00:00:00+00:00"}
    far_early = {"run_id": "run-right-far", "role": "code-review",
                 "covers_through": _head,
                 "started_at": "2026-01-01T00:00:00+00:00"}
    got, got_run, got_notes = domain_right_boundary([near_late, far_early], root=ROOT)
    ok("M-A 域右端 d（复核 major 的原始形态）：**后登记但覆盖更少**的 run "
       "不得缩小判定域"
       "——真 git 祖先比较选中覆盖更远者",
       got == _head and got_run == "run-right-far" and not got_notes,
       f"got={got[:10] if got else got} run={got_run} notes={got_notes[:1]}")
    bogus = {"run_id": "run-right-bogus", "role": "code-review",
             "covers_through": "f" * 40, "started_at": "2099-01-03T00:00:00+00:00"}
    _, _, div_notes = domain_right_boundary([far_early, bogus], root=ROOT)
    ok("M-A 域右端 e：两条覆盖端点**不可比**（互不为祖先）"
       "⇒ 具名问题（fail-closed，不猜）",
       any("不可比" in n for n in div_notes), f"notes={div_notes[:1]}")
    # 域右端 d/e（2026-09-25 实测事故后补）：**不承担覆盖的 run 不得界定右端**——
    # `produced_only` 与 `coverage_window: none` 两类各一条反向对照。
    prod = {**s16[4], "run_id": "run-x-prod", "covers_through": SHA_E,
            "started_at": "2099-01-01T00:00:00+00:00", "produced_only": True}
    ok("M-A 域右端 f：`produced_only` run 不得界定域右端（它不是覆盖声明）",
       domain_right_boundary([*s16, prod])[0] == SHA_D)
    real_pol_r = load_policy()
    impl = {"run_id": "run-x-impl", "role": "implementation", "covers_through": SHA_E,
            "started_at": "2099-01-01T00:00:00+00:00"}
    ok("M-A 域右端 g：`coverage_window: none` 的 role（实现类）不得界定域右端"
       "——它 finish 时会自动记下**空窗口**，却会因'最新一条'把域右端拉到它那一刻",
       domain_right_boundary([*s16, impl], policy=real_pol_r)[0] == SHA_D)
    # 在飞宽限的**下界**（复核 major）：未来时间戳的 run 不得被宽限永久豁免。
    future = [*s16[:1],
              _run("run-c-111", "code-review", "branch:windows",
                   "2099-01-01T00:00:00+00:00", "impact-assessment:run-k-101")]
    p = check_linkage(policy, parse_sprint(_doc(_rows(s16[:1]), SHA_A)), future,
                      "2026-09-20T01:00:00+00:00")
    ok("A-M13④ 反向对照（复核 major 的原始形态）：**未来时间戳**的 run 不适用在飞宽限"
       "（否则它永久免'§9 未登记'）",
       any("run-c-111" in x and "未来" in x for x in p), f"problems={p[:1]}")

    # ---- A-M13（实现类 role 落地后的三条判据）------------------------------------
    # ① 封闭世界**按全账本**（域可以收窄，"这个角色名有没有 spec"不能收窄）
    p = check_c2(policy, [], ledger=[{"run_id": "run-x-1", "role": "no-such-role"}])
    ok("A-M13② C2 封闭世界：账本里出现无 spec 的 role ⇒ FAIL（即使它只在域外出现）",
       any("no-such-role" in x for x in p), f"problems={p[:1]}")
    # ② §9 在飞宽限：刚登记 ⇒ 只提示；超期 ⇒ 照旧 FAIL（宽限不是豁免）
    fresh_iso = datetime.now(timezone.utc).isoformat()
    fresh = [*s16[:1],
             _run("run-c-109", "code-review", "branch:windows", fresh_iso,
                  "impact-assessment:run-k-101")]
    p = check_linkage(policy, parse_sprint(_doc(_rows(s16[:1]), SHA_A)), fresh,
                      "2026-09-20T01:00:00+00:00")
    ok("A-M13④ §9 在飞宽限：刚登记的 run 未写 §9 ⇒ 只提示不判"
       "（口径同 ledger_measurement.in_flight）",
       not any("未登记" in x for x in p), f"problems={p[:1]}")
    old = [*s16[:1],
           _run("run-c-110", "code-review", "branch:windows",
                "2026-09-20T02:00:00+00:00",
                "impact-assessment:run-k-101")]
    p = check_linkage(policy, parse_sprint(_doc(_rows(s16[:1]), SHA_A)), old,
                      "2026-09-20T01:00:00+00:00")
    ok("A-M13④ 反向对照：超过宽限仍未登记 ⇒ 照旧 FAIL（宽限不是豁免）",
       any("run-c-110" in x and "未登记" in x for x in p), f"problems={p[:1]}")

    # ---- A-M13①（真政策，不是 fixture）：implementation spec 必须**被闸门消费** ----
    real_pol = load_policy()
    ok("A-M13① `implementation` spec 被政策装载（不是只写文件）",
       "implementation" in real_pol.specs, f"specs={len(real_pol.specs)}")
    ok("A-M13① `implementation` 不是评审类 ⇒ C1 不再向它要 scope 声明",
       "implementation" not in real_pol.review_roles,
       "（这条假红正是本卡要消掉的）" + f"review_roles={sorted(real_pol.review_roles)}")
    real_reg = registry_path()
    if real_reg.exists():
        unknowns = sorted(real_pol.unresolved_roles(
            str(r.get("role") or "") for r in load_runs(real_reg)))
        ok("A-M13② 真数据封闭世界：账本里出现的每个 role 都有 spec",
           not unknowns, f"无 spec 的 role={unknowns}")

    p = evaluate(policy, good, runs, att=_att(runs, unowned_extra=False),
                 check_coverage=False)
    ok("覆盖检查可关闭（CI 无 git 历史时的显式降级路径）", p == [], f"problems={p}")

    probe = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--sprint",
         "docs/iteration/sprint/__no_such_sprint__.md"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok("真数据模式对不存在的 Sprint 文档 fail-closed（退出 2，不静默放行）",
       probe.returncode == 2 and "CLOSE-READINESS-ERROR" in (probe.stdout + probe.stderr),
       f"rc={probe.returncode} out={(probe.stdout + probe.stderr).strip()[:60]}")

    # M-B（`TG-19` 反空转不变式）反向对照：**账本缺失档**——CI 全新 checkout 的真实形态。
    # 用**真子进程**打真入口（`AGENT_OPS_DIR` 指向空目录 ⇒ `registry.json` 不存在）。
    # 判据三条：输出含 `SKIP[ledger-absent]`、**不含** `EVIDENCE:`（机读证据行不得由"跳过"产生）、
    # 且不得出现 `CLOSE-READINESS PASS`。
    empty_ops = Path(tempfile.mkdtemp(prefix="verify_close_readiness_noop_"))
    # 载体必须**自带**、不能写死 windows-only 的 Sprint 文档（二查 `run-…-088` critical
    # 3：
    # 第一版写死 `docs/iteration/sprint/2026-09-21-sprint-17.md` ⇒ 在没有
    # `docs/iteration/**`
    # 的分支（main）上，子进程拿到的是 `rc=2 Sprint 文档不存在` ⇒
    # 自检自己红，而判据本身没坏）。
    # 这里现写一份最小 Sprint 文档到 `%TEMP%`，两个分支都能跑同一条判据。
    (Path(tempfile.gettempdir()) / "close-readiness-selftest-sprint.md").write_text(
        "# Sprint fixture\n\n"
        "三查锚点: b6198f5180561868e07989e6689185199f439d76\n\n"
        "## 9. 关闭三查\n\n| run_id | role |\n|---|---|\n",
        encoding="utf-8")
    probe2 = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--sprint",
         str(Path(tempfile.gettempdir()) / "close-readiness-selftest-sprint.md")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "AGENT_OPS_DIR": str(empty_ops)})
    blob = probe2.stdout + probe2.stderr
    ok("M-B 反向对照：账本缺失 ⇒ 输出 SKIP 且**不打印** EVIDENCE 行（跳过不得冒充通过）",
       probe2.returncode == 0 and "SKIP[ledger-absent]" in blob
       and "EVIDENCE:" not in blob and "CLOSE-READINESS PASS" not in blob,
       f"rc={probe2.returncode} out={blob.strip()[:120]}")

    real = registry_path()
    if real.exists():
        warn("真数据模式未在自检中执行（需 `--sprint <当前 Sprint 文档>`）",
             f"账本 {len(load_runs(real))} 条：{real}")
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


def main() -> int:
    if "--sprint" in sys.argv:
        path = Path(sys.argv[sys.argv.index("--sprint") + 1])
        rc = run_real_data(path, check_coverage="--no-coverage" not in sys.argv)
        if rc == 0 and not _RUN_STATE["skipped"]:
            # TG-6：**只在成功路径**打印机读证据行。real-data 模式的 assertions =
            # **实际执行过的判据条数**（该模式不跑 ok() 自检断言，
            # 逐条判据各自 `_criterion()` 登记）。SKIP 档不打印（`TG-19` M-B）。
            print(f"EVIDENCE: verify_close_readiness.py assertions={CRITERIA_EXECUTED} rc=0 "
                  f"mode=real-data criteria={CRITERIA_EXECUTED}")
        return rc
    try:
        rc = _selfcheck()
    except AssertionError as exc:
        # 自检断言失败 = 本次运行不能出具结论（不是"数据违规"）：`ok()` 里是显式 `raise`
        # （`-O` 删不掉），这里收敛成一行点名 + rc=1，把点名从栈帧里提到台面上。
        print(f"CLOSE-READINESS FAIL（自检断言未通过）：{exc}")
        return 1
    if rc == 0:
        print(f"EVIDENCE: verify_close_readiness.py assertions={PASSED} rc=0 mode=selfcheck")
    return rc


if not __debug__:  # noqa: SIM108 —— -O/PYTHONOPTIMIZE 会剥离 assert；守卫必须是普通语句，不能是 assert
    raise SystemExit("本闸门不得在 -O/PYTHONOPTIMIZE 下运行（`__debug__` 为 False ⇒ 判据会被整体剥离）——见 3-LEARNED 1.65")


if __name__ == "__main__":
    raise SystemExit(main())

