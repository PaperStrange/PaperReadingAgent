"""TG-2 覆盖矩阵 SSOT：从各 verify 脚本头部元数据派生 TEST-MATRIX.MD（唯一真源=脚本自身）。

元数据声明格式（脚本头部，必须在 import 区之前或紧随其后）：
  Python（verify_*.py）:
      VERIFY_META = {
          "features": ["一句话，覆盖的功能/契约"],
          "tier": "offline | network | gui",
          "providers": ["deepseek", "dashscope", ...] 或 [],
          "est_seconds": 10,        # 粗估运行时长
          "est_cost_cny": 0.0,      # 粗估单轮 API 成本（offline=0）
          "routes": ["/api/xxx"],   # 触达的后端路由（可空）
          "requires": ["none | playwright | servers | keys"],  # 前置条件
      }
  JS（gui_check_*.mjs）:
      // VERIFY_META: {"features": "...", "tier": "gui", "providers": [], "est_seconds": 20, "est_cost_cny": 0, "routes": [], "requires": "playwright+servers"}

两种模式：
  derive <verify_dir>  → 扫描目录全部脚本，解析元数据，生成 TEST-MATRIX.MD（缺元数据的脚本 → FAIL 并列出）
  check  <verify_dir>  → 重新 derive 到内存，与已入库 TEST-MATRIX.MD 逐字节比对；不一致 → FAIL + diff 提示
                        （CI 离线套件用，防止"改了脚本/加了脚本不登记"的漂移——1.39 同源思想）

退出码：0=通过；1=失败。
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

META_KEYS = ("features", "tier", "providers", "est_seconds", "est_cost_cny", "routes", "requires")
VALID_TIERS = ("offline", "network", "gui")


def parse_py_meta(path: Path) -> dict | None:
    """从 Python 脚本头部提取 VERIFY_META 字典字面量（ast 安全解析）。"""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError) as e:
        raise SystemExit(f"FAIL: {path.name} 解析失败: {e}")
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
            if len(targets) == 1 and isinstance(targets[0], ast.Name) and targets[0].id == "VERIFY_META":
                try:
                    return ast.literal_eval(node.value)
                except (ValueError, TypeError) as e:
                    raise SystemExit(f"FAIL: {path.name} VERIFY_META 必须是字面量字典: {e}")
    return None


_JS_META_RE = re.compile(r"^\s*//\s*VERIFY_META:\s*(\{.*\})\s*$", re.MULTILINE)


def parse_js_meta(path: Path) -> dict | None:
    """从 gui_check_*.mjs 头部提取 `// VERIFY_META: {...}` 单行 JSON。"""
    text = path.read_text(encoding="utf-8")
    m = _JS_META_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise SystemExit(f"FAIL: {path.name} VERIFY_META JSON 非法: {e}")


def validate_meta(path: Path, meta: dict) -> None:
    missing = [k for k in META_KEYS if k not in meta]
    if missing:
        raise SystemExit(f"FAIL: {path.name} 元数据缺键 {missing}")
    if meta["tier"] not in VALID_TIERS:
        raise SystemExit(f"FAIL: {path.name} tier 非法: {meta['tier']}（合法值 {VALID_TIERS}）")
    if not isinstance(meta["providers"], list):
        raise SystemExit(f"FAIL: {path.name} providers 必须是列表")
    if not isinstance(meta["routes"], list):
        raise SystemExit(f"FAIL: {path.name} routes 必须是列表")
    if not isinstance(meta["features"], str):
        raise SystemExit(f"FAIL: {path.name} features 必须是字符串")
    if not isinstance(meta["est_seconds"], (int, float)):
        raise SystemExit(f"FAIL: {path.name} est_seconds 必须是数字")
    if not isinstance(meta["est_cost_cny"], (int, float)):
        raise SystemExit(f"FAIL: {path.name} est_cost_cny 必须是数字")


def collect(verify_dir: Path) -> list[tuple[Path, dict]]:
    entries: list[tuple[Path, dict]] = []
    problems: list[str] = []
    for p in sorted(verify_dir.iterdir()):
        if p.name == "verify_matrix.py" or not p.is_file():
            continue
        meta: dict | None = None
        if p.name.startswith(("verify_", "eval_")) and p.suffix == ".py":
            meta = parse_py_meta(p)
        elif p.name.startswith("gui_check_") and p.suffix == ".mjs":
            meta = parse_js_meta(p)
        else:
            continue
        if meta is None:
            problems.append(f"缺元数据: {p.name}")
            continue
        try:
            validate_meta(p, meta)
        except SystemExit as e:
            problems.append(str(e))
            continue
        entries.append((p, meta))
    if problems:
        print("FAIL: 以下脚本未登记元数据（TG-2 规则：verify 脚本必须带 VERIFY_META 头部）:")
        for prob in problems:
            print(f"  - {prob}")
        raise SystemExit(1)
    return entries


def render_matrix(entries: list[tuple[Path, dict]]) -> str:
    lines = [
        "# TEST-MATRIX.MD —— 覆盖矩阵（TG-2 SSOT，自动生成，勿手改）",
        "",
        "> 唯一真源 = 各 verify 脚本头部的 `VERIFY_META`；本文件由 `verify_matrix.py derive` 生成，",
        "> `verify_matrix.py check`（CI 离线套件）逐字节比对防漂移。手改本文件会被 check 拦下。",
        "",
        "| 脚本 | 覆盖功能 | tier | providers | 预估时长 | 预估成本 | 路由 | 前置条件 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for path, meta in entries:
        prov = ", ".join(meta["providers"]) if meta["providers"] else "—"
        routes = ", ".join(meta["routes"]) if meta["routes"] else "—"
        req = ", ".join(meta["requires"]) if isinstance(meta["requires"], list) else str(meta["requires"])
        lines.append(
            f"| `{path.name}` | {meta['features']} | {meta['tier']} | {prov} | "
            f"{meta['est_seconds']}s | ¥{meta['est_cost_cny']:g} | {routes} | {req} |"
        )
    n_off = sum(1 for _, m in entries if m["tier"] == "offline")
    n_net = sum(1 for _, m in entries if m["tier"] == "network")
    n_gui = sum(1 for _, m in entries if m["tier"] == "gui")
    lines += [
        "",
        f"共 {len(entries)} 个脚本：offline {n_off} / network {n_net} / gui {n_gui}。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="TG-2 覆盖矩阵 derive/check")
    ap.add_argument("mode", choices=["derive", "check"])
    ap.add_argument("verify_dir", nargs="?", default=str(Path(__file__).parent))
    args = ap.parse_args()
    verify_dir = Path(args.verify_dir)
    matrix_path = verify_dir / "TEST-MATRIX.MD"

    entries = collect(verify_dir)
    rendered = render_matrix(entries)

    if args.mode == "derive":
        matrix_path.write_text(rendered, encoding="utf-8")
        print(f"DERIVE OK: {len(entries)} 脚本 → {matrix_path}")
        return 0

    # check mode
    if not matrix_path.exists():
        print(f"FAIL: {matrix_path} 不存在，先运行 derive 生成")
        return 1
    current = matrix_path.read_text(encoding="utf-8")
    if current != rendered:
        print("FAIL: TEST-MATRIX.MD 与脚本元数据不一致（脚本/元数据变更后须重新 derive）")
        import difflib

        for line in difflib.unified_diff(
            current.splitlines(), rendered.splitlines(),
            fromfile="TEST-MATRIX.MD(已入库)", tofile="派生(当前脚本元数据)", lineterm="",
        ):
            print(line)
        return 1
    print(f"CHECK OK: {len(entries)} 脚本与 TEST-MATRIX.MD 一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
