# jiosaavn-dl
# made by bunnykek

import json
import requests
from html import unescape
from sanitize_filename import sanitize
import re
import os
import argparse
from mutagen.mp4 import MP4, MP4Cover


song_api = "https://www.jiosaavn.com/api.php?__call=webapi.get&token={}&type=song"
album_api = "https://www.jiosaavn.com/api.php?__call=webapi.get&token={}&type=album"
playlist_api = "https://www.jiosaavn.com/api.php?__call=webapi.get&token={}&type=playlist&_format=json&n=1000"
lyrics_api = "https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&ctx=web6dot0&api_version=4&_format=json&_marker=0%3F_marker%3D0&lyrics_id="
album_song_rx = re.compile("https://www\.jiosaavn\.com/(album|song)/.+?/(.+)")
playlist_rx = re.compile(
    "https://www\.jiosaavn\.com/(s/playlist|featured)/.+/(.+)")
json_rx = re.compile("({.+})")

logo = """
           /$$            /$$$$$$                                                         /$$ /$$
          |__/           /$$__  $$                                                       | $$| $$
       /$$ /$$  /$$$$$$ | $$  \__/  /$$$$$$   /$$$$$$  /$$    /$$ /$$$$$$$           /$$$$$$$| $$
      |__/| $$ /$$__  $$|  $$$$$$  |____  $$ |____  $$|  $$  /$$/| $$__  $$ /$$$$$$ /$$__  $$| $$
       /$$| $$| $$  \ $$ \____  $$  /$$$$$$$  /$$$$$$$ \  $$/$$/ | $$  \ $$|______/| $$  | $$| $$
      | $$| $$| $$  | $$ /$$  \ $$ /$$__  $$ /$$__  $$  \  $$$/  | $$  | $$        | $$  | $$| $$
      | $$| $$|  $$$$$$/|  $$$$$$/|  $$$$$$$|  $$$$$$$   \  $/   | $$  | $$        |  $$$$$$$| $$
      | $$|__/ \______/  \______/  \_______/ \_______/    \_/    |__/  |__/         \_______/|__/
 /$$  | $$                                                                                       
|  $$$$$$/                                                                             --by @bunnykek
 \______/                                                                                        
"""


def clear() -> None:
    """ Clears The Console Of All Text """
    os.system('clear' if os.name == 'posix' else 'cls')


class Jiosaavn:
    def __init__(self, add_numbers=False, download_cover=False, output_dir="Downloads", progress_callback=None) -> None:
        self.session = requests.Session()
        self.add_numbers = add_numbers
        self.download_cover = download_cover
        self.output_dir = output_dir
        self.progress_callback = progress_callback

    def _report_progress(self, message, current=0, total=0):
        """Report progress to callback if set."""
        if self.progress_callback:
            self.progress_callback(message, current, total)

    # Metadata-only methods (no download) for preview
    def getTrackInfo(self, song_id):
        """Fetch track metadata without downloading."""
        metadata = self.session.get(song_api.format(song_id)).text
        metadata = json.loads(json_rx.search(metadata).group(1))
        song_json = metadata[f'{list(metadata.keys())[0]}']
        return {
            'type': 'song',
            'title': unescape(song_json.get('song', '')),
            'album': unescape(song_json.get('album', '')),
            'artists': unescape(song_json.get('primary_artists', '')),
            'year': str(song_json.get('year', '')),
            'image': song_json.get('image', '').replace('150x150', '500x500'),
            'language': song_json.get('language', '').title(),
            'has_lyrics': song_json.get('has_lyrics', 'false') == 'true',
            'tracks': [{
                'title': unescape(song_json.get('song', '')),
                'artists': unescape(song_json.get('primary_artists', '')),
                'duration': song_json.get('duration', '0'),
            }],
            'total_tracks': 1,
        }

    def getAlbumInfo(self, album_id):
        """Fetch album metadata without downloading."""
        album_json = self.session.get(album_api.format(album_id)).text
        album_json = json.loads(json_rx.search(album_json).group(1))
        tracks = []
        for song in album_json.get('songs', []):
            tracks.append({
                'title': unescape(song.get('song', '')),
                'artists': unescape(song.get('primary_artists', '')),
                'duration': song.get('duration', '0'),
            })
        return {
            'type': 'album',
            'title': unescape(album_json.get('title', '')),
            'artists': album_json.get('primary_artists', ''),
            'year': str(album_json.get('year', '')),
            'image': album_json.get('image', '').replace('150x150', '500x500'),
            'language': album_json.get('language', '').title(),
            'tracks': tracks,
            'total_tracks': len(tracks),
        }

    def getPlaylistInfo(self, playlist_id):
        """Fetch playlist metadata without downloading."""
        playlist_json = self.session.get(playlist_api.format(playlist_id)).text
        playlist_json = json.loads(json_rx.search(playlist_json).group(1))
        tracks = []
        for song in playlist_json.get('songs', []):
            tracks.append({
                'title': unescape(song.get('song', '')),
                'artists': unescape(song.get('primary_artists', '')),
                'duration': song.get('duration', '0'),
            })
        return {
            'type': 'playlist',
            'title': playlist_json.get('listname', ''),
            'image': playlist_json.get('image', '').replace('150x150', '500x500'),
            'tracks': tracks,
            'total_tracks': int(playlist_json.get('list_count', 0)),
        }

    # Tags metadata to a track
    def tagger(self, json, song_path, album_artist, album_path, pos=1, total=1):
        audio = MP4(song_path)
        audio["\xa9nam"] = sanitize(unescape(json["song"]))
        audio["\xa9alb"] = sanitize(unescape(json["album"]))
        audio["\xa9ART"] = sanitize(unescape(json["primary_artists"]))
        audio["\xa9wrt"] = sanitize(unescape(json["music"]))
        audio["aART"] = album_artist if album_artist else sanitize(
            unescape(json["primary_artists"]))
        audio["\xa9day"] = json["release_date"]  # json["year"]
        audio["----:TXXX:Record label"] = bytes(json["label"], 'UTF-8')
        audio["cprt"] = json["copyright_text"]
        audio["----:TXXX:Language"] = bytes(json["language"].title(), 'UTF-8')
        audio["rtng"] = [2 if json["explicit_content"] == 0 else 4]
        # audio["----:TXXX:URL"] = bytes(json["album_url"], 'UTF-8')
        audio["trkn"] = [(pos, total)]

        # if the song has lyrics then tag else skip
        if (json["has_lyrics"] == "true"):
            lyric_json = self.session.get(lyrics_api + json["id"]).json()
            audio["\xa9lyr"] = lyric_json["lyrics"].replace("<br>", "\n")

        # cover artwork tag
        with open(os.path.join(album_path, "cover.jpg"), "rb") as f:
            audio["covr"] = [
                MP4Cover(f.read(), imageformat=MP4Cover.FORMAT_JPEG)]

        # featured artists
        if len(json['featured_artists']) > 1:
            audio["----:TXXX:Featured artists"] = bytes(
                json["featured_artists"], 'UTF-8')

        # singers
        if len(json['singers']) > 1:
            audio["----:TXXX:Singers"] = bytes(json["singers"], 'UTF-8')

        # starring
        if len(json['starring']) > 1:
            audio["----:TXXX:Starring"] = bytes(json["starring"], 'UTF-8')

        audio.pop("©too")

        audio.save()  # tagging done

    def processAlbum(self, album_id):

        # sanitization
        album_json = self.session.get(album_api.format(album_id)).text
        album_json = json.loads(json_rx.search(album_json).group(1))

        album_name = sanitize(unescape(album_json['title']))
        album_artist = album_json['primary_artists']
        total_tracks = len(album_json['songs'])
        year = str(album_json['year'])

        album_info = f"\n\
                    Album info:\n\
                    Album name       : {album_name}\n\
                    Album artists    : {album_artist}\n\
                    Year             : {year}\n\
                    Number of tracks : {total_tracks}\n"
        print(album_info)
        self._report_progress(f"Processing album: {album_name}", 0, total_tracks)

        song_pos = 1
        for song in album_json['songs']:
            song_id = album_song_rx.search(song['perma_url']).group(2)
            self.processTrack(song_id, album_artist, song_pos, total_tracks)
            song_pos += 1

    def processTrack(self, song_id, album_artist=None, song_pos=1, total_tracks=1, isPlaylist=False):

        metadata = self.session.get(song_api.format(song_id)).text
        metadata = json.loads(json_rx.search(metadata).group(1))
        # print(metadata.keys())
        song_json = metadata[f'{list(metadata.keys())[0]}']

        # sanitize
        primary_artists = album_artist if album_artist else sanitize(
            unescape(song_json["primary_artists"]))
        track_name = sanitize(unescape(song_json['song']))
        album = sanitize(unescape(song_json['album']))
        year = str(unescape(song_json['year']))

        # setting up the song directory
        if isPlaylist:
            folder_name = isPlaylist
        else:
            folder_name = f"{primary_artists if primary_artists.count(',') < 2 else 'Various Artists'} - {album} [{year}]"
        song_name = f"{str(song_pos).zfill(2)}. {track_name}.m4a" if self.add_numbers else f"{track_name}.m4a"

        album_path = os.path.join(self.output_dir, folder_name)
        song_path = os.path.join(self.output_dir, folder_name, song_name)

        try:
            os.makedirs(album_path)
        except:
            pass

        song_info = f"\n\
                    Track info:\n\
                    Song name      : {song_json['song']}\n\
                    Artist(s) name : {song_json['primary_artists']}\n\
                    Album name     : {song_json['album']}\n\
                    Year           : {song_json['year']}\n"

        print(song_info)
        self._report_progress(f"Downloading: {track_name}", song_pos, total_tracks)

        # checking if the cover already exists - always download for tagging
        cover_path = os.path.join(album_path, "cover.jpg")
        if not os.path.exists(cover_path) or isPlaylist:
            print("\nDownloading the cover...")
            with open(cover_path, "wb") as f:
                f.write(self.session.get(
                    song_json["image"].replace("150", "500")).content)

        # checking if the song already exists in the directory
        if (os.path.exists(song_path)):
            print(f"{song_name} already downloaded.")
            self._report_progress(f"Already downloaded: {track_name}", song_pos, total_tracks)
        else:
            print(f"Downloading : {song_name}...")

            # checking if the song is available in the region, if yes then proceed to download else prompt the unavailability
            if 'encrypted_media_url' in song_json:
                cdnURL: str = self.getCdnURL(song_json["encrypted_media_url"])
                # fix cdn url
                cdnURL = cdnURL.replace('web', 'aac', 1)
                # download the song
                with open(song_path, "wb") as f:
                    f.write(self.session.get(cdnURL).content)

                self._report_progress(f"Tagging: {track_name}", song_pos, total_tracks)
                print("Tagging metadata...")

                self.tagger(song_json, song_path, album_artist,
                            album_path, song_pos, total_tracks)

                # Delete cover if not needed
                if not self.download_cover:
                    cover_path = os.path.join(album_path, "cover.jpg")
                    if os.path.exists(cover_path):
                        os.remove(cover_path)

                self._report_progress(f"Done: {track_name}", song_pos, total_tracks)
                print("Done.")
            else:
                self._report_progress(f"Unavailable in your region: {track_name}", song_pos, total_tracks)
                print("\nTrack unavailable in your region!")

    def getCdnURL(self, encurl: str):
        params = {
            '__call': 'song.generateAuthToken',
            'url': encurl,
            'bitrate': '320',
            'api_version': '4',
            '_format': 'json',
            'ctx': 'web6dot0',
            '_marker': '0',
        }
        response = self.session.get(
            'https://www.jiosaavn.com/api.php', params=params)
        return response.json()["auth_url"]

    def processPlaylist(self, playlist_id):
        # json

        playlist_json = self.session.get(playlist_api.format(playlist_id)).text
        playlist_json = json.loads(json_rx.search(playlist_json).group(1))
        # print(json.dumps(playlist_json, indent=4))
        playlist_name = playlist_json['listname']
        total_tracks = int(playlist_json['list_count'])
        playlist_path = f"Playlist - {playlist_name}"
        playlist_info = f"\n\
                            Playlist info:\n\
                            Playlist name    : {playlist_name}\n\
                            Number of tracks : {total_tracks}\n"
        print(playlist_info)
        self._report_progress(f"Processing playlist: {playlist_name}", 0, total_tracks)

        song_pos = 1
        for song in playlist_json['songs']:
            song_id = album_song_rx.search(song['perma_url']).group(2)
            self.processTrack(song_id, None, song_pos,
                              total_tracks, playlist_path)
            song_pos += 1


if __name__ == "__main__":
    clear()
    print(logo)

    parser = argparse.ArgumentParser(
        description="Downloads songs/albums/playlist from JioSaavn")
    parser.add_argument("url", nargs='?',
                        default="link to a song/album/playlist",
                        help="Song/album/playlist URL (optional)")
    parser.add_argument("--with-numbers", action="store_true",
                        help="Enable track numbering in filenames")
    parser.add_argument("--with-cover", action="store_true",
                        help="Download cover images")
    args = parser.parse_args()

    url = args.url

    jiosaavn = Jiosaavn(add_numbers=args.with_numbers,
                        download_cover=args.with_cover)

    # handles album URL
    if ("/album/" in url or "/song/" in url):

        kind, id_ = album_song_rx.search(url).groups()

        if kind == 'song':
            jiosaavn.processTrack(id_, None, 1, 1)
        elif kind == 'album':
            jiosaavn.processAlbum(id_)
    elif '/playlist/' in url or '/featured/' in url:
        playlist_id = playlist_rx.search(url).group(2)
        jiosaavn.processPlaylist(playlist_id)
    else:
        print("Please enter a valid link!")
