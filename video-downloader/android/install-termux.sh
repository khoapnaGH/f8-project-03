#!/data/data/com.termux/files/usr/bin/bash
# =====================================================================
#  Cài VidGrab trên điện thoại Android (chạy trong ứng dụng Termux)
#  Cách chạy:  bash android/install-termux.sh
# =====================================================================
set -e
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -z "$TERMUX_VERSION" ] && [ ! -d /data/data/com.termux ]; then
  echo "[!] Script này chỉ dành cho Termux trên Android."; exit 1
fi

echo "==> [1/5] Cập nhật & cài gói hệ thống (python, ffmpeg, nodejs)…"
yes | pkg update -y -o Dpkg::Options::="--force-confnew" || true
pkg install -y -o Dpkg::Options::="--force-confnew" python ffmpeg nodejs curl termux-api

echo "==> [2/5] Cấp quyền truy cập bộ nhớ (hãy bấm CHO PHÉP nếu Android hỏi)…"
if [ ! -d "$HOME/storage/downloads" ]; then
  termux-setup-storage || true
  for _ in $(seq 1 20); do [ -d "$HOME/storage/downloads" ] && break; sleep 1; done
fi

echo "==> [3/5] Cài thư viện Python (yt-dlp, flask)…"
PKGS="yt-dlp yt-dlp-ejs flask mutagen"
if ! pip install --upgrade $PKGS; then
  echo "    Thử lại với trình biên dịch…"
  pkg install -y clang
  pip install --upgrade $PKGS
fi

echo "==> [4/5] Tạo lệnh 'vidgrab' và nút Chia sẻ → Termux…"
mkdir -p "$HOME/bin" "$HOME/.shortcuts"

cat > "$HOME/bin/vidgrab" <<EOS
#!/data/data/com.termux/files/usr/bin/bash
# Mở VidGrab (giữ máy không ngủ trong lúc tải)
termux-wake-lock 2>/dev/null || true
cd "$APP_DIR"
exec python app.py
EOS
chmod +x "$HOME/bin/vidgrab"

# Termux gọi file này khi bạn bấm "Chia sẻ → Termux" trong TikTok / Facebook / Instagram / YouTube
cat > "$HOME/bin/termux-url-opener" <<EOS
#!/data/data/com.termux/files/usr/bin/bash
SHARED="\$*"
if ! curl -s -o /dev/null --max-time 2 http://127.0.0.1:8686/api/settings; then
  echo "Đang khởi động VidGrab…"
  termux-wake-lock 2>/dev/null || true
  (cd "$APP_DIR" && VIDGRAB_NO_BROWSER=1 nohup python app.py > "\$HOME/.vidgrab.log" 2>&1 &)
  for _ in \$(seq 1 30); do
    curl -s -o /dev/null --max-time 1 http://127.0.0.1:8686/api/settings && break
    sleep 0.5
  done
fi
ENC=\$(python -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1], safe=""))' "\$SHARED")
termux-open-url "http://127.0.0.1:8686/?url=\$ENC"
echo "Đã mở VidGrab trong trình duyệt. VidGrab vẫn chạy nền — gõ 'vidgrab-stop' để tắt."
EOS
chmod +x "$HOME/bin/termux-url-opener"

cat > "$HOME/bin/vidgrab-stop" <<'EOS'
#!/data/data/com.termux/files/usr/bin/bash
pkill -f "python app.py" && echo "Đã tắt VidGrab." || echo "VidGrab không chạy."
termux-wake-unlock 2>/dev/null || true
EOS
chmod +x "$HOME/bin/vidgrab-stop"

# Lối tắt cho widget Termux:Widget (tuỳ chọn)
cp "$HOME/bin/vidgrab" "$HOME/.shortcuts/VidGrab"
chmod +x "$HOME/.shortcuts/VidGrab"

# đảm bảo ~/bin nằm trong PATH
grep -q 'HOME/bin' "$HOME/.bashrc" 2>/dev/null || echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"

echo "==> [5/5] Kiểm tra…"
python -c "import yt_dlp, flask; print('    yt-dlp', yt_dlp.version.__version__)"
command -v ffmpeg >/dev/null && echo "    ffmpeg OK"
command -v node   >/dev/null && echo "    nodejs OK (dùng cho YouTube)"

cat <<'MSG'

=====================================================
  ✅ Cài xong VidGrab!

  • Mở app:        gõ  vidgrab   (trình duyệt sẽ tự mở)
  • Tắt app:       gõ  vidgrab-stop
  • Tải nhanh:     trong TikTok/Facebook/Instagram/YouTube
                   bấm Chia sẻ → Termux
  • Cài ra màn hình chính: trong Chrome bấm "Cài app"
    (hoặc menu ⋮ → Thêm vào màn hình chính)
  • File lưu ở:    Download/VidGrab
=====================================================
MSG
