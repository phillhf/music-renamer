"""Umwandeln nach MP3: Erkennung von Videos, Umwandlung, Verlauf."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from musicrenamer import cli, convert, journal, library, tags

FFMPEG, FFPROBE = convert.find_tool("ffmpeg"), convert.find_tool("ffprobe")
COVER = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                      "1f15c4890000000d49444154789c6360000002000154a24f650000000049454e44ae426082")


def probe_answer(*streams, duration="200.0"):
    return subprocess.CompletedProcess([], 0, json.dumps({"streams": list(streams),
                                                         "format": {"duration": duration}}).encode(), b"")


AUDIO = {"codec_type": "audio", "codec_name": "flac"}
COVER_STREAM = {"codec_type": "video", "codec_name": "mjpeg", "disposition": {"attached_pic": 1}}
FILM = {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "nb_frames": "4800",
        "disposition": {"attached_pic": 0}}


class Detection(unittest.TestCase):
    def kind(self, *streams):
        with mock.patch.object(convert.subprocess, "run", return_value=probe_answer(*streams)):
            return convert.probe("x", "ffprobe")

    def test_cover_is_no_video_but_a_film_is(self):
        self.assertEqual(self.kind(AUDIO)["kind"], "audio")
        self.assertEqual(self.kind(AUDIO, COVER_STREAM)["kind"], "audio")
        self.assertTrue(self.kind(AUDIO, COVER_STREAM)["cover"])
        film = self.kind(AUDIO, FILM)
        self.assertEqual((film["kind"], film["reason"]), ("video", "h264 1920x1080"))
        # Ein Musikvideo mit Cover bleibt trotzdem ein Video
        self.assertEqual(self.kind(AUDIO, COVER_STREAM, FILM)["kind"], "video")

    def test_without_sound_or_broken(self):
        self.assertEqual(self.kind(FILM)["kind"], "video")
        self.assertEqual(self.kind(COVER_STREAM)["kind"], "stumm")
        broken = subprocess.CompletedProcess([], 1, b"", b"Invalid data found")
        with mock.patch.object(convert.subprocess, "run", return_value=broken):
            self.assertEqual(convert.probe("x", "ffprobe")["kind"], "defekt")

    def test_candidates_skip_mp3_and_originals(self):
        with tempfile.TemporaryDirectory() as root:
            for name in ("a.flac", "b.mp3", "c.mp4", "d.txt", os.path.join(convert.ORIGINALS, "e.flac")):
                os.makedirs(os.path.dirname(os.path.join(root, name)), exist_ok=True)
                open(os.path.join(root, name), "wb").close()
            found = [os.path.basename(p) for p in convert.find_candidates([root])]
            self.assertEqual(found, ["a.flac", "c.mp4"])
            # Die Sammlung liest den Ordner der Originale auch nicht mehr
            self.assertEqual(sorted(os.path.basename(p) for p in library.find_audio(root)),
                             ["a.flac", "b.mp3", "c.mp4"])

    def test_undo_brings_original_back_and_removes_mp3(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "a.flac")
            backup = os.path.join(root, convert.ORIGINALS, "a.flac")
            created = os.path.join(root, "a.mp3")
            os.makedirs(os.path.dirname(backup))
            open(backup, "wb").close()
            open(created, "wb").close()
            log = journal.Journal(os.path.join(root, "data"), "umwandeln")
            log.record(action="convert", source=source, created=created, backup=backup)
            log.close()
            journal.undo_last(os.path.join(root, "data"))
            self.assertTrue(os.path.exists(source))
            self.assertFalse(os.path.exists(created) or os.path.exists(backup))


@unittest.skipUnless(FFMPEG and FFPROBE, "braucht ffmpeg und ffprobe")
class RealConversion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.join(self.tmp.name, "Musik")
        os.makedirs(os.path.join(self.root, "Album"))
        for name, value in (("DATA_DIR", os.path.join(self.tmp.name, "data")),
                            ("REPORT_DIR", os.path.join(self.tmp.name, "berichte"))):
            patcher = mock.patch.object(cli, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make(self, name, *options, video=False):
        path = os.path.join(self.root, name)
        inputs = ["-f", "lavfi", "-i", "sine=frequency=440:duration=6"]
        if video:
            inputs += ["-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=6"]
        subprocess.run([FFMPEG, "-v", "error", "-y", *inputs, *options, path], check=True)
        return path

    def run_convert(self, apply, **options):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cli.cmd_convert(Namespace(dateien=[self.root], apply=apply, qualitaet=options.get("qualitaet", "v0"),
                                      originale_behalten=options.get("keep", False)))
        return output.getvalue()

    def test_audio_is_converted_with_tags_and_cover_videos_stay(self):
        flac = self.make(os.path.join("Album", "song.flac"))
        tags.write_tags(flac, {"artist": "Queen", "title": "Kiss", "album": "Parade", "track": "4", "cover": COVER})
        m4a = self.make("talk.m4a", "-c:a", "aac", "-b:a", "128k")
        film = self.make("film.mp4", "-c:v", "libx264", "-c:a", "aac", "-shortest", video=True)
        wav = self.make("raw.wav")
        preview = self.run_convert(False)
        self.assertIn("Umwandeln: 3", preview)
        self.assertIn("Videos, die liegen bleiben: 1", preview)
        self.assertFalse(os.path.exists(convert.target_for(flac)))

        self.run_convert(True)
        for source in (flac, m4a, wav):
            mp3 = convert.target_for(source)
            self.assertTrue(os.path.exists(mp3), mp3)
            self.assertFalse(os.path.exists(source))
            self.assertTrue(os.path.exists(convert.originals_folder(source, self.root)))
            self.assertEqual(convert.probe(mp3, FFPROBE)["kind"], "audio")
        self.assertTrue(os.path.exists(film))
        self.assertFalse(os.path.exists(convert.target_for(film)))
        audio = tags.open_audio(convert.target_for(flac))
        values = tags.read_tags(audio)
        self.assertEqual((values["artist"], values["title"], values["album"], values["track"]),
                         ("Queen", "Kiss", "Parade", "4"))
        self.assertEqual(tags.read_cover(audio), COVER)

        journal.undo_last(cli.DATA_DIR)
        for source in (flac, m4a, wav):
            self.assertTrue(os.path.exists(source))
            self.assertFalse(os.path.exists(convert.target_for(source)))

    def test_keep_originals_and_existing_mp3_is_left_alone(self):
        flac = self.make("a.flac")
        other = self.make("b.flac")
        open(convert.target_for(other), "wb").close()
        self.run_convert(True, keep=True, qualitaet="192")
        self.assertTrue(os.path.exists(flac) and os.path.exists(convert.target_for(flac)))
        self.assertEqual(os.path.getsize(convert.target_for(other)), 0)


if __name__ == "__main__":
    unittest.main()
