"""
DinoFetch — Android entry point.

The python-for-android `webview` bootstrap runs this file, pings
http://127.0.0.1:5000 until it answers, then shows it in a native WebView.
So: start the same Flask server the desktop build uses, on the port the
bootstrap was built with, and stay in the foreground.
"""
import os
import sys

PORT = 5000

# The bootstrap runs us from the app's private dir and passes it in ANDROID_ARGUMENT.
APP_ROOT = (os.environ.get("ANDROID_ARGUMENT")
            or os.environ.get("ANDROID_APP_PATH")
            or os.path.dirname(os.path.abspath(__file__)))

if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)
os.chdir(APP_ROOT)

from app import app as flask_app  # noqa: E402  (path must be set up first)
from media_downloader import PLATFORM_FOLDERS  # noqa: E402


def main():
    for folder in PLATFORM_FOLDERS.values():
        os.makedirs(folder, exist_ok=True)
    print("DinoFetch serving http://127.0.0.1:%d from %s" % (PORT, APP_ROOT), flush=True)
    # werkzeug's dev server is fine here: single user, loopback only
    flask_app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()