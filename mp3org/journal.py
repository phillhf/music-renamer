"""Protokoll aller Änderungen; jede Zeile wird vor der Änderung geschrieben."""
import glob
import json
import os
import shutil
import time

from .tags import write_tags


class Journal:
    def __init__(self, folder, kind):
        os.makedirs(folder, exist_ok=True)
        # Nanosekunden halten Läufe derselben Sekunde chronologisch sortierbar
        self.path = os.path.join(folder, f"journal-{time.time_ns()}-{kind}.jsonl")
        self._file = open(self.path, "a", encoding="utf-8")

    def record(self, **entry):
        self._file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._file.flush()
        os.fsync(self._file.fileno())

    def close(self):
        self._file.close()


def unique_path(path):
    """Freier Zielpfad; vorhandene Dateien werden nie überschrieben."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{base} ({n}){ext}"):
        n += 1
    return f"{base} ({n}){ext}"


def move_file(source, target, journal):
    os.makedirs(os.path.dirname(target), exist_ok=True)
    journal.record(action="move", source=source, target=target)
    shutil.move(source, target)


def undo_last(folder):
    """Macht den letzten Lauf rückgängig und benennt sein Journal um."""
    journals = sorted(glob.glob(os.path.join(folder, "journal-*.jsonl")))
    if not journals:
        return None, 0, []
    path = journals[-1]
    with open(path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    done, problems = 0, []
    for entry in reversed(entries):
        try:
            if entry["action"] == "move":
                if os.path.exists(entry["source"]):
                    raise FileExistsError(f"Ziel belegt: {entry['source']}")
                if os.path.exists(entry["target"]):
                    os.makedirs(os.path.dirname(entry["source"]), exist_ok=True)
                    shutil.move(entry["target"], entry["source"])
                    done += 1
            elif entry["action"] == "tag":
                write_tags(entry["path"], entry["old"])
                done += 1
        except Exception as exc:
            problems.append(f"{entry.get('source') or entry.get('path')}: {exc}")
    if not problems:
        os.replace(path, path + ".undone")
    return path, done, problems
