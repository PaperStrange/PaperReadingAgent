#!/usr/bin/env python3
"""A-PTR 稳定锚点解析器：`path#<锚文本>` -> 当前行号（零依赖，fail-closed）。

## 为什么需要它

`docs/6-DECISIONS.md` 的指针此前一律写成 `path:line`——**内容身份被绑在行号
上**：任何一次向被指文档插入内容，其后的指针全体顶偏（2026-11-10 一天内实测
3 次返工：`quotes_drift` 10->12、`A-230/A-231` 顶偏、§9.1 五处顶偏）。本工具
把"指向哪里"从**行号**改成**文本锚**：只要被指的那一行/那个标题还在，插入
多少行都不漂。

## 语法（规范正文见 `A-PTR.md` 的"设计"节）

    path#<锚文本>          锚文本取**标题行**或**唯一行首片段**
    path#<锚文本>+N/-N     相对锚点的第 N 行（默认 0；不鼓励，见设计节）

`<` `>` 是**语法的一部分**，不是占位符：它让指针在散文/表格/Shell 参数里自带
左右边界，不必依赖反引号或"锚文本不许含空格"这类隐式约定。

## 解析规则

1. 围栏（``` / ~~~）内是示例区，**不参与**锚点匹配（与登记册判据 8 同口径；
   行号按物理行算，不漂）；
2. 规范化 = 去 `**`、去反引号、去全部空白（含 U+3000）、去行首 `>` 引用符、
   去列表序号（`1.` / `-` / `*` / `+`）；
3. 一行命中 = 标题文本**以锚文本开头**，或该行正文**以锚文本开头**；
4. 命中数**必须恰好 1**：0 命中 / 多命中一律 **fail-closed** —— 多命中时把
   全部候选行号与首行摘要**点名**列出，要求收窄锚文本；"解析不出来就放过"
   会让锚点退化成装饰。

## 用法

    python scripts/anchor-resolve.py 'docs/1-WORKFLOW.MD#<交互类检查的反向对照规则>'
    python scripts/anchor-resolve.py --json 'a.md#<x>' 'b.md#<y>'
    python scripts/anchor-resolve.py --root <dir> 'rel.md#<x>'  # 夹具/异物根

`--root` 默认 = 仓库根（本文件的上两级目录）。本工具**只读**，不写任何文件。

rc: 0=全部解析成功 / 1=有 0 命中或多命中（fail-closed）/ 2=用法或语法错误。
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent

# `path#<锚文本>[+N]`：`<>` 是定界符，锚文本内不得再含 `<>`（否则边界不唯一）
POINTER_RE = re.compile(
    r"^(?P<path>[^#\s<>]+)#<(?P<anchor>[^<>]+)>(?P<offset>[+-]\d+)?$")
HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.*)$")
BULLET_RE = re.compile(r"^(?:\d+[.)]|[-*+])\s+")
FENCE_RE = re.compile(r"^\s{0,3}(?P<mark>`{3,}|~{3,})")
QUOTE_RE = re.compile(r"^>+\s*")
WIDE = "WF"


def display_width(text: str) -> int:
    """显示宽度：东亚宽字符（CJK/全角标点）计 2，其余计 1。"""
    return sum(2 if unicodedata.east_asian_width(c) in WIDE else 1 for c in text)


def preview(text: str, limit: int = 60) -> str:
    """按**显示宽度**截断（按字符数截会让 CJK 行宽度翻倍）。"""
    out = ""
    used = 0
    for ch in text:
        step = 2 if unicodedata.east_asian_width(ch) in WIDE else 1
        if used + step > limit:
            return out + "…"
        out += ch
        used += step
    return out


def norm(text: str) -> str:
    """锚点归一：去 `**`、反引号、全部空白（含 U+3000）。"""
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"[\s\u3000]+", "", text)


def visible_lines(lines: list[str]) -> dict[int, str]:
    """剥围栏：返回 `{物理行号: 文本}`，围栏内的行**不在**映射里。

    未闭合的围栏按"其后全部不可寻址"处理（fail-closed：锚点不会落在示例区
    里，与登记册判据 8 的围栏口径一致）。
    """
    out: dict[int, str] = {}
    mark = ""
    for idx, line in enumerate(lines, 1):
        found = FENCE_RE.match(line)
        if found:
            if not mark:
                mark = found.group("mark")[0]
            elif found.group("mark")[0] == mark:
                mark = ""
            continue
        if mark:
            continue
        out[idx] = line
    return out


def match_kind(line: str, want: str) -> str:
    """该行是否以锚文本开头：返回 `heading` / `line` / 空串。"""
    text = QUOTE_RE.sub("", line).strip()
    if not text:
        return ""
    head = HEADING_RE.match(text)
    if head:
        title = norm(head.group("text").rstrip("#").strip())
        return "heading" if title.startswith(want) else ""
    body = norm(BULLET_RE.sub("", text))
    return "line" if body.startswith(want) else ""


def _fail(pointer: str, reason: str, detail: str, **extra) -> dict:
    """构造失败结果（`--json` 与人类可读共用同一形状，故字段齐备）。"""
    result = {"pointer": pointer, "status": reason, "path": "", "anchor": "",
              "offset": 0, "line": None, "kind": "", "text": "", "detail": detail}
    result.update(extra)
    return result


def resolve(root: Path, pointer: str) -> dict:
    """解析一条 `path#<锚文本>[+N]` → 结果 dict（status/line/kind/text）。"""
    m = POINTER_RE.match(pointer.strip())
    if not m:
        return _fail(pointer, "syntax",
                     "语法错误：应为 `path#<锚文本>[+N]`（`<>` 是定界符，"
                     "锚文本内不得含 `<>`）")
    rel = m.group("path")
    anchor = norm(m.group("anchor"))
    offset = int(m.group("offset") or 0)
    base = {"path": rel, "anchor": anchor, "offset": offset}
    if not anchor:
        return _fail(pointer, "syntax", "锚文本规范化后为空（只有空白/强调符）",
                     **base)
    if Path(rel).is_absolute() or ".." in Path(rel).parts:
        return _fail(pointer, "syntax",
                     f"路径 `{rel}` 必须是仓库根下的相对路径（不许绝对路径或 `..`）",
                     **base)
    target = root / rel
    if not target.is_file():
        return _fail(pointer, "no-file", f"目标文件不存在：`{rel}`", **base)
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    visible = visible_lines(lines)
    hits: list[tuple[int, str]] = []
    for no, text in sorted(visible.items()):
        kind = match_kind(text, anchor)
        if kind:
            hits.append((no, kind))
    if not hits:
        return _fail(pointer, "not-found",
                     f"0 命中：`{rel}` 里没有以锚文本开头的标题或行 —— 锚文本 "
                     f"{preview(m.group('anchor'), 40)!r}；要么锚文本写错、要么被指"
                     f"的段落已被改写或删除（fail-closed，不得当未核放行）",
                     **base)
    if len(hits) > 1:
        named = "；".join(f":{no} {preview(visible[no].strip(), 34)}"
                         for no, _k in hits[:6])
        more = f"（另有 {len(hits) - 6} 处未列出）" if len(hits) > 6 else ""
        return _fail(pointer, "ambiguous",
                     f"{len(hits)} 处命中（多义 ⇒ fail-closed，必须收窄锚文本）："
                     f"{named}{more}", candidates=[no for no, _k in hits], **base)
    at, kind = hits[0]
    line = at + offset
    if line not in visible:
        return _fail(pointer, "offset",
                     f"偏移越界：锚点 :{at} {offset:+d} => :{line} 不在可寻址行内"
                     f"（该文件 {len(lines)} 行；围栏行与越界行都不可寻址）", **base)
    return {"pointer": pointer, "status": "ok", "path": rel, "anchor": anchor,
            "offset": offset, "line": line, "kind": kind,
            "text": preview(visible[line].strip(), 70), "detail": ""}


def report(result: dict) -> str:
    """人类可读一行：成功给 `path:line` + 该行摘要；失败给点名原因。"""
    if result["status"] == "ok":
        return (f"OK   {result['pointer']} -> {result['path']}:{result['line']}"
                f"  ({result['kind']})  {result['text']}")
    return f"FAIL {result['pointer']}  [{result['status']}]  {result['detail']}"


def main(argv: list[str]) -> int:
    """CLI 入口：解析全部指针，打印人类可读摘要或 `--json`，返回 rc。"""
    as_json = "--json" in argv
    args = [a for a in argv if a != "--json"]
    root = DEFAULT_ROOT
    if "--root" in args:
        idx = args.index("--root")
        if idx + 1 >= len(args):
            print("用法错误：--root 需要一个目录参数", file=sys.stderr)
            return 2
        root = Path(args[idx + 1]).resolve()
        args = args[:idx] + args[idx + 2:]
    if not args:
        print("用法：anchor-resolve.py [--json] [--root DIR] 'path#<锚文本>' ...",
              file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"用法错误：--root 不是目录：{root}", file=sys.stderr)
        return 2
    results = [resolve(root, ptr) for ptr in args]
    bad = sum(1 for r in results if r["status"] != "ok")
    if as_json:
        payload = {"root": root.as_posix(), "ok": bad == 0,
                   "counts": {"ok": len(results) - bad, "failed": bad},
                   "results": results}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(report(result))
        print(f"合计 {len(results)} 条：解析成功 {len(results) - bad}、失败 {bad}"
              f"（失败即 fail-closed，不许当成『未核』放行）")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
