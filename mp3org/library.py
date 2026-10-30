"""Scannt die Sammlung und merkt sich die Ergebnisse in SQLite.

Der Cache ist nach Pfad, Größe und Änderungszeit geschlüsselt, damit ein
erneuter Lauf über eine große Sammlung nur geänderte Dateien anfasst.
"""
import hashlib
import os
import re
import sqlite3
from dataclasses import dataclass

from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY, size INTEGER, mtime REAL,
    duration REAL, bitrate INTEGER,
    artist TEXT, title TEXT, album TEXT, year TEXT, genre TEXT, track TEXT,
    audio_start INTEGER, audio_size INTEGER, audio_hash TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS lookups (key TEXT PRIMARY KEY, result TEXT);
"""


@dataclass
class Track:
    path: str
    size: int
    duration: float
    bitrate: int
    artist: str
    title: str
    album: str
    year: str
    genre: str
    track: str
    audio_start: int
    audio_size: int
    audio_hash: str

    @property
    def tag_count(self):
        return sum(bool(v) for v in (self.artist, self.title, self.album,
                                     self.year, self.genre, self.track))


def connect(db_path):
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    db = sqlite3.connect(db_path)
    db.executescript(SCHEMA)
    return db


def find_mp3s(root, exclude=None):
    exclude = os.path.normcase(os.path.abspath(exclude)) if exclude else None
    for folder, subdirs, names in os.walk(root):
        if exclude:
            subdirs[:] = [d for d in subdirs if os.path.normcase(
                os.path.abspath(os.path.join(folder, d))) != exclude]
        for name in names:
            if name.lower().endswith(".mp3"):
                yield os.path.join(folder, name)


def audio_range(path):
    """Liefert (Start, Länge) der reinen Audiodaten ohne ID3-/APE-Tags."""
    size = os.path.getsize(path)
    start, end = 0, size
    with open(path, "rb") as f:
        head = f.read(10)
        if len(head) == 10 and head[:3] == b"ID3":
            tag_size = (head[6] << 21) | (head[7] << 14) | (head[8] << 7) | head[9]
            start = 10 + tag_size + (10 if head[5] & 0x10 else 0)
        if size >= 128:
            f.seek(-128, os.SEEK_END)
            if f.read(3) == b"TAG":
                end -= 128
        if end - start >= 32:
            f.seek(end - 32)
            footer = f.read(32)
            if footer[:8] == b"APETAGEX":
                ape_size = int.from_bytes(footer[12:16], "little")
                has_header = footer[23] & 0x80
                end -= ape_size + (32 if has_header else 0)
    return start, max(0, end - start)


def hash_audio(path, start, length):
    digest = hashlib.sha1()
    with open(path, "rb") as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            chunk = f.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def _first(tags, frame):
    value = tags.get(frame)
    return str(value.text[0]).strip() if value and value.text else ""


def read_file(path):
    audio = MP3(path)
    tags = audio.tags or {}
    start, length = audio_range(path)
    year = _first(tags, "TDRC") or _first(tags, "TYER")
    track = _first(tags, "TRCK")
    return {
        "duration": audio.info.length, "bitrate": audio.info.bitrate,
        "artist": _first(tags, "TPE1"), "title": _first(tags, "TIT2"),
        "album": _first(tags, "TALB"), "year": year[:4],
        "genre": _first(tags, "TCON"), "track": track,
        "audio_start": start, "audio_size": length,
    }


def scan(root, db, exclude=None, progress=print):
    """Bringt die Datenbank auf den Stand der Sammlung; gibt Fehlerliste zurück."""
    known = {row[0]: (row[1], row[2]) for row in
             db.execute("SELECT path, size, mtime FROM files WHERE path LIKE ? ESCAPE '\\'",
                        (_prefix(root),))}
    seen, errors, read = set(), [], 0
    for path in find_mp3s(root, exclude):
        seen.add(path)
        try:
            stat = os.stat(path)
        except OSError as exc:
            errors.append((path, str(exc)))
            continue
        if known.get(path) == (stat.st_size, stat.st_mtime):
            continue
        read += 1
        if read % 500 == 0:
            progress(f"  {read} Dateien gelesen ...")
        row = dict.fromkeys(("duration", "bitrate", "artist", "title", "album", "year",
                             "genre", "track", "audio_start", "audio_size"))
        error = None
        try:
            row = read_file(path)
        except ID3NoHeaderError:
            pass
        except Exception as exc:  # defekte Dateien dürfen den Lauf nicht abbrechen
            error = f"{type(exc).__name__}: {exc}"
            errors.append((path, error))
        db.execute(
            "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,?)",
            (path, stat.st_size, stat.st_mtime, row["duration"], row["bitrate"],
             row["artist"], row["title"], row["album"], row["year"], row["genre"],
             row["track"], row["audio_start"], row["audio_size"], error))
    for path in set(known) - seen:
        db.execute("DELETE FROM files WHERE path = ?", (path,))
    db.commit()
    return errors


def _prefix(root):
    escaped = re.sub(r"([\\%_])", r"\\\1", os.path.abspath(root))
    return escaped + "%"


def load_tracks(root, db):
    rows = db.execute(
        "SELECT path, size, duration, bitrate, artist, title, album, year, genre, track,"
        " audio_start, audio_size, audio_hash FROM files"
        " WHERE error IS NULL AND audio_size IS NOT NULL AND path LIKE ? ESCAPE '\\'"
        " ORDER BY path", (_prefix(root),))
    return [Track(*[("" if v is None else v) for v in row]) for row in rows]
