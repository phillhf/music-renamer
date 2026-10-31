"""Prüfansicht: Zeilen abwählen und Felder korrigieren, bevor etwas geändert wird."""
import tkinter as tk
from tkinter import ttk

from . import system
from .i18n import FIELD_LABELS, t

MARK = {True: "☑", False: "☐"}


class ReviewWindow(tk.Toplevel):
    def __init__(self, parent, title, columns, editable, rows, on_done, duplicates=False):
        super().__init__(parent)
        self.title(title)
        self.geometry("1000x620")
        self.columns, self.editable, self.rows, self.on_done = columns, editable, rows, on_done
        self.checked = dict.fromkeys(range(len(rows)), True)
        self.filter_text = tk.StringVar()
        self.status = tk.StringVar()
        self.cell = None
        self._build(duplicates)
        self._refresh()
        self.protocol("WM_DELETE_WINDOW", lambda: self._finish(None))

    def _build(self, duplicates):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)
        ttk.Label(main, text=t("Nur ausgewählte Zeilen werden ausgeführt. Doppelklick auf ein Feld ändert es.")).grid(
            row=0, column=0, sticky="w")
        search = ttk.Frame(main)
        search.grid(row=1, column=0, sticky="ew", pady=6)
        ttk.Label(search, text=t("Suchen:")).pack(side="left", padx=(0, 4))
        ttk.Entry(search, textvariable=self.filter_text).pack(side="left", fill="x", expand=True)
        ttk.Button(search, text=t("Alle"), command=lambda: self._check_all(True)).pack(side="left", padx=(6, 0))
        ttk.Button(search, text=t("Keine"), command=lambda: self._check_all(False)).pack(side="left", padx=(6, 0))
        self.filter_text.trace_add("write", lambda *unused: self._refresh())

        table = ttk.Frame(main)
        table.grid(row=2, column=0, sticky="nsew")
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=("check", *self.columns), show="headings", selectmode="extended")
        self.tree.heading("check", text="")
        self.tree.column("check", width=30, stretch=False, anchor="center")
        for column in self.columns:
            self.tree.heading(column, text=t(FIELD_LABELS.get(column, column)))
            self.tree.column(column, width=260 if column in ("Datei", "Alt", "Neu", "Behalten") else 90)
        vertical = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<Double-1>", self._double_click)
        self.tree.bind("<space>", self._toggle_selection)

        bottom = ttk.Frame(main)
        bottom.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        if duplicates:
            ttk.Button(bottom, text=t("Datei abspielen"), command=lambda: self._play("Datei")).pack(side="left")
            ttk.Button(bottom, text=t("Behaltene abspielen"), command=lambda: self._play("Behalten")).pack(
                side="left", padx=6)
            ttk.Button(bottom, text=t("Tauschen"), command=self.swap).pack(side="left")
        ttk.Button(bottom, text=t("Abbrechen"), command=lambda: self._finish(None)).pack(side="right")
        self.run_button = ttk.Button(bottom, command=self._run)
        self.run_button.pack(side="right", padx=6)

    def _texts(self, index):
        return [str(self.rows[index].get(column, "")) for column in self.columns]

    def _refresh(self):
        needle = self.filter_text.get().casefold()
        self.tree.delete(*self.tree.get_children())
        for index in range(len(self.rows)):
            texts = self._texts(index)
            if needle in " ".join(texts).casefold():
                self.tree.insert("", "end", iid=str(index), values=(MARK[self.checked[index]], *texts))
        self._update_count()

    def _update_count(self):
        count = sum(self.checked.values())
        self.run_button.configure(text=t("Ausgewählte ausführen ({count})", count=count),
                                  state="normal" if count else "disabled")

    def _show(self, index):
        if self.tree.exists(str(index)):
            self.tree.item(str(index), values=(MARK[self.checked[index]], *self._texts(index)))

    def _check_all(self, value):
        # Mit Suchtext wirkt das nur auf die sichtbaren Zeilen
        for item in self.tree.get_children():
            self.checked[int(item)] = value
            self._show(int(item))
        self._update_count()

    def _click(self, event):
        if self.tree.identify_column(event.x) == "#1" and self.tree.identify_region(event.x, event.y) == "cell":
            index = int(self.tree.identify_row(event.y))
            self.checked[index] = not self.checked[index]
            self._show(index)
            self._update_count()
            return "break"

    def _toggle_selection(self, event=None):
        for item in self.tree.selection():
            self.checked[int(item)] = not self.checked[int(item)]
            self._show(int(item))
        self._update_count()
        return "break"

    def _double_click(self, event):
        item, column = self.tree.identify_row(event.y), self.tree.identify_column(event.x)
        number = int(column[1:]) - 2
        if not item or number < 0 or self.columns[number] not in self.editable:
            return
        self._edit(item, self.columns[number], column)

    def _edit(self, item, name, column):
        x, y, width, height = self.tree.bbox(item, column)
        value = tk.StringVar(value=self.rows[int(item)].get(name, ""))
        entry = ttk.Entry(self.tree, textvariable=value)
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        entry.select_range(0, "end")

        def commit(event=None):
            self.rows[int(item)][name] = value.get().strip()
            self._show(int(item))
            entry.destroy()
        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)
        entry.bind("<Escape>", lambda event: entry.destroy())
        self.cell = entry

    def _chosen(self):
        return [self.rows[int(item)] for item in self.tree.selection()]

    def _play(self, column):
        for row in self._chosen()[:1]:
            system.open_path(row[column])

    def swap(self):
        """Behält statt der vorgeschlagenen Datei die ausgewählte."""
        for row in self._chosen():
            old_keep, new_keep = row["Behalten"], row["Datei"]
            for other in self.rows:
                if other["group"] == row["group"]:
                    other["Behalten"] = new_keep
            row["Datei"] = old_keep
        self._refresh()

    def _run(self):
        self._finish([row for index, row in enumerate(self.rows) if self.checked[index]])

    def _finish(self, rows):
        self.destroy()
        self.on_done(rows)
