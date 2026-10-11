# 🦖 DinoFetch v2.0

Download **YouTube / Instagram / Facebook** as **Video (MP4)** or **Audio (MP3)**.
Runs as a Windows `.exe` or as an Android app — same engine, same UI.

```
downloads/
  youtube/      <- YouTube files
  instagram/    <- Instagram reels
  facebook/     <- Facebook reels
```

## 🪟 Windows — `DinoFetch.exe`

Double-click **`dist\DinoFetch.exe`**. A standalone native window opens — no
browser, no server, no console.

- Paste a link, pick the target (YouTube / Instagram / Facebook), choose
  Video or Audio, set the bitrate for audio, hit **execute**.
- Live progress bar + file name, log line, and a library of everything saved.
- `[open folder]` opens `downloads\` in Explorer. It sits **next to the exe**, so
  move the exe anywhere and it keeps writing beside itself.
- Includes Python, yt-dlp and ffmpeg: nothing to install, nothing to clean up.

**Rebuild the exe** after changing any code:

```bat
build_exe.bat
```

Output: `dist\DinoFetch.exe` (~60 MB, single file).

### Phone browser access (optional)

`app.py` is the same engine as a small web server, still used for the Android app
and handy for grabbing files from your phone:

```bat
python app.py
```

It prints a LAN address (`http://192.168.1.5:5000`) for phones on the same WiFi.

## 🤖 Android — `DinoFetch.apk`

The APK is built in the cloud by GitHub Actions (python-for-android + a native
WebView), because building it needs a Linux toolchain.

1. Push this folder to a GitHub repo. Use `git` (or GitHub Desktop / CLI) rather
   than the browser drag-and-drop, so the hidden `.github/` folder lands with it —
   the workflow **must** exist at `.github/workflows/android-apk.yml`.
2. Open the repo → **Actions** tab. If it says "workflows aren't running yet",
   click *I understand, enable them*.
3. Click **DinoFetch APK → Run workflow** (it also runs on every push to `main`).
4. First run downloads the Android SDK/NDK (~2-3 GB): expect **20-40 min**.
   Later runs use the cache and are much quicker.
5. When it goes green, scroll to the bottom of the run page → **Artifacts →
   DinoFetch-debug-apk** → unzip → `dinofetch-2.0-arm64-v8a-debug.apk`.
6. Copy it to the phone, tap it, allow "install from unknown sources".

The app runs the downloader **on the phone itself** — no PC needed. Files land in
the app's private folder; the app shows the exact path and has an *open folder*
button.

> Android notes:
> - `arm64-v8a` only (any phone from ~2017+). Add `armeabi-v7a` to `android.archs`
>   in `android/buildozer.spec` for older devices.
> - The default build has **no ffmpeg** (it would double the build time), so audio
>   is saved as `.m4a`/`.webm` and video as a progressive `.mp4` (max ~720p).
>   For mp3 + 1080p merging, add `,ffmpeg` to `requirements` in
>   `android/buildozer.spec` — expect a much longer build.
> - Private/age-restricted reels need cookies and are unreliable on Android.

## ⌨️ Terminal version

```bat
python download.py
```

```bat
:: YouTube audio playlist
python download.py --url "https://www.youtube.com/playlist?list=ID" --mode audio --quality 192

:: YouTube video
python download.py --url "https://youtu.be/VIDEO_ID" --mode video

:: Instagram reel
python download.py --url "https://www.instagram.com/reel/XXX/" --platform instagram --mode video

:: Facebook reel
python download.py --url "https://www.facebook.com/reel/XXX" --platform facebook --mode video

:: Private reels (login needed)
python download.py --url "REEL_URL" --platform instagram --mode video --cookies cookies.txt

:: Show the library
python download.py --list
```

> `cookies.txt` comes from the browser extension "Get cookies.txt LOCALLY".

## 🔧 Run from source

```bat
pip install -r requirements.txt
python app.py
```

## 📁 Project layout

```
gui.py                  native Windows app (this is what the exe runs)
app.py                  Flask server (phone + Android build)
media_downloader.py     yt-dlp core: platform detection, formats, output folders
download.py             terminal front-end
templates/index.html    web UI (phone / Android)
static/                 PWA manifest, service worker, icons
android/                APK entry point + buildozer config
.github/workflows/      cloud APK build
DinoFetch.spec          PyInstaller build recipe
build_exe.bat           one-click exe build
```

## ⚖️ Notes

Personal / fair-use only. Respect the ToS and copyright of YouTube, Instagram and
Facebook. ffmpeg is bundled via `imageio-ffmpeg` in the Windows build; the Android
build falls back to non-converting formats when ffmpeg is absent.