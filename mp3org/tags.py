"""Schreibt ID3-Tags. Gespeichert wird als ID3v2.3, das auch ältere Player lesen."""
from mutagen.id3 import TALB, TCON, TDRC, TIT2, TPE1, TRCK
from mutagen.mp3 import MP3

FRAMES = {"artist": ("TPE1", TPE1), "title": ("TIT2", TIT2), "album": ("TALB", TALB),
          "year": ("TDRC", TDRC), "genre": ("TCON", TCON), "track": ("TRCK", TRCK)}


def write_tags(path, values):
    """Setzt die Felder aus values; ein leerer Wert entfernt das Feld."""
    audio = MP3(path)
    if audio.tags is None:
        audio.add_tags()
    for field, value in values.items():
        frame_id, frame_class = FRAMES[field]
        audio.tags.delall(frame_id)
        if field == "year":
            audio.tags.delall("TYER")
        if value:
            audio.tags.add(frame_class(encoding=3, text=[str(value)]))
    audio.tags.update_to_v23()
    audio.save(v2_version=3)
