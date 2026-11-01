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

## Cài đặt

**Yêu cầu:** Python 3.10+ · ffmpeg (khuyên cài) · Deno (khuyên cài cho YouTube)

### Windows
1. Cài [Python](https://www.python.org/downloads/) (nhớ tick **Add Python to PATH**)
2. Cài ffmpeg và Deno (mở PowerShell):
   ```powershell
   winget install Gyan.FFmpeg
   winget install DenoLand.Deno
   ```
3. Nhấp đúp **`run.bat`** → trình duyệt tự mở VidGrab.

### macOS / Linux
```bash
brew install ffmpeg deno          # macOS  (Linux: sudo apt install ffmpeg; curl -fsSL https://deno.land/install.sh | sh)
./run.sh
```

> Không cài được ffmpeg? App sẽ tự dùng ffmpeg đi kèm gói `imageio-ffmpeg`.
> YouTube hiện yêu cầu một JS runtime (Deno/Node) để giải mã link — nếu YouTube báo lỗi, hãy cài Deno.

## 📱 Chạy trên điện thoại Android

VidGrab chạy **ngay trên điện thoại** nhờ ứng dụng **Termux** (môi trường Linux cho Android), không cần máy tính.

### Cài đặt (làm 1 lần, ~5 phút, cần Wi-Fi)
1. Cài **Termux** từ [F-Droid](https://f-droid.org/packages/com.termux/) hoặc [GitHub](https://github.com/termux/termux-app/releases)
   (⚠️ **không** dùng bản trên Google Play, bản đó đã cũ và lỗi).
   Nên cài thêm **Termux:API** (cũng trên F-Droid) để video mới hiện ngay trong Thư viện ảnh.
2. Mở Termux, gõ từng dòng:
   ```bash
   pkg install -y git
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
