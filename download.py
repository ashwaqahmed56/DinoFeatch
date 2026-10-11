"""
DinoFetch terminal downloader — same engine as the web app, from the console.
Usage:
  python download.py                                  # interactive menu
  python download.py --url URL --mode audio|video     # auto platform
  python download.py --url URL --platform youtube --mode audio --quality 192
  python download.py --url REEL_URL --platform instagram --mode video
"""
import argparse
import os
import sys

from media_downloader import download, detect_platform, list_downloads

# ANSI colors (work on Win10+ terminal)
R = "\033[31m"; G = "\033[32m"; Y = "\033[33m"; B = "\033[34m"
M = "\033[35m"; C = "\033[36m"; W = "\033[37m"; BOLD = "\033[1m"; RST = "\033[0m"

LOGO = f"""{BOLD}{R}▓{Y}▓{G}▓ {W}Dino{R}Fetch{M} Downloader {W}v2{RST}
{BOLD}{C}YouTube {W}| {M}Instagram {W}| {B}Facebook{RST}
{C}Folders: downloads/youtube, downloads/instagram, downloads/facebook{RST}
"""

def cprint(color, msg):
    print(f"{color}{msg}{RST}")

def ask_choice(prompt, options, default=None):
    """options: list of (key, label). Returns key."""
    print(f"\n{BOLD}{prompt}{RST}")
    for i, (k, label) in enumerate(options, 1):
        mark = f" {Y}(default)" if default == k else ""
        print(f"  {C}{i}.{RST} {label}{mark}")
    while True:
        raw = input(f"{Y}Choose [1-{len(options)}]: {RST}").strip()
        if not raw and default:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        # allow typing key directly
        if raw.lower() in [k for k, _ in options]:
            return raw.lower()
        cprint(R, "Invalid choice, try again.")

def interactive():
    print(LOGO)
    print(f"{BOLD}--- New Download ---{RST}")
    url = input(f"{Y}Paste link (YouTube / Insta reel / FB reel): {RST}").strip()
    if not url:
        cprint(R, "No URL given.")
        return
    auto = detect_platform(url)
    print(f"  Detected platform: {BOLD}{auto}{RST}")

    plat = ask_choice("Select platform:", [
        ("auto", f"Auto ({auto})"),
        ("youtube", "🔴 YouTube (video / playlist)"),
        ("instagram", "📸 Instagram Reel"),
        ("facebook", "📘 Facebook Reel / Video"),
    ], default="auto")

    mode = ask_choice("Download as:", [
        ("video", "🎬 Video (MP4)"),
        ("audio", "🎵 Audio (MP3)"),
    ], default="video" if auto in ("instagram", "facebook") else "audio")

    quality = "192"
    if mode == "audio":
        quality = ask_choice("Audio quality:", [
            ("128", "128 kbps (small)"),
            ("192", "192 kbps (recommended)"),
            ("256", "256 kbps"),
            ("320", "320 kbps (best)"),
        ], default="192")

    start = end = None
    if (plat == "youtube" or auto == "youtube") and ("playlist" in url or "list=" in url):
        r = input(f"{Y}Playlist range? e.g. 1-10 or Enter for all: {RST}").strip()
        if r and "-" in r:
            try:
                a, b = r.split("-", 1)
                start, end = int(a.strip()), int(b.strip())
            except ValueError:
                pass

    cookies = None
    if auto in ("instagram", "facebook"):
        cprint(C, "Tip: private reels may need login cookies (cookies.txt from browser export).")
        c = input(f"{Y}Cookies file path (Enter to skip): {RST}").strip()
        if c and os.path.exists(c):
            cookies = c

    print(f"\n{G}{BOLD}Starting download...{RST}")
    res = download(url, platform=plat, mode=mode, quality=quality,
                   start=start, end=end, cookies=cookies)
    if res["success"]:
        cprint(G, "Done")
    else:
        cprint(R, "Failed")


def show_library():
    print(f"\n{BOLD}--- Downloaded Library ---{RST}")
    libs = list_downloads()
    for plat, files in libs.items():
        cprint(C, f"\n📁 {plat} ({len(files)} files):")
        for f in files[-10:]:
            print(f"   - {f['name']} ({f['size_mb']} MB)")
    print()


def main():
    ap = argparse.ArgumentParser(description="DinoFetch: YouTube/Instagram/Facebook downloader")
    ap.add_argument("--url", "-u", help="Media URL")
    ap.add_argument("--platform", "-p", default="auto",
                    choices=["auto", "youtube", "instagram", "facebook"])
    ap.add_argument("--mode", "-m", default="audio", choices=["audio", "video"])
    ap.add_argument("--quality", "-q", default="192",
                    choices=["128", "192", "256", "320", "best"])
    ap.add_argument("--output", "-o", default=None, help="Base output dir (default: downloads/)")
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--cookies", default=None, help="Path to cookies.txt for private reels")
    ap.add_argument("--cookies-from-browser", default=None,
                    help="Read cookies from browser (chrome/edge/firefox) - fixes YouTube bot-check")
    ap.add_argument("--list", action="store_true", help="Show downloaded files and exit")
    args = ap.parse_args()

    if args.list:
        show_library()
        return

    if not args.url:
        # interactive terminal test mode
        while True:
            interactive()
            again = input(f"\n{Y}Download another? (y/n): {RST}").strip().lower()
            if again not in ("y", "yes", ""):
                break
        return

    res = download(args.url, platform=args.platform, mode=args.mode,
                   quality=args.quality, output_base=args.output,
                   start=args.start, end=args.end, cookies=args.cookies,
                   cookies_from_browser=args.cookies_from_browser)
    sys.exit(0 if res["success"] else 1)


if __name__ == "__main__":
    main()
