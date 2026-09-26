#!/usr/bin/env python3
"""闸门可信度：`-O` 守卫 + 棘轮上限**只许下调**（2026-09-25，Sprint-17 关闭期交付）。

## 为什么需要这条闸门（两条都已实测）

**① 裸 `assert` 承担判定 ⇒ `-O` 下一套闸门空转并打印 `ALL PASS`**（3-LEARNED 1.65）：
`verify/verify_lint.py` 的 A/B 级硬闸门只用 `ok()
` 内的裸 `assert` 承担判定 ⇒ 同一份含 1 处
`F821` 的样本，正常档 `rc=1`，
`PYTHONOPTIMIZE=1` 档 **`rc=0` 且打印 `ALL PASS (11 assertions)`**
（`run-2026-09-25-lessons-learned-073` 在冻结 HEAD 副本上实测）。
套件 `run_suite.py` 起子进程时
不构造 `env=`（继承父环境）⇒ 一个环境变量能把整套闸门变成"永远绿"。

**② 棘轮上限是自声明数据，没有任何机制阻止"调高即变绿"**（3-LEARNED 1.66）：
`lint_readability_ratchet.caps.E501 =
2631` 而冻结 HEAD 实测 **2615/2616** ⇒ 中间约 16 条新增
违规被"上限"静默吸收（注入 16 条 → `rc=0`，日志自我认证 `2631/2631`）；注入 17 条才 `rc=1`。
同族的还有 `md_table_legacy_files.files`、`ledger_measurement.legacy_ratchet.caps`、
`derived_numbers.baseline`、`artifact_paths` 的动态目标上限。

## 判据（配置来自 `agents/policy.json::gate_integrity`）

1. **守卫行在位**：`guard_required`
列出的每个闸门必须含 `guard_line`（默认 `assert __debug__`），
   缺一个即 FAIL（`-O` 下 `__debug__` 为 `False` ⇒ 立即失败退出，不会打印成功行）；
2. **动态证明**：真实跑一次 `python -O
<probe_gate> --selftest` ⇒ **必须非零退出**且输出点名
   `__debug__`（静态检查只能证明"写了这行"，这条证明"这行真的拦得住"）；
3. **棘轮上限只许下调**：`ratchets` 列出的每个上限表，与其在 `git HEAD:
agents/policy.json`
   的对应值逐项比较——**任何上调即 FAIL**（新增键放行：新文件/新规则出现是正常的；
   删键放行：
   删掉上限 = 该类回到严格判定，方向更紧）；
4. **每个棘轮必须带未过期的 `review_by`**：缺 `review_by` 或已过期 → FAIL
   （没有到期日的豁免就是永久豁免）；
5. **覆盖面可见**：未被 `guard_required` 收录的 `verify/verify_*.py` 逐条打 **WARN**
   （存量不回溯改造，但缺口必须看得见，不得静默）。

## 反向对照（`--selftest`）

上限上调 → FAIL；下调/新增键/删键 → PASS；`review_by` 过期或缺席 → FAIL；
守卫行缺席（fixture 文件）→ FAIL 且点名文件；`-O` 探针必须红。

## 用法

    .venv\\Scripts\\python.exe verify\\verify_gate_integrity.py             # 真数据 + fixture 反向对照
    .venv\\Scripts\\python.exe verify\\verify_gate_integrity.py --selftest  # 只跑 fixture 反向对照
"""

from __future__ import annotations

VERIFY_META = {'features': '闸门可信度：-O/PYTHONOPTIMIZE 守卫行在位（含真实 -O 探针必须红）+ 棘轮上限与 git HEAD 逐项比较（只许下调、上调即 FAIL）+ review_by 必填未过期 + 未覆盖闸门逐条 WARN；含 7 条反向对照自检', 'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 6, 'routes': [], 'requires': ['none']}

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import load_policy  # noqa: E402

if not __debug__:  # noqa: SIM108 —— -O/PYTHONOPTIMIZE 会剥离 assert；守卫必须是普通语句，不能是 assert
    raise SystemExit("本闸门不得在 -O/PYTHONOPTIMIZE 下运行（`__debug__` 为 False ⇒ 判据会被整体剥离）——见 3-LEARNED 1.65")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_CFG = load_policy()._data("gate_integrity")  # noqa: SLF001 —— 政策读取器同源
GUARD_LINE: str = str(_CFG["guard_line"])
GUARD_REQUIRED: tuple[str, ...] = tuple(str(p) for p in _CFG["guard_required"])
PROBE_GATE: str = str(_CFG["probe_gate"])
PROBE_ARGS: tuple[str, ...] = tuple(str(a) for a in _CFG.get("probe_args") or ())
RATCHETS: tuple[tuple[str, str], ...] = tuple((str(r["pointer"]), str(r["review_by_pointer"]))
                                              for r in _CFG["ratchets"])
POLICY_REL = "agents/policy.json"
# A-M12 ①（2026-09-25 D4）：结构守卫"不可跳过层"的三处接线（见
# `unskippable_guard_problems`）。
# 路径是**本闸门要核的事实**（CI 文件、钩子模板、安装器），不是政策阈值 ⇒ 留在这里。
CI_REL = ".github/workflows/ci.yml"
HOOK_REL = "scripts/hooks/pre-commit"
COMMITHOOK_REL = "scripts/hooks/commit-msg"
INSTALLER_REL = "scripts/install-hooks.py"
PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    assert cond, f"{name} FAIL: {detail}"
    PASSED += 1
    print(f"PASS: {name} {detail}")


def warn(name: str, detail: str = "") -> None:
    print(f"WARN: {name} {detail}")


def dig(data: dict, pointer: str):
    """按 `a.b.c` 取值；任一段缺失 → None（调用方决定 fail-closed 方向）。"""
    cur = data
    for part in pointer.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def git_policy(rev: str = "HEAD", rel: str = POLICY_REL) -> dict | None:
    try:
        proc = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=str(ROOT), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def ratchet_problems(current: dict, previous: dict | None, *, today: str,
                     pointers: tuple[tuple[str, str], ...]) -> tuple[list[str], list[str]]:
    """纯函数：上限单调性 + `review_by` 在位未过期。返回 (problems, warnings)。"""
    problems: list[str] = []
    warnings: list[str] = []
    for pointer, review_pointer in pointers:
        caps = dig(current, pointer)
        if not isinstance(caps, dict):
            problems.append(f"[棘轮] {POLICY_REL}::{pointer} 不存在或不是对象——判据无从执行（fail-closed）")
            continue
        review_by = dig(current, review_pointer)
        if not review_by:
            problems.append(f"[棘轮] {pointer} 缺 {review_pointer}——没有到期日的豁免 = 永久豁免")
        elif str(review_by) < today:
            problems.append(f"[棘轮] {pointer} 的 review_by={review_by} 已过期（今日={today}）"
                            f"→ 必须重评基线，不得静默延期")
        # `measured_total`（若声明）必须**等于上限之和**：
        # 否则它就是"自己声明了一个比实测更高的总数"，
        # 与"cap 记在实测之上"同族（2026-09-25 复核 #3 finding：实测 2833 已过期、
        # 四类实际合计 2815）。
        # 要么把它改对，要么删掉这个字段——留着它就是**第二份会漂的声明**。
        parent = pointer.rsplit(".", 1)[0] if "." in pointer else ""
        total = dig(current, f"{parent}.measured_total") if parent else None
        if isinstance(total, int):
            s = sum(v for v in caps.values() if isinstance(v, int))
            if total != s:
                problems.append(
                    f"[棘轮] {pointer} 的 {parent}.measured_total={total} ≠ 上限之和 {s}"
                    f"（差 {total - s}）——改对或删掉该字段；留着一个没人读的『实测总数』"
                    f"就是静默配额的另一种写法")
        # ---- M-C（TG-19，2026-09-25 D3）：把重评时的**实测值钉进政策** -------------
        # 为什么需要：原判据只与 `git HEAD` 比较 ⇒ 只拦得住**未提交**的上调；
        # 一次**已提交**的放宽即成为新基线（复核机制缺口 2 / 3-LEARNED 1.66）。
        # 下面三条把"cap 记在实测之上"变成可机检的事实，
        # `committed_rebase_problems()` 再把"提交态放宽"变成**具名事件**。
        measured_ptr = f"{parent}.measured_value" if parent else "measured_value"
        measured_at_ptr = f"{parent}.measured_at" if parent else "measured_at"
        measured = dig(current, measured_ptr)
        measured_at = dig(current, measured_at_ptr)
        if not measured_at:
            problems.append(f"[棘轮] {pointer} 缺 {measured_at_ptr}——没有测量日期的"
                            f"实测快照无法判断它是否还对应这批上限（fail-closed）")
        if not isinstance(measured, dict):
            problems.append(f"[棘轮] {pointer} 缺 {measured_ptr}（对象）——没有实测快照"
                            f"就无法判定『上限是否记在实测之上』；cap 因此可能是静默配额")
        else:
            for key, value in sorted(caps.items()):
                if key not in measured:
                    problems.append(f"[棘轮] {measured_ptr} 缺键 {key!r}——上限表里有、"
                                    f"快照里没有 ⇒ 该键的上限无从对照（fail-closed）")
                    continue
                try:
                    cap_v, meas_v = int(value), int(measured[key])
                except (TypeError, ValueError):
                    problems.append(f"[棘轮] {pointer}.{key} 或 {measured_ptr}.{key} "
                                    f"不是整数（cap={value!r} measured={measured[key]!r}）")
                    continue
                if cap_v > meas_v:
                    problems.append(
                        f"[棘轮] {pointer}.{key} 的上限 {cap_v} **高于**重评时的实测 "
                        f"{meas_v}（{measured_at_ptr}={measured_at}）⇒ cap 记在实测之上 = "
                        f"给新增违规发**静默配额**；要么把 cap 降到实测，要么走一次"
                        f"『重评基线』（同时改 measured_value 并写 rebased_at + 理由）")
            for key in sorted(set(measured) - set(caps)):
                problems.append(f"[棘轮] {measured_ptr} 多出键 {key!r}（上限表里没有）"
                                f"——实测值里留着没人读的键 = 死数据/拼写漂移")
            if isinstance(total, int):
                ms = sum(v for v in measured.values() if isinstance(v, int))
                if ms != total:
                    problems.append(
                        f"[棘轮] {parent}.measured_total={total} ≠ 实测快照之和 {ms}"
                        f"（差 {total - ms}）——『实测总数』必须同时等于 Σcaps 与"
                        f" Σmeasured_value")
        if previous is None:
            warnings.append(f"{pointer}: 无 git HEAD 可比基准（新分支/未入库）——本次只判 review_by")
            continue
        prev_caps = dig(previous, pointer)
        if not isinstance(prev_caps, dict):
            warnings.append(f"{pointer}: HEAD 版无此上限表（本批新增）——无从比较单调性")
            continue
        for key, value in sorted(caps.items()):
            if key not in prev_caps:
                continue  # 新增键 = 新对象进入棘轮，方向更紧/等价，放行
            try:
                old, new = int(prev_caps[key]), int(value)
            except (TypeError, ValueError):
                problems.append(f"[棘轮] {pointer}.{key} 不是整数（{value!r}）——棘轮上限必须是数字")
                continue
            if new > old:
                problems.append(f"[棘轮] 上限被**上调**：{pointer}.{key} {old} → {new}"
                                f"（上限只许下调；要放宽必须走『重评基线』并改 review_by，"
                                f"而不是改数字——否则新增违规会被静默吸收）")
    return problems, warnings


def committed_rebase_problems(committed: dict | None, parent_policy: dict | None, *,
                              pointers: tuple[tuple[str, str], ...]) -> list[str]:
    """**提交态的放宽必须是一次具名事件**（M-C / `TG-19`）。

    背景（复核机制缺口 2）：`ratchet_problems` 比的是"工作区 vs `git HEAD`"⇒ 它只能拦住
    **未提交**的上调；一次**已提交**的放宽立刻成为新基线（`measured_total` 也可同步抬），
    事后没有任何装置能看出它被放宽过。本函数比的是 **`HEAD` vs `HEAD~1`**：只要上一个
    提交抬高了某个 `cap`（或抬高 `measured_value` 来"配合"），该棘轮块就必须带
    **`rebased_at` + `rebased_reason`（≥10 字符）**——把盲区变成一条可审计的记录。
    **它不判"这次放宽是否合理"**（那是评审的事），只保证"放宽有人署名、有理由、有日期"。
    """
    problems: list[str] = []
    if committed is None or parent_policy is None:
        return problems
    for pointer, _review in pointers:
        new_caps, old_caps = dig(committed, pointer), dig(parent_policy, pointer)
        if not isinstance(new_caps, dict) or not isinstance(old_caps, dict):
            continue
        raised = [k for k, v in sorted(new_caps.items())
                  if k in old_caps and isinstance(v, int)
                  and isinstance(old_caps[k], int) and v > old_caps[k]]
        block = pointer.rsplit(".", 1)[0] if "." in pointer else ""
        mv_ptr = f"{block}.measured_value" if block else "measured_value"
        new_mv, old_mv = dig(committed, mv_ptr), dig(parent_policy, mv_ptr)
        raised_mv: list[str] = []
        if isinstance(new_mv, dict) and isinstance(old_mv, dict):
            raised_mv = [k for k, v in sorted(new_mv.items())
                         if k in old_mv and isinstance(v, int)
                         and isinstance(old_mv[k], int) and v > old_mv[k]]
        if not (raised or raised_mv):
            continue
        rebased_at = dig(committed, f"{block}.rebased_at") if block else None
        reason = dig(committed, f"{block}.rebased_reason") if block else None
        if not rebased_at or not reason or len(str(reason).strip()) < 10:
            problems.append(
                f"[棘轮/提交态] {pointer} 在上一个提交（HEAD）里被**上调**"
                f"（cap: {raised or '—'}；measured_value: {raised_mv or '—'}）"
                f"却没有 `{block}.rebased_at` + `{block}.rebased_reason`（≥10 字符）⇒ "
                f"提交态的放宽必须是一次**具名事件**（谁、何时、依据哪次实测）；"
                f"补上这两个字段，或把上限改回去")
            continue
        # **署名必须绑定到它授权的那组数值**（2026-09-25 独立复核 `run-…083` major）：
        # 光有 `rebased_at` + 理由不够——"先降后升"可以复用上一次的旧署名绕过。
        # 现要求 `rebased_from` 逐键等于**父提交**里被抬高那些键的值：
        # 旧署名对不上新数值 ⇒ FAIL。
        rebased_from = dig(committed, f"{block}.rebased_from") if block else None
        before: dict = {}
        for k in raised:
            before[k] = old_caps.get(k)
        for k in raised_mv:
            before.setdefault(k, old_mv.get(k))
        if not isinstance(rebased_from, dict):
            problems.append(
                f"[棘轮/提交态] {pointer} 抬高了 {sorted(before)} "
                f"但缺 `{block}.rebased_from`"
                f"（**这次重评授权前的数值**）⇒ 无法判断署名是不是**这一次**的"
                f"（'先降后升 + 复用旧署名'正是这样绕过的）")
        else:
            stale = {k: (rebased_from.get(k), v) for k, v in before.items()
                     if rebased_from.get(k) != v}
            if stale:
                problems.append(
                    f"[棘轮/提交态] {pointer} 的 `{block}.rebased_from` "
                    f"与父提交实测不符"
                    f"（键: {{键: (rebased_from, 父提交值)}} = {stale}）"
                    f"⇒ 署名**不是这一次**的"
                    f"（旧署名被复用）；把 `rebased_from` 更新为本次重评前的数值")
    return problems


def _invokes_guard(text: str) -> bool:
    """该文件是否在**命令位置**调用了结构守卫的 git 档
    （`structure-guard.py verify --from-git`）。

    为什么不能只做子串搜索（二查 `run-…-087` major 1 的探针实测）：CI 里那行
    `Write-Host "gate: structure-guard.py verify --from-git …"`
    的**标签文本本身**就满足子串匹配
    ⇒ 把真调用删掉、只留标签，判据照样"零问题"。于是"接线判据"守的是一句**注释**，
    不是一条命令。
    判据改为：**跳过注释/回显行**（`#`、`Write-Host`、`echo`、`::`
    标签），再看剩下的行里有没有该调用
    ——与"守卫必须挂在真函数上"同一族（反例档案例 14）。
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "Write-Host", "echo", "::")):
            continue
        if re.search(r"structure-guard\.py\s+verify\s+--from-git", stripped):
            return True
    return False


HOOKS_TUPLE_RE = re.compile(r"HOOKS\s*=\s*\((?P<body>[^)]*)\)", re.S)


def _installs_hooks(text: str) -> bool:
    """安装器的 `HOOKS = (…)` 清单里必须**同时**含 `pre-commit` 与 `commit-msg`。

    修复验证复核 `run-…-091` minor 2 的原始形态：判据只核 `installer.is_file()` 与
    文本含 `--check`，**不核它装哪些钩子** ⇒ 把 `HOOKS = ("pre-commit", "commit-msg")`
    改成 `HOOKS = ("pre-commit",)`（模板仍在、仍调判据）时四处接线判据
    全绿。而在 `pre-commit` 改为 `--report-only` 之后，**本地层的终判压在 `commit-msg`
    上**（`pre-commit` 读不到署名 ⇒ 不判）——少了它，本地层对结构删除**既不拦也不判**，
    只剩 CI 一层。这是"模板存在"与"模板会被装上"之间的缺口。
    """
    m = HOOKS_TUPLE_RE.search(text)
    if not m:
        return False
    body = m.group("body")
    return "pre-commit" in body and "commit-msg" in body


def unskippable_wiring_problems(*, ci: Path, hook: Path, installer: Path,
                                commithook: Path | None = None) -> list[str]:
    """③ 判据本体（A-M12 ①）：结构守卫的「**不可跳过层**」三处接线必须在位。

    要治的形态（本仓实测过的那条）：守卫**有效**但**依赖人记得跑**——快照档的前提是
    "编辑前先 `snapshot`"，而 R1 第 6 次事故恰恰是"规则写了没执行"。修法分两层：
      * **便利层** = `scripts/hooks/pre-commit`（模板入库；`.git/hooks/`
      不在版本控制里，
        故配 `scripts/install-hooks.py` 安装 + `--check` 核对）；
      * **不可跳过层** = CI 里那条 `structure-guard.py verify --from-git <base>`——
        CI 每次 push 都会跑，基线取自 **git**（不是本地快照），"忘没忘"不再影响判据。
    本判据只认**可核的接线事实**：CI
    文件里必须有那条调用、模板必须存在且调用**同一条命令**
    （两层各判一套＝同一个字段两种读法）。它**不**声称"钩子一定装上了"——那只在 `.git/`
    里，
    版本控制看不见；这层边界照实说。

    落点由调用方**显式传入**（`unskippable_guard_problems` 用仓库路径，自检用 `%TEMP%`
    里的
    字面量探针）——这样自检的写盘目标可以写成"`Path(tempfile.gettempdir())` + 字面量"的
    单一表达式，满足 `verify_artifact_paths.py` 的静态可判定要求（第一版把落点交给变量，
    被该闸门当场判为 2 处动态目标）。
    """
    problems: list[str] = []
    if not ci.is_file():
        problems.append(f"[不可跳过] {CI_REL} 不存在——"
                        f"结构守卫的不可跳过层只能接在 CI 上（fail-closed）")
    elif not _invokes_guard(ci.read_text(encoding="utf-8", errors="replace")):
        problems.append(
            f"[不可跳过] {CI_REL} 里**命令位置**没有 `structure-guard.py verify "
            f"--from-git …`"
            f"（标签/注释里的同名字样不算）——守卫就退回『依赖人记得跑快照』的形态"
            f"（R1 第 6 次事故的根因）")
    if not hook.is_file():
        problems.append(f"[不可跳过] {HOOK_REL} 模板不存在"
                        f"（便利层缺失；CI 层仍在，但本地无即时拦截）")
    elif not _invokes_guard(hook.read_text(encoding="utf-8", errors="replace")):
        problems.append(f"[不可跳过] {HOOK_REL} 没有调用与 CI **同一条**判据"
                        f"（两层各判一套＝同一个字段两种读法）")
    # `commit-msg`（修复验证复核 `run-…-089` major ⇒ 二查 087-major-3）：
    # **带署名的那一半**。
    # `pre-commit` 跑在"提交信息还不存在"的时刻 ⇒ 它永远读不到 `Structure-Removal:`，
    # 合法结构删除在本地只能 `--no-verify`（两层判据不一致）。缺它即 FAIL。
    chook = commithook
    if not chook.is_file():
        problems.append(f"[不可跳过] {COMMITHOOK_REL} 模板不存在（`pre-commit` 读不到"
                        f"待提交信息里的署名 ⇒ 合法结构删除在本地只能 `--no-verify`）")
    elif not _invokes_guard(chook.read_text(encoding="utf-8", errors="replace")):
        problems.append(f"[不可跳过] {COMMITHOOK_REL} 没有调用与 CI **同一条**判据")
    elif "--ack-file" not in chook.read_text(encoding="utf-8", errors="replace"):
        problems.append(f"[不可跳过] {COMMITHOOK_REL} 没有把**待提交信息文件**交给判据"
                        f"（缺 `--ack-file` ⇒ 署名形同不存在）")
    if not installer.is_file():
        problems.append(f"[不可跳过] {INSTALLER_REL} 不存在——`.git/hooks/` "
        f"不在版本控制里，"
                        f"没有安装器就只剩『记得手动拷』")
    elif "--check" not in installer.read_text(encoding="utf-8", errors="replace"):
        problems.append(f"[不可跳过] {INSTALLER_REL} 缺 `--check` "
        f"档——『装没装』必须可核")
    elif not _installs_hooks(installer.read_text(encoding="utf-8", errors="replace")):
        problems.append(
            f"[不可跳过] {INSTALLER_REL} 的 `HOOKS` 清单没有**同时**装 "
            f"`pre-commit` 与 `commit-msg`（复核 `091` minor 2：`pre-commit` 已改为 "
            f"`--report-only`，本地层的**终判整个压在 `commit-msg` 上** ⇒ 少了它，"
            f"本地层对结构删除既不拦也不判，只剩 CI 一层）")
    return problems


def unskippable_guard_problems(root: Path = ROOT) -> list[str]:
    """③ 真数据入口：把四处接线落点解析到 `<root>/…` 后交给判据本体。"""
    return unskippable_wiring_problems(ci=root / CI_REL, hook=root / HOOK_REL,
                                       installer=root / INSTALLER_REL,
                                       commithook=root / COMMITHOOK_REL)


def guard_problems(root: Path = ROOT) -> tuple[list[str], list[str]]:
    """① 守卫行在位（静态）+ 覆盖面 WARN。"""
    problems: list[str] = []
    warnings: list[str] = []
    for item in GUARD_REQUIRED:
        path = root / item
        if not path.is_file():
            problems.append(f"[守卫] {item} 不存在（guard_required 是显式清单，缺文件即 FAIL）")
            continue
        if GUARD_LINE not in path.read_text(encoding="utf-8", errors="replace"):
            problems.append(f"[守卫] {item} 缺 `{GUARD_LINE}`——`-O`/`PYTHONOPTIMIZE=1` 下它的判据"
                            f"会被整体剥离却照常打印成功行（3-LEARNED 1.65）")
    covered = {Path(p).name for p in GUARD_REQUIRED}
    for path in sorted((root / "verify").glob("verify_*.py")):
        if path.name not in covered:
            warnings.append(f"{path.relative_to(root).as_posix()} 未列入 guard_required "
                            f"（存量不回溯；缺口可见，见 §判据 5）")
    return problems, warnings


def probe_o_mode(root: Path = ROOT) -> list[str]:
    """② 动态证明：`guard_required` 里**每一个**闸门在 `-O` 下都必须**非零退出且不打印成功行**。

    2026-09-25 修复验证复核 finding (ii)：原实现只跑 `probe_gate` 一条（等于自证），
    其余 7 条只靠"文本里有那行"（静态）——静态检查证明不了那行**真的拦得住**。
    现逐个真跑；判据 = `rc != 0` **且** 输出里没有 `ALL PASS`（"不打印成功行"才是要害；
    措辞里是否含 `__debug__` 只作附注、不作判据——有的闸门由更早的守卫分支以 rc=2 退出）
    。
    """
    problems: list[str] = []
    for rel in (list(GUARD_REQUIRED) or [PROBE_GATE]):
        gate = root / rel
        if not gate.is_file():
            problems.append(f"[守卫] 探针闸门 {rel} 不存在——`-O` 动态证明无从执行（fail-closed）")
            continue
        args = tuple(PROBE_ARGS) if rel == PROBE_GATE else ()
        cmd = [sys.executable, "-O", str(gate), *args]
        try:
            proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=300)
        except (OSError, subprocess.SubprocessError) as exc:
            problems.append(f"[守卫] `-O` 探针无法执行 {rel}（{type(exc).__name__}: {exc}）——fail-closed")
            continue
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0:
            problems.append(f"[守卫] `-O` 下 {rel} **退 0** ——该闸门在 `-O` 里静默通过"
                            f"（判据被剥离）；守卫行没起作用")
        elif "ALL PASS" in out:
            problems.append(f"[守卫] `-O` 下 {rel} 虽非零退出（rc={proc.returncode}）却仍打印了 "
                            f"`ALL PASS`——成功行与退出码互相矛盾（本 Sprint 要治的失信形态）")
    return problems


def selftest() -> int:
    today = "2026-09-25"
    pointers = (("lint_readability_ratchet.caps", "lint_readability_ratchet.review_by"),)

    def _blk(caps: dict, *, measured: dict | None = None,
             review: str | None = "2099-01-01",
             measured_at: str | None = "2026-09-25", **extra) -> dict:
        """构造一个棘轮块（M-C 起 `measured_value` / `measured_at` 是**必备**字段）。"""
        blk: dict = {"caps": caps,
                     "measured_value": dict(caps) if measured is None else measured}
        if review is not None:
            blk["review_by"] = review
        if measured_at is not None:
            blk["measured_at"] = measured_at
        blk.update(extra)
        return blk

    cur = {"lint_readability_ratchet": _blk({"E501": 10})}
    prev = {"lint_readability_ratchet": {"caps": {"E501": 10}}}
    problems, _ = ratchet_problems(cur, prev, today=today, pointers=pointers)
    ok("反向对照 A 上限不变 → PASS", problems == [], f"problems={problems[:1]}")
    raised = {"lint_readability_ratchet": _blk({"E501": 11}, measured={"E501": 11})}
    problems, _ = ratchet_problems(raised, prev, today=today, pointers=pointers)
    ok("反向对照 B 上限上调（10 → 11）→ FAIL",
       any("上调" in p for p in problems), f"problems={problems[:1]}")
    lowered = {"lint_readability_ratchet": _blk({"E501": 9})}
    problems, _ = ratchet_problems(lowered, prev, today=today, pointers=pointers)
    ok("反向对照 C 上限下调（10 → 9）→ PASS（收紧永远放行）", problems == [], f"problems={problems[:1]}")
    added = {"lint_readability_ratchet": _blk({"E501": 10, "D103": 5})}
    problems, _ = ratchet_problems(added, prev, today=today, pointers=pointers)
    ok("反向对照 D 新增上限键 → PASS（新对象进入棘轮）", problems == [], f"problems={problems[:1]}")
    removed = {"lint_readability_ratchet": _blk({})}
    problems, _ = ratchet_problems(removed, prev, today=today, pointers=pointers)
    ok("反向对照 E 删除上限键 → PASS（回到严格判定，方向更紧）", problems == [], f"problems={problems[:1]}")
    expired = {"lint_readability_ratchet": _blk({"E501": 10}, review="2020-01-01")}
    problems, _ = ratchet_problems(expired, prev, today=today, pointers=pointers)
    ok("反向对照 F review_by 过期 → FAIL", any("已过期" in p for p in problems), f"problems={problems[:1]}")
    missing = {"lint_readability_ratchet": {"caps": {"E501": 10}}}
    problems, _ = ratchet_problems(missing, prev, today=today, pointers=pointers)
    ok("反向对照 G 缺 review_by → FAIL（没有到期日的豁免 = 永久豁免）",
       any("没有到期日" in p for p in problems), f"problems={problems[:1]}")
    # 反向对照 I（2026-09-25 复核 #3 finding）：`measured_total` 与上限之和必须相等——
    # 实测它曾停在 2833 而四类合计 2815（"没人读的第二份声明"，同族形态）。
    skewed = {"lint_readability_ratchet": _blk({"E501": 10}, measured_total=18)}
    problems, _ = ratchet_problems(skewed, prev, today=today, pointers=pointers)
    ok("反向对照 I `measured_total` ≠ 上限之和 → FAIL（第二份会漂的声明）",
       any("measured_total" in p and "上限之和" in p for p in problems), f"problems={problems[:1]}")
    aligned = {"lint_readability_ratchet": _blk({"E501": 10}, measured_total=10)}
    problems, _ = ratchet_problems(aligned, prev, today=today, pointers=pointers)
    ok("反向对照 I2 二者相等 → PASS（防假红）", problems == [], f"problems={problems[:1]}")

    # ---- M-C（TG-19 D3）：棘轮完整性（实测值钉死 + 提交态放宽具名）----------------
    no_meas = {"lint_readability_ratchet": {"caps": {"E501": 10},
                                            "review_by": "2099-01-01",
                                            "measured_at": "2026-09-25"}}
    problems, _ = ratchet_problems(no_meas, prev, today=today, pointers=pointers)
    ok("M-C 反向对照 J 缺 `measured_value` → FAIL（没有实测快照 ⇒ cap 可能是静默配额）",
       any("measured_value" in p and "缺" in p for p in problems),
       f"problems={problems[:1]}")
    no_date = {"lint_readability_ratchet": _blk({"E501": 10}, measured_at=None)}
    problems, _ = ratchet_problems(no_date, prev, today=today, pointers=pointers)
    ok("M-C 反向对照 K 缺 `measured_at` → FAIL（实测快照没有测量日期）",
       any("measured_at" in p for p in problems), f"problems={problems[:1]}")
    over = {"lint_readability_ratchet": _blk({"E501": 12}, measured={"E501": 10})}
    problems, _ = ratchet_problems(over, prev, today=today, pointers=pointers)
    ok("M-C 反向对照 L cap 高于实测（12 > 10）→ FAIL 且点名『静默配额』",
       any("静默配额" in p for p in problems), f"problems={problems[:1]}")
    kset = {"lint_readability_ratchet": _blk({"E501": 10},
                                             measured={"E501": 10, "D999": 1})}
    problems, _ = ratchet_problems(kset, prev, today=today, pointers=pointers)
    ok("M-C 反向对照 M 实测快照多出键（上限表里没有）→ FAIL（死数据/拼写漂移）",
       any("多出键" in p for p in problems), f"problems={problems[:1]}")
    # 提交态：HEAD vs HEAD~1 的**上调**必须有具名重评（否则盲区）
    head_raised = {"lint_readability_ratchet": _blk({"E501": 12},
                                                    measured={"E501": 12})}
    problems = committed_rebase_problems(head_raised, prev, pointers=pointers)
    ok("M-C 反向对照 N **提交态**上调而无声 → FAIL（复核机制缺口 2：提交后即成新基线）",
       any("提交态" in p and "rebased_at" in p for p in problems),
       f"problems={problems[:1]}")
    named = {"lint_readability_ratchet": _blk(
        {"E501": 12}, measured={"E501": 12}, rebased_at="2026-09-25",
        rebased_reason="重评基线：按当次实测下调（E501 2631→2494）",
        rebased_from={"E501": 10})}
    problems = committed_rebase_problems(named, prev, pointers=pointers)
    ok("M-C 反向对照 N2 同样的上调**带 rebased_at + 理由 + rebased_from** "
       "→ PASS（具名事件）",
       problems == [], f"problems={problems[:1]}")
    stale_sig = {"lint_readability_ratchet": _blk(
        {"E501": 12}, measured={"E501": 12}, rebased_at="2026-04-01",
        rebased_reason="重评基线：按当次实测下调（2026-04 那次，不是这次）",
        rebased_from={"E501": 7})}
    problems = committed_rebase_problems(stale_sig, prev, pointers=pointers)
    ok("M-C 反向对照 N4（复核 major 的原始形态）：**先降后升 + 复用旧署名** ⇒ FAIL"
       "（`rebased_from` 必须等于父提交被抬高键的值）",
       any("rebased_from" in p and "旧署名" in p for p in problems),
       f"problems={problems[:1]}")
    problems = committed_rebase_problems(named, head_raised, pointers=pointers)
    ok("M-C 反向对照 N3 提交态**不变**时不做要求（防假红）", problems == [],
       f"problems={problems[:1]}")

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "a.py").write_text("x = 1\n", encoding="utf-8")
        saved_list, saved_line = GUARD_REQUIRED, GUARD_LINE
        try:
            globals()["GUARD_REQUIRED"] = ("a.py",)
            globals()["GUARD_LINE"] = "assert __debug__"
            problems, _ = guard_problems(base)
            ok("反向对照 H 守卫行缺席的闸门 → FAIL 且点名文件",
               any("a.py" in p and "__debug__" in p for p in problems), f"problems={problems[:1]}")
            (base / "a.py").write_text("assert __debug__\nx = 1\n", encoding="utf-8")
            problems, _ = guard_problems(base)
            ok("反向对照 H2 守卫行在位 → PASS（防假红）",
               not any("a.py" in p for p in problems), f"problems={problems[:1]}")
        finally:
            globals()["GUARD_REQUIRED"], globals()["GUARD_LINE"] = saved_list, saved_line
    # A-M12 ① 反向对照：把"不可跳过层"的三处接线分别拿掉 ⇒ 必须逐条 FAIL；
    # 原样 ⇒ PASS（防假红）。用 `%TEMP%` 里的**真文件副本**做，不动仓库文件。
    # 落点一律写成"`Path(tempfile.gettempdir())` + 字面量"的**单一表达式**：
    # 不经变量中转，满足 `verify_artifact_paths.py` 的静态可判定要求
    # （第一版把落点交给变量，被该闸门当场判为 2 处动态目标 ⇒ 记入本批自检的价值）。
    ci_probe = Path(tempfile.gettempdir()) / "gate-integrity-unskippable-ci.yml"
    hook_probe = Path(tempfile.gettempdir()) / "gate-integrity-unskippable-pre-commit"
    inst_probe = Path(tempfile.gettempdir()) / "gate-integrity-unskippable-installer.py"
    chook_probe = Path(tempfile.gettempdir()) / "gate-integrity-unskippable-commit-msg"
    ci_probe.write_text((ROOT / CI_REL).read_text(encoding="utf-8"), encoding="utf-8")
    hook_probe.write_text((ROOT / HOOK_REL).read_text(encoding="utf-8"),
                          encoding="utf-8")
    inst_probe.write_text((ROOT / INSTALLER_REL).read_text(encoding="utf-8"),
                          encoding="utf-8")
    chook_probe.write_text((ROOT / COMMITHOOK_REL).read_text(encoding="utf-8"),
                           encoding="utf-8")
    try:
        def _probe_problems() -> list[str]:
            return unskippable_wiring_problems(ci=ci_probe, hook=hook_probe,
                                               installer=inst_probe,
                                               commithook=chook_probe)

        ok("A-M12① 正向对照：四处接线原样 → 零问题（防假红）",
           _probe_problems() == [], f"problems={_probe_problems()[:1]}")
        ci_text = ci_probe.read_text(encoding="utf-8")
        ci_probe.write_text(
            ci_text.replace("structure-guard.py verify --from-git",
                            "structure-guard.py --replay"), encoding="utf-8")
        ok("A-M12① 反向对照 a：CI 里那条 git 基线调用被拿掉（只剩自检档）→ FAIL 且点名"
           "（守卫退回『依赖人记得跑快照』的形态）",
           any("--from-git" in p for p in _probe_problems()),
           f"problems={_probe_problems()[:1]}")
        # **二查 run-…-087 major 1 的原始形态**：只删**真调用**那一行、保留 `Write-Host`
        # 里的
        # 同名字样 ⇒ 子串匹配会把这句**标签**当成接线、判"零问题"（假绿）。
        ci_probe.write_text(
            "\n".join(line for line in ci_text.splitlines()
                      if "python scripts/structure-guard.py verify "
                      "--from-git" not in line),
            encoding="utf-8")
        ok("A-M12① 反向对照 a′：只删**真调用**、保留标签里的同名字样 ⇒ FAIL"
           "（判据必须认命令位置，不认文本出现）",
           any("--from-git" in p for p in _probe_problems()),
           f"problems={_probe_problems()[:1]}")
        ci_probe.write_text(ci_text, encoding="utf-8")
        hook_probe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        ok("A-M12① 反向对照 b：钩子模板空转（不调同一判据）→ FAIL（两层不得各判一套）",
           any(HOOK_REL in p for p in _probe_problems()),
           f"problems={_probe_problems()[:1]}")
        inst_probe.unlink()
        installer_problems = _probe_problems()
        ok("A-M12① 反向对照 c：安装器缺失 → FAIL（`.git/hooks/` 不在版本控制里，"
           "没有安装器就只剩『记得手动拷』）",
           any(INSTALLER_REL in p for p in installer_problems),
           next((p for p in installer_problems if INSTALLER_REL in p),
                installer_problems[:1]))
        # `commit-msg` 缺失 ⇒ FAIL（修复验证复核 `run-…-089` major 的原始形态：
        # 没有它，本地层读不到待提交信息里的署名）
        chook_probe.unlink()
        chook_problems = _probe_problems()
        ok("A-M12① 反向对照 d：`commit-msg` 模板缺失 → FAIL（本地读不到署名，"
           "合法结构删除只能 `--no-verify`）",
           any(COMMITHOOK_REL in p for p in chook_problems),
           next((p for p in chook_problems if COMMITHOOK_REL in p), chook_problems[:1]))
        # **复核 `091` minor 2 的原始形态**：模板都在、也都调判据，但安装器**不装**
        # `commit-msg`。而 `pre-commit` 已 report-only ⇒ 终判全压在 `commit-msg` 上
        # ⇒「模板在版本控制里存在」≠「它会被装上」，这一格此前没有判据。
        inst_probe.write_text((ROOT / INSTALLER_REL).read_text(encoding="utf-8")
                              .replace('"commit-msg"', '""'), encoding="utf-8")
        chook_probe.write_text((ROOT / COMMITHOOK_REL).read_text(encoding="utf-8"),
                               encoding="utf-8")
        hooks_problems = _probe_problems()
        ok("A-M12① 反向对照 e：安装器 `HOOKS` 去掉 `commit-msg`（模板仍在、仍调判据）"
           "→ FAIL（『模板存在』不等于『会被装上』；本地终判压在它身上）",
           any("HOOKS" in p for p in hooks_problems),
           next((p for p in hooks_problems if "HOOKS" in p), hooks_problems[:1]))
    finally:
        for probe in (ci_probe, hook_probe, inst_probe, chook_probe):
            probe.unlink(missing_ok=True)

    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


def main() -> int:
    import datetime
    today = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")
    if "--selftest" in sys.argv:
        return selftest()
    current = json.loads((ROOT / POLICY_REL).read_text(encoding="utf-8"))
    previous = git_policy()
    problems, warnings = ratchet_problems(current, previous, today=today, pointers=RATCHETS)
    # M-C：**提交态**的放宽（HEAD vs HEAD~1）必须带 `rebased_at` + `rebased_reason`——
    # 这一层补的正是"与 git HEAD 比较"的盲区（复核机制缺口 2）。
    committed, committed_parent = git_policy("HEAD"), git_policy("HEAD~1")
    problems += committed_rebase_problems(committed, committed_parent,
                                          pointers=RATCHETS)
    gp, gw = guard_problems()
    problems += gp
    warnings += gw
    # A-M12 ①：结构守卫的"不可跳过层"是否接线在位（CI 调用 + 钩子模板 + 安装器）。
    problems += unskippable_guard_problems()
    problems += probe_o_mode()
    for w in warnings:
        warn(w)
    if previous is None:
        warn(f"无法读取 git HEAD:{POLICY_REL}——单调性判据本次未执行（不是通过，是没判）")
    if problems:
        print(f"GATE-INTEGRITY FAIL（{len(problems)} 项）：")
        for p in problems[:40]:
            print(f"  - {p}")
        if len(problems) > 40:
            print(f"  … 另有 {len(problems) - 40} 项")
        return 1
    print(f"GATE-INTEGRITY PASS：守卫行 {len(GUARD_REQUIRED)} 个闸门在位（含真实 `-O` 探针红）；"
          f"{len(RATCHETS)} 个棘轮的上限与 HEAD 逐项比较无上调、且都带 "
          f"`measured_value`/`measured_at`；提交态（HEAD vs HEAD~1）无未署名的放宽")
    rc = selftest()
    if rc == 0:
        print(f"EVIDENCE: verify_gate_integrity.py assertions={PASSED} rc=0 "
              f"guard_required={len(GUARD_REQUIRED)} ratchets={len(RATCHETS)}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
