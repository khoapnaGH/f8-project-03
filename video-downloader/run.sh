#!/usr/bin/env bash
# =====================================================================
#  VidGrab launcher cho macOS / Linux
#  macOS: bấm đúp "VidGrab.command" (file này được gọi từ đó)
# =====================================================================
set -e
cd "$(dirname "$0")"

ok_py() { "$1" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)' >/dev/null 2>&1; }

find_python() {
  PY=""
  for c in python3.13 python3.12 python3.11 python3.10 python3 python \
           /opt/homebrew/bin/python3 /usr/local/bin/python3 \
           /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
    if command -v "$c" >/dev/null 2>&1 && ok_py "$c"; then PY="$(command -v "$c")"; return 0; fi
  done
  return 1
}

if ! find_python; then
  echo
  echo "[!] Cần Python 3.10 trở lên (Python có sẵn của macOS là 3.9, quá cũ)."
  if command -v brew >/dev/null 2>&1; then
    read -r -p "    Cài Python bằng Homebrew ngay bây giờ? [Y/n] " a
    if [[ ! "$a" =~ ^[Nn] ]]; then brew install python@3.12; find_python || true; fi
  fi
  if [ -z "$PY" ]; then
    echo "    Tải Python tại: https://www.python.org/downloads/  rồi chạy lại."
    if [[ "$(uname)" == "Darwin" ]]; then open "https://www.python.org/downloads/macos/"; fi
    exit 1
  fi
fi

# tạo lại môi trường nếu chưa có hoặc bị hỏng
if [ ! -x ".venv/bin/python" ] || ! ok_py ".venv/bin/python"; then
  echo "[*] Lần đầu chạy: đang tạo môi trường với $("$PY" --version)…"
  rm -rf .venv
  "$PY" -m venv .venv
fi

# chỉ cài lại thư viện khi requirements.txt thay đổi
if ! cmp -s requirements.txt .venv/requirements.installed; then
  echo "[*] Đang cài / cập nhật thư viện (1-3 phút)…"
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install -r requirements.txt
  cp requirements.txt .venv/requirements.installed
fi

exec .venv/bin/python app.py
