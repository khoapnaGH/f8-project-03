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
