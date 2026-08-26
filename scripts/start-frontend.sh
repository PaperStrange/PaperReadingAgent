#!/usr/bin/env bash
# start-frontend.sh — 启动 ReactFlow 前端（Vite，http://127.0.0.1:5173）—— macOS/Linux
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/paper-qa-script/reactflow-paperqa-prototype/frontend"

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "==> 首次运行：npm ci"
  (cd "$FRONTEND" && npm ci)
fi

cd "$FRONTEND"
exec npm run dev
