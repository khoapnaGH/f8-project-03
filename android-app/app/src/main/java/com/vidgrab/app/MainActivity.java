package com.vidgrab.app;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.MimeTypeMap;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import java.io.File;
import java.io.FileInputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends Activity {
    private static final String BASE = "http://127.0.0.1:" + VidGrabService.PORT + "/";
    private static final int REQ_FILE = 10;
    private static final int REQ_PERMS = 11;

    private WebView web;
    private View loading;
    private TextView loadingText;
    private ValueCallback<Uri[]> fileCallback;
    private WebChromeClient chrome;
    private View fullscreenView;
    private boolean serverReady = false;
    private String pendingUrl = null;
    private final Handler ui = new Handler(Looper.getMainLooper());

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        getWindow().setStatusBarColor(Color.parseColor("#0b0b14"));
        getWindow().setNavigationBarColor(Color.parseColor("#0b0b14"));

        web = findViewById(R.id.web);
        loading = findViewById(R.id.loading);
        loadingText = findViewById(R.id.loading_text);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setSupportMultipleWindows(false);
        web.setBackgroundColor(Color.parseColor("#0b0b14"));
        web.addJavascriptInterface(new JsBridge(), "VidGrabAndroid");

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                Uri u = req.getUrl();
                if ("127.0.0.1".equals(u.getHost())) return false;
                // link ngoài (link gốc, hướng dẫn…) mở bằng trình duyệt / app tương ứng
                openExternal(u);
                return true;
            }
        });
        chrome = new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = cb;
                Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType("*/*");
                try {
                    startActivityForResult(Intent.createChooser(i, "Chọn file cookie"), REQ_FILE);
                } catch (ActivityNotFoundException e) {
                    fileCallback = null;
                    return false;
                }
                return true;
            }

            @Override
            public void onShowCustomView(View view, CustomViewCallback callback) {
                fullscreenView = view;
                ((FrameLayout) getWindow().getDecorView()).addView(view,
                        new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                                ViewGroup.LayoutParams.MATCH_PARENT));
                getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
            }

            @Override
            public void onHideCustomView() {
                if (fullscreenView != null) {
                    ((FrameLayout) getWindow().getDecorView()).removeView(fullscreenView);
                    fullscreenView = null;
                }
                getWindow().clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
            }
        };
        web.setWebChromeClient(chrome);

        requestNeededPermissions();
        startVidGrabService();
        handleIntent(getIntent());
        waitForServer();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    /** Link được chia sẻ từ TikTok / Facebook / Instagram / YouTube → tự phân tích. */
    private void handleIntent(Intent intent) {
        if (intent == null) return;
        String text = null;
        if (Intent.ACTION_SEND.equals(intent.getAction())) {
            text = intent.getStringExtra(Intent.EXTRA_TEXT);
        } else if (Intent.ACTION_VIEW.equals(intent.getAction()) && intent.getData() != null) {
            text = intent.getData().toString();
        }
        if (text == null || text.trim().isEmpty()) return;
        String url;
        try {
            url = BASE + "?url=" + URLEncoder.encode(text.trim(), "UTF-8");
        } catch (Exception e) {
            return;
        }
        if (serverReady) web.loadUrl(url);
        else pendingUrl = url;
    }

    private void startVidGrabService() {
        Intent svc = new Intent(this, VidGrabService.class);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(svc);
        else startService(svc);
    }

    /** Chờ máy chủ Python sẵn sàng (lần đầu mất vài giây để giải nén) rồi mới tải giao diện. */
    private void waitForServer() {
        new Thread(() -> {
            long start = System.currentTimeMillis();
            while (System.currentTimeMillis() - start < 90_000) {
                try (Socket sock = new Socket()) {
                    sock.connect(new InetSocketAddress("127.0.0.1", VidGrabService.PORT), 500);
                    ui.post(this::onServerReady);
                    return;
                } catch (Exception ignored) {
                }
                String err = readStartupError();
                if (err != null) {
                    ui.post(() -> loadingText.setText("Không khởi động được VidGrab:\n\n" + err));
                    return;
                }
                long secs = (System.currentTimeMillis() - start) / 1000;
                if (secs > 6) {
                    ui.post(() -> loadingText.setText(
                            "Đang khởi động VidGrab…\n(lần đầu mở có thể mất tới 30 giây)"));
                }
                try {
                    Thread.sleep(400);
                } catch (InterruptedException e) {
                    return;
                }
            }
            ui.post(() -> loadingText.setText("VidGrab khởi động quá lâu. Hãy thoát app và mở lại."));
        }).start();
    }

    private String readStartupError() {
        File f = new File(new File(getFilesDir(), "vidgrab"), "startup_error.txt");
        if (!f.exists()) return null;
        try (FileInputStream in = new FileInputStream(f)) {
            byte[] b = new byte[(int) Math.min(f.length(), 4000)];
            int n = in.read(b);
            return new String(b, 0, Math.max(n, 0), StandardCharsets.UTF_8);
        } catch (Exception e) {
            return "(không đọc được chi tiết lỗi)";
        }
    }

    private void onServerReady() {
        serverReady = true;
        web.loadUrl(pendingUrl != null ? pendingUrl : BASE);
        pendingUrl = null;
        web.setVisibility(View.VISIBLE);
        loading.setVisibility(View.GONE);
    }

    private void requestNeededPermissions() {
        List<String> perms = new ArrayList<>();
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS);
        }
        if (Build.VERSION.SDK_INT <= 29
                && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            perms.add(Manifest.permission.WRITE_EXTERNAL_STORAGE);
        }
        if (!perms.isEmpty()) requestPermissions(perms.toArray(new String[0]), REQ_PERMS);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQ_FILE && fileCallback != null) {
            Uri[] result = null;
            if (resultCode == RESULT_OK && data != null && data.getData() != null) {
                result = new Uri[]{data.getData()};
            }
            fileCallback.onReceiveValue(result);
            fileCallback = null;
        }
    }

    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() {
        if (fullscreenView != null) {
            chrome.onHideCustomView();
        } else if (web.canGoBack()) {
            web.goBack();
        } else {
            moveTaskToBack(true); // giữ VidGrab chạy nền để tải tiếp
        }
    }

    private void openExternal(Uri u) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, u));
        } catch (ActivityNotFoundException e) {
            Toast.makeText(this, "Không có ứng dụng nào mở được link này", Toast.LENGTH_SHORT).show();
        }
    }

    private Uri contentUri(File f) {
        return FileProvider.getUriForFile(this, getPackageName() + ".files", f);
    }

    private static String mimeOf(File f) {
        String name = f.getName();
        int dot = name.lastIndexOf('.');
        String ext = dot >= 0 ? name.substring(dot + 1).toLowerCase() : "";
        String m = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);
        if (m == null) {
            if (ext.equals("srt") || ext.equals("vtt")) m = "text/plain";
            else if (ext.equals("opus")) m = "audio/ogg";
            else m = "*/*";
        }
        return m;
    }

    /** Hàm cho giao diện web gọi: window.VidGrabAndroid.xxx() */
    class JsBridge {
        @JavascriptInterface
        public String getClipboard() {
            ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (cm == null || !cm.hasPrimaryClip()) return "";
            ClipData clip = cm.getPrimaryClip();
            if (clip == null || clip.getItemCount() == 0) return "";
            CharSequence t = clip.getItemAt(0).coerceToText(MainActivity.this);
            return t == null ? "" : t.toString();
        }

        @JavascriptInterface
        public void openFile(String path) {
            ui.post(() -> {
                File f = new File(path);
                if (!f.exists()) {
                    Toast.makeText(MainActivity.this, "Không tìm thấy file", Toast.LENGTH_SHORT).show();
                    return;
                }
                Intent i = new Intent(Intent.ACTION_VIEW);
                i.setDataAndType(contentUri(f), mimeOf(f));
                i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                try {
                    startActivity(Intent.createChooser(i, "Mở bằng"));
                } catch (ActivityNotFoundException e) {
                    Toast.makeText(MainActivity.this, "Không có ứng dụng mở được file này", Toast.LENGTH_SHORT).show();
                }
            });
        }

        @JavascriptInterface
        public void shareFile(String path) {
            ui.post(() -> {
                File f = new File(path);
                if (!f.exists()) return;
                Intent i = new Intent(Intent.ACTION_SEND);
                i.setType(mimeOf(f));
                i.putExtra(Intent.EXTRA_STREAM, contentUri(f));
                i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                startActivity(Intent.createChooser(i, "Chia sẻ"));
            });
        }

        @JavascriptInterface
        public void openUrl(String url) {
            ui.post(() -> openExternal(Uri.parse(url)));
        }

        @JavascriptInterface
        public void exitApp() {
            ui.post(() -> startService(new Intent(MainActivity.this, VidGrabService.class)
                    .setAction(VidGrabService.ACTION_STOP)));
        }
    }
}
