# VidGrab — Tải video, story & phụ đề

Tool chạy **trên máy của bạn** (giao diện web tại `http://127.0.0.1:8686`) để tải:

| Nền tảng | Hỗ trợ |
|---|---|
| **YouTube** | Video (tới 8K), Shorts, playlist, kênh, MP3, **phụ đề gốc + phụ đề tự động / dịch tự động** (SRT / VTT / TXT), xem & copy transcript |
| **Facebook** | Video, reel, watch, video trong nhóm, video riêng tư (cần cookie) |
| **Instagram** | Reel, post, **story**, highlight, tài khoản private (cần cookie) |
| **TikTok** | Video (không logo), link share rút gọn, tài khoản private (cần cookie) |
| Khác | ~1800 trang mà [yt-dlp](https://github.com/yt-dlp/yt-dlp) hỗ trợ |

## Tính năng
- Dán link → phân tích → chọn chất lượng (4K/1080p/720p…, kèm dung lượng ước tính)
- Tải video MP4 / MKV, ưu tiên H.264, nhúng phụ đề & metadata vào video
- Tách âm thanh MP3 / M4A / OPUS / FLAC / WAV, gắn ảnh bìa
- Phụ đề: chọn nhiều ngôn ngữ, tìm kiếm ngôn ngữ, xem trước, copy transcript, lưu .txt
- Playlist / story nhiều mục: chọn từng mục cần tải
- Tải hàng loạt nhiều link cùng lúc, hàng đợi có tiến độ / tốc độ / thời gian còn lại, huỷ, thử lại
- Xem video / nghe nhạc / đọc phụ đề ngay trong app, mở thư mục chứa file
- Giao diện tối / sáng, dùng tốt trên điện thoại, `Ctrl+V` ở bất kỳ đâu để dán & phân tích, kéo-thả link
- Cập nhật yt-dlp bằng 1 nút (các mạng xã hội đổi cách hoạt động liên tục)

## Cài đặt trên máy tính

Chỉ cần **Python 3.10+**. Lần chạy đầu tiên, script tự tạo môi trường riêng (`.venv`) và cài mọi thứ còn lại
(yt-dlp, ffmpeg dự phòng, Deno cho YouTube). Lần sau mở lên ngay.

### 🪟 Windows 10 / 11
1. Tải code về: trên GitHub bấm **Code → Download ZIP**, rồi giải nén.
2. Mở thư mục `video-downloader`, **bấm đúp `run.bat`**.
   - Chưa có Python? Script sẽ hỏi có cài tự động bằng `winget` không: bấm **Y**.
     (Hoặc tự cài từ [python.org](https://www.python.org/downloads/) và tick **Add python.exe to PATH**.)
   - Windows SmartScreen cảnh báo thì bấm **More info → Run anyway**.
3. Trình duyệt tự mở VidGrab. Muốn tắt thì đóng cửa sổ đen.

*Tuỳ chọn:* `winget install Gyan.FFmpeg` nếu muốn ffmpeg đầy đủ (app đã có sẵn ffmpeg dự phòng).

### 🍎 macOS (Intel & Apple Silicon)
1. Cài Python 3.10+ từ [python.org](https://www.python.org/downloads/macos/) hoặc `brew install python`.
   (Python có sẵn của macOS là 3.9, **quá cũ**. Nếu máy có Homebrew, script sẽ hỏi để cài giúp.)
2. Tải code về và giải nén, mở thư mục `video-downloader`, **bấm đúp `VidGrab.command`**.
   - Lần đầu macOS báo *"không thể mở vì không xác định được nhà phát triển"*: **chuột phải → Mở → Mở**.
   - Nếu vẫn bị chặn, mở Terminal và chạy: `xattr -dr com.apple.quarantine ~/Downloads/f8-project-03-*/video-downloader`
3. Trình duyệt tự mở VidGrab. Muốn tắt thì đóng cửa sổ Terminal.

*Tuỳ chọn:* `brew install ffmpeg`.
Đọc cookie trực tiếp từ Safari cần cấp quyền **Full Disk Access** cho Terminal; dùng file cookies.txt thì không cần.

### 🐧 Linux
```bash
sudo apt install python3 python3-venv ffmpeg   # Debian/Ubuntu
./run.sh
```

## 📱 Android: cài bằng file APK (dễ nhất)

1. Trên điện thoại, mở trang **Releases** của repo:
   `https://github.com/khoapnaGH/f8-project-03/releases/latest`
2. Tải **`VidGrab-arm64.apk`** (điện thoại Android 7 trở lên, 64-bit: hầu hết máy từ 2017 trở lại đây).
3. Mở file vừa tải → cho phép **Cài ứng dụng không rõ nguồn gốc** nếu được hỏi → **Cài đặt**.
4. Mở **VidGrab**. Lần đầu mất khoảng 10–30 giây để chuẩn bị. Bấm **Cho phép** thông báo để app tải tiếp khi bạn chuyển sang app khác.

Dùng: trong TikTok / Facebook / Instagram / YouTube bấm **Chia sẻ → VidGrab**, app tự mở và phân tích link.
File lưu ở **Download/VidGrab**. Bấm ↗ để mở bằng app khác, bấm biểu tượng chia sẻ để gửi qua Zalo, Messenger…

APK có sẵn ffmpeg (video HD, MP3) và QuickJS (YouTube), không cần cài thêm gì.
Khi một trang bị lỗi tải hàng loạt: **Cài đặt → Hệ thống → Cập nhật yt-dlp**, rồi thoát hẳn app (thông báo VidGrab → **Thoát**) và mở lại.

> **Cập nhật app mà không phải gỡ bản cũ:** mỗi bản APK cần được ký bằng cùng một khoá. Hãy tạo khoá một lần
> rồi lưu vào GitHub: repo → **Settings → Secrets and variables → Actions**, thêm `VIDGRAB_KEYSTORE_BASE64`
> (file `.jks` mã hoá base64) và `VIDGRAB_KEYSTORE_PASSWORD`. Chưa có thì mỗi bản build dùng khoá tạm,
> nên phải gỡ VidGrab cũ trước khi cài bản mới (dữ liệu cookie trong app sẽ mất, video đã tải vẫn còn).

APK được GitHub Actions tự build từ thư mục `android-app/` mỗi khi code thay đổi.

## 📱 Android: chạy bằng Termux (cách cũ)

VidGrab chạy **ngay trên điện thoại** nhờ ứng dụng **Termux** (môi trường Linux cho Android), không cần máy tính.

### Cài đặt (làm 1 lần, ~5 phút, cần Wi-Fi)
1. Cài **Termux** từ [F-Droid](https://f-droid.org/packages/com.termux/) hoặc [GitHub](https://github.com/termux/termux-app/releases)
   (⚠️ **không** dùng bản trên Google Play, bản đó đã cũ và lỗi).
   Nên cài thêm **Termux:API** (cũng trên F-Droid) để video mới hiện ngay trong Thư viện ảnh.
2. Mở Termux, gõ từng dòng:
   ```bash
   apt update && apt install -y git
   git clone https://github.com/khoapnaGH/f8-project-03.git
   bash f8-project-03/video-downloader/android/install-termux.sh
   ```
   Android hỏi quyền truy cập bộ nhớ thì bấm **Cho phép**.
   *(Repo riêng tư? Tải ZIP từ GitHub về máy, rồi trong Termux: `termux-setup-storage`, `cd ~/storage/downloads`, `unzip f8-project-03-*.zip`, sau đó chạy script trong thư mục vừa giải nén.)*

### Sử dụng
| Việc | Cách làm |
|---|---|
| Mở VidGrab | Mở Termux, gõ `vidgrab` (Chrome sẽ tự mở giao diện) |
| **Tải nhanh từ app** | Trong TikTok / Facebook / Instagram / YouTube bấm **Chia sẻ → Termux**: VidGrab tự khởi động và phân tích link |
| Cài như app thật | Trong Chrome bấm nút **Cài app** trên thanh trên cùng (hoặc ⋮ → *Thêm vào màn hình chính*). Sau đó còn chọn được **Chia sẻ → VidGrab** (khi Termux đang chạy `vidgrab`) |
| Tắt | Gõ `vidgrab-stop`, hoặc vuốt tắt thông báo Termux |
| File tải về | Thư mục **Download/VidGrab**, mở bằng ứng dụng Tệp / Thư viện |
| Cookie (story, private) | Xuất `cookies.txt` trên máy tính (xem phần dưới), gửi sang điện thoại, rồi vào **Cài đặt → Cookie → Nạp file** |

> Mẹo: khi tải file lớn, đừng vuốt tắt Termux. Script đã bật *wake-lock* để máy không ngắt khi màn hình tắt.

### Cách khác: dùng điện thoại điều khiển VidGrab trên máy tính
Chạy trên máy tính với `VIDGRAB_HOST=0.0.0.0` (Windows: `set VIDGRAB_HOST=0.0.0.0` rồi `run.bat`).
Màn hình sẽ in địa chỉ dạng `http://192.168.x.x:8686`; mở địa chỉ đó trên điện thoại (cùng Wi-Fi).
File được tải về máy tính; bấm nút ⬇ cạnh file để lưu sang điện thoại.

## Tải nội dung riêng tư / story
Story và video riêng tư chỉ xem được khi đăng nhập, nên VidGrab dùng **cookie của chính tài khoản bạn** — chỉ tải được những gì tài khoản đó **được phép xem** (đã follow, đã vào nhóm…).

1. Cài extension **Get cookies.txt LOCALLY** (Chrome/Edge/Cốc Cốc) hoặc **cookies.txt** (Firefox)
2. Đăng nhập Facebook / Instagram / TikTok / YouTube trên trình duyệt
3. Mở trang đó → bấm extension → **Export**
4. VidGrab → **Cài đặt → Cookie** → **Nạp file** vào đúng nền tảng (hoặc kéo-thả / dán nội dung, hỗ trợ cả JSON)

Hoặc chọn **Đọc cookie trực tiếp từ trình duyệt** (Firefox ổn định nhất; Chrome bản mới mã hoá cookie nên thường phải dùng file).

⚠️ File cookie giống như mật khẩu — đừng chia sẻ. Thư mục `cookies/` đã được đưa vào `.gitignore`. Nên dùng tài khoản phụ nếu tải nhiều.
Hãy tôn trọng bản quyền và quyền riêng tư của người khác.

## Cấu hình nâng cao
| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `VIDGRAB_PORT` | `8686` | Cổng web |
| `VIDGRAB_HOST` | `127.0.0.1` | Đặt `0.0.0.0` để dùng từ điện thoại trong cùng mạng LAN (cẩn thận: ai cùng mạng cũng truy cập được) |
| `VIDGRAB_NO_BROWSER` | — | Đặt `1` để không tự mở trình duyệt |

File tải về mặc định nằm ở `~/Downloads/VidGrab/<Nền tảng>/` (đổi trong Cài đặt → Chung).

## Lỗi thường gặp
- **"Sign in to confirm you're not a bot"** (YouTube) → nạp cookie YouTube.
- **"login required" / "private"** → nạp cookie tài khoản có quyền xem.
- **Lỗi hàng loạt trên 1 nền tảng** → Cài đặt → Hệ thống → **Cập nhật yt-dlp**, rồi khởi động lại.
- **Video không có tiếng / không ghép được** → cài ffmpeg.
