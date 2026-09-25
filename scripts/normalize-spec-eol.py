#!/usr/bin/env python3
"""一次性修复：把 8 个 spec 的 CRLF 行尾归一化回 LF（TG-15 二查 p2 实证缺陷的收尾）。

背景：`scripts/migrate-scope-declarations.py` 原先用 `Path.write_text()`（文本模式），
Windows 下把整文件 `\\n` 翻成 `\\r\\n` → "只改 3 行 frontmatter"的文件 raw diffstat 虚高约 5 倍
（实测 8 个 spec：2653/882 → 语义 1961/190，每个 spec 实为精确 +3/-1）。
脚本本身已修（`write_lf()` + 读侧归一化），本脚本只负责把**已经写坏的那 8 个文件**改回来。

判据（自证）：
  ① 每个文件转换后 `git diff --stat` 的行数应回落为 +3/-1（frontmatter 三行），而不是整文件重写；
  ② `git ls-files --eol` 对这些文件应显示 `w/lf`。

用法：python scripts/normalize-spec-eol.py [--check]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_DIR = REPO_ROOT / "agents" / "functions"


def eol_state() -> str:
    r = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", "--eol", "agents/functions"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def normalize(path: Path) -> bool:
    """返回是否发生改动。用字节写盘 + `newline=""` 关闭行尾翻译。"""
    raw = path.read_bytes()
    if b"\r\n" not in raw:
        return False
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return True


def main() -> int:
    check = "--check" in sys.argv
    changed: list[str] = []
    for path in sorted(SPEC_DIR.glob("*.md")):
        raw = path.read_bytes()
        if b"\r\n" in raw:
            if check:
                changed.append(path.name)
                continue
            if normalize(path):
                changed.append(path.name)

    if check:
        if changed:
            print(f"EOL-CHECK FAIL：{len(changed)} 个 spec 仍是 CRLF：{changed}")
            return 1
        print("EOL-CHECK PASS：agents/functions/*.md 全部为 LF")
        return 0

    print(f"已归一化 {len(changed)} 个文件 → LF：{changed or '（无需改动）'}")
    print("\n-- git ls-files --eol（w/ 列为工作区行尾）--")
    for line in eol_state().splitlines():
        print("  " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
