"""Befehlszeile. Ohne --apply wird nur eine Vorschau als CSV geschrieben."""
import argparse
import csv
import os
import sys
from collections import Counter

from . import __version__, genres, updater
from . import journal as journaling
from . import library
from .albums import align_albums
from .dupes import find_duplicates
from .i18n import t
from .job import Cancelled, job
from .lookup import Lookup, fetch_cover, fetch_lyrics, find_fpcalc
from .names import clean, identify, safe_filename
from .tags import FIELDS as TAG_FIELDS
from .tags import write_tags


def app_dir(base):
    """Datenordner; bis 0.5.0 hieß er nach dem alten Programmnamen und zieht einmalig um."""
    new, old = os.path.join(base, "Music Renamer"), os.path.join(base, "MP3 Organizer")
    if os.path.isdir(old) and not os.path.exists(new):
        try:
            os.rename(old, new)
        except OSError:  # Zum Beispiel noch geöffnet: dann bleiben die Daten vorerst dort
            return old
    return new


# Nicht im Programmordner: der wird bei Updates ersetzt
APP_DIR = app_dir(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"))
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


def review(args, title, columns, editable, rows):
    """Lässt die Oberfläche die Zeilen prüfen; None heißt abgebrochen."""
    hook = getattr(args, "review", None)
    return hook(title, columns, editable, rows) if hook and args.apply and rows else rows


def dupes_dir(args):
    return os.path.abspath(getattr(args, "ziel", None) or os.path.join(args.ordner, "Dubletten"))


def prepare(args):
    root = os.path.abspath(args.ordner)
    if not os.path.isdir(root):
        sys.exit(t("Ordner nicht gefunden: {path}", path=root))
    db = library.connect(DB_PATH)
    print(t("Scanne {path} ...", path=root))
    # Der Dubletten-Ordner liegt in der Sammlung, gehört aber zu keinem Schritt
    errors = library.scan(root, db, dupes_dir(args))
    if errors:
        path = write_report("defekte-dateien.csv", ("Datei", "Fehler"), errors)
        print(t("Dateien nicht lesbar: {count}, siehe {path}", count=len(errors), path=path))
    tracks = library.load_tracks(root, db)
    print(t("Audiodateien erkannt: {count}", count=len(tracks)))
    return root, db, tracks


def cmd_dupes(args):
    target_dir = dupes_dir(args)
    root, db, tracks = prepare(args)
    fpcalc = None
    if getattr(args, "klang", False):
        fpcalc = find_fpcalc()
        if not fpcalc:
            sys.exit(t("Für den Klangvergleich fehlt fpcalc."))
        print(t("Klangvergleich läuft, das dauert je Datei etwa eine Sekunde."))
    groups = find_duplicates(tracks, db, fpcalc=fpcalc)
    report_rows, moves = [], []
    for number, group in enumerate(groups, 1):
        move = group.kind != "aehnlich" or args.aehnlich
        keep_rate = group.keep.bitrate // 1000
        report_rows.append((number, group.kind, "BEHALTEN", group.keep.path, keep_rate, round(group.keep.duration or 0)))
        for track in group.duplicates:
            report_rows.append((number, group.kind, "VERSCHIEBEN" if move else "nur gemeldet", track.path,
                                track.bitrate // 1000, round(track.duration or 0)))
            if move:
                moves.append({"group": number, "Art": group.kind, "Datei": track.path,
                              "kbit/s": track.bitrate // 1000, "Behalten": group.keep.path})
    report = write_report("dubletten.csv", ("Gruppe", "Art", "Aktion", "Datei", "kbit/s", "Sekunden"), report_rows)
    count = Counter()
    for group in groups:
        count[group.kind] += len(group.duplicates)
    print(t("Dubletten: {exact} exakt, {sound} klanggleich, {similar} ähnlich",
            exact=count["exakt"], sound=count["klang"], similar=count["aehnlich"]))
    print(t("Bericht: {path}", path=report))
    if not args.apply:
        print(t("Vorschau: {count} Dateien würden nach {path} verschoben.", count=len(moves), path=target_dir))
        return
    moves = review(args, t("1. Dubletten verschieben"), ("Art", "Datei", "kbit/s", "Behalten"), (), moves)
    if not moves:
        print(t("Keine Änderungen nötig."))
        return
    journal = journaling.Journal(DATA_DIR, "dubletten")
    moved = 0
    try:
        for number, row in enumerate(moves, 1):
            job.step(number, len(moves), t("Dateien verschieben"))
            relative = os.path.relpath(row["Datei"], root)
            target = journaling.unique_path(os.path.join(target_dir, relative))
            try:
                journaling.move_file(row["Datei"], target, journal)
                moved += 1
            except OSError as exc:
                print(t("Fehler bei {path}: {reason}", path=row["Datei"], reason=exc))
    finally:
        journal.close()
        print(t("Dateien verschoben: {count}", count=moved))


def planned_changes(track, found, overwrite):
    changes = {}
    for field in TAG_FIELDS:
        new = found.get(field, "")
        current = clean(getattr(track, field))
        if new and new != current and (overwrite or not current):
            changes[field] = new
    return changes


def _search(args, tracks, lookup, wants_genres):
    """Sucht Treffer; ein Album-Ordner wird ganz abgefragt, damit alle Titel mitzählen."""
    wants_cover = getattr(args, "cover", False)
    wants_lyrics = getattr(args, "songtexte", False)

    def complete(track):
        filled = all(clean(getattr(track, f)) for f in ("artist", "title", "album", "year", "genre"))
        extras = (wants_cover and not track.has_cover) or (wants_lyrics and not track.has_lyrics)
        return filled and not extras and not args.ueberschreiben

    open_folders = {os.path.dirname(track.path) for track in tracks if not complete(track)}
    matches, unresolved = [], []
    for number, track in enumerate(tracks, 1):
        job.step(number, len(tracks), t("Metadaten suchen"))
        done = complete(track)
        if done and os.path.dirname(track.path) not in open_folders:
            if wants_genres:
                matches.append((track, {"source": "genre"}))
            continue
        artist, title = identify(track)
        try:
            found = lookup.find(track.path, artist, title, track.duration)
        except ConnectionError as exc:
            sys.exit(t("Abbruch: {reason}. Bisherige Treffer sind gespeichert, einfach erneut starten.", reason=exc))
        if found and not found.get("rejected"):
            matches.append((track, found))
        elif done and wants_genres:
            matches.append((track, {"source": "genre"}))
        elif not done:
            unresolved.append((track.path, artist, title, (found or {}).get("score", "")))
    return matches, unresolved


def _apply_tags(chosen, plan):
    journal = journaling.Journal(DATA_DIR, "tags")
    covers = {}
    saved = covers_saved = lyrics_saved = 0
    try:
        for number, row in enumerate(chosen, 1):
            job.step(number, len(chosen), t("Metadaten schreiben"))
            track, found = plan[row["id"]]
            changes = {field: row[field] for field in TAG_FIELDS if row[field]}
            try:
                if row["Cover"]:
                    if found["group"] not in covers:
                        covers[found["group"]] = fetch_cover(found["group"])
                    if covers[found["group"]]:
                        changes["cover"] = covers[found["group"]]
                if row["Songtext"]:
                    text = fetch_lyrics(changes.get("artist") or found.get("artist", clean(track.artist)),
                                        changes.get("title") or found.get("title", clean(track.title)),
                                        changes.get("album") or found.get("album", ""), track.duration)
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
                print(t("Fehler bei {path}: {reason}", path=track.path, reason=exc))
    finally:
        journal.close()
        print(t("{count} Dateien gespeichert, davon {covers} mit Cover und {lyrics} mit Songtext.",
                count=saved, covers=covers_saved, lyrics=lyrics_saved))


def cmd_tag(args):
    root, db, tracks = prepare(args)
    if args.limit:
        tracks = tracks[:args.limit]
    try:
        lookup = Lookup(db, args.genauigkeit)
    except ValueError as exc:
        sys.exit(str(exc))
    if lookup.api_key and lookup.fpcalc:
        print(t("Klangerkennung aktiv, Mindestwert {value} %.", value=f"{lookup.min_score * 100:g}"))
    else:
        print(t("Hinweis: Ohne AcoustID-Key läuft die Suche nur über Name und Tags."))
    wants_cover = getattr(args, "cover", False)
    wants_lyrics = getattr(args, "songtexte", False)
    wants_genres = getattr(args, "genres", False)
    rules = genres.load_rules(APP_DIR) if wants_genres else {}
    matches, unresolved = _search(args, tracks, lookup, wants_genres)
    aligned = align_albums(matches)
    plan, rows = [], []
    for track, found in matches:
        if wants_genres and found.get("genre"):
            found["genre"] = genres.canonical(found["genre"], rules)
        changes = planned_changes(track, found, args.ueberschreiben)
        current = clean(track.genre)
        if wants_genres and current and genres.canonical(current, rules) != current:
            changes["genre"] = genres.canonical(current, rules)
        cover = wants_cover and not track.has_cover and bool(found.get("group"))
        lyrics = wants_lyrics and not track.has_lyrics and found.get("source") != "genre"
        if changes or cover or lyrics:
            rows.append({"id": len(plan), "Datei": track.path, "Quelle": found["source"],
                         "Trefferwert %": found.get("score", ""), **{f: changes.get(f, "") for f in TAG_FIELDS},
                         "Cover": "ja" if cover else "", "Songtext": "ja" if lyrics else ""})
            plan.append((track, found))
    columns = ("Datei", "Quelle", "Trefferwert %", *TAG_FIELDS, "Cover", "Songtext")
    report = write_report("tags-vorschau.csv", columns, [[r[c] for c in columns] for r in rows])
    missing = write_report("nicht-gefunden.csv", ("Datei", "Interpret", "Titel", "Trefferwert %"), unresolved)
    print(t("Neue Daten für {planned} Dateien, {unresolved} ohne sicheren Treffer, {aligned} Titel einem Album zugeordnet.",
            planned=len(plan), unresolved=len(unresolved), aligned=aligned))
    print(t("Berichte: {first} und {second}", first=report, second=missing))
    if not args.apply:
        print(t("Vorschau: nichts geändert."))
        return
    chosen = review(args, t("2. Metadaten ergänzen"), columns, TAG_FIELDS, rows)
    if not chosen:
        print(t("Keine Änderungen nötig."))
        return
    _apply_tags(chosen, plan)


def check_pattern(pattern):
    try:
        pattern.format(**dict.fromkeys(TAG_FIELDS, "x"))
    except (KeyError, ValueError, IndexError):
        sys.exit(t("Ungültiges Muster: {pattern}. Erlaubt sind {fields}.", pattern=pattern,
                   fields=", ".join(f"{{{f}}}" for f in TAG_FIELDS)))


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
    rows, skipped = [], 0
    taken = {os.path.normcase(t_.path) for t_ in tracks}
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
        rows.append({"Alt": track.path, "Neu": candidate})
    report = write_report("umbenennen-vorschau.csv", ("Alt", "Neu"), [(r["Alt"], r["Neu"]) for r in rows])
    print(t("Umbenennen: {planned} Dateien, {skipped} ohne Interpret oder Titel übersprungen.",
            planned=len(rows), skipped=skipped))
    print(t("Bericht: {path}", path=report))
    if not args.apply:
        print(t("Vorschau: nichts geändert."))
        return
    rows = review(args, t("3. Dateien umbenennen und sortieren"), ("Alt", "Neu"), ("Neu",), rows)
    if not rows:
        print(t("Keine Änderungen nötig."))
        return
    journal = journaling.Journal(DATA_DIR, "umbenennen")
    done = 0
    try:
        for number, row in enumerate(rows, 1):
            job.step(number, len(rows), t("Dateien umbenennen"))
            source, target = row["Alt"], row["Neu"]
            same_file = os.path.normcase(source) == os.path.normcase(target)
            if os.path.exists(target) and not same_file:
                print(t("Übersprungen, Ziel existiert: {path}", path=target))
                continue
            try:
                journaling.move_file(source, target, journal)
                remove_empty_folders(os.path.dirname(source), root)
                done += 1
            except OSError as exc:
                print(t("Fehler bei {path}: {reason}", path=source, reason=exc))
    finally:
        journal.close()
        print(t("Dateien umbenannt: {count}", count=done))


def cmd_undo(args):
    path, done, problems = journaling.undo_last(DATA_DIR)
    if not path:
        print(t("Nichts rückgängig zu machen."))
        return
    print(t("Dateien zurückgenommen: {count}", count=done))
    for problem in problems:
        print(problem)


def cmd_update(args):
    release = updater.check_latest()
    if release:
        print(t("Neue Version {version}: {page}", version=release.version, page=release.page))
    else:
        print(t("Version {version} ist aktuell.", version=__version__))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="musicrenamer", description="Musiksammlung aufräumen")
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
    tag.add_argument("--genres", action="store_true", help="Genres vereinheitlichen")
    rename = command("umbenennen", cmd_rename, "Dateien nach Tags benennen")
    rename.add_argument("--muster", default=PATTERNS[0],
                        help=f'Standard "{PATTERNS[0]}"; / sortiert die Sammlung in Unterordner')
    undo = commands.add_parser("undo", help="letzten ausgeführten Schritt zurücknehmen")
    undo.set_defaults(handler=cmd_undo)
    update = commands.add_parser("update", help="auf GitHub nach einer neuen Version suchen")
    update.set_defaults(handler=cmd_update)

    args = parser.parse_args()
    try:
        args.handler(args)
    except Cancelled:
        print(t("Abgebrochen. Bereits Erledigtes bleibt erhalten und lässt sich im Verlauf zurücknehmen."))


if __name__ == "__main__":
    main()
