# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for DinoFetch — single-file Windows build.
# Build:  python -m PyInstaller DinoFetch.spec --noconfirm
import os

# Native window: only the app icon travels with the exe.
# templates/ + the rest of static/ are for the web build (phone / Android).
datas = [
    (os.path.join("static", "icons", "icon-512.png"), os.path.join("static", "icons")),
]

hiddenimports = [
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "yt_dlp",
    "yt_dlp.extractor",
    "yt_dlp.postprocessor",
    "yt_dlp.downloader",
    "yt_dlp.networking",
    "certifi",
    "urllib3",
    "websockets",
    "Cryptodome",
]

a = Analysis(
    ["gui.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # yt-dlp pulls in a huge optional dependency graph; pruning keeps the exe lean
    excludes=["matplotlib", "numpy", "pandas", "IPython", "notebook",
              "pytest", "pip"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DinoFetch",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=os.path.join("static", "icons", "icon-512.png") if os.path.exists(
        os.path.join("static", "icons", "icon-512.png")) else None,
)