#!/usr/bin/env python3
"""
YouTube Downloader (Flask UI + PyTubeFix)
========================================

FEATURES:
- Flask backend with web UI (/)
- Stream selection (video/audio qualities)
- Progress tracking (speed, ETA, percent)
- Auto open browser at http://127.0.0.1:5000/
- OS-aware download folder handling
- PyInstaller friendly

DEPENDENCIES:
pip install flask pytubefix

RUN:
python main.py
"""

import os
import re
import time
import json
import threading
import webbrowser
import platform
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, render_template_string
from pytubefix import YouTube

APP_HOST = "127.0.0.1"
APP_PORT = 5000

app = Flask(__name__)

# -----------------------------
# Global runtime state
# -----------------------------
DOWNLOAD_STATE: Dict[str, Any] = {
    "status": "idle",  # idle | fetching | ready | downloading | done | error
    "message": "",
    "title": "",
    "url": "",
    "streams": [],
    "selected_itag": None,
    "progress": 0.0,
    "speed_mbps": 0.0,
    "eta": "--:--",
    "downloaded_mb": 0.0,
    "total_mb": 0.0,
    "output_path": "",
    "error": "",
}


LOCK = threading.Lock()


# -----------------------------
# Helpers
# -----------------------------
def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)  # Windows invalid chars
    name = re.sub(r"\s+", " ", name)
    return name[:140]


def get_download_base_folder() -> Path:
    system = platform.system().lower()

    # Windows: C:\Users\<user>\Downloads\YoutubeDownloader
    if "windows" in system:
        downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads"
        return downloads / "YoutubeDownloader"

    # Linux: /home/<user>/Downloads/YoutubeDownloads
    downloads = Path.home() / "Downloads"
    return downloads / "YoutubeDownloads"


def guess_extension(stream) -> str:
    subtype = getattr(stream, "subtype", "")
    mime_type = getattr(stream, "mime_type", "") or ""

    if subtype:
        return f".{subtype}"

    m = mime_type.lower()
    if "mp4" in m:
        return ".mp4"
    if "webm" in m:
        return ".webm"
    if "m4a" in m:
        return ".m4a"
    if "mp3" in m:
        return ".mp3"
    if "ogg" in m:
        return ".ogg"

    return ".bin"


def stream_to_dict(stream) -> Dict[str, Any]:
    # pytubefix Stream has various properties
    stype = getattr(stream, "type", "")
    itag = getattr(stream, "itag", None)
    mime_type = getattr(stream, "mime_type", "")
    abr = getattr(stream, "abr", "")
    resolution = getattr(stream, "resolution", "")
    fps = getattr(stream, "fps", "")
    codecs = getattr(stream, "codecs", "")

    # size (might fail for some streams)
    try:
        size_bytes = int(stream.filesize or 0)
    except Exception:
        size_bytes = 0

    size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes else 0.0

    label_parts = []
    if stype == "video":
        label_parts.append(f"{resolution or 'unknown'}")
        if fps:
            label_parts.append(f"{fps}fps")
        label_parts.append(mime_type)
    else:
        label_parts.append(f"{abr or 'unknown'}")
        label_parts.append(mime_type)

    label = " | ".join(label_parts)

    return {
        "itag": itag,
        "type": stype,
        "mime_type": mime_type,
        "resolution": resolution,
        "abr": abr,
        "fps": fps,
        "codecs": codecs,
        "size_mb": size_mb,
        "label": label,
    }


def reset_state():
    with LOCK:
        DOWNLOAD_STATE.update(
            {
                "status": "idle",
                "message": "",
                "title": "",
                "url": "",
                "streams": [],
                "selected_itag": None,
                "progress": 0.0,
                "speed_mbps": 0.0,
                "eta": "--:--",
                "downloaded_mb": 0.0,
                "total_mb": 0.0,
                "output_path": "",
                "error": "",
            }
        )


# -----------------------------
# UI (HTML)
# -----------------------------
HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>YouTube Downloader</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; background:#0b1220; color:#e6edf3; margin:0; }
    .wrap { max-width: 980px; margin: 30px auto; padding: 18px; }
    .card { background:#0f1b33; border:1px solid #223455; border-radius:16px; padding: 18px; margin-bottom: 14px; box-shadow: 0 10px 30px rgba(0,0,0,0.25); }
    h1 { margin:0 0 10px 0; font-size: 22px; }
    label { font-size: 13px; color:#b6c2d0; display:block; margin-bottom: 6px; }
    input[type=text] { width: 100%; padding: 12px 12px; border-radius: 12px; border:1px solid #2a4170; background:#0b162c; color:#e6edf3; outline:none; }
    button { border:0; border-radius: 12px; padding: 10px 12px; background:#2a70ff; color:white; font-weight:600; cursor:pointer; }
    button:disabled { opacity: 0.6; cursor:not-allowed; }
    .row { display:flex; gap: 12px; align-items:center; }
    .row > * { flex:1; }
    .muted { color:#9db0c6; font-size: 13px; }
    .streams { display:grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
    .streamItem { border:1px solid #2a4170; background:#0b162c; border-radius: 14px; padding: 12px; }
    .streamItem strong { display:block; margin-bottom:6px; }
    .progressWrap { width:100%; background:#0b162c; border:1px solid #2a4170; border-radius: 999px; overflow:hidden; height: 14px; }
    .bar { height:100%; width:0%; background: linear-gradient(90deg, #22c55e, #2a70ff); }
    .kv { display:flex; gap:12px; flex-wrap:wrap; }
    .kv .chip { background:#0b162c; border:1px solid #2a4170; border-radius: 999px; padding: 8px 10px; font-size: 13px; color:#dbe7f3; }
    footer { text-align:center; color:#8aa3bd; font-size:12px; margin-top:18px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Youtube Downloader by Sombit Pramanik</h1>
      <p class="muted">Paste a YouTube link, select quality, and download. The app runs locally on your system.</p>

      <div style="margin-top:12px;">
        <label>YouTube URL</label>
        <div class="row">
          <input id="url" type="text" placeholder="https://www.youtube.com/watch?v=..." />
          <button id="fetchBtn" onclick="fetchStreams()">Fetch</button>
        </div>
      </div>

      <div style="margin-top:12px;" class="kv">
        <span class="chip" id="statusChip">Status: idle</span>
        <span class="chip" id="titleChip">Title: -</span>
      </div>
    </div>

    <div class="card">
      <h1>Available Streams</h1>
      <p class="muted">Choose one stream and click download.</p>

      <div class="streams" id="streams"></div>

      <div style="margin-top:12px;">
        <button id="downloadBtn" onclick="startDownload()" disabled>Start Download</button>
        <button style="background:#334155" onclick="resetAll()">Reset</button>
      </div>
    </div>

    <div class="card">
      <h1>Download Progress</h1>

      <div class="progressWrap">
        <div class="bar" id="bar"></div>
      </div>

      <div style="margin-top:12px;" class="kv">
        <span class="chip" id="pct">0%</span>
        <span class="chip" id="speed">Speed: -- MB/s</span>
        <span class="chip" id="eta">ETA: --:--</span>
        <span class="chip" id="size">Size: -- / -- MB</span>
      </div>

      <p class="muted" id="msg" style="margin-top:12px;"></p>
      <p class="muted" id="out" style="margin-top:8px;"></p>
    </div>

    <footer>Runs on: http://127.0.0.1:5000/</footer>
  </div>

<script>
let selectedItag = null;
let pollTimer = null;

function setStatus(s) {
  document.getElementById("statusChip").innerText = "Status: " + s;
}

function setTitle(t) {
  document.getElementById("titleChip").innerText = "Title: " + (t || "-");
}

function renderStreams(streams) {
  const root = document.getElementById("streams");
  root.innerHTML = "";
  if (!streams || streams.length === 0) {
    root.innerHTML = "<p class='muted'>No streams loaded yet.</p>";
    return;
  }

  streams.forEach(st => {
    const div = document.createElement("div");
    div.className = "streamItem";

    const btn = document.createElement("button");
    btn.innerText = "Select";
    btn.style.background = "#22c55e";
    btn.style.marginTop = "10px";
    btn.onclick = () => {
      selectedItag = st.itag;
      document.getElementById("downloadBtn").disabled = false;
      // highlight selection
      Array.from(document.querySelectorAll(".streamItem")).forEach(x => x.style.outline = "none");
      div.style.outline = "2px solid #22c55e";
    };

    div.innerHTML = `
      <strong>${st.type.toUpperCase()} - ${st.label}</strong>
      <div class="muted">itag: ${st.itag}</div>
      <div class="muted">codecs: ${st.codecs}</div>
      <div class="muted">size: ${st.size_mb || 0} MB</div>
    `;
    div.appendChild(btn);
    root.appendChild(div);
  });
}

async function fetchStreams() {
  const url = document.getElementById("url").value.trim();
  if (!url) return;

  setStatus("fetching");
  document.getElementById("msg").innerText = "Fetching metadata...";

  const res = await fetch("/api/fetch", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({url})
  });

  const data = await res.json();
  if (!res.ok) {
    setStatus("error");
    document.getElementById("msg").innerText = data.error || "Failed";
    return;
  }

  setStatus("ready");
  setTitle(data.title || "-");
  renderStreams(data.streams);
  document.getElementById("msg").innerText = "Streams ready. Select one to download.";
}

async function startDownload() {
  if (!selectedItag) return;

  setStatus("downloading");
  document.getElementById("msg").innerText = "Starting download...";

  const res = await fetch("/api/download", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({itag: selectedItag})
  });

  const data = await res.json();
  if (!res.ok) {
    setStatus("error");
    document.getElementById("msg").innerText = data.error || "Failed to start";
    return;
  }

  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollProgress, 500);
}

async function pollProgress() {
  const res = await fetch("/api/status");
  const s = await res.json();

  setStatus(s.status || "unknown");
  setTitle(s.title || "-");

  const pct = Math.max(0, Math.min(100, s.progress || 0));
  document.getElementById("bar").style.width = pct + "%";
  document.getElementById("pct").innerText = pct.toFixed(1) + "%";
  document.getElementById("speed").innerText = "Speed: " + (s.speed_mbps || 0).toFixed(2) + " MB/s";
  document.getElementById("eta").innerText = "ETA: " + (s.eta || "--:--");
  document.getElementById("size").innerText = "Size: " + (s.downloaded_mb || 0).toFixed(2) + " / " + (s.total_mb || 0).toFixed(2) + " MB";
  document.getElementById("msg").innerText = s.message || "";
  document.getElementById("out").innerText = s.output_path ? ("Saved to: " + s.output_path) : "";

  if (s.status === "done" || s.status === "error") {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function resetAll() {
  await fetch("/api/reset", {method:"POST"});
  selectedItag = null;
  document.getElementById("downloadBtn").disabled = true;
  document.getElementById("streams").innerHTML = "";
  document.getElementById("bar").style.width = "0%";
  document.getElementById("pct").innerText = "0%";
  document.getElementById("speed").innerText = "Speed: -- MB/s";
  document.getElementById("eta").innerText = "ETA: --:--";
  document.getElementById("size").innerText = "Size: -- / -- MB";
  document.getElementById("msg").innerText = "";
  document.getElementById("out").innerText = "";
  setStatus("idle");
  setTitle("-");
}
</script>
</body>
</html>
"""


# -----------------------------
# API Routes
# -----------------------------
@app.get("/")
def index():
    return render_template_string(HTML_PAGE)


@app.post("/api/reset")
def api_reset():
    reset_state()
    return jsonify({"ok": True})


@app.get("/api/status")
def api_status():
    with LOCK:
        return jsonify(DOWNLOAD_STATE)


@app.post("/api/fetch")
def api_fetch():
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400

    with LOCK:
        DOWNLOAD_STATE["status"] = "fetching"
        DOWNLOAD_STATE["url"] = url
        DOWNLOAD_STATE["message"] = "Fetching metadata..."
        DOWNLOAD_STATE["error"] = ""
        DOWNLOAD_STATE["streams"] = []
        DOWNLOAD_STATE["selected_itag"] = None

    try:
        yt = YouTube(url)
        title = sanitize_filename(getattr(yt, "title", "Unknown Title"))

        # prefer progressive + adaptive streams together, sorted by size/resolution
        streams = list(getattr(yt, "streams", []))

        video_streams = []
        audio_streams = []

        for s in streams:
            try:
                d = stream_to_dict(s)
                if d["itag"] is None:
                    continue
                if d["type"] == "video":
                    video_streams.append(d)
                elif d["type"] == "audio":
                    audio_streams.append(d)
            except Exception:
                continue

        # sort: video higher resolution first, audio higher abr first
        def video_key(x):
            res = x.get("resolution") or "0p"
            num = int(re.sub(r"\D", "", res) or 0)
            return (num, x.get("size_mb") or 0.0)

        def audio_key(x):
            abr = x.get("abr") or "0kbps"
            num = int(re.sub(r"\D", "", abr) or 0)
            return (num, x.get("size_mb") or 0.0)

        video_streams.sort(key=video_key, reverse=True)
        audio_streams.sort(key=audio_key, reverse=True)

        combined = video_streams + audio_streams

        with LOCK:
            DOWNLOAD_STATE["status"] = "ready"
            DOWNLOAD_STATE["title"] = title
            DOWNLOAD_STATE["streams"] = combined
            DOWNLOAD_STATE["message"] = "Streams loaded. Select one to download."

        return jsonify({"title": title, "streams": combined})

    except Exception as e:
        with LOCK:
            DOWNLOAD_STATE["status"] = "error"
            DOWNLOAD_STATE["error"] = str(e)
            DOWNLOAD_STATE["message"] = "Failed to fetch metadata."
        return jsonify({"error": str(e)}), 500


def _download_worker(url: str, itag: int, title: str):
    try:
        yt = YouTube(url)

        stream = yt.streams.get_by_itag(itag)
        if not stream:
            raise RuntimeError("Invalid stream selected (itag not found).")

        base_dir = get_download_base_folder()
        base_dir.mkdir(parents=True, exist_ok=True)

        safe_title = sanitize_filename(title) or "youtube_download"
        ext = guess_extension(stream)
        filename = f"{safe_title}{ext}"

        out_path = str(base_dir / filename)

        with LOCK:
            DOWNLOAD_STATE["status"] = "downloading"
            DOWNLOAD_STATE["message"] = "Downloading..."
            DOWNLOAD_STATE["output_path"] = out_path
            DOWNLOAD_STATE["progress"] = 0.0
            DOWNLOAD_STATE["speed_mbps"] = 0.0
            DOWNLOAD_STATE["eta"] = "--:--"
            DOWNLOAD_STATE["downloaded_mb"] = 0.0
            DOWNLOAD_STATE["total_mb"] = 0.0
            DOWNLOAD_STATE["error"] = ""

        # progress tracking
        start_t = time.time()
        last_t = start_t
        last_downloaded = 0

        def on_progress(_stream, _chunk, bytes_remaining):
            nonlocal last_t, last_downloaded
            total = getattr(_stream, "filesize", 0) or 0
            downloaded = total - bytes_remaining if total else 0

            now = time.time()
            elapsed = now - last_t

            if total > 0:
                pct = (downloaded / total) * 100.0
            else:
                pct = 0.0

            # compute speed every ~0.4s
            if elapsed >= 0.4:
                diff = downloaded - last_downloaded
                speed_bps = diff / elapsed if elapsed > 0 else 0
                speed_mbps = speed_bps / (1024 * 1024)

                # ETA
                if speed_bps > 0:
                    eta_sec = bytes_remaining / speed_bps
                    eta_m = int(eta_sec // 60)
                    eta_s = int(eta_sec % 60)
                    eta_str = f"{eta_m:02d}:{eta_s:02d}"
                else:
                    eta_str = "--:--"

                with LOCK:
                    DOWNLOAD_STATE["progress"] = pct
                    DOWNLOAD_STATE["speed_mbps"] = speed_mbps
                    DOWNLOAD_STATE["eta"] = eta_str
                    DOWNLOAD_STATE["downloaded_mb"] = round(downloaded / (1024 * 1024), 2)
                    DOWNLOAD_STATE["total_mb"] = round(total / (1024 * 1024), 2)
                    DOWNLOAD_STATE["message"] = "Downloading..."

                last_t = now
                last_downloaded = downloaded

        def on_complete(_stream, file_path):
            with LOCK:
                DOWNLOAD_STATE["progress"] = 100.0
                DOWNLOAD_STATE["status"] = "done"
                DOWNLOAD_STATE["message"] = "Download completed successfully!"
                DOWNLOAD_STATE["output_path"] = file_path

        yt.register_on_progress_callback(on_progress)
        yt.register_on_complete_callback(on_complete)

        # actual download
        stream.download(output_path=str(base_dir), filename=filename)

        # if on_complete not triggered for any reason, set final
        with LOCK:
            if DOWNLOAD_STATE["status"] != "done":
                DOWNLOAD_STATE["status"] = "done"
                DOWNLOAD_STATE["progress"] = 100.0
                DOWNLOAD_STATE["message"] = "Download completed successfully!"

    except Exception as e:
        with LOCK:
            DOWNLOAD_STATE["status"] = "error"
            DOWNLOAD_STATE["error"] = str(e)
            DOWNLOAD_STATE["message"] = f"Download failed: {str(e)}"


@app.post("/api/download")
def api_download():
    data = request.get_json(force=True)
    itag = data.get("itag")

    with LOCK:
        url = DOWNLOAD_STATE.get("url", "")
        title = DOWNLOAD_STATE.get("title", "youtube_download")

    if not url:
        return jsonify({"error": "Fetch streams first"}), 400

    try:
        itag = int(itag)
    except Exception:
        return jsonify({"error": "Invalid itag"}), 400

    # start background download
    t = threading.Thread(target=_download_worker, args=(url, itag, title), daemon=True)
    t.start()

    return jsonify({"ok": True})


# -----------------------------
# Startup behavior
# -----------------------------
def open_browser():
    webbrowser.open(f"http://{APP_HOST}:{APP_PORT}/", new=2)


def main():
    # Auto-open browser shortly after server starts
    threading.Timer(0.7, open_browser).start()
    app.run(host=APP_HOST, port=APP_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
