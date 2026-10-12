# 🦖 DinoFetch v2.0

Download **YouTube / Instagram / Facebook** as **Video (MP4)** or **Audio (MP3)**.
Runs as a Windows `.exe` — same engine, same UI. Android APK automation is paused for now.

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

`app.py` is the same engine as a small web server, handy for grabbing files
from your phone:

```bat
python app.py
```

It prints a LAN address (`http://192.168.1.5:5000`) for phones on the same WiFi.

## 🤖 Android — paused for now

There is **no Android APK build enabled right now**. The current GitHub
automation builds/releases only the Windows EXE.

The Android source files are still in the repo for later (`android/`,
`app.py`, `media_downloader.py`, `templates/`, `static/`). If you want the
same download engine on a phone today, use **Phone browser access (optional)**
above over the same WiFi.

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
android/                future APK entry point + buildozer config
.github/workflows/      Windows EXE automation
DinoFetch.spec          PyInstaller build recipe
build_exe.bat           one-click exe build
```

## ⚖️ Notes

Personal / fair-use only. Respect the ToS and copyright of YouTube, Instagram and
Facebook. ffmpeg is bundled via `imageio-ffmpeg` in the Windows build.