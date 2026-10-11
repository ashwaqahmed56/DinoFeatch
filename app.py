"""
DinoFetch — download YouTube / Instagram / Facebook as MP4 or MP3.

Run the packaged build :  DinoFetch.exe
Run from source        :  python app.py

Opens in your browser; on the same WiFi your phone can open http://<pc-ip>:<port>.
"""
import os
import socket
import sys
import threading
import uuid
import webbrowser

from flask import Flask, request, jsonify, render_template, send_from_directory, abort

from media_downloader import download, list_downloads, PLATFORM_FOLDERS, detect_platform

APP_NAME = "DinoFetch"
VERSION = "2.0"
PREFERRED_PORT = 5000


def _find_web_root() -> str:
    """
    Folder holding templates/ + static/. PyInstaller unpacks them to a temp dir,
    an Android build runs from the app's private dir — check the known roots
    instead of assuming one layout.
    """
    candidates = [
        getattr(sys, "_MEIPASS", None),
        os.environ.get("ANDROID_ARGUMENT"),
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
    ]
    fallback = os.path.dirname(os.path.abspath(__file__))
    for base in candidates:
        if base and os.path.isfile(os.path.join(base, "templates", "index.html")):
            return base
    return fallback


WEB_ROOT = _find_web_root()

app = Flask(
    __name__,
    template_folder=os.path.join(WEB_ROOT, "templates"),
    static_folder=os.path.join(WEB_ROOT, "static"),
)

jobs = {}  # job_id -> {status, progress, result, url, platform, mode}


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def pick_port(start: int = PREFERRED_PORT) -> int:
    """First free TCP port at or after `start` (exe may outlive a stale run)."""
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return start


# Minimal page used only if the UI assets did not make it into a build.
# Same dark terminal look, same API — just without the library/brand sections.
FALLBACK_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>dinofetch://v2.0</title>
<style>:root{--bg:#04060c;--panel:#0a0f1a;--line:#1b2740;--grn:#00ff88;--cyn:#00e5ff;
--txt:#c9d6e8;--dim:#5b6b87;--red:#ff3355}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:Consolas,Menlo,monospace;padding:16px;
min-height:100vh;font-size:14px}
.sec{border:1px solid var(--line);background:rgba(10,15,26,.92);border-radius:10px;padding:14px}
.lbl{display:block;font-size:12px;color:var(--dim);margin:12px 0 6px}
.lbl::before{content:'> ';color:var(--grn)}
.in{background:#02040a;border:1px solid var(--line);color:#fff;border-radius:8px;width:100%;
padding:13px 12px;font-family:inherit;font-size:13px;outline:none}
.in:focus{border-color:var(--grn)}
.seg{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
.seg button{font-family:inherit;background:#02040a;color:var(--dim);border:1px solid var(--line);
border-radius:8px;padding:11px;font-weight:bold;cursor:pointer}
.seg button.on{color:#04120a;background:var(--grn);border-color:var(--grn)}
.exec{margin-top:14px;width:100%;font-family:inherit;font-size:15px;font-weight:bold;cursor:pointer;
color:#04120a;background:linear-gradient(90deg,var(--grn),var(--cyn));border:0;border-radius:8px;
padding:14px}
.pok{color:var(--grn);font-weight:bold}.perr{color:var(--red);font-weight:bold}
</style></head><body><div class="sec">
<div><span style="color:var(--grn)">root@dinofetch:~$</span> <b>./dinofetch</b></div>
<form id="f">
<label class="lbl">paste_url</label><input id="url" class="in" placeholder="https://...">
<label class="lbl">mode</label>
<div class="seg"><button id="bV" class="on" type="button">--mode=video</button>
<button id="bA" type="button">--mode=audio</button></div>
<button class="exec" id="go">$ execute --download</button>
</form>
<p id="out" style="margin-top:12px;font-size:12px"></p>
</div>
<script>
let mode='video',bV=document.getElementById('bV'),bA=document.getElementById('bA');
bV.onclick=()=>{mode='video';bV.classList.add('on');bA.classList.remove('on')};
bA.onclick=()=>{mode='audio';bA.classList.add('on');bV.classList.remove('on')};
document.getElementById('f').onsubmit=async e=>{
  e.preventDefault();
  const url=document.getElementById('url').value.trim(),out=document.getElementById('out');
  if(!url){out.innerHTML='<span class="perr">ERR: empty_url</span>';return}
  out.textContent='> fetching...';
  const r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({url,mode,platform:'auto'})});
  const d=await r.json();
  if(d.error){out.innerHTML='<span class="perr">ERR: '+d.error+'</span>';return}
  const t=setInterval(async()=>{
    const s=await (await fetch('/api/status/'+d.job_id)).json();
    out.textContent='> '+s.status+' '+(s.filename||'');
    if(s.status==='done'){clearInterval(t);out.innerHTML='<span class="pok">[OK] done</span>'}
    if(s.status==='error'){clearInterval(t);
      out.innerHTML='<span class="perr">[FAIL] '+((s.result&&s.result.error)||'error')+'</span>'}
  },1500);
};
</script></body></html>"""


@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception:
        return FALLBACK_PAGE


@app.route("/sw.js")
def service_worker():
    # served from root so its scope covers the whole app
    resp = send_from_directory(app.static_folder, "sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip()
    platform = (data.get("platform") or "auto").lower()
    mode = (data.get("mode") or "video").lower()
    quality = str(data.get("quality") or "192")

    if not url:
        return jsonify({"error": "Paste a link first"}), 400
    if platform == "auto":
        platform = detect_platform(url)
        if platform == "unknown":
            platform = "youtube"
    if mode not in ("audio", "video"):
        mode = "video"

    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {"status": "starting", "progress": 0, "url": url,
                    "platform": platform, "mode": mode, "result": None}

    def progress_cb(ev):
        j = jobs.get(job_id)
        if not j:
            return
        if ev.get("status") == "downloading":
            j["status"] = "downloading"
            if ev.get("percent") is not None:
                j["progress"] = ev["percent"]
            j["filename"] = ev.get("filename", "")
        elif ev.get("status") == "processing":
            j["status"] = "processing"
            j["progress"] = 100

    def worker():
        try:
            jobs[job_id]["status"] = "downloading"
            res = download(url, platform=platform, mode=mode, quality=quality,
                           progress_callback=progress_cb, quiet=True)
            jobs[job_id]["result"] = res
            jobs[job_id]["status"] = "done" if res["success"] else "error"
            jobs[job_id]["progress"] = 100
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["result"] = {"success": False, "error": str(e)}

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"job_id": job_id, "platform": platform, "mode": mode})


@app.route("/api/status/<job_id>")
def api_status(job_id):
    j = jobs.get(job_id)
    if not j:
        return jsonify({"error": "unknown job"}), 404
    out = {"status": j["status"], "progress": j.get("progress", 0),
           "platform": j.get("platform"), "mode": j.get("mode"),
           "filename": j.get("filename", "")}
    if j["status"] in ("done", "error"):
        out["result"] = j.get("result")
    return jsonify(out)


@app.route("/api/library")
def api_library():
    return jsonify(list_downloads())


@app.route("/files/<platform>/<path:filename>")
def serve_file(platform, filename):
    folder = PLATFORM_FOLDERS.get(platform)
    if not folder:
        abort(404)
    return send_from_directory(folder, filename, as_attachment=False)


def main(open_browser: bool = True):
    for folder in PLATFORM_FOLDERS.values():
        os.makedirs(folder, exist_ok=True)
    port = pick_port()
    local = f"http://127.0.0.1:{port}"
    if open_browser and os.environ.get("DINOFETCH_NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(local)).start()
    print("=" * 60)
    print(f"  {APP_NAME} v{VERSION}")
    print("=" * 60)
    print(f"  On this PC        : {local}")
    print(f"  On phone (same WiFi): http://{get_lan_ip()}:{port}")
    print("  Saving to         : " + os.path.dirname(next(iter(PLATFORM_FOLDERS.values()))))
    print("=" * 60)
    print("  Close this window or press Ctrl+C to stop.")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()