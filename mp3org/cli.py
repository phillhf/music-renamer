"""Befehlszeile. Ohne --apply wird nur eine Vorschau als CSV geschrieben."""
import argparse
import csv
import os
import sys
from collections import Counter

from . import __version__, updater
from . import journal as journaling
from . import library
from .albums import align_albums
from .dupes import find_duplicates
from .lookup import Lookup, fetch_cover, fetch_lyrics, find_fpcalc
from .names import clean, identify, safe_filename
from .tags import FIELDS as TAG_FIELDS
from .tags import write_tags

# Nicht im Programmordner: der wird bei Updates ersetzt
APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "MP3 Organizer")
DATA_DIR = os.path.join(APP_DIR, "data")
REPORT_DIR = os.path.join(APP_DIR, "berichte")
DB_PATH = os.path.join(DATA_DIR, "mp3org.sqlite")
UNKNOWN_ALBUM = "Unbekanntes Album"
PATTERNS = ("{artist} - {title}", "{track} - {title}", "{artist}/{album}/{track} - {title}",
            "{albumartist}/{year} - {album}/{track} - {title}")


def write_report(name, header, rows):
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, name)
    # utf-8-sig und Semikolon, damit Excel die Datei direkt richtig öffnet
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)
        writer.writerows(rows)
    return path


def dupes_dir(args):
    return os.path.abspath(getattr(args, "ziel", None) or os.path.join(args.ordner, "Dubletten"))


def prepare(args):
    root = os.path.abspath(args.ordner)
    if not os.path.isdir(root):
        sys.exit(f"Ordner nicht gefunden: {root}")
    db = library.connect(DB_PATH)
    print(f"Scanne {root} ...")
    # Der Dubletten-Ordner liegt in der Sammlung, gehört aber zu keinem Schritt
    errors = library.scan(root, db, dupes_dir(args))
    if errors:
        path = write_report("defekte-dateien.csv", ("Datei", "Fehler"), errors)
        print(f"{len(errors)} Dateien nicht lesbar, siehe {path}")
    tracks = library.load_tracks(root, db)
    print(f"{len(tracks)} Audiodateien erkannt.")
    return root, db, tracks


def cmd_dupes(args):
    target_dir = dupes_dir(args)
    root, db, tracks = prepare(args)
    fpcalc = None
    if getattr(args, "klang", False):
        fpcalc = find_fpcalc()
        if not fpcalc:
            sys.exit("Für den Klangvergleich fehlt fpcalc.")
        print("Klangvergleich läuft, das dauert je Datei etwa eine Sekunde ...")
    groups = find_duplicates(tracks, db, fpcalc=fpcalc)
    rows, to_move = [], []
    for number, group in enumerate(groups, 1):
        move = group.kind != "aehnlich" or args.aehnlich
        rows.append((number, group.kind, "BEHALTEN", group.keep.path, group.keep.bitrate // 1000,
                     round(group.keep.duration or 0)))
        for track in group.duplicates:
            rows.append((number, group.kind, "VERSCHIEBEN" if move else "nur gemeldet", track.path,
                         track.bitrate // 1000, round(track.duration or 0)))
            if move:
                to_move.append(track)
    report = write_report("dubletten.csv",
                          ("Gruppe", "Art", "Aktion", "Datei", "kbit/s", "Sekunden"), rows)
    count = Counter()
    for group in groups:
        count[group.kind] += len(group.duplicates)
    print(f"{count['exakt']} exakte, {count['klang']} klanggleiche und {count['aehnlich']} ähnliche Dubletten. "
          f"Bericht: {report}")
    if not args.apply:
        print(f"Vorschau: {len(to_move)} Dateien würden nach {target_dir} verschoben.")
        return
    journal = journaling.Journal(DATA_DIR, "dubletten")
    moved = 0
    for track in to_move:
        relative = os.path.relpath(track.path, root)
        target = journaling.unique_path(os.path.join(target_dir, relative))
        try:
            journaling.move_file(track.path, target, journal)
            moved += 1
        except OSError as exc:
            print(f"Fehler bei {track.path}: {exc}")
    journal.close()
    print(f"{moved} Dateien verschoben.")


def planned_changes(track, found, overwrite):
    changes = {}
    for field in TAG_FIELDS:
        new = found.get(field, "")
        current = clean(getattr(track, field))
        if new and new != current and (overwrite or not current):
            changes[field] = new
    return changes


def cmd_tag(args):
    root, db, tracks = prepare(args)
    if args.limit:
        tracks = tracks[:args.limit]
    try:
        lookup = Lookup(db, args.genauigkeit)
    except ValueError as exc:
        sys.exit(str(exc))
    if lookup.api_key and lookup.fpcalc:
        print(f"Klangerkennung aktiv, Mindestwert {lookup.min_score * 100:g} %.")
    else:
        print("Hinweis: ohne ACOUSTID_KEY und fpcalc läuft die Suche nur über Name und Tags.")
    wants_cover = getattr(args, "cover", False)
    wants_lyrics = getattr(args, "songtexte", False)
    matches, unresolved = [], []
    for number, track in enumerate(tracks, 1):
        if number % 25 == 0:
            print(f"  {number}/{len(tracks)} ...")
        artist, title = identify(track)
        complete = all(clean(getattr(track, f)) for f in ("artist", "title", "album", "year", "genre"))
        extras_missing = (wants_cover and not track.has_cover) or (wants_lyrics and not track.has_lyrics)
        if complete and not args.ueberschreiben and not extras_missing:
            continue
        try:
            found = lookup.find(track.path, artist, title, track.duration)
        except ConnectionError as exc:
            sys.exit(f"Abbruch: {exc}. Bisherige Treffer sind gespeichert, einfach erneut starten.")
        if not found or found.get("rejected"):
            unresolved.append((track.path, artist, title, (found or {}).get("score", "")))
            continue
        matches.append((track, found))
    aligned = align_albums(matches)
    plan, rows = [], []
    for track, found in matches:
        changes = planned_changes(track, found, args.ueberschreiben)
        cover = wants_cover and not track.has_cover and bool(found.get("group"))
        lyrics = wants_lyrics and not track.has_lyrics
        if changes or cover or lyrics:
            plan.append((track, found, changes, cover, lyrics))
            rows.append((track.path, found["source"], found.get("score", ""),
                         *[changes.get(f, "") for f in TAG_FIELDS],
                         "ja" if cover else "", "ja" if lyrics else ""))
    report = write_report("tags-vorschau.csv", ("Datei", "Quelle", "Trefferwert %", *TAG_FIELDS,
                                                "Cover", "Songtext"), rows)
    review = write_report("nicht-gefunden.csv", ("Datei", "Interpret", "Titel", "Trefferwert %"), unresolved)
    print(f"{len(plan)} Dateien bekommen neue Daten, {len(unresolved)} ohne sicheren Treffer, "
          f"{aligned} Titel einem Album zugeordnet.")
    print(f"Berichte: {report} und {review}")
    if not args.apply:
        print("Vorschau: nichts geändert.")
        return
    journal = journaling.Journal(DATA_DIR, "tags")
    covers = {}
    saved = covers_saved = lyrics_saved = 0
    for track, found, changes, cover, lyrics in plan:
        changes = dict(changes)
        try:
            if cover:
                if found["group"] not in covers:
                    covers[found["group"]] = fetch_cover(found["group"])
                if covers[found["group"]]:
                    changes["cover"] = covers[found["group"]]
            if lyrics:
                text = fetch_lyrics(changes.get("artist") or found["artist"], changes.get("title") or found["title"],
                                    changes.get("album") or found["album"], track.duration)
                if text:
                    changes["lyrics"] = text
            if not changes:
                continue
            # Cover und Songtexte kommen nur dazu, wenn keine da waren; zurücknehmen heißt entfernen
            old = {field: getattr(track, field, "") for field in changes}
            journal.record(action="tag", path=track.path, old=old,
                           new={f: v for f, v in changes.items() if f not in ("cover", "lyrics")})
            write_tags(track.path, changes)
            saved += 1
            covers_saved += "cover" in changes
            lyrics_saved += "lyrics" in changes
        except Exception as exc:
            print(f"Fehler bei {track.path}: {exc}")
    journal.close()
    print(f"{saved} Dateien gespeichert, davon {covers_saved} mit Cover und {lyrics_saved} mit Songtext.")


def check_pattern(pattern):
    try:
        pattern.format(**dict.fromkeys(TAG_FIELDS, "x"))
    except (KeyError, ValueError, IndexError):
        sys.exit(f"Ungültiges Muster: {pattern}. Erlaubt sind " + ", ".join(f"{{{f}}}" for f in TAG_FIELDS))


def target_name(track, pattern):
    values = {f: clean(getattr(track, f)) for f in TAG_FIELDS}
    if not (values["artist"] and values["title"]):
        return None
    values["albumartist"] = values["albumartist"] or values["artist"]
    values["album"] = values["album"] or UNKNOWN_ALBUM
    values["track"] = values["track"].split("/")[0].zfill(2) if values["track"] else ""
    # Fehlt z. B. die Tracknummer, soll kein Name mit " - " beginnen
    parts = [safe_filename(p.format(**values)).strip(" -") for p in pattern.split("/")]
    return os.path.join(*parts) + os.path.splitext(track.path)[1].lower() if all(parts) else None


def remove_empty_folders(folder, root):
    """Entfernt Ordner, die das Umsortieren geleert hat, aber nie die Sammlung selbst."""
    while os.path.normcase(folder) != os.path.normcase(root) and folder.startswith(root):
        try:
            os.rmdir(folder)
        except OSError:
            return
        folder = os.path.dirname(folder)


def cmd_rename(args):
    check_pattern(args.muster)
    root, db, tracks = prepare(args)
    rows, plan, skipped = [], [], 0
    taken = {os.path.normcase(t.path) for t in tracks}
    # Ein Muster mit Ordnern sortiert die ganze Sammlung, sonst bleibt jede Datei in ihrem Ordner
    sorts = "/" in args.muster
    for track in tracks:
        name = target_name(track, args.muster)
        if not name:
            skipped += 1
            continue
        target = os.path.join(root if sorts else os.path.dirname(track.path), name)
        if target == track.path:
            continue
        taken.discard(os.path.normcase(track.path))
        base, ext = os.path.splitext(target)
        candidate, n = target, 2
        while os.path.normcase(candidate) in taken:
            candidate, n = f"{base} ({n}){ext}", n + 1
        taken.add(os.path.normcase(candidate))
        plan.append((track.path, candidate))
        rows.append((track.path, candidate))
    report = write_report("umbenennen-vorschau.csv", ("Alt", "Neu"), rows)
    print(f"{len(plan)} Dateien umzubenennen, {skipped} ohne Interpret/Titel übersprungen. Bericht: {report}")
    if not args.apply:
        print("Vorschau: nichts geändert.")
        return
    journal = journaling.Journal(DATA_DIR, "umbenennen")
    done = 0
    for source, target in plan:
        same_file = os.path.normcase(source) == os.path.normcase(target)
        if os.path.exists(target) and not same_file:
            print(f"Übersprungen, Ziel existiert: {target}")
            continue
        try:
            journaling.move_file(source, target, journal)
            remove_empty_folders(os.path.dirname(source), root)
            done += 1
        except OSError as exc:
            print(f"Fehler bei {source}: {exc}")
    journal.close()
    print(f"{done} Dateien umbenannt.")


def cmd_undo(args):
    path, done, problems = journaling.undo_last(DATA_DIR)
    if not path:
        print("Nichts rückgängig zu machen.")
        return
    print(f"{done} Änderungen aus {os.path.basename(path)} zurückgenommen.")
    for problem in problems:
        print(f"Problem: {problem}")


def cmd_update(args):
    release = updater.check_latest()
    if release:
        print(f"Neue Version {release.version} verfügbar: {release.page}")
    else:
        print(f"Version {__version__} ist aktuell.")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="mp3org", description="Musiksammlung aufräumen")
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name, handler, help_text):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("ordner", help="Ordner der Musiksammlung")
        sub.add_argument("--apply", action="store_true", help="Änderungen wirklich ausführen")
        sub.set_defaults(handler=handler)
        return sub

    dupes = command("dubletten", cmd_dupes, "Dubletten finden und verschieben")
    dupes.add_argument("--ziel", help="Zielordner, Standard: <Sammlung>\\Dubletten")
    dupes.add_argument("--aehnlich", action="store_true", help="auch ähnliche Treffer verschieben")
    dupes.add_argument("--klang", action="store_true", help="am Klang vergleichen (langsam)")
    tag = command("tags", cmd_tag, "Metadaten suchen und ergänzen")
    tag.add_argument("--ueberschreiben", action="store_true", help="auch vorhandene Tags ersetzen")
    tag.add_argument("--limit", type=int, help="nur die ersten N Dateien (zum Ausprobieren)")
    tag.add_argument("--genauigkeit", default="normal",
                     help="Mindestwert der Klangerkennung: streng, normal, locker oder Prozentzahl")
    tag.add_argument("--cover", action="store_true", help="fehlende Cover einbetten")
    tag.add_argument("--songtexte", action="store_true", help="fehlende Songtexte einbetten")
    rename = command("umbenennen", cmd_rename, "Dateien nach Tags benennen")
    rename.add_argument("--muster", default=PATTERNS[0],
                        help=f'Standard "{PATTERNS[0]}"; / sortiert die Sammlung in Unterordner')
    undo = commands.add_parser("undo", help="letzten ausgeführten Schritt zurücknehmen")
    undo.set_defaults(handler=cmd_undo)
    update = commands.add_parser("update", help="auf GitHub nach einer neuen Version suchen")
    update.set_defaults(handler=cmd_update)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
