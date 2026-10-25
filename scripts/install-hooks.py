#!/usr/bin/env python
"""把本仓的 git 钩子目录指向**版本控制里的模板目录**（`scripts/hooks`）。

用法：
    .venv\\Scripts\\python.exe scripts/install-hooks.py            # 安装/更新
    .venv\\Scripts\\python.exe scripts/install-hooks.py --check    # 只核对（rc=1 =
    未安装或指向别处）

做法 = `git config --local core.hooksPath scripts/hooks`（git
官方支持的"钩子目录可配置"）。
**为什么不用"把模板拷进 `.git/hooks/`"**（第一版就是这么写的，两个理由）：
  * `.git/hooks/` **不在版本控制里** ⇒ "拷没拷过"不可核，且每次改模板都要重拷；
  * 拷贝的落点由 `git rev-parse --git-path hooks` 运行时解析 ⇒ 被
    `verify/verify_artifact_paths.py` 判为**动态写盘目标**（新脚本不允许）——本脚本现在
    **一个文件都不写**，只改一条 git 配置，落点是写死的仓库相对路径。

**诚实边界**：钩子是**便利层**——它可能没装、也可能被 `git commit --no-verify` 跳过。
真正"不可跳过"的那层是 CI（`.github/workflows/ci.yml` 用同一条
`structure-guard.py verify --from-git <base>` 判据复核本次 push 的提交范围）；
`verify/verify_gate_integrity.py::unskippable_guard_problems` 会断言那处接线**存在**。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 模块级常量（仓库相对、字面量）：钩子模板目录 = 版本控制里的 `scripts/hooks`
HOOKS_PATH_REL = "scripts/hooks"
# `commit-msg` 是**带署名的那一半**：只有它能读到待提交信息里的 `Structure-Removal:`
# （修复验证复核 `run-…-089` major ⇒ 二查 087-major-3）。
HOOKS = ("pre-commit", "commit-msg")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def main() -> int:
    """安装或核对 `core.hooksPath`；`--check` 模式只报差异（rc=1 = 需安装/修正）。"""
    ap = argparse.ArgumentParser(description="把本仓 git 钩子目录指向 "
    "scripts/hooks（结构守卫）")
    ap.add_argument("--check", action="store_true",
                    help="只核对，不写入（rc=1 = 未安装或指向别处）")
    args = ap.parse_args()

    template_dir = ROOT / HOOKS_PATH_REL
    problems: list[str] = []
    for name in HOOKS:
        path = template_dir / name
        if not path.is_file():
            problems.append(f"模板缺失：{path}")
    current = (_git("config", "--local", "--get",
                    "core.hooksPath").stdout or "").strip()
    if args.check:
        if current.replace("\\", "/").strip("/") != HOOKS_PATH_REL:
            problems.append(f"core.hooksPath = {current!r}（期望 {HOOKS_PATH_REL!r}）")
    elif not problems:
        setcfg = _git("config", "--local", "core.hooksPath", HOOKS_PATH_REL)
        if setcfg.returncode != 0:
            problems.append(f"`git config --local core.hooksPath` "
            f"失败：{setcfg.stderr.strip()[:120]}")
        else:
            print(f"installed: core.hooksPath -> {HOOKS_PATH_REL}"
                  f"（{len(HOOKS)} 个模板：{', '.join(HOOKS)}）")

    if problems:
        head = "HOOKS CHECK" if args.check else "INSTALL-HOOKS ERROR"
        print(f"{head}：{len(problems)} 项")
        for item in problems:
            print(f"  - {item}")
        if args.check:
            print("修法：`.venv\\Scripts\\python.exe scripts/install-hooks.py`")
        return 1
    print(f"HOOKS {'CHECK OK' if args.check else 'INSTALLED'}："
          f"core.hooksPath={current or HOOKS_PATH_REL}（模板目录 {HOOKS_PATH_REL}，"
          f"内容由版本控制保证）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
