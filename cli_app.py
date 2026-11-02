import subprocess
import sys
import urllib.error

from musicrenamer import updater
from musicrenamer.cli import main
from musicrenamer.lookup import find_fpcalc


def selftest():
    """Prüft im fertigen Paket, was erst dort schiefgehen kann."""
    subprocess.run([find_fpcalc(), "-version"], check=True)
    try:
        updater.check_latest()
    except urllib.error.HTTPError:  # Das Anfragelimit auf Build-Rechnern; die Antwort beweist die Zertifikate
        pass
    print("Selbsttest bestanden")


if "--selftest" in sys.argv:
    selftest()
else:
    main()
