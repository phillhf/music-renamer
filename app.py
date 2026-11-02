import subprocess
import sys
import tkinter
import urllib.error

from tkinterdnd2 import TkinterDnD

from musicrenamer import updater
from musicrenamer.gui import main
from musicrenamer.lookup import find_fpcalc


def selftest():
    """Prüft im fertigen Paket, was erst dort schiefgehen kann."""
    subprocess.run([find_fpcalc(), "-version"], check=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        updater.check_latest()
    except urllib.error.HTTPError:  # Das Anfragelimit auf Build-Rechnern; die Antwort beweist die Zertifikate
        pass
    window = tkinter.Tk()
    TkinterDnD._require(window)
    window.destroy()
    print("Selbsttest bestanden")


if "--selftest" in sys.argv:
    selftest()
else:
    main()
