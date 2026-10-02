"""Sprint-16 TG-5：分层验证 runner（fail-closed + 三态预算闸门）。

按 VERIFY_META.tier 分层执行 verify/ 下的脚本：
  offline = 零网络零 key（CI/本地默认）
  gui     = 需前后端 + Playwright
  network = 真实 API e2e（**花钱**，受预算上限约束）

语义（调研 run-2026-09-12-tech-research-047 采纳）：
  ① **fail-closed**：任一层任一脚本失败 → 整体 FAIL（非零退出，不"部分通过"）；
  ② **预算闸门**：启动前按 VERIFY_META.est_cost_cny 求上界，超上限 → **拒绝启动**（退出码 3，不静默降级）；
  ③ **三态记账**：本轮实际花费 = 由账本/价表核对；runner 自身不臆测花费——network 档记 `cost_status=unknown`
     并提示用真实用量回填（下一轮夜间套件遇到 unknown 会拒绝放行，见 scripts/scheduled-tasks.py）；
  ④ 上限与周期一律可配置：`--budget-cny` > env `PAPERQA_NIGHTLY_BUDGET_CNY` > 默认 10（D3 约束：不得写死）。
  ⑤ **第三态（SKIP）**：子脚本 rc=**3** 且末行是**具名 SKIP 横幅**
     （`<NAME> SKIP[<分类>]…本档不是通过`）⇒ 归入 skipped 档：
     **既不计 PASS 也不计 FAIL**，末行与 summary 都显式点名
     （`SUITE PASSED (23 scripts, 1 skipped): verify_agentops.py[…]`），
     套件自身 rc 取 **3**（"没有失败，但有判据未执行"——与 `spend-report --check`／
     `verify_agentops.py::SKIP_EXIT` 同码；取 0 就是"SKIP 冒充通过"）。
     两通道只满足其一都不是 SKIP，见 `skip_verdict()` 与
     `suite_verdict_line()`。

用法：
  .venv\\Scripts\\python.exe verify\\run_suite.py --tier offline
  .venv\\Scripts\\python.exe verify\\run_suite.py --tier network --budget-cny 10
  .venv\\Scripts\\python.exe verify\\run_suite.py --tier offline --verify-dir <fixture> --json <out>

结果 JSON（F4，2026-09-25 起**总是**写）：`--json` 默认 = `verify/suite_result.json`（已 gitignore），
且**启动时先落一份 `status=running` 的占位**再执行——中途崩/被杀留下的是"正在跑"，
而不是上一轮那份看起来仍像最新结果的 `ok`（`scheduled-tasks` 只认 `cost_status=measured`，占位不会被误采信）。
"""
from __future__ import annotations
VERIFY_META = {'features': 'TG-5 分层 runner：offline/gui/network 分层 + fail-closed + 三态预算闸门（上限可配置）+ 第三态 SKIP（rc=3：具名 SKIP 两通道同口径，既不计 PASS 也不计 FAIL）', 'tier': 'offline', 'providers': [], 'est_seconds': 5, 'est_cost_cny': 0, 'routes': [], 'requires': []}

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from verify.verify_matrix import collect  # noqa: E402

SELF_NAMES = {"run_suite.py"}

# 复核 `run-…-105` major 8：`VERIFY_META.est_seconds` 是**分支无关常量**，而实测耗时
# 随分支差 **110 倍**——`verify_decision_register.py` 在 windows 上约 5s（1248 个指针
# 里绝大多数指向本分支**存在**的文件，只有真正缺失的才走 git），在 main 上约 173s
# （1106 个指针指向 windows-only 的 `docs/iteration/**`，每个都要 git 问一次）。
# 本表把**按分支实测**的超时基准声明化：键 = "该路径在本分支的提交树里存在吗"，
# 值 = 该分支下的 `est_seconds`。`est_seconds` 本体保留一个**分支无关的上界**
# （`max`，见下），故任何一边都不会被低估。
#
# 取值口径（两者都是**实测**，不是猜的）：
#   * present（windows 分支）：本批修复后实测 1.4–2.9s ⇒ 取 5s（含余量）；
#   * absent（main 镜像）：修复前实测 173.1s、修复后实测 2.9s ⇒ 仍取 200s，
#     因为"该子树在本分支不存在"只是**当前**镜像事实：将来 main 若同步进更多
#     指向**别处** windows-only 子树的指针，耗时还可能上去，而超时上限宁松勿紧
#     （紧了就是把正常脚本判成 `TIMEOUT`＝假红）。
PROBE_KEY = "docs/iteration"
BRANCH_EST_OVERRIDES: dict[tuple[str, bool], float] = {
    ("verify_decision_register.py", True): 5.0,
    ("verify_decision_register.py", False): 200.0,
}

# -------------------------------------------------------- 行 34
# 判决句 ＋ 条数棘轮（口径＝按条数、必须分支感知）
# G2 复盘行 34（二查 `run-…-104` nit 9）：多处 `VERIFY_META['features']` 已把写死的
# "含 N 条反向对照"改成"见末行 `ALL PASS (N assertions)`"（方向正确），
# 但**没有任何判据**
# 要求 `--selftest` 真的跑到那句判决句——删掉一批 `ok()` 之后脚本照样退 0，只是 N 变小，
# 而 N 不被任何地方钉住。
#
# P2 裁定口径：**按「条数」**，且**必须分支感知**（同一判据在两分支的读数不同 ⇒ 下限也
# 必须分支感知；同 `BRANCH_EST_OVERRIDES`／指针短路同一思路）。
#
# 判据（对**自陈**了"条数见末行 `ALL PASS (N assertions)`"的脚本，逐脚本三道）：
#   ① 判据句必须真的出现（接受两种已声明的形态：`ALL PASS (N assertions)` 或
#      `EVIDENCE: <本脚本> assertions=N rc=0 …`）——"退 0"不等于"自检跑到了末行"；
#   ② 若末行是具名 SKIP 横幅（`<NAME> SKIP[...]`），**不算通过**（`TG-19` M-B：
#      SKIP 与 PASS 互斥；脚本自己就写着"本档不是通过"）；
#   ③ N 不得低于**本分支实测下限**（只增不减；删断言 ⇒ N 下降 ⇒ 红）；
#   ④ 自陈脚本的**数量**不得低于本分支下限（靠删掉 features 里的自陈来躲开棘轮 ⇒ 红）。
# 取值口径（全部**实测**，两侧都不是猜的；present = windows 工作树，
# absent = "windows 树减掉 `docs/iteration/**`"的**镜像**——与 `BRANCH_EST_OVERRIDES`
# 同口径：当前 `main` ref 上这几个脚本／登记册本身缺席，故 absent 侧只能用镜像量）：
#   * `verify_agentops.py`：present **180**；absent 侧**不登记下限** —— 该侧脚本
#     退 **3**（`verdict_exit`：`AGENTOPS SKIP[…]` 判决行与退出码同口径），
#     判据①/②在非零退出上短路，红由既有"非零退出"判据给出（**不是**假绿）。
#     **2026-09-30 本批更正**：此前这里写"该侧只打 SKIP 横幅且**退 0** ⇒ 套件把它算成
#     PASS"，实测**不成立**——`verdict_problems` 在 rc=0 且末行是具名 SKIP 横幅时
#     **本来就报红**（判据②）。真正的缺陷是"判决行说不是通过、退出码说成功"的
#     两通道矛盾，已由 `verify_agentops.py::verdict_exit` 收紧为 rc=3。
#   * `verify_card_index.py`：**唯一**两侧读数不同的脚本（17／15：absent 侧少 2 条依赖
#     windows-only 卡文件的判据）——正是"下限必须分支感知"的实例。
#   * `verify_decision_register.py` 32／32、`verify_derived_numbers.py` 19／19、
#     `verify_gate_integrity.py` 88／88（两侧同值：它们的断言不依赖 `docs/iteration`）。
#     **2026-09-30 本批同步（复核 `run-…-114` minor 2）**：该键此前写 **68**，而现跑
#     已是 **75**（`6a0cfc9` 加了 7 条判据却没抬下限）⇒ 与本表其它项（`verify_agentops.py`
#     174→177 同步抬）做法不一致，也违反本文件 `:93-94` 自陈的"只增不减"：
#     下限 68 ⇒ **删掉 7 条 `ok()` 仍判绿**。本批先抬到 75（同批复核 gap），
#     再随本批新增的 13 条断言抬到 **88**（两侧同值：该脚本的断言不依赖
#     `docs/iteration`，与上面的口径一致）。**同批另一处同类余量**：
#     `verify_agentops.py` 因本批新增 UC-26 三条断言（177→180）⇒ 该键同步抬到 **180**
#     （同批再复核本表其余各行，**只这两行有余量**）。
#     **2026-10-03 本批同步**：`verify_agentops.py` 新增 UC-27（成本预算阻断，
#     18 条断言）⇒ 现跑 **198**，该键同步抬到 **198**（`:93` 的"只增不减"：
#     不抬 ⇒ 删掉这 18 条判据仍判绿，等于本批白做）。其余各行本批复核后**无余量**。
#     复算口径 = 在工作树跑 `verify/verify_gate_integrity.py --selftest` 读末行
#     `ALL PASS (N assertions)`。
# 复算：`present` = 在工作树跑该脚本、读末行；`absent` = 在 %TEMP% 镜像（clone 后
# `git rm -r docs/iteration` 并提交、再把工作区改动同步进去、补上 gitignore 的
# `agents/runtime`＋`agents/runs`）里跑同一脚本。
VERDICT_LINE_RE = re.compile(r"^ALL PASS \((\d+) assertions\)$")
VERDICT_EVIDENCE_RE = re.compile(
    r"^EVIDENCE: (?P<name>[\w.\-]+) assertions=(?P<n>\d+)\s")
SKIP_VERDICT_RE = re.compile(r"^\S+ SKIP\[")
VERDICT_TAIL_LINES = 6          # 判决句必须落在输出的**末尾这几行**内（末行判决句）

# -------------------------------------------------------- 第三态（SKIP）
# 第三态的语义：**既不计 PASS 也不计 FAIL**（2026-09-30 本批）。
# 承接 `run-…-110` 把 `verify_agentops.py` 的"spec 缺席"档从 rc=0 收紧为 rc=3
# （判决行与退出码同口径）：套件此前只有两态（rc=0 = PASS / rc≠0 = FAIL），于是
# "该判据在本分支**无从执行**"这个第三态被 rc≠0 撞成了假红——absent 镜像实测
# `SUITE FAILED (1/26): verify_agentops.py`（**没有一条真判据失败**）。
#
# 具名 SKIP 的判据 = **两个通道同时**说"本档不是通过"（缺一不可）：
#   ① 退出码通道：rc == SKIP_EXIT(3)；
#   ② 判决行通道：输出**末行**是 `<NAME> SKIP[<分类>]…本档不是通过` 形态的横幅
#      （`SKIP_VERDICT_RE` 命中 + 含 `SKIP_NOT_PASS_MARK`；形态真源 =
#      `verify_agentops.py::verdict_line`）。
# 两通道只满足其一的都**不是** SKIP —— 这正是"假 SKIP 不得归入 skipped"的反向对照目标：
#   * rc=3 却无具名横幅：**照旧按失败计**（否则任何脚本退 3 就能溜出 PASS/FAIL 记账）；
#   * 有具名横幅却 rc≠3：两通道互相矛盾 ⇒ **不**归入 skipped，上屏 WARN。
#     **2026-09-30 本批已把仅有的那一处实例修掉**：`verify_close_readiness.py` 的
#     SKIP 档原为 `rc=0 ＋ SKIP 横幅`（既上屏"不是通过"、退出码又说成功），
#     现按 `verify_agentops.py` 的同一真源做法对齐到 rc=3
#     （`verdict_line`／`verdict_exit`：判决行与退出码同源）。
#     本 WARN 分支**保留**：它盯的是"将来新出现的同形态脚本"，不因修完一处就撤掉。
SKIP_EXIT = 3    # 与 `verify_agentops.py::SKIP_EXIT` / `spend-report` 同码
SKIP_NOT_PASS_MARK = "本档不是通过"
SKIP_BANNER_RE = re.compile(r"^\S+ SKIP\[(?P<cat>[^\]]+)\]")
BRANCH_ASSERTION_FLOORS: dict[tuple[str, bool], int] = {
    ("verify_agentops.py", True): 198,
    ("verify_card_index.py", True): 17, ("verify_card_index.py", False): 15,
    ("verify_decision_register.py", True): 32,
    ("verify_decision_register.py", False): 32,
    ("verify_derived_numbers.py", True): 19, ("verify_derived_numbers.py", False): 19,
    ("verify_gate_integrity.py", True): 88, ("verify_gate_integrity.py", False): 88,
}
BRANCH_VERDICT_SCOPE_MIN: dict[bool, int] = {True: 5, False: 5}
TAIL_KEEP = 60                  # 每个脚本留最后 60 行（判决句判据只读末尾数行）


def path_in_tree(rel: str) -> bool:
    """`rel` 是否在**本分支 `HEAD`** 的提交树里（分支感知的唯一事实来源 = git）。

    判据用**直接证据**（`git ls-tree`），不用"父目录在不在"这类间接推断——
    口径同 `verify/agent_policy.py::path_in_head`（`TG-17` G2 条目 3/7 立的口径）。
    """
    r = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "--name-only", "HEAD",
                        "--", rel], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        # git 不可用（shallow/无仓库）⇒ 当作"存在"（现值），fail-closed 到**更紧**的
        # 那一档：估小了会被超时杀掉（响亮失败），估大了只是慢一点。
        return True
    return bool((r.stdout or "").strip())


def effective_est_seconds(name: str, meta: dict) -> float:
    """按**当前分支**给 `est_seconds` 定值（有实测覆盖表时用覆盖值）。

    返回超时判定用的秒数；无覆盖项 ⇒ 原值（既有行为一字不变）。
    """
    override = BRANCH_EST_OVERRIDES.get((name, path_in_tree(PROBE_KEY)))
    if override is None:
        return float(meta.get("est_seconds") or 60)
    return override


def declared_verdict_scripts(picked: list[tuple[Path, dict]]) -> list[str]:
    """本轮里**自陈**了"条数见末行 `ALL PASS (N assertions)`"的脚本名（按名字排序）。

    自陈是 `VERIFY_META.features` 里的显式字样（不是"我看它源码里有 ok()"）——
    口径与行 34 的原文一致：这几处 features 自己承诺了"条数见末行"。
    """
    return sorted(p.name for p, m in picked
                  if "ALL PASS (N assertions)" in str(m.get("features") or ""))


def verdict_problems(name: str, tail: list[str], code: int, branch_present: bool,
                     floors: dict[tuple[str, bool], int] | None = None) -> list[str]:
    """行 34 的**纯函数**判决：`(该脚本的问题清单)`；空清单 = 这一道过。

    `tail` = 该脚本输出的末尾若干行（去空行）。判据见 `BRANCH_ASSERTION_FLOORS` 
    上方注释。
    抽成纯函数是为了让反向对照能直接驱动它（不必真去改一个脚本的断言数）。
    """
    table = BRANCH_ASSERTION_FLOORS if floors is None else floors
    problems: list[str] = []
    if code != 0:
        return problems          # 非零退出已由既有判据判红；这里不重复报
    last = [ln.rstrip() for ln in tail if ln.strip()]
    if last and SKIP_VERDICT_RE.match(last[-1]):
        problems.append(
            f"[行34] 自陈『条数见末行』却以**具名 SKIP 横幅**收尾且退 0："
            f"{last[-1][:80]}——`TG-19` M-B 口径要求 SKIP 与 PASS 互斥"
            f"（脚本自己写着『不是通过』，套件却把它算成 PASS）")
    n_found: int | None = None
    for line in reversed(last[-VERDICT_TAIL_LINES:]):
        m = VERDICT_LINE_RE.match(line)
        if m:
            n_found = int(m.group(1))
            break
        m = VERDICT_EVIDENCE_RE.match(line)
        if m and m.group("name") == name:
            n_found = int(m.group("n"))
            break
    if n_found is None:
        problems.append(
            f"[行34] 自陈『条数见末行 `ALL PASS (N assertions)`』，但输出末尾 "
            f"{VERDICT_TAIL_LINES} 行内**没有**判决句 ⇒ 判据没跑到末行就不能算通过"
            f"（末行：{(last[-1][:80] if last else '（无输出）')}）")
        return problems
    key = (name, branch_present)
    floor = table.get(key)
    if floor is None:
        problems.append(
            f"[行34] {name} 在 present={branch_present} 上**没有登记断言数下限**"
            f"（fail-closed：打印了判决句就必须有基线，否则棘轮可被『不登记』绕过）")
        return problems
    if n_found < floor:
        problems.append(
            f"[行34 棘轮] {name} 断言数 {n_found} < 本分支下限 {floor}"
            f"（present={branch_present}）——只增不减：删掉一批自检会让这条红")
    return problems


def verdict_scope_problems(present_count: int, branch_present: bool,
                           mins: dict[bool, int] | None = None) -> list[str]:
    """行 34 判据④的**纯函数**：自陈脚本数不得低于本分支下限（删自陈 = 躲棘轮）。"""
    table = BRANCH_VERDICT_SCOPE_MIN if mins is None else mins
    floor = table.get(branch_present)
    if floor is None:
        return [f"[行34] 分支判据 present={branch_present} 无自陈脚本数下限"
                f" ⇒ fail-closed"]
    if present_count < floor:
        return [f"[行34 棘轮] 自陈『条数见末行』的脚本只有 {present_count} 个 < 下限 "
                f"{floor} 个（present={branch_present}）——删掉 `VERIFY_META.features` "
                f"里的自陈字样就会把该脚本移出棘轮范围 ⇒ 这条把它钉住"]
    return []


def skip_verdict(tail: list[str], code: int) -> tuple[str, str]:
    """第三态判决（**纯函数**；反向对照与端到端夹具都直接驱动它）：`(态, 说明)`。

    态三值（口径见 `SKIP_EXIT` 上方注释）：
      * `("skipped", <分类>)`：**具名 SKIP** —— rc=3 **且**末行是
        `<NAME> SKIP[<分类>]…本档不是通过` 横幅 ⇒ 既不计 PASS 也不计 FAIL；
      * `("mismatch", <说明>)`：末行有具名横幅却 rc≠3 ⇒ 两通道矛盾，**不**归入 skipped
        （调用方上屏 WARN；是 PASS 还是 FAIL 交回原有判据）；
      * `("none", "")`：与第三态无关（rc=3 却无横幅 / 普通 PASS / 普通失败）。
    """
    last = [ln.rstrip() for ln in tail if ln.strip()]
    cat: str | None = None
    if last:
        m = SKIP_BANNER_RE.match(last[-1])
        if m and SKIP_NOT_PASS_MARK in last[-1]:
            cat = m.group("cat")
    if code == SKIP_EXIT:
        return ("skipped", cat) if cat is not None else ("none", "")
    if cat is not None:
        return "mismatch", (f"末行是具名 SKIP 横幅（分类 {cat}）"
                            f"却 rc={code}≠{SKIP_EXIT}"
                            f"——判决行说『{SKIP_NOT_PASS_MARK}』、退出码却说成功")
    return "none", ""


def skipped_badge(skipped: list[dict]) -> str:
    """skipped 档的点名片：`verify_agentops.py[spec-absent-on-branch]`（逗号分隔）。

    **末行、行 34 读数段、summary 三处共用**——三处各拼一次字符串必然漂移。
    """
    return ", ".join(f"{e['name']}[{e.get('category') or '?'}]" for e in skipped)


def suite_verdict_line(total: int, failed: list[str], skipped: list[dict]) -> str:
    """套件**末行判决句**（单一真源；三态各说各的，互不冒充）。

    * 有 failed ⇒ `SUITE FAILED (n/total[, m skipped]): …`——**failed 优先**（rc=1），
      skipped 另列，不得因为"有跳过"而把失败说轻；
    * 无 failed 但有 skipped ⇒
      `SUITE PASSED (total-m scripts, m skipped): name[分类] —— 本档不是通过`。
      **skipped 不混进 PASSED 的脚本数**（写 `total-m scripts`）：
      把跳过的算进"通过"就是冒充全绿；
    * 都没有 ⇒ `SUITE PASSED (total scripts)`——与既有形态**逐字一致**
      （windows 侧零回归）。
    """
    badge = skipped_badge(skipped)
    if failed:
        head = f"SUITE FAILED ({len(failed)}/{total}"
        head += f", {len(skipped)} skipped" if skipped else ""
        tail = f" —— 另有 skipped（判据未执行，非 PASS）：{badge}" if skipped else ""
        return f"{head}): {', '.join(failed)}{tail}"
    if skipped:
        n_ok, n_sk = total - len(skipped), len(skipped)
        return (f"SUITE PASSED ({n_ok} scripts, {n_sk} skipped): {badge}"
                f" —— 无失败，但 {n_sk} 个脚本的判据未执行（SKIP≠PASS）"
                f"⇒ {SKIP_NOT_PASS_MARK}（rc={SKIP_EXIT}）")
    return f"SUITE PASSED ({total} scripts)"


# F4（2026-09-25）：结果 JSON 的**标准路径**。原实现 `--json` 默认为空字符串，而 `_write_json("")`
# 直接 return ⇒ 默认跑一次 `run_suite.py --tier offline` **不刷新** `verify/suite_result.json`，
# 那份旧文件（上次 network 档留下的）看起来仍像"最新结果"——读的人要翻 `finished_at` 才发现不是本轮。
# 现改为：默认就写这个路径（它已在 `.gitignore` 内 → 不产生 git 产物），
# 并在**启动时**先落一份 `status=running` 的占位（中途崩/被杀留下的是"正在跑"，不是旧的 `ok`）。
SUITE_RESULT_REL = "verify/suite_result.json"
DEFAULT_BUDGET_CNY = 10.0
EST_SAFETY_FACTOR_DEFAULT = 1.3  # 预检上界 = Σest_cost_cny × 系数（可配置：--est-factor / PAPERQA_EST_SAFETY_FACTOR）
REFUSE_EXIT = 3


def budget_from(args) -> float:
    """上限优先级：CLI > env PAPERQA_NIGHTLY_BUDGET_CNY > 默认 10（可配置，不写死常量语义）。

    **必须是有限正数**：`nan` 会让 `est_cost > budget` 恒为 False（裸比较）→ 闸门被静默绕过
    （复核 run-053 Round 5 major#1 同型问题；预算与系数两条入口都要挡）。
    """
    raw: object = args.budget_cny if args.budget_cny is not None else os.environ.get("PAPERQA_NIGHTLY_BUDGET_CNY")
    if raw is None or raw == "":
        return DEFAULT_BUDGET_CNY
    try:
        val = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        print(f"WARN: PAPERQA_NIGHTLY_BUDGET_CNY 非法（{raw!r}）→ 回落默认 {DEFAULT_BUDGET_CNY}")
        return DEFAULT_BUDGET_CNY
    if not math.isfinite(val) or val <= 0:
        print(f"WARN: 预算上限必须为有限正数（{raw!r}）→ 回落默认 {DEFAULT_BUDGET_CNY}（不放松闸门）")
        return DEFAULT_BUDGET_CNY
    return val


def est_factor_from(args) -> float:
    """预估安全系数（**可配置**，2026-09-21 用户口径）：CLI `--est-factor` > env `PAPERQA_EST_SAFETY_FACTOR` > 默认 1.3。

    为什么需要系数：`VERIFY_META.est_cost_cny` 记的是"近次实测值"，而预检闸门需要的是**上界**——
    实测 ¥1.013 而 est 定 1.1 时只剩 8.6% 余量，一次略长的运行就会被误拒（真花钱反而更少），
    故默认 ×1.3 留余量。

    **必须是有限正数**（复核 run-053 Round 5 major#1 实测）：只挡 `<=0` 不够——`--est-factor nan`
    或 env `=nan` 会让 `est_cost=nan`，而闸门是裸比较 `est_cost > budget` → **NaN 比较恒 False → 直接放行**。
    故用 `math.isfinite` 一并挡掉 `nan/inf`，非法值一律回落默认（绝不放松闸门）。
    """
    raw: object = args.est_factor if args.est_factor is not None else os.environ.get("PAPERQA_EST_SAFETY_FACTOR")
    if raw is None or raw == "":
        return EST_SAFETY_FACTOR_DEFAULT
    try:
        val = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        print(f"WARN: est 安全系数非法（{raw!r}）→ 回落默认 {EST_SAFETY_FACTOR_DEFAULT}")
        return EST_SAFETY_FACTOR_DEFAULT
    if not math.isfinite(val) or val <= 0:
        print(f"WARN: est 安全系数必须为有限正数（{raw!r}）→ 回落默认 {EST_SAFETY_FACTOR_DEFAULT}（不放松闸门）")
        return EST_SAFETY_FACTOR_DEFAULT
    if val < 1.0:
        print(f"WARN: est 安全系数 {val} < 1 → 预检上界低于实测值，闸门更紧（可能误拒真实运行）")
    return val


def nonfinite_sources(est_values: list[tuple[str, float]], est_raw: float, est_cost: float) -> list[str]:
    """返回"使预估花费非有限"的来源名（空列表 = 正常）。

    教训 1.61（2026-09-21 关闭三查·二查 major）：`est_cost_cny: NaN` 会让 `nan > budget` 恒为 False
    → **付费 network 档被静默放行**（修复前实测 `exit=0 status=ok executed=True`）。故 Σ 入口、
    乘积入口都必须挡，不能只挡 CLI/env 两个入口（`budget_from`/`est_factor_from`）。
    抽成纯函数是为了让该守卫本身可被回归断言直接驱动（而不是只能靠端到端 fixture 间接触发）。
    """
    bad = sorted({n for n, v in est_values if not math.isfinite(v)})
    if not math.isfinite(est_raw):
        bad = sorted(set(bad) | {"<Σ est_cost_raw>"})
    if not math.isfinite(est_cost) and not bad:
        bad = ["<Σ est_cost>"]
    return bad


def select(verify_dir: Path, tier: str, only: list[str] | None) -> list[tuple[Path, dict]]:
    try:
        entries = collect(verify_dir)
    except SystemExit as exc:  # 元数据缺失/非法 → fail-closed 且给出可执行提示
        print(f"FAIL: 脚本元数据校验未通过，runner 拒绝启动（fail-closed）：{exc}")
        print("提示：TG-2 规则要求每个 verify 脚本带 VERIFY_META 头部；修复后重跑 `verify_matrix.py derive`。")
        raise SystemExit(2) from exc
    picked = [
        (p, m)
        for p, m in entries
        if m.get("tier") == tier and p.name not in SELF_NAMES and (not only or p.name in only)
    ]
    return sorted(picked, key=lambda pm: pm[0].name)


def run_one(path: Path, meta: dict, timeout_s: int) -> tuple[int, float, list[str]]:
    """跑一个脚本：**逐行实时转发**子进程输出，同时留下末尾若干行（行 34 的判决句判据）
    。

    为什么要抓输出：`rc == 0` 只说明"进程正常退出"，**不能**说明自检真的跑到了末行判决句
    ——删掉一批 `ok()` 之后脚本照样退 0。故这里把每个脚本的**末行判决句**与断言条数留下，
    交给 `verdict_problems()` 判。

    实时性不做妥协：用 `Popen` + 读线程逐行 `print`（`PYTHONUNBUFFERED=1` 
    让子进程不攒块），
    超时仍按原口径（`timeout_s` 秒后 `kill` ⇒ 判 `124`）；只多留最后 `TAIL_KEEP` 行。
    """
    if path.suffix == ".py":
        cmd = [sys.executable, str(path)]
    elif path.suffix == ".mjs":
        cmd = ["node", str(path)]
    else:
        return 127, 0.0, []
    tail: list[str] = []
    lock = threading.Lock()
    t0 = time.perf_counter()

    def _forward(stream) -> None:
        for line in stream:
            with lock:
                tail.append(line)
                if len(tail) > TAIL_KEEP:
                    del tail[0]
            sys.stdout.write(line)
            sys.stdout.flush()

    try:
        proc = subprocess.Popen(
            cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            env={**os.environ, "PYTHONUNBUFFERED": "1"})
    except OSError as exc:
        print(f"  SPAWN-ERROR: {type(exc).__name__}: {exc}")
        return 126, 0.0, []
    reader = threading.Thread(target=_forward, args=(proc.stdout,), daemon=True)
    reader.start()
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        reader.join(timeout=5)
        print(f"  TIMEOUT after {timeout_s}s")
        return 124, round(time.perf_counter() - t0, 2), tail
    reader.join(timeout=5)
    return proc.returncode, round(time.perf_counter() - t0, 2), tail


def main() -> int:
    ap = argparse.ArgumentParser(description="分层验证 runner（TG-5）")
    ap.add_argument("--tier", default="offline", choices=["offline", "gui", "network"])
    ap.add_argument("--budget-cny", dest="budget_cny", type=float, default=None,
                    help="本轮花费上限（CNY）；缺省读 env PAPERQA_NIGHTLY_BUDGET_CNY，再缺省 10")
    ap.add_argument("--est-factor", dest="est_factor", default=None,
                    help="预估安全系数（预检上界 = Σest_cost_cny × 系数）；缺省读 env PAPERQA_EST_SAFETY_FACTOR，再缺省 1.3")
    ap.add_argument("--verify-dir", default=str(ROOT / "verify"))
    ap.add_argument("--scripts", default="", help="只跑这些脚本（逗号分隔文件名）")
    ap.add_argument("--json", default=SUITE_RESULT_REL,
                    help=f"结果 JSON 落盘路径（默认 {SUITE_RESULT_REL}——**总是**会写，不会静默跳过）")
    ap.add_argument("--dry-run", action="store_true", help="只列将执行的脚本与预估花费，不执行")
    args = ap.parse_args()

    verify_dir = Path(args.verify_dir)
    if not verify_dir.is_absolute():
        verify_dir = (ROOT / verify_dir).resolve()
    only = [s.strip() for s in args.scripts.split(",") if s.strip()] or None

    picked = select(verify_dir, args.tier, only)
    est_values = [(p.name, float(m.get("est_cost_cny") or 0)) for p, m in picked]
    est_factor = est_factor_from(args)
    est_raw = round(sum(v for _, v in est_values), 4)
    est_cost = round(est_raw * est_factor, 4)
    budget = budget_from(args)
    started = time.time()
    summary: dict = {
        "tier": args.tier,
        "verify_dir": str(verify_dir),
        "budget_cny": budget,
        "est_cost_cny": est_cost,
        "est_cost_cny_raw": est_raw,
        "est_safety_factor": est_factor,
        "cost_measured_cny": None,
        "cost_status": "not_applicable" if args.tier != "network" else "unknown",
        "started_at": started,
        "scripts": [],
        "status": "unknown",
    }

    print(f"== run_suite tier={args.tier} scripts={len(picked)} est_raw={est_raw} × factor={est_factor} "
          f"→ est_cost={est_cost} CNY budget={budget} CNY ==")
    # F4：**启动即落占位**（status=running）——见 SUITE_RESULT_REL 处的说明。
    # 位置在预算/非有限闸门之前：这两条 fail-closed 路径会各自覆写为 refused_*，语义仍然正确。
    _write_json(args.json, {**summary, "status": "running"})
    if args.tier == "gui":
        print("NOTE: gui 档需要后端 8787 + 前端 5173 已启动（并用 Playwright）；请先确认端口空闲/服务在线，否则本档必然失败。")
    for p, m in picked:
        print(f"  - {p.name} (est {effective_est_seconds(p.name, m)}s"
              f" / {m.get('est_cost_cny')} CNY)")

    # 非有限值守卫（2026-09-21 关闭三查·二查 windows major，教训 1.61）：
    # `est_cost_cny: NaN` 会让 `nan > budget` 恒为 False → **付费 network 档被静默放行**（实测复现）。
    # 反向对照证据：修复前该 fixture 得到 `exit=0 status=ok executed=True`。
    # 关键：**Σ 入口与乘积入口都必须挡**——只挡 CLI/env 两个入口（budget_from / est_factor_from）等于没挡。
    bad = nonfinite_sources(est_values, est_raw, est_cost)
    if bad:
        summary["status"] = "refused_nonfinite_est"
        summary["finished_at"] = time.time()
        print(f"REFUSED: 预估花费含非有限值（{'、'.join(bad)}）→ 拒绝启动（fail-closed）。"
              f"NaN/inf/-inf 会使预算比较恒为 False 从而静默绕过闸门；请修脚本 VERIFY_META.est_cost_cny。")
        _write_json(args.json, summary)
        return REFUSE_EXIT

    if not math.isfinite(est_cost) or est_cost > budget:
        # 三态之"超限"：直接拒绝启动（fail-closed，不降级、不部分执行）
        summary["status"] = "refused_budget"
        summary["finished_at"] = time.time()
        print(f"REFUSED: 预估花费 {est_cost} CNY 超过上限 {budget} CNY → 拒绝启动（fail-closed）。"
              f"如需放行请调高 --budget-cny 或 env PAPERQA_NIGHTLY_BUDGET_CNY。")
        _write_json(args.json, summary)
        return REFUSE_EXIT

    if args.dry_run:
        summary["status"] = "dry_run"
        summary["finished_at"] = time.time()
        print("DRY-RUN: 未执行任何脚本。")
        _write_json(args.json, summary)
        return 0

    failed: list[str] = []
    branch_present = path_in_tree(PROBE_KEY)
    declared = set(declared_verdict_scripts(picked))
    verdict_readings: list[str] = []
    verdict_failed: list[str] = []
    undeclared_printers: list[str] = []
    # 第三态（SKIP，见 `SKIP_EXIT` 上方注释）：skipped = 具名 SKIP 的脚本
    # （既不计 PASS 也不计 FAIL）；skip_mismatch = 末行有具名横幅却 rc≠3 的
    # **两通道矛盾**（不归 skipped，上屏 WARN）。
    skipped: list[dict] = []
    skip_mismatch: list[str] = []
    # Retro ③（2026-09-20）：子脚本把实测用量写成 JSONL 指标文件，suite 据此聚合出真实成本。
    # 复核 round-4 minor：文件在**确定要执行之后**才创建（避免 --dry-run/拒绝启动路径遗留文件）。
    fd, metrics_name = tempfile.mkstemp(prefix="suite_metrics_", suffix=".jsonl")
    os.close(fd)  # 关键：立即关闭句柄，否则子进程继承 fd → unlink 报 WinError 32
    metrics_path = Path(metrics_name)
    os.environ["PAPERQA_SUITE_METRICS"] = str(metrics_path)
    try:
        for p, m in picked:
            # 超时基准按**分支实测**取（见 `BRANCH_EST_OVERRIDES`）：分支无关常量会让
            # 一边低估 110 倍（`TIMEOUT` 假红）或另一边白等十几分钟。
            timeout_s = int(effective_est_seconds(p.name, m) * 4 + 60)
            print(f"--- {p.name} ---", flush=True)
            code, secs, tail = run_one(p, m, timeout_s)
            # 第三态**先判**（纯函数，见 `skip_verdict`）：具名 SKIP 不进 `failed`
            # ——但两通道只满足其一的都**不算**（rc=3 无横幅照旧按失败计；
            # 有横幅却 rc≠3 上屏 WARN）。
            state, detail = skip_verdict(tail, code)
            if state == "skipped":
                entry_verdict = f"skipped[{detail}]"
            elif state == "mismatch":
                entry_verdict = "skip-banner-rc-mismatch"
            else:
                entry_verdict = "ok" if code == 0 else "failed"
            summary["scripts"].append({"name": p.name, "exit": code, "seconds": secs,
                                       "verdict": entry_verdict})
            print(f"--- {p.name}: exit={code} ({secs}s) ---", flush=True)
            if state == "skipped":
                skipped.append({"name": p.name, "category": detail, "exit": code})
                print(f"  SKIPPED: {p.name}[{detail}] —— 具名 SKIP"
                      f"（rc={SKIP_EXIT} ＋ 末行判决行「{SKIP_NOT_PASS_MARK}」"
                      f"**同口径**）：不计 PASS 也不计 FAIL；"
                      f"套件末行与 rc 会如实说出「有判据未执行」")
            elif state == "mismatch":
                skip_mismatch.append(p.name)
                print(f"  WARN: {p.name} {detail} ⇒ **不**归入 skipped"
                      f"（两通道必须同时说「不是通过」才认第三态）；本条按原有判据处置")
            if code != 0 and state != "skipped":
                failed.append(p.name)
            # 行 34：只对**自陈**『条数见末行』的脚本判判决句与条数棘轮（其余脚本的
            # 判决句形态不在本条射程内，见 `BRANCH_ASSERTION_FLOORS` 上方注释）。
            if p.name in declared:
                floor_txt = BRANCH_ASSERTION_FLOORS.get((p.name, branch_present),
                                                        "未登记")
                if state == "skipped":
                    # 具名 SKIP：判据根本没执行 ⇒ 条数棘轮无从判（判据①/②在非零退出上
                    # 本就短路）。这里显式记账：读的人看到的是"没跑"，不是"跑过且通过"。
                    verdict_readings.append(
                        f"{p.name}：（具名 SKIP[{detail}]，判据未执行）"
                        f"｜本分支下限 {floor_txt}"
                        f" ⇒ 不计 PASS/FAIL（见末行 skipped 档）")
                else:
                    vp = verdict_problems(p.name, tail, code, branch_present)
                    got = next((ln.strip()
                                for ln in reversed(tail[-VERDICT_TAIL_LINES:])
                                if VERDICT_LINE_RE.match(ln.strip())
                                or VERDICT_EVIDENCE_RE.match(ln.strip())),
                               "（无判决句）")
                    verdict_readings.append(f"{p.name}：{got}｜本分支下限 {floor_txt}")
                    if vp:
                        verdict_failed.append(p.name)
                        failed.append(f"{p.name}（行34）")
                        for prob in vp:
                            print(f"  VERDICT-FAIL: {prob}")
            elif any(VERDICT_LINE_RE.match(ln.strip())
                     or VERDICT_EVIDENCE_RE.match(ln.strip())
                     for ln in tail):
                # 打印了判决句却没自陈 ⇒ 未纳入条数棘轮。**上屏可见**（不判红：
                # 纳入棘轮要
                # 先给两侧实测下限，那是逐脚本的登记工作，本批只登记自陈的那 5 个）。
                undeclared_printers.append(p.name)

        metrics = _read_metrics(metrics_path)
    finally:
        # 复核 round-4 minor：环境变量必须清理，否则会泄漏到同进程的后续非套件运行
        os.environ.pop("PAPERQA_SUITE_METRICS", None)
        try:
            metrics_path.unlink(missing_ok=True)
        except OSError:
            pass  # 被占用也不影响结论（临时文件，系统会清）

    # 复核 round-4 major：只有**确有调用**（calls>0）且成本可换算的记录才算"已回报实测成本"，
    # 空账（回调尚未落地）不得被当成 measured，否则闸门会从 unknown 误推到 measured 且金额低估。
    measured = [m for m in metrics if isinstance(m.get("cost_cny"), (int, float)) and int(m.get("calls") or 0) > 0]
    unpriced = sorted({u for m in metrics for u in (m.get("unpriced_models") or [])})
    no_data = sorted({m.get("script") for m in metrics if not int(m.get("calls") or 0)})
    executed = [s["name"] for s in summary["scripts"]]
    summary["metrics"] = metrics
    summary["cost_measured_cny"] = round(sum(float(m["cost_cny"]) for m in measured), 6) if measured else None
    summary["cost_unpriced_models"] = unpriced
    summary["cost_no_data_scripts"] = no_data
    if args.tier == "network":
        # 三态之"未测量"：只有**所有被执行脚本**都给出可换算成本才转 measured；否则保持 unknown（不臆测）
        summary["cost_status"] = (
            "measured" if executed and set(executed) <= {m.get("script") for m in measured} else "unknown"
        )

    summary["finished_at"] = time.time()
    # 行 34 判据④（自陈脚本数棘轮）只对 offline 档判：Declared 集合是 offline 档的
    # 5 个脚本（gui/network 档不选它们 ⇒ 比较两个不同的清单没有意义）。
    if args.tier == "offline":
        print(f"\n== 行 34 判决句／条数棘轮（分支判据 `{PROBE_KEY}` "
              f"在树里={branch_present}）==")
        for line in verdict_readings:
            print(f"  {line}")
        print(f"  自陈『条数见末行』的脚本 {len(declared)} 个")
        if undeclared_printers:
            print(f"  WARN（可见缺口，**本批不判红**）："
                  f"{len(undeclared_printers)} 个脚本打印了判决句但未在 "
                  f"`VERIFY_META.features` 里自陈条数 ⇒ 未纳入条数棘轮："
                  f"{', '.join(sorted(undeclared_printers))}")
        if skip_mismatch:
            print(f"  WARN（可见缺口，**本批不判红**）：{len(skip_mismatch)} 个脚本"
                  f"末行是具名 SKIP 横幅却 rc≠{SKIP_EXIT}"
                  f"（两通道矛盾：判决行说『{SKIP_NOT_PASS_MARK}』、退出码说成功）"
                  f"⇒ **不**归入 skipped：{', '.join(sorted(skip_mismatch))}"
                  f"——改判要动那些脚本的退出码，属另一批")
        if skipped:
            print(f"  具名 SKIP（第三态，既不计 PASS 也不计 FAIL）："
                  f"{skipped_badge(skipped)}"
                  f" ⇒ 套件 rc={SKIP_EXIT}（无失败，但有判据未执行）")
        # 判据④（自陈脚本数棘轮）**只对仓库自己的 `verify/` 目录**判：`--verify-dir`
        # 指向
        # fixture（`verify_runner.py` 的自检就是这么跑的）时脚本集是造的，"本分支应有 5
        # 个
        # 自陈脚本"在那里没有意义——按 fixture 判会造出假红。
        if verify_dir.resolve() == (ROOT / "verify").resolve():
            _scope_min = BRANCH_VERDICT_SCOPE_MIN.get(branch_present)
            print(f"  自陈脚本数下限（本分支）＝{_scope_min} 个")
            for prob in verdict_scope_problems(len(declared), branch_present):
                print(f"  VERDICT-FAIL: {prob}")
                failed.append("（行34 自陈脚本数棘轮）")
        else:
            print(f"  NOTE: `--verify-dir`＝{verify_dir}（非仓库 `verify/`）"
                  f"⇒ 自陈脚本数棘轮不判（fixture 的脚本集是造的；"
                  f"逐脚本的判决句／条数判据照常）")
    # 三态（`status` 也是三值：ok / failed / skipped）——skipped **不得**写成 ok，
    # 否则 summary 这一通道又会说"全绿"（末行已经说过"本档不是通过"）。
    summary["status"] = "failed" if failed else ("skipped" if skipped else "ok")
    summary["failed_scripts"] = failed
    summary["skipped_scripts"] = [e["name"] for e in skipped]
    summary["skipped"] = skipped
    summary["skipped_badge"] = skipped_badge(skipped)
    summary["skip_banner_rc_mismatch"] = sorted(skip_mismatch)
    summary["verdict_floor_branch_present"] = branch_present
    summary["verdict_readings"] = verdict_readings
    summary["verdict_failed"] = verdict_failed
    _write_json(args.json, summary)

    if args.tier == "network":
        print(f"MEASURED: cost={summary['cost_measured_cny']} CNY status={summary['cost_status']} "
              f"scripts_reporting={len(measured)}/{len(executed)} unpriced={unpriced}"
              + (f" no_data={no_data}" if no_data else ""))
        if summary["cost_status"] == "measured":
            print(f"NOTE: network 档**实测**花费 {summary['cost_measured_cny']} CNY（token 实测 + 本地价表换算）；"
                  "`scheduled-tasks.py` 会自动回填该值（无需人工 --record-cost）。")
        else:
            print("NOTE: network 档成本未测量完整（脚本缺用量回报或价表缺单价）→ cost_status=unknown；"
                  "未回填时下一轮夜间套件仍拒绝放行（三态闸门）。"
                  + (f" 缺价模型：{unpriced}" if unpriced else ""))
    # 判决句**永远最后一行**（`suite_verdict_line` 是它的单一真源）：三态各说各的，
    # 谁都不许借"有跳过"把失败说轻，也不许借"没失败"把跳过说成通过。
    print(f"\n{suite_verdict_line(len(picked), failed, skipped)}")
    if failed:
        return 1
    if skipped:
        # 第三态：**没有失败，但有判据未执行** ⇒ 3（不得取 0——取 0 就是"SKIP 冒充通过"；
        # 与 `verify_agentops.py::SKIP_EXIT` / `spend-report --check` 同码）。
        return SKIP_EXIT
    return 0


def _read_metrics(path: Path) -> list[dict]:
    """读子脚本写的用量指标行（JSONL；Retro ③）。文件不存在/坏行 → 跳过，不抛。"""
    out: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    except OSError:
        pass
    return out


def _write_json(path_str: str, data: dict) -> None:
    """把结果 JSON **原子落盘**（先写 `.tmp` 再 `os.replace`）。

    **不再有"静默跳过"分支**（F4，2026-09-25）：旧实现在 `path_str` 为空时直接 `return`，
    而 `--json` 的默认值就是空串 ⇒ 默认跑法**不刷新** `verify/suite_result.json`，
    盘上那份旧结果看起来仍像最新结果（`scheduled-tasks` 靠 `finished_at ≥ t0` 才没被它骗到，
    但读文件的人会）。现默认路径 = `SUITE_RESULT_REL`；即使调用方显式传空串，
    也落到默认路径而不是什么都不写——"以为写了其实没写"正是要消灭的形态。
    """
    p = Path(path_str.strip() or SUITE_RESULT_REL)
    if not p.is_absolute():
        p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)
    print(f"summary → {p}（status={data.get('status')}）")


if __name__ == "__main__":
    sys.exit(main())
