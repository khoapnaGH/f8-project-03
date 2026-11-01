#!/usr/bin/env bash
# VidGrab launcher (macOS / Linux)
set -e
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python)
if [ ! -x ".venv/bin/python" ]; then
  echo "[*] Lần đầu chạy: đang tạo môi trường và cài thư viện..."
  "$PY" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python app.py
