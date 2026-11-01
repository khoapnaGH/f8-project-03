"""
Khởi động VidGrab bên trong APK (Chaquopy).
Java gọi serve(config_json) trong một thread nền; hàm này chạy server Flask tại 127.0.0.1:8686.
"""
import json
import os
import shutil
import stat
import sys
import traceback
import zipfile

PORT = 8686


def _extract_libs(native_dir: str, files_dir: str, name: str, only_shared_libs: bool = False) -> str:
    """lib<name>.zip.so (từ youtubedl-android) chứa các thư viện .so kèm symlink.
    Giải nén một lần vào files/<name>/, trả về thư mục lib để đặt LD_LIBRARY_PATH.
    only_shared_libs: chỉ lấy usr/lib/*.so* (bỏ thư viện chuẩn Python không dùng tới)."""
    src = os.path.join(native_dir, f"lib{name}.zip.so")
    dst = os.path.join(files_dir, name)
    libdir = os.path.join(dst, "usr", "lib")
    if not os.path.exists(src):
        return ""
    sig = f"{os.path.getsize(src)}-{int(os.path.getmtime(src))}"
    marker = os.path.join(dst, ".extracted")
    try:
        with open(marker) as f:
            if f.read() == sig:
                return libdir
    except OSError:
        pass

    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    with zipfile.ZipFile(src) as z:
        for info in z.infolist():
            if only_shared_libs and not (info.filename.startswith("usr/lib/lib") and ".so" in info.filename):
                continue
            target = os.path.join(dst, info.filename)
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                link = z.read(info).decode()
                if os.path.lexists(target):
                    os.remove(target)
                os.symlink(link, target)
            else:
                with z.open(info) as fsrc, open(target, "wb") as fdst:
                    shutil.copyfileobj(fsrc, fdst)
    with open(marker, "w") as f:
        f.write(sig)
    return libdir


def serve(config_json: str) -> None:
    cfg = json.loads(config_json)
    data_dir = cfg["data_dir"]
    os.makedirs(data_dir, exist_ok=True)
    err_file = os.path.join(data_dir, "startup_error.txt")
    try:
        if os.path.exists(err_file):
            os.remove(err_file)

        os.environ.update({
            "VIDGRAB_APK": "1",
            "VIDGRAB_NO_BROWSER": "1",
            "VIDGRAB_DATA_DIR": data_dir,
            "VIDGRAB_STATIC_DIR": cfg["static_dir"],
            "VIDGRAB_DOWNLOAD_DIR": cfg["download_dir"],
            "VIDGRAB_STAGING_DIR": cfg["staging_dir"],
        })
        os.environ.setdefault("HOME", cfg["files_dir"])

        # ffmpeg / ffprobe / QuickJS đi kèm app (từ youtubedl-android).
        # Thư viện phụ (libc++_shared, libcrypto…) nằm trong gói python của họ.
        native = cfg["native_lib_dir"]
        try:
            libdirs = [
                _extract_libs(native, cfg["files_dir"], "ffmpeg"),
                _extract_libs(native, cfg["files_dir"], "python", only_shared_libs=True),
            ]
            old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join([d for d in libdirs if d] + ([old] if old else []))
            ff = os.path.join(native, "libffmpeg.so")
            if os.path.exists(ff):
                os.environ["VIDGRAB_FFMPEG"] = ff
            qjs = os.path.join(native, "libqjs.so")
            if os.path.exists(qjs):
                os.environ["VIDGRAB_QJS"] = qjs   # để yt-dlp giải mã link YouTube
        except Exception:
            traceback.print_exc()

        # bản yt-dlp mới tải qua nút "Cập nhật yt-dlp" (wheel = file zip, import thẳng được)
        whl = os.path.join(data_dir, "updates", "yt_dlp.whl")
        if os.path.exists(whl):
            try:
                with zipfile.ZipFile(whl) as z:
                    z.testzip()
                sys.path.insert(0, whl)
            except Exception:
                os.remove(whl)

        import app as vidgrab  # app.py dùng chung với bản máy tính

        vidgrab.load_history()
        print("VidGrab: ffmpeg =", vidgrab.FFMPEG, "| yt-dlp =", vidgrab.yt_dlp.version.__version__)

        from werkzeug.serving import make_server

        server = make_server("127.0.0.1", PORT, vidgrab.app, threaded=True)
        server.serve_forever()
    except Exception:
        with open(err_file, "w") as f:
            f.write(traceback.format_exc())
        raise
