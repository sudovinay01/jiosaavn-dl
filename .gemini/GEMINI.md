# GEMINI.md — Project Context for AI Assistants

## Project Overview

**jiosaavn-dl** is a command-line Python tool that downloads music tracks, albums, and playlists from [JioSaavn](https://www.jiosaavn.com/). It fetches audio in the highest available quality (320 kbps AAC in an M4A container) and automatically tags files with metadata, lyrics, and cover art.

**Author:** bunnykek

## Tech Stack

- **Language:** Python 3.13+
- **Key Dependencies** (`requirements.txt`):
  - `requests` — HTTP client for JioSaavn API calls and media downloads
  - `mutagen` — Audio metadata tagging (MP4/M4A)
  - `sanitize_filename` — Safe filename generation

## Repository Structure

```
jiosaavn-dl/
├── jiosaavn.py          # Main script — CLI entry point + Jiosaavn class
├── requirements.txt     # Python dependencies
├── .gitignore           # Ignores .venv and Downloads/
├── assets/              # Logo and screenshot assets for README
├── README.md            # User-facing documentation
└── Downloads/           # Output directory for downloaded tracks (git-ignored)
```

## Architecture

The entire application lives in a single file: `jiosaavn.py`.

### Core Class: `Jiosaavn`

- **`__init__(add_numbers, download_cover)`** — Initialises a `requests.Session` and config flags.
- **`processTrack(song_id, ...)`** — Downloads a single track, saves to `Downloads/`, and tags it.
- **`processAlbum(album_id)`** — Fetches album metadata, iterates through all songs calling `processTrack`.
- **`processPlaylist(playlist_id)`** — Fetches playlist metadata, iterates through all songs calling `processTrack`.
- **`tagger(json, song_path, ...)`** — Applies metadata (title, artist, album, lyrics, cover art, etc.) to the M4A file using `mutagen`.
- **`getCdnURL(encurl)`** — Calls JioSaavn's auth token API to resolve encrypted media URLs to downloadable CDN URLs.

### API Endpoints Used

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

- `<URL>` — JioSaavn song, album, or playlist URL
- `--with-numbers` — Prefix filenames with zero-padded track numbers
- `--with-cover` — Keep `cover.jpg` in the album folder after tagging

### Output

Downloaded files are saved to `Downloads/<Artist - Album [Year]>/` (or `Downloads/Playlist - <Name>/` for playlists).

## Development Notes

- **No tests** currently exist in the repo.
- **No virtual environment** is checked in; create one with `python -m venv .venv` and install deps via `pip install -r requirements.txt`.
- The codebase uses `\r\n` (Windows-style) line endings in `jiosaavn.py`.
- `os.makedirs` errors are silently caught with a bare `except` — this could mask real errors.
- The script clears the console on every run (`clear()`/`cls`).

## Coding Conventions

- Keep it as a single-file CLI tool unless refactoring is explicitly requested.
- Use `sanitize()` and `unescape()` on any user-facing strings from the API.
- Maintain compatibility with Python 3.13+.
- Follow existing patterns: method names use camelCase (e.g., `processTrack`, `getCdnURL`).
