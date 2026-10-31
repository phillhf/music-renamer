"""Fenster für die drei Arbeitsschritte. Die Logik liegt in cli.py."""
import contextlib
import datetime
import json
import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from argparse import Namespace
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from . import __version__, cli, genres, i18n, journal, system, updater
from .editor import TagEditor
from .i18n import format_duration, t
from .job import Cancelled, job
from .lookup import LEVELS, parse_accuracy
from .review import ReviewWindow

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


class HistoryWindow(tk.Toplevel):
    """Alle ausgeführten Schritte; Zurücknehmen schließt neuere Schritte mit ein."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title(t("Verlauf"))
        self.geometry("560x380")
        columns = {"date": "Datum", "kind": "Art", "count": "Gesamt"}
        self.tree = ttk.Treeview(self, columns=tuple(columns), show="headings", selectmode="browse")
        for column, label in columns.items():
            self.tree.heading(column, text=t(label))
        self.tree.pack(fill="both", expand=True, padx=12, pady=(12, 6))
        ttk.Button(self, text=t("Zurücknehmen"), command=self.undo).pack(anchor="e", padx=12, pady=(0, 12))
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for run in journal.list_runs(cli.DATA_DIR):
            date = datetime.datetime.fromtimestamp(run["time"]).strftime("%d.%m.%Y %H:%M")
            self.tree.insert("", "end", iid=run["path"], values=(date, run["kind"], run["count"]))

    def undo(self):
        selection = self.tree.selection()
        if selection and messagebox.askyesno(
                t("Verlauf"), t("Zurücknehmen bis zu diesem Schritt? Neuere Schritte werden mit zurückgenommen."),
                parent=self):
            done, problems = journal.undo_until(cli.DATA_DIR, selection[0])
            self.app._print(t("Dateien zurückgenommen: {count}", count=done))
            for problem in problems:
                self.app._print(problem)
            self.refresh()


class App(tk.Tk, TkinterDnD.DnDWrapper):
    def __init__(self, auto_update_check=True):
        super().__init__()
        settings = load_settings()
        i18n.language = settings.get("sprache", "de")
        self.title(f"Music Renamer {__version__}")
        self.geometry("840x760")
        self.minsize(740, 680)
        icon = os.path.join(getattr(sys, "_MEIPASS", ""), "app.ico")
        if getattr(sys, "frozen", False) and os.path.exists(icon):
            self.iconbitmap(icon)
        self.events = queue.Queue()
        self.buttons = []
        self.folder = tk.StringVar(value=settings.get("ordner", ""))
        self.acoustid_key = tk.StringVar(value=settings.get("acoustid_key", ""))
        self.discogs_token = tk.StringVar(value=settings.get("discogs_token", ""))
        saved_level = settings.get("genauigkeit", "normal").lower()
        self.accuracy = tk.StringVar(value=level_label(saved_level if saved_level in LEVELS else "normal"))
        self.custom_accuracy = tk.StringVar(value=settings.get("eigene_genauigkeit", ""))
        self.similar = tk.BooleanVar(value=False)
        self.sound = tk.BooleanVar(value=False)
        self.overwrite = tk.BooleanVar(value=False)
        self.cover = tk.BooleanVar(value=settings.get("cover", False))
        self.lyrics = tk.BooleanVar(value=settings.get("songtexte", False))
        self.unify_genres = tk.BooleanVar(value=settings.get("genres", False))
        self.pattern = tk.StringVar(value=settings.get("muster", cli.PATTERNS[0]))
        self.language = tk.StringVar(value=next(k for k, v in i18n.LANGUAGES.items() if v == i18n.language))
        self.progress_text = tk.StringVar()
        self._build()
        self._enable_drop()
        job.listener = lambda *values: self.events.put(("progress", values))
        self.after(100, self._drain_events)
        if auto_update_check:
            self._run_background(self._check_update, quiet=True)

    def _build(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(7, weight=1)

        ttk.Label(main, text=t("Sammlung:")).grid(row=0, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.folder).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(main, text=t("Auswählen ..."), command=self._choose).grid(row=0, column=2, sticky="ew")

        self._step(main, 1, t("1. Dubletten verschieben"), self._dupes)
        dupes = ttk.Frame(main)
        dupes.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        ttk.Checkbutton(dupes, text=t("Am Klang vergleichen (findet auch andere Bitraten und Formate, langsamer)"),
                        variable=self.sound).pack(anchor="w")
        ttk.Checkbutton(dupes, text=t("Auch ähnliche Dubletten (gleicher Titel, andere Datei)"),
                        variable=self.similar).pack(anchor="w")
        self._step(main, 3, t("2. Metadaten ergänzen"), self._tags)
        options = ttk.Frame(main)
        options.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        ttk.Checkbutton(options, text=t("Vorhandene Tags ersetzen statt nur leere Felder füllen"),
                        variable=self.overwrite).pack(anchor="w")
        extras = ttk.Frame(options)
        extras.pack(anchor="w")
        ttk.Checkbutton(extras, text=t("Fehlende Cover einbetten"), variable=self.cover).pack(side="left")
        ttk.Checkbutton(extras, text=t("Fehlende Songtexte einbetten"), variable=self.lyrics).pack(
            side="left", padx=(12, 0))
        ttk.Checkbutton(extras, text=t("Genres vereinheitlichen"), variable=self.unify_genres).pack(
            side="left", padx=(12, 0))
        accuracy = ttk.Frame(options)
        accuracy.pack(anchor="w", pady=(4, 0))
        ttk.Label(accuracy, text=t("Genauigkeit Klangerkennung:")).pack(side="left", padx=(0, 4))
        self.level_box = ttk.Combobox(accuracy, textvariable=self.accuracy, values=list(LEVEL_LABELS),
                                      state="readonly", width=14)
        self.level_box.pack(side="left")
        ttk.Label(accuracy, text=t("oder eigener Wert:")).pack(side="left", padx=(12, 4))
        ttk.Entry(accuracy, textvariable=self.custom_accuracy, width=6).pack(side="left")
        ttk.Label(accuracy, text="%").pack(side="left", padx=(2, 0))
        self.custom_accuracy.trace_add("write", self._update_level_box)
        self._update_level_box()
        key_row = ttk.Frame(options)
        key_row.pack(anchor="w", pady=(4, 0))
        ttk.Label(key_row, text=t("AcoustID-Key:")).pack(side="left", padx=(0, 4))
        ttk.Entry(key_row, textvariable=self.acoustid_key, width=18, show="*").pack(side="left")
        link = tk.Label(key_row, text=t("Key holen"), fg="#0a58ca", cursor="hand2",
                        font=("Segoe UI", 9, "underline"))
        link.pack(side="left", padx=(6, 0))
        link.bind("<Button-1>", lambda event: webbrowser.open(ACOUSTID_KEY_URL))
        ttk.Label(key_row, text=t("Discogs-Token:")).pack(side="left", padx=(14, 4))
        ttk.Entry(key_row, textvariable=self.discogs_token, width=18, show="*").pack(side="left")
        self._step(main, 5, t("3. Dateien umbenennen und sortieren"), self._rename)
        section = ttk.Frame(main)
        section.grid(row=6, column=0, columnspan=3, sticky="ew")
        rename = ttk.Frame(section)
        rename.pack(fill="x")
        ttk.Label(rename, text=t("Muster:")).pack(side="left", padx=(0, 4))
        ttk.Combobox(rename, textvariable=self.pattern, values=cli.PATTERNS).pack(side="left", fill="x", expand=True)
        self.drop_zone = ttk.Label(section, text=t("Audiodateien oder Ordner hier ablegen, um sie direkt umzubenennen"),
                                   anchor="center", relief="groove", padding=8)
        self.drop_zone.pack(fill="x", pady=(6, 0))

        self.log = tk.Text(main, height=6, state="disabled", wrap="word")
        self.log.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=8)

        progress = ttk.Frame(main)
        progress.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.progress = ttk.Progressbar(progress, maximum=100)
        self.progress.pack(side="left", fill="x", expand=True)
        self.cancel_button = ttk.Button(progress, text=t("Abbrechen"), command=job.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(6, 0))
        ttk.Label(main, textvariable=self.progress_text).grid(row=9, column=0, columnspan=3, sticky="w", pady=(0, 6))

        bottom = ttk.Frame(main)
        bottom.grid(row=10, column=0, columnspan=3, sticky="ew")
        self._button(bottom, t("Verlauf"), lambda: HistoryWindow(self)).pack(side="left")
        ttk.Button(bottom, text=t("Berichte öffnen"), command=self._open_reports).pack(side="left", padx=6)
        self._button(bottom, t("Tag-Editor"), self._open_editor).pack(side="left")
        ttk.Button(bottom, text=t("Genre-Regeln"), command=self._open_rules).pack(side="left", padx=6)
        self._button(bottom, t("Nach Updates suchen"),
                     lambda: self._run_background(self._check_update, quiet=False)).pack(side="left")
        language = ttk.Combobox(bottom, textvariable=self.language, values=list(i18n.LANGUAGES),
                                state="readonly", width=8)
        language.pack(side="right")
        language.bind("<<ComboboxSelected>>", self._language_changed)
        ttk.Label(bottom, text=t("Sprache:")).pack(side="right", padx=(0, 4))

    def _enable_drop(self):
        """Macht das ganze Fenster zum Ablageziel; ohne tkdnd geht alles andere weiter."""
        try:
            TkinterDnD._require(self)
        except (RuntimeError, tk.TclError) as exc:
            self.drop_zone.pack_forget()
            self._print(t("Dateien ablegen ist nicht verfügbar: {reason}", reason=exc))
            return
        widgets = [self]
        while widgets:
            widget = widgets.pop()
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._drop)
            widgets.extend(widget.winfo_children())

    def _drop(self, event):
        if str(self.cancel_button.cget("state")) == "normal":
            self._print(t("Bitte warten, bis der laufende Schritt fertig ist."))
            return event.action
        paths = self.tk.splitlist(event.data)
        settings = self._save()
        self._run_background(cli.cmd_rename_files, Namespace(dateien=paths, muster=settings["muster"], apply=True,
                                                             review=self._ask_review))
        return event.action

    def _step(self, parent, row, label, action):
        ttk.Label(parent, text=label).grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 2))
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=2, sticky="e", pady=(6, 2))
        self._button(frame, t("Vorschau"), lambda: action(False)).pack(side="left")
        self._button(frame, t("Prüfen und ausführen"), lambda: action(True)).pack(side="left", padx=(6, 0))

    def _button(self, parent, text, command):
        button = ttk.Button(parent, text=text, command=command)
        self.buttons.append(button)
        return button

    def _choose(self):
        folder = filedialog.askdirectory(title=t("Sammlung auswählen"))
        if folder:
            self.folder.set(os.path.normpath(folder))

    def _open_reports(self):
        os.makedirs(cli.REPORT_DIR, exist_ok=True)
        system.open_path(cli.REPORT_DIR)

    def _open_rules(self):
        system.open_path(genres.ensure_rules_file(cli.APP_DIR))

    def _language_changed(self, event=None):
        self._save()
        messagebox.showinfo("Music Renamer", t("Die Sprache gilt nach dem nächsten Start."))

    def _print(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _show_progress(self, done, total, text, left):
        self.progress["value"] = done * 100 / total if total else 0
        status = f"{text}: {t('{done} von {total}', done=done, total=total)}"
        if left is not None and left >= 1:
            status += f", {t('Restzeit etwa {time}', time=format_duration(left))}"
        self.progress_text.set(status)

    def _set_busy(self, busy):
        for button in self.buttons:
            button.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if not busy:
            self.progress["value"] = 0
            self.progress_text.set("")

    def _drain_events(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._print(value)
            elif kind == "busy":
                self._set_busy(value)
            elif kind == "progress":
                self._show_progress(*value)
            elif kind == "review":
                self._open_review(*value)
            elif kind == "offer_update":
                self._offer_update(value)
            elif kind == "editor":
                TagEditor(self, value)
            elif kind == "quit":
                self.destroy()
                return
        self.after(100, self._drain_events)

    def _run_background(self, work, *args, **kwargs):
        def runner():
            job.reset()
            self.events.put(("busy", True))
            with contextlib.redirect_stdout(QueueWriter(self.events)):
                try:
                    work(*args, **kwargs)
                except Cancelled:
                    print(t("Abgebrochen. Bereits Erledigtes bleibt erhalten und lässt sich im Verlauf zurücknehmen."))
                except SystemExit as exc:
                    if exc.code:
                        print(exc.code)
                except Exception as exc:
                    print(t("Fehler: {reason}", reason=exc))
            self.events.put(("busy", False))
        threading.Thread(target=runner, daemon=True).start()

    def _ask_review(self, title, columns, editable, rows):
        """Läuft im Hintergrund-Thread und wartet, bis die Prüfansicht geschlossen ist."""
        answer, closed = {}, threading.Event()

        def finished(chosen):
            answer["rows"] = chosen
            closed.set()
        self.events.put(("review", (title, columns, editable, rows, finished)))
        closed.wait()
        return answer["rows"]

    def _open_review(self, title, columns, editable, rows, finished):
        ReviewWindow(self, title, columns, editable, rows, finished, duplicates="Behalten" in columns)

    def _save(self):
        settings = {"ordner": self.folder.get().strip(), "acoustid_key": self.acoustid_key.get().strip(),
                    "discogs_token": self.discogs_token.get().strip(),
                    "genauigkeit": LEVEL_LABELS[self.accuracy.get()],
                    "eigene_genauigkeit": self.custom_accuracy.get().strip(),
                    "cover": self.cover.get(), "songtexte": self.lyrics.get(), "genres": self.unify_genres.get(),
                    "muster": self.pattern.get().strip(), "sprache": i18n.LANGUAGES[self.language.get()]}
        save_settings(settings)
        return settings

    def _start(self, command, apply, **options):
        folder = self.folder.get().strip()
        if not folder:
            messagebox.showinfo("Music Renamer", t("Bitte zuerst die Sammlung auswählen."))
            return
        settings = self._save()
        os.environ["ACOUSTID_KEY"] = settings["acoustid_key"]
        os.environ["DISCOGS_TOKEN"] = settings["discogs_token"]
        self._run_background(command, Namespace(ordner=folder, apply=apply, review=self._ask_review, **options))

    def _dupes(self, apply):
        self._start(cli.cmd_dupes, apply, ziel=None, aehnlich=self.similar.get(), klang=self.sound.get())

    def _tags(self, apply):
        accuracy = self.custom_accuracy.get().strip() or LEVEL_LABELS[self.accuracy.get()]
        try:
            parse_accuracy(accuracy)
        except ValueError:
            messagebox.showerror("Music Renamer", t("Bitte als eigenen Wert eine Zahl von 1 bis 100 eintragen."))
            return
        self._start(cli.cmd_tag, apply, ueberschreiben=self.overwrite.get(), limit=None, genauigkeit=accuracy,
                    cover=self.cover.get(), songtexte=self.lyrics.get(), genres=self.unify_genres.get())

    def _open_editor(self):
        folder = self.folder.get().strip()
        if not folder:
            messagebox.showinfo("Music Renamer", t("Bitte zuerst die Sammlung auswählen."))
            return
        self._run_background(self._load_editor, folder)

    def _load_editor(self, folder):
        self.events.put(("editor", cli.prepare(Namespace(ordner=folder))[2]))

    def _update_level_box(self, *unused):
        # Ein eigener Wert hat Vorrang, die Stufe gilt dann nicht
        self.level_box.configure(state="disabled" if self.custom_accuracy.get().strip() else "readonly")

    def _rename(self, apply):
        self._start(cli.cmd_rename, apply, muster=self.pattern.get().strip())

    def _check_update(self, quiet):
        try:
            release = updater.check_latest()
        except Exception as exc:
            if not quiet:
                print(t("Update-Prüfung fehlgeschlagen: {reason}", reason=exc))
            return
        if release:
            self.events.put(("offer_update", release))
        elif not quiet:
            print(t("Version {version} ist aktuell.", version=__version__))

    def _offer_update(self, release):
        if not updater.can_self_update():
            self._print(t("Neue Version {version}: {page}", version=release.version, page=release.page))
            return
        versions = {"new": release.version, "old": __version__}
        if system.MACOS:
            question = t("Version {new} ist verfügbar (installiert: {old}).\nJetzt herunterladen?\n\nDas Programm schließt sich. Ziehe die neue Version danach in den Programme-Ordner.",
                         **versions)
        else:
            question = t("Version {new} ist verfügbar (installiert: {old}).\nJetzt herunterladen und installieren?",
                         **versions)
        if messagebox.askyesno(t("Update verfügbar"), question):
            self._run_background(self._install_update, release)

    def _install_update(self, release):
        print(t("Lade Version {version} ...", version=release.version))
        path = updater.download(release)
        print(t("Installation startet, das Programm schließt sich."))
        updater.start_installer(path)
        self.events.put(("quit", None))


def main():
    App().mainloop()
