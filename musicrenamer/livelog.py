"""Live-Protokoll: jede Einzelmeldung als Zeile in einer Datei, die das Live-Fenster mitliest."""
import os
import threading
import time

NAME = "live-protokoll.txt"
MAX_BYTES = 20 * 1024 * 1024  # darüber beginnt beim nächsten Start eine neue Datei


class LiveLog:
    def __init__(self, folder):
        self.path = os.path.join(folder, NAME)
        self._lock = threading.Lock()
        self._file = None

    def rotate(self):
        """Hält die Datei klein; die vorige bleibt als .alt erhalten."""
        try:
            if os.path.getsize(self.path) > MAX_BYTES:
                os.replace(self.path, self.path + ".alt")
        except OSError:  # fehlt noch oder ist gerade geöffnet
            pass

    def ensure(self):
        """Legt die Datei an, damit das Live-Fenster sie sofort öffnen kann."""
        self.write("")
        return self.path

    def write(self, text):
        line = f"{time.strftime('%H:%M:%S')}  {text}\n" if text else ""
        with self._lock:
            try:
                if self._file is None:
                    os.makedirs(os.path.dirname(self.path), exist_ok=True)
                    self._file = open(self.path, "a", encoding="utf-8")
                self._file.write(line)
                self._file.flush()
            except OSError:  # ein volles Laufwerk darf keinen Lauf beenden
                pass

    def close(self):
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None
