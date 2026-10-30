"""Metadaten aus MusicBrainz, ergänzt um iTunes (Genre) und optional AcoustID.

MusicBrainz erlaubt eine Anfrage pro Sekunde; jede Antwort landet im Cache,
sodass ein abgebrochener Lauf ohne Verlust weiterläuft.
"""
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

from . import __version__
from .names import normalize

USER_AGENT = f"MP3Organizer/{__version__} (https://github.com/phillhf/mp3-organizer)"
MB_URL = "https://musicbrainz.org/ws/2"
MIN_SIMILARITY = 0.85
MAX_DURATION_DIFF = 8.0
MAX_RECORDINGS = 5
MAX_RELEASES = 40
# Mindestwert der Klangerkennung je Stufe
LEVELS = {"streng": 0.95, "normal": 0.85, "locker": 0.70}


def parse_accuracy(value):
    """Stufenname oder Prozentzahl wie "92" oder "92,5 %" als Wert von 0 bis 1."""
    if value in LEVELS:
        return LEVELS[value]
    try:
        percent = float(str(value).replace("%", "").replace(",", ".").strip())
    except ValueError:
        percent = 0
    if not 1 <= percent <= 100:
        raise ValueError(f"Ungültige Genauigkeit: {value} (erlaubt: {', '.join(LEVELS)} oder 1 bis 100)")
    return percent / 100


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Python 3.14 lehnt die Zertifikatskette von archive.org (dort liegen die Cover) wegen dieser
# Zusatzregel ab. Zertifikat und Hostname werden weiterhin geprüft.
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.verify_flags &= ~ssl.VERIFY_X509_STRICT

_last_call = {}


def _fetch(url, min_interval, data=None):
    host = urllib.parse.urlparse(url).netloc
    for attempt in range(4):
        wait = _last_call.get(host, 0) + min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.monotonic()
        request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30, context=SSL_CONTEXT) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(2 ** (attempt + 1))
    raise ConnectionError(f"Keine Antwort von {host}")


def _get(url, min_interval, data=None):
    content = _fetch(url, min_interval, data)
    return json.loads(content) if content else None


def fetch_cover(group_id):
    """Vorderes Cover eines Albums von der Cover Art Archive oder None."""
    try:
        image = _fetch(f"https://coverartarchive.org/release-group/{group_id}/front-500", 0.5)
    except ConnectionError:
        return None  # ein fehlendes Cover soll den Lauf nicht aufhalten
    return image if image and image[:3] in (b"\xff\xd8\xff", b"\x89PN") else None


def fetch_lyrics(artist, title, album, duration):
    """Songtext von LRCLIB oder ein leerer Text."""
    params = urllib.parse.urlencode({"artist_name": artist, "track_name": title, "album_name": album,
                                     "duration": round(duration or 0)})
    try:
        data = _get(f"https://lrclib.net/api/get?{params}", 0.3) or {}
    except ConnectionError:
        return ""
    return (data.get("plainLyrics") or "").strip()


def _similar(a, b):
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def _pick(candidates):
    """Wählt aus (Ähnlichkeit, Aufnahme)-Paaren die beste Aufnahme."""
    score, best = min(candidates, key=lambda c: _preference(*c))
    # Remaster sind eigene Aufnahmen; das Jahr soll die Erstveröffentlichung des Songs sein
    dates = [r["first-release-date"] for _, r in candidates if r.get("first-release-date")]
    if dates:
        best = {**best, "first-release-date": min(dates)}
    return score, best


def _credit(recording):
    return "".join(c.get("name", c.get("artist", {}).get("name", "")) + c.get("joinphrase", "")
                   for c in recording.get("artist-credit", []))


def _release_rank(release):
    group = release.get("release-group", {})
    return (release.get("status") != "Official", group.get("primary-type") != "Album",
            bool(group.get("secondary-types")), release.get("date") or "9999")


def _track_number(release):
    media = release.get("media") or []
    number = str(media[0]["track"][0].get("number", "")) if media and media[0].get("track") else ""
    return number if number.isdigit() else ""


def _release_entry(release):
    """Das Wenige, was die Album-Erkennung je Veröffentlichung braucht."""
    return {"group": release.get("release-group", {}).get("id", ""), "title": release.get("title", ""),
            "date": release.get("date") or "", "track": _track_number(release),
            "rank": sum(_release_rank(release)[:3])}


def _best_release(recording):
    """Bevorzugt das früheste offizielle Studioalbum."""
    releases = recording.get("releases") or []
    return min(releases, key=_release_rank) if releases else {}


def _preference(similarity, recording):
    """Sortierschlüssel: beste Namensgleichheit, dann Studioalbum, dann ältestes Datum."""
    release = _best_release(recording)
    return (-similarity, _release_rank(release)[:3] if release else (True, True, True),
            recording.get("first-release-date") or "9999")


def _top_genre(entity):
    entries = entity.get("genres") or entity.get("tags") or []
    entries = [e for e in entries if e.get("count", 0) > 0]
    if not entries:
        return ""
    return max(entries, key=lambda e: e["count"])["name"].title()


def _result_from(recording, source):
    release = _best_release(recording)
    date = recording.get("first-release-date") or release.get("date") or ""
    return {"artist": _credit(recording), "title": recording.get("title", ""),
            "album": release.get("title", ""), "year": date[:4],
            "genre": _top_genre(recording), "track": _track_number(release),
            "source": source, "group": release.get("release-group", {}).get("id", ""),
            # Beliebte Titel stehen auf Hunderten Samplern, das Album darf nicht herausfallen
            "releases": [_release_entry(r) for r in
                         sorted(recording.get("releases") or [], key=_release_rank)[:MAX_RELEASES]],
            "artist_id": (recording.get("artist-credit") or [{}])[0].get("artist", {}).get("id", "")}


def _search_mb(artist, title, duration):
    escape = lambda s: re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r"\\\1", s)
    query = f'recording:"{escape(title)}" AND artist:"{escape(artist)}"'
    # Beliebte Titel haben Hunderte Live-Mitschnitte, die sonst die Trefferliste füllen
    wants_live = "live" in normalize(title).split()
    if not wants_live:
        query += " AND NOT comment:live"
    url = f"{MB_URL}/recording?" + urllib.parse.urlencode({"query": query, "fmt": "json", "limit": 50})
    data = _get(url, 1.1) or {}
    candidates = []
    for recording in data.get("recordings", []):
        similarity = min(_similar(title, recording.get("title", "")),
                         _similar(artist, _credit(recording)))
        length = (recording.get("length") or 0) / 1000
        if similarity < MIN_SIMILARITY:
            continue
        if duration and length and abs(length - duration) > MAX_DURATION_DIFF:
            continue
        if not wants_live and "live" in (recording.get("disambiguation") or "").lower():
            continue
        candidates.append((round(similarity, 2), recording))
    return _pick(candidates) if candidates else None


def _artist_genre(artist_id, cache):
    if not artist_id:
        return ""
    key = f"artist-genre:{artist_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    data = _get(f"{MB_URL}/artist/{artist_id}?inc=genres+tags&fmt=json", 1.1) or {}
    genre = _top_genre(data)
    cache.set(key, genre)
    return genre


def _itunes(artist, title):
    params = urllib.parse.urlencode({"term": f"{artist} {title}", "media": "music",
                                     "entity": "song", "limit": 5, "country": "DE"})
    data = _get(f"https://itunes.apple.com/search?{params}", 3.2) or {}
    for item in data.get("results", []):
        if _similar(item.get("artistName", ""), artist) >= MIN_SIMILARITY \
                and _similar(item.get("trackName", ""), title) >= MIN_SIMILARITY:
            return item
    return None


def find_fpcalc():
    # sys._MEIPASS ist der Programmordner der installierten Version
    folders = (getattr(sys, "_MEIPASS", ""), os.path.join(PROJECT_DIR, "tools"))
    for folder in folders:
        bundled = os.path.join(folder, "fpcalc.exe")
        if folder and os.path.exists(bundled):
            return bundled
    return shutil.which("fpcalc")


def _acoustid(path, api_key, fpcalc):
    output = subprocess.run([fpcalc, "-json", path], capture_output=True, text=True, timeout=120,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if output.returncode != 0:
        return 0, None
    fingerprint = json.loads(output.stdout)
    body = urllib.parse.urlencode({
        "client": api_key, "duration": int(fingerprint["duration"]),
        "fingerprint": fingerprint["fingerprint"], "meta": "recordingids"}).encode()
    data = _get("https://api.acoustid.org/v2/lookup", 0.4, data=body) or {}
    # Die Schwelle wird erst beim Lesen angewendet, damit ein Stufenwechsel ohne neue Analyse geht
    for result in sorted(data.get("results", []), key=lambda r: -r.get("score", 0)):
        if result.get("recordings"):
            recordings = [_get(f"{MB_URL}/recording/{r['id']}?inc=artist-credits+releases+"
                               "release-groups+genres+tags&fmt=json", 1.1)
                          for r in result["recordings"][:MAX_RECORDINGS]]
            recordings = [r for r in recordings if r]
            if recordings:
                return result["score"], _pick([(1.0, r) for r in recordings])[1]
    return 0, None


class Cache:
    def __init__(self, db):
        self.db = db

    def get(self, key):
        row = self.db.execute("SELECT result FROM lookups WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO lookups VALUES (?, ?)", (key, json.dumps(value)))
        self.db.commit()


class Lookup:
    def __init__(self, db, level="normal"):
        self.cache = Cache(db)
        self.api_key = os.environ.get("ACOUSTID_KEY", "")
        self.fpcalc = find_fpcalc() if self.api_key else None
        self.min_score = parse_accuracy(level)

    def find(self, path, artist, title, duration):
        """Liefert die Metadaten, ein Dict mit "rejected" oder None, wenn nichts passt."""
        result = self._by_name(artist, title, duration)
        if result or not self.fpcalc:
            return result or None
        return self._by_sound(path)

    def _by_name(self, artist, title, duration):
        if not (artist and title):
            return {}
        key = f"song:{normalize(artist)}|{normalize(title)}|{round((duration or 0) / 10)}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        found = _search_mb(artist, title, duration) or _search_mb(title, artist, duration)
        result = self._details(found[1], "musicbrainz", found[0]) if found else {}
        self.cache.set(key, result)
        return result

    def _by_sound(self, path):
        key = f"acoustid:{path}"
        entry = self.cache.get(key)
        if not entry:
            score, recording = _acoustid(path, self.api_key, self.fpcalc)
            entry = {"score": score, "result": self._details(recording, "acoustid", score) if recording else {}}
            self.cache.set(key, entry)
        if not entry["result"]:
            return None
        if entry["score"] < self.min_score:
            return {"score": round(entry["score"] * 100), "rejected": True}
        return entry["result"]

    def _details(self, recording, source, score):
        result = _result_from(recording, source)
        result["score"] = round(score * 100)
        artist_id = result.pop("artist_id")
        if not result["genre"]:
            result["genre"] = _artist_genre(artist_id, self.cache)
        if not result["genre"] or not result["year"]:
            item = _itunes(result["artist"], result["title"])
            if item:
                result["genre"] = result["genre"] or item.get("primaryGenreName", "")
                result["year"] = result["year"] or item.get("releaseDate", "")[:4]
        return result
