"""Befehlszeile. Ohne --apply wird nur eine Vorschau als CSV geschrieben."""
import argparse
import csv
import os
import sys

from . import __version__, updater
from . import journal as journaling
from . import library
from .dupes import find_duplicates
from .lookup import Lookup
from .names import clean, identify, safe_filename
from .tags import write_tags

# Nicht im Programmordner: der wird bei Updates ersetzt
APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "MP3 Organizer")
DATA_DIR = os.path.join(APP_DIR, "data")
REPORT_DIR = os.path.join(APP_DIR, "berichte")
DB_PATH = os.path.join(DATA_DIR, "mp3org.sqlite")
TAG_FIELDS = ("artist", "title", "album", "year", "genre", "track")


def write_report(name, header, rows):
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, name)
    # utf-8-sig und Semikolon, damit Excel die Datei direkt richtig öffnet
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)
        writer.writerows(rows)
    return path


def default_dupes_dir(root):
    root = os.path.abspath(root)
    return f"{root.rstrip(os.sep)}_Dubletten"


def prepare(args, exclude=None):
    root = os.path.abspath(args.ordner)
    if not os.path.isdir(root):
        sys.exit(f"Ordner nicht gefunden: {root}")
    db = library.connect(DB_PATH)
    print(f"Scanne {root} ...")
    errors = library.scan(root, db, exclude)
    if errors:
        path = write_report("defekte-dateien.csv", ("Datei", "Fehler"), errors)
        print(f"{len(errors)} Dateien nicht lesbar, siehe {path}")
    tracks = library.load_tracks(root, db)
    print(f"{len(tracks)} MP3-Dateien erkannt.")
    return root, db, tracks


def cmd_dupes(args):
    target_dir = os.path.abspath(args.ziel or default_dupes_dir(args.ordner))
    root, db, tracks = prepare(args, exclude=target_dir)
    groups = find_duplicates(tracks, db)
    rows, to_move = [], []
    for number, group in enumerate(groups, 1):
        move = group.kind == "exakt" or args.aehnlich
        rows.append((number, group.kind, "BEHALTEN", group.keep.path, group.keep.bitrate // 1000,
                     round(group.keep.duration or 0)))
        for track in group.duplicates:
            rows.append((number, group.kind, "VERSCHIEBEN" if move else "nur gemeldet", track.path,
                         track.bitrate // 1000, round(track.duration or 0)))
            if move:
                to_move.append(track)
    report = write_report("dubletten.csv",
                          ("Gruppe", "Art", "Aktion", "Datei", "kbit/s", "Sekunden"), rows)
    exact = sum(len(g.duplicates) for g in groups if g.kind == "exakt")
    similar = sum(len(g.duplicates) for g in groups if g.kind == "aehnlich")
    print(f"{exact} exakte und {similar} ähnliche Dubletten. Bericht: {report}")
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
    lookup = Lookup(db)
    if not (lookup.api_key and lookup.fpcalc):
        print("Hinweis: ohne ACOUSTID_KEY und fpcalc läuft die Suche nur über Name und Tags.")
    plan, unresolved, rows = [], [], []
    for number, track in enumerate(tracks, 1):
        if number % 25 == 0:
            print(f"  {number}/{len(tracks)} ...")
        artist, title = identify(track)
        complete = all(clean(getattr(track, f)) for f in ("artist", "title", "album", "year", "genre"))
        if complete and not args.ueberschreiben:
            continue
        try:
            found = lookup.find(track.path, artist, title, track.duration)
        except ConnectionError as exc:
            sys.exit(f"Abbruch: {exc}. Bisherige Treffer sind gespeichert, einfach erneut starten.")
        if not found:
            unresolved.append((track.path, artist, title))
            continue
        changes = planned_changes(track, found, args.ueberschreiben)
        if changes:
            plan.append((track, changes))
            rows.append((track.path, found["source"], *[changes.get(f, "") for f in TAG_FIELDS]))
    report = write_report("tags-vorschau.csv", ("Datei", "Quelle", *TAG_FIELDS), rows)
    review = write_report("nicht-gefunden.csv", ("Datei", "Interpret", "Titel"), unresolved)
    print(f"{len(plan)} Dateien bekommen neue Tags, {len(unresolved)} ohne sicheren Treffer.")
    print(f"Berichte: {report} und {review}")
    if not args.apply:
        print("Vorschau: nichts geändert.")
        return
    journal = journaling.Journal(DATA_DIR, "tags")
    for track, changes in plan:
        old = {field: getattr(track, field) for field in changes}
        try:
            journal.record(action="tag", path=track.path, old=old, new=changes)
            write_tags(track.path, changes)
        except Exception as exc:
            print(f"Fehler bei {track.path}: {exc}")
    journal.close()
    print(f"{len(plan)} Dateien getaggt.")


def target_name(track, pattern):
    values = {f: clean(getattr(track, f)) for f in TAG_FIELDS}
    if not (values["artist"] and values["title"]):
        return None
    if "{track}" in pattern and values["track"]:
        values["track"] = values["track"].split("/")[0].zfill(2)
    parts = [safe_filename(p.format(**values)) for p in pattern.split("/")]
    return os.path.join(*parts) + ".mp3" if all(parts) else None


def cmd_rename(args):
    root, db, tracks = prepare(args)
    rows, plan, skipped = [], [], 0
    taken = {os.path.normcase(t.path) for t in tracks}
    for track in tracks:
        name = target_name(track, args.muster)
        if not name:
            skipped += 1
            continue
        target = os.path.join(os.path.dirname(track.path), name)
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
    parser = argparse.ArgumentParser(prog="mp3org", description="MP3-Sammlung aufräumen")
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name, handler, help_text):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("ordner", help="Ordner der MP3-Sammlung")
        sub.add_argument("--apply", action="store_true", help="Änderungen wirklich ausführen")
        sub.set_defaults(handler=handler)
        return sub

    dupes = command("dubletten", cmd_dupes, "Dubletten finden und verschieben")
    dupes.add_argument("--ziel", help="Zielordner, Standard: <Sammlung>_Dubletten")
    dupes.add_argument("--aehnlich", action="store_true", help="auch ähnliche Treffer verschieben")
    tag = command("tags", cmd_tag, "Metadaten suchen und ergänzen")
    tag.add_argument("--ueberschreiben", action="store_true", help="auch vorhandene Tags ersetzen")
    tag.add_argument("--limit", type=int, help="nur die ersten N Dateien (zum Ausprobieren)")
    rename = command("umbenennen", cmd_rename, "Dateien nach Tags benennen")
    rename.add_argument("--muster", default="{artist} - {title}",
                        help='Standard "{artist} - {title}"; / erzeugt Unterordner')
    undo = commands.add_parser("undo", help="letzten ausgeführten Schritt zurücknehmen")
    undo.set_defaults(handler=cmd_undo)
    update = commands.add_parser("update", help="auf GitHub nach einer neuen Version suchen")
    update.set_defaults(handler=cmd_update)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
