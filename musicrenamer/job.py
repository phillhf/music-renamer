"""Fortschritt und Abbrechen des laufenden Schritts."""
import threading
import time

MIN_REPORT_GAP = 0.2


class Cancelled(BaseException):
    """Kein Exception: Fehlerbehandlung je Datei darf das Abbrechen nicht schlucken."""


class Job:
    def __init__(self):
        self.listener = None
        self.detail_listener = None  # bekommt jede Einzelmeldung, etwa für das Live-Fenster
        self.current = ""  # die letzte Einzelmeldung, für die Statuszeile
        self._cancel = threading.Event()
        self._started = 0.0
        self._last_report = 0.0
        self._phase = ""
        self._position = (0, 0)

    def reset(self):
        self._cancel.clear()
        self.current = ""
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

    def activity(self, text):
        """Meldet Arbeit, deren Menge nicht bekannt ist; die Oberfläche zeigt dann einen laufenden Balken."""
        if self._cancel.is_set():
            raise Cancelled()
        self._phase, self._position = text, (0, 0)
        if self.listener:
            self.listener(0, 0, text, None)

    def detail(self, text, sub=False):
        """Eine Zeile für das Live-Fenster, etwa welche Datei gerade dran ist.

        Hauptzeilen tragen die Position wie [4210/28000], Unterzeilen (sub) sind eingerückt
        und zeigen, was mit der Datei gerade geschieht, etwa eine Anfrage oder eine Wartezeit.
        """
        done, total = self._position
        if sub:
            line = f"      {text}"
        else:
            line = f"[{done}/{total}] {text}" if total else text
            self.current = text
        if self.detail_listener:
            self.detail_listener(line)

    def wait(self, seconds):
        """Wartet; Abbrechen wirkt sofort und die Pause zählt nicht zur Restzeit."""
        if self._cancel.wait(seconds):
            raise Cancelled()
        self._started += seconds

    def notice(self, text):
        """Zeigt einen Hinweis in der Statuszeile, ohne den Stand zu ändern."""
        if self.listener:
            self.listener(*self._position, text, None)
        self.detail(text)


job = Job()
