import subprocess
import sys
import tkinter

from musicrenamer import updater
from musicrenamer.gui import main
from musicrenamer.lookup import find_fpcalc


def selftest():
    """Prüft im fertigen Paket, was erst dort schiefgehen kann."""
    subprocess.run([find_fpcalc(), "-version"], check=True)
    updater.check_latest()
    tkinter.Tk().destroy()
    print("Selbsttest bestanden")


if "--selftest" in sys.argv:
    selftest()
else:
    main()
