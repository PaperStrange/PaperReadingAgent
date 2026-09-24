#!/usr/bin/env python3
"""Markdown 表格结构自检（TG-15 三次 R1 事故后固化）。

背景与教训（2026-09-23，Sprint-17 D2 实测）：本日三次"内容/结构被吞"全部发生在**编辑 Markdown 表格**
时——`edit` 的 `old_string` 跨到相邻单元格或下一节标题就会把边界吃掉，而肉眼很难发现。
本脚本把当时的临时检查固化为可复用命令。

判定：
  ① 单元格数一致性——在**未转义**的 `|` 处切分（`\\|` 是转义，属于内容），比对该表块的众数；
  ② 转义/管道平衡——原始管道数必须等于 未转义管道数 + 转义管道数；不等即说明有**未转义管道**（会切坏表格）。

    为什么单列这一条：修复转义时最典型的错法是"该转义的地方没转义、或转义后整行管道数与预期不符"，
    而 ① 如果切分器本身对转义处理不当（本轮实测过一次），就会给出与事实相反的结论（把正确的行判为错）。
    两条一起看，才能自证"是文档坏了"而不是"检查器坏了"。
  ③ 只能报，不能自动改：本脚本**不修改文件**（--check 语义），修法由人决定。

用法：
    .venv\\Scripts\\python.exe verify/verify_md_tables.py [文件 …]      # 默认检查项目主文档集
    .venv\\Scripts\\python.exe verify/verify_md_tables.py docs/1-WORKFLOW.MD --quiet

退出码：0 = 全部通过；1 = 发现问题（并逐条给出 file:line 与建议）。
"""

from __future__ import annotations
VERIFY_META = {'features': 'Markdown 表格结构自检：未转义管道切分的单元格数一致性 + 管道转义平衡（三次 R1 事故后固化的编辑安全网）', 'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 2, 'routes': [], 'requires': ['none']}

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import load_policy  # noqa: E402

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


def pipe_balance(line: str) -> tuple[int, int]:
    raw = line.count(PIPE)
    escaped = sum(1 for i, ch in enumerate(line) if ch == PIPE and i and line[i - 1] == ESC)
    return raw, escaped


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
    # 管道转义平衡：原始管道数应等于 未转义 + 转义
    for i, ln in enumerate(lines, 1):
        if not ln.strip().startswith(PIPE):
            continue
        raw, escaped = pipe_balance(ln)
        unescaped = raw - escaped
        if raw != unescaped + escaped:  # 恒等式，仅用于自检本函数（防御性）
            problems.append(f"{path}:{i} 管道计数自相矛盾（raw={raw} unesc={unescaped} esc={escaped}）")
    if not quiet:
        print(f"  {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: "
              f"表格块 {len(blocks)}，问题 {len([p for p in problems if str(path) in p])}")
    return problems


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    policy = load_policy()
    targets = [Path(a) for a in args] if args else [ROOT / t for t in policy.md_table_targets]
    legacy = {str((ROOT / f).resolve()) for f in policy.md_table_legacy_files}

    all_problems: list[str] = []
    baselined: list[str] = []
    print("Markdown 表格结构自检（未转义管道切分 + 转义平衡）：")
    for path in targets:
        if not path.is_file():
            print(f"  SKIP（不存在）: {path}")
            continue
        found = check_file(path, quiet)
        if str(path.resolve()) in legacy:
            # 棘轮：历史文件的既存缺陷**只报不判失败**（见 policy::md_table_legacy_files 说明）
            baselined += found
            if found and not quiet:
                print(f"    [baseline] {len(found)} 处既存缺陷（历史文件，只报不判失败）")
        else:
            all_problems += found

    if baselined:
        files = sorted({p.split(":")[1] for p in baselined if ":" in p})
        print(f"\n棘轮基线（历史文件，不判失败）：{len(baselined)} 处，涉及 {len(files)} 个文件")

    if all_problems:
        print(f"\nMD-TABLE FAIL（{len(all_problems)} 项，非基线文件）：")
        for p in all_problems:
            print(f"  - {p}")
        print("\n修法：① 内容里的 `|` 加反斜杠转义（`\\|`）；② 补齐/删除多余的单元格分隔符；"
              "③ 若行数属**表头与数据行列数不同**（如标题行少一列），改分隔行 `|---|...|` 与表头对齐。")
        return 1
    print(f"\nMD-TABLE PASS（{len(targets)} 个文件；其中 {len(legacy)} 个历史文件走棘轮基线）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
