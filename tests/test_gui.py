"""Menüführung: Schritte, Seiten und gespeicherter Status. Braucht eine Anzeige, unter Linux xvfb."""
import os
import sys
import time
import tkinter as tk
from tkinter import ttk
import unittest
from argparse import Namespace
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
        self.app.pattern.set(cli.PATTERNS[0])
        self.app._go("dubletten")
        self.app.update()

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
        self.app.pattern.set("{zeitraum}/{genre}/{artist} - {title}")
        self.app.period_years.set("5")
        self.assertIn(os.path.join("1985 - 1989", "Funk", "Prince - Kiss.mp3"), self.app.example.get())
        self.app.pattern.set("{kaputt}")
        self.assertIn("ungültig", self.app.example.get())

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

    def test_quick_rename_has_its_own_page(self):
        self.assertIs(self.app.drop_zone.master, self.app.pages[gui.QUICK])


if __name__ == "__main__":
    unittest.main()
