"""Tests für Abbrechen, Prüfansicht, Verlauf, Genres, Discogs und Übersetzung."""
import glob
import json
import os
import re
import sys
import unittest
from argparse import Namespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_mp3org import Base, make_mp3

from mp3org import albums, cli, genres, i18n, journal, library, lookup
from mp3org.job import Cancelled, Job, job


class Cancelling(Base):
    def tearDown(self):
        job.reset()

    def test_cancel_stops_and_keeps_finished_work_undoable(self):
        for name in ("a", "b", "c"):
            make_mp3(self.path("Musik", f"{name}.mp3"), 1, tags={"artist": "A", "title": name})
        args = Namespace(ordner=self.root, muster="{artist} - {title}", apply=True)
        real_step = job.step

        def cancel_after_first(done, total, text=""):
            real_step(done, total, text)
            if text == "Dateien umbenennen" and done == 1:
                job.cancel()
        with mock.patch.object(job, "step", cancel_after_first):
            with self.assertRaises(Cancelled):
                cli.cmd_rename(args)
        left = os.listdir(self.path("Musik"))
        self.assertEqual(sum(name.startswith("A - ") for name in left), 1)
        job.reset()
        cli.cmd_undo(None)
        self.assertEqual(sorted(os.listdir(self.path("Musik"))), ["a.mp3", "b.mp3", "c.mp3"])

    def test_scan_can_be_cancelled(self):
        make_mp3(self.path("a.mp3"), 1)
        job.cancel()
        with self.assertRaises(Cancelled):
            library.scan(self.root, self.db)

    def test_progress_reports_remaining_time(self):
        seen = []
        running = Job()
        running.listener = lambda *values: seen.append(values)
        running.step(0, 10, "x")
        running.step(10, 10, "x")
        self.assertEqual(seen[0][:3], (0, 10, "x"))
        self.assertEqual(seen[-1][:3], (10, 10, "x"))
        self.assertEqual(seen[-1][3], 0)


class Reviewing(Base):
    def test_unticked_rows_stay_untouched(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "A", "title": "Eins"})
        make_mp3(self.path("b.mp3"), 2, tags={"artist": "A", "title": "Zwei"})
        hook = lambda title, columns, editable, rows: [r for r in rows if r["Alt"].endswith("b.mp3")]
        cli.cmd_rename(Namespace(ordner=self.root, muster="{artist} - {title}", apply=True, review=hook))
        self.assertEqual(sorted(os.listdir(self.root)), ["A - Zwei.mp3", "a.mp3"])

    def test_edited_name_is_used(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "A", "title": "Eins"})

        def hook(title, columns, editable, rows):
            self.assertEqual(editable, ("Neu",))
            rows[0]["Neu"] = self.path("Mein Name.mp3")
            return rows
        cli.cmd_rename(Namespace(ordner=self.root, muster="{artist} - {title}", apply=True, review=hook))
        self.assertEqual(os.listdir(self.root), ["Mein Name.mp3"])

    def test_closing_the_review_changes_nothing(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "A", "title": "Eins"})
        hook = lambda *values: None
        cli.cmd_rename(Namespace(ordner=self.root, muster="{artist} - {title}", apply=True, review=hook))
        self.assertEqual(os.listdir(self.root), ["a.mp3"])

    def test_preview_never_opens_the_review(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "A", "title": "Eins"})
        hook = mock.Mock()
        cli.cmd_rename(Namespace(ordner=self.root, muster="{artist} - {title}", apply=False, review=hook))
        hook.assert_not_called()

    def test_edited_tag_is_written(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "A", "title": "T"})

        def hook(title, columns, editable, rows):
            rows[0]["album"] = "Handarbeit"
            rows[0]["year"] = ""
            return rows
        found = {"album": "Falsch", "year": "1999", "source": "musicbrainz", "releases": [], "group": ""}
        args = Namespace(ordner=self.root, apply=True, ueberschreiben=False, limit=None,
                         genauigkeit="normal", review=hook)
        with mock.patch.object(lookup.Lookup, "find", lambda *a: dict(found)):
            cli.cmd_tag(args)
        values = library.read_file(self.path("a.mp3"))
        self.assertEqual((values["album"], values["year"]), ("Handarbeit", ""))

    def test_swapped_duplicate_moves_the_other_file(self):
        make_mp3(self.path("gut.mp3"), 1, bitrate=320)
        make_mp3(self.path("gut (1).mp3"), 1, bitrate=320)

        def hook(title, columns, editable, rows):
            row = rows[0]
            row["Datei"], row["Behalten"] = row["Behalten"], row["Datei"]
            return rows
        cli.cmd_dupes(Namespace(ordner=self.root, ziel=None, aehnlich=False, apply=True, review=hook))
        self.assertEqual(os.listdir(self.path("Dubletten")), ["gut.mp3"])
        self.assertTrue(os.path.exists(self.path("gut (1).mp3")))


class History(Base):
    def run_rename(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "A", "title": "Eins"})
        cli.cmd_rename(Namespace(ordner=self.root, muster="{artist} - {title}", apply=True))
        cli.cmd_rename(Namespace(ordner=self.root, muster="{title}", apply=True))

    def test_lists_newest_first(self):
        self.run_rename()
        runs = journal.list_runs(cli.DATA_DIR)
        self.assertEqual([r["kind"] for r in runs], ["umbenennen", "umbenennen"])
        self.assertGreater(runs[0]["time"], runs[1]["time"])
        self.assertEqual(runs[0]["count"], 1)

    def test_undoing_old_step_also_undoes_newer_ones(self):
        self.run_rename()
        self.assertEqual(os.listdir(self.root), ["Eins.mp3"])
        oldest = journal.list_runs(cli.DATA_DIR)[-1]["path"]
        done, problems = journal.undo_until(cli.DATA_DIR, oldest)
        self.assertEqual((done, problems), (2, []))
        self.assertEqual(os.listdir(self.root), ["a.mp3"])
        self.assertEqual(journal.list_runs(cli.DATA_DIR), [])

    def test_undoing_newest_step_keeps_older_one(self):
        self.run_rename()
        newest = journal.list_runs(cli.DATA_DIR)[0]["path"]
        journal.undo_until(cli.DATA_DIR, newest)
        self.assertEqual(os.listdir(self.root), ["A - Eins.mp3"])
        self.assertEqual(len(journal.list_runs(cli.DATA_DIR)), 1)


class Genres(Base):
    def test_variants_become_one_genre(self):
        cases = {"Synth-Pop": "Electronic", "Industrial Metal": "Metal", "Punk Rock": "Punk",
                 "Hip Hop": "Hip-Hop", "Rock": "Rock", "Indie Rock": "Rock", "Unbekanntes": "Unbekanntes"}
        for genre, expected in cases.items():
            self.assertEqual(genres.canonical(genre, {}), expected, genre)

    def test_own_rules_win(self):
        self.assertEqual(genres.canonical("Synth-Pop", {"synth-pop": "Pop"}), "Pop")

    def test_rules_file(self):
        path = genres.ensure_rules_file(self.tmp.name)
        self.assertTrue(os.path.exists(path))
        self.assertEqual(genres.load_rules(self.tmp.name)["krautrock"], "Rock")
        self.assertEqual(genres.load_rules(os.path.join(self.tmp.name, "fehlt")), {})
        with open(path, "w", encoding="utf-8") as f:
            f.write("kaputt")
        self.assertEqual(genres.load_rules(self.tmp.name), {})

    def test_complete_files_get_unified_without_lookup(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "A", "title": "T", "album": "B", "year": "1", "genre": "Synth-Pop"})
        args = Namespace(ordner=self.root, apply=True, ueberschreiben=False, limit=None, genauigkeit="normal", genres=True)
        with mock.patch.object(lookup.Lookup, "find") as find, mock.patch.object(cli, "APP_DIR", self.tmp.name):
            cli.cmd_tag(args)
        find.assert_not_called()
        self.assertEqual(library.read_file(self.path("a.mp3"))["genre"], "Electronic")


class AlbumFolders(Base):
    def test_complete_files_count_for_the_album(self):
        release = lambda number: {"group": "g", "title": "Album", "date": "1990", "track": str(number), "rank": 0}
        make_mp3(self.path("x", "1.mp3"), 1, tags={"artist": "A", "title": "T1", "album": "B", "year": "1", "genre": "G"})
        make_mp3(self.path("x", "2.mp3"), 2, tags={"artist": "A", "title": "T2", "album": "B", "year": "1", "genre": "G"})
        make_mp3(self.path("x", "3.mp3"), 3, tags={"artist": "A", "title": "T3"})

        def find(fake, path, artist, title, duration):
            number = int(os.path.basename(path)[0])
            return {"artist": "A", "title": title, "album": "Einzeln", "year": "2000", "track": "", "group": "g",
                    "source": "musicbrainz", "releases": [release(number)]}
        args = Namespace(ordner=self.root, apply=True, ueberschreiben=False, limit=None, genauigkeit="normal")
        with mock.patch.object(lookup.Lookup, "find", find) as patched:
            cli.cmd_tag(args)
        values = library.read_file(self.path("x", "3.mp3"))
        self.assertEqual((values["album"], values["track"], values["year"]), ("Album", "3", "1990"))
        self.assertEqual(library.read_file(self.path("x", "1.mp3"))["album"], "B")

    def test_folder_with_two_albums(self):
        def match(number, group):
            track = Namespace(path=os.path.join("x", f"{number}.mp3"))
            return track, {"artist": "A", "album": "?", "releases": [
                {"group": group, "title": group, "date": "", "track": str(number), "rank": 0}]}
        matches = [match(i, "Eins") for i in range(5)] + [match(i, "Zwei") for i in range(5, 10)]
        self.assertEqual(albums.align_albums(matches), 10)
        self.assertEqual({f["album"] for _, f in matches}, {"Eins", "Zwei"})

    def test_sampler_in_mixed_folder_gets_various_artists(self):
        def match(number):
            track = Namespace(path=os.path.join("x", f"{number}.mp3"))
            return track, {"artist": f"A{number}", "album": "?", "releases": [
                {"group": "s", "title": "Sampler", "date": "", "track": str(number), "rank": 3}]}
        matches = [match(i) for i in range(5)] + [(Namespace(path=os.path.join("x", f"e{i}.mp3")), {"artist": "B"}) for i in range(5)]
        self.assertEqual(albums.align_albums(matches), 5)
        self.assertEqual(matches[0][1]["albumartist"], "Various Artists")


class AudioKey(Base):
    def test_survives_rename_and_tagging(self):
        make_mp3(self.path("a.mp3"), 1)
        before = library.audio_key(self.path("a.mp3"))
        from mp3org.tags import write_tags
        write_tags(self.path("a.mp3"), {"artist": "Neu"})
        os.rename(self.path("a.mp3"), self.path("b.mp3"))
        self.assertEqual(library.audio_key(self.path("b.mp3")), before)

    def test_different_audio_differs(self):
        make_mp3(self.path("a.mp3"), 1)
        make_mp3(self.path("b.mp3"), 2)
        self.assertNotEqual(library.audio_key(self.path("a.mp3")), library.audio_key(self.path("b.mp3")))

    def test_sound_recognition_is_not_repeated_after_rename(self):
        make_mp3(self.path("a.mp3"), 1)
        recording = {"title": "T", "artist-credit": [{"name": "A", "artist": {"id": ""}}]}
        with mock.patch.dict(os.environ, {"ACOUSTID_KEY": "k"}), \
                mock.patch.object(lookup, "find_fpcalc", return_value="f"), \
                mock.patch.object(lookup, "_itunes", return_value=None), \
                mock.patch.object(lookup, "_search_mb", return_value=None), \
                mock.patch.object(lookup, "_acoustid", return_value=(0.9, recording)) as acoustid:
            lookup.Lookup(self.db).find(self.path("a.mp3"), "", "", 20)
            os.rename(self.path("a.mp3"), self.path("b.mp3"))
            lookup.Lookup(self.db).find(self.path("b.mp3"), "", "", 20)
        self.assertEqual(acoustid.call_count, 1)


class Discogs(Base):
    ANSWER = json.dumps({"results": [{"title": "Fremd - Anderes", "year": "1980"},
                                     {"title": "Band (2) - Album", "year": "1991", "genre": ["Rock"]}]}).encode()

    def find(self, token="t"):
        with mock.patch.dict(os.environ, {"ACOUSTID_KEY": "", "DISCOGS_TOKEN": token}), \
                mock.patch.object(lookup, "_search_mb", return_value=None):
            return lookup.Lookup(self.db).find("a.mp3", "Band", "Song", 100)

    def test_used_when_musicbrainz_finds_nothing(self):
        with mock.patch.object(lookup, "_fetch", return_value=self.ANSWER) as fetch:
            result = self.find()
            self.find()
        self.assertEqual((result["album"], result["year"], result["genre"], result["source"]),
                         ("Album", "1991", "Rock", "discogs"))
        self.assertEqual(fetch.call_count, 1)
        self.assertIn("Discogs token=t", fetch.call_args.kwargs["headers"]["Authorization"])

    def test_without_token_nothing_is_sent(self):
        with mock.patch.object(lookup, "_fetch") as fetch:
            self.assertIsNone(self.find(""))
        fetch.assert_not_called()

    def test_foreign_artist_is_ignored(self):
        answer = json.dumps({"results": [{"title": "Fremd - Album", "year": "1980"}]}).encode()
        with mock.patch.object(lookup, "_fetch", return_value=answer):
            self.assertIsNone(self.find())


class Translation(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, i18n, "language", "de")

    def test_every_text_has_a_translation(self):
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mp3org")
        call = re.compile(r"""\bt\(\s*(['"])(.+?)(?<!\\)\1""", re.S)
        missing = set()
        for path in glob.glob(os.path.join(folder, "*.py")):
            with open(path, encoding="utf-8") as f:
                for match in call.finditer(f.read()):
                    text = match[2].encode().decode("unicode_escape").encode("latin-1", "ignore").decode("utf-8", "ignore") \
                        if "\\n" in match[2] else match[2]
                    if text not in i18n.EN:
                        missing.add(text)
        self.assertEqual(missing, set())

    def test_placeholders_match(self):
        names = re.compile(r"\{(\w+)\}")
        for german, english in i18n.EN.items():
            self.assertEqual(set(names.findall(german)), set(names.findall(english)), german)

    def test_switching_language(self):
        i18n.language = "en"
        self.assertEqual(i18n.t("Verlauf"), "History")
        self.assertEqual(i18n.t("{done} von {total}", done=1, total=2), "1 of 2")
        self.assertEqual(i18n.format_duration(7500), "2 h 5 min")
        i18n.language = "de"
        self.assertEqual(i18n.t("Verlauf"), "Verlauf")
        self.assertEqual(i18n.format_duration(30), "30 Sek.")


if __name__ == "__main__":
    unittest.main()
