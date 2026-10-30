"""Erkennt gleiche Aufnahmen am Klang, unabhängig von Format, Bitrate und Tags.

fpcalc erzeugt je Datei eine Folge von 32-Bit-Werten. Gleiche Aufnahmen stimmen darin
fast überall überein, fremde nur zufällig zu etwa der Hälfte der Bits. Ein Index über
die oberen Bits verhindert, dass jede Datei mit jeder verglichen werden muss.
"""
import json
import subprocess
from collections import Counter, defaultdict
from itertools import combinations

MIN_SIMILARITY = 0.85
MAX_DURATION_GAP = 5.0
MAX_OFFSET = 32        # etwa 4 Sekunden Versatz, z. B. durch Stille am Anfang
MIN_ITEMS = 40
MIN_SHARED = 3
MAX_FILES_PER_VALUE = 50  # häufige Werte (Stille) sagen nichts aus
SAMPLE_LENGTH = 120


def raw_fingerprint(path, fpcalc):
    output = subprocess.run([fpcalc, "-raw", "-json", "-length", str(SAMPLE_LENGTH), path],
                            capture_output=True, text=True, timeout=120,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if output.returncode != 0:
        return []
    return [value & 0xFFFFFFFF for value in json.loads(output.stdout).get("fingerprint", [])]


def similarity(a, b):
    """Anteil gleicher Bits beim besten Versatz, 0 bis 1."""
    best = 0.0
    for offset in range(-MAX_OFFSET, MAX_OFFSET + 1):
        x, y = a[max(offset, 0):], b[max(-offset, 0):]
        count = min(len(x), len(y))
        if count < MIN_ITEMS:
            continue
        # Jeder vierte Wert reicht und spart bei großen Sammlungen viel Zeit
        checked = range(0, count, 4)
        different = sum((x[i] ^ y[i]).bit_count() for i in checked)
        best = max(best, 1 - different / (32 * len(checked)))
    return best


def _load(tracks, db, fpcalc, progress):
    prints = {}
    for number, track in enumerate(tracks, 1):
        if number % 100 == 0:
            progress(f"  {number}/{len(tracks)} Dateien am Klang analysiert ...")
        if not track.fingerprint:
            track.fingerprint = json.dumps(raw_fingerprint(track.path, fpcalc))
            db.execute("UPDATE files SET fingerprint = ? WHERE path = ?", (track.fingerprint, track.path))
            if number % 100 == 0:
                db.commit()
        values = json.loads(track.fingerprint)
        if values:
            prints[track.path] = values
    db.commit()
    return prints


def _candidates(prints):
    index = defaultdict(list)
    for path, values in prints.items():
        for value in {v >> 12 for v in values}:
            index[value].append(path)
    shared = Counter()
    for paths in index.values():
        if 1 < len(paths) <= MAX_FILES_PER_VALUE:
            shared.update(combinations(sorted(paths), 2))
    return [pair for pair, count in shared.items() if count >= MIN_SHARED]


def find_groups(tracks, db, fpcalc, progress=print):
    """Liefert Listen von Tracks, die am Klang gleich sind."""
    by_path = {track.path: track for track in tracks}
    prints = _load(tracks, db, fpcalc, progress)
    parent = {path: path for path in prints}

    def root(path):
        while parent[path] != path:
            parent[path] = parent[parent[path]]
            path = parent[path]
        return path

    for a, b in _candidates(prints):
        gap = abs((by_path[a].duration or 0) - (by_path[b].duration or 0))
        if gap <= MAX_DURATION_GAP and root(a) != root(b) \
                and similarity(prints[a], prints[b]) >= MIN_SIMILARITY:
            parent[root(a)] = root(b)
    groups = defaultdict(list)
    for path in prints:
        groups[root(path)].append(by_path[path])
    return [group for group in groups.values() if len(group) > 1]
