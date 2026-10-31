"""Scannt die Sammlung und merkt sich die Ergebnisse in SQLite.

Der Cache ist nach Pfad, Größe und Änderungszeit geschlüsselt, damit ein
erneuter Lauf über eine große Sammlung nur geänderte Dateien anfasst.
"""
import hashlib
import os
import re
import sqlite3
from dataclasses import dataclass

from mutagen.flac import FLAC
from mutagen.mp3 import MP3

from . import system
from .i18n import t
from .job import job
from .tags import EXTENSIONS, open_audio, read_tags

SCHEMA_VERSION = 3
SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY, size INTEGER, mtime REAL,
    duration REAL, bitrate INTEGER,
    artist TEXT, title TEXT, album TEXT, albumartist TEXT, year TEXT, genre TEXT, track TEXT,
    has_cover INTEGER, has_lyrics INTEGER,
    audio_start INTEGER, audio_size INTEGER, audio_hash TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS lookups (key TEXT PRIMARY KEY, result TEXT);
"""
TRACK_COLUMNS = ("path", "size", "duration", "bitrate", "artist", "title", "album", "albumartist",
                 "year", "genre", "track", "has_cover", "has_lyrics", "audio_start", "audio_size",
                 "audio_hash")
KEY_SAMPLE = 1024 * 1024
READ_COLUMNS = ("duration", "bitrate", "artist", "title", "album", "albumartist", "year", "genre",
                "track", "has_cover", "has_lyrics", "audio_start", "audio_size", "audio_hash")


@dataclass
class Track:
    path: str
    size: int
    duration: float
    bitrate: int
    artist: str
    title: str
    album: str
    albumartist: str
    year: str
    genre: str
    track: str
    has_cover: int
    has_lyrics: int
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
    # Die Dateitabelle ist nur ein Cache; die Suchergebnisse bleiben erhalten
    if db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        db.execute("DROP TABLE IF EXISTS files")
        db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    db.executescript(SCHEMA)
    return db


def find_audio(root, exclude=None):
    exclude = system.fold(os.path.abspath(exclude)) if exclude else None
    for folder, subdirs, names in os.walk(root):
        if exclude:
            subdirs[:] = [d for d in subdirs if system.fold(
                os.path.abspath(os.path.join(folder, d))) != exclude]
        for name in names:
            if name.lower().endswith(EXTENSIONS):
                yield os.path.join(folder, name)


def audio_range(path):
    """Liefert (Start, Länge) der reinen MP3-Audiodaten ohne ID3-/APE-Tags."""
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


def audio_key(path):
    """Kennung des Audioinhalts; bleibt beim Umbenennen und bei MP3 auch beim Taggen gleich."""
    is_mp3 = path.lower().endswith(".mp3")
    start, length = audio_range(path) if is_mp3 else (0, os.path.getsize(path))
    return f"{length}:{hash_audio(path, start, min(length, KEY_SAMPLE))}"


def read_file(path):
    audio = open_audio(path)
    values = read_tags(audio)
    values.update(duration=audio.info.length, bitrate=getattr(audio.info, "bitrate", 0) or 0,
                  audio_hash=None)
    if isinstance(audio, MP3):
        values["audio_start"], values["audio_size"] = audio_range(path)
    else:
        # Nur MP3 lässt sich hier von den Tags trennen; sonst zählt die ganze Datei
        values["audio_start"], values["audio_size"] = 0, os.path.getsize(path)
    if isinstance(audio, FLAC) and audio.info.md5_signature:
        values["audio_hash"] = f"flac:{audio.info.md5_signature:032x}"
    return values


def scan(root, db, exclude=None, progress=print):
    """Bringt die Datenbank auf den Stand der Sammlung; gibt Fehlerliste zurück."""
    known = {row[0]: (row[1], row[2]) for row in
             db.execute("SELECT path, size, mtime FROM files WHERE path LIKE ? ESCAPE '\\'",
                        (_prefix(root),))}
    seen, errors, read = set(), [], 0
    paths = list(find_audio(root, exclude))
    for number, path in enumerate(paths, 1):
        job.step(number, len(paths), t("Sammlung lesen"))
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
        row = dict.fromkeys(READ_COLUMNS)
        error = None
        try:
            row = read_file(path)
        except Exception as exc:  # defekte Dateien dürfen den Lauf nicht abbrechen
            error = f"{type(exc).__name__}: {exc}"
            errors.append((path, error))
        marks = ",".join("?" * (len(READ_COLUMNS) + 4))
        db.execute(f"INSERT OR REPLACE INTO files (path, size, mtime, {', '.join(READ_COLUMNS)}, error)"
                   f" VALUES ({marks})",
                   (path, stat.st_size, stat.st_mtime, *[row[c] for c in READ_COLUMNS], error))
    for path in set(known) - seen:
        db.execute("DELETE FROM files WHERE path = ?", (path,))
    db.commit()
    return errors


def _prefix(root):
    escaped = re.sub(r"([\\%_])", r"\\\1", os.path.abspath(root))
    return escaped + "%"


def load_tracks(root, db):
    rows = db.execute(
        f"SELECT {', '.join(TRACK_COLUMNS)} FROM files"
        " WHERE error IS NULL AND audio_size IS NOT NULL AND path LIKE ? ESCAPE '\\'"
        " ORDER BY path", (_prefix(root),))
    return [Track(*[("" if v is None else v) for v in row]) for row in rows]
