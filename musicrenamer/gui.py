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
from tkinter import filedialog, font, messagebox, ttk
from types import SimpleNamespace

from tkinterdnd2 import DND_FILES, TkinterDnD

from . import __version__, cli, genres, i18n, journal, system, updater
from .editor import TagEditor
from .i18n import progress_line, t
from .job import Cancelled, job
from .lookup import LEVELS, parse_accuracy
from .review import ReviewWindow

SETTINGS_PATH = os.path.join(cli.APP_DIR, "einstellungen.json")
ACOUSTID_KEY_URL = "https://acoustid.org/new-application"
STEPS = ("dubletten", "tags", "umbenennen")
QUICK = "schnell"
NAME_PATTERNS = ("{artist} - {title}", "{track} - {title}", "{artist} - {album} - {track} - {title}", "{title}")
STEP_NAMES = {"dubletten": "Dubletten aussortieren", "tags": "Metadaten ergänzen",
              "umbenennen": "Umbenennen und sortieren"}


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
        self.geometry("980x700")
        self.minsize(920, 640)
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
        # Bis 0.15 gab es nur ein Muster; Ordner darin werden zu den neuen Häkchen
        old = settings.get("muster", cli.PATTERNS[0]).split("/")
        self.file_name = tk.StringVar(value=settings.get("dateiname", old[-1]))
        self.by_period = tk.BooleanVar(value=settings.get("ordner_zeitraum", "{zeitraum}" in old[:-1]))
        self.by_genre = tk.BooleanVar(value=settings.get("ordner_genre", "{genre}" in old[:-1]))
        self.by_album = tk.BooleanVar(value=settings.get("ordner_album", any("{album}" in p for p in old[:-1])))
        self.target_folder = tk.StringVar(value=settings.get("zielordner", ""))
        self.period_years = tk.StringVar(value=str(settings.get("zeitraum_jahre", cli.PERIOD_YEARS)))
        self.language = tk.StringVar(value=next(k for k, v in i18n.LANGUAGES.items() if v == i18n.language))
        self.progress_text = tk.StringVar()
        self.status = settings.get("status", {})
        self.running_step = None
        self.review_cancelled = False
        self._build()
        self.folder.trace_add("write", self._refresh_nav)
        self._enable_drop()
        job.listener = lambda *values: self.events.put(("progress", values))
        self.drain_id = self.after(100, self._drain_events)
        if auto_update_check:
            self._run_background(self._check_update, quiet=True)

    def _build(self):
        style = ttk.Style(self)
        style.configure("Nav.Toolbutton", anchor="w", padding=(10, 8))
        style.configure("Info.TLabel", foreground="#4a4a4a")
        base = font.nametofont("TkDefaultFont")
        self.title_font = base.copy()
        self.title_font.configure(size=round(base.actual("size") * 1.35), weight="bold")

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        top = ttk.Frame(main)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text=t("Sammlung:")).pack(side="left")
        ttk.Entry(top, textvariable=self.folder).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text=t("Auswählen ..."), command=self._choose).pack(side="left")
        ttk.Separator(main).grid(row=1, column=0, sticky="ew", pady=10)

        body = ttk.Frame(main)
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(2, weight=1)
        nav = ttk.Frame(body)
        nav.grid(row=0, column=0, sticky="ns")
        ttk.Separator(body, orient="vertical").grid(row=0, column=1, sticky="ns", padx=(10, 0))
        self.content = ttk.Frame(body)
        self.content.grid(row=0, column=2, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.page = tk.StringVar(value=STEPS[0])
        self.nav_texts = {key: tk.StringVar() for key in (*STEPS, QUICK)}
        for key in (*STEPS, QUICK):
            if key == QUICK:
                ttk.Separator(nav).pack(fill="x", pady=8)
            ttk.Radiobutton(nav, textvariable=self.nav_texts[key], variable=self.page, value=key,
                            style="Nav.Toolbutton", width=30, command=self._show_page).pack(fill="x", pady=1)
        self.pages = {}
        self._build_dupes()
        self._build_tags()
        self._build_rename()
        self._build_quick()
        self._refresh_nav()
        self._show_page()

        log = ttk.Frame(main)
        log.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        log.columnconfigure(0, weight=1)
        log.rowconfigure(1, weight=1)
        ttk.Label(log, text=t("Protokoll")).grid(row=0, column=0, sticky="w")
        self.log = tk.Text(log, height=5, state="disabled", wrap="word")
        self.log.grid(row=1, column=0, sticky="nsew", pady=(2, 0))

        progress = ttk.Frame(main)
        progress.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.progress = ttk.Progressbar(progress, maximum=100)
        self.progress.pack(side="left", fill="x", expand=True)
        self.cancel_button = ttk.Button(progress, text=t("Abbrechen"), command=job.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(6, 0))
        ttk.Label(main, textvariable=self.progress_text).grid(row=5, column=0, sticky="w", pady=(2, 6))

        bottom = ttk.Frame(main)
        bottom.grid(row=6, column=0, sticky="ew")
        self._button(bottom, t("Verlauf"), lambda: HistoryWindow(self)).pack(side="left")
        ttk.Button(bottom, text=t("Berichte öffnen"), command=self._open_reports).pack(side="left", padx=6)
        self._button(bottom, t("Tag-Editor"), self._open_editor).pack(side="left")
        ttk.Button(bottom, text=t("Genre-Regeln"), command=self._open_rules).pack(side="left", padx=6)
        ttk.Button(bottom, text=t("Hilfe"), command=lambda: webbrowser.open(cli.DOCS_URL + "Bedienung.md")).pack(
            side="left", padx=(0, 6))
        self._button(bottom, t("Nach Updates suchen"),
                     lambda: self._run_background(self._check_update, quiet=False)).pack(side="left")
        language = ttk.Combobox(bottom, textvariable=self.language, values=list(i18n.LANGUAGES),
                                state="readonly", width=8)
        language.pack(side="right")
        language.bind("<<ComboboxSelected>>", self._language_changed)
        ttk.Label(bottom, text=t("Sprache:")).pack(side="right", padx=(0, 4))

    def _page(self, key, title, info):
        """Eine Seite pro Schritt: Überschrift, ein Satz, was er tut, darunter nur seine Optionen."""
        page = ttk.Frame(self.content, padding=(16, 0, 0, 0))
        page.grid(row=0, column=0, sticky="nsew")
        ttk.Label(page, text=title, font=self.title_font).pack(anchor="w")
        text = ttk.Label(page, text=info, style="Info.TLabel", justify="left", wraplength=560)
        text.pack(anchor="w", fill="x", pady=(4, 10))
        text.bind("<Configure>", lambda event: event.widget.configure(wraplength=max(event.width - 12, 200)))
        self.pages[key] = page
        return page

    def _actions(self, page, action, next_step=None):
        row = ttk.Frame(page)
        row.pack(fill="x", pady=(14, 0))
        self._button(row, t("1. Vorschau ansehen"), lambda: action(False)).pack(side="left")
        self._button(row, t("2. Prüfen und ausführen"), lambda: action(True)).pack(side="left", padx=(6, 0))
        if next_step:
            ttk.Button(row, text=t("Weiter zu Schritt {number} →", number=STEPS.index(next_step) + 1),
                       command=lambda: self._go(next_step)).pack(side="right")

    def _build_dupes(self):
        page = self._page("dubletten", t("Schritt 1: Dubletten aussortieren"),
                          t("Findet doppelte Dateien und verschiebt sie in den Ordner „Dubletten“ in deiner Sammlung. Behalten wird jeweils die beste Datei. Gelöscht wird nichts, alles lässt sich im Verlauf zurücknehmen."))
        ttk.Checkbutton(page, text=t("Am Klang vergleichen (findet auch andere Bitraten und Formate, langsamer)"),
                        variable=self.sound).pack(anchor="w", pady=2)
        ttk.Checkbutton(page, text=t("Auch ähnliche Dubletten (gleicher Titel, andere Datei)"),
                        variable=self.similar).pack(anchor="w", pady=2)
        self._actions(page, self._dupes, "tags")

    def _build_tags(self):
        page = self._page("tags", t("Schritt 2: Metadaten ergänzen"),
                          t("Sucht online Interpret, Album, Jahr, Genre und Tracknummer und schreibt sie in die Dateien, auf Wunsch auch Cover und Songtexte. Bei großen Sammlungen dauert das Tage. Du kannst jederzeit abbrechen oder das Programm schließen, beim nächsten Start geht es dort weiter."))
        for text, variable in ((t("Fehlende Cover einbetten"), self.cover),
                               (t("Fehlende Songtexte einbetten"), self.lyrics),
                               (t("Genres vereinheitlichen (zum Beispiel Rap zu Hip-Hop)"), self.unify_genres),
                               (t("Vorhandene Tags ersetzen statt nur leere Felder füllen"), self.overwrite)):
            ttk.Checkbutton(page, text=text, variable=variable).pack(anchor="w", pady=2)

        toggle = ttk.Button(page, style="Toolbutton")
        toggle.pack(anchor="w", pady=(8, 0))
        advanced = ttk.Frame(page, padding=(18, 4, 0, 0))
        accuracy = ttk.Frame(advanced)
        accuracy.pack(anchor="w")
        ttk.Label(accuracy, text=t("Genauigkeit Klangerkennung:")).pack(side="left", padx=(0, 4))
        self.level_box = ttk.Combobox(accuracy, textvariable=self.accuracy, values=list(LEVEL_LABELS),
                                      state="readonly", width=14)
        self.level_box.pack(side="left")
        ttk.Label(accuracy, text=t("oder eigener Wert:")).pack(side="left", padx=(12, 4))
        ttk.Entry(accuracy, textvariable=self.custom_accuracy, width=6).pack(side="left")
        ttk.Label(accuracy, text="%").pack(side="left", padx=(2, 0))
        self.custom_accuracy.trace_add("write", self._update_level_box)
        self._update_level_box()
        key_row = ttk.Frame(advanced)
        key_row.pack(anchor="w", pady=(6, 0))
        ttk.Label(key_row, text=t("AcoustID-Key:")).pack(side="left", padx=(0, 4))
        ttk.Entry(key_row, textvariable=self.acoustid_key, width=18, show="*").pack(side="left")
        link = tk.Label(key_row, text=t("Key holen"), fg="#0a58ca", cursor="hand2",
                        font=("Segoe UI", 9, "underline"))
        link.pack(side="left", padx=(6, 0))
        link.bind("<Button-1>", lambda event: webbrowser.open(ACOUSTID_KEY_URL))
        ttk.Label(key_row, text=t("Discogs-Token:")).pack(side="left", padx=(14, 4))
        ttk.Entry(key_row, textvariable=self.discogs_token, width=18, show="*").pack(side="left")

        label = t("Erweitert: Klangerkennung und Discogs")

        def switch(show):
            toggle.configure(text=("▾ " if show else "▸ ") + label)
            if show:
                advanced.pack(anchor="w", fill="x", after=toggle)
            else:
                advanced.pack_forget()
        toggle.configure(command=lambda: switch(not advanced.winfo_ismapped()))
        # Wer schon einen Key eingetragen hat, sieht ihn gleich
        switch(bool(self.acoustid_key.get() or self.discogs_token.get()))
        self._actions(page, self._tags, "umbenennen")

    def _build_rename(self):
        page = self._page("umbenennen", t("Schritt 3: Umbenennen und in Ordner sortieren"),
                          t("Benennt die Dateien nach ihren Metadaten aus Schritt 2 und sortiert sie in Ordner. Mit einem Zielordner wandern sie dorthin, Dateien ohne Interpret oder Titel bleiben in der Sammlung."))
        form = ttk.Frame(page)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text=t("Zielordner:")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=self.target_folder).grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Button(form, text=t("Auswählen ..."), command=self._choose_target).grid(row=0, column=2, padx=(6, 0))
        ttk.Label(form, text=t("Leer lassen, wenn alles in der Sammlung bleiben soll."), style="Info.TLabel").grid(
            row=1, column=1, columnspan=2, sticky="w")
        ttk.Label(form, text=t("Ordner:")).grid(row=2, column=0, sticky="nw", padx=(0, 8), pady=(8, 3))
        folders = ttk.Frame(form)
        folders.grid(row=2, column=1, columnspan=2, sticky="w", pady=(8, 3))
        period = ttk.Frame(folders)
        period.pack(anchor="w")
        ttk.Checkbutton(period, text=t("Nach Zeitraum, zum Beispiel 1980 - 1984, mit"),
                        variable=self.by_period).pack(side="left")
        ttk.Spinbox(period, textvariable=self.period_years, from_=1, to=100, width=4).pack(side="left", padx=4)
        ttk.Label(period, text=t("Jahren je Ordner")).pack(side="left")
        ttk.Checkbutton(folders, text=t("Darin nach Genre"), variable=self.by_genre).pack(anchor="w", pady=2)
        ttk.Checkbutton(folders, text=t("Darin nach Interpret und Album"), variable=self.by_album).pack(anchor="w")
        ttk.Label(folders, text=t("Ohne Häkchen landen alle Dateien direkt im Zielordner."), style="Info.TLabel").pack(
            anchor="w", pady=(2, 0))
        ttk.Label(form, text=t("Dateiname:")).grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(8, 3))
        ttk.Combobox(form, textvariable=self.file_name, values=NAME_PATTERNS).grid(
            row=3, column=1, columnspan=2, sticky="ew", pady=(8, 3))
        self.example = tk.StringVar()
        ttk.Label(form, textvariable=self.example, style="Info.TLabel").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))
        for variable in (self.file_name, self.by_period, self.by_genre, self.by_album, self.period_years,
                         self.target_folder, self.folder):
            variable.trace_add("write", self._update_example)
        self._update_example()
        self._actions(page, self._rename)

    def _build_quick(self):
        page = self._page(QUICK, t("Einzelne Dateien schnell umbenennen"),
                          t("Zieh Audiodateien oder Ordner hierher. Sie werden nach dem Muster aus Schritt 3 umbenannt und bleiben in ihrem Ordner. Eine Sammlung brauchst du dafür nicht, und vor dem Umbenennen siehst du die neuen Namen."))
        self.drop_zone = ttk.Label(page, text=t("Dateien hier ablegen"), anchor="center", relief="groove",
                                   padding=50)
        self.drop_zone.pack(fill="x", pady=(6, 0))

    def _pattern(self):
        """Das Muster aus den Häkchen und dem Dateinamen, wie es cli.target_name versteht."""
        folders = ["{zeitraum}"] * self.by_period.get() + ["{genre}"] * self.by_genre.get()
        if self.by_album.get():
            folders += ["{albumartist}", "{album}"]
        return "/".join([*folders, self.file_name.get().strip() or NAME_PATTERNS[0]])

    def _update_example(self, *unused):
        """Zeigt am Beispiel, wohin eine Datei mit dem aktuellen Muster käme."""
        sample = SimpleNamespace(artist="Prince", title="Kiss", album="Parade", albumartist="", year="1986",
                                 genre="Funk", track="4", disc="", label="", path="kiss.mp3")
        try:
            name = cli.target_name(sample, self._pattern(), self._period_years(quiet=True) or 5)
        except (KeyError, ValueError, IndexError):
            name = None
        if not name:
            self.example.set(t("Das Muster ist ungültig oder ergibt keinen Namen."))
            return
        base = self.target_folder.get().strip() or self.folder.get().strip() or t("Sammlung")
        if "/" not in self._pattern() and not self.target_folder.get().strip():
            base = os.path.join(base, "…")
        self.example.set(t("Beispiel: {path}", path=os.path.join(base, name)))

    def _go(self, key):
        self.page.set(key)
        self._show_page()

    def _show_page(self):
        self.pages[self.page.get()].tkraise()

    def _status_key(self):
        folder = self.folder.get().strip()
        return system.fold(os.path.abspath(folder)) if folder else ""

    def _refresh_nav(self, *unused):
        done = self.status.get(self._status_key(), {})
        for number, key in enumerate(STEPS, 1):
            when = done.get(key)
            state = t("Ausgeführt am {date}", date=when) if when else t("Noch nicht ausgeführt")
            self.nav_texts[key].set(f"{number}. {t(STEP_NAMES[key])}\n     {state}")
        self.nav_texts[QUICK].set(f"{t('Schnell umbenennen')}\n     {t('Ohne Sammlung')}")

    def _mark_done(self, step, folder):
        key = system.fold(os.path.abspath(folder))
        self.status.setdefault(key, {})[step] = datetime.datetime.now().strftime("%d.%m.%Y")
        self._save()
        self._refresh_nav()

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
        years = self._period_years()
        if years is None:
            return event.action
        settings = self._save()
        self._run_background(cli.cmd_rename_files, Namespace(dateien=paths, muster=settings["muster"], zeitraum=years, apply=True,
                                                             review=self._ask_review))
        return event.action

    def _button(self, parent, text, command):
        button = ttk.Button(parent, text=text, command=command)
        self.buttons.append(button)
        return button

    def _choose(self):
        folder = filedialog.askdirectory(title=t("Sammlung auswählen"))
        if folder:
            self.folder.set(os.path.normpath(folder))

    def _choose_target(self):
        folder = filedialog.askdirectory(title=t("Zielordner auswählen"))
        if folder:
            self.target_folder.set(os.path.normpath(folder))

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
        self.progress_text.set(progress_line(done, total, text, left))
        if self.running_step:
            number = STEPS.index(self.running_step) + 1
            self.nav_texts[self.running_step].set(
                f"{number}. {t(STEP_NAMES[self.running_step])}\n     {t('Läuft: {percent} %', percent=round(self.progress['value']))}")

    def _set_busy(self, busy):
        for button in self.buttons:
            button.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if not busy:
            self.progress["value"] = 0
            self.progress_text.set("")
            self.running_step = None
            self._refresh_nav()

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
            elif kind == "done":
                value()
            elif kind == "editor":
                TagEditor(self, value)
            elif kind == "quit":
                self.destroy()
                return
        self.drain_id = self.after(100, self._drain_events)

    def destroy(self):
        self.after_cancel(self.drain_id)
        super().destroy()

    def _run_background(self, work, *args, on_success=None, **kwargs):
        def runner():
            job.reset()
            self.events.put(("busy", True))
            with contextlib.redirect_stdout(QueueWriter(self.events)):
                try:
                    work(*args, **kwargs)
                    if on_success and not self.review_cancelled:
                        self.events.put(("done", on_success))
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
        self.review_cancelled = answer["rows"] is None
        return answer["rows"]

    def _open_review(self, title, columns, editable, rows, finished):
        ReviewWindow(self, title, columns, editable, rows, finished, duplicates="Behalten" in columns)

    def _save(self):
        settings = {"ordner": self.folder.get().strip(), "acoustid_key": self.acoustid_key.get().strip(),
                    "discogs_token": self.discogs_token.get().strip(),
                    "genauigkeit": LEVEL_LABELS[self.accuracy.get()],
                    "eigene_genauigkeit": self.custom_accuracy.get().strip(),
                    "cover": self.cover.get(), "songtexte": self.lyrics.get(), "genres": self.unify_genres.get(),
                    "muster": self._pattern(), "dateiname": self.file_name.get().strip(),
                    "ordner_zeitraum": self.by_period.get(), "ordner_genre": self.by_genre.get(),
                    "ordner_album": self.by_album.get(), "zielordner": self.target_folder.get().strip(),
                    "zeitraum_jahre": self._period_years(quiet=True) or cli.PERIOD_YEARS,
                    "sprache": i18n.LANGUAGES[self.language.get()], "status": self.status}
        save_settings(settings)
        return settings

    def _start(self, step, command, apply, then=None, **options):
        folder = self.folder.get().strip()
        if not folder:
            messagebox.showinfo("Music Renamer", t("Bitte zuerst oben die Sammlung auswählen."))
            return
        settings = self._save()
        os.environ["ACOUSTID_KEY"] = settings["acoustid_key"]
        os.environ["DISCOGS_TOKEN"] = settings["discogs_token"]
        # Nur ein ausgeführter Schritt zählt als erledigt, eine Vorschau nicht
        self.running_step, self.review_cancelled = step, False
        self._run_background(command, Namespace(ordner=folder, apply=apply, review=self._ask_review, **options),
                             on_success=(lambda: self._finished(step, folder, then)) if apply else None)

    def _finished(self, step, folder, then):
        self._mark_done(step, folder)
        if then:
            then()

    def _dupes(self, apply):
        self._start("dubletten", cli.cmd_dupes, apply, ziel=None, aehnlich=self.similar.get(), klang=self.sound.get())

    def _tags(self, apply):
        accuracy = self.custom_accuracy.get().strip() or LEVEL_LABELS[self.accuracy.get()]
        try:
            parse_accuracy(accuracy)
        except ValueError:
            messagebox.showerror("Music Renamer", t("Bitte als eigenen Wert eine Zahl von 1 bis 100 eintragen."))
            return
        self._start("tags", cli.cmd_tag, apply, ueberschreiben=self.overwrite.get(), limit=None, genauigkeit=accuracy,
                    cover=self.cover.get(), songtexte=self.lyrics.get(), genres=self.unify_genres.get())

    def _open_editor(self):
        folder = self.folder.get().strip()
        if not folder:
            messagebox.showinfo("Music Renamer", t("Bitte zuerst oben die Sammlung auswählen."))
            return
        self._run_background(self._load_editor, folder)

    def _load_editor(self, folder):
        self.events.put(("editor", cli.prepare(Namespace(ordner=folder))[2]))

    def _update_level_box(self, *unused):
        # Ein eigener Wert hat Vorrang, die Stufe gilt dann nicht
        self.level_box.configure(state="disabled" if self.custom_accuracy.get().strip() else "readonly")

    def _period_years(self, quiet=False):
        try:
            years = int(self.period_years.get().strip())
        except ValueError:
            years = 0
        if 1 <= years <= 100:
            return years
        if not quiet:
            messagebox.showerror("Music Renamer", t("Jahre je Zeitraum müssen zwischen 1 und 100 liegen."))
        return None

    def _rename(self, apply):
        years = self._period_years()
        if years is None:
            return
        folder = self.folder.get().strip()
        tagged = self.status.get(self._status_key(), {}).get("tags")
        if apply and folder and not tagged and not messagebox.askyesno(
                "Music Renamer", t("Schritt 2 wurde für diese Sammlung noch nicht ausgeführt. Ohne ihn fehlen Jahr, Genre und Cover, und Dateien ohne Jahr landen in „Unbekanntes Jahr“.\n\nTrotzdem umbenennen?")):
            self._go("tags")
            return
        target = self.target_folder.get().strip()
        self._start("umbenennen", cli.cmd_rename, apply, muster=self._pattern(), zeitraum=years,
                    zielordner=target or None, then=lambda: self._offer_new_collection(target))

    def _offer_new_collection(self, target):
        """Nach dem Verschieben liegen die Dateien woanders; dort sollen die nächsten Schritte arbeiten."""
        if target and system.fold(os.path.abspath(target)) != self._status_key() and messagebox.askyesno(
                "Music Renamer", t("Die Dateien liegen jetzt in {path}.\n\nDiesen Ordner als Sammlung übernehmen, damit die nächsten Schritte dort arbeiten?", path=target)):
            self.folder.set(target)
            self._save()

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
