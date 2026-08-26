#!/usr/bin/env bash
# setup-env.sh — 一键创建 venv 并安装全部依赖（macOS/Linux）
# 用法：bash scripts/setup-env.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> 创建 venv: $ROOT/.venv"
python3 -m venv "$ROOT/.venv"

PY="$ROOT/.venv/bin/python"
"$PY" -m pip install --upgrade pip

# paper-qa 源码包未纳入 git，setuptools-scm 需要伪装版本号
export SETUPTOOLS_SCM_PRETEND_VERSION="2026.1.6.dev10+g36348d0ca"

# 先锁定与 uv.lock 对齐的版本，避免被 pip 升级到不兼容大版本
echo "==> 锁定 fhlmi / litellm 版本"
"$PY" -m pip install "fhlmi==0.42.1" "litellm==1.76.1"

echo "==> 安装本地 paper-qa 源码包（pypdf[media] + pymupdf readers）"
"$PY" -m pip install -e "$ROOT/paper-qa"
"$PY" -m pip install -e "$ROOT/paper-qa/packages/paper-qa-pypdf[media]"
"$PY" -m pip install -e "$ROOT/paper-qa/packages/paper-qa-pymupdf"

echo "==> 安装其余依赖"
"$PY" -m pip install -r "$ROOT/requirements-windows.txt"

echo ""
echo "完成！激活环境： source $ROOT/.venv/bin/activate"
