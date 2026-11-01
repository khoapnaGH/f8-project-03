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

APT_OPTS=(-y -o Dpkg::Options::="--force-confnew" -o Dpkg::Options::="--force-confdef")

echo "==> [1/5] Nâng cấp toàn bộ gói Termux (bắt buộc, tránh lỗi thư viện)…"
# Dùng 'apt' trực tiếp thay vì 'pkg': 'pkg' cần curl để chọn máy chủ, mà khi Termux
# nâng cấp dở dang thì chính curl bị lỗi "CANNOT LINK EXECUTABLE". 'apt' không cần curl.
export DEBIAN_FRONTEND=noninteractive
upgrade_all() {
  dpkg --configure -a || true
  apt-get update || true
  apt-get full-upgrade "${APT_OPTS[@]}" || true
  apt-get --fix-broken install "${APT_OPTS[@]}" || true
  dpkg --configure -a || true
}
upgrade_all

echo "    Cài python, nodejs…"
apt-get install "${APT_OPTS[@]}" python nodejs termux-api

echo "    Cài ffmpeg…"
ffmpeg_ok() { ffmpeg -version >/dev/null 2>&1; }
if ! { apt-get install "${APT_OPTS[@]}" ffmpeg && ffmpeg_ok; }; then
  echo "    ffmpeg lỗi — nâng cấp lại các thư viện nền rồi cài lại…"
  apt-get install --only-upgrade "${APT_OPTS[@]}" libc++ openssl || true
  upgrade_all
  apt-get install --reinstall "${APT_OPTS[@]}" ffmpeg || true
  dpkg --configure -a || true
fi
if ffmpeg_ok; then
  echo "    ffmpeg OK"
else
  FFMPEG_FAILED=1
  echo "    [!] ffmpeg vẫn lỗi. VidGrab vẫn chạy được (video thường, phụ đề, ảnh),"
  echo "        nhưng chưa ghép được video HD / chuyển MP3. Cách sửa ở cuối."
fi

echo "==> [2/5] Cấp quyền truy cập bộ nhớ (hãy bấm CHO PHÉP nếu Android hỏi)…"
if [ ! -d "$HOME/storage/downloads" ]; then
  termux-setup-storage || true
  for _ in $(seq 1 20); do [ -d "$HOME/storage/downloads" ] && break; sleep 1; done
fi

echo "==> [3/5] Cài thư viện Python (yt-dlp, flask)…"
PKGS="yt-dlp yt-dlp-ejs flask mutagen"
if ! pip install --upgrade $PKGS; then
  echo "    Thử lại với trình biên dịch…"
  apt-get install "${APT_OPTS[@]}" clang
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
alive() { python -c 'import urllib.request as u; u.urlopen("http://127.0.0.1:8686/api/settings", timeout=1)' >/dev/null 2>&1; }
if ! alive; then
  echo "Đang khởi động VidGrab…"
  termux-wake-lock 2>/dev/null || true
  (cd "$APP_DIR" && VIDGRAB_NO_BROWSER=1 nohup python app.py > "\$HOME/.vidgrab.log" 2>&1 &)
  for _ in \$(seq 1 30); do
    alive && break
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
ffmpeg_ok && echo "    ffmpeg OK"
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

if [ -n "$FFMPEG_FAILED" ]; then
cat <<'MSG'

⚠️  ffmpeg chưa chạy được. Thử lần lượt:
   1) termux-change-repo      (chọn "Mirror group" → "All mirrors")
   2) apt update && apt full-upgrade -y && dpkg --configure -a
   3) apt install --reinstall -y ffmpeg
   4) Kiểm tra Termux được cài từ F-Droid / GitHub, KHÔNG phải Google Play
      (bản Google Play quá cũ, luôn bị lỗi thư viện như thế này).
   5) Vẫn lỗi: Cài đặt Android → Ứng dụng → Termux → Xoá dữ liệu, mở lại Termux
      và chạy lại script này (bản Termux mới tinh luôn đồng bộ thư viện).
MSG
fi
