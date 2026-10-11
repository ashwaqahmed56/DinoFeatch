[app]

# (str) Title of your application
title = DinoFetch

# (str) Package name
package.name = dinofetch

# (str) Package domain (needed for android/ios packaging)
package.domain = org.dinofetch

# (str) Source code where the main.py live (the workflow copies the shared
# python files + templates/ + static/ in here before building)
source.dir = .

# (str) File extensions to include — the web UI is not Python
source.include_exts = py,html,js,webmanifest,png,ico,css,json

# (str) Application versioning (method 1)
version = 2.0

# (list) Application requirements
#   python3 + flask  -> python-for-android automatically picks the `webview`
#                       bootstrap (native WebView, no Kivy/SDL needed)
#   Everything below must be a pure-python wheel: p4a can pip-install those,
#   anything with a C extension needs a slow NDK recipe instead.
#   yt-dlp declares its deps as extras, and p4a does not install extras, so the
#   runtime deps are listed explicitly here (without them yt-dlp cannot open a
#   single connection). Left out on purpose: brotli and pycryptodomex (compiled
#   only) - yt-dlp has pure-python fallbacks for both.
requirements = python3,flask,yt-dlp,yt-dlp-ejs,certifi,urllib3,requests,mutagen,websockets

# optional: add `ffmpeg` to the line above for mp3 conversion + 1080p merging.
# It makes the build much longer (ffmpeg is compiled from source).

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# (str) Presplash background color (for android toolchain)
# (str) Presplash animation using Lottie format.
#presplash_lottie = ''

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

#
# Android specific section
#

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android NDK API to use.
android.ndk_api = 24

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_path =

# (str) ANT directory (if empty, it will be automatically downloaded.)
#android.ant_path =

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess Internet downloads or save time
# when an update is due and you just want to test/build your package
android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only.
android.accept_sdk_license = True

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# arm64-v8a covers every phone made in the last ~8 years and halves build time.
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) Presplash background color (for android toolchain)
# (str) Fetch the GTK theme
# This allows to use custom fonts, icons and etc...
# android.presplash_color = #04060c

# (str) Screen orientation
# (str) Icon / presplash
# NOTE: buildozer copies icon.png / presplash.png from source.include_exts
android.release_artifact = apk

#
# Python for android (p4a) specific section
#

# (str) The Android arch to build for
p4a.bootstrap = webview

# (int) Port the WebView loads — must match android/main.py
p4a.port = 5000

#
# Buildozer specific section
#

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 0

# (str) Path to build artifact storage, absolute or relative to spec file
build_dir = ./.buildozer
bin_dir = ./bin
