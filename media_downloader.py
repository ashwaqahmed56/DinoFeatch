"""
Core downloader for YouTube / Instagram / Facebook.
- Auto-detects platform from URL
- Separate folders: downloads/youtube, downloads/instagram, downloads/facebook
- Mode: audio (mp3) or video (mp4)
- Used by the web app (app.py), the terminal CLI (download.py) and the Android build
"""
import os
import re
import shutil
import sys

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import yt_dlp
except ImportError:
    print("ERROR: yt-dlp not installed. Run: pip install -r requirements.txt")
    raise


def _bundle_dir() -> str:
    """Temp unpack dir of a PyInstaller one-file build."""
    return getattr(sys, "_MEIPASS", "") or ""


def _app_dir() -> str:
    """
    Folder that owns the user's data. Never the bundle temp dir: a one-file
    build unpacks to a temp folder that is wiped on exit, and it may be read-only.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _writable(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".dinofetch_write_test")
        with open(probe, "w") as fh:
            fh.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def _resolve_base_dir() -> str:
    """downloads/ next to the app; falls back to the user profile if not writable."""
    base = os.path.join(_app_dir(), "downloads")
    if _writable(base):
        return base
    # Android / locked-down dirs: the app's private files dir is the safe spot.
    home = os.environ.get("HOME") or os.path.expanduser("~")
    fallback = os.path.join(home, "DinoFetch", "downloads")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def _find_ffmpeg():
    """ffmpeg bundled with the exe, provided by imageio-ffmpeg, or on PATH."""
    env = os.environ.get("IMAGEIO_FFMPEG_EXE")  # set by PyInstaller's imageio-ffmpeg hook
    candidates = [env, os.path.join(_bundle_dir(), "ffmpeg"), shutil.which("ffmpeg")]
    for cand in candidates:
        if cand and os.path.exists(cand):
            return cand
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


FFMPEG_EXE = _find_ffmpeg()
if FFMPEG_EXE:
    ffmpeg_dir = os.path.dirname(os.path.abspath(FFMPEG_EXE))
    if ffmpeg_dir and ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

BASE_DIR = _resolve_base_dir()

PLATFORM_FOLDERS = {
    "youtube": os.path.join(BASE_DIR, "youtube"),
    "instagram": os.path.join(BASE_DIR, "instagram"),
    "facebook": os.path.join(BASE_DIR, "facebook"),
}


# ---------- platform detection ----------

def detect_platform(url: str) -> str:
    u = url.lower()
    if "instagram.com" in u:
        return "instagram"
    if "facebook.com" in u or "fb.watch" in u or "fb.com" in u:
        return "facebook"
    if "youtube.com" in u or "youtu.be" in u or "music.youtube.com" in u:
        return "youtube"
    return "unknown"


def get_output_folder(platform: str, base: str | None = None) -> str:
    if base:
        # keep separate subfolders even with custom base
        folder = os.path.join(os.path.abspath(base), platform)
    else:
        folder = PLATFORM_FOLDERS.get(platform, os.path.join(BASE_DIR, platform))
    os.makedirs(folder, exist_ok=True)
    return folder


# ---------- progress ----------

class _SilentLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        # only real errors surface; yt-dlp warnings stay hidden
        pass


def make_progress_hook(callback=None):
    def hook(d):
        try:
            if callback:
                status = d.get("status")
                if status == "downloading":
                    pct = d.get("_percent_str", "").strip()
                    try:
                        pct_f = float(pct.replace("%", "").strip())
                    except Exception:
                        pct_f = None
                    callback({"status": "downloading", "percent": pct_f,
                              "filename": os.path.basename(d.get("filename", ""))})
                elif status == "finished":
                    callback({"status": "processing",
                              "filename": os.path.basename(d.get("filename", ""))})
        except Exception:
            pass
    return hook


# ---------- main download ----------

def short_name(title: str, vid_id: str = "", max_len: int = 60) -> str:
    """Windows-safe short filename base (no template fields)."""
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", title or "").strip()
    name = re.sub(r"\s+", " ", name)
    if not name:
        name = vid_id or "video"
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name


def download(url: str, platform: str | None = None, mode: str = "audio",
             quality: str = "192", output_base: str | None = None,
             start: int | None = None, end: int | None = None,
             cookies: str | None = None, cookies_from_browser: str | None = None,
             progress_callback=None,
             quiet: bool = False) -> dict:
    """
    Download url as audio(mp3) or video(mp4).
    Returns dict: {success, platform, mode, folder, files}
    """
    url = url.strip()
    if not url:
        return {"success": False, "error": "Empty URL"}

    platform = (platform or "auto").lower()
    if platform == "auto":
        platform = detect_platform(url)
        if platform == "unknown":
            # default to youtube extractor (yt-dlp handles many sites)
            platform = "youtube"

    mode = mode.lower()
    if mode not in ("audio", "video"):
        mode = "audio"

    folder = get_output_folder(platform, output_base)

    if str(quality).lower() == "best":
        quality = "320"

    os.makedirs(folder, exist_ok=True)
    before = set(os.listdir(folder))

    if mode == "audio":
        outtmpl = os.path.join(folder, "%(playlist_index)03d - %(title)s.%(ext)s")
        if FFMPEG_EXE:
            postprocessors = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                 "preferredquality": str(quality)},
                {"key": "FFmpegMetadata", "add_chapters": True, "add_metadata": True},
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
                {"key": "EmbedThumbnail"},
            ]
            ydl_format = "bestaudio/best"
            post_args = {"FFmpegExtractAudio": ["-ar", "44100", "-ac", "2"]}
        else:
            # no ffmpeg on this build (e.g. Android): keep the native audio track
            postprocessors = []
            ydl_format = "bestaudio[ext=m4a]/bestaudio/best"
            post_args = {}
        write_thumb = bool(FFMPEG_EXE)
    else:
        # video mp4 — best quality up to 1080p (phone-friendly)
        outtmpl = os.path.join(folder, "%(playlist_index)03d - %(title)s.%(ext)s")
        if FFMPEG_EXE:
            postprocessors = [
                {"key": "FFmpegMetadata", "add_chapters": True, "add_metadata": True},
            ]
            ydl_format = "bv*[height<=1080]+ba/b[height<=1080]/b"
        else:
            # already-muxed progressive files only, nothing to merge
            postprocessors = []
            ydl_format = "best[ext=mp4][height<=1080]/best[ext=mp4]/best"
        post_args = {}
        write_thumb = False

    ydl_opts = {
        "format": ydl_format,
        "outtmpl": outtmpl,
        "ignoreerrors": True,
        "noplaylist": True,
        "continuedl": True,
        "nooverwrites": False,
        "restrictfilenames": False,
        "windowsfilenames": True,
        "writethumbnail": write_thumb,
        "postprocessors": postprocessors,
        "ffmpeg_location": os.path.abspath(FFMPEG_EXE) if FFMPEG_EXE else None,
        "js_runtimes": {"node": {}, "deno": {}, "bun": {}, "quickjs": {}},
        "postprocessor_args": post_args,
        "progress_hooks": [make_progress_hook(progress_callback)],
        "playliststart": start,
        "playlistend": end,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "verbose": False,
        "logger": _SilentLogger(),
        "outtmpl_na_placeholder": "",
        "trim_file_name": 120,
        "merge_output_format": "mp4" if mode == "video" else None,
    }
    if cookies and os.path.exists(cookies):
        ydl_opts["cookiefile"] = cookies
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser, None, None, None)
    ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                if not quiet:
                    print("Failed")
                return {"success": False, "error": "Could not fetch info. Private/login-required?",
                        "platform": platform, "mode": mode, "folder": folder}
            title = info.get("title", url) or url
            if not quiet:
                print(title)
            if info.get("_type") == "playlist":
                # playlist: keep indexed template
                ydl.download([url])
            else:
                # single video/reel: fixed short name (long titles break Windows paths)
                base = short_name(title, info.get("id", ""))
                ydl.params["outtmpl"] = {"default": os.path.join(folder, base + ".%(ext)s")}
                ydl.process_ie_result(info, download=True)

        after = set(os.listdir(folder))
        new_files = sorted([os.path.join(folder, f) for f in (after - before)
                            if f.lower().endswith((".mp3", ".mp4", ".m4a", ".webm"))])
        # fallback: if no new files detected (overwrite), list recent matching
        if not new_files:
            all_media = sorted([os.path.join(folder, f) for f in after
                                if f.lower().endswith((".mp3", ".mp4", ".m4a"))])
            new_files = all_media[-5:] if all_media else []

        if not new_files:
            if not quiet:
                print("Failed")
            return {"success": False, "error": "No file saved. Private or bot-checked? Try again later.",
                    "platform": platform, "mode": mode, "folder": folder}

        if not quiet:
            print("Done")

        return {"success": True, "platform": platform, "mode": mode,
                "folder": folder, "files": new_files, "title": title}
    except Exception as e:
        msg = str(e)
        if not quiet:
            print("Failed")
        return {"success": False, "error": msg, "platform": platform,
                "mode": mode, "folder": folder}


def list_downloads():
    """Return {platform: [files]} for the web app."""
    result = {}
    for plat, folder in PLATFORM_FOLDERS.items():
        files = []
        if os.path.exists(folder):
            for f in sorted(os.listdir(folder)):
                fp = os.path.join(folder, f)
                if os.path.isfile(fp) and f.lower().endswith((".mp3", ".mp4", ".m4a")):
                    files.append({
                        "name": f,
                        "size": os.path.getsize(fp),
                        "size_mb": round(os.path.getsize(fp) / 1024 / 1024, 2),
                    })
        result[plat] = files
    return result