#!/usr/bin/env bash
# start-backend.sh — 启动 FastAPI 后端（http://127.0.0.1:8787）—— macOS/Linux
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 读取 paper-qa-script/.env（bash 风格 export KEY=value）
if [ -f "$ROOT/paper-qa-script/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/paper-qa-script/.env"
  set +a
fi
export HF_HUB_DISABLE_SYMLINKS_WARNING=1

cd "$ROOT"
exec "$ROOT/.venv/bin/python" "$ROOT/paper-qa-script/reactflow-paperqa-prototype/backend/main.py"
