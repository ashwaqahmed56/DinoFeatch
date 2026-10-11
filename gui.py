"""
DinoFetch — native Windows desktop app.

Double-click DinoFetch.exe: a standalone window, no browser, no server.
Downloads land in the downloads/ folder next to the exe.

The web UI (app.py) is still there for the phone + Android build; this file is
the desktop shell and calls the exact same media_downloader engine.
"""
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from media_downloader import (BASE_DIR, FFMPEG_EXE, PLATFORM_FOLDERS,
                              detect_platform, download, list_downloads)

APP_NAME = "DinoFetch"
VERSION = "2.0"


def _enable_dpi_awareness():
    """
    Must run before the first window exists. Without it Windows treats the app as
    DPI-unaware and stretches the rendered bitmap — that is the blurry, pixelated
    text you get on a scaled (125%/150%) display.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:  # Windows 10 1703+
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            return
        except Exception:
            pass
        try:  # Windows 8.1
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


_enable_dpi_awareness()

BG = "#04060c"
PANEL = "#0a0f1a"
PANEL2 = "#0f1729"
LINE = "#22304d"
GRN = "#00ff88"
CYN = "#00e5ff"
TXT = "#dbe6f5"
DIM = "#8497b3"
RED = "#ff5a7a"
AMB = "#ffc043"

PLATFORMS = [("youtube", "YOUTUBE"), ("instagram", "INSTAGRAM"), ("facebook", "FACEBOOK")]
QUALITIES = [("128", "128 kbps  //  small"), ("192", "192 kbps  //  recommended"),
             ("256", "256 kbps"), ("320", "320 kbps  //  best")]

FONT = ("Consolas", 11)
FONT_SM = ("Consolas", 10)
FONT_B = ("Consolas", 11, "bold")


def resource_path(*parts) -> str:
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def open_folder(path: str) -> None:
    """Open a folder in the system file browser."""
    try:
        os.makedirs(path, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        messagebox.showerror(APP_NAME, f"Could not open folder:\n{exc}")


# ---------------------------------------------------------------- engine
# No Tk here, so this is testable on its own and safe to call from a thread.

def run_download(url, platform, mode, quality, emit):
    """Download in the calling thread, reporting through emit(dict)."""
    try:
        result = download(url, platform=platform, mode=mode, quality=quality,
                          progress_callback=lambda ev: emit(ev), quiet=True)
    except Exception as exc:  # never let a worker die silently
        result = {"success": False, "error": str(exc)}
    emit({"status": "done", "result": result})


# ---------------------------------------------------------------- window

def _Evt(widget):
    """A tiny stand-in so _resize_columns can be called outside a real event."""
    return type("E", (), {"widget": widget})()


class DinoFetchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.events = queue.Queue()
        self.busy = False
        self.platform = "youtube"
        self.mode = "video"
        self._pct = 0.0

        root.title(f"{APP_NAME} v{VERSION}")
        root.configure(bg=BG)
        self._center(root, 1380, 820)
        root.minsize(900, 640)

        # crisp text on scaled displays: one Tk font pixel per screen pixel
        try:
            root.tk.call("tk", "scaling", root.winfo_fpixels("1i") / 72.0)
        except Exception:
            pass

        icon = resource_path("static", "icons", "icon-512.png")
        if os.path.exists(icon):
            try:
                root.iconphoto(True, tk.PhotoImage(file=icon))
            except Exception:
                pass

        self._style()
        self._build()
        self.refresh_library()
        self.root.after(100, self._drain)

    # ---------- helpers ----------
    @staticmethod
    def _center(win, width, height):
        """Fit the window to the screen (sizes are physical pixels once DPI-aware)."""
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        w = max(1040, min(width, int(sw * 0.88)))
        h = max(660, min(height, int(sh * 0.88)))
        x, y = max(0, (sw - w) // 2), max(0, (sh - h) // 2 - 20)
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TXT,
                        fieldbackground=PANEL2, bordercolor=LINE,
                        lightcolor=LINE, darkcolor=LINE)
        style.configure("TCombobox", fieldbackground=PANEL2, background=PANEL2,
                        foreground=TXT, arrowcolor=TXT, bordercolor=LINE,
                        selectbackground=PANEL2, selectforeground=TXT)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL2)],
                  foreground=[("readonly", TXT)], bordercolor=[("focus", GRN)])
        root_listbox = self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", TXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", GRN)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#04120a")
        del root_listbox

    def _panel(self, parent, **kw) -> tk.Frame:
        return tk.Frame(parent, bg=kw.pop("bg", PANEL), highlightbackground=LINE,
                        highlightthickness=1, bd=0, **kw)

    def _label(self, parent, text, color=DIM, font=FONT_SM, padx=0, pady=0, **kw) -> tk.Label:
        """Label that packs itself; callers may re-pack it to tweak options."""
        lab = tk.Label(parent, text=text, bg=kw.pop("bg", PANEL), fg=color,
                       font=font, anchor=kw.pop("anchor", "w"),
                       justify=kw.pop("justify", "left"))
        lab.pack(fill="x", padx=padx, pady=pady, **kw)
        return lab

    def _button(self, parent, text, command, **kw):
        return tk.Button(parent, text=text, command=command, font=kw.pop("font", FONT_SM),
                         bg=kw.pop("bg", PANEL2), fg=kw.pop("fg", TXT),
                         activebackground=kw.pop("activebackground", GRN),
                         activeforeground=kw.pop("activeforeground", "#04120a"),
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=kw.pop("highlightbackground", LINE),
                         highlightcolor=GRN, cursor="hand2",
                         padx=kw.pop("padx", 12), pady=kw.pop("pady", 8), **kw)

    # ---------- layout ----------
    def _build(self):
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=14)

        # ---- header ----
        head = self._panel(wrap)
        head.pack(fill="x")
        row = tk.Frame(head, bg=PANEL)
        row.pack(fill="x", padx=18, pady=(14, 2))
        self.led = tk.Label(row, text="■", bg=PANEL, fg=GRN, font=FONT_B)
        self.led.pack(side="left")
        tk.Label(row, text="root@dinofetch:~$", bg=PANEL, fg=GRN,
                 font=FONT_B).pack(side="left", padx=(8, 16))
        tk.Label(row, text=f"./dinofetch --v{VERSION}", bg=PANEL,
                 fg="#ffffff", font=FONT_B).pack(side="left")
        self._label(head, f"engine yt-dlp   ·   ffmpeg {'yes' if FFMPEG_EXE else 'no'}"
                          f"   ·   out mp4|mp3",
                    color=DIM).pack(fill="x", padx=18, pady=(0, 14))

        # ---- two columns: controls left, activity + library right ----
        cols = tk.Frame(wrap, bg=BG)
        cols.pack(fill="both", expand=True, pady=(14, 0))
        self.cols = cols

        left = self._panel(cols)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)          # width is driven by the layout code
        right = self._panel(cols)
        right.pack(side="left", fill="both", expand=True)
        self.left_panel, self.right_panel = left, right
        cols.bind("<Configure>", self._resize_columns, add="+")

        # ============ LEFT: the download form ============
        self._label(left, "[1] DOWNLOAD", color=CYN, font=FONT_B, padx=20, pady=(16, 12))
        body = tk.Frame(left, bg=PANEL)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 18))

        targets = tk.Frame(body, bg=PANEL)
        targets.pack(fill="x")
        self.tgt_buttons = {}
        for idx, (key, label) in enumerate(PLATFORMS):
            btn = self._button(targets, label, lambda k=key: self.set_platform(k), font=FONT)
            btn.pack(side="left", fill="x", expand=True, padx=(0 if idx == 0 else 8, 0))
            self.tgt_buttons[key] = btn
        self.set_platform("youtube")

        self._label(body, "> paste_url", pady=(18, 6))
        self.url_var = tk.StringVar()
        self.url = tk.Entry(body, textvariable=self.url_var, bg="#02040a", fg="#ffffff",
                           insertbackground=GRN, relief="flat", bd=0,
                           highlightthickness=1, highlightbackground=LINE,
                           highlightcolor=GRN, font=FONT)
        self.url.pack(fill="x", ipady=12, padx=2)
        self.url.bind("<Return>", lambda _e: self.start())

        self._label(body, "> mode", pady=(18, 6))
        modes = tk.Frame(body, bg=PANEL)
        modes.pack(fill="x")
        self.mode_buttons = {}
        for key, label in (("video", "--mode=video"), ("audio", "--mode=audio")):
            btn = self._button(modes, label, lambda k=key: self.set_mode(k), font=FONT)
            btn.pack(side="left", fill="x", expand=True,
                     padx=(0 if key == "video" else 8, 0))
            self.mode_buttons[key] = btn

        self.qlbl = self._label(body, "> bitrate", pady=(18, 6))
        self.quality = ttk.Combobox(body, values=[label for _, label in QUALITIES],
                                    state="readonly", font=FONT, height=8)
        self.quality.current(1)
        self.quality.pack(fill="x", padx=2, pady=(0, 2))
        self.set_mode("video")

        self.go_btn = tk.Button(body, text="$ execute --download", command=self.start,
                                font=("Consolas", 13, "bold"), bg=GRN, fg="#04120a",
                                activebackground=CYN, activeforeground="#04120a",
                                relief="flat", bd=0, cursor="hand2", pady=14)
        self.go_btn.pack(fill="x", pady=(20, 0))

        # progress: bar on the left, percentage on the right
        prog = tk.Frame(body, bg=PANEL)
        prog.pack(fill="x", pady=(20, 0))
        self.bar = tk.Frame(prog, bg=PANEL2, height=20,
                            highlightthickness=1, highlightbackground=LINE)
        self.bar.pack(side="left", fill="both", expand=True)
        self.bar_fill = tk.Frame(self.bar, bg=GRN)
        self.bar_fill.place(x=2, y=2, relheight=0.72, relwidth=0)
        self.bar_text = tk.Label(prog, text="0%", bg=PANEL, fg=TXT,
                                 font=FONT_B, width=6, anchor="e")
        self.bar_text.pack(side="left", padx=(10, 0))

        self.status = self._label(body, "awaiting input_", color=DIM, font=FONT)
        self.status.pack(fill="x", pady=(12, 0))

        # ============ RIGHT: activity, save location, library ============
        self._label(right, "[2] ACTIVITY", color=CYN, font=FONT_B, padx=20, pady=(16, 10))
        rbody = tk.Frame(right, bg=PANEL)
        rbody.pack(fill="both", expand=True, padx=20, pady=(0, 18))

        self.log = tk.Text(rbody, height=5, width=48, bg="#02040a", fg=DIM, relief="flat", bd=0,
                           font=FONT_SM, wrap="word", state="disabled",
                           highlightthickness=1, highlightbackground=LINE,
                           padx=10, pady=8)
        self.log.pack(fill="both", expand=True)

        # where the files land — big, readable, one click away
        save = tk.Frame(rbody, bg="#071018", highlightthickness=1,
                        highlightbackground=LINE)
        save.pack(fill="x", pady=(12, 0))
        tk.Label(save, text="SAVED TO", bg="#071018", fg=CYN, font=FONT_SM,
                 anchor="w").pack(fill="x", padx=16, pady=(12, 4))
        self.path_label = tk.Label(save, text=BASE_DIR, bg="#071018", fg=TXT,
                                   font=FONT, anchor="w", justify="left",
                                   wraplength=360)
        self.path_label.pack(fill="x", padx=16, pady=(0, 10))
        btns = tk.Frame(save, bg="#071018")
        btns.pack(fill="x", padx=16, pady=(0, 12))
        self._button(btns, "[ open folder ]", self.open_library,
                     bg="#0d2a1c", fg=GRN, highlightbackground=GRN,
                     activebackground=GRN, activeforeground="#04120a",
                     font=FONT_B).pack(side="left", fill="x", expand=True)
        self._button(btns, "[ copy path ]", self.copy_path,
                     font=FONT_SM).pack(side="left", fill="x", expand=True,
                                        padx=(10, 0))

        # library
        lib_head = tk.Frame(rbody, bg=PANEL)
        lib_head.pack(fill="x", pady=(16, 8))
        self._label(lib_head, "[3] SAVED FILES", color=CYN, font=FONT_B).pack(side="left")
        self._button(lib_head, "[refresh]", self.refresh_library,
                     font=FONT_SM).pack(side="right")

        listbody = tk.Frame(rbody, bg=PANEL)
        listbody.pack(fill="both", expand=True)
        self.library = tk.Listbox(listbody, width=48, bg=PANEL2, fg=TXT, relief="flat", bd=0,
                                  font=FONT_SM, highlightthickness=1,
                                  highlightbackground=LINE, selectbackground=GRN,
                                  selectforeground="#04120a", activestyle="none",
                                  borderwidth=0, highlightcolor=LINE)
        scroll = ttk.Scrollbar(listbody, orient="vertical", command=self.library.yview)
        self.library.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.library.pack(side="left", fill="both", expand=True)
        self.library.bind("<Double-Button-1>", lambda _e: self.open_item())
        tk.Label(rbody, text="double-click a file to open its folder",
                 bg=PANEL, fg=DIM, font=FONT_SM, anchor="w").pack(fill="x", pady=(6, 0))

        # keep the long status/path text wrapped to the real column width
        for panel in (left, right):
            panel.bind("<Configure>",
                       lambda e, p=panel: self._rewrap(p.winfo_width()),
                       add="+")
        self.root.after(60, lambda: self._resize_columns(_Evt(cols)))

        tk.Label(wrap, text=f"{APP_NAME.lower()} v{VERSION}   //   ready",
                 bg=BG, fg=DIM, font=FONT_SM).pack(pady=(12, 0))

    def _resize_columns(self, event):
        """Pin the left column to ~52% so the layout never drifts on resize."""
        total = event.widget.winfo_width()
        if total <= 1:
            return
        self.left_panel.configure(width=max(420, int(total * 0.52)))
        self._rewrap(self.left_panel.winfo_width())

    def _rewrap(self, width: int):
        """Long Windows paths must wrap, not stretch the layout."""
        width = max(200, width - 60)
        self.status.configure(wraplength=width)
        self.path_label.configure(wraplength=width)

    # ---------- state ----------
    def set_platform(self, key: str):
        self.platform = key
        for name, btn in self.tgt_buttons.items():
            on = name == key
            btn.configure(bg="#0d2a1c" if on else PANEL2,
                          fg=GRN if on else DIM,
                          highlightbackground=GRN if on else LINE)

    def set_mode(self, mode: str):
        self.mode = mode
        for name, btn in self.mode_buttons.items():
            on = name == mode
            btn.configure(bg=GRN if on else PANEL2,
                          fg="#04120a" if on else DIM,
                          highlightbackground=GRN if on else LINE)
        audio = mode == "audio"
        if audio:
            self.qlbl.pack(fill="x", pady=(16, 6), before=self.go_btn)
            self.quality.pack(fill="x", padx=2, pady=(0, 2), before=self.go_btn)
        else:
            self.qlbl.pack_forget()
            self.quality.pack_forget()

    # ---------- actions ----------
    def start(self):
        if self.busy:
            self.write("ERR: already downloading")
            return
        url = self.url_var.get().strip()
        if not url:
            self.set_status("ERR: empty_url — paste a link first", RED)
            return

        platform = self.platform
        detected = detect_platform(url)
        if detected != "unknown" and detected != platform:
            self.write(f"> url looks like {detected}, using {platform}")
        quality = QUALITIES[self.quality.current()][0] if self.mode == "audio" else "192"

        self.busy = True
        self.set_progress(0)
        self.go_btn.configure(state="disabled", bg=DIM, fg=PANEL, cursor="arrow")
        self.set_status(f"> fetching :: {url[:64]}", CYN)
        threading.Thread(target=run_download,
                         args=(url, platform, self.mode, quality, self.events.put),
                         daemon=True).start()

    def refresh_library(self):
        self.library.delete(0, "end")
        total = 0
        for platform in ("youtube", "instagram", "facebook"):
            files = list_downloads().get(platform, [])
            self.library.insert("end", f"{platform.upper()}  —  {len(files)} file(s)"
                                        f"   ·   {os.path.join(BASE_DIR, platform)}")
            if not files:
                self.library.insert("end", "      (nothing saved yet)")
            for item in reversed(files[-50:]):
                total += 1
                self.library.insert("end", f"      {item['name']}   [{item['size_mb']} MB]")
        if not total:
            self.library.insert("end", "No downloads yet — your files will appear here.")

    def open_library(self):
        open_folder(BASE_DIR)

    def copy_path(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(BASE_DIR)
        self.set_status(f"copied to clipboard :: {BASE_DIR}", CYN)

    def open_item(self):
        """Double-click a file row: reveal it in Explorer."""
        sel = self.library.curselection()
        if not sel:
            return self.open_library()
        text = self.library.get(sel[0]).strip()
        name = text.lstrip("-• ").strip()
        for platform in PLATFORM_FOLDERS:
            folder = PLATFORM_FOLDERS[platform]
            if os.path.exists(os.path.join(folder, name)):
                return open_folder(folder)
        self.open_library()

    # ---------- worker events ----------
    def _drain(self):
        try:
            while True:
                self._handle(self.events.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._drain)

    def _handle(self, ev):
        status = ev.get("status")
        if status == "downloading":
            pct = ev.get("percent")
            if pct is not None:
                self.set_progress(pct)
                self.set_status(f"> [{self._pct:3.0f}%]  "
                                f"{(ev.get('filename') or '')[:56]}", GRN)
        elif status == "processing":
            self.set_progress(100)
            self.set_status("> processing (converting / merging)...", AMB)
        elif status == "done":
            self._finish(ev.get("result") or {})

    def _finish(self, result):
        self.busy = False
        self.go_btn.configure(state="normal", bg=GRN, fg="#04120a", cursor="hand2")
        if not result.get("success"):
            error = (result.get("error") or "error")[:100]
            self.set_status(f"[FAIL] {error}", RED)
            self.write("ERR: " + error)
            return

        self.set_progress(100)
        files = result.get("files") or []
        if files:
            path = files[0]
            self.set_status(f"[OK] saved  →  {path}", GRN)
            self.write("+ " + path)
        else:
            self.set_status("[OK] done", GRN)
        self.path_label.configure(text=result.get("folder") or BASE_DIR)
        self.refresh_library()

    def set_progress(self, pct: float):
        self._pct = max(0.0, min(100.0, float(pct)))
        self.bar_fill.place_configure(relwidth=self._pct / 100.0)
        self.bar_text.configure(text=f"{self._pct:.0f}%")

    def set_status(self, text, color=TXT):
        self.status.configure(text=text, fg=color)

    def write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


# ---------------------------------------------------------------- startup

def main():
    root = tk.Tk()
    try:
        DinoFetchApp(root)
    except Exception as exc:
        messagebox.showerror(APP_NAME, f"DinoFetch failed to start:\n{exc}")
        raise
    root.mainloop()


if __name__ == "__main__":
    main()