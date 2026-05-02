# jiosaavn-dl web app
# Flask backend for the JioSaavn downloader

import os
import io
import re
import zipfile
import tempfile
from flask import Flask, render_template, request, send_file, jsonify
from jiosaavn import Jiosaavn, album_song_rx, playlist_rx

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "No URL provided."}), 400

    url = data["url"].strip()
    add_numbers = data.get("addNumbers", False)
    download_cover = data.get("downloadCover", False)

    # Validate URL
    is_song_or_album = "/album/" in url or "/song/" in url
    is_playlist = "/playlist/" in url or "/featured/" in url

    if not (is_song_or_album or is_playlist):
        return jsonify({"error": "Invalid URL. Please provide a valid JioSaavn song, album, or playlist link."}), 400

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            jiosaavn = Jiosaavn(
                add_numbers=add_numbers,
                download_cover=download_cover,
                output_dir=temp_dir,
            )

            # Process based on URL type
            if is_song_or_album:
                match = album_song_rx.search(url)
                if not match:
                    return jsonify({"error": "Could not parse the song/album URL."}), 400
                kind, id_ = match.groups()
                if kind == "song":
                    jiosaavn.processTrack(id_, None, 1, 1)
                elif kind == "album":
                    jiosaavn.processAlbum(id_)
            elif is_playlist:
                match = playlist_rx.search(url)
                if not match:
                    return jsonify({"error": "Could not parse the playlist URL."}), 400
                playlist_id = match.group(2)
                jiosaavn.processPlaylist(playlist_id)

            # Collect all .m4a files
            m4a_files = []
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    if f.endswith(".m4a"):
                        m4a_files.append(os.path.join(root, f))

            if not m4a_files:
                return jsonify({"error": "No tracks were downloaded. The content may be unavailable in your region."}), 404

            # Single file → send .m4a directly
            if len(m4a_files) == 1:
                file_path = m4a_files[0]
                file_name = os.path.basename(file_path)
                buffer = io.BytesIO()
                with open(file_path, "rb") as f:
                    buffer.write(f.read())
                buffer.seek(0)
                return send_file(
                    buffer,
                    mimetype="audio/mp4",
                    as_attachment=True,
                    download_name=file_name,
                )

            # Multiple files → zip into memory
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in m4a_files:
                    # Use relative path from temp_dir for clean zip structure
                    arcname = os.path.relpath(file_path, temp_dir)
                    zf.write(file_path, arcname)

            buffer.seek(0)

            # Build a zip filename from the folder name
            subdirs = [
                d for d in os.listdir(temp_dir)
                if os.path.isdir(os.path.join(temp_dir, d))
            ]
            zip_name = (subdirs[0] if subdirs else "jiosaavn-dl") + ".zip"

            return send_file(
                buffer,
                mimetype="application/zip",
                as_attachment=True,
                download_name=zip_name,
            )

    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
