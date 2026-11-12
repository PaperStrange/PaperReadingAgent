"""A-CASE 反例语料检索入口（零依赖、只读）。

三件事，输出一律带 `文件:行号`，便于人直接跳转：
  --form <F12|G6>  该形态的主案例 ＋ 同形态案例（主案例在前）
  --grep <关键词>   跨两份语料逐行命中：案例标题 ＋ 命中行号
  --list            全部形态、形名与该形态的主案例

解析与判定口径**复用** `verify/verify_case_index.py` 的同一份解析器
（同一真源，避免检索端与闸门端各写一套解析而漂移）。

用法：
  .venv\\Scripts\\python.exe scripts\\case-search.py --form F12
  .venv\\Scripts\\python.exe scripts\\case-search.py --grep 短 sha
  .venv\\Scripts\\python.exe scripts\\case-search.py --list
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.verify_case_index import (
    CARD_REL, CORPUS_RELS, parse_card_forms, parse_headings, _read)


def _load() -> tuple[list, dict[str, str], dict[str, int]]:
    """读卡与两份语料，返回 `(cases, 形名表, 表的主案例列)`。"""
    names, prim, _ = parse_card_forms(_read(ROOT / CARD_REL))
    cases: list = []
    for rel in CORPUS_RELS:
        cases += parse_headings(_read(ROOT / rel), rel)
    return cases, names, prim


def _sort_key(code: str) -> tuple[str, int]:
    """形态码排序键：先 F 后 G，再按数字。"""
    return code[0], int(code[1:])


def _form_view(code: str, cases: list, names: dict[str, str]) -> int:
    """`--form`：主案例在前，同形态案例随后；全部带 `文件:行号`。"""
    group = [c for c in cases if c.code == code]
    if code not in names and not group:
        print(f"未登记的形态码：{code}（--list 看全部）", file=sys.stderr)
        return 2
    print(f"{code} {names.get(code, '（表里没有这个码）')}")
    primaries = [c for c in group if c.marker == "主案例"]
    secondary = [c for c in group if c.marker == "同形态见主案例"]
    if not primaries:
        print("  主案例   （语料里没有）")
    for c in primaries:
        print(f"  主案例   案例 {c.num}  {c.rel}:{c.line}")
    if not secondary:
        print("  同形态   无")
    for i, c in enumerate(secondary):
        label = "同形态   " if i == 0 else "         "
        print(f"  {label} 案例 {c.num}  {c.rel}:{c.line}")
    return 0


def _list_view(cases: list, names: dict[str, str]) -> int:
    """`--list`：每个形态一行底色 ＋ 主案例 `文件:行号`，同形态只报条数。"""
    for code in sorted(names, key=_sort_key):
        group = [c for c in cases if c.code == code]
        primaries = [c for c in group if c.marker == "主案例"]
        n_same = len(group) - len(primaries)
        print(f"{code} {names[code]}")
        if primaries:
            p = primaries[0]
            print(f"    主案例 案例 {p.num}  {p.rel}:{p.line}"
                  f" ｜ 同形态 {n_same} 条")
        else:
            print(f"    主案例 （语料里没有） ｜ 同形态 {n_same} 条")
    return 0


def _grep_view(keyword: str, cases: list) -> int:
    """`--grep`：逐行命中，输出 `文件:行号` ＋ 所属案例标题（含前言）。"""
    needle = keyword.casefold()
    hits = 0
    for rel in CORPUS_RELS:
        text = _read(ROOT / rel)
        own = [c for c in cases if c.rel == rel]
        for i, line in enumerate(text.splitlines(), 1):
            if needle not in line.casefold():
                continue
            hits += 1
            title = "（前言）"
            for c in own:
                if c.line <= i:
                    title = f"案例 {c.num}｜{c.title}"
                else:
                    break
            body = line.strip()
            if len(body) > 90:
                body = body[:90] + "…"
            print(f"{rel}:{i}  {title}  :: {body}")
    if not hits:
        print(f"（无命中：{keyword}）")
        return 1
    print(f"-- 命中 {hits} 行")
    return 0


def main() -> int:
    """CLI 入口：`--form` / `--grep` / `--list` 三选一。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="A-CASE 反例语料检索（只读）")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--form", metavar="CODE", help="形态码，如 F12 / G6")
    group.add_argument("--grep", metavar="KW", help="关键词（跨两份语料）")
    group.add_argument("--list", action="store_true", help="列出全部形态")
    args = ap.parse_args()
    cases, names, _prim = _load()
    if args.list:
        return _list_view(cases, names)
    if args.form:
        return _form_view(args.form.strip().upper(), cases, names)
    return _grep_view(args.grep, cases)


if __name__ == "__main__":
    sys.exit(main())
