"""Wandelt Audiodateien in MP3 um; echte Videos werden vorher erkannt und bleiben liegen.

Geprüft wird mit ffprobe: Eine Datei braucht eine Tonspur und darf kein bewegtes Bild haben.
Ein eingebettetes Cover zählt nicht als Video, ein Film in einer MP4-Datei schon.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from mutagen.mp3 import MP3

from .i18n import t
from .job import job
from .journal import unique_path
from .library import ORIGINALS  # auch die Sammlung lässt diesen Ordner aus
from .tags import FIELDS, OPENERS, open_audio, read_cover, read_tags
from .tags import _write_id3 as write_id3

# Alles, was Ton enthalten kann; Videoformate gehören dazu, damit sie geprüft und gemeldet werden
CANDIDATES = (".flac", ".m4a", ".m4b", ".mp4", ".aac", ".ogg", ".oga", ".opus", ".wav", ".wma", ".aif",
              ".aiff", ".ape", ".wv", ".mka", ".webm", ".mkv", ".mov", ".avi", ".3gp", ".amr", ".ac3",
              ".mpc", ".tta", ".dsf", ".mp2", ".wmv", ".flv")
IMAGE_CODECS = {"mjpeg", "png", "bmp", "gif", "webp", "tiff", "jpegls"}
QUALITIES = {"v0": ["-q:a", "0"], "320": ["-b:a", "320k"], "256": ["-b:a", "256k"], "192": ["-b:a", "192k"]}
MAX_DURATION_GAP = 1.5  # Sekunden; mehr Abweichung heißt, die Umwandlung ist abgebrochen
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_tool(name):
    """ffmpeg oder ffprobe: mitgeliefert, aus tools/ oder vom System."""
    exe = name + (".exe" if os.name == "nt" else "")
    bundled = getattr(sys, "_MEIPASS", "")
    # Unter Windows liegt die Befehlszeile in <Programm>\cli und nutzt das ffmpeg des Fenster-Programms
    shared = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "_internal") if bundled else ""
    for folder in (bundled, shared, os.path.join(PROJECT_DIR, "tools")):
        path = os.path.join(folder, exe)
        if folder and os.path.exists(path):
            return path
    return shutil.which(name)


def tools():
    ffmpeg, ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
    if not (ffmpeg and ffprobe):
        sys.exit(t("Zum Umwandeln fehlt ffmpeg. Windows: Setup erneut starten. Linux: sudo apt install ffmpeg. Mac: brew install ffmpeg."))
    return ffmpeg, ffprobe


def probe(path, ffprobe):
    """Was in der Datei steckt: kind ist audio, video, stumm oder defekt."""
    try:
        output = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                                capture_output=True, timeout=120, creationflags=NO_WINDOW)
        data = json.loads(output.stdout or b"{}")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return {"kind": "defekt", "reason": str(exc)}
    if output.returncode != 0 or not data.get("streams"):
        return {"kind": "defekt", "reason": output.stderr.decode("utf-8", "replace").strip()[:200]}
    audio = [s for s in data["streams"] if s.get("codec_type") == "audio"]
    moving = [s for s in data["streams"] if s.get("codec_type") == "video" and not _still_image(s)]
    duration = float(data.get("format", {}).get("duration") or (audio[0].get("duration") if audio else 0) or 0)
    info = {"duration": duration, "codec": audio[0].get("codec_name", "") if audio else "",
            "cover": any(s.get("codec_type") == "video" and _still_image(s) for s in data["streams"])}
    if moving:
        video = moving[0]
        return {**info, "kind": "video",
                "reason": f"{video.get('codec_name', '')} {video.get('width', '?')}x{video.get('height', '?')}"}
    if not audio:
        return {**info, "kind": "stumm", "reason": t("keine Tonspur")}
    return {**info, "kind": "audio"}


def _still_image(stream):
    """Ein Cover ist als Bild-Stream eingebettet; ein Film hat viele Bilder."""
    if stream.get("disposition", {}).get("attached_pic"):
        return True
    return stream.get("codec_name") in IMAGE_CODECS and int(stream.get("nb_frames") or 1) <= 1


def find_candidates(paths):
    """Dateien, die umgewandelt werden könnten; MP3 und der Ordner der Originale bleiben außen vor."""
    found = []
    for path in map(os.path.abspath, paths):
        if os.path.isdir(path):
            for folder, subdirs, names in os.walk(path):
                job.detail(t("Ordner: {path}", path=folder))
                subdirs[:] = [d for d in subdirs if d != ORIGINALS]
                found += [os.path.join(folder, n) for n in sorted(names) if n.lower().endswith(CANDIDATES)]
        elif path.lower().endswith(CANDIDATES):
            found.append(path)
    return list(dict.fromkeys(found))


def target_for(path):
    return os.path.splitext(path)[0] + ".mp3"


def check(paths, ffprobe):
    """Prüft jede Datei; liefert (umwandelbar, Bericht)."""
    ready, rows = [], []
    for number, path in enumerate(paths, 1):
        job.step(number, len(paths), t("Dateien prüfen"))
        job.detail(t("Prüfen: {path}", path=path))
        info = probe(path, ffprobe)
        if info["kind"] == "audio" and os.path.exists(target_for(path)):
            info = {**info, "kind": "vorhanden", "reason": t("{name} gibt es schon", name=os.path.basename(target_for(path)))}
        verdict = {"audio": t("wird umgewandelt"), "video": t("Video, bleibt liegen"), "stumm": t("keine Tonspur, bleibt liegen"),
                   "defekt": t("nicht lesbar, bleibt liegen"), "vorhanden": t("MP3 gibt es schon, bleibt liegen")}[info["kind"]]
        details = info.get("reason") or f"{info['codec']}, {round(info['duration'])} s" + (", Cover" if info.get("cover") else "")
        job.detail(f"{verdict} ({details})", sub=True)
        rows.append({"Datei": path, "Format": info.get("codec", ""), "Prüfung": verdict, "Hinweis": info.get("reason", ""),
                     "Sekunden": round(info.get("duration") or 0)})
        if info["kind"] == "audio":
            ready.append((path, info))
    return ready, rows


def convert_file(path, info, ffmpeg, ffprobe, quality):
    """Wandelt eine Datei um und prüft das Ergebnis; liefert den Pfad der MP3."""
    target = target_for(path)
    part = target + ".teil"
    command = [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", path, "-map", "0:a:0", "-vn",
               "-codec:a", "libmp3lame", *QUALITIES[quality], "-map_metadata", "0", "-id3v2_version", "3",
               "-f", "mp3", part]
    try:
        output = subprocess.run(command, capture_output=True, timeout=3600, creationflags=NO_WINDOW)
        if output.returncode != 0:
            raise RuntimeError(output.stderr.decode("utf-8", "replace").strip()[-300:] or f"ffmpeg {output.returncode}")
        result = probe(part, ffprobe)
        if result["kind"] != "audio" or abs(result["duration"] - info["duration"]) > MAX_DURATION_GAP:
            raise RuntimeError(t("Ergebnis unvollständig: {got} statt {want} Sekunden",
                                 got=round(result.get("duration") or 0), want=round(info["duration"])))
        _copy_tags(path, part)
        os.replace(part, target)
    finally:
        if os.path.exists(part):
            os.remove(part)
    return target


def _copy_tags(source, mp3):
    """Überträgt Tags und Cover über die eigene Tag-Schicht, damit alle Felder gleich heißen."""
    if os.path.splitext(source)[1].lower() not in OPENERS:
        return  # ffmpeg hat übernommen, was es lesen konnte
    try:
        audio = open_audio(source)
        values = {f: v for f, v in read_tags(audio).items() if f in FIELDS and v}
        cover = read_cover(audio)
    except Exception:  # Tags sind nett, aber kein Grund, die Umwandlung zu verwerfen
        return
    if cover:
        values["cover"] = cover
    if values:
        # Die Teildatei endet noch nicht auf .mp3, darum direkt als MP3 öffnen
        audio = MP3(mp3)
        if audio.tags is None:
            audio.add_tags()
        write_id3(audio, values)


def originals_folder(path, root):
    """Wohin das Original wandert: gleicher Unterordner unter „Originale vor dem Umwandeln“."""
    base = root if root and os.path.isdir(root) else os.path.dirname(path)
    relative = os.path.relpath(path, base)
    return os.path.join(base, ORIGINALS, relative)


def convert_all(ready, ffmpeg, ffprobe, quality, keep, root, journal):
    """Wandelt parallel um; jede fertige Datei landet sofort im Verlauf."""
    workers = max(1, min(4, (os.cpu_count() or 2) // 2))
    count = {"done": 0, "failed": 0, "number": 0}
    started = {}

    def finish(future):
        count["number"] += 1
        path, begin = started.pop(future)
        try:
            target = future.result()
        except Exception as exc:
            count["failed"] += 1
            print(t("Fehler bei {path}: {reason}", path=path, reason=exc))
            return
        backup = None if keep else unique_path(originals_folder(path, root))
        journal.record(action="convert", source=path, created=target, backup=backup)
        if backup:
            os.makedirs(os.path.dirname(backup), exist_ok=True)
            shutil.move(path, backup)
        count["done"] += 1
        job.detail(t("fertig: {path} ({seconds} s)", path=target, seconds=f"{time.monotonic() - begin:.1f}"), sub=True)

    queue, pending = list(ready), set()
    with ThreadPoolExecutor(workers) as pool:
        try:
            job.step(0, len(ready), t("Nach MP3 umwandeln"))
            while queue or pending:
                while queue and len(pending) < workers:
                    path, info = queue.pop(0)
                    job.detail(t("Umwandeln: {path}", path=path))
                    future = pool.submit(convert_file, path, info, ffmpeg, ffprobe, quality)
                    started[future] = (path, time.monotonic())
                    pending.add(future)
                finished, pending = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                for future in finished:
                    finish(future)
                job.step(count["number"], len(ready), t("Nach MP3 umwandeln"))
        except BaseException:
            # Beim Abbrechen laufende Dateien noch fertig machen und eintragen, keine halben Zustände
            pool.shutdown(wait=True, cancel_futures=True)
            for future in [f for f in pending if not f.cancelled()]:
                finish(future)
            raise
        finally:
            print(t("Umgewandelt: {done}, fehlgeschlagen: {failed}.", done=count["done"], failed=count["failed"]))
    return count["done"], count["failed"]
