# GEMINI.md — Project Context for AI Assistants

## Project Overview

**jiosaavn-dl** is a command-line Python tool (and web app) that downloads music tracks, albums, and playlists from [JioSaavn](https://www.jiosaavn.com/). It fetches audio in the highest available quality (320 kbps AAC in an M4A container) and automatically tags files with metadata, lyrics, and cover art.

**Author:** bunnykek

## Tech Stack

- **Language:** Python 3.13+
- **Web Framework:** Flask
- **Key Dependencies** (`requirements.txt`):
  - `requests` — HTTP client for JioSaavn API calls and media downloads
  - `mutagen` — Audio metadata tagging (MP4/M4A)
  - `sanitize_filename` — Safe filename generation
  - `flask` — Web framework for the GUI

## Repository Structure

```
jiosaavn-dl/
├── jiosaavn.py          # Core library — Jiosaavn class (shared by CLI & web)
├── app.py               # Flask web app — routes & download logic
├── templates/
│   └── index.html       # Web UI — dark-themed single-page interface
├── requirements.txt     # Python dependencies
├── .gitignore           # Ignores .venv and Downloads/
├── assets/              # Logo and screenshot assets for README
├── README.md            # User-facing documentation
└── Downloads/           # Output directory for CLI downloads (git-ignored)
```

## Architecture

### Core Class: `Jiosaavn` (jiosaavn.py)

- **`__init__(add_numbers, download_cover, output_dir)`** — Initialises a `requests.Session`, config flags, and output directory (default: `"Downloads"`).
- **`processTrack(song_id, ...)`** — Downloads a single track, saves to `output_dir/`, and tags it.
- **`processAlbum(album_id)`** — Fetches album metadata, iterates through all songs calling `processTrack`.
- **`processPlaylist(playlist_id)`** — Fetches playlist metadata, iterates through all songs calling `processTrack`.
- **`tagger(json, song_path, ...)`** — Applies metadata (title, artist, album, lyrics, cover art, etc.) to the M4A file using `mutagen`.
- **`getCdnURL(encurl)`** — Calls JioSaavn's auth token API to resolve encrypted media URLs to downloadable CDN URLs.

### Web App: Flask (app.py)

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Serves the web UI |
| `/download` | POST | Accepts a JioSaavn URL, downloads tracks, returns .m4a or .zip |

**Download flow:**
1. Validate URL → create `TemporaryDirectory` → process tracks
2. Single track → send `.m4a` directly
3. Multiple tracks → zip in memory via `BytesIO` → send `.zip`
4. `TemporaryDirectory` auto-cleans on context exit

### API Endpoints Used (JioSaavn)

| Purpose          | Endpoint Pattern |
|------------------|-----------------|
| Song metadata    | `api.php?__call=webapi.get&type=song` |
| Album metadata   | `api.php?__call=webapi.get&type=album` |
| Playlist metadata| `api.php?__call=webapi.get&type=playlist` |
| Lyrics           | `api.php?__call=lyrics.getLyrics` |
| CDN auth token   | `api.php?__call=song.generateAuthToken` |

### CLI Usage

```bash
python jiosaavn.py <URL> [--with-numbers] [--with-cover]
```

### Web App Usage

```bash
python app.py
# Open http://localhost:5000
```

## Development Notes

- **Virtual environment:** Create with `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
- **No tests** currently exist in the repo.
- The codebase uses `\r\n` (Windows-style) line endings in `jiosaavn.py`.
- `os.makedirs` errors are silently caught with a bare `except` — this could mask real errors.
- The CLI script clears the console on every run (`clear()`/`cls`).

## Coding Conventions

- Keep `jiosaavn.py` as the core library, `app.py` as the web layer.
- Use `sanitize()` and `unescape()` on any user-facing strings from the API.
- Maintain compatibility with Python 3.13+.
- Follow existing patterns: method names use camelCase (e.g., `processTrack`, `getCdnURL`).
