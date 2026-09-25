#!/usr/bin/env python3
"""Markdown 表格结构自检（TG-15 三次 R1 事故后固化）。

背景与教训（2026-09-23，Sprint-17 D2 实测）：本日三次"内容/结构被吞"全部发生在**编辑 Markdown 表格**
时——`edit` 的 `old_string` 跨到相邻单元格或下一节标题就会把边界吃掉，而肉眼很难发现。
本脚本把当时的临时检查固化为可复用命令。

判定：
  ① 单元格数一致性——在**未转义**的 `|` 处切分（`\\|` 是转义，属于内容），比对该表块的众数；
  ② **（2026-09-25 删除——原判据是恒真式，D2/D3 审核 R5）**：原文写
     `unescaped = raw - escaped` 再判 `raw != unescaped + escaped`，即 `raw != raw` ⇒ **分支不可达**，
     恒不成立。故"两条判据"实际只有一条（R5 的判定）。它想表达的"某行有**单元格内裸管道**"
     **已由 ① 完整覆盖**：裸 `|` 会让 `split_row` 在该处多切一格 ⇒ 该行单元格数 ≠ 该表众数 ⇒ ① 报错。
     删除必须**可证**，故本模块自带 `reverse_control()`（由 `main()` 无条件执行）：裸管道坏样本必须报错、
     `\\|` 好样本必须放行。留一条恒真的"判据"只会让 PASS 的语义虚高（读代码的人以为有两道防线）。
  ③ 只能报，不能自动改：本脚本**不修改文件**（--check 语义），修法由人决定。
  ④ **扫描集双向差集**（A10 / 审核 N1）：扫描集由政策声明（`md_table_coverage.roots` +
     `include_files`）与文件系统双向核对，打印"应扫 N / 实扫 M"并要求相等。

    为什么必须双向（N1 实测）：原先扫描集只有 4 条**窄 glob**（`docs/iteration/phases/*/backlog.MD`
    这类），于是**阶段级 `.MD`**（`architecture.MD`/`README.MD`/`ROADMAP.MD`/带日期的分析文档）
    以及 `pre-research/**` 一个都不扫 —— 相关集 **160**、实扫 **131**、**漏 29**，
    而这 29 份里今天就藏着 **7 处真实表格缺陷**，闸门却打印 `MD-TABLE PASS`。
    "漏扫"比"漏报"更危险：它让 PASS 的含义从"检查过且没问题"退化成"没检查"。
    现判据三条：① 政策里每个显式路径必须存在（缺失 fail-closed）；② 每条 glob 必须至少命中 1 个文件
    （死 glob fail-closed）；③ 应扫集与实扫集必须相等（差集逐条点名）。
    `roots` 是**独立声明**的（不是从 glob 推导），所以"删掉一棵树的 glob"也会被差集抓到。

用法：
    .venv\\Scripts\\python.exe verify/verify_md_tables.py [文件 …]      # 默认检查项目主文档集
    .venv\\Scripts\\python.exe verify/verify_md_tables.py docs/1-WORKFLOW.MD --quiet

退出码：0 = 全部通过；1 = 发现问题（并逐条给出 file:line 与建议）。
"""

from __future__ import annotations
VERIFY_META = {'features': 'Markdown 表格结构自检：未转义管道切分的单元格数一致性（② 恒真式判据已删，裸管道由 ① 覆盖，脚本内建坏/好样本反向对照）+ 扫描集双向差集 + 棘轮上限；三次 R1 事故后固化的编辑安全网', 'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 2, 'routes': [], 'requires': ['none']}

import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import PolicyError, load_policy  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PIPE = "|"
ESC = "\\"


def split_row(line: str) -> list[str]:
    """按**未转义**管道切分（`\\|` 视为内容），返回单元格。

    ⚠️ 2026-09-23 实测踩坑（本函数的第一版是错的，值得写在这里）：
    第一版切分后把"首尾空段"全部丢弃 —— 于是 `| a | b |  |  |`（**真实的空单元格**）
    被当成 2 格而不是 4 格，导致：① 正确的行被判为"列数不符"；② 我据此"补格"反而把
    备份库的 TG-1~TG-6 行改成了 8 格。**空单元格是内容，不是分隔符**。
    正确做法：行以 `|` 开头/结尾时，只丢弃**最外层管道产生的那个空段**（首段、末段各一个），
    中间的空段一律保留。
    """
    cells, cur = [], []
    for i, ch in enumerate(line):
        if ch == PIPE and (i == 0 or line[i - 1] != ESC):
            cells.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    cells.append("".join(cur))
    # 去掉最外层管道造成的空段（仅当它不是内容时——行首/行尾的管道不可能是内容）
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return [c.strip() for c in cells]


def reverse_control(quiet: bool = False) -> list[str]:
    """② 删除后的**反向对照**（`TG-6` ⑤"倒过来试"）：证明"裸管道"确实由 ① 抓住。

    删除 ② 的前提是"① 已覆盖"。这句话必须**可执行**，否则删掉一条恒真判据就退化成
    "少了一道防线"的口头承诺（正是本轮审核在别处抓到的形态）。两个样本：
      * 坏样本：单元格内**未转义**的 `|` → 该行被多切一格 → ① 必须报错；
      * 好样本：同一处写成 `\\|`（转义）→ 必须零 problem（防"① 因切分器对转义处理不当而误报"）。
    """
    bad = "| a | b | c |\n|---|---|---|\n| 1 | x|y | 3 |\n"
    good = "| a | b | c |\n|---|---|---|\n| 1 | x\\|y | 3 |\n"
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        for name, body, want in (("bad.md", bad, True), ("good.md", good, False)):
            probe = Path(td) / name
            probe.write_text(body, encoding="utf-8")
            found = check_file(probe, quiet=True)
            if (len(found) > 0) is not want:
                problems.append(f"反向对照 {name}：期望{'报错' if want else '放行'}，实测 {found}")
            elif not quiet:
                print(f"  PASS: 反向对照 {name} → {'报错（裸管道被 ① 抓住）' if want else '放行（转义管道不误报）'}")
    return problems


def check_file(path: Path, quiet: bool = False) -> list[str]:
    problems: list[str] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    blocks: list[list[tuple[int, str]]] = []
    cur: list[tuple[int, str]] = []
    for i, ln in enumerate(lines, 1):
        if ln.strip().startswith(PIPE):
            cur.append((i, ln))
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)

    for block in blocks:
        counts = Counter(len(split_row(ln)) for _, ln in block)
        if len(counts) > 1:
            mode, _ = counts.most_common(1)[0]
            for i, ln in block:
                n = len(split_row(ln))
                if n != mode:
                    problems.append(
                        f"{path}:{i} 单元格数 {n} ≠ 该表众数 {mode}（表头 {block[0][0]} 行）"
                        f"｜多半是**未转义管道**把行切多了，或行尾少了分隔符")
    # ② 已于 2026-09-25 删除（R5 判定它是恒真式）：原写法 `unescaped = raw - escaped` 后自比
    # `raw == unescaped + escaped` 恒为真、分支不可达；它想表达的"单元格内有**未转义**管道"
    # 由 ① 覆盖（裸管道多切一格 ⇒ 该行单元格数 ≠ 该表众数）。反向对照见 `reverse_control()`，
    # 由 `main()` 无条件执行——"① 已覆盖"必须是**可执行断言**，不是删除时的一句口头承诺。
    if not quiet:
        print(f"  {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: "
              f"表格块 {len(blocks)}，问题 {len([p for p in problems if str(path) in p])}")
    return problems


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def coverage_problems(policy) -> tuple[list[str], list[str], list[str]]:
    """扫描集 ↔ 文件系统**双向差集**（A10 / 审核 finding N1）。返回 `(应扫, 实扫, problems)`。

    * **应扫**（expected）= `md_table_coverage.roots` 递归下的全部 `.md`/`.MD`（大小写都算，
      与平台无关：判据用 `suffix.lower()`，不依赖 Windows 的大小写不敏感 glob）
      ∪ `include_files`（目录之外的单个文件，必须存在）。
    * **实扫**（actual）= `md_table_docs`（每条必须存在）∪ `md_table_globs` 展开（每条必须 ≥1 命中）。

    为什么 `roots` 必须是**独立声明**而不是"从 glob 反推目录"：从 glob 反推是恒真式——
    删掉一条 glob 会连带缩小它声明的范围，于是"少扫一整棵树"永远看不出来。独立声明后，
    两侧任一方缺失都会落进差集并被逐条点名（这正是 N1：政策 4 条窄 glob vs 相关集 160）。
    """
    cov = policy.policy_file.get("md_table_coverage")
    if not isinstance(cov, dict):
        raise PolicyError("agents/policy.json 缺 md_table_coverage（扫描集范围声明；缺它则"
                          "'应扫/实扫'无从核对 → fail-closed）")
    roots = [str(p) for p in (cov.get("roots") or [])]
    include = [str(p) for p in (cov.get("include_files") or [])]
    docs = [str(p) for p in (policy.policy_file.get("md_table_docs") or [])]
    globs = [str(p) for p in (policy.policy_file.get("md_table_globs") or [])]
    problems: list[str] = []
    if not roots:
        problems.append("[覆盖声明] md_table_coverage.roots 为空 → 应扫集无从计算（fail-closed）")

    expected: set[str] = set()
    for rel in include:
        if not (ROOT / rel).is_file():
            problems.append(f"[覆盖声明] md_table_coverage.include_files 里的 {rel!r} 不存在（fail-closed）")
        expected.add(rel)
    for root in roots:
        base = ROOT / root
        if not base.is_dir():
            problems.append(f"[覆盖声明] md_table_coverage.roots 里的目录不存在：{root!r}（fail-closed）")
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() == ".md":
                expected.add(_rel(p))

    actual: set[str] = set()
    for rel in docs:
        if not (ROOT / rel).is_file():
            problems.append(f"[显式文档] {rel!r} 不存在：政策里点名的路径必须真实存在（缺失即 fail-closed，"
                            f"不静默跳过）")
            continue
        actual.add(rel)
    for pattern in globs:
        hits = {_rel(p) for p in ROOT.glob(pattern) if p.is_file()}
        if not hits:
            problems.append(f"[死 glob] {pattern!r} 命中 0 个文件：留着它 = 让人以为扫了、其实没扫"
                            f"（删掉或写对，不要留死数据）")
        actual |= hits

    for rel in sorted(expected - actual):
        problems.append(f"[应扫未扫] {rel}：在覆盖声明范围内，但没有任何 md_table_docs/md_table_globs "
                        f"覆盖它 → 闸门**根本不检查它**（N1 形态：漏 29/160）")
    for rel in sorted(actual - expected):
        problems.append(f"[实扫超出声明] {rel}：被政策扫到，但不在 md_table_coverage 声明范围内"
                        f" → 要么补进 roots/include_files，要么把它移出扫描集（声明与行为必须一致）")
    return sorted(expected), sorted(actual), problems


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    policy = load_policy()
    cov_problems: list[str] = []
    if args:
        targets = [Path(a) for a in args]
        expected_n = actual_n = None
    else:
        expected, actual, cov_problems = coverage_problems(policy)
        expected_n, actual_n = len(expected), len(actual)
        targets = [ROOT / rel for rel in actual]
    # 空集 ≠ PASS（N8 的同族，与 `verify_close_readiness` 的"空区间 ≠ 通过"同一判据）：
    # 显式路径全部不存在时旧实现逐条 SKIP 后打印 `MD-TABLE PASS（0 个文件）`——
    # 一个"什么都没查"的绿。这里把它变成 FAIL（fail-closed），并点名请求过的路径。
    missing = [] if not args else [str(p) for p in targets if not p.is_file()]
    # A2（M-a/N2/R3）：棘轮 = `{路径: 缺陷数上限}`，不是路径白名单。
    legacy_caps = {str((ROOT / f).resolve()): cap for f, cap in policy.md_table_legacy_files.items()}
    review_by = policy.md_table_review_by
    today = str(date.today())

    all_problems: list[str] = list(cov_problems)
    baselined: list[str] = []
    baseline_files_scanned: set[str] = set()
    print("Markdown 表格结构自检（未转义管道切分的单元格数一致性）：")
    rc_problems = reverse_control(quiet)
    if rc_problems:
        print(f"\nMD-TABLE FAIL（{len(rc_problems)} 项反向对照失效：判据与实际行为不符，"
              f"先修判据再看真数据）:")
        for item in rc_problems:
            print(f"  - {item}")
        return 1
    if expected_n is not None:
        same = expected_n == actual_n and not cov_problems
        print(f"  扫描集双向差集：应扫 {expected_n} / 实扫 {actual_n} → "
              f"{'一致' if same else '**不一致（fail-closed，逐条点名见下）**'}"
              f"（roots={list((policy.policy_file.get('md_table_coverage') or {}).get('roots') or [])}）")
    print(f"  棘轮基线：{len(legacy_caps)} 个文件（按文件设缺陷上限）；review_by={review_by}，"
          f"今日={today} → {'**已过期**' if today > review_by else '未到期'}")
    scanned = 0
    for path in targets:
        if not path.is_file():
            print(f"  SKIP（不存在）: {path}")
            continue
        scanned += 1
        found = check_file(path, quiet)
        cap = legacy_caps.get(str(path.resolve()))
        if cap is not None:
            # 棘轮（ratchet）：历史文件的既存缺陷**不必清零**，但**只许变紧**——
            # `len(found) > cap` 即 FAIL。定义域仍是"政策里点名的那些文件"（路径比较语义保留）：
            # 基线之外的任何文件，缺陷一律进 all_problems（新文件/新改动一律判失败）。
            baseline_files_scanned.add(str(path))
            if len(found) > cap:
                # 超出上限 → 该文件的缺陷**全部**进 FAIL 清单（点名具体行，便于逐处修）
                all_problems += found
                if not quiet:
                    print(f"    [baseline] 上限 {cap}，实测 {len(found)} → **超出上限，判失败**")
            else:
                baselined += found
                if not quiet:
                    print(f"    [baseline] 实测 {len(found)} <= 上限 {cap}（历史既存缺陷，只报不判失败）")
        else:
            all_problems += found

    if baselined:
        base_files = sorted({p.rsplit(":", 1)[0] for p in baselined})
        print(f"\n棘轮基线（历史文件，上限内不判失败）：{len(baselined)} 处，涉及 {len(base_files)} 个文件")

    if scanned == 0:
        print(f"\nMD-TABLE FAIL：本次**一个文件都没解析**（请求 {len(targets)} 个，全部不存在）"
              f"——『什么都没查』不是通过（N8：空集/缺失 = PASS 的失效形态）。"
              f"请求过的路径：{missing[:5]}")
        return 1

    # 到期日：过期 = 基线失效 → FAIL（提示"必须重评基线"）
    if today > review_by:
        print(f"\nMD-TABLE FAIL：棘轮基线已过期（review_by={review_by}，今日={today}）"
              f"——**必须重评基线**：逐处复核历史缺陷是否仍成立、上限是否可下调，并更新 "
              f"agents/policy.json::md_table_legacy_files.review_by（不得静默延期）。")
        return 1

    if all_problems:
        print(f"\nMD-TABLE FAIL（{len(all_problems)} 项，非基线文件或超出上限的基线文件）：")
        for p in all_problems:
            print(f"  - {p}")
        print("\n修法：① 内容里的 `|` 加反斜杠转义（`\\|`）；② 补齐/删除多余的单元格分隔符；"
              "③ 若行数属**表头与数据行列数不同**（如标题行少一列），改分隔行 `|---|...|` 与表头对齐。")
        return 1
    # 注：基线文件数按**本次实际扫描到的**计（首版打印的是政策里的总数，跑子集时会误导；
    # 又：首版把 15 个问题串当 15 个文件打印——见 N8 的计数口径问题）。
    # A10 起 `scanned` 是**真正解析过的文件数**（不是请求数）：政策模式下它与"实扫"同源，
    # 于是"应扫 N / 实扫 M"与 PASS 行不会各说一套。
    print(f"\nMD-TABLE PASS（{scanned} 个文件解析通过；其中 {len(baseline_files_scanned)} 个历史文件"
          f"走棘轮基线、均在各自的 defect 上限内）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
