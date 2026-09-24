#!/usr/bin/env python3
"""阶段卡库存实测（TG-14 迁移基线）。

为什么需要它：`TG-14` 卡内写着"全仓 94 张卡（2026-09-23 实测…）"，但那行是**手抄事实**，
卡自己都注明"开/关卡后必须同步——正是 TG-12 要治的形态"。迁移前必须先拿到**命令可复现**的基线，
否则迁移完无法证明"一张卡都没丢"。

判定：卡行 = `phases/<阶段>/backlog.MD` 表格里**首格匹配卡号形态**的行（`TG-1`/`A-M11`/`MM-1`/`F-AC13`…），
并单独统计非卡行（如 `—` 占位、表头、分隔行），把差异说清楚而不是"大概"。

用法：
    python scripts/card-inventory.py                 # 表格式汇总
    python scripts/card-inventory.py --json <path>   # 同时落盘机器可读基线（供迁移前后 diff）
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
PHASES = REPO / "docs" / "iteration" / "phases"

def is_card_id(text: str) -> bool:
    """卡号判定（**按定义写，不靠正则穷举形态**——2026-09-23 实测四轮才收敛）。

    定义：`<字母前缀>-<字母数字主体>` 或 `<字母前缀><数字>`；即
      * 恰好一个连字符时：前缀**全字母**、整体 `prefix_body` 是合法标识符（`A-CLOSE`/`TG-1`/`F-AC13`/`A-PM1`）；
      * 无连字符时：字母前缀 + 纯数字（`F1`/`M18`）。
    排除：`卡号`（表头，前缀后无内容）、`—`/`---`（占位）、`2026-09-21`（前缀是数字）、`R-E3` 由第一条覆盖。
    这个写法比正则更难"漏一类"，且每一条都能对着真实卡号解释。
    """
    if "-" in text:
        prefix, _, body = text.partition("-")
        if text.count("-") != 1 or not prefix.isalpha() or not prefix.isascii():
            return False
        return bool(body) and f"{prefix}_{body}".isidentifier() and body[0].isalnum()
    # 无连字符：**字母前缀 + 其后全是数字**（`F1`/`M18`）。首版写成"只有最后一位是数字"
    # （`text[:-1].isalpha()`），于是所有**两位以上**编号（M10~M18）全被判非卡 —— 实测抓出。
    head = text.rstrip("0123456789")
    return bool(head) and len(head) < len(text) and head.isalpha() and head.isascii()


CARD_RE = None  # 保留名字位（下方逻辑改用 is_card_id；正则穷举形态易漏，已弃用）
# 更宽的兜底：首格像"卡号"（字母数字连字符点、无空格/中文、长度 ≤12），用于把**未识别**的首格列出来
LOOSE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.\-]{0,11}$")


def split_row(line: str) -> list[str]:
    """按未转义管道切分（与外层管道产生的空段区分开——空单元格是内容）。"""
    PIPE, ESC = "|", "\\"
    cells, cur = [], []
    for i, ch in enumerate(line):
        if ch == PIPE and (i == 0 or line[i - 1] != ESC):
            cells.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    cells.append("".join(cur))
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return [c.strip() for c in cells]


def inventory() -> dict:
    out: dict = {"phases": {}, "totals": {}}
    for backlog in sorted(PHASES.glob("*/backlog.MD")):
        phase = backlog.parent.name
        lines = backlog.read_text(encoding="utf-8", errors="replace").splitlines()
        cards: list[dict] = []
        non_card_rows: list[dict] = []
        for i, ln in enumerate(lines, 1):
            if not ln.strip().startswith("|"):
                continue
            cells = split_row(ln)
            if not cells:
                continue
            first = cells[0]
            if is_card_id(first):
                title = cells[1] if len(cells) > 1 else ""
                # 一句话摘要：去掉来源前缀与 markdown 强调，取前 60 字
                summary = re.sub(r"^`\[[^\]]+\]`\s*", "", title)
                summary = summary.replace("**", "").strip()
                cards.append({"card": first, "line": i, "cells": len(cells),
                              "title": summary[:60], "title_chars": len(title)})
            elif first in {"卡号", "---"} or set(first) <= {"-", " "}:
                continue
            else:
                # 未识别的首格：可能是卡号漏判（用 LOOSE_RE 标出来供人工确认），也可能是真占位
                kind = "loose-card?" if LOOSE_RE.match(first) else "placeholder"
                non_card_rows.append({"first_cell": first[:20], "line": i, "cells": len(cells),
                                      "kind": kind})
        out["phases"][phase] = {"backlog": str(backlog.relative_to(REPO)).replace("\\", "/"),
                                "cards": cards, "non_card_rows": non_card_rows,
                                "card_count": len(cards)}
    out["totals"] = {
        "cards": sum(p["card_count"] for p in out["phases"].values()),
        "phases": len(out["phases"]),
        "non_card_rows": sum(len(p["non_card_rows"]) for p in out["phases"].values()),
    }
    return out


def main() -> int:
    inv = inventory()
    print(f"{'阶段':22s} {'卡数':>4s} {'非卡行':>6s}  最大单卡正文字符")
    for phase, data in inv["phases"].items():
        biggest = max((c["title_chars"] for c in data["cards"]), default=0)
        print(f"{phase:22s} {data['card_count']:4d} {len(data['non_card_rows']):6d}  {biggest}")
    t = inv["totals"]
    print(f"\n合计：{t['cards']} 张卡 / {t['phases']} 个阶段 / 非卡行 {t['non_card_rows']}")
    print("卡号示例：" + ", ".join(c["card"] for c in list(inv["phases"].values())[0]["cards"][:6]))
    if inv["totals"]["non_card_rows"]:
        print("\n非卡行（迁移时需保留或显式处置）：")
        for phase, data in inv["phases"].items():
            for row in data["non_card_rows"]:
                print(f"  {phase}:{row['line']} 首格={row['first_cell']!r} 格数={row['cells']} 类别={row['kind']}")

    if "--json" in sys.argv:
        path = Path(sys.argv[sys.argv.index("--json") + 1])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8", newline="")
        print(f"\n基线已落盘：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
