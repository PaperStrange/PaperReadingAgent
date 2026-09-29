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

VERIFY_META = {'features': '闸门可信度：-O/PYTHONOPTIMIZE 守卫行在位'
                          '（含真实 -O 探针必须红）+ 棘轮上限与 git HEAD 逐项比较'
                          '（只许下调、上调即 FAIL）+ review_by 必填未过期 '
                          '+ 未覆盖闸门逐条 WARN；'
                          '反向对照条数见末行 `ALL PASS (N assertions)`',
               'tier': 'offline', 'providers': [], 'est_cost_cny': 0,
               'est_seconds': 6, 'routes': [], 'requires': ['none']}

import json
import re
import shutil
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
# 行 6：**终判层**＝不可跳过的那一层（CI）。本地两层都可能没装 / 被 `--no-verify`
# 跳过，故"本地终判必须由退出码承载"的落点只能钉在这里；它一旦 `--report-only`，
# 整条链就没有任何一层在拒绝。
EXIT_CODE_JUDGE_REL = CI_REL
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


# 行 4（089 minor）：**命令位置**判定 = 黑名单换成正向结构。
# 黑名单（见 `_cmd_line` 的 docstring）的失败形态是"**枚举不完**"：少列一种回显/赋值
# 形态就多一个假绿，而假绿只能等下一次事故来发现。
# 正向判定走**词元**：把命令行按空白切词，只看**前两个词元**——
#   ① 首词元是解释器（`python` / `python.exe` / `$py` / `"$py"` / `.venv/Scripts/python.exe`
#      / `"$py.exe"`）⇒ 次词元必须是守卫脚本；
#   ② 首词元本身就是守卫脚本路径（CI 真行把 `python` 写在行首、脚本在第二个词元）。
# 每一步都要求**词元本身**是干净的一整段（见 `_has_cmd_char`）⇒
#   * `cmd = "structure-guard.py verify --from-git HEAD"`：首词元 `cmd`、次词元 `=`，
#     都不成立；
#   * `Write-Output "python … structure-guard.py …"`：首词元含 `"`；
#   * 行尾注释里的同名字样：`_strip_comment` 已剥掉。
# 认的是"这条命令会被执行"，不是"这串字出现在文件里"。
GUARD_SCRIPT = "structure-guard.py"
GUARD_SUBCOMMAND = "verify"
# 词元里出现这些字符 ⇒ 它不是一个干净的"命令/解释器/脚本路径"词元。
NO_CMD_CHAR_RE = re.compile(r"[\"'`=(){}|&;]")
# **调用点自带的赋值前缀**（钩子模板的第一句就是 `out=$("$py" scripts/… 2>&1)`）：
# `out=$( … )` 里被执行的是 `$(` 之后的命令，判据必须穿透这一层；
# 不穿透的话，真实的钩子模板会被判成"没有调用守卫"（假红）。
ASSIGN_PREFIX_RE = re.compile(r"^\s*[A-Za-z_]\w*=\$\(\s*")
# 解释器词元（大小写不敏感；必须是**整个词元**）。三种写法都算：
# `python` / `python3.13` / `python.exe`（`python` 字面量 + 可选版本/后缀）；
# `$py` / `${PY}` / `$py.exe`（shell 变量命名，变量名里含 `py`；**必须带 `$`**）；
# `py`（Windows 启动器，裸词只此一个）；
# `.venv/Scripts/python.exe`（带目录；调用前已按路径末段比较，这里只看末段）。
# **`cmd` 不是解释器** ⇒ 赋值不会被误认成调用；
# `Write-Output` 含连字符，被 `[\w${}]*` 挡住，也不会被误认成解释器。
#
# **行 30（复核 `run-…-104` minor 5）**：旧式 `^(?:python[\w.]*|[\w${}]*py)$` 的**第二支**
# 是"任何以 `py` 结尾的裸词"⇒ 解释器判定取决于**词尾字母**而不是结构：
# 探针实测 `copy` / `happy` 判 True（而 `empty` / `apply` 判 False ⇒ 同一类词两个读数）。
# 后果是一条 `copy scripts/structure-guard.py verify …` 会被整条认成
# "解释器 ＋ 守卫脚本 ＋ verify"（假绿就是判据被一行无关的 `copy` 满足）。
# 现在：裸词只认 `python*` 与 `py`，变量形态一律要求 `$`。
PY_WORD_RE = re.compile(
    r"^(?:python[\w.]*|py|\$\{?[\w${}]*py[\w${}]*\}?(?:\.exe)?)$", re.I)
# CI 是 YAML：命令可以写成 `run: python …`（键与值同一行）。
# 这不是"命令名"，是**同一个步骤的写法**；真文件实测：不认它会把 CI 判成没调用。
# 只认 `run` 这一个键（`cmd = …` 这类赋值不会被误放行）。
RUN_KEY_RE = re.compile(r"^run\s*:\s*")
# 行 22②（G2 关闭）：**回显动词清单已删除**。它的方向是"默认放行"——只有命中
# 清单的行才被当作文本跳过，未列入者（`Out-Host`／`Out-File`）照样冒充接线（探针
# 实测：`Out-Host("python … structure-guard.py verify …")` 修前判"有调用"）。
# 现在反过来：见 `_cmd_head` —— 首词元必须**正向**是解释器或守卫脚本，否则该行
# 没有命令位置。行 6（092 minor）复用同一份判定：`--report-only` 也认命令位置，
# 否则新判据会栽在它自己要治的同一种形态上（注释里提一句就假红）。


def _mask_quotes(line: str) -> str:
    """把**成对引号内**的字符换成 `.`（保长度、保位置），返回掩码串。

    修复验证复核 `run-…-114` major 1 时发现的新缺口：`#` 与 `;`／`&&`／`||` 的
    判据都必须**引号感知**——`echo "a; b"` 里的 `;` 不是命令分隔符，
    `echo "a # b"` 里的 `#` 不是注释起点。掩码（而不是删除）是为了让**列位置不变**，
    调用方按同一坐标取子串即可。
    """
    chars = list(line)
    quote = ""
    for i, ch in enumerate(chars):
        if quote:
            chars[i] = "."
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            chars[i] = "."
    return "".join(chars)


def _strip_comment(line: str) -> str:
    """剥掉行尾注释（`#` 起）。

    行 4 的第二半（092 minor）：旧实现只跳**整行**注释 ⇒
    行尾注释里的同名字样（CI 里 `run: echo x   # structure-guard.py verify …`）
    照样满足判据。三份层文件的注释一律用 `#`，故这一步够用且方向收紧。

    `run-…-114` major 1：`#` 也要**引号感知**——`echo "a # b"` 里的 `#` 不是注释起点。
    旧实现（`partition("#")`）会把引号内的 `#` 当注释起点，于是
    `echo "a # b"; <守卫调用>` 这类行被**截断**、守卫调用整段丢失 ⇒ 判据在真调用上
    假红（而修法方向是收紧，不能靠"反正真文件里没有"放过）。故改为在掩码串上找
    第一个真注释位，再按同一坐标切**原文**。
    """
    i = _mask_quotes(line).find("#")
    return line if i < 0 else line[:i]


def _clean_word(word: str) -> str:
    """去掉词元两端成对的引号，并校验它是一整段**命令/路径**。

    禁字符只查**末段**（文件名）：`=`、引号、括号出现在**目录**里是合法的
    （`.venv/Scripts/python.exe` 这类路径带 `/`，而 `/` 不在禁字符表里；
    但引号/赋值出现在裸词元里就是"这不是一条命令"的信号）。
    先剥引号再查禁字符：`"$py"` 是干净解释器词元，`W="python` 不是。
    """
    core = word.strip("\"'`")
    if NO_CMD_CHAR_RE.search(re.split(r"[/\\]", core)[-1]):
        return ""
    return core


def _script_name(word: str) -> str:
    """词元里的**脚本文件名**（`scripts/structure-guard.py` ⇒ `structure-guard.py`）。

    真调用一律带目录（`scripts/…`），用 `startswith` 比会判成 false（假红）；
    故按路径末段比。
    """
    return re.split(r"[/\\]", word)[-1]


def _cmd_head(word: str) -> bool:
    """首词元是否**本身就是一条命令**（解释器或守卫脚本）——行 22② 的默认判红门。

    修前形态（探针实测有假绿）：不在 `ECHO_PREFIXES` 里的词元一律算"命令位置"，
    而**含 `(`／`|` 等字符的首词元被静默丢弃** ⇒ 后面的词元移位成首词元，于是
    `Out-Host("python … structure-guard.py verify …")` 判成"有调用"。现在反过来：
    首词元必须被**正向**认成解释器（`PY_WORD_RE`，按路径末段）或守卫脚本本身；
    认不出 ⇒ 该行没有命令位置（未知形态不再默认放行）。
    双引号是 shell 引用真命令（`"$py" scripts/…`）⇒ 先剥；反引号不剥
    （markdown 代码跨度/PS 转义是**文本**，不是命令位置）。
    """
    core = _script_name(word.strip('"'))
    if not core:
        return False
    return core == GUARD_SCRIPT or bool(PY_WORD_RE.match(core))


def _cmd_line(line: str) -> str:
    """该行**命令位置**上真正会被执行的那段；不是命令则返回空串。

    行 22②：**默认判红**。剥掉行尾注释、赋值前缀（`out=$(…`）与 YAML `run:` 键
    之后，首词元必须过 `_cmd_head` —— 没有"回显动词清单"这回事，未知形态一律
    判"没有命令"（旧实现的清单方向相反：不在清单里就默认放行）。
    """
    body = _strip_comment(line).strip()
    if not body:
        return ""
    m = ASSIGN_PREFIX_RE.match(body) or RUN_KEY_RE.match(body)
    if m:
        body = body[m.end():].strip()
    if not body or not _cmd_head(body.split()[0]):
        return ""
    return body


def _is_guard_invocation(body: str) -> bool:
    """一段（已剥注释的）命令行是否**以守卫调用开头**——词元级结构判定。

    只看前两个词元：解释器+脚本，或（无解释器时）脚本自己。这样
    `cmd = "…"`、`Write-Output "…"`、`echo x # …` 都不会被认成调用，
    而 `"$py" scripts/structure-guard.py …` 这种带引号/带目录的**真调用**照样认得出
    （黑名单版漏掉的正是前者，正向判定不得把后者误判成 false）。
    """
    m = ASSIGN_PREFIX_RE.match(body)
    if m:
        body = body[m.end():]
    key = RUN_KEY_RE.match(body)                 # YAML：`run: <命令>`
    if key:
        body = body[key.end():]
    words = [w for w in (_clean_word(w) for w in body.split()) if w]
    if not words:
        return False
    if _script_name(words[0]) == GUARD_SCRIPT:
        return len(words) > 1 and words[1] == GUARD_SUBCOMMAND
    if not PY_WORD_RE.match(_script_name(words[0])):     # 解释器按末段认
        return False              # 首词元既不是解释器、也不是守卫脚本
    return (len(words) > 2 and _script_name(words[1]) == GUARD_SCRIPT
            and words[2] == GUARD_SUBCOMMAND)


def _guard_command_lines(text: str) -> list[str]:
    """该文件里**真的会执行**守卫的每一行（命令位置 + 结构判定）。

    行 4 的判据本体；行 6 也复用它（同一条"命令位置"语义，两个判据不各判一套）。
    """
    return [ln for ln in (_cmd_line(line) for line in text.splitlines())
            if _is_guard_invocation(ln)]


def _invokes_guard(text: str) -> bool:
    """该文件是否在**命令位置**调用了结构守卫的 git 档。

    为什么不能只做子串搜索（二查 `run-…-087` major 1 的探针实测）：CI 里那行
    `Write-Host "gate: structure-guard.py verify --from-git …"`
    的**标签文本本身**就满足子串匹配 ⇒ 把真调用删掉、只留标签，判据照样"零问题"。
    于是"接线判据"守的是一句**注释**，不是一条命令。

    黑名单版（`_invokes_guard:291`，089 minor，G2 行 4）的残留：判据只跳
    `#`/`Write-Host`/`echo`/`::` **四种行首** ⇒ `Write-Output` 回显、变量赋值
    （`cmd = "structure-guard.py verify --from-git HEAD"`）、here-string、
    **行尾注释**四种形态仍可满足它——修前实测四种里有三种假绿（探针见
    `docs/iteration/phases/testing-governance/2026-09-26-g2-closure-ledger.MD`
    的实现记录）。现在改成**正向结构判定**：见 `_cmd_head` / `_cmd_line`
    （行 22② 起 `_cmd_line` 会先剥赋值/`run:` 前缀，故本函数里的同名前缀处理只是
    让它自带完整语义——两层用同两条正则，不各判一套）。
    """
    return bool(_guard_command_lines(text))


def _invokes_report_only(text: str) -> bool:
    """该文件是否在**命令位置**给守卫传了 `--report-only`（行 6 的检测器）。

    只用 `"--report-only" in text` 会栽在同一种形态上：注释/文档里提一句就假红。
    故与 `_invokes_guard` 共用"命令位置"语义。
    """
    return any("--report-only" in ln for ln in _guard_command_lines(text))


def _enforces_exit_code(text: str) -> tuple[bool, bool]:
    """返回 `(命令位置有几次守卫调用, 其中是否有一次由**退出码**终判)`。

    行 6（复核 `092` minor，E3：批 7／批 9 的**共同残余**）：批 7 把
    `pre-commit` 改成 `--report-only`（终判压到 `commit-msg`），批 9 修了
    `structure-guard` 的基线 fail-open——两批都没给"**不许所有层都加
    `--report-only`**"留判据。三处接线全加上它 = 整条链 fail-open：守卫照样逐条
    打印 `[FAIL]`，每一处却都 rc=0。

    判据落在**退出码**上：`--report-only` 的语义是"rc 恒 0"（见
    `structure-guard.py::cmd_verify_git` 的 `report_only` 分支）⇒ "这一段命令
    由退出码终判"的**必要**条件是**不带** `--report-only`。

    **加强（复核 `run-…-105` major 6）**：旧实现把上面这条当**充要**，实为
    **必要非充分**——`--report-only` 只覆盖"守卫自己让出终判"这一种形态，覆盖不了
    "**调用方把 rc 吞掉**"：
      * `out=$(python … guard.py verify … 2>&1) || true` ⇒ rc 被 `|| true` 吞；
      * `python … guard.py verify …; rc=$?; echo done` ⇒ rc 存进变量却再没用过。
    两种形态旧码都判"由退出码终判"（实测 True），而它们的 rc 一个字都没进入终判
    ⇒ 整条链在那两处是 fail-open。现判据改判**结构**：rc 必须被逐层传到一条 `exit`
    （见 `_rc_reaches_final_verdict`）。注意：三层现状**恰好都没踩中**这两种形态，
    故这是判据强度缺口而不是现行事故——50 条既有断言一条都不许因此变红。

    **再加强（复核 `run-…-114` major 1：上面这版只治了"多行形态"）**：
    `run-…-105` 的两种吞码形态**写在同一行**时旧码照旧判 True（现跑实测 8 形态）
    ——`… verify --from-git HEAD; echo done` ⇒ True（应 False）、
    `…; echo done` ＋ 末行 `exit 0` ⇒ True、`… || exit 0` ⇒ True（旧
    `SWALLOW_TAIL_RE` 只认 `|| true`／`|| :`）。根因是判据只把**行首**当命令位置：
    `;` 之后的尾巴（`echo done`／`exit 0`／`rc=$?`）既不参与"调用是否裸"的判定、
    也不参与"rc 是否进终判"的判定。现在改为**段感知**（`_split_commands`：按未加引号的
    `;`／`&&`／`||`／`&` 切段，引号感知）＋**位置判定**（`_guard_call_end`）：
    调用之后若还有**别的命令**（无论同行还是下一行）⇒ rc 已被那条命令盖掉/吞掉，
    不判"由退出码终判"，除非那条尾巴本身就是一条**承载该 rc 的 `exit`**。
    ⚠ 边界同 `run-…-114` 报告（不夸大）：仓库现三层（`ci.yml` 裸调用、
    `commit-msg` `exit 1`、`pre-commit` `exit $rc`）**恰好都没踩中**上述形态，
    故这是**判据强度缺口**、不是现行事故；修复后旧断言一条未减（只增不减）。

    为什么不是"数一数有几层非 report-only"（台账 A 表行 6 的原始措辞）：后者只数
    **层数**、不看**退出码**，正好落进 E3 自己写的那条反证——"只数层数、不看退出码
    ⇒ 又变回 fail-open"。故这里逐**调用**判，并在
    `unskippable_wiring_problems` 里把"三处合起来至少一次由退出码终判"与
    "终判层（`EXIT_CODE_JUDGE_REL`）自己不得让出"分别写成判据。
    """
    lines = text.splitlines()
    # 判据本体复用 `_cmd_line` / `_is_guard_invocation`（与 `_guard_command_lines`
    # 同一条"命令位置 + 结构"语义，不各判一套）；只是这里要**行号**才能取到
    # "下一行"（`v=$(…)` / `rc=$?` 是两行的组合形态）。
    hits: list[int] = []
    bodies: dict[int, str] = {}
    masked: dict[int, str] = {}
    for idx, raw in enumerate(lines):
        body = _cmd_line(raw)
        if body and _is_guard_invocation(body):
            hits.append(idx)
            bodies[idx] = body
            masked[idx] = _mask_quotes(_strip_comment(raw))
    enforces = any(
        "--report-only" not in bodies[idx]
        and _rc_reaches_final_verdict(text, _line_and_next(lines, idx),
                                      masked[idx], lines, idx)
        for idx in hits)
    return len(hits), enforces


# 行 6 加强（复核 `run-…-105` major 6）：**退出码真的被用于终判**的结构判据。
# 旧实现的判据只有一条"这一行不带 `--report-only`"，自陈"充要"实为**必要非充分**：
#   * `out=$(python … guard.py verify … 2>&1) || true` —— `|| true` 把 rc 吞掉；
#   * `python … guard.py verify …; rc=$?; echo done` —— `$?` 存进了变量却再没用过。
# 两种形态旧码都判"由退出码终判"，而它们的 rc 一个字都没进入文件的终判。
EXIT_JUDGE_RE = re.compile(r"\bexit\b\s+[\"']?\$\{?(?P<name>\w+)")
# 赋值捕获：`v=$(<命令>)` / `v=`<命令>``（commmand substitution 的 rc ⇒ 赋给 v）。
# 锚 `^` ＋ 掩码串 ⇒ **只认段首／行首的赋值**：`…; rc=$?` 这种**同行尾巴**不会被
# 误认成"调用行自己捕获了 rc"（那正是 `run-…-114` major 1 的第二个根因）。
CMD_SUBST_ASSIGN_RE = re.compile(r"^\s*(?P<name>\w+)=(?:\$\(|`)")
# `rc=$?`：把**上一条命令**的 rc 存进变量。块是多行的 ⇒ 行内空白用 `[ \t]`、
# 不用 `\s`：`\s` 会吞掉**换行**，于是 `^` 从块首起算、`rc=$?` 永远匹配不上
# （这条被自己的反向对照 s 实测打脸过一次）。
# **`\$` 必须转义**（`run-…-114` major 1 第六版探针实测）：写成 `=\$?` 时 `$` 落在
# `\` 前面 ⇒ 正则里它是"**行尾锚**"，`?...` 又把 `?` 当量词 ⇒ 该 pattern 认的是
# `rc=` 后跟零个量词，**永远匹配不到 `rc=$?`**。原版（`run-…-105`）正是这么写的，
# 而它的自检在多行形态上"看起来绿"纯属巧合：捕获取不到 ⇒ 判成裸调用 ⇒ 恰好也是 True。
RC_ASSIGN_RE = re.compile(r"^[ \t]*(?P<name>\w+)=\$\?", re.MULTILINE)
# 未加引号的命令分隔符（行 6 加强②：`;` 之后的尾巴也是命令）。
#   * `&&`／`||` 必须排在 `&` 前面，否则会被切坏；
#   * `&` 不得是**重定向**的一部分（`2>&1`／`>&1`）——`run-…-114` major 1 第二版
#     探针实测：`out=$(… 2>&1)` 被 `&` 切碎，于是真形态被误判成"调用之后还有命令"；
#   * `;` 在**跨行的 `$( … )` 里**不是分隔符（`file_scope=True` 时才判，见下）。
CMD_SEP_RE = re.compile(r"&&|\|\||;|(?<![>])&(?![>0-9])")
# 尾巴的分类：`; rc=$?`（同行捕获）⇒ 由 `_captured_rc_var` 认；`; exit $out`
# ⇒ 由 `_swallow_expr` 的"传 rc 的退出"那一支认；`; echo done`／`; exit 0`
# ⇒ 两条都不认 ⇒ 判否。
# **重定向不是"别的命令"**：`… verify … 2>&1`（含 `--report-only 2>&1)`）之后
# 没有第二条命令，rc 仍是这一行的 rc（不设这条会把真形态判成吞码）。
REDIRECT_ONLY_RE = re.compile(r"^\d*[<>]")


def _split_commands(masked: str, file_scope: bool = False
                    ) -> list[tuple[str, str]]:
    """把一行按**未加引号的** `;`／`&&`／`||`／`&` 切段；返回 `(段, 段后的分隔符)`。

    `run-…-114` major 1：判据此前只把**整行**当一个命令块 ⇒ `… verify …; echo done`
    里的 `echo done` 既不在"调用是否裸"的判定里、也不在"rc 是否进终判"的判定里。
    掩码串上的 `;` 一定是真分隔符（引号内的已被 `_mask_quotes` 换成 `.`），
    而**列位置保真** ⇒ 段文本可直接按同一坐标从掩码串取（分段判定不需要原文）。
    末段的"段后分隔符"记为空串。

    `file_scope=True`（整块）时多一条：`$( … )` **内部**（嵌套深度 > 0）的分隔符不算
    ——`out=$(cmd; echo x)` 是一整条命令，不是三条。`run-…-114` major 1 第五版探针
    实测：不设这条，`out=$(cmd 2>&1) || true` 会在 `&` 处被切碎、真形态反而判不出来。
    单行文本（`file_scope=False`）不做嵌套判定：那里要的正是"同一行的 `;` 尾巴"。
    """
    depth = 0
    prev = 0
    parts: list[tuple[str, str]] = []
    i = 0
    while i < len(masked):
        ch = masked[i]
        if ch == "\\":
            i += 2
            continue
        if masked.startswith("$(", i):
            depth += 1
            i += 2
            continue
        if ch == ")" and depth:
            depth -= 1
            i += 1
            continue
        if depth == 0 or not file_scope:
            m = CMD_SEP_RE.match(masked, i)
            if m:
                parts.append((masked[prev:i], m.group(0)))
                prev = i = m.end()
                continue
        i += 1
    parts.append((masked[prev:], ""))
    return parts


def _guard_call_end(seg: str) -> int | None:
    """段内**守卫调用结束**的列位置；`seg` 不是"守卫调用" ⇒ None。

    词元级（与 `_is_guard_invocation` 同一套 `_clean_word` / `_script_name` /
    `PY_WORD_RE`），只是这里还要"调用在哪结束"——否则无法判断后面有没有别的命令。
    引号内的空格被掩码成 `.` ⇒ 不会把词元切错。

    "结束"= 该调用**最后一个选项/实参词元**之后：`verify` 之后的第一批**干净词元**
    （`_clean_word` 认得、即不含 `;`／`&`／`|`／引号／括号／`=` 的词元）全是它的
    选项与实参（`--from-git HEAD`、`--ack-file "$msgfile"`），不含这些字符的词元
    （`;`／`||`／`&&`／`&`／`2>&1`）才是"调用之后还有别的命令"的信号。
    """
    words = [(m.start(), m.group(0)) for m in re.finditer(r"\S+", seg)]
    kept = [i for i, (_pos, tok) in enumerate(words) if _clean_word(tok)]
    if not kept:
        return None
    clean = [_script_name(_clean_word(words[i][1])) for i in kept]
    if clean[0] == GUARD_SCRIPT:
        offset = 1                       # 无解释器：`structure-guard.py verify …`
        if len(clean) < 2 or clean[1] != GUARD_SUBCOMMAND:
            return None
    elif PY_WORD_RE.match(clean[0]):
        offset = 3                       # `<解释器> structure-guard.py verify …`
        if len(clean) < 3 or clean[1] != GUARD_SCRIPT:
            return None
        if clean[2] != GUARD_SUBCOMMAND:
            return None
    else:
        return None                      # 首词元既不是解释器、也不是守卫脚本
    end = kept[offset:]                  # 该调用的选项与实参（`verify` 之后的干净词元）
    if not end:
        return None
    return words[end[-1]][0] + len(words[end[-1]][1])


def _captured_rc_var(block: str) -> str | None:
    """这段（守卫调用行 ＋ 紧随的下一行）是否把 rc **捕获进变量**；返回变量名。

    四种真形态（本仓三层里都有）：
      * `v=$(<命令>)` / ``v=`<命令>` `` —— 赋值即捕获（命令替换的 rc 赋给 `v`）；
      * `<命令>` 之后紧跟 `rc=$?` —— 也是捕获（`$?` 就是上一条命令的 rc）；
      * `<命令>; rc=$?`（**同一行**的 `;` 尾巴）—— 同样是捕获（`run-…-114` major 1
        要求穷举的那个形态）；
      * 裸调用（既不赋值、也没有 `rc=$?`）⇒ None：它的 rc 直接就是整个脚本/步骤的
        rc，不需要传递（判据在本函数之外按"这一行就是终判"处理）。

    `block` 由 `_line_and_next` 给出（调用行 ＋ 下一行）。**两类捕获必须分开归属**：
    赋值只可能出现在**调用所在那一行**（`v=$(…)`），而 `rc=$?` 既可能是下一行
    （两行组合形态）、也可能是同一行的 `;` 尾巴——两者结论相同（都是"捕获"），
    但**同行 `; rc=$?; echo done`** 与**下一行 `rc=$?` ＋ `echo done`** 都要认，
    所以下面的 `search` 跑在整块（含下一行）上。
    """
    block = _strip_comment(block)
    first = block.split("\n", 1)[0]
    m = CMD_SUBST_ASSIGN_RE.match(first)
    # 赋值捕获要求这一行**没有未加引号的命令分隔符**：`… verify …; rc=$?` 里的
    # `rc=$?` 是"调用之后的另一条命令的捕获"，不是"**这一行**把整条调用赋给变量"
    # （`run-…-114` major 1 第三版探针实测：不设这条，`…; rc=$?` ＋ `exit $rc`
    # 会被赋成 `out` 而判出错误结论）。
    if m and not CMD_SEP_RE.search(first):
        return m.group("name")
    # `re.match` **只锚定串首**、`MULTILINE` 也救不了它；`rc=$?` 在第 2 行
    # ⇒ 必须 `search`
    # （被自己的反向对照 s 实测打脸过一次：match 恒 None ⇒ 吞码形态照样判 True）。
    # 判据落在"**命令段首**"上（`run-…-114` major 1 第七版探针实测）：`rc=$?` 既可以
    # 是下一行的第一个命令（`^` 够），也可以是**同一行 `;` 之后**的第一个命令
    # （`^` 不够，MULTILINE 也救不了——`;` 不是行首）⇒ 逐段逐行判 `match`。
    for seg, _sep in _split_commands(block):
        for piece in seg.split("\n"):
            m = RC_ASSIGN_RE.match(piece)
            if m:
                return m.group("name")
    return None


def _rc_reaches_final_verdict(text: str, line: str, masked: str = "",
                              lines: list[str] | None = None,
                              idx: int = 0) -> bool:
    """`line` 上那次守卫调用的 rc 是否**真的**参与了这个文件的终判。

    复核 `run-…-105` major 6＋`run-…-114` major 1 的**全部**吞码形态都必须判否：
      * `out=$(… guard.py verify …) || true` —— 捕获了，但 `|| true` 把整行的 rc
        变成 0，且后续没有任何 `exit $out` ⇒ 守卫的非零 rc 进不了终判；
      * `… guard.py verify …; rc=$?; echo done` —— `$?` 存进 `rc` 却再没被用过
        （也没有 `exit $rc`）⇒ 同上；**同一行**写 `; rc=$?; echo done` 与
        分三行写结论必须一致（旧码只在多行形态上判否）；
      * `… verify …; echo done` ／ `… verify … || exit 0` ／ `… verify … && true`
        ／ `… verify … &` —— 调用之后那条尾巴才是这一行的 rc，
        守卫的 rc 被它盖掉（`&` 更是直接后台化）⇒ 判否。
    判据是**结构**的（rc 是否被逐层传到一条 `exit`），不是"这一行长什么样"：
      * 裸调用（行首就是命令、且**调用之后没有别的命令**）⇒ 它的 rc **就是**终判；
      * 捕获进变量 `v`（赋值 `v=$(…)`／紧随 `rc=$?`／同行 `; rc=$?`）⇒ 文件里必须
        存在 `exit $v`（否则判否）；
      * 调用之后跟着**别的命令**（含 `|| true`／`|| :`／`|| exit 0`）⇒ 判否，
        唯一例外是那条尾巴本身就是承载 `$v` 的 `exit`（或传 `$?` 的 `exit`）；
      * 调用之后**无条件覆盖** `$v`（`v=false`）⇒ 判否（旧码只看"文件里有没有
        `exit $v`"，前面覆盖掉也算，同属"自陈强于实际"）。
    `masked` 由 `_enforces_exit_code` 给出（行首/段首的掩码串）；缺省时按明文重算，
    故本函数可以单独真驱动（自检里正是这么用的）。
    """
    body = _strip_comment(line)
    masked = masked or _mask_quotes(body)
    var = _captured_rc_var(line)
    segs = _split_commands(masked, file_scope=True)
    if len(segs) > 1:
        # 调用之后**还有别的命令**：守卫的 rc 已被那条命令盖掉……除非那条命令就是
        # 承载这个 rc 的 `exit`／`rc=$?`。分支内**不重复**判 `|| true`：那条尾巴由
        # `_swallow_expr` 统一判（一处判据、一处自陈，不各判一套）。
        _seg, sep = segs[0]
        if sep == "&":
            return False                     # 后台化：rc 连读都读不到
        rest = sep + "".join(s + t for s, t in segs[1:])
        # 尾巴 = "第一个分隔符 ＋ 其后各段"（**不在** `masked` 上按段内坐标切片：
        # `seg` 是切分后的片段，段内坐标与整行坐标不是一回事——第十二版探针实测
        # B9 被切错；E1 又因切片把 `|| true` 切没了 ⇒ 假绿）。
        tail = rest.strip()
        # 尾巴**含分隔符**（`|| exit $?` 的 `||` 就是分隔符本身）⇒ 交给
        # `_swallow_expr` 前先剥掉：判据看的是"分隔符之后那条命令是什么"。
        # 尾巴是 `exit`／`return` 时还要核**实参真的引用了这次调用的 rc**
        # （`exit 1`／`exit $((1))` 都是常量 ⇒ 仍算吞码，见 `_exit_carries`）。
        tail = tail.lstrip("&|; \t")
        if re.match(r"^(?:exit|return)\b", tail):
            if not _exit_carries(tail, {var} if var else None, raw_dollar=True):
                return False
        elif _condition_on_rc(tail):
            return False                 # `if [ $? -ne 0 ]; then exit 1; fi`：真拒绝
        elif _swallow_expr(tail):
            return False
    else:
        # 调用是这一行唯一（或最后的）命令：调用之后若还有别的词元（含 `|| true`
        # 这类同段尾巴），同判"rc 已被盖掉"。
        head = segs[0][0]
        end = _guard_call_end(head)
        tail = head[end:].strip() if end is not None else ""
        if _swallow_expr(tail):
            return False
    if var is None:
        # 裸调用：它的 rc **就是**这一行的 rc，但"这一行的 rc 是不是文件的终判"还要看
        # **后面还有没有别的命令**（`run-…-114` major 1 第十一版探针实测：旧码在
        # "调用行之后还有 `echo`／`exit`"时照样判 True，等于把"后面把 rc 覆盖掉"的
        # 形态放行）。故：
        #   * 调用行之后没有别的行（或只剩空行/注释/提示符/块结束括号）⇒ 它的 rc 就是
        #     终判（CI 真形态：`run:` 块的最后一条命令就是该步骤的 rc）；
        #   * 有后续行 ⇒ 由 `exit` 承担（裸调用 ＋ `if [ $? -ne 0 ]` 的 `commit-msg`
        #     真形态；`exit 0` 而无 `$?` 的形态仍判否）。
        after = _after_line(lines if lines is not None else text.split("\n"), idx)
        if _shell_noise_only(after) or _after_is_own_scope(after):
            return True
        return _exit_carries(after, raw_dollar=True)
    # 覆盖判定搜**整段文件文本**（`line` 只是"调用行 ＋ 下一行"）：只搜那两行会漏掉
    # "调用之后第三行才无条件覆盖"的形态（`run-…-114` major 1 第八版探针实测 A5）。
    if _static_rc_assign(text, var):
        return False
    # **捕获链**（第九版探针实测 F1b／A3）：真仓形态是两级 —— `out=$(<守卫>)` 捕获
    # 命令替换的 rc，紧接着 `rc=$?` 又把**同一个 rc** 捕获一次，终判用的是 `exit $rc`。
    # 只看"有没有 `exit $out`"会把这种**真传递**判红。
    chain = {var, *RC_ASSIGN_RE.findall(_strip_comment(line))}
    return _exit_carries(text, chain, raw_dollar=True)


# `exit` / `return` 的**实参**（`exit $rc` / `exit "$1"` / `exit 1`）。
# 判"终判用的是不是被捕获的那个变量"必须在**实参**上判，不能只判"文件里出现过
# `exit $v`"：`if …; then exit 1; fi; exit $rc`（`commit-msg` 真形态）里前一条
# `exit` 是常量的分支出口，只看"出现过"会把 `exit $((1))` 这种常量也算成传递。
EXIT_ARG_RE = re.compile(r"\b(?:exit|return)\s+(?P<arg>[^\s;&|]+)")
# 条件形态：`if` / `elif` / `while` / `until` / `case` 或 `[` / `[[` / `((`。
CONDITION_RE = re.compile(r"[\[(]|\b(?:if|elif|while|until|case)\b")


def _condition_on_rc(tail: str) -> bool:
    """尾巴是否是"**条件读 rc ⇒ 拒绝**"的形态（`if [ $? -ne 0 ]; then exit 1; fi`）。

    这是**合法**的终判形态，与"把 rc 吞成 0"（`|| true`／`; echo done`）必须分开：
      * `commit-msg` 真形态 —— `if [ $rc -ne 0 ]; then echo …; exit 1; fi`；
      * 反向对照（**不**算条件拒绝）：`; echo done`（无 `$?`／`$v`）、
        `|| true`（无 `exit`）、`; exit 0`（无 `$?`／`$v`）。
    故判据合取三件事：尾巴里有**条件结构**、条件里引用了 **rc**（`$?`／`$变量`）、
    且尾巴里有 `exit`／`return`（拒绝通道真的存在）。
    """
    return bool(CONDITION_RE.search(tail)
                and re.search(r"\$(?:\?|\{?\w)", tail)
                and re.search(r"\b(?:exit|return)\b", tail))


def _exit_carries(text: str, names: set[str] | None = None, raw_dollar: bool = False
                  ) -> bool:
    """`text` 里**最后一条** `exit`／`return` 是否承载了这次调用的 rc。

    `names` = 这次调用的 rc 捕获链（`out=$(…)` 的 `out` 与紧随的 `rc=$?` 的 `rc`
    是同一层传递）⇒ 实参引用其中任一个即算承载。
    `raw_dollar=True` 时额外认"实参就是 `$?`"（`|| exit $?` 与"裸调用 ＋
    `if [ $? -ne 0 ]`"两种形态：没有变量名可对，`$?` 就是守卫的 rc）。

    取**最后一条**是保守方向：`run-…-114` major 1 第十版探针实测，取"出现过任意
    一条"会让 `exit $((1))`（常量）也算成传递 ⇒ 假绿。
    """
    args = [m.group("arg") for m in EXIT_ARG_RE.finditer(_strip_comment(text))]
    if not args:
        return False
    for m in reversed(list(EXIT_ARG_RE.finditer(_strip_comment(text)))):
        arg = m.group("arg").lstrip("\"'")
        if raw_dollar and arg.lstrip("${").startswith("?"):
            return True
        name = re.match(r"[A-Za-z_]\w*", arg.lstrip("$").lstrip("{"))
        if name and name.group(0) in (names or set()):
            return True
        if _exit_is_conditional(_strip_comment(text), m.start()):
            # `if [ $v -ne 0 ]; then exit 1; fi`：**条件**里的常量退出码就是拒绝通道
            # （守卫的 rc 被读进条件）⇒ 算承载。无条件形态（`; echo done` ＋ `exit 0`）
            # 的扫描回看里没有条件关键字 ⇒ 仍判否。
            return True
    return False


# 条件关键字：`if` / `elif` / `[` / `[[` / `((`；`fi` 是条件块**结束**。
COND_OPEN_RE = re.compile(r"\bif\b|\belif\b|\[\[?|\(\(")
COND_CLOSE_RE = re.compile(r"\bfi\b")


def _exit_is_conditional(text: str, pos: int) -> bool:
    """`text[pos:]` 这条 `exit`／`return` 是否落在**条件块内**（回看最近的关键字）。

    只看"最近一个条件关键字是不是 `fi`"：`if …; then exit 1; fi; exit 0` 里
    `exit 1` 最近的是 `if`（条件内 ⇒ 承载），`exit 0` 最近的是 `fi`（条件外 ⇒ 不承载）。
    """
    head = text[:pos]
    opens = [m.start() for m in COND_OPEN_RE.finditer(head)]
    closes = [m.start() for m in COND_CLOSE_RE.finditer(head)]
    return bool(opens) and (not closes or opens[-1] > closes[-1])


def _swallow_expr(tail: str) -> bool:
    """守卫调用**之后**的尾巴 `tail` 是否把 rc 吞掉/盖掉。

    穷举本项要覆盖的同行与多行形态（每一条都在自检里有真驱动的反向对照）：
      * `""`（调用之后什么都没有）⇒ **不吞**：这一行（或这一行的命令）就是终判；
      * `|| true` / `|| :` / `&& true` / `; true` / `true` ⇒ **吞**（常量恒 0）；
      * `|| exit 0` / `; exit 0` / `exit 0`（常量退出码）⇒ **吞**；
      * `|| exit $rc` / `; exit $out` / `; exit $?` / `exit $((…))`（传 rc 的
        退出）⇒ **不吞**（这正是"rc 真进终判"的形态，不得误判成吞码）；
      * `; rc=$?` / `rc=$?`（同行捕获）⇒ **不吞**：`$?` 就是守卫的 rc，
        由调用方继续判"文件里有没有 `exit $rc`"（这是"同行 `;` 尾巴"与
        "同行吞码尾巴"的分界）；
      * `; echo done` / `; exit 0 && echo ok` 之类的普通尾巴 ⇒ **吞**
        （这条尾巴的 rc 才是这一行的 rc，守卫的 rc 一个字都没进终判）。
    判据是"尾巴的 rc 会不会等于守卫的 rc"：只有 `exit $<变量>`（含 `$?`）会。
    """
    if not tail:
        return False
    tail = tail.lstrip()
    if re.match(r"^(?:exit|return)\b", tail):
        # `exit <常量>` 吞码；`exit $v` / `exit $?` / `exit $#` / `exit $((…))` 是传递。
        return not re.match(r"^(?:exit|return)\b\s*[\"']?\$[A-Za-z_0-9?#(]", tail)
    if RC_ASSIGN_RE.match(tail):
        return False                     # `rc=$?`：守卫的 rc 被捕获（尚未使用）
    if REDIRECT_ONLY_RE.match(tail):
        return False                     # `2>&1` / `> out.log`：重定向不是别的命令
    return True


def _static_rc_assign(snippet: str, var: str) -> bool:
    """`snippet` 里是否有**无条件**把 `var` 覆盖成常量的赋值（`v=false`）。

    只认"行/段首即赋值、且右值不是 `$?`／命令替换"的形态。带 `||`/`&&` 前缀的
    条件赋值（`cmd || v=1`）**不算**覆盖——那种形态下 rc 仍可能原样传出。

    **逐行**判（`run-…-114` major 1 第四版探针实测：把整块交给 `re.match` 时
    `^` 只锚**串首**、`re.MULTILINE` 又救不了段中间的行 ⇒ `rc=$?\\nrc=0\\nexit $rc`
    这个"覆盖后传递"的形态照样判 True）。
    """
    if not snippet:
        return False
    pat = re.compile(rf"^[ \t]*(?:export[ \t]+)?{re.escape(var)}=(?!\$\?|\$\(|`)")
    return any(pat.match(seg) for seg, _sep in _split_commands(
        _mask_quotes(snippet)) for seg in seg.split("\n"))


# YAML **步骤边界**：`- name:` / `- uses:` / `- run:`（下一个 CI 步骤）——它之后的
# 命令属于**另一次执行**，不会把这一步的 rc 盖掉。
YAML_STEP_RE = re.compile(r"^\s*-\s*(?:name|uses|run|id)\s*:")


def _shell_noise_only(text: str) -> bool:
    """`text` 里是否只剩"**不执行命令**的行"（空行、`#` 注释、shell 提示符、单独的大括号）。

    用于"裸调用之后还有没有别的命令"这一判定：`run: |` 块末尾的 `}`（PowerShell 块
    结束）与 `$ ` 提示符都不是命令，而 `- name: …`（下一个 CI 步骤）与普通命令行都是。
    判"噪声"是**收紧**方向：认不出来的一律当命令（⇒ 判否）。
    """
    for line in text.splitlines():
        body = _strip_comment(line).strip()
        if not body or body in ("}", "{", "fi", "done", "esac") or body.startswith("$ "):
            continue
        return False
    return True


def _after_is_own_scope(text: str) -> bool:
    """裸调用之后的那段是否属于**别的执行单元**（YAML 下一个步骤／别的文件）。

    `ci.yml` 真形态：守卫调用是它那个 `run:` 块的**最后一条命令**（下一行是 `}`，
    再往下就是 `- name: Build reactflow frontend`）。GH 的 `run: |` 是**同一个 pwsh**
    跑完整个块 ⇒ 块内最后一条命令的 rc 就是该步骤的 rc，守卫的 rc 不会被后续步骤
    盖掉（后续步骤是**另一次机会**，各自独立判红）。故"下一个步骤边界"要当"调用行
    之后没有别的命令"处理——否则 CI 真形态会被判成"后面还有命令"而假红
    （`run-…-114` major 1 第十四版探针实测：自检 A-M12① 当场咬住）。
    """
    for line in text.splitlines():
        if not _strip_comment(line).strip():
            continue
        return bool(YAML_STEP_RE.match(line))
    return True


def _after_line(lines: list[str], idx: int) -> str:
    """`lines` 里**这次调用行之后**的部分（跳过调用行与紧随的下一行）。

    `run-…-114` major 1 第十三版探针实测：早先按 `_line_and_next` 的**块长度**切，
    而块永远是 2 行 ⇒ 在"调用在文件第 367 行"的真文件上切出来的是**文件开头两行**，
    于是 CI 真形态被判成"后面还有别的命令"⇒ 假红（自检 A-M12① 当场咬住）。
    按**行号**切才对。
    """
    return "\n".join(lines[idx + 2:])


def _line_and_next(lines: list[str], idx: int) -> str:
    """`idx` 行（含）与其**紧随的下一行**——`v=$(…)` / `rc=$?` 是两行的组合形态。"""
    return lines[idx] + "\n" + (lines[idx + 1] if idx + 1 < len(lines) else "")


def _hooks_from_ast(text: str) -> list[str] | None:
    """解析 `HOOKS = <字面量>` 的**结构**，取出其中的字符串清单。

    一个**可糊弄的子串**（复核 `run-…-091` minor 2 交付的正则
    `HOOKS\\s*=\\s*\\((?P<body>[^)]*)\\)`，G2 行 5）会栽在两种形态上：
      * **假绿**：`# HOOKS = ("pre-commit", "commit-msg")` 注释行照样命中
        ⇒ 真清单写成 `HOOKS = ()` 时判据仍绿（实测）；
      * **假红**：`HOOKS = ["pre-commit", "commit-msg"]`（合法 list 形态）
        不匹配元组正则 ⇒ 判据判 FAIL，而代码没有错（实测）。
    故改为按 `ast` 取赋值右值里的**字符串元素**（元组/列表都算，不需要求值、
    **不执行**被测文件）；解析不了（语法错 / 没有这个赋值）交给调用方 fail-closed。
    """
    import ast
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "HOOKS"
                   for t in node.targets):
            continue
        value = node.value
        if isinstance(value, (ast.Tuple, ast.List)):
            items = value.elts
        else:
            items = [value]
        if not all(isinstance(e, ast.Constant) and isinstance(e.value, str)
                   for e in items):
            return None          # 非常量元素 ⇒ 解析不出清单（fail-closed）
        return [e.value for e in items]
    return None


def _installs_hooks(text: str) -> bool:
    """安装器的 `HOOKS` 清单里必须**同时**含 `pre-commit` 与 `commit-msg`。

    修复验证复核 `run-…-091` minor 2 的原始形态：判据只核 `installer.is_file()` 与
    文本含 `--check`，**不核它装哪些钩子** ⇒ 把 `HOOKS = ("pre-commit", "commit-msg")`
    改成 `HOOKS = ("pre-commit",)`（模板仍在、仍调判据）时四处接线判据
    全绿。而在 `pre-commit` 改为 `--report-only` 之后，**本地层的终判压在 `commit-msg`
    上**（`pre-commit` 读不到署名 ⇒ 不判）——少了它，本地层对结构删除**既不拦也不判**，
    只剩 CI 一层。这是"模板存在"与"模板会被装上"之间的缺口。

    行 5（复核 `092` minor）：上一版只做到**文本子串层**（正则抓 `HOOKS = (…)` 的
    括号体再判子串）⇒ 注释一行同名清单即可糊弄。现在解析 `HOOKS` 的**结构**
    （`_hooks_from_ast`）。解析不出清单时的兜底（旧式 `HOOKS = <变量>`）保持
    **fail-closed**：判否，不猜。
    """
    names = _hooks_from_ast(text)
    if names is None:
        m = re.search(r"HOOKS\s*=\s*(?P<rest>[^\n]*)", text)   # 兜底：非字面量形态
        rest = _strip_comment(m.group("rest")) if m else ""
        names = re.findall(r"""["']([^"']+)["']""", rest)
    return "pre-commit" in names and "commit-msg" in names


def _option_in_guard_call(text: str, opt: str) -> bool:
    """`opt` 是不是**守卫调用**里的一个**带参**选项（命令位置 + 词元级取参）。

    行 4 同族：认的是"这条被执行的命令真的带着这个参数"，不是"这串字出现在文件里"。
    只扫 `_guard_command_lines`（真调用行）⇒ 注释、回显、`Write-Host` 标签里的
    同名字样一律不算；`--opt VALUE` 与 `--opt=VALUE` 两种写法都认。
    判"**存在一次**带参出现"（裸 `--opt` 收尾不算）——同名的裸写作不掩盖真参数。
    """
    for line in _guard_command_lines(text):
        words = line.split()
        for i, word in enumerate(words):
            if word == opt:
                if i + 1 < len(words) and _clean_word(words[i + 1]):
                    return True
            elif word.startswith(f"{opt}=") and _clean_word(word[len(opt) + 1:]):
                return True
    return False


def _cli_surface(text: str) -> tuple[set[str], set[str]] | None:
    """安装器 CLI 的**结构面**：`add_argument` 注册的选项集 + 被读取的属性名集。

    用 `ast`（同 `_hooks_from_ast` 一族）：不执行被测文件、注释与字符串冒充不了
    "注册"。解析不出（语法错）→ `None`，调用方 fail-closed。
    """
    import ast
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    options: set[str] = set()
    attrs: set[str] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    options.add(arg.value)
        elif isinstance(node, ast.Attribute):
            attrs.add(node.attr)
    return options, attrs


def _check_ok(text: str, opt: str, *, cli: bool = False) -> bool:
    """`opt` 是否**结构上**真的接线（行 22①）：裸文本出现不算。

    修前形态 = `f"{opt}" not in text`：注释里写一行字面即可满足——探针实测两处
    都假绿（`commit-msg` 的真参数被拿掉、`installer` 的 `add_argument("--check")`
    被拿掉，只要留一句注释，判据报零问题）。载体由调用方点名，两种结构不互相顶替：
      * `cli=False`（`commit-msg` 的 `--ack-file`）：必须是**守卫调用**里的带参选项
        （`_option_in_guard_call`，行 4 同一份"命令位置"语义）；
      * `cli=True`（安装器的 `--check`）：`ast` 里**注册**（`add_argument`）且**被
        读取**（`args.check`）的 CLI 档——声明了却没人读的选项不是"档"。
    """
    if not cli:
        return _option_in_guard_call(text, opt)
    surface = _cli_surface(text)
    if surface is None:
        return False                 # 解析不出 ⇒ 判否，不猜（fail-closed）
    options, attrs = surface
    return opt in options and opt.lstrip("-").replace("-", "_") in attrs


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
    # 读盘一次、结果留给下面两段判据共用（行 4/5 是结构判定，行 6 要按层核退出码）。
    def _text(p: Path) -> str:
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""

    ci_text = _text(ci)
    hook_text = _text(hook)
    chook_text = _text(commithook) if commithook else ""
    inst_text = _text(installer)
    if not ci.is_file():
        problems.append(f"[不可跳过] {CI_REL} 不存在——"
                        f"结构守卫的不可跳过层只能接在 CI 上（fail-closed）")
    elif not _invokes_guard(ci_text):
        problems.append(
            f"[不可跳过] {CI_REL} 里**命令位置**没有 `structure-guard.py verify "
            f"--from-git …`"
            f"（标签/注释里的同名字样不算）——守卫就退回『依赖人记得跑快照』的形态"
            f"（R1 第 6 次事故的根因）")
    if not hook.is_file():
        problems.append(f"[不可跳过] {HOOK_REL} 模板不存在"
                        f"（便利层缺失；CI 层仍在，但本地无即时拦截）")
    elif not _invokes_guard(hook_text):
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
    elif not _invokes_guard(chook_text):
        problems.append(f"[不可跳过] {COMMITHOOK_REL} 没有调用与 CI **同一条**判据")
    elif not _check_ok(chook_text, "--ack-file"):
        problems.append(f"[不可跳过] {COMMITHOOK_REL} 的守卫调用没有把**待提交信息"
                        f"文件**交给判据（`--ack-file <文件>` 必须出现在命令位置的"
                        f"调用里；注释/回显里的同名字样不算）⇒ 署名形同不存在")
    if not installer.is_file():
        problems.append(f"[不可跳过] {INSTALLER_REL} 不存在——`.git/hooks/` "
        f"不在版本控制里，"
                        f"没有安装器就只剩『记得手动拷』")
    elif not _check_ok(inst_text, "--check", cli=True):
        problems.append(f"[不可跳过] {INSTALLER_REL} 没有真的 `--check` 档"
                        f"（`add_argument(\"--check\", …)` 注册且被读取；注释里写一行"
                        f"字面不算）——『装没装』必须可核")
    elif not _installs_hooks(inst_text):
        problems.append(
            f"[不可跳过] {INSTALLER_REL} 的 `HOOKS` 清单没有**同时**装 "
            f"`pre-commit` 与 `commit-msg`（复核 `091` minor 2：`pre-commit` 已改为 "
            f"`--report-only`，本地层的**终判整个压在 `commit-msg` 上** ⇒ 少了它，"
            f"本地层对结构删除既不拦也不判，只剩 CI 一层）")
    # ---- 行 6（092 minor；E3：批 7／批 9 的**共同残余**）--------------------
    # 批 7 把 `pre-commit` 改成 `--report-only`（终判压到 `commit-msg`），
    # 批 9 修了 `structure-guard` 的基线 fail-open——**两批都没有给
    # "不许所有层都加 `--report-only`"留判据**。三处接线全加上它 = 整条链 fail-open：
    # 守卫逐条打印 `[FAIL]`，而每一处都 rc=0。
    # 判据分两半（都被反向对照 f′ 覆盖；判据本体 = `_enforces_exit_code`）：
    #   ① **三处合起来**至少有一次调用由退出码终判（不许"三处全 report-only"）；
    #   ② 终判层 `EXIT_CODE_JUDGE_REL`（= 不可跳过层 CI）自己不得让出终判。
    # 单层 report-only 是**合法**的（批 7 就是这么定的：本地早期层只报告、终判上移），
    # 故判据不禁止任何单独一层，只禁止"**没有任何一处**在拒绝"。
    layers = ((CI_REL, ci_text), (HOOK_REL, hook_text), (COMMITHOOK_REL, chook_text))
    report_only_here = [rel for rel, text in layers if _invokes_report_only(text)]
    if all(text for _, text in layers) and not any(
            _enforces_exit_code(text)[1] for _, text in layers):
        problems.append(
            f"[report-only/终判] {len(layers)} 处接线"
            f"（{', '.join(rel for rel, _ in layers)}）**全部**带 `--report-only`"
            f"（现测：{report_only_here}）⇒ 没有任何一处由**退出码**终判，"
            f"整条链 fail-open：守卫照样逐条打印 `[FAIL]`，三处却都 rc=0。"
            f"批 7／批 9 改完留下的正是这一格（E3）——本地层终判必须有载体，"
            f"不得三层全 report-only。")
    # ② 终判层自己不得让出。为什么单列一条、而不靠 ① 推出：① 是"三处合起来还有
    # 一处在判"，将来若把终判挂到别处（再加一个本地层）① 仍可能全绿，而
    # **不可跳过层**已经在只报告——那正是这个 Sprint 要治的"看起来很通过"。
    calls, enforces = _enforces_exit_code(ci_text)
    if not ci_text:
        problems.append(f"[report-only/终判] {CI_REL} 读不到内容 ⇒ 终判层无从判定"
                        f"（fail-closed，不把『没判』当『通过』）")
    elif calls and not enforces:
        problems.append(
            f"[report-only/终判] 终判层 {EXIT_CODE_JUDGE_REL}（不可跳过层）变成 "
            f"`--report-only` ⇒ 本地层可能没装、可能被 `--no-verify` 跳过，"
            f"这一层再只报告就**没有任何一层**在拒绝结构删除——正是行 6 要禁的形态。")
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
    # 行 8：落点 = **run 级唯一目录**（`mkdtemp`）里的四个探针——原实现是 `%TEMP%`
    # 下的固定文件名，并发实例会互相覆盖/删掉对方的探针（`finally` 里的 `unlink`
    # 更是直接删别人的）。`gate_root` 是 `mkdtemp` 的直接结果且只赋值一次，
    # 仍满足 `verify_artifact_paths.py` 的静态可判定要求（挂参数会被判动态目标）。
    gate_root = Path(tempfile.mkdtemp(prefix="gate-integrity-unskippable-"))
    ci_probe = gate_root / "ci.yml"
    hook_probe = gate_root / "pre-commit"
    inst_probe = gate_root / "installer.py"
    chook_probe = gate_root / "commit-msg"
    ci_probe.write_text((ROOT / CI_REL).read_text(encoding="utf-8"), encoding="utf-8")
    hook_probe.write_text((ROOT / HOOK_REL).read_text(encoding="utf-8"),
                          encoding="utf-8")
    inst_probe.write_text((ROOT / INSTALLER_REL).read_text(encoding="utf-8"),
                          encoding="utf-8")
    chook_probe.write_text((ROOT / COMMITHOOK_REL).read_text(encoding="utf-8"),
                           encoding="utf-8")
    # 行 6 的夹具用**仓库真文件**的文本（只读）：前置条件于是是真的。
    hook_txt = (ROOT / HOOK_REL).read_text(encoding="utf-8")
    chook_txt = (ROOT / COMMITHOOK_REL).read_text(encoding="utf-8")
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
        # ---- 行 22①（`_check_ok`：裸文本出现 → 结构判定）---------------------
        # 两处都从**仓库真文件**的文本出发（前置条件因此是真的）：真接线拿掉、
        # 只在注释里留字面 ⇒ 修前 `f"{opt}" not in text` 报零问题（探针实测假绿）。
        real_chook = (ROOT / COMMITHOOK_REL).read_text(encoding="utf-8")
        mut_chook = real_chook.replace(' --ack-file "$msgfile"', "")
        mut_chook = mut_chook.replace(
            "out=$(", "# 本钩子用 --ack-file（注释，不是参数）\nout=$(", 1)
        chook_probe.write_text(mut_chook, encoding="utf-8")
        ack_problems = _probe_problems()
        ok("行 22① 反向对照 r：`commit-msg` 的真参数被拿掉、只剩注释里的 "
           "`--ack-file` ⇒ FAIL（裸文本出现不算接线）",
           '--ack-file "$msgfile"' not in mut_chook
           and any("--ack-file" in p for p in ack_problems),
           next((p for p in ack_problems if "--ack-file" in p), ack_problems[:1]))
        chook_probe.write_text(real_chook, encoding="utf-8")
        # 安装器：`add_argument("--check", …)` 是**真档**；注释里写一行字面不算。
        # 变体保留 `args.check` 的**读取**（只删注册）⇒ 判据必须两条都核。
        real_inst = (ROOT / INSTALLER_REL).read_text(encoding="utf-8")
        mut_inst = real_inst.replace(
            'ap.add_argument("--check", action="store_true",',
            '# 本脚本有 --check 档（注释，不是真选项）\nap.add_argument("--nope",')
        inst_probe.write_text(mut_inst, encoding="utf-8")
        check_problems = _probe_problems()
        ok("行 22① 反向对照 s：安装器的 `--check` 只剩注释、`args.check` 仍在 "
           "⇒ FAIL（注册 + 读取才算档）",
           'add_argument("--check",' not in mut_inst
           and any("--check" in p for p in check_problems),
           next((p for p in check_problems if "--check" in p), check_problems[:1]))
        inst_probe.write_text(real_inst, encoding="utf-8")
        hook_probe.write_text(hook_txt, encoding="utf-8")   # b 的反向对照到此收工
        ok("行 22 夹具复原：两处真文件文本复原后接线判据回到零问题（防夹具自伤）",
           _probe_problems() == [], f"problems={_probe_problems()[:1]}")
        # ---- 行 4（`_invokes_guard` 由黑名单改**结构判定**）------------------
        call_ok = ("python scripts/structure-guard.py verify "
                   "--from-git $guardBase")
        ok("行 4 反向对照 f：真调用＋**行尾注释里的同名字样** ⇒ 判有调用（防假红）",
           _invokes_guard(f"{call_ok}   # 就是这一行 {call_ok}"),
           f"lines={_guard_command_lines(call_ok)}")
        ok("行 4 反向对照 g：只剩 `Write-Host` **日志标签** ⇒ 判无调用（087 major 1）",
           not _invokes_guard(f'Write-Host "{call_ok}"'))
        ok("行 4 反向对照 h：只剩**行尾注释** ⇒ 判无调用（新洞，修前假绿）",
           not _invokes_guard(f"run: echo placeholder   # {call_ok}"))
        ok("行 4 反向对照 i：只剩**变量赋值**（here-string/赋值族） ⇒ 判无调用",
           not _invokes_guard(f'cmd = "{call_ok}"'))
        ok("行 4 反向对照 j：`Write-Output` 回显 ⇒ 判无调用（旧黑名单漏掉的别名）",
           not _invokes_guard(f'Write-Output "{call_ok}"'))
        ok("行 4 防假红：`--from-git` 后面还有参数`--report-only` 仍算真调用",
           _invokes_guard(f"{call_ok} --report-only"),
           f"lines={_guard_command_lines(call_ok + ' --report-only')}")
        # ---- 行 22②（`ECHO_PREFIXES` 回显动词清单 → **默认判红**）------------
        # 清单的方向相反：**不在清单里**的动词照样冒充接线（探针实测 z1/z2 假绿）。
        # 新实现不看动词清单，只看**首词元**是否被正向认成命令。
        ok("行 22② 反向对照 z1：`Out-Host(\"python … verify …\")`（首词元含 `(` "
           "被静默丢弃 ⇒ 守卫脚本成了首词元）⇒ 判无调用",
           not _invokes_guard(f'Out-Host("{call_ok}")'))
        ok("行 22② 反向对照 z2：表格单元格里的同名字样（首词元 `|` 被丢弃）"
           "⇒ 判无调用",
           not _invokes_guard(f"| `{call_ok}` | 说明 |"))
        ok("行 22② 不回归：行首是代码跨度或花括号块（旧清单里的两项）仍判无调用",
           not _invokes_guard(f"`{call_ok}`")
           and not _invokes_guard(f"{{ {call_ok} }}"))
        ok("行 22② 防假红：三种真调用形态（引号解释器／无解释器／带目录解释器）"
           "都判有调用",
           _invokes_guard('out=$("$py" scripts/structure-guard.py verify '
                          '--from-git HEAD --report-only 2>&1)')
           and _invokes_guard("scripts/structure-guard.py verify --from-git HEAD")
           and _invokes_guard(".venv/Scripts/python.exe scripts/structure-guard.py "
                              "verify --from-git HEAD"))
        # ---- 行 30（复核 `run-…-104` minor 5）：`PY_WORD_RE` 的**词边界** --------------
        # 修前形态（探针实测）：第二支 `[\w${}]*py` 认"任何以 `py` 结尾的裸词"，
        # 于是下面的 `copy` / `happy` 两行判"有调用"（`empty` / `apply` 判无 ——
        # 读数由**词尾字母**决定而不是结构）。
        ok("行 30 反向对照 x1：`copy scripts/structure-guard.py verify …`"
           "（首词元以 `py` 结尾、但不是解释器）⇒ 判无调用（修前判有调用）",
           not _invokes_guard("copy scripts/structure-guard.py verify --from-git HEAD"),
           f"lines={_guard_command_lines('copy scripts/structure-guard.py verify --from-git HEAD')}")
        ok("行 30 反向对照 x2：`happy …` 同形 ⇒ 判无调用；且 `copy` / `happy` / "
           "`empty` / `apply` 四个裸词**一律**不认（读数不再取决于词尾字母）",
           not _invokes_guard("happy scripts/structure-guard.py verify --from-git HEAD")
           and [PY_WORD_RE.match(w) for w in ("copy", "happy", "empty", "apply")]
           == [None, None, None, None])
        ok("行 30 防假红：六种**真解释器形态**（`$py` / `${PY}` / `$py.exe` / `py` / "
           "`python.exe` / `python3.13`）仍被认成解释器；带引号变量与带目录解释器的"
           "真调用仍判有调用",
           all(PY_WORD_RE.match(w) for w in
               ("$py", "${PY}", "$py.exe", "py", "python.exe", "python3.13"))
           and _invokes_guard('out=$("$py" scripts/structure-guard.py verify '
                              '--from-git HEAD 2>&1)')
           and _invokes_guard('"$py.exe" scripts/structure-guard.py verify '
                              '--from-git HEAD')
           and _invokes_guard(".venv/Scripts/python.exe scripts/structure-guard.py "
                              "verify --from-git HEAD"))
        # ---- 行 5（`_installs_hooks` 由文本子串改**解析 HOOKS 结构**）--------
        ok("行 5 反向对照 k：`HOOKS` 被注释掉、真清单为空元组 ⇒ FAIL"
           "（修前子串假绿的原形态）",
           not _installs_hooks("# HOOKS = (\"pre-commit\", \"commit-msg\")\n"
                               "HOOKS = ()"))
        ok("行 5 反向对照 l：合法 list 形态 `HOOKS = [...]` 含两名 ⇒ PASS"
           "（修前元组正则认不出 ⇒ 假红）",
           _installs_hooks('HOOKS = ["pre-commit", "commit-msg"]'))
        ok("行 5 反向对照 m：list 里少了 `commit-msg` ⇒ FAIL（合法形态也要判）",
           not _installs_hooks('HOOKS = ["pre-commit"]'))
        ok("行 5 反向对照 n：兜底路径（`HOOKS = VARIANT`，值不在同一行）⇒ FAIL，"
           "不因解析不出而放行",
           not _installs_hooks('HOOKS = VARIANT["windows"]'))
        # ---- 行 6（三层全 `--report-only`）---------------------------------
        # 夹具用**仓库真文件**的文本（不是手写的假层）：前置条件"三处都在命令位置
        # 调用了守卫"因此是真的，不是判据自证。
        layers = (("CI", ci_text), ("pre-commit", hook_txt),
                  ("commit-msg", chook_txt))
        flags = [(len(_guard_command_lines(t)),
                  _enforces_exit_code(t)[1]) for _, t in layers]
        ok("行 6 前置条件：三处接线**都**在命令位置调用了守卫"
           "（没这个前置，下面的判据等于没触发）",
           all(n > 0 for n, _ in flags), f"(调用数, 由退出码终判)={flags}")
        ok("行 6 反向对照 o：仓库现状（`pre-commit` 单层 report-only）⇒ "
           "**至少一处**由退出码终判 ⇒ 不误报（批 7 的合法形态）",
           any(enforce for _, enforce in flags),
           f"(调用数, 由退出码终判)={flags}")
        all_ro = [_enforces_exit_code(f"{call_ok} --report-only")
                  for _ in layers]
        ok("行 6 反向对照 p：三处接线**全**带 `--report-only` ⇒ "
           "**没有一处**由退出码终判（判据本体的红条件）",
           not any(enforce for _, enforce in all_ro), f"all={all_ro}")
        ok("行 6 反向对照 p′：终判层（CI）自己带 `--report-only` ⇒ "
           "不可跳过层也只剩「上报」",
           _guard_command_lines(f"{call_ok} --report-only")
           and _enforces_exit_code(f"{call_ok} --report-only")[1] is False)
        ok("行 6 反向对照 q：混合（CI 非 report-only、本地层 report-only）⇒ "
           "判据**不得**报『全 report-only』（防假红）",
           any(_enforces_exit_code(f"{call_ok} --report-only")[1] is False
               for _ in layers)
           and _enforces_exit_code(call_ok)[1] is True)
        # ---- 行 6 加强（复核 `run-…-105` major 6）：rc 必须**真的**进终判 ----------
        # 旧实现只判"这一行不带 `--report-only`"，自陈充要、实为必要非充分：
        # 下面两种形态都不带 `--report-only`，却都把 rc 吞掉，而旧码判 True。
        swallow_capture = f"out=$({call_ok} 2>&1) || true"
        swallow_rcvar = f"{call_ok}\nrc=$?\necho done"
        ok("行 6 加强反证 r：`out=$(<守卫>) || true`"
           "（rc 被本行吞掉、且没有 `exit $out`）"
           "⇒ **不得**判『由退出码终判』（旧码判 True）",
           _enforces_exit_code(swallow_capture)[1] is False,
           f"{_enforces_exit_code(swallow_capture)}")
        ok("行 6 加强反证 s：`<守卫>; rc=$?; echo done`（rc 存进 `$?` 却再没用过）"
           "⇒ **不得**判『由退出码终判』（旧码判 True）",
           _enforces_exit_code(swallow_rcvar)[1] is False,
           f"{_enforces_exit_code(swallow_rcvar)}")
        ok("行 6 加强反证 t：同样的捕获形态，一旦真的 `exit $out` ⇒ 判『由退出码终判』"
           "（收紧不得把正确的传递形态判红）",
           _enforces_exit_code(swallow_capture.replace(" || true", "")
                               + "\nexit $out")[1] is True)
        ok("行 6 加强反证 u：`rc=$?` 形态，一旦真的 `exit $rc` ⇒ 判『由退出码终判』",
           _enforces_exit_code(swallow_rcvar.replace("echo done",
                                                     "exit $rc"))[1] is True)
        ok("行 6 加强反证 v：**裸调用**（没有赋值、没有吞码后缀）⇒ 它的 rc 就是终判",
           _enforces_exit_code(call_ok)[1] is True)
        ok("行 6 加强反证 w：仓库真三层的判定（批 7 的合法形态：`pre-commit` 只报告、"
           "`commit-msg` 用 `exit 1` 终判）在加强后**一条都不变**",
           [_enforces_exit_code(t) for _, t in layers] == flags,
           f"flags={flags}")
        ok("行 6 检测器不认注释：注释里写 `--report-only` 不算 report-only 档"
           "（否则新判据栽在同一种形态上）",
           not _invokes_report_only(f"# 本层不用 --report-only\n{call_ok}"))
        ok("行 6 检测器认命令位置：真调用带 `--report-only` ⇒ 检测器点名",
           _invokes_report_only(f"{call_ok} --report-only"))
        # ---- 行 6 加强②（复核 `run-…-114` major 1）：**同一行**的 `;`／`||`／`&&`／`&`
        # 尾巴也必须判否。旧版的判据只把**行首**当命令位置 ⇒ `;` 之后的尾巴
        # （`echo done`／`exit 0`／`rc=$?`）既不参与"调用是否裸"、也不参与
        # "rc 是否进终判"⇒ `… verify …; echo done` 判 True（**应 False**）。
        # 下面逐形态真驱动（每条都有反向对照；既有断言一条未减）。
        def _enf(body: str) -> bool:
            """这次调用是否由退出码终判（局部让断言行宽可控）。"""
            return _enforces_exit_code(body)[1]

        ok("行 6 加强② 反证 x1：**同一行** `… verify …; echo done`（104 报告逐字形态）"
           "⇒ 判否（旧码判 True）", _enf(f"{call_ok}; echo done") is False)
        ok("行 6 加强② 反证 x2：**同一行** `; echo done` ＋ 末行硬编码 `exit 0` ⇒ 判否"
           "（旧码判 True；`exit 0` 把 rc 盖成常量）",
           _enf(f"{call_ok}; echo done\nexit 0") is False)
        ok("行 6 加强② 反证 x3：**同一行** `; rc=$?; echo done`（`$?` 存进 `rc` 却再没"
           "用过）⇒ 判否（与多行形态 x3′ 结论必须一致）",
           _enf(f"{call_ok}; rc=$?; echo done") is False
           and _enf(f"{call_ok}\nrc=$?\necho done") is False)
        ok("行 6 加强② 反证 x4：`|| true` / `|| :` / `&& true` / `; true` 四种常量"
           "吞码尾巴 ⇒ 全判否", not any(_enf(f"{call_ok}{t}")
                                        for t in (" || true", " || :", " && true",
                                                  "; true")))
        ok("行 6 加强② 反证 x5：`|| exit 0` / `; exit 0` / `; exit $((1))`（**常量退出码**）"
           "⇒ 判否（旧 `SWALLOW_TAIL_RE` 只认 `|| true`／`|| :` ⇒ 前两条漏网）",
           not any(_enf(f"{call_ok}{t}")
                   for t in (" || exit 0", "; exit 0", "; exit $((1))", " || exit 1")))
        ok("行 6 加强② 反证 x6：`… verify … &`（后台化 ⇒ rc 连读都读不到）⇒ 判否",
           _enf(f"{call_ok} &") is False)
        ok("行 6 加强② 反证 x7：**同行** `; rc=$?` 之后真的 `exit $rc` ⇒ 判『由退出码"
           "终判』（收紧不得把同行真传递形态判红）",
           _enf(f"{call_ok}; rc=$?\nexit $rc") is True)
        ok("行 6 加强② 反证 x8：`|| exit $?`（传 `$?` 的退出）⇒ 判『由退出码终判』",
           _enf(f"{call_ok} || exit $?") is True)
        ok("行 6 加强② 反证 x9：`… verify …; exit $rc`（`$rc` **未绑定**）⇒ 判否"
           "（保守方向：认不出承载就不认）",
           _enf(f"{call_ok}; exit $rc") is False)
        ok("行 6 加强② 反证 x10：**多行** `rc=$?` 后无条件覆盖 `rc=0` ⇒ 判否"
           "（旧码只看『文件里有没有 `exit $rc`』⇒ 覆盖也算 ⇒ 假绿）",
           _enf(f"{call_ok}\nrc=$?\nrc=0\nexit $rc") is False)
        ok("行 6 加强② 反证 x11：调用之后**还有命令**、且末行是常量 `exit 0` ⇒ 判否"
           "（裸调用的 rc 不再等于文件 rc）",
           _enf(f"{call_ok}\necho done\nexit 0") is False)
        ok("行 6 加强② 反向对照 x12：仓库真三层判定在加强②后**一条不变**"
           "（`ci.yml` 由退出码终判；两个钩子各自按本层语义）",
           [_enforces_exit_code(t) for _, t in layers] == flags,
           f"flags={flags}")
        ok("行 6 加强② 引号感知：`echo \"a; b\"` 里的 `;` 不是分隔符、"
           "引号里的 `#` 不是注释起点（防假红）",
           _enf('echo "a; b" # note\n' + call_ok) is True
           and _enf('echo "a # b"\n' + call_ok) is True)
    finally:
        # 行 8：整目录回收（含四个探针；`ignore_errors` 与旧实现的 unlink 同口径）
        shutil.rmtree(gate_root, ignore_errors=True)

    # 行 34（P2 裁定：口径＝**条数**＋**分支感知**）：`run_suite.py`
    # 的判决句／条数棘轮。
    # 判据本体在 `run_suite.verdict_problems`（纯函数）——本闸门（"闸门的闸门"）把它
    # 逐形态驱动一遍，并静态钉住"它**真的被套件调用**"（否则删掉调用点 =
    # 判据形同不存在）。
    from verify.run_suite import (BRANCH_ASSERTION_FLOORS, BRANCH_VERDICT_SCOPE_MIN,
                                  SKIP_EXIT, SKIP_NOT_PASS_MARK, skip_verdict,
                                  suite_verdict_line,
                                  verdict_problems, verdict_scope_problems)  # noqa: PLC0415
    # 条数**从下限表派生**，不再写死：这里曾写死 `174`，而 `verify_agentops.py`
    # 加了一批判据（判决行／退出码同口径）后下限变 **177** ⇒ 写死的那个数当场变成
    # "低于下限"的坏样本，反向对照①会**假红**。同一个数出现在两处必然会漂移
    # （`docs/1-WORKFLOW.MD:440` 的"读数必须有来源"）。
    floor_ao = BRANCH_ASSERTION_FLOORS[("verify_agentops.py", True)]
    vline = f"ALL PASS ({floor_ao} assertions)"
    ok("行 34 反向对照①：判决句在末行、条数 = 本分支下限 ⇒ 无缺陷",
       verdict_problems("verify_agentops.py", ["x", vline], 0, True) == [], vline)
    ok(f"行 34 反向对照②：判决句在、条数**低于**下限"
       f"（{floor_ao - 1} < {floor_ao}）⇒ FAIL 且点名棘轮",
       any("棘轮" in p for p in
           verdict_problems("verify_agentops.py",
                            [f"ALL PASS ({floor_ao - 1} assertions)"], 0, True)),
       f"{floor_ao - 1} < {floor_ao}")
    ok("行 34 反证③：**没有判决句**（只有普通 PASS 行）⇒ FAIL"
       "（这正是行 34 的病：删掉一批自检后脚本照样退 0）",
       any("没有" in p for p in
           verdict_problems("verify_agentops.py", ["PASS: a", "PASS: b"], 0, True)),
       "无判决句")
    ok("行 34 反证④：末行是**具名 SKIP 横幅**且退 0 ⇒ FAIL（TG-19 M-B：SKIP≠PASS）",
       any("SKIP" in p for p in verdict_problems(
           "verify_agentops.py",
           [vline, "AGENTOPS SKIP[spec-absent-on-branch]（…不是通过）"],
           0, True)),
       "SKIP 横幅")
    ok("行 34 反证⑤：判决句在、但该分支**没登记下限** ⇒ FAIL（fail-closed）",
       any("没有登记断言数下限" in p for p in
           verdict_problems("verify_agentops.py", [vline], 0, True, floors={})),
       "floors 空")
    ok("行 34 对照⑥：非零退出**不**由本条重复报（退出码已由既有判据判红）",
       verdict_problems("verify_agentops.py", [], 1, True) == [], "code=1")
    ok("行 34 反向对照⑦：自陈脚本数 5 = 本分支下限 ⇒ 无缺陷；4 < 5 ⇒ FAIL"
       "（删掉 features 里的自陈字样 = 把该脚本移出棘轮 ⇒ 这条钉住）",
       verdict_scope_problems(5, True) == [] and bool(verdict_scope_problems(4, True)),
       f"下限={BRANCH_VERDICT_SCOPE_MIN.get(True)}")
    ok("行 34 反向对照⑧：分支感知——同一读数在 absent 侧（下限 15）放行、"
       "在 present 侧（下限 17）判红（「全局一个数」必然误判一边）",
       verdict_problems("verify_card_index.py", ["ALL PASS (15 assertions)"],
                        0, False) == []
       and bool(verdict_problems("verify_card_index.py",
                                 ["ALL PASS (15 assertions)"], 0, True)),
       f"floors={BRANCH_ASSERTION_FLOORS.get(('verify_card_index.py', True))}/"
       f"{BRANCH_ASSERTION_FLOORS.get(('verify_card_index.py', False))}")
    rs_src = (ROOT / "verify" / "run_suite.py").read_text(
        encoding="utf-8", errors="replace")
    ok("行 34 判据**真被套件调用**（静态钉住调用点：删掉接线 = 判据形同不存在）",
       len(re.findall(r"^\s*vp = verdict_problems\(", rs_src, re.MULTILINE)) == 1
       and "verdict_scope_problems(len(declared), branch_present)" in rs_src,
       "run_suite.py 调用点")

    # 第三态（SKIP，2026-09-30 本批）：套件多了一档"既不计 PASS 也不计 FAIL"。
    # 判据本体在 `run_suite.skip_verdict` / `run_suite.suite_verdict_line`（纯函数）——
    # 这里（"闸门的闸门"）逐形态驱动一遍，并静态钉住"**真的被套件接线**"：
    # 删掉调用点 / 把 rc 改回 0，本闸门必须红。
    _banner = (f"AGENTOPS SKIP[spec-absent-on-branch]（1 条判据未执行）"
               f"——其余 170 条已验，**{SKIP_NOT_PASS_MARK}**")
    ok("第三态①：**具名 SKIP**（rc=3 ＋ 末行横幅）⇒ 归 skipped 档并带出分类",
       skip_verdict([_banner], SKIP_EXIT) == ("skipped", "spec-absent-on-branch"),
       f"{skip_verdict([_banner], SKIP_EXIT)}")
    ok("第三态②（反向对照）：末行有横幅却 rc≠3 ⇒ **不**归 skipped"
       "（两通道矛盾；rc=0 与 rc=1 两种都不认）",
       skip_verdict([_banner], 0)[0] == "mismatch"
       and skip_verdict([_banner], 1)[0] == "mismatch",
       f"rc0={skip_verdict([_banner], 0)[0]} rc1={skip_verdict([_banner], 1)[0]}")
    ok("第三态③（反向对照）：rc=3 但末行**没有**具名横幅 ⇒ 不是 SKIP"
       "（否则任何脚本退 3 就能溜出 PASS/FAIL 记账）",
       skip_verdict(["PASS: a", "BOOM: rc=3"], SKIP_EXIT)[0] == "none"
       and skip_verdict([f"AGENTOPS SKIP[x] 本行不是 PASS"], SKIP_EXIT)[0] == "none"
       and skip_verdict([_banner, "NOTE: 横幅之后还有输出"], SKIP_EXIT)[0] == "none",
       "无横幅/缺『本档不是通过』/横幅不在末行 三形态")
    _one = [{"name": "verify_agentops.py", "category": "spec-absent-on-branch"}]
    ok("第三态④：末行**显式区分**——skipped 不混进 PASSED 的脚本数、且判决句带分类与"
       "『本档不是通过』（absent 侧形态）",
       suite_verdict_line(26, [], _one)
       == (f"SUITE PASSED (25 scripts, 1 skipped): "
           f"verify_agentops.py[spec-absent-on-branch]"
           f" —— 无失败，但 1 个脚本的判据未执行（SKIP≠PASS）⇒ {SKIP_NOT_PASS_MARK}"
           f"（rc={SKIP_EXIT}）"),
       suite_verdict_line(26, [], _one))
    ok("第三态⑤：零跳过时判决句与既有形态**逐字一致**（windows 侧零回归）",
       suite_verdict_line(26, [], []) == "SUITE PASSED (26 scripts)"
       and suite_verdict_line(26, ["verify_x.py"], [])
       == "SUITE FAILED (1/26): verify_x.py",
       f"{suite_verdict_line(26, [], [])} / "
       f"{suite_verdict_line(26, ['verify_x.py'], [])}")
    ok("第三态⑥（反向对照）：failed 与 skipped 同时出现 ⇒ **failed 优先**，"
       "且跳过档另列可见（不得因'有跳过'把失败说轻）",
       suite_verdict_line(26, ["verify_x.py"], _one).startswith(
           "SUITE FAILED (1/26, 1 skipped):")
       and "另有 skipped" in suite_verdict_line(26, ["verify_x.py"], _one),
       suite_verdict_line(26, ["verify_x.py"], _one))
    ok("第三态判据**真被套件调用**（静态钉住接线：判据本体 ＋ rc 两处，"
       "删任一处 = 形同不存在）",
       len(re.findall(r"^\s*state, detail = skip_verdict\(tail, code\)",
                      rs_src, re.MULTILINE)) == 1
       and "suite_verdict_line(len(picked), failed, skipped)" in rs_src
       and len(re.findall(r"^\s*return SKIP_EXIT$", rs_src, re.MULTILINE)) == 1,
       "run_suite.py 的第三态调用点")

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
