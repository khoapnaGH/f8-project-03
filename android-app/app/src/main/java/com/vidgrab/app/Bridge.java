package com.vidgrab.app;

import android.content.Context;
import android.media.MediaScannerConnection;

import java.util.List;

/** Các hàm tĩnh mà Python (app.py) gọi qua Chaquopy: jclass("com.vidgrab.app.Bridge"). */
public final class Bridge {
    static volatile Context appContext;

    private Bridge() {}

    /** Báo cho Android biết có file mới để hiện ngay trong Thư viện ảnh / Nhạc. */
    public static void scanFiles(List<String> paths) {
        Context ctx = appContext;
        if (ctx == null || paths == null || paths.isEmpty()) return;
        MediaScannerConnection.scanFile(ctx, paths.toArray(new String[0]), null, null);
    }
}
