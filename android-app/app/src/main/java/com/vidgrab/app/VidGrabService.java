package com.vidgrab.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.content.res.AssetManager;
import android.os.Build;
import android.os.Environment;
import android.os.IBinder;
import android.util.Log;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Dịch vụ chạy nền giữ cho máy chủ VidGrab (Python + yt-dlp) sống
 * kể cả khi bạn chuyển sang app khác trong lúc đang tải.
 */
public class VidGrabService extends Service {
    static final String TAG = "VidGrab";
    static final int PORT = 8686;
    static final String ACTION_STOP = "com.vidgrab.app.STOP";
    private static final String CHANNEL = "vidgrab";
    private static volatile boolean serverStarted = false;

    @Override
    public void onCreate() {
        super.onCreate();
        Bridge.appContext = getApplicationContext();
        goForeground();
        startServer(this);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopForeground(true);
            stopSelf();
            // tắt hẳn tiến trình (Python không dừng được giữa chừng)
            android.os.Process.killProcess(android.os.Process.myPid());
            return START_NOT_STICKY;
        }
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void goForeground() {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "VidGrab đang chạy",
                    NotificationManager.IMPORTANCE_LOW);
            ch.setShowBadge(false);
            nm.createNotificationChannel(ch);
        }
        int piFlags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;
        PendingIntent open = PendingIntent.getActivity(this, 0,
                new Intent(this, MainActivity.class), piFlags);
        PendingIntent stop = PendingIntent.getService(this, 1,
                new Intent(this, VidGrabService.class).setAction(ACTION_STOP), piFlags);

        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL) : new Notification.Builder(this);
        b.setSmallIcon(R.drawable.ic_stat_download)
                .setContentTitle("VidGrab đang chạy")
                .setContentText("Chạm để mở · tải video vẫn tiếp tục khi bạn rời app")
                .setContentIntent(open)
                .setOngoing(true)
                .addAction(new Notification.Action.Builder(null, "Thoát", stop).build());
        Notification n = b.build();
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        } else {
            startForeground(1, n);
        }
    }

    static File downloadDir() {
        return new File(Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS), "VidGrab");
    }

    static synchronized void startServer(Context ctx) {
        if (serverStarted) return;
        serverStarted = true;
        final Context app = ctx.getApplicationContext();
        new Thread(() -> {
            try {
                File web = new File(app.getFilesDir(), "web");
                copyAssets(app.getAssets(), "web", web);

                File dl = downloadDir();
                //noinspection ResultOfMethodCallIgnored
                dl.mkdirs();
                File staging = new File(app.getExternalCacheDir() != null
                        ? app.getExternalCacheDir() : app.getCacheDir(), "staging");

                JSONObject cfg = new JSONObject();
                cfg.put("data_dir", new File(app.getFilesDir(), "vidgrab").getAbsolutePath());
                cfg.put("static_dir", web.getAbsolutePath());
                cfg.put("download_dir", dl.getAbsolutePath());
                cfg.put("staging_dir", staging.getAbsolutePath());
                cfg.put("files_dir", app.getFilesDir().getAbsolutePath());
                cfg.put("native_lib_dir", app.getApplicationInfo().nativeLibraryDir);

                if (!Python.isStarted()) Python.start(new AndroidPlatform(app));
                Python.getInstance().getModule("vidgrab_android").callAttr("serve", cfg.toString());
            } catch (Throwable t) {
                Log.e(TAG, "Không khởi động được VidGrab", t);
                serverStarted = false;
            }
        }, "vidgrab-server").start();
    }

    /** Sao chép giao diện web từ APK ra bộ nhớ app (làm mới mỗi lần chạy để luôn khớp bản APK). */
    private static void copyAssets(AssetManager am, String path, File dest) throws IOException {
        String[] list = am.list(path);
        if (list == null || list.length == 0) {
            //noinspection ResultOfMethodCallIgnored
            dest.getParentFile().mkdirs();
            try (InputStream in = am.open(path); OutputStream out = new FileOutputStream(dest)) {
                byte[] buf = new byte[16384];
                int n;
                while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            }
            return;
        }
        //noinspection ResultOfMethodCallIgnored
        dest.mkdirs();
        for (String name : list) copyAssets(am, path + "/" + name, new File(dest, name));
    }
}
