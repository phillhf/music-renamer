"""Tests für Formate, Klangvergleich, Alben, Cover, Songtexte und Muster."""
import os
import sqlite3
import ssl
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_musicrenamer import Base, make_mp3

from musicrenamer import albums, cli, fingerprint, library, lookup, tags
from musicrenamer.dupes import find_duplicates

JPEG = b"\xff\xd8\xff\xe0" + b"bild" * 50
PNG = b"\x89PNG\r\n\x1a\n" + b"bild" * 50


def make_flac(path, md5=1):
    """Kleinste gültige FLAC-Datei; mutagen braucht nur den STREAMINFO-Block."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = (44100 << 44) | (1 << 41) | (15 << 36) | 441000
    info = (4096).to_bytes(2, "big") * 2 + bytes(6) + fields.to_bytes(8, "big") + md5.to_bytes(16, "big")
    with open(path, "wb") as f:
        f.write(b"fLaC\x80\x00\x00\x22" + info + bytes(64))


class Formats(Base):
    def test_flac_roundtrip_with_cover_and_lyrics(self):
        path = self.path("a.flac")
        make_flac(path)
        tags.write_tags(path, {"artist": "Die Ärzte", "albumartist": "Band", "year": "1998", "track": "3",
                               "cover": PNG, "lyrics": "Text"})
        values = library.read_file(path)
        self.assertEqual((values["artist"], values["albumartist"], values["year"], values["track"]),
                         ("Die Ärzte", "Band", "1998", "3"))
        self.assertTrue(values["has_cover"] and values["has_lyrics"])
        tags.write_tags(path, {"cover": "", "lyrics": "", "artist": ""})
        values = library.read_file(path)
        self.assertFalse(values["has_cover"] or values["has_lyrics"] or values["artist"])

    def test_mp3_cover_and_lyrics(self):
        path = self.path("a.mp3")
        make_mp3(path, 1, tags={"artist": "A", "albumartist": "B", "cover": JPEG, "lyrics": "Text"})
        values = library.read_file(path)
        self.assertEqual(values["albumartist"], "B")
        self.assertTrue(values["has_cover"] and values["has_lyrics"])

    def test_scan_finds_all_extensions_but_ignores_others(self):
        make_mp3(self.path("a.mp3"), 1)
        make_flac(self.path("b.FLAC"))
        open(self.path("c.txt"), "w").close()
        names = sorted(os.path.basename(t.path) for t in self.tracks())
        self.assertEqual(names, ["a.mp3", "b.FLAC"])

    def test_broken_file_is_reported_not_fatal(self):
        os.makedirs(self.root)
        with open(self.path("kaputt.m4a"), "wb") as f:
            f.write(b"kein audio")
        errors = library.scan(self.root, self.db, progress=lambda m: None)
        self.assertEqual(len(errors), 1)

    def test_flac_with_same_audio_is_exact_duplicate(self):
        make_flac(self.path("a.flac"), md5=7)
        make_flac(self.path("b.flac"), md5=7)
        tags.write_tags(self.path("b.flac"), {"artist": "X"})
        groups = find_duplicates(self.tracks(), self.db, lambda m: None)
        self.assertEqual([g.kind for g in groups], ["exakt"])


class Database(unittest.TestCase):
    def test_old_database_is_rebuilt_but_keeps_lookups(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = os.path.join(folder.name, "alt.sqlite")
        old = sqlite3.connect(path)
        old.executescript("CREATE TABLE files (path TEXT PRIMARY KEY, size INTEGER);"
                          "CREATE TABLE lookups (key TEXT PRIMARY KEY, result TEXT);"
                          "INSERT INTO lookups VALUES ('k', '1');")
        old.close()
        db = library.connect(path)
        self.addCleanup(db.close)
        self.assertEqual(db.execute("SELECT count(*) FROM lookups").fetchone()[0], 1)
        db.execute("SELECT has_cover FROM files")


class Sound(Base):
    SONG = [(i * 2654435761) & 0xFFFFFFFF for i in range(1, 300)]
    OTHER = [(i * 40503 * 65599 + 7) & 0xFFFFFFFF for i in range(1, 300)]

    def noisy(self, values, flips=1):
        return [v ^ ((1 << (i % 32)) if i % 3 == 0 else 0) for i, v in enumerate(values)]

    def test_similarity_separates_same_and_different(self):
        self.assertGreater(fingerprint.similarity(self.SONG, self.noisy(self.SONG)), 0.95)
        self.assertLess(fingerprint.similarity(self.SONG, self.OTHER), 0.7)

    def test_similarity_handles_offset(self):
        self.assertGreater(fingerprint.similarity(self.SONG, [0] * 16 + self.SONG), 0.95)

    def test_too_short_is_not_a_match(self):
        self.assertEqual(fingerprint.similarity(self.SONG[:5], self.SONG[:5]), 0)

    def fake_raw(self, path, fpcalc):
        return {"a.mp3": self.SONG, "b.mp3": self.noisy(self.SONG), "c.mp3": self.OTHER}[os.path.basename(path)]

    def test_groups_by_sound_and_keeps_best_file(self):
        make_mp3(self.path("a.mp3"), 1, bitrate=320)
        make_mp3(self.path("b.mp3"), 2)
        make_mp3(self.path("c.mp3"), 3)
        with mock.patch.object(fingerprint, "raw_fingerprint", self.fake_raw) as raw:
            groups = find_duplicates(self.tracks(), self.db, lambda m: None, fpcalc="fpcalc")
        self.assertEqual([g.kind for g in groups], ["klang"])
        self.assertTrue(groups[0].keep.path.endswith("a.mp3"))

    def test_fingerprints_are_cached(self):
        make_mp3(self.path("a.mp3"), 1)
        calls = []

        def counting(path, fpcalc):
            calls.append(path)
            return self.SONG
        with mock.patch.object(fingerprint, "raw_fingerprint", counting):
            find_duplicates(self.tracks(), self.db, lambda m: None, fpcalc="f")
            find_duplicates(self.tracks(), self.db, lambda m: None, fpcalc="f")
        self.assertEqual(len(calls), 1)

    def test_different_length_is_never_a_match(self):
        make_mp3(self.path("a.mp3"), 1)
        make_mp3(self.path("b.mp3"), 2, seconds=60)
        with mock.patch.object(fingerprint, "raw_fingerprint", lambda p, f: self.SONG):
            self.assertEqual(find_duplicates(self.tracks(), self.db, lambda m: None, fpcalc="f"), [])

    def test_sound_duplicates_are_moved_without_similar_option(self):
        make_mp3(self.path("a.mp3"), 1, bitrate=320)
        make_mp3(self.path("b.mp3"), 2)
        with mock.patch.object(fingerprint, "raw_fingerprint", lambda p, f: self.SONG), \
                mock.patch.object(cli, "find_fpcalc", return_value="f"):
            cli.cmd_dupes(Namespace(ordner=self.root, ziel=None, aehnlich=False, klang=True, apply=True))
        self.assertEqual(os.listdir(self.path("Dubletten")), ["b.mp3"])


def release(group, title, track, date="1990", rank=0):
    return {"group": group, "title": title, "date": date, "track": track, "rank": rank}


class Albums(unittest.TestCase):
    def match(self, folder, name, artist, *releases):
        track = Namespace(path=os.path.join(folder, name))
        return track, {"artist": artist, "album": releases[0]["title"], "year": "2000", "track": "",
                       "group": releases[0]["group"], "releases": list(releases)}

    def test_folder_agrees_on_one_album(self):
        matches = [
            self.match("x", "1.mp3", "A", release("hits", "Sampler", "9", rank=2), release("alb", "Album", "1")),
            self.match("x", "2.mp3", "A", release("alb", "Album", "2")),
            self.match("x", "3.mp3", "A", release("hits", "Sampler", "1", rank=2), release("alb", "Album", "3")),
        ]
        self.assertEqual(albums.align_albums(matches), 3)
        self.assertEqual([(f["album"], f["track"], f["albumartist"], f["year"]) for _, f in matches],
                         [("Album", str(i), "A", "1990") for i in (1, 2, 3)])
        self.assertEqual(matches[0][1]["group"], "alb")

    def test_few_tracks_stay_as_they_are(self):
        matches = [self.match("x", "1.mp3", "A", release("g", "Album", "1")),
                   self.match("x", "2.mp3", "A", release("g", "Album", "2"))]
        self.assertEqual(albums.align_albums(matches), 0)

    def test_mixed_folder_stays_as_it_is(self):
        matches = [self.match("x", f"{i}.mp3", "A", release(f"g{i}", f"Album {i}", "1")) for i in range(5)]
        self.assertEqual(albums.align_albums(matches), 0)
        self.assertEqual(matches[0][1]["album"], "Album 0")

    def test_several_artists_become_various_artists(self):
        matches = [self.match("x", f"{i}.mp3", f"A{i}", release("g", "Sampler", str(i))) for i in range(3)]
        albums.align_albums(matches)
        self.assertEqual(matches[0][1]["albumartist"], "Various Artists")

    def test_folders_are_separate(self):
        matches = [self.match("x", "1.mp3", "A", release("g", "Album", "1")),
                   self.match("x", "2.mp3", "A", release("g", "Album", "2")),
                   self.match("y", "3.mp3", "A", release("g", "Album", "3"))]
        self.assertEqual(albums.align_albums(matches), 0)


class Extras(Base):
    def arguments(self, **options):
        return Namespace(ordner=self.root, apply=True, ueberschreiben=False, limit=None,
                         genauigkeit="normal", **options)

    def fake_find(self, path, artist, title, duration):
        return {"artist": "Band", "title": "Song", "album": "Album", "year": "1999", "genre": "Rock",
                "track": "1", "source": "musicbrainz", "group": "g1", "releases": []}

    def test_cover_and_lyrics_are_embedded_and_undone(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "Band", "title": "Song"})
        with mock.patch.object(lookup.Lookup, "find", self.fake_find), \
                mock.patch.object(cli, "fetch_cover", return_value=JPEG) as cover, \
                mock.patch.object(cli, "fetch_lyrics", return_value="Text") as lyrics:
            cli.cmd_tag(self.arguments(cover=True, songtexte=True))
        values = library.read_file(self.path("a.mp3"))
        self.assertTrue(values["has_cover"] and values["has_lyrics"])
        self.assertEqual(values["album"], "Album")
        cli.cmd_undo(None)
        values = library.read_file(self.path("a.mp3"))
        self.assertFalse(values["has_cover"] or values["has_lyrics"] or values["album"])
        self.assertEqual(values["artist"], "Band")

    def test_one_cover_download_per_album(self):
        make_mp3(self.path("a.mp3"), 1)
        make_mp3(self.path("b.mp3"), 2)
        with mock.patch.object(lookup.Lookup, "find", self.fake_find), \
                mock.patch.object(cli, "fetch_cover", return_value=JPEG) as cover:
            cli.cmd_tag(self.arguments(cover=True))
        self.assertEqual(cover.call_count, 1)

    def test_existing_cover_is_kept(self):
        make_mp3(self.path("a.mp3"), 1, tags={"cover": PNG})
        with mock.patch.object(lookup.Lookup, "find", self.fake_find), \
                mock.patch.object(cli, "fetch_cover", return_value=JPEG) as cover:
            cli.cmd_tag(self.arguments(cover=True))
        self.assertEqual(cover.call_count, 0)

    def test_preview_downloads_nothing(self):
        make_mp3(self.path("a.mp3"), 1)
        args = self.arguments(cover=True, songtexte=True)
        args.apply = False
        with mock.patch.object(lookup.Lookup, "find", self.fake_find), \
                mock.patch.object(cli, "fetch_cover") as cover, mock.patch.object(cli, "fetch_lyrics") as lyrics:
            cli.cmd_tag(args)
        self.assertEqual((cover.call_count, lyrics.call_count), (0, 0))

    def test_complete_file_is_still_looked_up_for_missing_cover(self):
        make_mp3(self.path("a.mp3"), 1, tags={"artist": "A", "title": "T", "album": "B", "year": "1", "genre": "G"})
        with mock.patch.object(lookup.Lookup, "find", self.fake_find), \
                mock.patch.object(cli, "fetch_cover", return_value=JPEG) as cover:
            cli.cmd_tag(self.arguments(cover=True))
        self.assertEqual(cover.call_count, 1)

    def test_invalid_cover_is_ignored(self):
        with mock.patch.object(lookup, "_fetch", return_value=b"<html>"):
            self.assertIsNone(lookup.fetch_cover("g"))
        with mock.patch.object(lookup, "_fetch", return_value=JPEG):
            self.assertEqual(lookup.fetch_cover("g"), JPEG)

    def test_failed_downloads_do_not_stop_the_run(self):
        with mock.patch.object(lookup, "_fetch", side_effect=ConnectionError("weg")):
            self.assertIsNone(lookup.fetch_cover("g"))
            self.assertEqual(lookup.fetch_lyrics("A", "T", "B", 100), "")

    def test_missing_lyrics_give_empty_text(self):
        with mock.patch.object(lookup, "_get", return_value=None):
            self.assertEqual(lookup.fetch_lyrics("A", "T", "B", 100), "")


class Patterns(Base):
    def rename(self, pattern):
        cli.cmd_rename(Namespace(ordner=self.root, muster=pattern, apply=True))

    def test_folder_pattern_sorts_collection_and_keeps_extension(self):
        make_mp3(self.path("wirr", "x.mp3"), 1, tags={"artist": "Queen", "title": "Song", "album": "Opera", "track": "3/12"})
        make_flac(self.path("y.flac"))
        tags.write_tags(self.path("y.flac"), {"artist": "Queen", "title": "Mehr", "album": "Opera", "track": "4"})
        self.rename("{artist}/{album}/{track} - {title}")
        self.assertEqual(sorted(os.listdir(self.path("Queen", "Opera"))), ["03 - Song.mp3", "04 - Mehr.flac"])
        self.assertFalse(os.path.exists(self.path("wirr")))
        cli.cmd_undo(None)
        self.assertTrue(os.path.exists(self.path("wirr", "x.mp3")))
        self.assertFalse(os.path.exists(self.path("Queen", "Opera", "03 - Song.mp3")))

    def test_missing_values_stay_readable(self):
        make_mp3(self.path("x.mp3"), 1, tags={"artist": "Queen", "title": "Song"})
        self.rename("{albumartist}/{album}/{track} - {title}")
        self.assertTrue(os.path.exists(self.path("Queen", "Unbekanntes Album", "Song.mp3")))

    def test_without_folders_file_stays_in_its_folder(self):
        make_mp3(self.path("Sub", "x.mp3"), 1, tags={"artist": "Queen", "title": "Song"})
        self.rename("{artist} - {title}")
        self.assertTrue(os.path.exists(self.path("Sub", "Queen - Song.mp3")))

    def test_dubletten_folder_stays_out_of_sorting(self):
        make_mp3(self.path("Dubletten", "x.mp3"), 1, tags={"artist": "Queen", "title": "Song"})
        self.rename("{artist}/{title}")
        self.assertTrue(os.path.exists(self.path("Dubletten", "x.mp3")))

    def test_unknown_placeholder_is_refused(self):
        make_mp3(self.path("x.mp3"), 1)
        with self.assertRaises(SystemExit):
            self.rename("{kuenstler} - {title}")


class ReleaseData(unittest.TestCase):
    def test_result_keeps_album_data(self):
        recording = {"title": "T", "first-release-date": "1980", "artist-credit": [{"name": "A", "artist": {"id": "x"}}],
                     "releases": [{"title": "Album", "status": "Official", "date": "1980",
                                   "release-group": {"id": "rg", "primary-type": "Album"},
                                   "media": [{"track": [{"number": "4"}]}]}]}
        result = lookup._result_from(recording, "musicbrainz")
        self.assertEqual((result["group"], result["track"]), ("rg", "4"))
        self.assertEqual(result["releases"][0], {"group": "rg", "title": "Album", "date": "1980", "track": "4", "rank": 0})

    def test_album_survives_many_samplers(self):
        sampler = {"title": "Sampler", "status": "Official", "date": "2000",
                   "release-group": {"id": "s", "primary-type": "Album", "secondary-types": ["Compilation"]}}
        album = {"title": "Album", "status": "Official", "date": "1990",
                 "release-group": {"id": "a", "primary-type": "Album"}}
        result = lookup._result_from({"title": "T", "releases": [sampler] * 100 + [album]}, "musicbrainz")
        self.assertEqual(len(result["releases"]), lookup.MAX_RELEASES)
        self.assertEqual(result["releases"][0]["group"], "a")

    def test_certificates_are_still_verified(self):
        self.assertEqual(lookup.SSL_CONTEXT.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(lookup.SSL_CONTEXT.check_hostname)


if __name__ == "__main__":
    unittest.main()
