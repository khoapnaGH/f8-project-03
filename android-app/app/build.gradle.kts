// VidGrab cho Android: WebView hiển thị giao diện web của VidGrab,
// Python (Chaquopy) chạy chính app.py + yt-dlp bên trong app, ffmpeg đi kèm.
plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

val webDir = rootProject.file("../video-downloader")
val buildNumber = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()

android {
    namespace = "com.vidgrab.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.vidgrab.app"
        minSdk = 24
        targetSdk = 35
        versionCode = buildNumber
        versionName = "1.0.$buildNumber"
    }

    // Mỗi loại chip một APK cho nhẹ (điện thoại = arm64; x86_64 cho giả lập).
    // Python 3.12 của Chaquopy chỉ có bản 64-bit nên không có APK cho máy 32-bit (armv7).
    // Chaquopy cần ndk.abiFilters nên dùng product flavor thay cho "splits".
    flavorDimensions += "abi"
    productFlavors {
        create("arm64") {
            dimension = "abi"
            ndk { abiFilters += "arm64-v8a" }
        }
        create("x86_64") {
            dimension = "abi"
            ndk { abiFilters += "x86_64" }
        }
    }

    signingConfigs {
        create("release") {
            storeFile = file(System.getenv("VIDGRAB_KEYSTORE_FILE") ?: "vidgrab-release.jks")
            storePassword = System.getenv("VIDGRAB_KEYSTORE_PASSWORD")
            keyAlias = System.getenv("VIDGRAB_KEY_ALIAS") ?: "vidgrab"
            keyPassword = System.getenv("VIDGRAB_KEY_PASSWORD") ?: System.getenv("VIDGRAB_KEYSTORE_PASSWORD")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("release")
        }
    }

    // giao diện web (index.html, app.js, …) đóng gói vào assets/web/
    sourceSets {
        getByName("main") {
            assets.srcDir(layout.buildDirectory.dir("generated/vidgrab-assets"))
        }
    }

    packaging {
        // giải nén .so ra đĩa để chạy được libffmpeg.so như một chương trình
        jniLibs.useLegacyPackaging = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        buildConfig = true
    }
}

val copyWebAssets by tasks.registering(Copy::class) {
    from(File(webDir, "static"))
    into(layout.buildDirectory.dir("generated/vidgrab-assets/web"))
}
// chỉ lấy app.py (dùng chung với bản máy tính), không kéo theo .venv, cookies…
val copyPythonApp by tasks.registering(Copy::class) {
    from(File(webDir, "app.py"))
    into(layout.buildDirectory.dir("generated/vidgrab-python"))
}
tasks.named("preBuild") { dependsOn(copyWebAssets, copyPythonApp) }

chaquopy {
    defaultConfig {
        version = "3.12"
        pip {
            install("yt-dlp")
            install("yt-dlp-ejs")
            install("flask")
            install("mutagen")
            install("certifi")
        }
    }
    sourceSets {
        getByName("main") {
            srcDir("src/main/python")
            srcDir("build/generated/vidgrab-python")
        }
    }
}

dependencies {
    implementation("androidx.core:core:1.13.1")
    // ffmpeg + ffprobe đã build sẵn cho Android, cùng QuickJS và thư viện phụ (module "library")
    implementation("io.github.junkfood02.youtubedl-android:ffmpeg:0.18.1")
    implementation("io.github.junkfood02.youtubedl-android:library:0.18.1")
}
