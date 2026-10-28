"""R1 共享闸门基座：断言计数 / 通过判决 / 机读 `EVIDENCE` 行 / 第三态 SKIP。

**只放逐字重复的骨架**（2026-10-28 R1 试点；抽取前先读码确认重复，不设计
没有重复的东西）：

* `ok()` ＋ 计数器：`verify/` 下 **18/41** 个脚本各写一份同形实现
  （`assert cond, f"{name} FAIL: {detail}"` ＋ `PASSED += 1` ＋
  `print(f"PASS: {name} {detail}")`），本批三处试点脚本**逐字相同**；
* 收尾两行：`ALL PASS (N assertions)`（**23/41** 个脚本有）与
  `EVIDENCE: <脚本名> assertions=N rc=R`——后者是**协议**，不只上屏：
  `run_suite.py::VERDICT_EVIDENCE_RE` 与 `verdict_problems()` 都在解析它，
  23 份各写一遍就会在措辞上漂；
* 第三态 SKIP：`rc=3` ＋ 末行 `<NAME> SKIP[<类别>] … 本档不是通过（rc=3）`
  （`run_suite.py::skip_verdict` 的**两通道**判据：退出码 ＋ 末行横幅，
  缺一不算）。形态**逐字**取自 `verify_spend_report.py`，与另外 3 处现成生产者
  （`verify_agentops.py` / `verify_close_readiness.py` / `verify_usage.py`）同构。

**不放**（那是各闸门的价值，搬进来等于把判据变成框架）：

* 判据逻辑、`argparse`、失败清单：`FAILURES (k/N)：[…]` 形态全仓只有
  `verify_spend_report.py` 一处 ⇒ 属**单点**而非重复，搬它只是位移；
* **policy 读取**：`PAPERQA_AGENT_POLICY` 覆盖语义已经只有一份
  （`verify/agent_policy.py::load_policy`，`policy_path` 那一行即 env 覆盖），
  各脚本只是**调用**它；再包一层就是**新增**第二份实现，与"只搬真重复"相反；
* `-O` 守卫：`agents/policy.json::gate_integrity.guard_line` = `if not __debug__:`，
  `verify_gate_integrity.py` **逐文件**检查该行在位 ⇒ 挪进基座会让迁移过的闸门
  被判"守卫行缺席"。故留在各脚本。

本文件是**库**而非闸门：不写 `VERIFY_META` ⇒ 不进 `TEST-MATRIX.MD`、
不被 `run_suite.py::collect`（只收 `verify_*`/`eval_*`）当作脚本，同
`verify/e2e_common.py` 的既有做法。**不写任何文件** ⇒ 不触发
`verify_artifact_paths.py` 的动态目标棘轮。
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 第三态（SKIP）的协议常量：**唯一真源**。`run_suite.py` 用同一组字面量判
# `<NAME> SKIP[<类别>]…本档不是通过` 与 rc=3；各写一份就会漂（spend-report /
# agentops / close-readiness / usage 四家各存一份，本批只收进第一家的字面量）。
SKIP_EXIT = 3
SKIP_NOT_PASS_MARK = "本档不是通过"

_N = 0                             # 已执行断言数（`ALL PASS (N assertions)` 的 N）
_SKIPPED: list[list[str]] = []     # [类别, 判据名, 未执行原因]


def ok(name: str, cond: bool, detail: str = "") -> None:
    """断言 ＋ 计数 ＋ 打印 `PASS: …`：形态与各闸门现状**逐字一致**。"""
    global _N
    assert cond, f"{name} FAIL: {detail}"
    _N += 1
    print(f"PASS: {name} {detail}")


def skip(category: str, name: str, why: str = "") -> None:
    """记一条具名 SKIP：该判据在本环境**无从执行**（既不计 PASS 也不计 FAIL）。"""
    _SKIPPED.append([category, name, why])


def all_pass(note: str = "") -> None:
    """打印通过横幅 `ALL PASS (N assertions)`（`note` 原样接在其后）。"""
    print(f"\nALL PASS ({_N} assertions){note}")


def evidence(script: str, extra: str = "", rc: int = 0) -> None:
    """打印机读证据行 `EVIDENCE: <script> assertions=N rc=<rc><extra>`。"""
    print(f"EVIDENCE: {script} assertions={_N} rc={rc}{extra}")


def finish(script: str, extra: str = "", *, tag: str = "") -> int:
    """收尾判决（**唯一出口**）：通过 → 0；有具名 SKIP → 3 且末行是横幅。

    SKIP 档三行次序与 `verify_spend_report.py` 逐字同形：
    `ALL PASS (N assertions)（另有 k 条判据未执行）` → `EVIDENCE: … rc=3` →
    `<NAME> SKIP[<类别>] … 本档不是通过（rc=3）`，随后 `return 3`。
    横幅必须是**末行**：`run_suite.py::skip_verdict` 只读输出末行（两通道判据），
    所以这条次序由本函数保证，不交给调用方按约定摆。
    """
    if not _SKIPPED:
        all_pass()
        evidence(script, extra)
        return 0
    cats = "；".join(dict.fromkeys(item[0] for item in _SKIPPED))
    names = "，".join(item[1] for item in _SKIPPED)
    whys = "；".join(item[2] for item in _SKIPPED if item[2]) or "判据未执行"
    all_pass(f"（另有 {len(_SKIPPED)} 条判据未执行）")
    evidence(script, rc=SKIP_EXIT)
    print(f"{tag or script.removesuffix('.py')} SKIP[{cats}] {names}"
          f" —— {whys} ⇒ {SKIP_NOT_PASS_MARK}（rc={SKIP_EXIT}）")
    return SKIP_EXIT
