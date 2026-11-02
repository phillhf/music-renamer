"""Fortschritt und Abbrechen des laufenden Schritts."""
import threading
import time

MIN_REPORT_GAP = 0.2


class Cancelled(BaseException):
    """Kein Exception: Fehlerbehandlung je Datei darf das Abbrechen nicht schlucken."""


class Job:
    def __init__(self):
        self.listener = None
        self._cancel = threading.Event()
        self._started = 0.0
        self._last_report = 0.0
        self._phase = ""
        self._position = (0, 0)

    def reset(self):
        self._cancel.clear()
        self._phase = ""
        self._position = (0, 0)

    def cancel(self):
        self._cancel.set()

    def step(self, done, total, text=""):
        """Meldet den Stand und beendet den Lauf, wenn abgebrochen wurde."""
        if self._cancel.is_set():
            raise Cancelled()
        now = time.monotonic()
        self._position = (done, total)
        if text != self._phase:
            self._phase, self._started, self._last_report = text, now, 0.0
        if self.listener and (now - self._last_report >= MIN_REPORT_GAP or done == total):
            self._last_report = now
            left = (now - self._started) / done * (total - done) if done else None
            self.listener(done, total, text, left)

    def wait(self, seconds):
        """Wartet; Abbrechen wirkt sofort und die Pause zählt nicht zur Restzeit."""
        if self._cancel.wait(seconds):
            raise Cancelled()
        self._started += seconds

    def notice(self, text):
        """Zeigt einen Hinweis in der Statuszeile, ohne den Stand zu ändern."""
        if self.listener:
            self.listener(*self._position, text, None)


job = Job()
