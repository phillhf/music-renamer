"""Was sich zwischen Windows und macOS unterscheidet."""
import os
import ssl
import subprocess
import sys

MACOS = sys.platform == "darwin"
if MACOS:
    import certifi


def data_base():
    if MACOS:
        return os.path.expanduser("~/Library/Application Support")
    return os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")


def open_path(path):
    """Öffnet Datei oder Ordner mit dem Standardprogramm."""
    if MACOS:
        subprocess.Popen(["open", path])
    else:
        os.startfile(path)


def _ssl_context():
    # Python bringt auf dem Mac keine Stammzertifikate mit
    context = ssl.create_default_context(cafile=certifi.where() if MACOS else None)
    # Python 3.14 lehnt die Zertifikatskette von archive.org (dort liegen die Cover) wegen dieser
    # Zusatzregel ab. Zertifikat und Hostname werden weiterhin geprüft.
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


SSL_CONTEXT = _ssl_context()
