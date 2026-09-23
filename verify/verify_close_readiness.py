"""TG-15：关闭前置闸门（offline）——**三条不变式 + 数据驱动**，替换原先的按角色硬编码判据。

历史（为什么改）：TG-11 ③b 版本把判据写成"按角色名逐条判断"——`CLOSE_ROLES` 写死 4 个角色、
二查必须含 `windows`/`main`、〇查必须早于二查……**每加一个步骤/角色/分支都要改这个文件**，
而"改代码"本身没有任何闸门在守（`TG-15` 卡的起因）。TG-15 之后：

    C1 声明完备：凡产出评审结论的 run 必须有 scope 声明（外部引用 或 自选理由）
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
    """解析 §9 结构化 run 表 + 三查锚点（容错：表格列数 ≥5 且首列以 run- 开头）。"""
    rows = []
    for line in doc.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in ROW_SPLIT.split(line)[1:-1]]
        if len(cells) >= 5 and cells[0].startswith("run-"):
            rows.append({
                "run_id": cells[0], "role": cells[1], "target": cells[2],
                "scope_source": cells[3], "coverage": cells[4],
                "deviation": cells[5] if len(cells) > 5 else "",
            })
    m = ANCHOR_RE.search(doc)
    return {"rows": rows, "anchor": m.group(1) if m else None}


def _spec_of(policy: AgentPolicy, role: str) -> dict:
    spec = policy.specs.get(role)
    return parse_frontmatter(spec.path) if spec else {}


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
            if not any(target in str(r.get("task_id") or "") for r in bucket):
                problems.append(
                    f"[C1/需求] 步骤 {step.order}:{step.step} 缺 target={target!r} 的 run"
                    f"（已有 task_id：{[str(r.get('task_id')) for r in bucket][:3]}）")

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


def check_c1(policy: AgentPolicy, runs: list[dict]) -> list[str]:
    """C1 声明完备：凡**产出评审结论**的 run（spec 声明 scope_required: true）必须有 scope 声明。"""
    problems: list[str] = []
    for r in runs:
        role = str(r.get("role") or "")
        if role not in policy.review_roles:
            continue
        source = str(r.get("scope_source") or "").strip()
        deviation = str(r.get("scope_deviation") or "").strip()
        if not source and not deviation:
            problems.append(f"[C1] {r.get('run_id')}（role={role}）产出评审结论但未声明 scope 来源，"
                            f"也无自选范围理由")
        elif source == "self-chosen" and not deviation:
            problems.append(f"[C1] {r.get('run_id')} 自选范围但未声明 deviation")
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
            if target.get("status") in {"failed", "cancelled"}:
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


def check_linkage(policy: AgentPolicy, sprint: dict, runs: list[dict]) -> list[str]:
    """§9 结构化表 ↔ 账本**双向**一致（防"写了没跑"/"跑了没写"）。"""
    problems: list[str] = []
    by_id = {r.get("run_id"): r for r in runs}
    ledger_roles = {s.role for s in policy.close_ledger_steps} | policy.review_roles
    table_ids = {row["run_id"] for row in sprint["rows"]}

    window = [str(r.get("started_at") or "") for row in sprint["rows"]
              if (r := by_id.get(row["run_id"])) is not None]
    window_start = min(window) if window else None
    scoped = [r for r in runs if r.get("role") in ledger_roles
              and (window_start is None or str(r.get("started_at") or "") >= window_start)]

    for rid in sorted(table_ids - set(by_id)):
        problems.append(f"[linkage] §9 写了 run 但账本无记录：{rid}")
    for r in scoped:
        if r.get("run_id") not in table_ids:
            problems.append(f"[linkage] 账本有 run 但 §9 run 表未登记：{r.get('run_id')}")
    return problems


def check_c3(policy: AgentPolicy, sprint: dict, runs: list[dict], att: Attribution) -> list[str]:
    """C3 覆盖闭环：锚点存在、每个提交有归属、且与 §9 声明的覆盖口径一致。"""
    problems: list[str] = []
    if not sprint.get("anchor"):
        problems.append("[C3] 未声明三查锚点（`三查锚点: <sha>`）→ 无法判定三查是否失效")
        return problems

    problems += [f"[C3-T] {p}" for p in att.exception_problems()]

    globs = tuple((policy.close_gate.get("coverage") or {}).get("doc_only_globs") or ())
    unowned = att.unowned(globs)
    if unowned:
        # 失效方向反转（用户 P2 关切）：表没跟上 → 默认 FAIL 并**逐条点名**
        problems.append(
            f"[C3] 锚点 {sprint['anchor'][:8]}→HEAD 有 {len(unowned)} 个提交无归属（run 窗口/例外表/"
            f"doc-only 都不覆盖）：" + ", ".join(s[:10] for s in unowned[:8])
            + (" …" if len(unowned) > 8 else ""))

    # §9 行声明的覆盖范围必须与账本一致（防"文档写了覆盖、账本没有窗口"）
    by_id = {r.get("run_id"): r for r in runs}
    for row in sprint["rows"]:
        run = by_id.get(row["run_id"])
        if run is None:
            continue
        declared_source = str(row.get("scope_source") or "").strip()
        actual_source = str(run.get("scope_source") or "").strip()
        if declared_source not in {"-", ""} and declared_source != actual_source:
            problems.append(f"[C3] §9 表 {row['run_id']} 的 scope_source={declared_source!r} "
                            f"与账本 {actual_source!r} 不一致")
    return problems


def evaluate(policy: AgentPolicy, sprint: dict, runs: list[dict], *,
             att: Attribution | None = None, check_coverage: bool = True) -> list[str]:
    """返回失败原因列表（空 = 通过）。三条不变式 + 需求（全部数据驱动）。"""
    problems: list[str] = []
    problems += check_requirements(policy, runs)
    problems += check_c1(policy, runs)
    problems += check_c2(policy, runs)
    problems += check_linkage(policy, sprint, runs)
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
                         unowned_extra: bool = False) -> Attribution:
    """合成历史：锚点 = SHA_A（最旧），HEAD = SHA_D（最新），中间 SHA_B/SHA_C（新→旧 D,C,B,A）。

    覆盖窗口 (SHA_A, SHA_D] 覆盖 B、C、D 三个提交。`unowned_extra=True` 时改写 ran 的窗口
    使它们只覆盖到 SHA_C —— 于是 SHA_D（HEAD 本身）无归属，模拟"覆盖表/窗口落后于 HEAD"。
    """
    shas = [SHA_B, SHA_C, SHA_D]
    order = {SHA_D: 0, SHA_C: 1, SHA_B: 2, SHA_A: 3}
    windows = _windows(runs)
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
        att = attribution(ROOT, anchor, head, runs, exceptions)

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

