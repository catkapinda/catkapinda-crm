#!/usr/bin/env bash
set -euo pipefail

PORT_VALUE="${PORT:-8501}"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  echo "Python executable not found." >&2
  exit 1
fi

exec "$PYTHON_BIN" -m streamlit run app.py \
  --server.headless true \
  --server.address 0.0.0.0 \
  --server.port "$PORT_VALUE" \
  --browser.gatherUsageStats false
