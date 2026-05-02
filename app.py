# jiosaavn-dl web app
# Flask backend for the JioSaavn downloader

import os
import io
import re
import uuid
import zipfile
import tempfile
import threading
import json as json_module
from queue import Queue, Empty
from flask import Flask, render_template, request, send_file, jsonify, Response, session, redirect, url_for
from jiosaavn import Jiosaavn, album_song_rx, playlist_rx

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
APP_PASSWORD = os.environ.get("APP_PASSWORD", "secret")

# Task storage for background downloads
tasks = {}
tasks_lock = threading.Lock()


@app.before_request
def require_login():
    if request.endpoint in ('login', 'static'):
        return
    if not session.get('logged_in'):
        # For API requests, return 401 instead of redirect
        if request.is_json or request.path.startswith(('/preview', '/start', '/progress', '/result')):
            if request.method == 'GET' and not request.is_json:
                return redirect(url_for('login'))
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for('login'))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template("login.html", error="Invalid password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    """Fetch metadata for a URL without downloading."""
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "No URL provided."}), 400

    url = data["url"].strip()
    is_song_or_album = "/album/" in url or "/song/" in url
    is_playlist = "/playlist/" in url or "/featured/" in url

    if not (is_song_or_album or is_playlist):
        return jsonify({"error": "Invalid URL. Please provide a valid JioSaavn song, album, or playlist link."}), 400

    try:
        jiosaavn = Jiosaavn()

        if is_song_or_album:
            match = album_song_rx.search(url)
            if not match:
                return jsonify({"error": "Could not parse the song/album URL."}), 400
            kind, id_ = match.groups()
            if kind == "song":
                info = jiosaavn.getTrackInfo(id_)
            elif kind == "album":
                info = jiosaavn.getAlbumInfo(id_)
            else:
                return jsonify({"error": "Unsupported URL type."}), 400
        elif is_playlist:
            match = playlist_rx.search(url)
            if not match:
                return jsonify({"error": "Could not parse the playlist URL."}), 400
            playlist_id = match.group(2)
            info = jiosaavn.getPlaylistInfo(playlist_id)
        else:
            return jsonify({"error": "Unsupported URL type."}), 400

        return jsonify(info)

    except Exception as e:
        return jsonify({"error": f"Failed to fetch metadata: {str(e)}"}), 500


@app.route("/start", methods=["POST"])
def start_download():
    """Start a download task in the background. Returns a task ID."""
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "No URL provided."}), 400

    url = data["url"].strip()
    add_numbers = data.get("addNumbers", False)
    download_cover = data.get("downloadCover", False)

    is_song_or_album = "/album/" in url or "/song/" in url
    is_playlist = "/playlist/" in url or "/featured/" in url

    if not (is_song_or_album or is_playlist):
        return jsonify({"error": "Invalid URL."}), 400

    task_id = str(uuid.uuid4())
    progress_queue = Queue()

    task = {
        "status": "running",
        "progress_queue": progress_queue,
        "result": None,  # will hold (BytesIO, filename, mimetype)
        "error": None,
    }

    with tasks_lock:
        tasks[task_id] = task

    def run_download():
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                def on_progress(message, current, total):
                    progress_queue.put({
                        "message": message,
                        "current": current,
                        "total": total,
                        "status": "downloading",
                    })

                jiosaavn = Jiosaavn(
                    add_numbers=add_numbers,
                    download_cover=download_cover,
                    output_dir=temp_dir,
                    progress_callback=on_progress,
                )

                if is_song_or_album:
                    match = album_song_rx.search(url)
                    kind, id_ = match.groups()
                    if kind == "song":
                        jiosaavn.processTrack(id_, None, 1, 1)
                    elif kind == "album":
                        jiosaavn.processAlbum(id_)
                elif is_playlist:
                    match = playlist_rx.search(url)
                    playlist_id = match.group(2)
                    jiosaavn.processPlaylist(playlist_id)

                # Collect .m4a files
                m4a_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for f in files:
                        if f.endswith(".m4a"):
                            m4a_files.append(os.path.join(root, f))

                if not m4a_files:
                    task["status"] = "error"
                    task["error"] = "No tracks downloaded. Content may be unavailable in your region."
                    progress_queue.put({"status": "error", "message": task["error"]})
                    return

                # Single file → send .m4a directly
                if len(m4a_files) == 1:
                    file_path = m4a_files[0]
                    file_name = os.path.basename(file_path)
                    buffer = io.BytesIO()
                    with open(file_path, "rb") as f:
                        buffer.write(f.read())
                    buffer.seek(0)
                    task["result"] = (buffer, file_name, "audio/mp4")
                else:
                    # Multiple files → zip
                    buffer = io.BytesIO()
                    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        for file_path in m4a_files:
                            arcname = os.path.relpath(file_path, temp_dir)
                            zf.write(file_path, arcname)
                    buffer.seek(0)
                    subdirs = [
                        d for d in os.listdir(temp_dir)
                        if os.path.isdir(os.path.join(temp_dir, d))
                    ]
                    zip_name = (subdirs[0] if subdirs else "jiosaavn-dl") + ".zip"
                    task["result"] = (buffer, zip_name, "application/zip")

                task["status"] = "done"
                progress_queue.put({
                    "status": "done",
                    "message": "Download complete!",
                    "filename": task["result"][1],
                })

        except Exception as e:
            task["status"] = "error"
            task["error"] = str(e)
            progress_queue.put({"status": "error", "message": str(e)})

    thread = threading.Thread(target=run_download, daemon=True)
    thread.start()

    return jsonify({"taskId": task_id})


@app.route("/progress/<task_id>")
def progress(task_id):
    """SSE endpoint for real-time progress updates."""
    with tasks_lock:
        task = tasks.get(task_id)

    if not task:
        return jsonify({"error": "Task not found."}), 404

    def generate():
        while True:
            try:
                event = task["progress_queue"].get(timeout=30)
                yield f"data: {json_module.dumps(event)}\n\n"
                if event.get("status") in ("done", "error"):
                    break
            except Empty:
                # Send keepalive
                yield f"data: {json_module.dumps({'status': 'keepalive'})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/result/<task_id>")
def result(task_id):
    """Serve the downloaded file for a completed task."""
    with tasks_lock:
        task = tasks.get(task_id)

    if not task:
        return jsonify({"error": "Task not found."}), 404

    if task["status"] == "error":
        return jsonify({"error": task["error"]}), 500

    if task["status"] != "done" or not task["result"]:
        return jsonify({"error": "Task not ready yet."}), 202

    buffer, filename, mimetype = task["result"]
    buffer.seek(0)

    # Clean up the task after serving
    def cleanup():
        with tasks_lock:
            tasks.pop(task_id, None)

    response = send_file(
        buffer,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )

    # Schedule cleanup after response is sent
    @response.call_on_close
    def on_close():
        cleanup()

    return response


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
