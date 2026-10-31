"""Betrachtet einen Ordner als Album, statt jeden Titel einzeln einzuordnen.

Einzeln passt ein Song oft besser zu einem Sampler. Stimmen aber mehrere Titel eines
Ordners in einem Album überein, bekommen sie dieses Album. Ein Ordner darf auch mehrere
Alben enthalten; sie werden nacheinander herausgelöst.
"""
import os
from collections import Counter, defaultdict

MIN_TRACKS = 3
MIN_SHARE = 0.6
CLEAR_MAJORITY = 5  # so viele Titel eines Albums reichen auch in einem gemischten Ordner
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
    enough = votes[group] >= MIN_TRACKS and (
        votes[group] >= MIN_SHARE * len(matches) or votes[group] >= CLEAR_MAJORITY)
    return group if enough else None


def _assign(members, group):
    years = [entry["date"][:4] for _, entry in members if entry["date"]]
    artists = {found.get("artist") for found, _ in members}
    for found, entry in members:
        found.update(album=entry["title"], group=group,
                     albumartist=next(iter(artists)) if len(artists) == 1 else VARIOUS)
        if entry["track"]:
            found["track"] = entry["track"]
        if years:
            found["year"] = min(years)


def align_albums(matches):
    """Passt die Treffer aus (Track, Treffer)-Paaren an; gibt die Zahl angepasster Titel zurück."""
    folders = defaultdict(list)
    for track, found in matches:
        folders[os.path.dirname(track.path)].append(found)
    aligned = 0
    for remaining in folders.values():
        while group := _best_group(remaining):
            members = [(found, _entry(found, group)) for found in remaining if _entry(found, group)]
            _assign(members, group)
            aligned += len(members)
            done = {id(found) for found, _ in members}
            remaining = [found for found in remaining if id(found) not in done]
    return aligned
