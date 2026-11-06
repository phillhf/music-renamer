"""Metadaten aus MusicBrainz, ergänzt um iTunes (Genre) und optional AcoustID.

MusicBrainz erlaubt eine Anfrage pro Sekunde; jede Antwort landet im Cache,
sodass ein abgebrochener Lauf ohne Verlust weiterläuft. Reißt die Verbindung ab,
pausiert der Lauf und macht von selbst weiter, sobald sie wieder steht.
"""
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

from . import __version__
from .i18n import format_duration, t
from .job import job
from .library import audio_key
from .names import FEATURING, normalize
from .system import SSL_CONTEXT

USER_AGENT = f"MusicRenamer/{__version__} (https://github.com/phillhf/music-renamer)"
MB_URL = "https://musicbrainz.org/ws/2"
MIN_SIMILARITY = 0.85
MAX_DURATION_DIFF = 8.0
MAX_RECORDINGS = 5
MAX_RELEASES = 40
RETRIES = 4
RETRY_CODES = (429, 500, 502, 503, 504)
PAUSE_STEP = 30
SKIP_SECONDS = 600
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

_last_call = {}
_skip_until = {}


def _online():
    """Prüft an MusicBrainz, ob nur ein Zusatzdienst ausfällt oder das ganze Netz."""
    request = urllib.request.Request(f"{MB_URL}/genre/all?limit=1&fmt=json", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=15, context=SSL_CONTEXT) as response:
            json.loads(response.read())  # Eine WLAN-Anmeldeseite ist keine Verbindung
        return True
    except urllib.error.HTTPError:
        return True
    except (OSError, http.client.HTTPException, ValueError):
        return False


class InvalidKey(Exception):
    """AcoustID lehnt den Key ab, meist weil der Benutzer-Key statt des Anwendungs-Keys eingetragen ist."""


def _service_message(exc):
    """Die Begründung, die ein Dienst einer Ablehnung mitgibt, etwa "invalid API key"."""
    try:
        error = json.loads(exc.read()).get("error")
    except Exception:
        return ""
    return str(error.get("message", "") if isinstance(error, dict) else error or "")


def _report_back(host, paused):
    if paused:
        print(t("Verbindung zu {host} wieder da nach {time}, es geht weiter.", host=host, time=format_duration(time.monotonic() - paused)))


def _fetch(url, min_interval, data=None, headers=None, check=None, optional=False):
    """Holt eine Antwort und wartet Ausfälle ab, ohne Begrenzung und bis zum Abbrechen.

    Ein optionaler Dienst hält den Lauf nur auf, wenn das ganze Netz weg ist; fällt er
    allein aus, gibt es ConnectionError und er wird eine Weile nicht mehr gefragt.
    """
    host = urllib.parse.urlparse(url).netloc
    if optional and time.monotonic() < _skip_until.get(host, 0):
        raise ConnectionError(f"Keine Antwort von {host}")
    failures, paused = 0, None
    while True:
        wait = _last_call.get(host, 0) + min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.monotonic()
        request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=30, context=SSL_CONTEXT) as response:
                content = response.read()
            if check:
                check(content)
            _report_back(host, paused)
            return content
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                _report_back(host, paused)
                return None
            if exc.code not in RETRY_CODES:
                detail = _service_message(exc)
                if detail:
                    exc.msg = f"{exc.msg}, {host}: {detail}"
                if optional:
                    raise ConnectionError(f"{host}: {exc}") from exc
                raise
        # Abgerissene Antworten kommen nicht als URLError, eine WLAN-Anmeldeseite als gültige Antwort
        except (OSError, http.client.HTTPException, ValueError):
            pass
        failures += 1
        if failures < RETRIES:
            job.wait(2 ** failures)
            continue
        if optional and not paused and _online():
            _skip_until[host] = time.monotonic() + SKIP_SECONDS
            print(t("{host} antwortet nicht und wird 10 Minuten ausgelassen. Fehlende Cover und Songtexte holt ein erneuter Lauf nach.", host=host))
            raise ConnectionError(f"Keine Antwort von {host}")
        if not paused:
            paused = time.monotonic()
            print(t("Achtung: keine Verbindung zu {host}. Pausiert, es geht von selbst weiter, sobald sie wieder steht.", host=host))
        job.notice(t("Pausiert, keine Verbindung zu {host} seit {time}", host=host, time=format_duration(time.monotonic() - paused)))
        job.wait(PAUSE_STEP)


def _get(url, min_interval, data=None, optional=False):
    content = _fetch(url, min_interval, data, check=json.loads, optional=optional)
    return json.loads(content) if content else None


def fetch_cover(group_id):
    """Vorderes Cover eines Albums von der Cover Art Archive oder None, ConnectionError bei Ausfall."""
    image = _fetch(f"https://coverartarchive.org/release-group/{group_id}/front-500", 0.5, optional=True)
    return image if image and image[:3] in (b"\xff\xd8\xff", b"\x89PN") else None


def fetch_lyrics(artist, title, album, duration):
    """Songtext von LRCLIB oder ein leerer Text, ConnectionError bei Ausfall."""
    params = urllib.parse.urlencode({"artist_name": artist, "track_name": title, "album_name": album,
                                     "duration": round(duration or 0)})
    data = _get(f"https://lrclib.net/api/get?{params}", 0.3, optional=True) or {}
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


def _medium(release):
    """CD-Nummer und Titelzahl der CD, auf der die Aufnahme liegt."""
    media = release.get("media") or [{}]
    return str(media[0].get("position") or ""), str(media[0].get("track-count") or "")


def _release_entry(release):
    """Das Wenige, was die Album-Erkennung je Veröffentlichung braucht."""
    disc, tracks = _medium(release)
    return {"group": release.get("release-group", {}).get("id", ""), "title": release.get("title", ""),
            "date": release.get("date") or "", "track": _track_number(release),
            "rank": sum(_release_rank(release)[:3]), "id": release.get("id", ""), "disc": disc, "tracks": tracks}


def _release_details(data):
    labels = [info["label"]["name"] for info in data.get("label-info") or []
              if (info.get("label") or {}).get("name") and info["label"]["name"] != "[no label]"]
    return {"discs": str(len(data.get("media") or []) or ""), "label": labels[0] if labels else "",
            "albumartist": _credit(data)}


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
    disc, tracks = _medium(release)
    return {"artist": _credit(recording), "title": recording.get("title", ""),
            "release_id": release.get("id", ""), "disc": disc, "tracks": tracks,
            "album": release.get("title", ""), "year": date[:4],
            "genre": _top_genre(recording), "track": _track_number(release),
            "source": source, "group": release.get("release-group", {}).get("id", ""),
            # Beliebte Titel stehen auf Hunderten Samplern, das Album darf nicht herausfallen
            "releases": [_release_entry(r) for r in
                         sorted(recording.get("releases") or [], key=_release_rank)[:MAX_RELEASES]],
            "artist_id": (recording.get("artist-credit") or [{}])[0].get("artist", {}).get("id", "")}


def _search_mb(artist, title, duration):
    escape = lambda s: re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r"\\\1", s)
    # "Stan (ft. Dido)" findet MusicBrainz nur ohne den Gast, der Abgleich danach prüft ihn ohnehin nicht
    plain = lambda s: FEATURING.sub("", s).strip() or s
    query = f'recording:"{escape(plain(title))}" AND artist:"{escape(plain(artist))}"'
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
    data = _get(f"https://itunes.apple.com/search?{params}", 3.2, optional=True) or {}
    for item in data.get("results", []):
        if _similar(item.get("artistName", ""), artist) >= MIN_SIMILARITY \
                and _similar(item.get("trackName", ""), title) >= MIN_SIMILARITY:
            return item
    return None


def _discogs(artist, title, token):
    """Zweite Quelle für das, was MusicBrainz nicht kennt."""
    params = urllib.parse.urlencode({"artist": artist, "track": title, "type": "release", "per_page": 10})
    content = _fetch(f"https://api.discogs.com/database/search?{params}", 1.1,
                     headers={"Authorization": f"Discogs token={token}"}, optional=True)
    for item in json.loads(content or "{}").get("results", []):
        found_artist, separator, album = item.get("title", "").partition(" - ")
        # Discogs hängt bei gleichnamigen Künstlern eine Nummer an: "Nirvana (2)"
        found_artist = re.sub(r"\s*\(\d+\)$", "", found_artist)
        if separator and _similar(found_artist, artist) >= MIN_SIMILARITY:
            return {"artist": found_artist, "title": title, "album": album, "year": str(item.get("year") or ""),
                    "genre": (item.get("genre") or [""])[0], "track": "", "source": "discogs",
                    "group": "", "releases": [], "score": ""}
    return None


def find_fpcalc():
    # sys._MEIPASS ist der Programmordner der installierten Version
    folders = (getattr(sys, "_MEIPASS", ""), os.path.join(PROJECT_DIR, "tools"))
    for folder in folders:
        bundled = os.path.join(folder, "fpcalc.exe" if os.name == "nt" else "fpcalc")
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
    try:
        data = _get("https://api.acoustid.org/v2/lookup", 0.4, data=body) or {}
    except urllib.error.HTTPError as exc:
        if "invalid api key" in str(exc).lower():
            raise InvalidKey() from exc
        raise
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
        self.discogs_token = os.environ.get("DISCOGS_TOKEN", "")
        self.min_score = parse_accuracy(level)
        self.remembered = 0

    def find(self, path, artist, title, duration):
        """Liefert die Metadaten, ein Dict mit "rejected" oder None, wenn nichts passt."""
        result = self._by_name(artist, title, duration)
        if result:
            return result
        # Der Klang ist sicherer als ein zweiter Namensabgleich, darum zuerst AcoustID
        result = self._by_sound(path) if self.fpcalc else None
        if (not result or result.get("rejected")) and self.discogs_token:
            return self._by_discogs(artist, title) or result
        return result

    def release(self, release_id):
        """Label, CD-Zahl und Album-Interpret einer Veröffentlichung; eine Abfrage je Album."""
        key = f"release:{release_id}"
        cached = self.cache.get(key)
        if cached is None:
            data = _get(f"{MB_URL}/release/{release_id}?inc=labels+artist-credits+media&fmt=json", 1.1) or {}
            cached = _release_details(data)
            self.cache.set(key, cached)
        return cached

    def _by_discogs(self, artist, title):
        if not (artist and title):
            return None
        key = f"discogs:{normalize(artist)}|{normalize(title)}"
        cached = self.cache.get(key)
        if cached is None:
            try:
                cached = _discogs(artist, title, self.discogs_token) or {}
            except ConnectionError:  # Zum Beispiel ein ungültiges Token
                return None
            self.cache.set(key, cached)
        return cached or None

    def _by_name(self, artist, title, duration):
        if not (artist and title):
            return {}
        key = f"song:{normalize(artist)}|{normalize(title)}|{round((duration or 0) / 10)}"
        cached = self.cache.get(key)
        if cached is not None:
            self.remembered += 1
            return cached
        found = _search_mb(artist, title, duration) or _search_mb(title, artist, duration)
        result = self._details(found[1], "musicbrainz", found[0]) if found else {}
        self.cache.set(key, result)
        return result

    def _by_sound(self, path):
        # Am Audioinhalt gemerkt, damit Umbenennen keine neue Analyse auslöst
        key = f"acoustid:{audio_key(path)}"
        entry = self.cache.get(key)
        if not entry:
            try:
                score, recording = _acoustid(path, self.api_key, self.fpcalc)
            except InvalidKey:
                # Einmal melden und ohne Klangerkennung weitersuchen, statt jede Datei scheitern zu lassen
                print(t("AcoustID lehnt den eingetragenen Key ab. Nötig ist der Key einer Anwendung, nicht der persönliche Benutzer-Key. Die Suche läuft ohne Klangerkennung weiter."))
                self.fpcalc = None
                return None
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
            try:
                item = _itunes(result["artist"], result["title"])
            except ConnectionError:
                item = None
            if item:
                result["genre"] = result["genre"] or item.get("primaryGenreName", "")
                result["year"] = result["year"] or item.get("releaseDate", "")[:4]
        return result
