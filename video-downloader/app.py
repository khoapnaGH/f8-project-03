"""
VidGrab - Local video / story / subtitle downloader
Hỗ trợ: YouTube, Facebook, Instagram, TikTok (+ ~1800 trang khác mà yt-dlp hỗ trợ)

Chạy:  python app.py   ->  mở http://127.0.0.1:8686
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.parse
import urllib.request
import uuid
import webbrowser
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory, Response

import yt_dlp
from yt_dlp.utils import DownloadCancelled

BASE_DIR = Path(__file__).resolve().parent
# Bản APK Android truyền các thư mục qua biến môi trường (xem android-app/)
STATIC_DIR = Path(os.environ.get("VIDGRAB_STATIC_DIR") or BASE_DIR / "static")
DATA_DIR = Path(os.environ.get("VIDGRAB_DATA_DIR") or BASE_DIR)
DATA_DIR.mkdir(parents=True, exist_ok=True)
COOKIES_DIR = DATA_DIR / "cookies"
SETTINGS_FILE = DATA_DIR / "settings.json"
HISTORY_FILE = DATA_DIR / "history.json"
IS_APK = os.environ.get("VIDGRAB_APK") == "1"

COOKIES_DIR.mkdir(exist_ok=True)

PLATFORMS = ["youtube", "facebook", "instagram", "tiktok"]
SUPPORTED_BROWSERS = ["chrome", "edge", "firefox", "brave", "opera", "vivaldi", "chromium", "safari", "whale"]

IS_ANDROID = bool(IS_APK or os.environ.get("TERMUX_VERSION") or hasattr(sys, "getandroidapilevel")
                  or os.path.isdir("/data/data/com.termux"))


def default_download_dir() -> str:
    if os.environ.get("VIDGRAB_DOWNLOAD_DIR"):
        return os.environ["VIDGRAB_DOWNLOAD_DIR"]
    if IS_ANDROID:
        # sau khi chạy `termux-setup-storage`, ~/storage/downloads trỏ tới thư mục Download của máy
        for cand in (Path.home() / "storage" / "downloads", Path("/sdcard/Download"),
                     Path("/storage/emulated/0/Download")):
            if cand.is_dir() and os.access(cand, os.W_OK):
                return str(cand / "VidGrab")
        return str(Path.home() / "VidGrab")
    return str(Path.home() / "Downloads" / "VidGrab")


DEFAULT_SETTINGS = {
    "download_dir": default_download_dir(),
    "cookie_browser": "",          # "" = không dùng cookie trình duyệt
    "max_concurrent": 3,
    "filename_template": "%(title).120B [%(id)s].%(ext)s",
    "folder_per_platform": True,
}

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")


# --------------------------------------------------------------------------- #
#  Settings / helpers
# --------------------------------------------------------------------------- #
_settings_lock = threading.Lock()


def load_settings() -> dict:
    data = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            data.update(json.loads(SETTINGS_FILE.read_text("utf-8")))
        except Exception:
            pass
    return data


def save_settings(data: dict) -> None:
    with _settings_lock:
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


SETTINGS = load_settings()


def download_dir() -> Path:
    p = Path(SETTINGS["download_dir"]).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def which(name: str) -> str | None:
    """Tìm chương trình trong PATH và cả trong thư mục môi trường ảo (.venv/bin, .venv\\Scripts),
    nơi pip cài deno — vì khi chạy .venv/python trực tiếp, thư mục đó không nằm trong PATH."""
    found = shutil.which(name)
    if found:
        return found
    return shutil.which(name, path=str(Path(sys.executable).parent))


def ffmpeg_works(path: str) -> bool:
    """ffmpeg có thể tồn tại nhưng hỏng (vd. Termux lệch thư viện) — chạy thử cho chắc."""
    try:
        return subprocess.run([path, "-version"], capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False


def find_ffmpeg() -> str | None:
    """Trả về đường dẫn ffmpeg: ưu tiên ffmpeg hệ thống, sau đó imageio-ffmpeg."""
    env_ff = os.environ.get("VIDGRAB_FFMPEG")   # APK: libffmpeg.so đi kèm app
    if env_ff and ffmpeg_works(env_ff):
        return env_ff
    sys_ff = which("ffmpeg")
    if sys_ff and ffmpeg_works(sys_ff):
        return sys_ff
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


FFMPEG = find_ffmpeg()


def available_js_runtimes() -> dict:
    """YouTube cần JS runtime để giải mã link. Bật mọi runtime có sẵn (Android thường chỉ có node)."""
    try:
        from yt_dlp.globals import supported_js_runtimes

        supported = set(supported_js_runtimes.value.keys())
    except Exception:
        supported = {"deno"}
    exe = {"deno": "deno", "node": "node", "bun": "bun", "quickjs": "qjs"}
    found = {}
    qjs = os.environ.get("VIDGRAB_QJS")   # APK: QuickJS đi kèm app
    if qjs and "quickjs" in supported and os.path.exists(qjs):
        found["quickjs"] = {"path": qjs}
    for k in ("deno", "node", "bun", "quickjs"):
        if k in found:
            continue
        path = which(exe[k]) if k in supported else None
        if path:
            found[k] = {"path": path}
    return found


JS_RUNTIMES = available_js_runtimes()


def detect_platform(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    if any(h in host for h in ("youtube.com", "youtu.be", "youtube-nocookie.com")):
        return "youtube"
    if any(h in host for h in ("facebook.com", "fb.watch", "fb.com", "fbcdn.net")):
        return "facebook"
    if any(h in host for h in ("instagram.com", "instagr.am")):
        return "instagram"
    if "tiktok.com" in host:
        return "tiktok"
    return "other"


URL_RE = re.compile(r"https?://[^\s<>\"']+")


def clean_url(text: str) -> str:
    """Lấy URL đầu tiên trong đoạn text (vd. text share của TikTok có kèm chữ)."""
    text = (text or "").strip()
    m = URL_RE.search(text)
    if not m:
        return text
    return m.group(0).rstrip(").,;!")


def cookie_opts(url: str, use_cookies: bool = True) -> dict:
    """Chọn nguồn cookie: file cookies/<platform>.txt  ->  cookies/all.txt  ->  trình duyệt."""
    if not use_cookies:
        return {}
    plat = detect_platform(url)
    for name in (f"{plat}.txt", "all.txt"):
        f = COOKIES_DIR / name
        if f.exists() and f.stat().st_size > 0:
            return {"cookiefile": str(f)}
    browser = SETTINGS.get("cookie_browser") or ""
    if browser:
        return {"cookiesfrombrowser": (browser,)}
    return {}


def base_opts(url: str, use_cookies: bool = True) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "windowsfilenames": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
    }
    if JS_RUNTIMES:
        opts["js_runtimes"] = JS_RUNTIMES
    if FFMPEG:
        opts["ffmpeg_location"] = FFMPEG
    opts.update(cookie_opts(url, use_cookies))
    return opts


def friendly_error(msg: str) -> str:
    raw = re.sub(r"\x1b\[[0-9;]*m", "", str(msg)).replace("ERROR: ", "").strip()
    low = raw.lower()
    hint = ""
    if "sign in to confirm" in low or "not a bot" in low:
        hint = "YouTube yêu cầu xác minh. Hãy nạp cookie YouTube (Cài đặt → Cookie) rồi thử lại."
    elif any(k in low for k in ("login", "log in", "cookies", "private", "requires authentication",
                                 "not available", "restricted", "checkpoint", "you need to log")):
        hint = ("Nội dung riêng tư / cần đăng nhập. Nạp cookie của tài khoản có quyền xem "
                "(Cài đặt → Cookie) rồi thử lại.")
    elif "unsupported url" in low:
        hint = "Link này không được hỗ trợ hoặc sai định dạng."
    elif "rate" in low and "limit" in low or "429" in low:
        hint = "Bị giới hạn tốc độ (rate-limit). Đợi vài phút hoặc dùng cookie đăng nhập."
    elif "ffmpeg" in low:
        hint = "Thiếu ffmpeg. Cài ffmpeg (xem README) để ghép video/âm thanh."
    elif "could not copy" in low and "cookie" in low or "failed to decrypt" in low:
        hint = ("Không đọc được cookie từ trình duyệt (Chrome mới mã hoá cookie). "
                "Hãy đóng trình duyệt, hoặc dùng Firefox, hoặc xuất file cookies.txt.")
    elif "unable to extract" in low or "http error 4" in low:
        hint = "Không lấy được dữ liệu. Thử cập nhật yt-dlp (Cài đặt → Cập nhật) hoặc dùng cookie."
    return raw + (f"\n💡 {hint}" if hint else "")


# --------------------------------------------------------------------------- #
#  Subtitle parsing (VTT/SRT  ->  plain text / segments)
# --------------------------------------------------------------------------- #
TS_RE = re.compile(r"(\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{3}\s*-->\s*(\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{3}")
TAG_RE = re.compile(r"<[^>]+>")


def parse_subtitle(text: str) -> list[dict]:
    """Trả về [{start, text}] đã khử trùng lặp (auto-caption YouTube lặp dòng)."""
    segments: list[dict] = []
    last_line = None
    blocks = re.split(r"\r?\n\r?\n", text.replace("﻿", ""))
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        ts_idx = next((i for i, l in enumerate(lines) if TS_RE.search(l)), None)
        if ts_idx is None:
            continue
        start = lines[ts_idx].split("-->")[0].strip().replace(",", ".")
        for l in lines[ts_idx + 1:]:
            clean = TAG_RE.sub("", l)
            clean = (clean.replace("&nbsp;", " ").replace("&amp;", "&")
                     .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
                     .replace("&quot;", '"').strip())
            if not clean or clean == last_line:
                continue
            last_line = clean
            segments.append({"start": start.split(".")[0], "text": clean})
    return segments


def segments_to_text(segments: list[dict], with_time: bool = False) -> str:
    if with_time:
        return "\n".join(f"[{s['start']}] {s['text']}" for s in segments)
    return "\n".join(s["text"] for s in segments)


# --------------------------------------------------------------------------- #
#  Job manager
# --------------------------------------------------------------------------- #
class Job:
    def __init__(self, url: str, options: dict):
        self.id = uuid.uuid4().hex[:10]
        self.url = url
        self.options = options
        self.platform = detect_platform(url)
        self.title = options.get("title") or url
        self.thumbnail = options.get("thumbnail") or ""
        self.mode = options.get("mode", "video")
        self.status = "queued"          # queued|downloading|processing|done|error|cancelled
        self.progress = 0.0
        self.speed = ""
        self.eta = ""
        self.downloaded = ""
        self.total = ""
        self.item = ""                  # "2/10" khi tải playlist
        self.message = ""
        self.error = ""
        self.files: list[dict] = []
        self.created = time.time()
        self.finished = None
        self.cancel = threading.Event()

    def to_dict(self) -> dict:
        return {
            k: getattr(self, k)
            for k in ("id", "url", "platform", "title", "thumbnail", "mode", "status", "progress",
                      "speed", "eta", "downloaded", "total", "item", "message", "error", "files",
                      "created", "finished")
        }


JOBS: dict[str, Job] = {}
JOBS_LOCK = threading.Lock()
_slots = threading.Semaphore(int(SETTINGS.get("max_concurrent", 3)))


def load_history() -> None:
    if not HISTORY_FILE.exists():
        return
    try:
        for d in json.loads(HISTORY_FILE.read_text("utf-8")):
            j = Job(d["url"], {"title": d.get("title"), "thumbnail": d.get("thumbnail"), "mode": d.get("mode")})
            for k, v in d.items():
                if k in ("id", "status", "progress", "message", "error", "files", "created", "finished", "item"):
                    setattr(j, k, v)
            if j.status in ("queued", "downloading", "processing"):
                j.status, j.error = "error", "Bị gián đoạn do tắt ứng dụng."
            JOBS[j.id] = j
    except Exception:
        pass


def save_history() -> None:
    with JOBS_LOCK:
        data = [j.to_dict() for j in sorted(JOBS.values(), key=lambda x: x.created)][-300:]
    try:
        HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    except Exception:
        pass


def human_size(n) -> str:
    if not n:
        return ""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"


def human_eta(sec) -> str:
    if sec is None:
        return ""
    sec = int(sec)
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


VIDEO_EXT = {"mp4", "mkv", "webm", "mov", "avi", "flv", "m4v", "3gp"}
AUDIO_EXT = {"mp3", "m4a", "opus", "ogg", "wav", "flac", "aac"}
SUB_EXT = {"srt", "vtt", "ass", "txt", "json3", "ttml", "srv3"}
IMG_EXT = {"jpg", "jpeg", "png", "webp", "heic"}


def file_kind(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in SUB_EXT:
        return "subtitle"
    if ext in IMG_EXT:
        return "image"
    return "other"


def build_download_opts(job: Job, folder: Path) -> dict:
    """folder = thư mục tạm riêng của job; file được chuyển sang thư mục đích khi xong."""
    o = job.options
    url = job.url
    opts = base_opts(url, o.get("use_cookies", True))
    sub = "%(extractor_key)s" if SETTINGS.get("folder_per_platform", True) else ""
    tmpl = SETTINGS.get("filename_template") or DEFAULT_SETTINGS["filename_template"]
    if not tmpl.endswith(".%(ext)s"):
        tmpl += ".%(ext)s"
    opts["outtmpl"] = {"default": str(folder / sub / tmpl) if sub else str(folder / tmpl)}
    if o.get("is_playlist"):
        opts["ignoreerrors"] = "only_download"   # 1 mục lỗi không làm hỏng cả danh sách
    pps: list[dict] = []

    mode = job.mode
    if o.get("playlist_items"):
        opts["playlist_items"] = o["playlist_items"]
    if not o.get("playlist", True):
        opts["noplaylist"] = True

    if mode == "video":
        q = str(o.get("quality", "best"))
        if q == "best":
            fmt = "bv*+ba/b"
        else:
            h = int(q)
            fmt = f"bv*[height<={h}]+ba/b[height<={h}]/bv*+ba/b"
        opts["format"] = fmt
        if o.get("prefer_mp4", True):
            opts["format_sort"] = ["res", "vcodec:h264", "ext:mp4:m4a"] if o.get("h264") else ["res", "ext:mp4:m4a"]
            opts["merge_output_format"] = "mp4"
        else:
            opts["merge_output_format"] = "mkv"
        if o.get("embed_metadata"):
            pps.append({"key": "FFmpegMetadata", "add_metadata": True})
        if o.get("thumbnail_file"):
            opts["writethumbnail"] = True
    elif mode == "audio":
        afmt = o.get("audio_format", "mp3")
        opts["format"] = "ba/b"
        pps.append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": afmt,
            "preferredquality": str(o.get("audio_quality", "192")),
        })
        if o.get("embed_metadata", True):
            pps.append({"key": "FFmpegMetadata", "add_metadata": True})
        if o.get("embed_thumbnail", True) and afmt in ("mp3", "m4a", "opus", "flac"):
            opts["writethumbnail"] = True
            pps.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"})
            pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
    elif mode == "subs":
        opts["skip_download"] = True
    elif mode == "thumbnail":
        opts["skip_download"] = True
        opts["writethumbnail"] = True
        pps.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"})

    # ----- subtitles -----
    subs = o.get("subs") or {}
    langs = subs.get("langs") or []
    if langs and mode in ("video", "subs"):
        opts["writesubtitles"] = bool(subs.get("manual", True))
        opts["writeautomaticsub"] = bool(subs.get("auto", False))
        opts["subtitleslangs"] = langs
        sfmt = subs.get("format", "srt")
        if sfmt in ("srt", "txt"):
            opts["subtitlesformat"] = "srt/vtt/best" if sfmt == "srt" else "vtt/srt/best"
            if sfmt == "srt":
                pps.append({"key": "FFmpegSubtitlesConvertor", "format": "srt", "when": "before_dl"})
        else:
            opts["subtitlesformat"] = f"{sfmt}/best"
        if mode == "video" and subs.get("embed"):
            pps.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": True})

    opts["postprocessors"] = pps

    # ----- hooks -----
    def progress_hook(d):
        if job.cancel.is_set():
            raise DownloadCancelled("Đã huỷ")
        info = d.get("info_dict") or {}
        if info.get("playlist_index") and info.get("n_entries"):
            job.item = f"{info['playlist_index']}/{info['n_entries']}"
        if d["status"] == "downloading":
            job.status = "downloading"
            done = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if total:
                job.progress = round(min(done / total * 100, 99.9), 1)
            elif d.get("fragment_count"):
                job.progress = round((d.get("fragment_index") or 0) / d["fragment_count"] * 100, 1)
            job.speed = (human_size(d.get("speed")) + "/s") if d.get("speed") else ""
            job.eta = human_eta(d.get("eta"))
            job.downloaded = human_size(done)
            job.total = human_size(total)
            fn = os.path.basename(d.get("filename") or "")
            job.message = fn
        elif d["status"] == "finished":
            job.progress = 100.0
            job.message = "Đã tải xong phần dữ liệu, đang xử lý…"

    def pp_hook(d):
        if job.cancel.is_set():
            raise DownloadCancelled("Đã huỷ")
        if d["status"] == "started":
            job.status = "processing"
            names = {
                "Merger": "Ghép video + âm thanh",
                "FFmpegMerger": "Ghép video + âm thanh",
                "FFmpegExtractAudio": "Chuyển đổi âm thanh",
                "FFmpegSubtitlesConvertor": "Chuyển đổi phụ đề",
                "FFmpegEmbedSubtitle": "Nhúng phụ đề",
                "EmbedThumbnail": "Nhúng ảnh bìa",
                "FFmpegMetadata": "Ghi metadata",
                "FFmpegVideoRemuxer": "Đóng gói lại video",
                "MoveFiles": "Hoàn thiện file",
                "FFmpegThumbnailsConvertor": "Chuyển đổi ảnh bìa",
                "FFmpegFixupM3u8": "Sửa lỗi luồng video",
                "FFmpegFixupM4a": "Sửa lỗi âm thanh",
            }
            job.message = names.get(d.get("postprocessor"), f"Xử lý: {d.get('postprocessor')}")

    opts["progress_hooks"] = [progress_hook]
    opts["postprocessor_hooks"] = [pp_hook]
    return opts


class JobLogger:
    """Ghi nhận lỗi/cảnh báo của yt-dlp để báo lại cho người dùng."""

    def __init__(self, job: "Job"):
        self.job = job
        self.errors: list[str] = []

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        self.errors.append(str(msg))


def android_visible_path(p: Path) -> str:
    s = str(p)
    for prefix in (str(Path.home() / "storage" / "downloads"), "/storage/emulated/0/Download", "/sdcard/Download"):
        if s.startswith(prefix):
            return "Download" + s[len(prefix):]
    return s


def android_media_scan(paths: list[Path]) -> None:
    """Cho file mới hiện ngay trong Thư viện ảnh / Nhạc (Termux: cần gói termux-api)."""
    if not IS_ANDROID or not paths:
        return
    if IS_APK:
        try:
            from java import jclass  # type: ignore  # Chaquopy

            jclass("com.vidgrab.app.Bridge").scanFiles([str(p) for p in paths])
        except Exception:
            traceback.print_exc()
        return
    if not shutil.which("termux-media-scan"):
        return
    try:
        subprocess.Popen(["termux-media-scan", *map(str, paths)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def staging_dir(job: Job) -> Path:
    base = os.environ.get("VIDGRAB_STAGING_DIR")
    return (Path(base) if base else download_dir() / ".vidgrab-tmp") / job.id


def move_staged_files(job: Job) -> list[dict]:
    """Chuyển file hoàn chỉnh từ thư mục tạm của job sang thư mục tải về."""
    root = download_dir()
    stage = staging_dir(job)
    moved = []
    if not stage.exists():
        return moved
    for dirpath, _dirs, files in os.walk(stage):
        for fn in files:
            if fn.endswith((".part", ".ytdl", ".temp")) or ".part-Frag" in fn:
                continue
            src = Path(dirpath) / fn
            rel = src.relative_to(stage)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(src, dst)
            except OSError:
                shutil.move(str(src), str(dst))
            moved.append({
                "name": dst.name,
                "path": str(dst.relative_to(root)).replace("\\", "/"),
                "size": human_size(dst.stat().st_size),
                "kind": file_kind(dst.name),
            })
    order = {"video": 0, "audio": 1, "image": 2, "subtitle": 3, "other": 4}
    moved.sort(key=lambda f: (order[f["kind"]], f["name"]))
    android_media_scan([root / f["path"] for f in moved])
    return moved


def convert_staged_subs_to_txt(job: Job) -> None:
    for dirpath, _dirs, files in os.walk(staging_dir(job)):
        for fn in files:
            if fn.lower().endswith((".vtt", ".srt")):
                p = Path(dirpath) / fn
                try:
                    segs = parse_subtitle(p.read_text("utf-8", errors="ignore"))
                    p.with_suffix(".txt").write_text(segments_to_text(segs), "utf-8")
                    p.unlink()
                except Exception:
                    pass


def run_job(job: Job) -> None:
    with _slots:
        if job.cancel.is_set():
            job.status = "cancelled"
            return
        job.status = "downloading"
        job.message = "Đang kết nối…"
        logger = JobLogger(job)
        stage = staging_dir(job)
        info = None
        try:
            opts = build_download_opts(job, stage)
            opts["logger"] = logger
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(job.url, download=True)
            if info and job.title == job.url:
                job.title = info.get("title") or job.url
            if info and not job.thumbnail:
                job.thumbnail = info.get("thumbnail") or ""
            if job.mode == "subs" and (job.options.get("subs") or {}).get("format") == "txt":
                convert_staged_subs_to_txt(job)
            job.files = move_staged_files(job)
            if not job.files:
                last = logger.errors[-1] if logger.errors else ""
                if job.mode == "subs":
                    raise RuntimeError(last or "Không tìm thấy phụ đề cho ngôn ngữ đã chọn.")
                raise RuntimeError(last or "Không tải được file nào.")
            job.status = "done"
            job.progress = 100.0
            fails = len(logger.errors)
            job.message = f"Hoàn tất · {len(job.files)} file" + (f" · {fails} mục lỗi" if fails else "")
        except DownloadCancelled:
            job.status = "cancelled"
            job.message = "Đã huỷ"
        except Exception as e:  # noqa: BLE001
            if job.cancel.is_set():
                job.status = "cancelled"
                job.message = "Đã huỷ"
            else:
                job.status = "error"
                job.error = friendly_error(str(e))
                traceback.print_exc()
            # giữ lại những file đã tải xong (vd. một phần playlist)
            if job.status == "error":
                try:
                    job.files = move_staged_files(job)
                except Exception:
                    pass
        finally:
            shutil.rmtree(stage, ignore_errors=True)
            job.finished = time.time()
            job.speed = job.eta = ""
            save_history()


# --------------------------------------------------------------------------- #
#  Info extraction
# --------------------------------------------------------------------------- #
def summarize_info(info: dict, url: str) -> dict:
    is_playlist = info.get("_type") == "playlist" or bool(info.get("entries"))
    result = {
        "url": url,
        "webpage_url": info.get("webpage_url") or url,
        "platform": detect_platform(url),
        "extractor": info.get("extractor_key") or info.get("extractor"),
        "id": info.get("id"),
        "title": info.get("title") or info.get("id") or "Không có tiêu đề",
        "uploader": info.get("uploader") or info.get("channel") or info.get("uploader_id") or "",
        "thumbnail": info.get("thumbnail") or "",
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "upload_date": info.get("upload_date"),
        "description": (info.get("description") or "")[:600],
        "is_playlist": is_playlist,
        "entries": [],
        "heights": [],
        "subtitles": [],
        "auto_subtitles": [],
        "has_video": True,
    }
    if is_playlist:
        entries = [e for e in (info.get("entries") or []) if e]
        result["count"] = info.get("playlist_count") or len(entries)
        for i, e in enumerate(entries[:300], 1):
            thumb = e.get("thumbnail") or ""
            if not thumb and e.get("thumbnails"):
                thumb = e["thumbnails"][-1].get("url", "")
            result["entries"].append({
                "index": i,
                "id": e.get("id"),
                "title": e.get("title") or e.get("id") or f"Mục {i}",
                "duration": e.get("duration"),
                "thumbnail": thumb,
                "url": e.get("webpage_url") or e.get("url"),
            })
        if not result["thumbnail"] and result["entries"]:
            result["thumbnail"] = result["entries"][0]["thumbnail"]
        # gộp chất lượng của các mục (nếu đã được trích đầy đủ, vd. story)
        heights = set()
        for e in entries:
            for f in e.get("formats") or []:
                if f.get("height") and f.get("vcodec") != "none":
                    heights.add(int(f["height"]))
        result["heights"] = sorted(heights, reverse=True)
        return result

    formats = info.get("formats") or [info]
    best_audio = 0
    for f in formats:
        if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none"):
            best_audio = max(best_audio, f.get("filesize") or f.get("filesize_approx") or 0)
    by_h: dict[int, dict] = {}
    for f in formats:
        h = f.get("height")
        if not h or f.get("vcodec") == "none":
            continue
        size = f.get("filesize") or f.get("filesize_approx") or 0
        if f.get("acodec") == "none" and size:
            size += best_audio
        cur = by_h.get(h)
        if not cur or (size and size > cur["size"]):
            by_h[int(h)] = {"height": int(h), "size": size, "fps": f.get("fps")}
    result["heights"] = [
        {"height": v["height"], "size": human_size(v["size"]), "fps": v["fps"]}
        for v in sorted(by_h.values(), key=lambda x: -x["height"])
    ]
    result["has_video"] = bool(by_h) or not any(f.get("vcodec") == "none" for f in formats)

    def sub_list(d: dict, auto: bool) -> list[dict]:
        out = []
        for code, items in (d or {}).items():
            if code in ("live_chat", "rechat") or not items:
                continue
            name = next((it.get("name") for it in items if it.get("name")), code)
            out.append({"code": code, "name": name, "auto": auto,
                        "exts": sorted({it.get("ext") for it in items if it.get("ext")})})
        return out

    result["subtitles"] = sub_list(info.get("subtitles"), False)
    autos = sub_list(info.get("automatic_captions"), True)
    # ưu tiên ngôn ngữ gốc (YouTube đánh dấu "-orig") và vi/en lên đầu
    pri = {"vi": 0, "en": 1}

    def ak(s):
        if s["code"].endswith("-orig"):
            return (-1, s["name"])
        return (pri.get(s["code"], 9), s["name"])

    result["auto_subtitles"] = sorted(autos, key=ak)
    result["subtitles"].sort(key=lambda s: (pri.get(s["code"].split("-")[0], 9), s["name"]))
    return result


# --------------------------------------------------------------------------- #
#  Routes
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/manifest.webmanifest")
def manifest():
    return send_from_directory(STATIC_DIR, "manifest.webmanifest", mimetype="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    resp = send_from_directory(STATIC_DIR, "sw.js", mimetype="text/javascript")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.post("/api/info")
def api_info():
    body = request.get_json(force=True) or {}
    url = clean_url(body.get("url", ""))
    if not url.startswith(("http://", "https://")):
        return jsonify(error="Link không hợp lệ. Hãy dán link bắt đầu bằng http(s)://"), 400
    opts = base_opts(url, body.get("use_cookies", True))
    opts["extract_flat"] = "in_playlist"
    opts["skip_download"] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            info = ydl.sanitize_info(info)
        return jsonify(summarize_info(info, url))
    except Exception as e:  # noqa: BLE001
        return jsonify(error=friendly_error(str(e))), 400


@app.post("/api/download")
def api_download():
    body = request.get_json(force=True) or {}
    urls = body.get("urls") or [body.get("url", "")]
    options = body.get("options") or {}
    created = []
    for raw in urls:
        url = clean_url(raw)
        if not url.startswith(("http://", "https://")):
            continue
        opt = dict(options)
        if len(urls) > 1:
            opt.pop("title", None)
            opt.pop("thumbnail", None)
        job = Job(url, opt)
        with JOBS_LOCK:
            JOBS[job.id] = job
        threading.Thread(target=run_job, args=(job,), daemon=True).start()
        created.append(job.to_dict())
    if not created:
        return jsonify(error="Không có link hợp lệ."), 400
    return jsonify(jobs=created)


@app.get("/api/jobs")
def api_jobs():
    with JOBS_LOCK:
        data = [j.to_dict() for j in sorted(JOBS.values(), key=lambda x: -x.created)]
    return jsonify(jobs=data)


@app.post("/api/jobs/<jid>/cancel")
def api_cancel(jid):
    job = JOBS.get(jid)
    if not job:
        abort(404)
    job.cancel.set()
    if job.status == "queued":
        job.status = "cancelled"
    return jsonify(ok=True)


@app.post("/api/jobs/<jid>/retry")
def api_retry(jid):
    old = JOBS.get(jid)
    if not old:
        abort(404)
    opt = dict(old.options)
    opt.setdefault("title", old.title)
    opt.setdefault("thumbnail", old.thumbnail)
    opt.setdefault("mode", old.mode)
    job = Job(old.url, opt)
    with JOBS_LOCK:
        JOBS.pop(jid, None)
        JOBS[job.id] = job
    threading.Thread(target=run_job, args=(job,), daemon=True).start()
    return jsonify(job=job.to_dict())


@app.delete("/api/jobs/<jid>")
def api_delete_job(jid):
    delete_files = request.args.get("files") == "1"
    job = JOBS.get(jid)
    if not job:
        abort(404)
    job.cancel.set()
    if delete_files:
        root = download_dir()
        for f in job.files:
            try:
                (root / f["path"]).unlink(missing_ok=True)
            except Exception:
                pass
    with JOBS_LOCK:
        JOBS.pop(jid, None)
    save_history()
    return jsonify(ok=True)


@app.post("/api/jobs/clear")
def api_clear_jobs():
    with JOBS_LOCK:
        for jid in [k for k, j in JOBS.items() if j.status in ("done", "error", "cancelled")]:
            JOBS.pop(jid, None)
    save_history()
    return jsonify(ok=True)


def _safe_path(rel: str) -> Path:
    root = download_dir().resolve()
    p = (root / rel).resolve()
    if root != p and root not in p.parents:
        abort(403)
    if not p.exists():
        abort(404)
    return p


@app.get("/api/file")
def api_file():
    p = _safe_path(request.args.get("path", ""))
    as_attachment = request.args.get("dl") == "1"
    return send_file(p, as_attachment=as_attachment, download_name=p.name, conditional=True)


@app.get("/api/file-text")
def api_file_text():
    p = _safe_path(request.args.get("path", ""))
    if p.stat().st_size > 5_000_000:
        return jsonify(error="File quá lớn"), 400
    raw = p.read_text("utf-8", errors="ignore")
    segs = parse_subtitle(raw) if p.suffix.lower() in (".vtt", ".srt") else []
    return jsonify(raw=raw, segments=segs, text=segments_to_text(segs) if segs else raw)


@app.post("/api/open-folder")
def api_open_folder():
    body = request.get_json(silent=True) or {}
    target = download_dir()
    if body.get("path"):
        target = _safe_path(body["path"])
    if IS_ANDROID:
        return jsonify(error=f"Trên Android: mở ứng dụng Tệp / File Manager → {android_visible_path(target)}"), 400
    try:
        system = platform.system()
        if system == "Windows":
            if target.is_file():
                subprocess.Popen(["explorer", "/select,", str(target)])
            else:
                os.startfile(str(target))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", "-R", str(target)] if target.is_file() else ["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target.parent if target.is_file() else target)])
        return jsonify(ok=True)
    except Exception as e:  # noqa: BLE001
        return jsonify(error=str(e)), 500


@app.post("/api/transcript")
def api_transcript():
    """Tải 1 phụ đề vào thư mục tạm và trả về văn bản để xem / copy."""
    body = request.get_json(force=True) or {}
    url = clean_url(body.get("url", ""))
    lang = body.get("lang")
    auto = bool(body.get("auto"))
    if not url or not lang:
        return jsonify(error="Thiếu url hoặc ngôn ngữ"), 400
    tmp = tempfile.mkdtemp(prefix="vidgrab_")
    try:
        opts = base_opts(url, body.get("use_cookies", True))
        opts.update({
            "skip_download": True,
            "noplaylist": True,
            "writesubtitles": not auto,
            "writeautomaticsub": auto,
            "subtitleslangs": [lang],
            "subtitlesformat": "vtt/srt/best",
            "outtmpl": {"default": os.path.join(tmp, "sub.%(ext)s")},
        })
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
        files = [f for f in os.listdir(tmp) if f.endswith((".vtt", ".srt"))]
        if not files:
            return jsonify(error="Không lấy được phụ đề này."), 404
        raw = Path(tmp, files[0]).read_text("utf-8", errors="ignore")
        segs = parse_subtitle(raw)
        return jsonify(segments=segs, text=segments_to_text(segs), lang=lang)
    except Exception as e:  # noqa: BLE001
        return jsonify(error=friendly_error(str(e))), 400
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@app.get("/api/thumb")
def api_thumb():
    """Proxy ảnh thumbnail (Instagram/TikTok chặn hiển thị ảnh từ trang khác)."""
    url = request.args.get("url", "")
    if not url.startswith(("http://", "https://")):
        abort(400)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36",
            "Referer": "",
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read(8_000_000)
            ctype = r.headers.get("Content-Type", "image/jpeg")
        if not ctype.startswith("image/"):
            abort(415)
        return Response(data, mimetype=ctype, headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        abort(502)


# ----- settings & cookies -----
@app.get("/api/settings")
def api_get_settings():
    cookies = {}
    for p in PLATFORMS + ["all"]:
        f = COOKIES_DIR / f"{p}.txt"
        cookies[p] = (
            {"exists": True, "size": human_size(f.stat().st_size),
             "updated": time.strftime("%d/%m/%Y %H:%M", time.localtime(f.stat().st_mtime))}
            if f.exists() else {"exists": False}
        )
    return jsonify(
        settings=SETTINGS,
        cookies=cookies,
        browsers=SUPPORTED_BROWSERS,
        ffmpeg=FFMPEG,
        ytdlp_version=yt_dlp.version.__version__,
        python=sys.version.split()[0],
        os="Android" if IS_ANDROID else platform.system(),
        android=IS_ANDROID,
        apk=IS_APK,
        js_runtime=", ".join(JS_RUNTIMES) or "",
    )


@app.post("/api/settings")
def api_set_settings():
    global _slots
    body = request.get_json(force=True) or {}
    for k in DEFAULT_SETTINGS:
        if k in body:
            SETTINGS[k] = body[k]
    if SETTINGS.get("cookie_browser") not in [""] + SUPPORTED_BROWSERS:
        SETTINGS["cookie_browser"] = ""
    try:
        SETTINGS["max_concurrent"] = max(1, min(10, int(SETTINGS.get("max_concurrent", 3))))
    except (TypeError, ValueError):
        SETTINGS["max_concurrent"] = 3
    _slots = threading.Semaphore(SETTINGS["max_concurrent"])
    try:
        download_dir()
    except Exception as e:  # noqa: BLE001
        return jsonify(error=f"Không tạo được thư mục: {e}"), 400
    save_settings(SETTINGS)
    return api_get_settings()


@app.post("/api/cookies/<plat>")
def api_upload_cookies(plat):
    if plat not in PLATFORMS + ["all"]:
        abort(400)
    content = ""
    if "file" in request.files:
        content = request.files["file"].read().decode("utf-8", errors="ignore")
    else:
        content = (request.get_json(silent=True) or {}).get("content", "")
    content = content.strip()
    if not content:
        return jsonify(error="Nội dung cookie trống"), 400
    if content.startswith("[") or content.startswith("{"):
        content = json_cookies_to_netscape(content)
        if not content:
            return jsonify(error="Không đọc được cookie dạng JSON"), 400
    elif "\t" not in content:
        return jsonify(error="Sai định dạng. Cần file cookies.txt (Netscape) hoặc JSON xuất từ extension."), 400
    if not content.startswith("# Netscape") and not content.startswith("# HTTP Cookie File"):
        content = "# Netscape HTTP Cookie File\n" + content
    (COOKIES_DIR / f"{plat}.txt").write_text(content + "\n", "utf-8")
    return api_get_settings()


@app.delete("/api/cookies/<plat>")
def api_delete_cookies(plat):
    if plat not in PLATFORMS + ["all"]:
        abort(400)
    (COOKIES_DIR / f"{plat}.txt").unlink(missing_ok=True)
    return api_get_settings()


def json_cookies_to_netscape(raw: str) -> str:
    """Chuyển cookie JSON (EditThisCookie / Cookie-Editor) sang định dạng Netscape."""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = data.get("cookies") or [data]
        lines = ["# Netscape HTTP Cookie File"]
        for c in data:
            domain = c.get("domain") or c.get("host") or ""
            if not domain:
                continue
            include_sub = "TRUE" if domain.startswith(".") or not c.get("hostOnly", False) else "FALSE"
            if include_sub == "TRUE" and not domain.startswith("."):
                domain = "." + domain
            exp = c.get("expirationDate") or c.get("expires") or c.get("expiry") or 0
            try:
                exp = int(float(exp))
            except (TypeError, ValueError):
                exp = 0
            lines.append("\t".join([
                domain, include_sub, c.get("path", "/"),
                "TRUE" if c.get("secure") else "FALSE", str(max(exp, 0)),
                c.get("name", ""), str(c.get("value", "")),
            ]))
        return "\n".join(lines) if len(lines) > 1 else ""
    except Exception:
        return ""


def update_ytdlp_wheel() -> tuple[bool, str, str]:
    """APK không có pip: tải bản wheel yt-dlp mới nhất từ PyPI vào DATA_DIR/updates.
    Lần khởi động sau, wheel được đặt đầu sys.path (Python import thẳng từ file .whl/zip)."""
    import hashlib

    with urllib.request.urlopen("https://pypi.org/pypi/yt-dlp/json", timeout=30) as r:
        meta = json.load(r)
    latest = meta["info"]["version"]
    if latest == yt_dlp.version.__version__:
        return True, f"Đang dùng bản mới nhất ({latest}).", ""
    wheel = next(u for u in meta["urls"] if u["filename"].endswith("-py3-none-any.whl"))
    with urllib.request.urlopen(wheel["url"], timeout=120) as r:
        data = r.read()
    if hashlib.sha256(data).hexdigest() != wheel["digests"]["sha256"]:
        return False, "File tải về bị lỗi (sai checksum), hãy thử lại.", ""
    upd = DATA_DIR / "updates"
    upd.mkdir(exist_ok=True)
    tmp = upd / "yt_dlp.whl.tmp"
    tmp.write_bytes(data)
    os.replace(tmp, upd / "yt_dlp.whl")
    return True, f"Đã tải yt-dlp {latest}. Hãy thoát hẳn VidGrab rồi mở lại để áp dụng.", wheel["filename"]


@app.post("/api/update-ytdlp")
def api_update():
    if IS_APK:
        try:
            ok, msg, out = update_ytdlp_wheel()
            return jsonify(ok=ok, message=msg, output=out)
        except Exception as e:  # noqa: BLE001
            return jsonify(ok=False, message=f"Cập nhật thất bại: {e}"), 500
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U",
             *(["yt-dlp", "yt-dlp-ejs"] if IS_ANDROID else ["yt-dlp[default]"])],
            capture_output=True, text=True, timeout=300,
        )
        ok = out.returncode == 0
        tail = (out.stdout + out.stderr).strip().splitlines()[-6:]
        return jsonify(ok=ok, output="\n".join(tail),
                       message="Đã cập nhật. Hãy khởi động lại VidGrab để áp dụng." if ok else "Cập nhật thất bại.")
    except Exception as e:  # noqa: BLE001
        return jsonify(ok=False, message=str(e)), 500


# --------------------------------------------------------------------------- #
def lan_ip() -> str:
    import socket

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def open_browser(url: str) -> None:
    if IS_ANDROID and shutil.which("termux-open-url"):
        subprocess.Popen(["termux-open-url", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(url)


def main():
    load_history()
    host = os.environ.get("VIDGRAB_HOST", "127.0.0.1")
    port = int(os.environ.get("VIDGRAB_PORT", "8686"))
    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '') else host}:{port}"
    print("=" * 56)
    print("  VidGrab đang chạy tại:", url)
    if host in ("0.0.0.0", "") and lan_ip():
        print(f"  Từ điện thoại (cùng Wi-Fi):  http://{lan_ip()}:{port}")
    print("  Thư mục tải về:", download_dir())
    print("  ffmpeg:", FFMPEG or "KHÔNG TÌM THẤY (cần để ghép video HD / mp3)")
    print("  JS runtime (YouTube):", ", ".join(JS_RUNTIMES) or "KHÔNG CÓ (cài deno hoặc nodejs)")
    print("  Nhấn Ctrl+C để thoát")
    print("=" * 56)
    if os.environ.get("VIDGRAB_NO_BROWSER") != "1":
        threading.Timer(1.2, lambda: open_browser(url)).start()
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
