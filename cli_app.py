import subprocess
import sys

from musicrenamer import updater
from musicrenamer.cli import main
from musicrenamer.lookup import find_fpcalc


def selftest():
    """Prüft im fertigen Paket, was erst dort schiefgehen kann."""
    subprocess.run([find_fpcalc(), "-version"], check=True)
    updater.check_latest()
    print("Selbsttest bestanden")


if "--selftest" in sys.argv:
    selftest()
else:
    main()
