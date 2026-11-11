"""Was sich zwischen Windows, macOS und Linux unterscheidet."""
import os
import shutil
import ssl
import subprocess
import sys
import unicodedata

MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")
if MACOS:
    import certifi
if LINUX and getattr(sys, "frozen", False):
    # Das fertige Paket biegt den Pfad auf seine eigenen Bibliotheken um, das bricht fpcalc und xdg-open
    original = os.environ.pop("LD_LIBRARY_PATH_ORIG", None)
    os.environ.pop("LD_LIBRARY_PATH", None)
    if original is not None:
        os.environ["LD_LIBRARY_PATH"] = original


def data_base():
    if MACOS:
        return os.path.expanduser("~/Library/Application Support")
    if LINUX:
        return os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")


def fold(path):
    """Form, in der das Dateisystem zwei Schreibweisen als denselben Pfad behandelt."""
    if MACOS:
        return unicodedata.normalize("NFC", path).casefold()
    return os.path.normcase(path)


def open_path(path):
    """Öffnet Datei oder Ordner mit dem Standardprogramm."""
    if MACOS:
        subprocess.Popen(["open", path])
    elif LINUX:
        subprocess.Popen(["xdg-open", path])
    else:
        os.startfile(path)


LINUX_TERMINALS = (("x-terminal-emulator", "-e"), ("gnome-terminal", "--"), ("konsole", "-e"),
                   ("xfce4-terminal", "-x"), ("mate-terminal", "-x"), ("xterm", "-e"))


def live_view_command(path, title):
    """Befehl für ein Terminalfenster, das die Datei laufend mitliest; None, wenn es keins gibt."""
    if MACOS:
        tail = "tail -n 200 -F '" + path.replace("'", "'\\''") + "'"
        script = tail.replace("\\", "\\\\").replace('"', '\\"')
        return ["osascript", "-e", f'tell application "Terminal" to do script "{script}"',
                "-e", 'tell application "Terminal" to activate']
    if LINUX:
        for name, flag in LINUX_TERMINALS:
            if shutil.which(name):
                return [name, flag, "tail", "-n", "200", "-F", path]
        return None
    quoted = path.replace("'", "''")
    return ["powershell", "-NoProfile", "-NoExit", "-Command",
            f"$Host.UI.RawUI.WindowTitle = '{title}'; [Console]::OutputEncoding = [Text.Encoding]::UTF8; "
            f"Get-Content -LiteralPath '{quoted}' -Wait -Tail 200 -Encoding UTF8"]


def open_live_view(path, title):
    """Öffnet ein Konsolenfenster mit dem Live-Protokoll; False, wenn das System keins anbietet."""
    command = live_view_command(path, title)
    if not command:
        return False
    flags = 0 if MACOS or LINUX else subprocess.CREATE_NEW_CONSOLE
    subprocess.Popen(command, creationflags=flags)
    return True


def _ssl_context():
    # Python bringt auf dem Mac keine Stammzertifikate mit
    context = ssl.create_default_context(cafile=certifi.where() if MACOS else None)
    # Python 3.14 lehnt die Zertifikatskette von archive.org (dort liegen die Cover) wegen dieser
    # Zusatzregel ab. Zertifikat und Hostname werden weiterhin geprüft.
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


SSL_CONTEXT = _ssl_context()
