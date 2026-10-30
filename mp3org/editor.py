"""Tag-Editor: Dateien suchen, auswählen und Felder von Hand ändern."""
import os
import tkinter as tk
from tkinter import messagebox, ttk

from . import cli, journal
from .i18n import FIELD_LABELS as LABELS
from .i18n import t
from .tags import FIELDS, write_tags

COLUMNS = ("artist", "title", "album", "year", "genre", "track")


class TagEditor(tk.Toplevel):
    def __init__(self, parent, tracks):
        super().__init__(parent)
        self.title(t("Tag-Editor"))
        self.geometry("980x620")
        self.tracks = tracks
        self.filter_text = tk.StringVar()
        self.values = {field: tk.StringVar() for field in FIELDS}
        self.status = tk.StringVar(value=t("Mehrere Dateien auswählen und nur die Felder füllen, die sich ändern sollen."))
        self._build()
        self._refresh()

    def _build(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        search = ttk.Frame(main)
        search.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(search, text=t("Suchen:")).pack(side="left", padx=(0, 4))
        ttk.Entry(search, textvariable=self.filter_text).pack(side="left", fill="x", expand=True)
        self.filter_text.trace_add("write", lambda *unused: self._refresh())

        table = ttk.Frame(main)
        table.grid(row=1, column=0, sticky="nsew")
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=("file", *COLUMNS), show="headings", selectmode="extended")
        self.tree.heading("file", text=t("Datei"))
        self.tree.column("file", width=260)
        for field in COLUMNS:
            self.tree.heading(field, text=t(LABELS[field]))
            self.tree.column(field, width=60 if field in ("year", "track") else 130)
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._selected)

        form = ttk.Frame(main)
        form.grid(row=2, column=0, sticky="ew", pady=8)
        for column in (1, 3):
            form.columnconfigure(column, weight=1)
        for number, field in enumerate(FIELDS):
            row, column = number // 2, (number % 2) * 2
            ttk.Label(form, text=f"{t(LABELS[field])}:").grid(row=row, column=column, sticky="w", padx=(8, 4), pady=2)
            ttk.Entry(form, textvariable=self.values[field]).grid(row=row, column=column + 1, sticky="ew")

        bottom = ttk.Frame(main)
        bottom.grid(row=3, column=0, sticky="ew")
        ttk.Label(bottom, textvariable=self.status).pack(side="left")
        ttk.Button(bottom, text=t("Speichern"), command=self.save).pack(side="right")

    def _refresh(self):
        needle = self.filter_text.get().casefold()
        self.tree.delete(*self.tree.get_children())
        for number, track in enumerate(self.tracks):
            texts = [os.path.basename(track.path), *[getattr(track, f) for f in COLUMNS]]
            if needle in " ".join(map(str, texts)).casefold():
                self.tree.insert("", "end", iid=str(number), values=texts)

    def _selection(self):
        return [self.tracks[int(item)] for item in self.tree.selection()]

    def _selected(self, event=None):
        selection = self._selection()
        for field in FIELDS:
            shown = {getattr(track, field) for track in selection}
            self.values[field].set(shown.pop() if len(shown) == 1 else "")
        self.status.set(t("Dateien ausgewählt: {count}", count=len(selection)))

    def save(self):
        selection = self._selection()
        entered = {f: v.get().strip() for f, v in self.values.items() if v.get().strip()}
        if not selection or not entered:
            self.status.set(t("Bitte Dateien auswählen und mindestens ein Feld füllen."))
            return
        log = journal.Journal(cli.DATA_DIR, "editor")
        saved, failed = 0, []
        for track in selection:
            changes = {f: v for f, v in entered.items() if v != getattr(track, f)}
            if not changes:
                continue
            try:
                log.record(action="tag", path=track.path, old={f: getattr(track, f) for f in changes}, new=changes)
                write_tags(track.path, changes)
            except Exception as exc:
                failed.append(f"{os.path.basename(track.path)}: {exc}")
                continue
            for field, value in changes.items():
                setattr(track, field, value)
            saved += 1
        log.close()
        selected = self.tree.selection()
        self._refresh()
        self.tree.selection_set([item for item in selected if self.tree.exists(item)])
        self.status.set(t("Dateien gespeichert: {count}", count=saved))
        if failed:
            messagebox.showerror(t("Tag-Editor"), "\n".join(failed[:10]))
