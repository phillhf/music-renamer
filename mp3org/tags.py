"""Liest und schreibt Tags aller unterstützten Formate.

MP3 wird als ID3v2.3 gespeichert, das auch ältere Player lesen.
"""
import base64
import os

from mutagen.asf import ASF
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, TALB, TCON, TDRC, TIT2, TPE1, TPE2, TRCK, USLT
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

OPENERS = {".mp3": MP3, ".flac": FLAC, ".m4a": MP4, ".mp4": MP4,
           ".ogg": OggVorbis, ".opus": OggOpus, ".wma": ASF}
EXTENSIONS = tuple(OPENERS)
FIELDS = ("artist", "title", "album", "albumartist", "year", "genre", "track")

ID3_FRAMES = {"artist": ("TPE1", TPE1), "title": ("TIT2", TIT2), "album": ("TALB", TALB),
              "albumartist": ("TPE2", TPE2), "year": ("TDRC", TDRC), "genre": ("TCON", TCON),
              "track": ("TRCK", TRCK)}
VORBIS_KEYS = {"artist": "artist", "title": "title", "album": "album", "albumartist": "albumartist",
               "year": "date", "genre": "genre", "track": "tracknumber", "lyrics": "lyrics"}
MP4_KEYS = {"artist": "\xa9ART", "title": "\xa9nam", "album": "\xa9alb", "albumartist": "aART",
            "year": "\xa9day", "genre": "\xa9gen", "lyrics": "\xa9lyr"}
ASF_KEYS = {"artist": "Author", "title": "Title", "album": "WM/AlbumTitle",
            "albumartist": "WM/AlbumArtist", "year": "WM/Year", "genre": "WM/Genre",
            "track": "WM/TrackNumber", "lyrics": "WM/Lyrics"}


def open_audio(path):
    return OPENERS[os.path.splitext(path)[1].lower()](path)


def _first(values):
    return str(values[0]).strip() if values else ""


def _read_id3(tags):
    def text(frame):
        value = tags.get(frame)
        return _first(value.text) if value else ""
    values = {field: text(frame) for field, (frame, _) in ID3_FRAMES.items()}
    values["year"] = (values["year"] or text("TYER"))[:4]
    values["has_cover"] = bool(tags.getall("APIC"))
    values["has_lyrics"] = bool(tags.getall("USLT"))
    return values


def _read_keys(tags, keys):
    values = {field: _first(tags.get(key)) for field, key in keys.items() if field != "lyrics"}
    values["year"] = values["year"][:4]
    values["has_lyrics"] = keys["lyrics"] in tags
    return values


def read_tags(audio):
    """Felder einer mit open_audio geöffneten Datei, dazu has_cover und has_lyrics."""
    tags = audio.tags if audio.tags is not None else {}
    if isinstance(audio, MP3):
        return _read_id3(tags) if tags else {**dict.fromkeys(FIELDS, ""), "has_cover": False, "has_lyrics": False}
    if isinstance(audio, MP4):
        values = _read_keys(tags, MP4_KEYS)
        number = tags.get("trkn")
        values["track"] = str(number[0][0]) if number and number[0][0] else ""
        values["has_cover"] = bool(tags.get("covr"))
        return values
    if isinstance(audio, ASF):
        return {**_read_keys(tags, ASF_KEYS), "has_cover": "WM/Picture" in tags}
    values = _read_keys(tags, VORBIS_KEYS)
    values["has_cover"] = bool(getattr(audio, "pictures", None)) or "metadata_block_picture" in tags
    return values


def _image_type(data):
    return "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"


def _picture(data):
    picture = Picture()
    picture.type, picture.mime, picture.data = 3, _image_type(data), data
    return picture


def _write_id3(audio, values):
    tags = audio.tags
    for field, value in values.items():
        if field == "cover":
            tags.delall("APIC")
            if value:
                tags.add(APIC(encoding=3, mime=_image_type(value), type=3, desc="Cover", data=value))
        elif field == "lyrics":
            tags.delall("USLT")
            if value:
                tags.add(USLT(encoding=3, lang="und", desc="", text=value))
        else:
            frame_id, frame_class = ID3_FRAMES[field]
            tags.delall(frame_id)
            if field == "year":
                tags.delall("TYER")
            if value:
                tags.add(frame_class(encoding=3, text=[str(value)]))
    tags.update_to_v23()
    audio.save(v2_version=3)


def _set_keys(tags, keys, field, value):
    key = keys[field]
    if value:
        tags[key] = [str(value)]
    elif key in tags:
        del tags[key]


def _write_mp4(audio, values):
    for field, value in values.items():
        if field == "cover":
            image = MP4Cover.FORMAT_PNG if _image_type(value or b"") == "image/png" else MP4Cover.FORMAT_JPEG
            if value:
                audio.tags["covr"] = [MP4Cover(value, imageformat=image)]
            else:
                audio.tags.pop("covr", None)
        elif field == "track":
            number = str(value).split("/")[0]
            if number.isdigit():
                audio.tags["trkn"] = [(int(number), 0)]
            else:
                audio.tags.pop("trkn", None)
        else:
            _set_keys(audio.tags, MP4_KEYS, field, value)
    audio.save()


def _write_vorbis(audio, values):
    for field, value in values.items():
        if field != "cover":
            _set_keys(audio.tags, VORBIS_KEYS, field, value)
        elif isinstance(audio, FLAC):
            audio.clear_pictures()
            if value:
                audio.add_picture(_picture(value))
        elif value:
            audio.tags["metadata_block_picture"] = [base64.b64encode(_picture(value).write()).decode()]
        elif "metadata_block_picture" in audio.tags:
            del audio.tags["metadata_block_picture"]
    audio.save()


def _write_asf(audio, values):
    for field, value in values.items():
        # Cover in WMA sind ein eigenes Binärformat und werden nicht unterstützt
        if field != "cover":
            _set_keys(audio.tags, ASF_KEYS, field, value)
    audio.save()


def write_tags(path, values):
    """Setzt die Felder aus values; ein leerer Wert entfernt das Feld."""
    audio = open_audio(path)
    if audio.tags is None:
        audio.add_tags()
    if isinstance(audio, MP3):
        _write_id3(audio, values)
    elif isinstance(audio, MP4):
        _write_mp4(audio, values)
    elif isinstance(audio, ASF):
        _write_asf(audio, values)
    else:
        _write_vorbis(audio, values)
