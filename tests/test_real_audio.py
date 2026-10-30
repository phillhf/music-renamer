"""Prüfung mit echten Dateien. Läuft nur, wenn ffmpeg und fpcalc vorhanden sind (GitHub Actions)."""
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mp3org import fingerprint, library, lookup, tags

FFMPEG = shutil.which("ffmpeg")
FPCALC = lookup.find_fpcalc()
ENCODINGS = {"128.mp3": ["-b:a", "128k"], "320.mp3": ["-b:a", "320k"], "song.flac": [],
             "song.m4a": ["-b:a", "160k"], "song.ogg": ["-c:a", "libvorbis"], "song.opus": ["-c:a", "libopus"],
             "song.wma": ["-c:a", "wmav2", "-b:a", "128k"]}
RATE = 22050


def melody(path, seed, seconds=45):
    """Zufällige Melodie mit Obertönen, damit fpcalc echte Musik zu hören bekommt."""
    rng = random.Random(seed)
    samples = []
    while len(samples) < seconds * RATE:
        pitch = 110 * 2 ** (rng.randrange(36) / 12)
        for n in range(rng.choice((2205, 4410, 6615))):
            t = n / RATE
            value = sum(math.sin(2 * math.pi * pitch * k * t) / k for k in (1, 2, 3)) * math.exp(-2 * t)
            samples.append(int(max(-1, min(1, value / 2)) * 20000))
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(struct.pack(f"<{len(samples)}h", *samples))


@unittest.skipUnless(FFMPEG and FPCALC, "braucht ffmpeg und fpcalc")
class RealAudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, cls.dir, ignore_errors=True)
        cls.files = {}
        for seed in (1, 2):
            source = os.path.join(cls.dir, f"source{seed}.wav")
            melody(source, seed)
            for name, options in ENCODINGS.items():
                target = os.path.join(cls.dir, f"{seed}-{name}")
                subprocess.run([FFMPEG, "-v", "error", "-y", "-i", source, *options, target], check=True)
                cls.files[seed, name] = target

    def test_tags_in_every_format(self):
        for name in ENCODINGS:
            with self.subTest(name):
                path = self.files[1, name]
                values = {"artist": "Die Ärzte", "title": "Männer", "album": "13", "albumartist": "Die Ärzte",
                          "year": "1998", "genre": "Punk", "track": "3", "lyrics": "Text"}
                if not name.endswith(".wma"):
                    values["cover"] = b"\xff\xd8\xff\xe0" + b"bild" * 50
                tags.write_tags(path, values)
                read = library.read_file(path)
                self.assertGreater(read["duration"], 30)
                for field in tags.FIELDS:
                    self.assertEqual(read[field], values[field], field)
                self.assertTrue(read["has_lyrics"])
                self.assertEqual(read["has_cover"], "cover" in values)
                tags.write_tags(path, {"lyrics": "", "cover": ""})
                self.assertFalse(library.read_file(path)["has_lyrics"])

    def test_same_recording_matches_across_formats(self):
        reference = fingerprint.raw_fingerprint(self.files[1, "320.mp3"], FPCALC)
        self.assertGreater(len(reference), 100)
        scores = {}
        for name in ENCODINGS:
            same = fingerprint.raw_fingerprint(self.files[1, name], FPCALC)
            other = fingerprint.raw_fingerprint(self.files[2, name], FPCALC)
            scores[name] = (fingerprint.similarity(reference, same), fingerprint.similarity(reference, other))
        print("Klangwerte (gleich, anders):", {k: (round(a, 3), round(b, 3)) for k, (a, b) in scores.items()})
        for name, (same, other) in scores.items():
            self.assertGreaterEqual(same, fingerprint.MIN_SIMILARITY, name)
            self.assertLess(other, fingerprint.MIN_SIMILARITY, name)

    def test_index_finds_the_pairs(self):
        prints = {name: fingerprint.raw_fingerprint(self.files[1, name], FPCALC) for name in ENCODINGS}
        pairs = fingerprint._candidates(prints)
        print("Kandidatenpaare:", len(pairs), "von", len(ENCODINGS) * (len(ENCODINGS) - 1) // 2)
        self.assertGreaterEqual(len(pairs), len(ENCODINGS) - 1)


if __name__ == "__main__":
    unittest.main()
