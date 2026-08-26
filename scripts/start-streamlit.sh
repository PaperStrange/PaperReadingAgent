#!/usr/bin/env bash
# start-streamlit.sh — 启动 Streamlit 调试 UI（http://127.0.0.1:8501）—— macOS/Linux
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$ROOT/paper-qa-script/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/paper-qa-script/.env"
  set +a
fi
export HF_HUB_DISABLE_SYMLINKS_WARNING=1

cd "$ROOT"
exec "$ROOT/.venv/bin/python" -m streamlit run \
  "$ROOT/paper-qa-script/streamlit_paperqa_app.py" \
  --server.headless true --browser.gatherUsageStats false
