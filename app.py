import os
import subprocess
import sys
import tkinter
import urllib.error

from tkinterdnd2 import TkinterDnD

from musicrenamer import updater
from musicrenamer.gui import main
from musicrenamer.lookup import find_fpcalc


def convert_selftest():
    """Eine Sekunde Ton erzeugen und mit dem mitgelieferten ffmpeg nach MP3 umwandeln."""
    import tempfile
    from musicrenamer import convert
    ffmpeg, ffprobe = convert.tools()
    with tempfile.TemporaryDirectory() as folder:
        source = os.path.join(folder, "ton.flac")
        subprocess.run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", "sine=duration=1", source], check=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        info = convert.probe(source, ffprobe)
        assert info["kind"] == "audio", info
        assert convert.probe(convert.convert_file(source, info, ffmpeg, ffprobe, "v0"), ffprobe)["kind"] == "audio"


def selftest():
    """Prüft im fertigen Paket, was erst dort schiefgehen kann."""
    subprocess.run([find_fpcalc(), "-version"], check=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        updater.check_latest()
    except urllib.error.HTTPError:  # Das Anfragelimit auf Build-Rechnern; die Antwort beweist die Zertifikate
        pass
    if sys.platform in ("win32", "darwin"):  # dort liegt ffmpeg im Paket, unter Linux kommt es vom System
        convert_selftest()
    window = tkinter.Tk()
    TkinterDnD._require(window)
    window.destroy()
    print("Selbsttest bestanden")


if "--selftest" in sys.argv:
    selftest()
else:
    main()
