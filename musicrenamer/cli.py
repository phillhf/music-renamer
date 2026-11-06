"""Befehlszeile. Ohne --apply wird nur eine Vorschau als CSV geschrieben."""
import argparse
import csv
import os
import re
import sys
import time
from collections import Counter

from . import __version__, genres, system, updater
from . import journal as journaling
from . import library
from .albums import align_albums
from .dupes import find_duplicates
from .i18n import progress_line, t
from .job import Cancelled, job
from .lookup import Lookup, fetch_cover, fetch_lyrics, find_fpcalc
from .names import artist_list, clean, display_artist, identify, main_artist, normalize, safe_filename
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
APP_DIR = app_dir(system.data_base())
DATA_DIR = os.path.join(APP_DIR, "data")
REPORT_DIR = os.path.join(APP_DIR, "berichte")
DB_PATH = os.path.join(DATA_DIR, "mp3org.sqlite")
UNKNOWN_ALBUM = "Unbekanntes Album"
UNKNOWN_YEAR = "Unbekanntes Jahr"
UNKNOWN_GENRE = "Unbekanntes Genre"
PERIOD_YEARS = 5
MAX_FAILURES = 25
PROGRESS_GAP = 30
DOCS_URL = "https://github.com/phillhf/music-renamer/blob/main/docs/"
HELP_EPILOG = f"""\
Ohne --apply wird nichts geändert, nur ein Bericht geschrieben.
Mit --apply wird sofort ausgeführt, ohne Rückfrage.

Beispiele:
  music-renamer-cli dubletten ~/Musik
  music-renamer-cli tags ~/Musik --cover --songtexte
  music-renamer-cli tags ~/Musik --cover --songtexte --apply
  music-renamer-cli umbenennen ~/Musik --muster "{{artist}}/{{album}}/{{track}} - {{title}}"
  music-renamer-cli undo

Hilfe zu einem Befehl: music-renamer-cli tags --help
Alle Befehle mit Beispielen: {DOCS_URL}Befehlszeile.md
"""
PATTERNS = ("{artist} - {title}", "{track} - {title}", "{artist}/{album}/{track} - {title}",
            "{albumartist}/{year} - {album}/{track} - {title}", "{zeitraum}/{genre}/{artist} - {title}")
PLACEHOLDERS = (*TAG_FIELDS, "zeitraum", "jahrzehnt", "buchstabe")
# Was die Oberfläche als Ordnerebene anbietet; eigene Muster aus PLACEHOLDERS gehen genauso
FOLDER_LEVELS = (("Zeitraum", "{zeitraum}"), ("Jahrzehnt", "{jahrzehnt}"), ("Jahr", "{year}"),
                 ("Genre", "{genre}"), ("Interpret", "{albumartist}"), ("Interpret des Titels", "{artist}"),
                 ("Anfangsbuchstabe", "{buchstabe}"), ("Album", "{album}"), ("Jahr - Album", "{year} - {album}"),
                 ("Label", "{label}"))
# Ein leerer Ordnername wird hierzu, damit die Datei trotzdem einsortiert wird
UNKNOWN_FOLDER = {"year": UNKNOWN_YEAR, "zeitraum": UNKNOWN_YEAR, "jahrzehnt": UNKNOWN_YEAR,
                  "genre": UNKNOWN_GENRE, "album": UNKNOWN_ALBUM, "label": "Unbekanntes Label"}


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
        # Eine Liste wie "Dr. Dre/Nate Dogg" ist kein brauchbarer Interpret, der Treffer ersetzt sie
        listed = field in ("artist", "albumartist") and len(artist_list(current)) > 1
        if new and new != current and (overwrite or not current or listed):
            changes[field] = new
    return changes


def add_release_details(matches, lookup):
    """Ergänzt CD-Nummer, Titelzahl, Label und Album-Interpret; eine Abfrage je Album."""
    releases = sorted({found["release_id"] for _, found in matches if found.get("release_id")})
    details = {}
    for number, release_id in enumerate(releases, 1):
        job.step(number, len(releases), t("Album-Angaben laden"))
        try:
            details[release_id] = lookup.release(release_id)
        except Exception as exc:  # ohne diese Angaben geht es trotzdem weiter
            print(t("Album-Angaben nicht verfügbar: {reason}", reason=exc))
    for _, found in matches:
        info = details.get(found.get("release_id"))
        if not info:
            continue
        if found.get("track") and found.get("tracks"):
            found["track"] = f"{found['track']}/{found['tracks']}"
        if found.get("disc"):
            found["disc"] = f"{found['disc']}/{info['discs']}" if info.get("discs") else found["disc"]
        found["label"] = found.get("label") or info.get("label", "")
        found["albumartist"] = found.get("albumartist") or info.get("albumartist", "")


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
    failures = 0
    for number, track in enumerate(tracks, 1):
        job.step(number, len(tracks), t("Metadaten suchen"))
        done = complete(track)
        if done and os.path.dirname(track.path) not in open_folders:
            if wants_genres:
                matches.append((track, {"source": "genre"}))
            continue
        artist, title = identify(track)
        try:
            found = lookup.find(track.path, main_artist(artist), title, track.duration)
            failures = 0
        except Exception as exc:  # Eine Datei, die der Dienst ablehnt, darf den Lauf nicht beenden
            failures += 1
            if failures >= MAX_FAILURES:  # So oft in Folge liegt es nicht an der Datei, sondern z. B. am Key
                sys.exit(t("Abbruch: {reason}. Bisherige Treffer sind gespeichert, einfach erneut starten.", reason=exc))
            print(t("Fehler bei {path}: {reason}", path=track.path, reason=exc))
            found = None
        if found and not found.get("rejected"):
            matches.append((track, found))
        elif done and wants_genres:
            matches.append((track, {"source": "genre"}))
        elif not done:
            unresolved.append((track.path, artist, title, (found or {}).get("score", "")))
    if lookup.remembered:
        print(t("Aus früheren Läufen übernommen: {count} Titel.", count=lookup.remembered))
    return matches, unresolved


def _fetch_once(cache, key, fetch):
    """Fragt nicht neu nach, was ein Dienst sicher nicht hat; ein Ausfall zählt nicht dazu."""
    if cache.get(key):
        return None
    try:
        value = fetch()
    except ConnectionError:
        return None
    if not value:
        cache.set(key, True)
    return value


def _apply_tags(chosen, plan, cache):
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
                        # Nur das aktuelle Album behalten, bei 70.000 Titeln wäre der Speicher sonst voll
                        covers = {found["group"]: _fetch_once(cache, f"no-cover:{found['group']}",
                                                              lambda: fetch_cover(found["group"]))}
                    if covers[found["group"]]:
                        changes["cover"] = covers[found["group"]]
                if row["Songtext"]:
                    artist = changes.get("artist") or found.get("artist", clean(track.artist))
                    title = changes.get("title") or found.get("title", clean(track.title))
                    album = changes.get("album") or found.get("album", "")
                    text = _fetch_once(cache, f"no-lyrics:{normalize(artist)}|{normalize(title)}",
                                       lambda: fetch_lyrics(artist, title, album, track.duration))
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
    if lookup.fpcalc:
        print(t("Klangerkennung aktiv, Mindestwert {value} %.", value=f"{lookup.min_score * 100:g}"))
    else:
        print(t("Hinweis: fpcalc fehlt, die Suche läuft nur über Name und Tags."))
    wants_cover = getattr(args, "cover", False)
    wants_lyrics = getattr(args, "songtexte", False)
    wants_genres = getattr(args, "genres", False)
    rules = genres.load_rules(APP_DIR) if wants_genres else {}
    matches, unresolved = _search(args, tracks, lookup, wants_genres)
    aligned = align_albums(matches)
    add_release_details(matches, lookup)
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
    _apply_tags(chosen, plan, lookup.cache)


def check_pattern(pattern):
    try:
        pattern.format(**dict.fromkeys(PLACEHOLDERS, "x"))
    except (KeyError, ValueError, IndexError):
        sys.exit(t("Ungültiges Muster: {pattern}. Erlaubt sind {fields}.", pattern=pattern,
                   fields=", ".join(f"{{{f}}}" for f in PLACEHOLDERS)))


def period_years(args):
    years = getattr(args, "zeitraum", None)
    years = PERIOD_YEARS if years is None else years
    if not 1 <= years <= 100:
        sys.exit(t("Jahre je Zeitraum müssen zwischen 1 und 100 liegen."))
    return years


def period(year, years=PERIOD_YEARS):
    """Zeitraum wie "1980 - 1984"; die Grenzen liegen auf Vielfachen von years."""
    found = re.search(r"\d{4}", year or "")  # Tags enthalten auch "1984-05-01"
    if not found:
        return UNKNOWN_YEAR
    start = int(found[0]) // years * years
    return str(start) if years == 1 else f"{start} - {start + years - 1}"


def decade(year):
    found = re.search(r"\d{4}", year or "")
    return f"{int(found[0]) // 10 * 10}er" if found else UNKNOWN_YEAR


def initial(name):
    """Anfangsbuchstabe für Ordner wie „A“; „The Who“ steht unter W, Ziffern und Zeichen unter #."""
    name = re.sub(r"(?i)^(the|die|der|das)\s+", "", name.strip())
    first = name[:1].upper()
    return first if first.isalpha() else "#"


def target_name(track, pattern, years=PERIOD_YEARS):
    values = {f: clean(getattr(track, f)) for f in TAG_FIELDS}
    if not (values["artist"] and values["title"]):
        return None
    values["artist"] = display_artist(values["artist"])
    values["albumartist"] = display_artist(values["albumartist"]) or values["artist"]
    values["album"] = values["album"] or UNKNOWN_ALBUM
    # Bei mehreren Genres wie "Hip-Hop; Rap" zählt das erste, sonst entstünde ein Ordner je Kombination
    values["genre"] = re.split(r"\s*[;/,|]\s*", values["genre"])[0] or UNKNOWN_GENRE
    values["zeitraum"] = period(values["year"], years)
    values["jahrzehnt"] = decade(values["year"])
    values["buchstabe"] = initial(values["albumartist"])
    found = re.search(r"\d{4}", values["year"])  # Tags enthalten auch "1984-05-01"
    values["year"] = found[0] if found else ""
    values["track"] = values["track"].split("/")[0].zfill(2) if values["track"] else ""
    values["disc"] = values["disc"].split("/")[0]
    # Fehlt z. B. die Tracknummer, soll kein Name mit " - " beginnen
    *folders, file_name = [safe_filename(p.format(**values)).strip(" -") for p in pattern.split("/")]
    for number, part in enumerate(folders):
        if not part:  # Ordner ohne Angabe, etwa ohne Jahr oder Label
            used = re.findall(r"\{(\w+)\}", pattern.split("/")[number])
            folders[number] = UNKNOWN_FOLDER.get(used[0] if used else "", "Unbekannt")
    return os.path.join(*folders, file_name) + os.path.splitext(track.path)[1].lower() if file_name else None


def remove_empty_folders(folder, root):
    """Entfernt Ordner, die das Umsortieren geleert hat, aber nie die Sammlung selbst."""
    while system.fold(folder) != system.fold(root) and folder.startswith(root):
        try:
            os.rmdir(folder)
        except OSError:
            return
        folder = os.path.dirname(folder)


def plan_renames(tracks, pattern, root, taken, destination=None, years=PERIOD_YEARS):
    """Plant neue Namen; mit destination wandert alles Benennbare dorthin, der Rest bleibt liegen."""
    rows, skipped = [], 0
    # Ein Muster mit Ordnern sortiert die ganze Sammlung, sonst bleibt jede Datei in ihrem Ordner
    sorts = "/" in pattern or destination
    for track in tracks:
        name = target_name(track, pattern, years)
        if not name:
            skipped += 1
            continue
        target = os.path.join((destination or root) if sorts else os.path.dirname(track.path), name)
        if target == track.path:
            continue
        taken.discard(system.fold(track.path))
        base, ext = os.path.splitext(target)
        candidate, n = target, 2
        while system.fold(candidate) in taken:
            candidate, n = f"{base} ({n}){ext}", n + 1
        taken.add(system.fold(candidate))
        rows.append({"Alt": track.path, "Neu": candidate})
    return rows, skipped


def run_renames(args, rows, skipped, root):
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
            if os.path.exists(target) and not os.path.samefile(source, target):
                print(t("Übersprungen, Ziel existiert: {path}", path=target))
                continue
            try:
                journaling.move_file(source, target, journal)
                if root:
                    remove_empty_folders(os.path.dirname(source), root)
                done += 1
            except OSError as exc:
                print(t("Fehler bei {path}: {reason}", path=source, reason=exc))
    finally:
        journal.close()
        print(t("Dateien umbenannt: {count}", count=done))


def files_below(folder):
    return {system.fold(os.path.join(path, name)) for path, _, names in os.walk(folder) for name in names}


def cmd_rename(args):
    check_pattern(args.muster)
    years = period_years(args)
    destination = getattr(args, "zielordner", None)
    if destination:
        destination = os.path.abspath(destination)
        dupes = system.fold(dupes_dir(args))
        if system.fold(destination) == dupes or system.fold(destination).startswith(dupes + os.sep):
            sys.exit(t("Der Zielordner darf nicht im Dubletten-Ordner liegen."))
    root, db, tracks = prepare(args)
    taken = {system.fold(t_.path) for t_ in tracks}
    if destination:
        print(t("Zielordner: {path}. Dateien ohne Interpret oder Titel bleiben, wo sie sind.", path=destination))
        # Was dort schon liegt, auch Nicht-Musik, darf nicht überschrieben werden
        taken |= files_below(destination)
    rows, skipped = plan_renames(tracks, args.muster, root, taken, destination, years)
    run_renames(args, rows, skipped, root)


def collect_audio(paths):
    """Audiodateien aus einzeln gewählten Dateien und Ordnern, jede nur einmal."""
    found = {}
    for path in map(os.path.abspath, paths):
        if os.path.isdir(path):
            found.update(dict.fromkeys(library.find_audio(path, os.path.join(path, "Dubletten"))))
        elif path.lower().endswith(library.EXTENSIONS):
            found[path] = None
    return list(found)


def cmd_rename_files(args):
    """Benennt einzelne Dateien um; sie bleiben in ihrem Ordner, auch wenn das Muster Ordner enthält."""
    check_pattern(args.muster)
    paths = collect_audio(args.dateien)
    if not paths:
        print(t("Keine Audiodateien dabei."))
        return
    tracks = []
    for number, path in enumerate(paths, 1):
        job.step(number, len(paths), t("Dateien lesen"))
        try:
            track = library.read_track(path)
        except Exception as exc:  # defekte Dateien dürfen den Lauf nicht abbrechen
            print(t("Fehler bei {path}: {reason}", path=path, reason=exc))
            continue
        track.artist, track.title = identify(track)
        tracks.append(track)
    folders = {os.path.dirname(track.path) for track in tracks}
    taken = {system.fold(os.path.join(folder, name)) for folder in folders for name in os.listdir(folder)}
    years = period_years(args)
    rows, skipped = plan_renames(tracks, args.muster.split("/")[-1], None, taken, years=years)
    run_renames(args, rows, skipped, None)


def genre_counts(tracks):
    """Wie viele Dateien jedes Genre haben; "" zählt die Dateien ohne Genre."""
    counts = {}
    for track in tracks:
        genre = clean(track.genre)
        counts[genre] = counts.get(genre, 0) + 1
    return counts


def genre_changes(tracks, rules):
    """Dateien, deren Genre nach den eigenen Regeln anders heißen soll, mit dem neuen Genre."""
    changes = []
    for track in tracks:
        genre = clean(track.genre)
        target = genres.resolve(genre, rules) if genre else ""
        if target and target != genre:
            changes.append((track, target))
    return changes


def write_genres(changes):
    journal = journaling.Journal(DATA_DIR, "genres")
    saved = 0
    try:
        for number, (track, target) in enumerate(changes, 1):
            job.step(number, len(changes), t("Genres schreiben"))
            try:
                journal.record(action="tag", path=track.path, old={"genre": track.genre}, new={"genre": target})
                write_tags(track.path, {"genre": target})
                track.genre = target
                saved += 1
            except Exception as exc:
                print(t("Fehler bei {path}: {reason}", path=track.path, reason=exc))
    finally:
        journal.close()
        print(t("Genre geändert in {count} Dateien.", count=saved))


def cmd_genres(args):
    root, db, tracks = prepare(args)
    rules = genres.load_rules(APP_DIR)
    try:
        merges = genres.parse_merges(getattr(args, "zusammenfassen", None) or [])
    except ValueError as exc:
        sys.exit(t("Ungültige Angabe: {text}. Beispiel: --zusammenfassen „Dubstep, House=Techno“", text=exc))
    rules.update(merges)
    counts = genre_counts(tracks)
    rows = [(genre or t("(ohne Genre)"), count, genres.resolve(genre, rules) if genre else "")
            for genre, count in sorted(counts.items(), key=lambda item: (not item[0], -item[1], item[0].casefold()))]
    path = write_report("genres.csv", ("Genre", "Dateien", "wird zu"), rows)
    for genre, count, target in rows:
        print(f"{count:>7}  {genre}" + (f"  →  {target}" if target and target != genre else ""))
    changes = genre_changes(tracks, rules)
    print(t("{genres} Genres, {count} Dateien bekommen ein neues Genre. Bericht: {path}",
            genres=len([g for g in counts if g]), count=len(changes), path=path))
    if not args.apply:
        print(t("Vorschau: nichts geändert."))
        return
    if merges:
        genres.save_rules(APP_DIR, rules)
    write_genres(changes)


def forget_results(db):
    """Löscht Suchergebnisse, Fingerabdrücke und den gelesenen Stand der Sammlung; der Verlauf bleibt."""
    count = db.execute("SELECT count(*) FROM lookups").fetchone()[0]
    db.execute("DELETE FROM lookups")
    db.execute("DELETE FROM files")
    db.commit()
    return count


def cmd_forget(args):
    count = forget_results(library.connect(DB_PATH))
    print(t("Gespeicherte Ergebnisse gelöscht: {count}. Der nächste Lauf beginnt von vorn, der Verlauf bleibt erhalten.", count=count))


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


def console_progress():
    """Macht lange Läufe auf der Konsole sichtbar, ohne sie zu fluten."""
    last = [0.0]

    def report(done, total, text, left):
        now = time.monotonic()
        if now - last[0] >= PROGRESS_GAP:
            last[0] = now
            print(progress_line(done, total, text, left), flush=True)
    return report


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    job.listener = console_progress()
    keep_lines = argparse.RawDescriptionHelpFormatter  # sonst bricht argparse die Links um
    parser = argparse.ArgumentParser(prog="music-renamer-cli", description="Musiksammlung aufräumen",
                                     formatter_class=keep_lines, epilog=HELP_EPILOG)
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name, handler, help_text):
        sub = commands.add_parser(name, help=help_text, formatter_class=keep_lines,
                                  epilog=f"Beispiele: {DOCS_URL}Befehlszeile.md#{name}")
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
    rename.add_argument("--zeitraum", type=int, default=PERIOD_YEARS,
                        help=f"Jahre je Zeitraum für {{zeitraum}}, Standard {PERIOD_YEARS}")
    rename.add_argument("--ziel", dest="zielordner",
                        help="verschiebt alle benennbaren Dateien in diesen Ordner, der Rest bleibt in der Sammlung")
    genre = command("genres", cmd_genres, "Genres der Sammlung auflisten und zusammenfassen")
    genre.add_argument("--zusammenfassen", action="append", metavar='"A, B=ZIEL"',
                       help='macht aus den Genres A und B das Genre ZIEL, mehrfach möglich')
    undo = commands.add_parser("undo", help="letzten ausgeführten Schritt zurücknehmen", formatter_class=keep_lines,
                               epilog=f"Mehr dazu: {DOCS_URL}Befehlszeile.md#undo")
    undo.set_defaults(handler=cmd_undo)
    forget = commands.add_parser("vergessen", help="gespeicherte Suchergebnisse löschen, um von vorn zu beginnen",
                                 formatter_class=keep_lines, epilog=f"Mehr dazu: {DOCS_URL}Befehlszeile.md#vergessen")
    forget.set_defaults(handler=cmd_forget)
    update = commands.add_parser("update", help="auf GitHub nach einer neuen Version suchen", formatter_class=keep_lines,
                                 epilog=f"Mehr dazu: {DOCS_URL}Befehlszeile.md#update")
    update.set_defaults(handler=cmd_update)

    args = parser.parse_args()
    try:
        args.handler(args)
    except Cancelled:
        print(t("Abgebrochen. Bereits Erledigtes bleibt erhalten und lässt sich im Verlauf zurücknehmen."))


if __name__ == "__main__":
    main()
