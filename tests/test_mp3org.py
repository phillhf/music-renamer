import io
import os
import random
import sys
import tempfile
import unittest
import urllib.request
from argparse import Namespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mutagen.id3 import ID3

from mp3org import cli, journal, library, lookup, updater
from mp3org.dupes import find_duplicates
from mp3org.names import parse_filename
from mp3org.tags import write_tags

HEADERS = {128: b"\xff\xfb\x90\x64", 320: b"\xff\xfb\xe0\x64"}
FRAME_SIZES = {128: 417, 320: 1044}


def make_mp3(path, seed, seconds=20, bitrate=128, tags=None):
    """Erzeugt gültige MPEG-Frames; gleicher Seed heißt gleiche Audiodaten."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rng = random.Random(seed)
    frames = int(seconds * 44100 / 1152)
    size = FRAME_SIZES[bitrate]
    with open(path, "wb") as f:
        for _ in range(frames):
            f.write(HEADERS[bitrate] + rng.randbytes(size - 4))
    if tags:
        write_tags(path, tags)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.join(self.tmp.name, "Musik")
        self.db = library.connect(os.path.join(self.tmp.name, "data", "t.sqlite"))
        self.addCleanup(self.db.close)
        connect = mock.patch.object(library, "connect", lambda path: self.db)
        connect.start()
        self.addCleanup(connect.stop)
        for name, value in (("DB_PATH", os.path.join(self.tmp.name, "data", "t.sqlite")),
                            ("DATA_DIR", os.path.join(self.tmp.name, "data")),
                            ("REPORT_DIR", os.path.join(self.tmp.name, "berichte"))):
            original = getattr(cli, name)
            setattr(cli, name, value)
            self.addCleanup(setattr, cli, name, original)

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def tracks(self):
        library.scan(self.root, self.db, progress=lambda m: None)
        return library.load_tracks(self.root, self.db)


class Filenames(unittest.TestCase):
    def test_patterns(self):
        cases = {
            "01 - Queen - Bohemian Rhapsody.mp3": ("Queen", "Bohemian Rhapsody"),
            "Queen_-_Bohemian_Rhapsody.mp3": ("Queen", "Bohemian Rhapsody"),
            "Queen - Bohemian Rhapsody (Official Video).mp3": ("Queen", "Bohemian Rhapsody"),
            "Queen - Bohemian Rhapsody [www.mp3site.com].mp3": ("Queen", "Bohemian Rhapsody"),
            "Queen - Bohemian Rhapsody - Kopie.mp3": ("Queen", "Bohemian Rhapsody"),
            "Queen - Bohemian Rhapsody (1).mp3": ("Queen", "Bohemian Rhapsody"),
        }
        for name, expected in cases.items():
            self.assertEqual(parse_filename(os.path.join("X", "Musik", name)), expected, name)

    def test_folder_as_artist(self):
        path = os.path.join("D:", os.sep, "Musik", "Queen", "03 Bohemian Rhapsody.mp3")
        self.assertEqual(parse_filename(path), ("Queen", "Bohemian Rhapsody"))


class Duplicates(Base):
    def test_exact_ignores_tags_and_name(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "A", "title": "T", "album": "X"})
        make_mp3(self.path("sub", "b - Kopie.mp3"), 1)
        make_mp3(self.path("c.mp3"), 2)
        groups = find_duplicates(self.tracks(), self.db, lambda m: None)
        self.assertEqual([g.kind for g in groups], ["exakt"])
        self.assertTrue(groups[0].keep.path.endswith("a.mp3"))
        self.assertTrue(groups[0].duplicates[0].path.endswith("b - Kopie.mp3"))

    def test_similar_prefers_higher_bitrate(self):
        make_mp3(self.path("low.mp3"), 1, tags={"artist": "A", "title": "Song"})
        make_mp3(self.path("high.mp3"), 2, bitrate=320, tags={"artist": "a", "title": "SONG"})
        group = find_duplicates(self.tracks(), self.db, lambda m: None)[0]
        self.assertEqual(group.kind, "aehnlich")
        self.assertTrue(group.keep.path.endswith("high.mp3"))

    def test_live_version_and_other_length_are_kept_apart(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "A", "title": "Song"})
        make_mp3(self.path("b.mp3"), 2, tags={"artist": "A", "title": "Song (Live)"})
        make_mp3(self.path("c.mp3"), 3, seconds=40, tags={"artist": "A", "title": "Song"})
        self.assertEqual(find_duplicates(self.tracks(), self.db, lambda m: None), [])

    def test_move_and_undo(self):
        make_mp3(self.path("Unter", "a.mp3"), 1)
        make_mp3(self.path("Unter", "a (1).mp3"), 1)
        args = Namespace(ordner=self.root, ziel=None, aehnlich=False, apply=False)
        cli.cmd_dupes(args)
        self.assertTrue(os.path.exists(self.path("Unter", "a (1).mp3")))
        args.apply = True
        cli.cmd_dupes(args)
        self.assertFalse(os.path.exists(self.path("Unter", "a (1).mp3")))
        moved = self.path("Dubletten", "Unter", "a (1).mp3")
        self.assertTrue(os.path.exists(moved))
        cli.cmd_undo(None)
        self.assertTrue(os.path.exists(self.path("Unter", "a (1).mp3")))
        self.assertFalse(os.path.exists(moved))

    def test_moved_files_are_left_alone_by_later_steps(self):
        tags = {"artist": "A", "title": "T"}
        make_mp3(self.path("a.mp3"), 1, tags=tags)
        make_mp3(self.path("b.mp3"), 1, tags=tags)
        arguments = dict(ordner=self.root, apply=True)
        cli.cmd_dupes(Namespace(ziel=None, aehnlich=False, **arguments))
        self.assertEqual(len(os.listdir(self.path("Dubletten"))), 1)

        cli.cmd_rename(Namespace(muster="{artist} - {title}", **arguments))
        self.assertEqual(os.listdir(self.path("Dubletten")), ["b.mp3"])
        self.assertTrue(os.path.exists(self.path("A - T.mp3")))
        self.assertEqual(len(self.tracks_without_dupes()), 1)

        cli.cmd_dupes(Namespace(ziel=None, aehnlich=True, **arguments))
        self.assertEqual(os.listdir(self.path("Dubletten")), ["b.mp3"])

    def test_collection_at_drive_root_gets_valid_folder(self):
        self.assertEqual(cli.dupes_dir(Namespace(ordner="C:\\", ziel=None)), "C:\\Dubletten")

    def tracks_without_dupes(self):
        library.scan(self.root, self.db, self.path("Dubletten"), progress=lambda m: None)
        return library.load_tracks(self.root, self.db)


class Tagging(Base):
    def test_only_empty_fields_are_filled(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "Echt", "genre": "Track 1"})
        track = self.tracks()[0]
        found = {"artist": "Anders", "title": "T", "year": "1999", "genre": "Rock"}
        self.assertEqual(cli.planned_changes(track, found, False),
                         {"title": "T", "year": "1999", "genre": "Rock"})

    def test_tag_undo_restores_old_values_and_audio(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "Alt"})
        before = library.hash_audio(self.path("a.mp3"), *library.audio_range(self.path("a.mp3")))
        log = journal.Journal(cli.DATA_DIR, "tags")
        log.record(action="tag", path=self.path("a.mp3"), old={"artist": "Alt", "year": ""},
                   new={"artist": "Neu", "year": "1999"})
        log.close()
        write_tags(self.path("a.mp3"), {"artist": "Neu", "year": "1999"})
        self.assertEqual(library.read_file(self.path("a.mp3"))["year"], "1999")
        after = library.hash_audio(self.path("a.mp3"), *library.audio_range(self.path("a.mp3")))
        self.assertEqual(before, after)
        cli.cmd_undo(None)
        values = library.read_file(self.path("a.mp3"))
        self.assertEqual((values["artist"], values["year"]), ("Alt", ""))

    def test_umlauts_survive(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "Die Ärzte", "title": "Männer"})
        self.assertEqual(ID3(self.path("a.mp3"))["TPE1"].text[0], "Die Ärzte")
        self.assertEqual(ID3(self.path("a.mp3")).version[:2], (2, 3))


class Renaming(Base):
    def test_rename_collision_and_undo(self):
        make_mp3(self.path("x.mp3"), 1, tags={"artist": "AC/DC", "title": "T.N.T?"})
        make_mp3(self.path("y.mp3"), 2, tags={"artist": "AC/DC", "title": "T.N.T?"})
        make_mp3(self.path("kein tag.mp3"), 3)
        args = Namespace(ordner=self.root, muster="{artist} - {title}", apply=True)
        cli.cmd_rename(args)
        names = sorted(os.listdir(self.root))
        self.assertEqual(names, ["ACDC - T.N.T (2).mp3", "ACDC - T.N.T.mp3", "kein tag.mp3"])
        cli.cmd_undo(None)
        self.assertEqual(sorted(os.listdir(self.root)), ["kein tag.mp3", "x.mp3", "y.mp3"])

    def test_case_only_rename(self):
        make_mp3(self.path("queen - song.mp3"), 1, tags={"artist": "Queen", "title": "Song"})
        cli.cmd_rename(Namespace(ordner=self.root, muster="{artist} - {title}", apply=True))
        self.assertEqual(os.listdir(self.root), ["Queen - Song.mp3"])


class AcoustidRetry(Base):
    RECORDING = {"title": "Song", "first-release-date": "1999",
                 "artist-credit": [{"name": "Band", "artist": {"id": ""}}]}

    def find(self, key="", level="normal"):
        with mock.patch.dict(os.environ, {"ACOUSTID_KEY": key}), \
                mock.patch.object(lookup, "find_fpcalc", return_value="fpcalc.exe"), \
                mock.patch.object(lookup, "_itunes", return_value=None):
            return lookup.Lookup(self.db, level).find("a.mp3", "Band", "Song", 100)

    def test_level_can_change_without_new_analysis(self):
        with mock.patch.object(lookup, "_search_mb", return_value=None), \
                mock.patch.object(lookup, "_acoustid", return_value=(0.9, self.RECORDING)) as acoustid:
            self.assertEqual(self.find("key", "streng"), {"score": 90, "rejected": True})
            self.assertEqual(self.find("key", "normal")["score"], 90)
            self.assertEqual(acoustid.call_count, 1)

    def test_low_score_is_rejected_on_normal_but_accepted_on_loose(self):
        with mock.patch.object(lookup, "_search_mb", return_value=None), \
                mock.patch.object(lookup, "_acoustid", return_value=(0.75, self.RECORDING)):
            self.assertTrue(self.find("key")["rejected"])
            self.assertEqual(self.find("key", "locker")["year"], "1999")

    def test_custom_percentage_overrides_levels(self):
        with mock.patch.object(lookup, "_search_mb", return_value=None), \
                mock.patch.object(lookup, "_acoustid", return_value=(0.9, self.RECORDING)):
            self.assertTrue(self.find("key", "92")["rejected"])
            self.assertEqual(self.find("key", "88,5")["score"], 90)

    def test_accuracy_values(self):
        self.assertEqual(lookup.parse_accuracy("normal"), 0.85)
        self.assertEqual(lookup.parse_accuracy("92"), 0.92)
        self.assertEqual(lookup.parse_accuracy("92,5 %"), 0.925)
        for wrong in ("0", "0,5", "101", "-5", "abc", "", "nan"):
            with self.assertRaises(ValueError, msg=wrong):
                lookup.parse_accuracy(wrong)

    def test_invalid_accuracy_stops_the_run(self):
        make_mp3(self.path("a.mp3"), 1)
        args = Namespace(ordner=self.root, apply=False, ueberschreiben=False, limit=None, genauigkeit="abc")
        with self.assertRaises(SystemExit):
            cli.cmd_tag(args)

    def test_acoustid_prefers_studio_album_over_first_recording(self):
        def recording(date, title, *secondary):
            group = {"primary-type": "Album", "secondary-types": list(secondary)}
            return {"title": "Song", "first-release-date": date, "releases": [
                {"status": "Official", "date": date, "title": title, "release-group": group}]}
        answers = [{"results": [{"score": 0.5, "recordings": [{"id": "x"}]},
                                {"score": 0.97, "recordings": [{"id": "a"}, {"id": "b"}]}]},
                   recording("2010", "Sampler", "Compilation"), recording("1984", "Studio")]
        fpcalc = mock.Mock(returncode=0, stdout='{"duration": 100, "fingerprint": "f"}')
        with mock.patch.object(lookup.subprocess, "run", return_value=fpcalc), \
                mock.patch.object(lookup, "_get", side_effect=answers):
            score, best = lookup._acoustid("a.mp3", "key", "fpcalc.exe")
        self.assertEqual(score, 0.97)
        self.assertEqual(best["releases"][0]["title"], "Studio")

    def test_report_shows_score_and_rejected_files(self):
        make_mp3(self.path("gut.mp3"), 1)
        make_mp3(self.path("unsicher.mp3"), 2)

        def find(fake, path, artist, title, duration):
            if path.endswith("gut.mp3"):
                return {"title": "T", "source": "acoustid", "score": 93}
            return {"score": 72, "rejected": True}
        args = Namespace(ordner=self.root, apply=False, ueberschreiben=False, limit=None, genauigkeit="normal")
        with mock.patch.object(lookup.Lookup, "find", find):
            cli.cmd_tag(args)
        with open(os.path.join(cli.REPORT_DIR, "tags-vorschau.csv"), encoding="utf-8-sig") as f:
            self.assertIn(";93;", f.read())
        with open(os.path.join(cli.REPORT_DIR, "nicht-gefunden.csv"), encoding="utf-8-sig") as f:
            self.assertIn(";72", f.read())

    def test_key_added_later_retries_only_sound_recognition(self):
        with mock.patch.object(lookup, "_search_mb", return_value=None) as search, \
                mock.patch.object(lookup, "_acoustid", return_value=(0.9, self.RECORDING)) as acoustid:
            self.assertIsNone(self.find())
            searches = search.call_count
            self.assertEqual(acoustid.call_count, 0)

            result = self.find("key")
            self.assertEqual((result["year"], result["source"]), ("1999", "acoustid"))
            self.assertEqual((search.call_count, acoustid.call_count), (searches, 1))

            self.assertEqual(self.find("key")["year"], "1999")
            self.assertEqual((search.call_count, acoustid.call_count), (searches, 1))

    def test_miss_without_key_is_not_searched_twice(self):
        with mock.patch.object(lookup, "_search_mb", return_value=None) as search:
            self.find()
            searches = search.call_count
            self.assertIsNone(self.find())
            self.assertEqual(search.call_count, searches)


class Lookup(unittest.TestCase):
    def test_prefers_studio_album_over_compilation(self):
        def recording(date, title, *secondary):
            group = {"primary-type": "Album", "secondary-types": list(secondary)}
            return {"first-release-date": date,
                    "releases": [{"status": "Official", "date": date, "title": title, "release-group": group}]}
        best = min([(1.0, recording("2023", "Hits", "Compilation")), (1.0, recording("1975", "Opera")),
                    (1.0, recording("1992", "Studio"))], key=lambda c: lookup._preference(*c))
        self.assertEqual(best[1]["releases"][0]["title"], "Opera")


class Updates(unittest.TestCase):
    def release(self, tag, name="MP3-Organizer-Setup-1.2.0.exe"):
        return {"tag_name": tag, "html_url": "u", "assets": [
            {"name": "quelle.zip", "browser_download_url": "z"},
            {"name": name, "browser_download_url": "x", "digest": "sha256:ab"}]}

    def test_newer_version_is_offered(self):
        release = updater.parse_release(self.release("v1.2.0"), "1.1.9")
        self.assertEqual((release.version, release.asset_url), ("1.2.0", "x"))

    def test_numeric_compare(self):
        self.assertIsNotNone(updater.parse_release(self.release("v0.10.0"), "0.9.0"))

    def test_same_or_older_is_ignored(self):
        self.assertIsNone(updater.parse_release(self.release("v1.2.0"), "1.2.0"))
        self.assertIsNone(updater.parse_release(self.release("v1.0.0"), "1.2.0"))

    def test_release_without_installer_is_ignored(self):
        self.assertIsNone(updater.parse_release(self.release("v2.0.0", "notizen.txt"), "1.0.0"))

    def test_installer_restarts_the_app(self):
        with mock.patch.object(updater.subprocess, "Popen") as popen:
            updater.start_installer("setup.exe")
        arguments = popen.call_args.args[0]
        self.assertIn("/VERYSILENT", arguments)
        self.assertIn("/RESTARTAPP=1", arguments)

    def test_wrong_checksum_is_rejected(self):
        release = updater.Release("1.2.0", "u", "x", "MP3-Organizer-Setup-1.2.0.exe", "sha256:falsch")
        with mock.patch.object(urllib.request, "urlopen", return_value=io.BytesIO(b"daten")) as fake:
            fake.return_value.headers = {}
            with self.assertRaises(ValueError):
                updater.download(release)


if __name__ == "__main__":
    unittest.main()
