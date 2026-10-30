# MP3 Organizer

Räumt große Musiksammlungen unter Windows auf: Dubletten aussortieren, fehlende Metadaten, Cover und Songtexte ergänzen, Dateien einheitlich benennen und sortieren.

Unterstützt MP3, FLAC, M4A, MP4, OGG, Opus und WMA. Cover lassen sich in WMA nicht einbetten.

## Installation

Den aktuellen `MP3-Organizer-Setup-x.y.z.exe` von der [Release-Seite](https://github.com/phillhf/mp3-organizer/releases/latest) laden und starten. Adminrechte sind nicht nötig. Der Installer ist nicht signiert, deshalb warnt Windows SmartScreen beim ersten Start („Weitere Informationen“ → „Trotzdem ausführen“).

Der Standardordner ist `C:\Tools\MP3 Organizer`. Das Setup erkennt eine vorhandene Installation und aktualisiert sie, Einstellungen und Berichte bleiben dabei erhalten.

Beim Start prüft das Programm, ob es auf GitHub eine neue Version gibt, und bietet das Update an. Über „Nach Updates suchen“ geht das auch von Hand.

## Deinstallation

Über das Startmenü („MP3 Organizer deinstallieren“) oder die Windows-Einstellungen unter „Installierte Apps“. Der Uninstaller fragt, ob auch Einstellungen, Suchergebnisse, Berichte und Änderungsprotokolle entfernt werden sollen. Deine Musik und der Dubletten-Ordner bleiben in jedem Fall unberührt.

## Benutzung

Sammlung auswählen und die drei Schritte nacheinander abarbeiten. Jeder Schritt hat **Vorschau** (ändert nichts, schreibt einen CSV-Bericht) und **Prüfen und ausführen**. Die Berichte öffnen sich über „Berichte öffnen“.

Die **Prüfansicht** zeigt jede geplante Änderung. Zeilen lassen sich abwählen und Felder per Doppelklick korrigieren; ausgeführt wird nur, was angehakt ist. Bei Dubletten lassen sich beide Dateien im Standard-Player anhören, und „Tauschen“ behält die andere Datei.

Jeder Lauf zeigt Fortschritt und Restzeit und lässt sich mit „Abbrechen“ stoppen. Bereits Erledigtes bleibt erhalten, gesuchte Treffer auch, sodass der nächste Lauf dort weitermacht.

1. **Dubletten verschieben.** Identische Audiodaten werden auch bei unterschiedlichen Tags und Namen erkannt. Behalten wird die Datei mit der höchsten Bitrate, danach die mit den meisten Tags. Der Rest wandert nach `<Sammlung>\Dubletten`, also zum Beispiel von `C:\Musik` nach `C:\Musik\Dubletten`, gelöscht wird nichts. Alle Schritte lassen diesen Ordner aus. Mit „Am Klang vergleichen“ findet das Programm dieselbe Aufnahme auch in anderer Bitrate oder anderem Format, unabhängig von den Tags; dafür analysiert es jede Datei einmal, etwa eine Sekunde je Datei. Einen Key braucht das nicht. Ähnliche Dubletten (gleicher Interpret und Titel, Länge bis 2 Sekunden Abstand) werden nur verschoben, wenn das Häkchen gesetzt ist. Live-Versionen und Remixe zählen nicht als gleich.
2. **Metadaten ergänzen.** Interpret und Titel kommen aus den Tags oder dem Dateinamen, Album, Jahr, Genre und Tracknummer aus [MusicBrainz](https://musicbrainz.org) und bei Bedarf aus der iTunes-Suche. Standardmäßig werden nur leere Felder und Platzhalter wie „Track 01“ gefüllt. Dateien ohne sicheren Treffer bleiben unverändert und stehen in `nicht-gefunden.csv`.

   Ein Ordner gilt als Album: Passen mindestens drei Titel und 60 % des Ordners oder mindestens fünf Titel zum selben Album, bekommen sie dieses Album samt Tracknummern und Album-Interpret, auch wenn einzelne Titel für sich eher zu einem Sampler passen würden. Enthält ein Ordner mehrere Alben, werden sie nacheinander erkannt. Bereits vollständige Titel im selben Ordner zählen dabei mit, behalten aber ihre Tags.

   „Genres vereinheitlichen“ führt Varianten wie „Synth-Pop“ auf eine kurze Liste zurück, auch bei schon getaggten Dateien. Eigene Zuordnungen stehen in der Datei, die „Genre-Regeln“ öffnet, zum Beispiel `"krautrock": "Rock"`.

   Findet MusicBrainz nichts, fragt das Programm die Klangerkennung und danach [Discogs](https://www.discogs.com/settings/developers), falls ein Token eingetragen ist.

   Auf Wunsch bettet das Programm fehlende Cover aus dem [Cover Art Archive](https://coverartarchive.org) und Songtexte von [LRCLIB](https://lrclib.net) ein. Vorhandene bleiben unberührt. Heruntergeladen wird erst bei „Ausführen“.
3. **Dateien umbenennen und sortieren.** Das Muster bestimmt den Namen, Standard ist `{artist} - {title}`. Verfügbar sind `{artist}`, `{title}`, `{album}`, `{albumartist}`, `{year}`, `{genre}` und `{track}`. Ein `/` erzeugt Ordner, zum Beispiel sortiert `{artist}/{album}/{track} - {title}` die ganze Sammlung nach Interpret und Album; leere Ordner werden dabei entfernt. Dateien ohne Interpret oder Titel werden übersprungen.

Der **Tag-Editor** zeigt alle Dateien mit Suche. Mehrere Dateien lassen sich auswählen und gemeinsam ändern: Nur ausgefüllte Felder werden gespeichert.

Der **Verlauf** listet alle ausgeführten Schritte mit Datum, auch Änderungen aus dem Tag-Editor. Zurücknehmen geht bis zu einem gewählten Schritt; neuere Schritte werden dabei mit zurückgenommen, weil sie darauf aufbauen.

Die Oberfläche gibt es auf Deutsch und Englisch, die Sprache gilt ab dem nächsten Start.

## Laufzeit

MusicBrainz erlaubt eine Anfrage pro Sekunde, 10.000 Titel dauern also mehrere Stunden. Alle Treffer werden gespeichert: Ein abgebrochener Lauf setzt beim nächsten Start ohne Verlust fort, und „Ausführen“ nach der Vorschau geht schnell.

## Dateien ohne brauchbaren Namen

Dateien wie `track01.mp3` ohne Tags lassen sich nur am Klang erkennen. Dafür einen kostenlosen Key auf [acoustid.org](https://acoustid.org/new-application) anlegen (der Link „Key holen“ im Programm führt direkt dorthin) und im Feld „AcoustID-Key“ eintragen. Das nötige `fpcalc` ist im Installer enthalten.

Die Auswahl „Genauigkeit Klangerkennung“ legt fest, wie sicher ein Treffer mindestens sein muss: Streng (95 %), Normal (85 %) oder Locker (70 %). Im Feld „eigener Wert“ lässt sich stattdessen eine Zahl von 1 bis 100 eintragen, sie hat dann Vorrang vor der Auswahl. Der Wert lässt sich jederzeit ohne neue Analyse ändern. `tags-vorschau.csv` zeigt den Trefferwert jeder Datei, `nicht-gefunden.csv` den Wert abgelehnter Treffer. Bei Treffern über Name und Tags ist er die Namensähnlichkeit, dafür gilt fest ein Mindestwert von 85 %. Der Wert sagt, wie gut Klang oder Name passen, nicht ob Album und Jahr stimmen.

## Daten

Datenbank, Protokolle und Berichte liegen in `%LOCALAPPDATA%\MP3 Organizer`.

## Entwicklung

```bash
pip install -r requirements.txt
```

```bash
python -m unittest discover -s tests
```

```bash
python app.py
```

Die Befehlszeile gibt es mit `python -m mp3org --help`.

Programm und Installer lokal bauen (braucht PyInstaller und Inno Setup 6):

```bash
powershell -ExecutionPolicy Bypass -File installer\build.ps1
```

Für ein Release `__version__` in `mp3org/__init__.py` erhöhen, committen und einen passenden Tag pushen, zum Beispiel `v0.2.0`. GitHub Actions baut daraus den Installer und veröffentlicht ihn.

## Lizenz

GPL-3.0, siehe [LICENSE](LICENSE). Enthält [mutagen](https://github.com/quodlibet/mutagen) (GPL-2.0-or-later) und [fpcalc](https://github.com/acoustid/chromaprint) (LGPL/MIT).
