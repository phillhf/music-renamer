"""Erkennung von Interpret/Titel aus Tags und Dateinamen sowie Normalisierung."""
import os
import re
import unicodedata

JUNK_VALUES = {"", "unknown", "unknown artist", "unknown album", "unbekannt",
               "unbekannter interpret", "artist", "title", "track", "various", "n/a", "none"}
JUNK_PATTERN = re.compile(r"^(track|titel|audiotrack|spur)\s*\d*$|https?://|www\.|\.(com|net|org|ru)\b", re.I)
GENERIC_FOLDERS = {"music", "musik", "mp3", "mp3s", "downloads", "download", "neuer ordner",
                   "new folder", "sammlung", "various", "various artists", "unsorted", "sonstiges"}
NOISE_BRACKET = re.compile(
    r"[\(\[\{][^\)\]\}]*(official|lyrics?|video|audio|hq|hd|\d{3}\s*kbps|www\.|\.com|\.net|free download)"
    r"[^\)\]\}]*[\)\]\}]", re.I)
COPY_SUFFIX = re.compile(r"(\s*[\(\[]\d{1,2}[\)\]]|\s+-\s*(kopie|copy)(\s*\(\d+\))?|\s+(kopie|copy))$", re.I)
TRACK_PREFIX = re.compile(r"^\s*(?:cd\s*\d+\s*)?\d{1,3}[\s.\-_)]+(?=\S)", re.I)
FEATURING = re.compile(r"\s*[\(\[]?\b(feat|ft|featuring)\b\.?.*$", re.I)
VERSION_NOISE = re.compile(r"[\(\[][^\)\]]*(remaster|album version|original version|explicit|mono|stereo)"
                           r"[^\)\]]*[\)\]]", re.I)
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def is_junk(value):
    value = (value or "").strip()
    return value.lower() in JUNK_VALUES or bool(JUNK_PATTERN.search(value))


def clean(value):
    """Tagwert oder leer, falls er nur ein Platzhalter ist."""
    return "" if is_junk(value) else value.strip()


def parse_filename(path):
    """Leitet (Interpret, Titel) aus Datei- und Ordnername ab."""
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = COPY_SUFFIX.sub("", stem.replace("_", " "))
    stem = NOISE_BRACKET.sub("", stem)
    stem = TRACK_PREFIX.sub("", stem)
    stem = re.sub(r"\s+", " ", stem).strip(" -.")
    parts = [p.strip() for p in re.split(r"\s+[-–—]\s+", stem) if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    if not stem or is_junk(stem):
        return "", ""
    folders = os.path.normpath(path).split(os.sep)[:-1]
    for folder in reversed(folders[-2:]):
        # Ordner wie "Album (1999)" oder "1999 - Album" sind kein Interpret
        if folder.lower() not in GENERIC_FOLDERS and not re.search(r"\d{4}|^cd\s*\d", folder, re.I):
            return folder, stem
    return "", stem


def identify(track):
    """Bester bekannter (Interpret, Titel) einer Datei: Tags vor Dateiname."""
    artist, title = clean(track.artist), clean(track.title)
    if artist and title:
        return artist, title
    parsed_artist, parsed_title = parse_filename(track.path)
    return artist or parsed_artist, title or parsed_title


def normalize(text):
    """Vergleichsform; 'Live' oder 'Remix' bleiben bewusst erhalten."""
    text = FEATURING.sub("", text or "")
    text = VERSION_NOISE.sub("", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"^the\s+", "", text)
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def safe_filename(name, limit=150):
    name = INVALID_FILENAME.sub("", name).strip()
    name = re.sub(r"\s+", " ", name).rstrip(". ")
    return name[:limit].rstrip(". ")
