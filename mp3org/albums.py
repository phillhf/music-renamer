"""Betrachtet einen Ordner als Album, statt jeden Titel einzeln einzuordnen.

Einzeln passt ein Song oft besser zu einem Sampler. Stimmen aber die meisten Titel
eines Ordners in einem Album überein, bekommen sie alle dieses Album.
"""
import os
from collections import Counter, defaultdict

MIN_TRACKS = 3
MIN_SHARE = 0.6
VARIOUS = "Various Artists"


def _entry(found, group):
    """Der beste Eintrag dieses Albums; mehrere Auflagen zählen als ein Album."""
    entries = [r for r in found.get("releases", []) if r["group"] == group]
    return min(entries, key=lambda r: (r["rank"], r["date"] or "9999")) if entries else None


def _best_group(matches):
    votes = Counter()
    for found in matches:
        votes.update({r["group"] for r in found.get("releases", []) if r["group"]})
    if not votes:
        return None
    # Bei Gleichstand gewinnt das Studioalbum
    group = min(votes, key=lambda g: (-votes[g], min(
        (r["rank"] for f in matches for r in f.get("releases", []) if r["group"] == g))))
    enough = votes[group] >= MIN_TRACKS and votes[group] >= MIN_SHARE * len(matches)
    return group if enough else None


def align_albums(matches):
    """Passt die Treffer aus (Track, Treffer)-Paaren an; gibt die Zahl angepasster Titel zurück."""
    folders = defaultdict(list)
    for track, found in matches:
        folders[os.path.dirname(track.path)].append(found)
    aligned = 0
    for found_list in folders.values():
        group = _best_group(found_list)
        if not group:
            continue
        members = [(found, _entry(found, group)) for found in found_list if _entry(found, group)]
        years = [entry["date"][:4] for _, entry in members if entry["date"]]
        artists = {found["artist"] for found, _ in members}
        for found, entry in members:
            found.update(album=entry["title"], group=group,
                         albumartist=artists.copy().pop() if len(artists) == 1 else VARIOUS)
            if entry["track"]:
                found["track"] = entry["track"]
            if years:
                found["year"] = min(years)
            aligned += 1
    return aligned
