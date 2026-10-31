"""Protokoll aller Änderungen; jede Zeile wird vor der Änderung geschrieben."""
import glob
import json
import os
import re
import shutil
import time

from .tags import write_tags

NAME = re.compile(r"journal-(\d+)-(\w+)\.jsonl$")


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


def _entries(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def list_runs(folder):
    """Alle zurücknehmbaren Läufe, der neueste zuerst."""
    runs = []
    for path in sorted(glob.glob(os.path.join(folder, "journal-*.jsonl")), reverse=True):
        match = NAME.search(path)
        count = len(_entries(path))
        if match and count:
            runs.append({"path": path, "time": int(match[1]) / 1e9, "kind": match[2], "count": count})
    return runs


def undo_run(path):
    """Nimmt einen Lauf zurück und benennt sein Protokoll um."""
    done, problems = 0, []
    for entry in reversed(_entries(path)):
        try:
            if entry["action"] == "move":
                if os.path.exists(entry["source"]):
                    same = os.path.normcase(entry["source"]) == os.path.normcase(entry["target"])
                    if not same:
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
    return done, problems


def undo_until(folder, path):
    """Nimmt alle Läufe bis einschließlich path zurück, der neueste zuerst.

    Spätere Läufe bauen auf früheren auf, darum geht es nur in dieser Reihenfolge.
    """
    done, problems = 0, []
    for run in list_runs(folder):
        count, failed = undo_run(run["path"])
        done += count
        problems += failed
        if failed or run["path"] == path:
            break
    return done, problems


def undo_last(folder):
    runs = list_runs(folder)
    if not runs:
        return None, 0, []
    return (runs[0]["path"], *undo_run(runs[0]["path"]))
