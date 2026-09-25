"""TG-15：关闭前置闸门（offline）——**三条不变式 + 数据驱动**，替换原先的按角色硬编码判据。

历史（为什么改）：TG-11 ③b 版本把判据写成"按角色名逐条判断"——`CLOSE_ROLES` 写死 4 个角色、
二查必须含 `windows`/`main`、〇查必须早于二查……**每加一个步骤/角色/分支都要改这个文件**，
而"改代码"本身没有任何闸门在守（`TG-15` 卡的起因）。TG-15 之后：

    C1 声明完备：**本次关闭窗口内**凡产出评审结论的 run 必须有 scope 声明
                 （外部引用 或 自选理由，且理由长度 ≥
                 `agents/policy.json::scope_min_deviation_chars`）；
                 窗口起点取自**账本侧**（`ledger_close_window`），
                 窗口之前的 run 属历史、不产生问题
    C2 指涉可核：任何外部引用必须解析到"存在且可用"的对象；运行数据里的每个 role 必须能落到 spec
    C3 覆盖闭环：`git rev-list <锚点>..<HEAD>` 的**每个提交**必须有归属

需求来源（**只有两个**，本文件不再有角色名单）：

    agents/fanout.json :: sprint_close_pipeline   → 哪些关闭步骤/role/target 必填（`close_ledger`/`close_targets`）
    agents/functions/<role>.md frontmatter        → `scope_required`（谁必须声明 scope）、`coverage_window`
    agents/policy.json                            → 阈值与开关（偏离理由长度、覆盖例外表路径、doc-only 规则）

C3-T 例外表（用户 2026-09-23 选型 + 对"表过期"的担心）：覆盖**默认由 run 数据计算**
（run 自动记录的 `coverage_anchor`/`covers_through`），例外表**只登记例外**、sha 钉死；
**表落后 = 默认 FAIL 并逐条点名未归属 sha**（失效方向反转：不静默变绿）。

用法：
    .venv\\Scripts\\python.exe verify\\verify_close_readiness.py                    # 自检（合成 fixture，含反向对照）
    .venv\\Scripts\\python.exe verify\\verify_close_readiness.py --sprint <文件>     # 真数据（关闭时）
    .venv\\Scripts\\python.exe verify\\verify_close_readiness.py --sprint <文件> --no-coverage
                                                                                  # 覆盖检查需 git 历史，CI 可关

**为什么默认只跑自检**：Sprint 未关闭时真数据模式必然 FAIL（正确的 fail-closed 语义），
但会让 offline 套件长期变红。故套件跑自检；关闭时由主代理跑 `--sprint` 并把输出写进 Sprint §9。

§9 结构化 run 表格式（供本脚本解析，`1-WORKFLOW.MD` §4.2）：
    | run_id | role | target | scope_source | coverage | deviation |
"""

from __future__ import annotations
VERIFY_META = {'features': 'TG-15 关闭前置闸门：C1 声明完备 / C2 指涉可核 / C3 覆盖闭环（锚点→HEAD 每提交有归属），需求全来自 fanout.json + spec frontmatter；含变异用例自 fanout 自动生成的反向对照', 'tier': 'offline', 'providers': [], 'est_seconds': 15, 'est_cost_cny': 0, 'routes': [], 'requires': ['none']}

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import (  # noqa: E402
    Attribution,
    PolicyError,
    attribution,
    coverage_windows_from_runs,
    head_sha,
    load_coverage_exceptions,
    load_policy,
    parse_frontmatter,
)
from verify.agent_policy import Policy as AgentPolicy  # noqa: E402  （类型注解用；避免与下方局部名冲突）

ROW_SPLIT = re.compile(r"(?<!\\)\|")
ANCHOR_RE = re.compile(r"\**三查锚点\**\s*[:：]\s*`?([0-9a-fA-F]{7,40})`?")
TABLE_HEADER = "| run_id | role | target | scope_source | coverage | deviation |"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


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


def ledger_close_window(policy: AgentPolicy, runs: list[dict]) -> str | None:
    """从**账本侧**推导本次关闭窗口的起点（N6，`started_at` 最小值）。

    为什么不能取自 §9 自己（二查实测的绕过路径）：原实现是
    `window_start = min(§9 各行的 started_at)`，于是**删掉 §9 里最早的几行**就把窗口整体抬高，
    落在窗口之前、账本里真实存在的 run 全部退出 `scoped` → "账本有 run 但 §9 未登记"一条都不报
    → 闸门 PASS。**被校验的文档不得定义自己的校验窗口。**

    做法（不读 §9）：对每条**必填关闭步骤**，取账本里满足它（role + target 精确匹配）的**最新** run
    ——最新 = 本次关闭那一批（更早的同 role run 属于上一个 Sprint 的关闭，不应被本 Sprint 的 §9 要求）；
    再取这些 run 的 `started_at` 最小值 = 窗口起点。账本里连一条关闭 run 都没有时返回 None
    （此时需求侧 C1 已经报"缺 run"，本函数不替它下结论）。

    **同一个窗口供两处使用**（一处推导、两处消费，避免两套口径）：
      * `check_linkage`：窗口内每个 close/review role 的 run 必须登记在
        §9 表里（双向比对）；
      * `check_c1`（D1，2026-09-25 用户裁定）：C1 的判定域 = 窗口内的 run；
        窗口之前的历史 run（`TG-11` 之前的记录里根本没有 `scope_source`
        字段，且账本有完整性哈希、不可回填）**不产生问题**——否则真数据上
        恒有 34 条"永久 FAIL"，闸门退化成人人无视的噪音。
        窗口不可推导（返回 None）时**不过滤**（= 全域）：这是 fail-closed
        方向，宁可多报也不静默收窄。

    比较口径：`started_at` 按**字符串字典序**比较（与 N6 的区间比对同口径）。
    账本写入的时间戳统一带 `+00:00` 偏移时字典序 = 时间序；该前提由账本自身
    保证（`agent-ops register` 用 UTC ISO 串），混入别的偏移会让本函数失去
    意义——故这里不做时区归一化，而是明确记录口径。
    """
    starts: list[str] = []
    for step in policy.close_ledger_steps:
        bucket = [r for r in runs if str(r.get("role") or "") == step.role]
        if step.targets:
            wanted = set(step.targets)
            bucket = [r for r in bucket if exact_target(r) in wanted]
        if not bucket:
            continue
        latest = max(bucket, key=lambda r: str(r.get("started_at") or ""))
        start = str(latest.get("started_at") or "")
        if start:
            starts.append(start)
    return min(starts) if starts else None


# --------------------------------------------------------------------- 判据

def check_requirements(policy: AgentPolicy, runs: list[dict]) -> list[str]:
    """需求侧（数据驱动）：关闭流水线的必填步骤 / role / target 是否都真的跑过。

    原先这些判据是 `if role == "code-review": 必须有 windows 和 main` 这样的代码；
    现在**从 `fanout.json` 推导**——加减步骤/分支只改数据。
    """
    problems: list[str] = []
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

    # 〇查必须先于二查：顺序来自数据（scope_ref_step 指向的第一步 vs 其余步骤），不是写死的角色名
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


def check_c2(policy: AgentPolicy, runs: list[dict]) -> list[str]:
    """C2 指涉可核：外部引用解析到"存在且可用"的对象；运行数据 role 必须能落到 spec（不认角色名）。"""
    problems: list[str] = []
    by_id = {r.get("run_id"): r for r in runs}
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
    unresolved = policy.unresolved_roles(str(r.get("role") or "") for r in runs)
    for role in unresolved:
        problems.append(f"[C2] 账本出现无 spec 的 role={role!r}（新增角色必须建 "
                        f"{policy.spec_dir.name}/<role>.md 并声明 scope_required）")
    return problems


def check_linkage(policy: AgentPolicy, sprint: dict, runs: list[dict],
                  window_start: str | None = None) -> list[str]:
    """§9 结构化表 ↔ 账本**双向**一致（防"写了没跑"/"跑了没写"）。

    **窗口起点取自账本侧**（`ledger_close_window`），不取自被校验的 §9 文档——
    否则"删掉 §9 里最早的几行"就能把窗口抬高、把早期 run 挤出检查范围（N6 实测的绕过路径）。
    文档侧只参与**区间比对**：§9 最早一行不得晚于账本窗口起点。

    `window_start` 由 `evaluate()` 统一推导后传入（与 `check_c1` 同一个窗口；
    单独调用时传 None 则本函数自行推导，语义相同）。
    `sprint["malformed"]`（首列 `run-…` 但列数 <5 的行）逐条点名：这些行**等于没登记**，
    静默丢掉它们会让"登记了"与"闸门认了"两件事悄悄分叉（N8 一族）。
    """
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
    for r in scoped:
        if r.get("run_id") not in table_ids:
            problems.append(f"[linkage] 账本有 run 但 §9 run 表未登记：{r.get('run_id')}")

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


def check_c3(policy: AgentPolicy, sprint: dict, runs: list[dict], att: Attribution) -> list[str]:
    """C3 覆盖闭环：锚点存在、每个提交有归属、且与 §9 声明的覆盖口径一致。"""
    problems: list[str] = []
    if not sprint.get("anchor"):
        problems.append("[C3] 未声明三查锚点（`三查锚点: <sha>`）→ 无法判定三查是否失效")
        return problems

    # **空区间 ≠ 通过**（2026-09-23 二查 critical 实测）：锚点 == HEAD 时 `rev_list` 为空集，
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
        problems.append(
            f"[C3] 锚点 {sprint['anchor'][:8]}→HEAD 有 {len(unowned)} 个提交无归属（run 窗口/例外表/"
            f"doc-only 都不覆盖）：" + ", ".join(s[:10] for s in unowned[:8])
            + (" …" if len(unowned) > 8 else ""))

    # §9 行声明的覆盖范围必须与账本一致（防"文档写了覆盖、账本没有窗口"）。
    # N6（2026-09-25 二查）：原先**只比对 `scope_source`** → §9 把 role/target 写错也 PASS。
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
             att: Attribution | None = None, check_coverage: bool = True) -> list[str]:
    """返回失败原因列表（空 = 通过）。三条不变式 + 需求（全部数据驱动）。

    **关闭窗口只推导一次**：C1 的判定域（D1）与 §9↔账本的区间比对（N6）
    必须用**同一个**窗口，两处各推一次＝两套口径，而口径分叉正是本卡要治的
    形态（"工具一个口径、闸门另一个口径"）。
    """
    problems: list[str] = []
    window_start = ledger_close_window(policy, runs)
    problems += check_requirements(policy, runs)
    problems += check_c1(policy, runs, window_start)
    problems += check_c2(policy, runs)
    problems += check_linkage(policy, sprint, runs, window_start)
    if check_coverage:
        if att is None:
            problems.append("[C3] 覆盖检查已启用但未提供归属计算结果（内部错误）")
        else:
            problems += check_c3(policy, sprint, runs, att)
    return problems


# ------------------------------------------------------- 自检 fixture（合成政策 + 合成历史）

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
    "close_gate": {
        "scope_ref_step": "scope",
        "coverage": {"exceptions_file": "coverage-exceptions.json",
                     "doc_only_globs": ["docs/**"]},
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

    覆盖窗口 (SHA_A, SHA_D] 覆盖 B、C、D 三个提交。`unowned_extra=True` 时改写 run 的窗口
    使它们只覆盖到 SHA_C —— 于是 SHA_D（HEAD 本身）无归属，模拟"覆盖表/窗口落后于 HEAD"。
    """
    shas = [SHA_B, SHA_C, SHA_D]
    order = {SHA_D: 0, SHA_C: 1, SHA_B: 2, SHA_A: 3}
    windows = coverage_windows_from_runs(runs, policy)
    if unowned_extra:
        # HEAD 之后的收尾提交（本例即 SHA_D）没有任何 run 覆盖到：锚点→HEAD 覆盖未闭环
        windows = [type(w)(run_id=w.run_id, role=w.role, anchor=SHA_A, through=SHA_C,
                          from_run=True) for w in windows]
    return Attribution(anchor=SHA_A, head=SHA_D, shas=shas, order=order,
                       windows=windows, exceptions=list(exceptions or []), root=None)


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

    att = None
    if check_coverage:
        anchor = sprint.get("anchor") or ""
        head = head_sha(ROOT)
        exceptions: list[dict] = []
        cov = (policy.close_gate.get("coverage") or {})
        exc_file = cov.get("exceptions_file")
        if exc_file:
            try:
                exceptions = load_coverage_exceptions(ROOT / str(exc_file))
            except PolicyError as exc:
                print(f"CLOSE-READINESS-ERROR: {exc}")
                return 2
        att = attribution(ROOT, anchor, head, runs, exceptions, policy=policy)

    problems = evaluate(policy, sprint, runs, att=att, check_coverage=check_coverage)
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
          f"锚点 {(sprint.get('anchor') or '')[:8]}，覆盖提交 {len(att.shas) if att else 0}）")
    return 0


def _selfcheck() -> int:
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="verify_close_readiness_"))
    policy = _load_fixture_policy(tmp)
    runs = _fixture_runs()
    good = parse_sprint(_doc([
        {"run_id": r["run_id"], "role": r["role"], "target": r["task_id"],
         "scope_source": r.get("scope_source") or "-",
         "coverage": "core", "deviation": r.get("scope_deviation") or "-"} for r in runs],
        SHA_A))

    ok("自检 ⓪ 数据源完备（fanout 步骤 role 都有 spec + 全部显式声明 scope_required + 无死键）",
       policy.closure_problems() == [], f"problems={policy.closure_problems()[:2]}")
    ok("自检 ① 合规场景 + 覆盖闭环 → PASS",
       evaluate(policy, good, runs, att=_fixture_attribution(runs)) == [], "problems=[]")

    # ---- 变异用例：**从 fanout.json 自动生成**（不逐场景手写）----------------
    for step in policy.close_ledger_steps:
        mutant = [r for r in runs if r.get("role") != step.role]
        rows = [row for row in good["rows"] if row["role"] != step.role]
        p = evaluate(policy, parse_sprint(_doc(rows, SHA_A)), mutant, att=_fixture_attribution(mutant))
        ok(f"变异（自动生成）① 抽掉步骤 {step.order}:{step.step}（role={step.role}）→ FAIL",
           any("缺 run" in x for x in p), f"problems={p[:1]}")

    for role, targets in policy.role_targets().items():
        for target in targets:
            # 关键：**该 role 仍有别的 run**（这里造一个其它 target 的诱饵 run），否则报的是
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
                         att=_fixture_attribution(mutant))
            ok(f"变异（自动生成）② 抽掉 {role} 的 target={target!r}（保留同 role 诱饵 run）→ FAIL",
               any(f"缺 target={target!r}" in x for x in p), f"problems={p[:1]}")

    # ---- 三条不变式各自的反向对照 ----------------------------------------
    mutant = [dict(r, scope_source="", scope_deviation=None) if r["role"] == "code-review" else r
              for r in runs]
    p = evaluate(policy, good, mutant, att=_fixture_attribution(mutant))
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
                 att=_fixture_attribution(hist_runs))
    ok("D1 反向对照 a：窗口**之前**的评审 run 缺 scope 声明 → 不报告"
       "（历史不卷入；整条闸门仍 PASS）",
       p == [], f"problems={p[:2]}")

    inwin = _run("run-hist-901", "agent-onboarding-review", "onboarding-scan",
                 "2026-09-21T02:30:00+00:00", scope="", dev=None)
    inwin_runs = [*runs, inwin]
    p = evaluate(policy, parse_sprint(_doc(_rows(inwin_runs), SHA_A)), inwin_runs,
                 att=_fixture_attribution(inwin_runs))
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
    p = evaluate(policy, sp_bad, runs, att=_fixture_attribution(runs))
    ok("D2 反向对照：结构非法的 run 行（列数 <5）→ 逐条点名，不再静默丢",
       len(sp_bad["malformed"]) == 1 and len(sp_bad["rows"]) == len(runs)
       and any("表行结构非法" in x and "run-bad-999" in x for x in p),
       f"malformed={sp_bad['malformed']}")

    mutant = [dict(r, scope_source="impact-assessment:run-ghost-999") if r["role"] == "code-review" else r
              for r in runs]
    p = evaluate(policy, good, mutant, att=_fixture_attribution(mutant))
    ok("C2 反向对照：引用不存在的 run（幻影引用）→ FAIL",
       any("不存在的对象" in x for x in p), f"problems={p[:1]}")

    ghost_role = [*runs, _run("run-x-900", "no-such-role", "t", "2026-09-21T05:00:00+00:00")]
    p = evaluate(policy, good, ghost_role, att=_fixture_attribution(ghost_role))
    ok("C2 反向对照：账本出现无 spec 的 role（不认角色名）→ FAIL",
       any("无 spec 的 role" in x for x in p), f"problems={p[:1]}")

    # ---- spec 缺声明：封闭世界**是运行时不变量**（防"删声明即绕过 C1"）---------
    # 注意：TG-15 起该检查在 `load_policy()` 里直接抛 PolicyError（而不是"返回一个完好的
    # Policy、再让某个自检报出来"）——否则普通命令会带着缺口照常运行，而缺口正是绕过入口。
    (tmp / "specs" / "sneaky-role.md").write_text(
        '---\nname: sneaky-role\ndescription: 未声明 scope_required\nversion: "1.0.0"\n---\n',
        encoding="utf-8")
    try:
        _load_fixture_policy(tmp)
        ok("C1 反向对照：spec 缺 scope_required → 装载即 fail-closed", False, "未抛 PolicyError")
    except PolicyError as exc:
        ok("C1 反向对照：spec 缺 scope_required → 装载即 fail-closed（删声明绕不过 C1）",
           "未声明 scope_required" in str(exc), str(exc)[:110])

    # 迁移期口子必须**显式开启**、且拿掉后立刻回到 fail-closed（否则它就是"永久绕过开关"）
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
                 att=_fixture_attribution(runs))
    ok("C3 反向对照：未声明三查锚点 → FAIL", any("未声明三查锚点" in x for x in p), f"problems={p[:1]}")

    p = evaluate(policy, good, runs, att=_fixture_attribution(runs, unowned_extra=True))
    ok("C3 反向对照：锚点→HEAD 有未归属提交（窗口/表落后于 HEAD）→ FAIL 且点名 sha",
       any("无归属" in x and SHA_D[:10] in x for x in p), f"problems={p[:1]}")

    bad_exc = [{"sha": SHA_E, "class": "DOC-ONLY", "reason": "ok"},
               {"sha": "f" * 8, "class": "DOC-ONLY", "reason": "短 sha"}]
    p = evaluate(policy, good, runs, att=_fixture_attribution(runs, exceptions=bad_exc))
    ok("C3-T 反向对照：例外表短 sha → FAIL（例外必须 sha 钉死）",
       any("不是完整 40 位" in x for x in p), f"problems={p[:2]}")

    bad_exc = [{"sha": SHA_E, "class": "DOC-ONLY", "reason": "ok"},
               {"sha": "*" * 40, "class": "DOC-ONLY", "reason": "通配"}]
    p = evaluate(policy, good, runs, att=_fixture_attribution(runs, exceptions=bad_exc))
    ok("C3-T 反向对照：例外表含通配 sha → FAIL（禁止模式匹配未来提交）",
       any("含通配" in x for x in p), f"problems={p[:2]}")

    bad_exc = [{"sha": SHA_E, "class": "DOC-ONLY", "reason": ""}]
    p = evaluate(policy, good, runs, att=_fixture_attribution(runs, exceptions=bad_exc))
    ok("C3-T 反向对照：例外缺 reason → FAIL", any("缺 reason" in x for x in p), f"problems={p[:1]}")

    # ---- linkage 反向对照 -------------------------------------------------
    ghost = parse_sprint(_doc(good["rows"] + [{"run_id": "run-ghost-999", "role": "code-review",
                                               "target": "branch:main", "scope_source": "-",
                                               "coverage": "core", "deviation": "-"}], SHA_A))
    p = evaluate(policy, ghost, runs, att=_fixture_attribution(runs))
    ok("linkage 反向对照：§9 写了 run 但账本无记录 → FAIL",
       any("账本无记录" in x for x in p), f"problems={p[:1]}")

    # ---- N3 反向对照：target 判据必须是**精确匹配**（子串匹配 = 改名即可冒充）---------
    for tampered, expected_target in (("branch:windows-backup", "branch:windows"),
                                      ("branch:mainline", "branch:main"),
                                      ("OLD-working-tree-JUNK", "working-tree")):
        mutant = [dict(r, task_id=tampered) if exact_target(r) == expected_target else r for r in runs]
        rows = [{"run_id": r["run_id"], "role": r["role"], "target": r["task_id"],
                 "scope_source": r.get("scope_source") or "-", "coverage": "core",
                 "deviation": r.get("scope_deviation") or "-"} for r in mutant]
        p = evaluate(policy, parse_sprint(_doc(rows, SHA_A)), mutant, att=_fixture_attribution(mutant))
        ok(f"N3 反向对照：task_id={tampered!r} 不得冒充 target={expected_target!r}（精确匹配，子串不算）→ FAIL",
           any(f"缺 target={expected_target!r}" in x for x in p), f"problems={p[:1]}")

    # ---- N6a 反向对照：**删掉 §9 里最早的两行**不得让窗口抬高（窗口取自账本侧）-------
    p = evaluate(policy, parse_sprint(_doc(good["rows"][2:], SHA_A)), runs,
                 att=_fixture_attribution(runs))
    ok("N6 反向对照 a：§9 删掉最早两行 → 仍 FAIL（账本有 run 未登记 + 区间比对）",
       any("账本有 run 但 §9 run 表未登记" in x and "run-k-001" in x for x in p)
       and any("linkage/区间" in x for x in p), f"problems={p[:2]}")
    p = evaluate(policy, parse_sprint(_doc(good["rows"], SHA_A)), runs, att=_fixture_attribution(runs))
    ok("N6 正向对照：§9 行齐全时窗口比对不误报（好输入 rc=0）", p == [], f"problems={p[:1]}")

    # ---- N6b 反向对照：§9 的 role / target 写错 → FAIL（原先只比对 scope_source）------
    for field, bad in (("role", "doc-audit"), ("target", "branch:production")):
        rows = [dict(r) for r in good["rows"]]
        rows[2] = {**rows[2], field: bad}
        p = evaluate(policy, parse_sprint(_doc(rows, SHA_A)), runs, att=_fixture_attribution(runs))
        ok(f"N6 反向对照 b：§9 第 3 行 {field} 写错（{bad!r}）→ FAIL（role/target 一并比对）",
           any(f"{field}={bad!r} 与账本" in x for x in p), f"problems={p[:1]}")

    p = evaluate(policy, good, runs, att=_fixture_attribution(runs, unowned_extra=False),
                 check_coverage=False)
    ok("覆盖检查可关闭（CI 无 git 历史时的显式降级路径）", p == [], f"problems={p}")

    probe = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--sprint",
         "docs/iteration/sprint/__no_such_sprint__.md"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok("真数据模式对不存在的 Sprint 文档 fail-closed（退出 2，不静默放行）",
       probe.returncode == 2 and "CLOSE-READINESS-ERROR" in (probe.stdout + probe.stderr),
       f"rc={probe.returncode} out={(probe.stdout + probe.stderr).strip()[:60]}")

    real = registry_path()
    if real.exists():
        warn("真数据模式未在自检中执行（需 `--sprint <当前 Sprint 文档>`）",
             f"账本 {len(load_runs(real))} 条：{real}")
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


def main() -> int:
    if "--sprint" in sys.argv:
        path = Path(sys.argv[sys.argv.index("--sprint") + 1])
        return run_real_data(path, check_coverage="--no-coverage" not in sys.argv)
    return _selfcheck()


if __name__ == "__main__":
    raise SystemExit(main())

