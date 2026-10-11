#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[setup] Root: $ROOT_DIR"

if [[ ! -f "config.json" ]]; then
  cp config.example.json config.json
  echo "[setup] Created config.json from config.example.json"
fi

PYTHON_BIN="${ROOT_DIR}/venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  python3.12 -m venv venv
  echo "[setup] Created virtual environment at venv/"
fi

"$PYTHON_BIN" -m ensurepip --upgrade >/dev/null 2>&1 || true
"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
"$PYTHON_BIN" -m pip install -r requirements.txt

echo ""
echo "[setup] Done."
echo "[setup] Configure provider keys in config.json."
echo "[setup] Start with: source venv/bin/activate && python scripts/producer_mode.py --help"
echo "[setup] For video rendering, install Node dependencies in remotion/."
