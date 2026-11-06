"""Menüführung: Schritte, Seiten und gespeicherter Status. Braucht eine Anzeige, unter Linux xvfb."""
import os
import sys
import time
import tkinter as tk
from tkinter import ttk
import unittest
from argparse import Namespace
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from musicrenamer import cli, gui


def has_display():
    # Kein Probefenster: Tk 9 stürzt auf dem Mac ab, wenn im selben Prozess ein zweites Tk entsteht
    return bool(os.environ.get("DISPLAY")) or not sys.platform.startswith("linux")


@unittest.skipUnless(has_display(), "braucht eine Anzeige")
class Navigation(unittest.TestCase):
    """Alle Tests teilen ein Fenster, aus demselben Grund."""

    @classmethod
    def setUpClass(cls):
        cls.saved = {}
        cls.patchers = [mock.patch.object(gui, "load_settings", return_value={"ordner": "C:/Musik"}),
                        mock.patch.object(gui, "save_settings", side_effect=cls.saved.update)]
        for patcher in cls.patchers:
            patcher.start()
        cls.app = gui.App(auto_update_check=False)

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()
        for patcher in cls.patchers:
            patcher.stop()

    def setUp(self):
        self.saved.clear()
        self.app.status.clear()
        self.app.folder.set("C:/Musik")
        self.app.target_folder.set("")
        self.set_levels()
        self.app.file_name.set(gui.NAME_PATTERNS[0])
        self.app._go("dubletten")
        self.app.update()

    def set_levels(self, *labels):
        for variable, label in zip(self.app.levels, [*labels, *[gui.NO_FOLDER] * gui.FOLDER_DEPTH]):
            variable.set(label)

    def wait(self, condition, seconds=5):
        end = time.time() + seconds
        while time.time() < end and not condition():
            self.app.update()
            time.sleep(0.02)

    def visible_page(self):
        return next(key for key, page in self.app.pages.items()
                    if page.winfo_ismapped() and self.app.content.winfo_children()[-1] is page)

    def test_starts_with_step_one(self):
        self.assertEqual(self.visible_page(), "dubletten")
        self.assertIn("Noch nicht ausgeführt", self.app.nav_texts["dubletten"].get())

    def test_next_button_leads_through_the_steps(self):
        for current, following in (("dubletten", "tags"), ("tags", "umbenennen")):
            self.app._go(current)
            button = next(w for w in self.all_widgets(self.app.pages[current])
                          if isinstance(w, ttk.Button) and str(w.cget("text")).startswith("Weiter zu Schritt"))
            button.invoke()
            self.app.update()
            self.assertEqual(self.visible_page(), following)

    def all_widgets(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self.all_widgets(child)

    def test_finished_run_marks_the_step_for_this_collection(self):
        self.app._start("tags", lambda args: None, True)
        self.wait(lambda: "Ausgeführt am" in self.app.nav_texts["tags"].get())
        self.assertIn("Ausgeführt am", self.app.nav_texts["tags"].get())
        self.assertIn("tags", self.saved["status"][next(iter(self.saved["status"]))])
        self.app.folder.set("C:/Andere")
        self.assertIn("Noch nicht ausgeführt", self.app.nav_texts["tags"].get())

    def test_preview_and_cancelled_review_do_not_count(self):
        self.app._start("dubletten", lambda args: None, False)

        def cancelled_review(args):
            self.app.review_cancelled = True
        self.wait(lambda: str(self.app.cancel_button.cget("state")) == "disabled", 1)
        self.app._start("umbenennen", cancelled_review, True)
        self.wait(lambda: False, 1)
        self.assertIn("Noch nicht ausgeführt", self.app.nav_texts["dubletten"].get())
        self.assertIn("Noch nicht ausgeführt", self.app.nav_texts["umbenennen"].get())

    def test_example_follows_pattern_and_target(self):
        self.app.target_folder.set("D:/Sortiert")
        self.set_levels("Zeitraum", "Genre")
        self.app.period_years.set("5")
        self.assertIn(os.path.join("D:/Sortiert", "1985 - 1989", "Funk", "Prince - Kiss.mp3"), self.app.example.get())
        self.set_levels()
        self.assertIn(os.path.join("D:/Sortiert", "Prince - Kiss.mp3"), self.app.example.get())
        self.set_levels("Interpret", "Album")
        self.app.file_name.set("{track} - {title}")
        self.assertIn(os.path.join("Prince", "Parade", "04 - Kiss.mp3"), self.app.example.get())
        self.app.file_name.set("{kaputt}")
        self.assertIn("ungültig", self.app.example.get())

    def test_folders_are_optional_and_build_the_pattern(self):
        self.assertEqual(self.app._pattern(), "{artist} - {title}")
        self.set_levels("Zeitraum", "Genre")
        self.assertEqual(self.app._pattern(), "{zeitraum}/{genre}/{artist} - {title}")
        # Jede Reihenfolge, Lücken und eigene Namen
        self.set_levels("Genre", gui.NO_FOLDER, "{genre} ({jahrzehnt})", "album")
        self.assertEqual(self.app._pattern(), "{genre}/{genre} ({jahrzehnt})/{album}/{artist} - {title}")
        self.assertIn(os.path.join("Funk", "Funk (1980er)", "Parade", "Prince - Kiss.mp3"), self.app.example.get())
        self.app._save()
        self.assertEqual(self.saved["ordner_ebenen"], ["{genre}", "{genre} ({jahrzehnt})", "{album}"])

    def test_old_checkboxes_become_levels(self):
        old = {"ordner_zeitraum": True, "ordner_genre": False, "ordner_album": True, "muster": "x"}
        self.assertEqual(gui.saved_levels(old), ["{zeitraum}", "{albumartist}", "{album}", ""])
        self.assertEqual(gui.saved_levels({"muster": "{zeitraum}/{genre}/{title}"}), ["{zeitraum}", "{genre}", "", ""])
        self.assertEqual(gui.saved_levels({"ordner_ebenen": ["{label}"]}), ["{label}", "", "", ""])

    def test_warns_when_step_two_is_missing_and_offers_new_collection(self):
        started = []
        with mock.patch.object(self.app, "_start", side_effect=lambda *a, **k: started.append(k)), \
                mock.patch.object(gui.messagebox, "askyesno", return_value=False) as ask:
            self.app._rename(True)
        self.assertEqual((started, self.visible_page()), ([], "tags"))
        self.assertIn("Schritt 2", ask.call_args[0][1])
        self.app.status[self.app._status_key()] = {"tags": "06.11.2026"}
        self.app.target_folder.set("D:/Sortiert")
        self.set_levels("Zeitraum")
        with mock.patch.object(self.app, "_start", side_effect=lambda *a, **k: started.append(k)):
            self.app._rename(True)
        self.assertEqual(started[0]["muster"], "{zeitraum}/{artist} - {title}")
        with mock.patch.object(gui.messagebox, "askyesno", return_value=True):
            started[0]["then"]()
        self.assertEqual(self.app.folder.get(), "D:/Sortiert")

    def test_genre_window_merges_and_writes(self):
        from musicrenamer import genre_window, genres
        tracks = [SimpleNamespace(genre=g, path=f"{n}.mp3") for n, g in enumerate(("Dubstep", "House", "House", "Rock"))]
        written = []
        with mock.patch.object(genres, "load_rules", return_value={"rock": "Dubstep"}),                 mock.patch.object(genres, "save_rules") as save,                 mock.patch.object(genre_window.messagebox, "askyesno", return_value=True):
            window = genre_window.GenreWindow(self.app, tracks, written.extend)
            window.tree.selection_set(["Dubstep", "House"])
            window.target.set("Rock")
            window._merge()  # Rock zeigte auf Dubstep; das würde ein Kreis, also gilt Rock selbst
            self.assertEqual(window.tree.set("House", "target"), "Rock")
            self.assertEqual(window.tree.set("Rock", "target"), "")
            self.assertIn("3 Dateien bekommen ein neues Genre", window.summary.get())
            window.tree.selection_set(["Dubstep"])
            window._unmerge()
            window._write()
        self.assertEqual(save.call_args[0][1], {"house": "Rock"})
        self.assertEqual(sorted((t.path, g) for t, g in written), [("1.mp3", "Rock"), ("2.mp3", "Rock")])

    def test_advanced_options_open_and_close(self):
        toggle = next(w for w in self.all_widgets(self.app.pages["tags"])
                      if isinstance(w, ttk.Button) and "Erweitert" in str(w.cget("text")))
        self.app._go("tags")
        self.app.update()
        opened = self.app.level_box.winfo_ismapped()
        toggle.invoke()
        self.app.update()
        self.assertNotEqual(self.app.level_box.winfo_ismapped(), opened)
        toggle.invoke()
        self.app.update()
        self.assertEqual(self.app.level_box.winfo_ismapped(), opened)

    def test_start_over_clears_status_after_asking(self):
        self.app.status[self.app._status_key()] = {"tags": "06.11.2026"}
        self.app._refresh_nav()
        with mock.patch.object(gui.messagebox, "askyesno", return_value=False), \
                mock.patch.object(self.app, "_run_background") as run:
            self.app._forget()
        self.assertFalse(run.called)
        with mock.patch.object(gui.messagebox, "askyesno", return_value=True), \
                mock.patch.object(self.app, "_run_background") as run:
            self.app._forget()
        self.assertIs(run.call_args[0][0], cli.cmd_forget)
        self.assertIn("Noch nicht ausgeführt", self.app.nav_texts["tags"].get())

    def test_quick_rename_has_its_own_page(self):
        self.assertIs(self.app.drop_zone.master, self.app.pages[gui.QUICK])


if __name__ == "__main__":
    unittest.main()
