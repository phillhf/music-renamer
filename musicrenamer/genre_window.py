"""Genre-Übersicht: welche Genres die Sammlung hat und welche zusammengefasst werden."""
import tkinter as tk
from tkinter import messagebox, ttk

from . import cli, genres, system
from .i18n import t


class GenreWindow(tk.Toplevel):
    def __init__(self, parent, tracks, on_write):
        super().__init__(parent)
        self.title(t("Genres"))
        self.geometry("760x600")
        self.minsize(640, 460)
        self.tracks = tracks
        self.on_write = on_write
        self.counts = cli.genre_counts(tracks)
        self.rules = genres.load_rules(cli.APP_DIR)
        self.target = tk.StringVar()
        self.summary = tk.StringVar()
        self._build()
        self._refresh()

    def _build(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        ttk.Label(main, text=t("Markiere Genres, die zusammengehören, zum Beispiel Dubstep und House, und fasse sie zu einem Genre zusammen. Mit Strg oder Umschalt markierst du mehrere."),
                  wraplength=720, justify="left").grid(row=0, column=0, sticky="w", pady=(0, 8))

        table = ttk.Frame(main)
        table.grid(row=1, column=0, sticky="nsew")
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=("count", "target"), selectmode="extended")
        self.tree.heading("#0", text=t("Genre"))
        self.tree.heading("count", text=t("Dateien"))
        self.tree.heading("target", text=t("wird zu"))
        self.tree.column("#0", width=280)
        self.tree.column("count", width=80, anchor="e")
        self.tree.column("target", width=260)
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        merge = ttk.Frame(main)
        merge.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(merge, text=t("Markierte zusammenfassen zu:")).pack(side="left")
        self.target_box = ttk.Combobox(merge, textvariable=self.target, width=24)
        self.target_box.pack(side="left", padx=6)
        self.target_box.bind("<Return>", lambda event: self._merge())
        ttk.Button(merge, text=t("Zusammenfassen"), command=self._merge).pack(side="left")
        ttk.Button(merge, text=t("Zuordnung entfernen"), command=self._unmerge).pack(side="left", padx=6)

        ttk.Label(main, textvariable=self.summary).grid(row=3, column=0, sticky="w", pady=(8, 0))
        buttons = ttk.Frame(main)
        buttons.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text=t("In Dateien schreiben"), command=self._write).pack(side="left")
        ttk.Button(buttons, text=t("Nur Regeln speichern"), command=self._save_only).pack(side="left", padx=6)
        ttk.Button(buttons, text=t("Regeldatei öffnen"), command=self._open_file).pack(side="left")
        ttk.Button(buttons, text=t("Abbrechen"), command=self.destroy).pack(side="right")

    def _target_of(self, genre):
        return genres.resolve(genre, self.rules) if genre else ""

    def _refresh(self):
        selected = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        for genre, count in sorted(self.counts.items(), key=lambda item: (not item[0], -item[1], item[0].casefold())):
            target = self._target_of(genre)
            # Die iid ist das Genre selbst, "" steht für Dateien ohne Genre
            self.tree.insert("", "end", iid=genre or "\0", text=genre or t("(ohne Genre)"),
                             values=(count, target if target != genre else ""))
        self.tree.selection_set([item for item in selected if self.tree.exists(item)])
        names = {g for g in self.counts if g} | {self._target_of(g) for g in self.counts if g}
        self.target_box.configure(values=sorted(names, key=str.casefold))
        changed = cli.genre_changes(self.tracks, self.rules)
        result = {target for _, target in changed} | {g for g in self.counts if g and self._target_of(g) == g}
        self.summary.set(t("{genres} Genres, nach dem Zusammenfassen {after}. {count} Dateien bekommen ein neues Genre.",
                           genres=len([g for g in self.counts if g]), after=len(result), count=len(changed)))

    def _chosen(self):
        return [item for item in self.tree.selection() if item != "\0"]

    def _merge(self):
        target = self.target.get().strip()
        chosen = self._chosen()
        if not chosen or not target:
            messagebox.showinfo(t("Genres"), t("Bitte Genres markieren und unten den neuen Namen eintragen."), parent=self)
            return
        for genre in chosen:
            if genre.casefold() == target.casefold():
                self.rules.pop(genre.casefold(), None)
            else:
                self.rules[genre.casefold()] = target
        # Zeigte das Ziel bisher auf eines der markierten Genres, entstünde ein Kreis; das Ziel gilt dann selbst
        sources = {genre.casefold() for genre in chosen}
        step, seen = target.casefold(), set()
        while step in self.rules and step not in seen:
            seen.add(step)
            step = self.rules[step].casefold()
            if step in sources:
                self.rules.pop(target.casefold())
                break
        self._refresh()

    def _unmerge(self):
        for genre in self._chosen():
            self.rules.pop(genre.casefold(), None)
        self._refresh()

    def _save_only(self):
        genres.save_rules(cli.APP_DIR, self.rules)
        self.destroy()

    def _write(self):
        changes = cli.genre_changes(self.tracks, self.rules)
        genres.save_rules(cli.APP_DIR, self.rules)
        if changes and not messagebox.askyesno(
                t("Genres"), t("Das Genre in {count} Dateien ändern? Im Verlauf lässt sich das zurücknehmen.",
                               count=len(changes)), parent=self):
            return
        self.destroy()
        if changes:
            self.on_write(changes)

    def _open_file(self):
        genres.save_rules(cli.APP_DIR, self.rules)
        system.open_path(genres.rules_path(cli.APP_DIR))
