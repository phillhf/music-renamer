"""Findet Dubletten und wählt je Gruppe die beste Datei aus.

"exakt":    identische Audiodaten, nur Tags oder Name unterscheiden sich.
"klang":    gleiche Aufnahme laut akustischem Fingerabdruck, auch in anderer Bitrate
            oder anderem Format. Läuft nur auf Wunsch, weil es jede Datei analysiert.
"aehnlich": gleicher Interpret und Titel bei fast gleicher Länge. Das kann auch eine
            Fehlzuordnung sein, darum werden diese Treffer nur auf Wunsch verschoben.
"""
import os
from collections import defaultdict
from dataclasses import dataclass

from .fingerprint import find_groups
from .library import hash_audio
from .names import COPY_SUFFIX, identify, normalize

MAX_DURATION_GAP = 2.0


@dataclass
class Group:
    kind: str
    keep: object
    duplicates: list


def _ensure_hashes(tracks, db, progress):
    """Hasht nur Dateien, deren Audiolänge mit einer anderen übereinstimmt."""
    by_size = defaultdict(list)
    for track in tracks:
        if track.audio_size:
            by_size[track.audio_size].append(track)
    todo = [t for group in by_size.values() if len(group) > 1 for t in group if not t.audio_hash]
    for n, track in enumerate(todo, 1):
        if n % 500 == 0:
            progress(f"  {n}/{len(todo)} Dateien gehasht ...")
        track.audio_hash = hash_audio(track.path, track.audio_start, track.audio_size)
        db.execute("UPDATE files SET audio_hash = ? WHERE path = ?", (track.audio_hash, track.path))
    db.commit()


def rank(track):
    """Sortierschlüssel: die Datei mit dem kleinsten Wert wird behalten."""
    stem = os.path.splitext(os.path.basename(track.path))[0]
    is_copy = bool(COPY_SUFFIX.search(stem))
    return (-(track.bitrate or 0), is_copy, -track.tag_count, len(track.path), track.path)


def _split_by_duration(tracks):
    tracks = sorted(tracks, key=lambda t: t.duration or 0)
    clusters = [[tracks[0]]]
    for track in tracks[1:]:
        if (track.duration or 0) - (clusters[-1][-1].duration or 0) <= MAX_DURATION_GAP:
            clusters[-1].append(track)
        else:
            clusters.append([track])
    return clusters


def _make_group(kind, tracks):
    ordered = sorted(tracks, key=rank)
    return Group(kind, ordered[0], ordered[1:])


def find_duplicates(tracks, db, progress=print, fpcalc=None):
    _ensure_hashes(tracks, db, progress)
    groups, remaining = [], {}
    by_hash = defaultdict(list)
    for track in tracks:
        if track.audio_hash:
            by_hash[track.audio_hash].append(track)
        else:
            remaining[track.path] = track
    for same in by_hash.values():
        if len(same) > 1:
            group = _make_group("exakt", same)
            groups.append(group)
            remaining[group.keep.path] = group.keep
        else:
            remaining[same[0].path] = same[0]

    if fpcalc:
        for same in find_groups(list(remaining.values()), db, fpcalc, progress):
            group = _make_group("klang", same)
            groups.append(group)
            for track in group.duplicates:
                del remaining[track.path]

    by_name = defaultdict(list)
    for track in remaining.values():
        artist, title = identify(track)
        if artist and title:
            by_name[(normalize(artist), normalize(title))].append(track)
    for same in by_name.values():
        if len(same) > 1:
            groups.extend(_make_group("aehnlich", c) for c in _split_by_duration(same) if len(c) > 1)
    return groups
