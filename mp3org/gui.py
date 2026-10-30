"""Fenster für die drei Arbeitsschritte. Die Logik liegt in cli.py."""
import contextlib
import json
import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from argparse import Namespace
from tkinter import filedialog, messagebox, ttk

from . import __version__, cli, journal, updater
from .lookup import LEVELS, parse_accuracy

SETTINGS_PATH = os.path.join(cli.APP_DIR, "einstellungen.json")
ACOUSTID_KEY_URL = "https://acoustid.org/new-application"


def level_label(level):
    return f"{level.title()} ({LEVELS[level] * 100:.0f} %)"


LEVEL_LABELS = {level_label(level): level for level in LEVELS}


class QueueWriter:
    def __init__(self, target):
        self.target = target

    def write(self, text):
        if text.strip():
            self.target.put(("log", text.rstrip()))

    def flush(self):
        pass


def load_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    os.makedirs(cli.APP_DIR, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


class App(tk.Tk):
    def __init__(self, auto_update_check=True):
        super().__init__()
        self.title(f"MP3 Organizer {__version__}")
        self.geometry("820x620")
        self.minsize(680, 480)
        icon = os.path.join(getattr(sys, "_MEIPASS", ""), "app.ico")
        if getattr(sys, "frozen", False) and os.path.exists(icon):
            self.iconbitmap(icon)
        self.events = queue.Queue()
        self.buttons = []
        settings = load_settings()
        self.folder = tk.StringVar(value=settings.get("ordner", ""))
        self.acoustid_key = tk.StringVar(value=settings.get("acoustid_key", ""))
        saved_level = settings.get("genauigkeit", "normal").lower()
        self.accuracy = tk.StringVar(value=level_label(saved_level if saved_level in LEVELS else "normal"))
        self.custom_accuracy = tk.StringVar(value=settings.get("eigene_genauigkeit", ""))
        self.similar = tk.BooleanVar(value=False)
        self.overwrite = tk.BooleanVar(value=False)
        self._build()
        self.after(100, self._drain_events)
        if auto_update_check:
            self._run_background(self._check_update, quiet=True)

    def _build(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(6, weight=1)

        ttk.Label(main, text="Sammlung:").grid(row=0, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.folder).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(main, text="Auswählen ...", command=self._choose).grid(row=0, column=2, sticky="ew")

        self._step(main, 1, "1. Dubletten verschieben", self._dupes)
        ttk.Checkbutton(main, text="Auch ähnliche Dubletten (gleicher Titel, andere Datei)",
                        variable=self.similar).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 6))
        self._step(main, 3, "2. Metadaten ergänzen", self._tags)
        options = ttk.Frame(main)
        options.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        ttk.Checkbutton(options, text="Vorhandene Tags ersetzen statt nur leere Felder füllen",
                        variable=self.overwrite).pack(anchor="w")
        accuracy = ttk.Frame(options)
        accuracy.pack(anchor="w", pady=(4, 0))
        ttk.Label(accuracy, text="Genauigkeit Klangerkennung:").pack(side="left", padx=(0, 4))
        self.level_box = ttk.Combobox(accuracy, textvariable=self.accuracy, values=list(LEVEL_LABELS),
                                      state="readonly", width=14)
        self.level_box.pack(side="left")
        ttk.Label(accuracy, text="oder eigener Wert:").pack(side="left", padx=(12, 4))
        ttk.Entry(accuracy, textvariable=self.custom_accuracy, width=6).pack(side="left")
        ttk.Label(accuracy, text="%").pack(side="left", padx=(2, 0))
        self.custom_accuracy.trace_add("write", self._update_level_box)
        self._update_level_box()
        self._step(main, 5, "3. Dateien umbenennen", self._rename)

        self.log = tk.Text(main, height=12, state="disabled", wrap="word")
        self.log.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=8)

        bottom = ttk.Frame(main)
        bottom.grid(row=7, column=0, columnspan=3, sticky="ew")
        self._button(bottom, "Letzten Schritt rückgängig", self._undo).pack(side="left")
        ttk.Button(bottom, text="Berichte öffnen", command=self._open_reports).pack(side="left", padx=6)
        self._button(bottom, "Nach Updates suchen",
                     lambda: self._run_background(self._check_update, quiet=False)).pack(side="left")
        ttk.Label(bottom, text="AcoustID-Key:").pack(side="left", padx=(12, 4))
        ttk.Entry(bottom, textvariable=self.acoustid_key, width=14, show="*").pack(side="left")
        link = tk.Label(bottom, text="Key holen", fg="#0a58ca", cursor="hand2",
                        font=("Segoe UI", 9, "underline"))
        link.pack(side="left", padx=(6, 0))
        link.bind("<Button-1>", lambda event: webbrowser.open(ACOUSTID_KEY_URL))

    def _step(self, parent, row, label, action):
        ttk.Label(parent, text=label).grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 2))
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=2, sticky="e", pady=(6, 2))
        self._button(frame, "Vorschau", lambda: action(False)).pack(side="left")
        self._button(frame, "Ausführen", lambda: action(True)).pack(side="left", padx=(6, 0))

    def _button(self, parent, text, command):
        button = ttk.Button(parent, text=text, command=command)
        self.buttons.append(button)
        return button

    def _choose(self):
        folder = filedialog.askdirectory(title="MP3-Sammlung auswählen")
        if folder:
            self.folder.set(os.path.normpath(folder))

    def _open_reports(self):
        os.makedirs(cli.REPORT_DIR, exist_ok=True)
        os.startfile(cli.REPORT_DIR)

    def _print(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drain_events(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._print(value)
            elif kind == "busy":
                for button in self.buttons:
                    button.configure(state="disabled" if value else "normal")
            elif kind == "offer_update":
                self._offer_update(value)
            elif kind == "quit":
                self.destroy()
                return
        self.after(100, self._drain_events)

    def _run_background(self, work, *args, **kwargs):
        def runner():
            self.events.put(("busy", True))
            with contextlib.redirect_stdout(QueueWriter(self.events)):
                try:
                    work(*args, **kwargs)
                except SystemExit as exc:
                    if exc.code:
                        print(exc.code)
                except Exception as exc:
                    print(f"Fehler: {exc}")
            self.events.put(("busy", False))
        threading.Thread(target=runner, daemon=True).start()

    def _start(self, command, apply, question, **options):
        folder = self.folder.get().strip()
        if not folder:
            messagebox.showinfo("MP3 Organizer", "Bitte zuerst die Sammlung auswählen.")
            return
        if apply and not messagebox.askyesno("MP3 Organizer", question):
            return
        settings = {"ordner": folder, "acoustid_key": self.acoustid_key.get().strip(),
                    "genauigkeit": LEVEL_LABELS[self.accuracy.get()],
                    "eigene_genauigkeit": self.custom_accuracy.get().strip()}
        save_settings(settings)
        os.environ["ACOUSTID_KEY"] = settings["acoustid_key"]
        self._run_background(command, Namespace(ordner=folder, apply=apply, **options))

    def _dupes(self, apply):
        self._start(cli.cmd_dupes, apply, "Dubletten jetzt in den Dubletten-Ordner verschieben?",
                    ziel=None, aehnlich=self.similar.get())

    def _tags(self, apply):
        accuracy = self.custom_accuracy.get().strip() or LEVEL_LABELS[self.accuracy.get()]
        try:
            parse_accuracy(accuracy)
        except ValueError:
            messagebox.showerror("MP3 Organizer", "Bitte als eigenen Wert eine Zahl von 1 bis 100 eintragen.")
            return
        self._start(cli.cmd_tag, apply, "Tags jetzt in die Dateien schreiben?",
                    ueberschreiben=self.overwrite.get(), limit=None, genauigkeit=accuracy)

    def _update_level_box(self, *unused):
        # Ein eigener Wert hat Vorrang, die Stufe gilt dann nicht
        self.level_box.configure(state="disabled" if self.custom_accuracy.get().strip() else "readonly")

    def _rename(self, apply):
        self._start(cli.cmd_rename, apply, "Dateien jetzt umbenennen?", muster="{artist} - {title}")

    def _undo(self):
        if messagebox.askyesno("MP3 Organizer", "Den zuletzt ausgeführten Schritt zurücknehmen?"):
            self._run_background(cli.cmd_undo, None)

    def _check_update(self, quiet):
        try:
            release = updater.check_latest()
        except Exception as exc:
            if not quiet:
                print(f"Update-Prüfung fehlgeschlagen: {exc}")
            return
        if release:
            self.events.put(("offer_update", release))
        elif not quiet:
            print(f"Version {__version__} ist aktuell.")

    def _offer_update(self, release):
        if not updater.can_self_update():
            self._print(f"Neue Version {release.version}: {release.page}")
            return
        if messagebox.askyesno("Update verfügbar",
                               f"Version {release.version} ist verfügbar (installiert: {__version__}).\n"
                               "Jetzt herunterladen und installieren?"):
            self._run_background(self._install_update, release)

    def _install_update(self, release):
        print(f"Lade Version {release.version} ...")
        path = updater.download(release)
        print("Installation startet, das Programm schließt sich.")
        updater.start_installer(path)
        self.events.put(("quit", None))


def main():
    App().mainloop()
