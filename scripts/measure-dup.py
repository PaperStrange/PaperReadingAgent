"""量化代码冗余：对若干 git 提交快照统计 文件数/LOC/重复率/超大文件/长函数。

重复率算法（自实现，零依赖）：
  1) 归一化行：去首尾空白、丢空行、丢纯注释行、丢只有括号的行；
  2) 6 行滑窗 → 内容指纹；同一指纹出现 ≥2 次即"重复窗口"（跨文件/文件内都算）；
  3) 重复率 = 重复窗口数 × 6 / 归一化行总数（上限 100%）。
长函数：用 ast 统计 .py 里函数体 >60 行的个数。
"""
from __future__ import annotations

import ast
import collections
import hashlib
import pathlib
import subprocess
import sys
import tarfile
import tempfile

R = pathlib.Path(r"D:\All-Downloads\PaperReading\PaperReading-Windows")
CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
AREA_PREFIX = [
    ("paper-qa-script/reactflow-paperqa-prototype", "ReactFlow 前端+后端"),
    ("paper-qa-script/app", "后端 app"),
    ("paper-qa-script", "后端脚本(其它)"),
    ("agents-dashboard", "看板"),
    ("verify", "闸门/测试"),
    ("scripts", "运维脚本"),
]
WINDOW = 6


def normalize(text: str) -> list[str]:
    """抽归一化行。"""
    out: list[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith(("#", "//", "/*", "*", "'''", '"""', "--")):
            continue
        if s in ("{", "}", "(", ")", "};", "});", "):", "else:", "try:", "pass"):
            continue
        out.append(" ".join(s.split()))
    return out


def archive_root(sha: str) -> pathlib.Path:
    """把某提交的树导出到临时目录。"""
    d = pathlib.Path(tempfile.mkdtemp(prefix="dup-"))
    tar = d / "s.tar"
    subprocess.run(["git", "-C", str(R), "archive", "--format=tar",
                    "-o", str(tar), sha], check=True, capture_output=True)
    root = d / "tree"
    with tarfile.open(tar) as tf:
        tf.extractall(root)
    tar.unlink()
    return root


def area_of(rel: str) -> str:
    """归到一个功能区。"""
    for pref, name in AREA_PREFIX:
        if rel.startswith(pref):
            return name
    return "其它"


def count_long_funcs(text: str, limit: int = 60) -> int:
    """统计函数体行数 > limit 的函数个数。"""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return 0
    n = 0
    for node in ast.walk(tree):
        is_func = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        if is_func and node.end_lineno:
            if node.end_lineno - node.lineno > limit:
                n += 1
    return n


def measure(root: pathlib.Path) -> dict:
    """统计一棵树。"""
    areas: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"files": 0, "loc": 0, "norm": 0})
    win: collections.Counter[str] = collections.Counter()
    big: list[tuple[str, int]] = []
    long_funcs = 0
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in CODE_EXT:
            continue
        rel = p.relative_to(root).as_posix()
        txt = p.read_text(encoding="utf-8", errors="replace")
        norm = normalize(txt)
        loc = sum(1 for ln in txt.splitlines() if ln.strip())
        a = areas[area_of(rel)]
        a["files"] += 1
        a["loc"] += loc
        a["norm"] += len(norm)
        if loc > 600:
            big.append((rel, loc))
        if p.suffix == ".py":
            long_funcs += count_long_funcs(txt)
        for i in range(len(norm) - WINDOW + 1):
            block = "\n".join(norm[i:i + WINDOW]).encode()
            h = hashlib.blake2b(block, digest_size=8).hexdigest()
            win[h] += 1
    total_norm = sum(v["norm"] for v in areas.values())
    dup_windows = sum(1 for c in win.values() if c >= 2)
    return {"areas": dict(areas), "norm": total_norm, "dup_windows": dup_windows,
            "dup_rate": (dup_windows * WINDOW / total_norm) if total_norm else 0.0,
            "big": sorted(big, key=lambda t: -t[1])[:6], "long_funcs": long_funcs}


def main() -> int:
    """对命令行给的每个 sha 统计一次。"""
    for sha in sys.argv[1:]:
        m = measure(archive_root(sha))
        print(f"\n=== {sha[:12]} ===")
        print(f"  归一化行 {m['norm']:>6} | 重复窗口 {m['dup_windows']:>4} | "
              f"重复率 {m['dup_rate'] * 100:>5.1f}% | >60 行函数 {m['long_funcs']}")
        for a, v in sorted(m["areas"].items(), key=lambda kv: -kv[1]["loc"]):
            print(f"    {a:<20} 文件 {v['files']:>4}  LOC {v['loc']:>6}")
        if m["big"]:
            names = [f"{r.split('/')[-1]}({n})" for r, n in m["big"]]
            print("  最大文件:", ", ".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
