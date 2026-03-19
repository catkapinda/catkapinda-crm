#!/usr/bin/env bash
set -euo pipefail

PORT_VALUE="${PORT:-8501}"

exec python -m streamlit run app.py \
  --server.headless true \
  --server.address 0.0.0.0 \
  --server.port "$PORT_VALUE" \
  --browser.gatherUsageStats false
