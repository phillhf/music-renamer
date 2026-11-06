# Music Renamer

Räumt große Musiksammlungen unter Windows, macOS und Linux auf: Dubletten aussortieren, fehlende Metadaten, Cover und Songtexte ergänzen, Dateien einheitlich benennen und sortieren.

Bis Version 0.5.0 hieß das Programm MP3 Organizer. Das Update übernimmt Einstellungen und Verlauf; eine bestehende Installation bleibt in ihrem Ordner.

Unterstützt MP3, FLAC, M4A, MP4, OGG, Opus und WMA. Cover lassen sich in WMA nicht einbetten.

## Anleitungen

| Anleitung | Inhalt |
|---|---|
| [Windows](docs/Windows.md) | Installation, Befehlszeile, Update, Standby, Deinstallation, Lösungen für Probleme |
| [macOS](docs/macOS.md) | Installation, erster Start trotz Warnung, Update, Deinstallation, Lösungen für Probleme |
| [Linux](docs/Linux.md) | Pakete für Debian und Ubuntu, Update, Server, Deinstallation, Lösungen für Probleme |
| [Bedienungsanleitung](docs/Bedienung.md) | alle Schritte und Optionen im Fenster, für alle Systeme gleich |
| [Befehlszeile](docs/Befehlszeile.md) | alle Befehle und Optionen mit Beispielen |

## Schnellstart

1. Lade das Paket für dein System von der [Release-Seite](https://github.com/phillhf/music-renamer/releases/latest):

   | System | Datei |
   |---|---|
   | Windows, Befehlszeile als Option | `Music-Renamer-Setup-x.y.z.exe` |
   | Mac mit Apple-Chip | `Music-Renamer-x.y.z-macOS-arm64.dmg` |
   | Mac mit Intel | `Music-Renamer-x.y.z-macOS-intel.dmg` |
   | Debian, Ubuntu mit Fenster | `music-renamer_x.y.z_amd64.deb` oder `_arm64.deb` |
   | Debian, Ubuntu, Befehlszeile | `music-renamer-cli_x.y.z_amd64.deb` oder `_arm64.deb` |

2. Installiere es wie in der Anleitung für dein System beschrieben.
3. Erstelle eine Sicherung deiner Musik und wähle sie im Programm als **Sammlung** aus.
4. Arbeite die drei Schritte in der Liste links der Reihe nach ab: **Dubletten aussortieren**, **Metadaten ergänzen**, **Umbenennen und sortieren**. Jeder Schritt erklärt oben, was er tut, zeigt dann, was er vorhat, und führt es erst nach deiner Bestätigung aus. Die Liste zeigt, welche Schritte schon erledigt sind.

Gelöscht wird nie etwas: Dubletten werden nur verschoben, und jeder Schritt lässt sich im **Verlauf** zurücknehmen.

## Was das Programm kann

- **Dubletten finden:** am identischen Audioinhalt, auf Wunsch auch am Klang in anderer Bitrate oder anderem Format
- **Metadaten ergänzen:** Interpret, Titel, Album, Album-Interpret, Jahr, Genre, Track- und CD-Nummer und Label aus [MusicBrainz](https://musicbrainz.org), der iTunes-Suche und optional [Discogs](https://www.discogs.com)
- **Cover und Songtexte einbetten:** aus dem [Cover Art Archive](https://coverartarchive.org) und von [LRCLIB](https://lrclib.net)
- **Am Klang erkennen:** auch Dateien ohne Tags und ohne brauchbaren Namen, über [AcoustID](https://acoustid.org), ohne dass du etwas einrichten musst
- **Umbenennen und sortieren:** nach frei wählbarem Muster, auf Wunsch in Ordner nach Interpret und Album oder nach Zeitraum wie 1980 - 1984 und Genre, auch in einen eigenen Zielordner
- **Dateien ins Fenster ziehen:** direkt umbenennen, ohne Sammlung
- **Prüfansicht, Tag-Editor, Verlauf:** jede Änderung vorher sehen, von Hand korrigieren und zurücknehmen
- **Für große Sammlungen gebaut:** Treffer werden sofort gespeichert, und bei Verbindungsabbrüchen pausiert der Lauf und macht von selbst weiter

Die Oberfläche gibt es auf Deutsch und Englisch.

## Befehlszeile auf einen Blick

Ohne `--apply` wird nur eine Vorschau geschrieben, mit `--apply` sofort und ohne Rückfrage ausgeführt. Der Befehl `music-renamer-cli` kommt unter Windows aus der Option **Befehlszeile hinzufügen** im Setup und unter Linux aus dem gleichnamigen Paket. Auf dem Mac läuft die Befehlszeile aus dem Quellcode. Beispiele und alle Details stehen in der [Befehlsreferenz](docs/Befehlszeile.md).

```bash
music-renamer-cli dubletten ORDNER [--apply] [--klang] [--aehnlich] [--ziel ZIELORDNER]
```

```bash
music-renamer-cli tags ORDNER [--apply] [--cover] [--songtexte] [--genres] [--ueberschreiben] [--genauigkeit WERT] [--limit N]
```

```bash
music-renamer-cli umbenennen ORDNER [--apply] [--muster "MUSTER"] [--zeitraum N] [--ziel ZIELORDNER]
```

```bash
music-renamer-cli undo
```

```bash
music-renamer-cli update
```

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

Die Befehlszeile gibt es mit `python -m musicrenamer --help`.

Programm und Installer lokal bauen (braucht PyInstaller und Inno Setup 6):

```bash
powershell -ExecutionPolicy Bypass -File installer\build.ps1
```

Auf einem Mac baut `bash installer/build_mac.sh` App und Disk-Image für den eigenen Prozessor, unter Debian oder Ubuntu `bash installer/build_deb.sh` die beiden Pakete.

Für ein Release `__version__` in `musicrenamer/__init__.py` erhöhen, committen und einen passenden Tag pushen, zum Beispiel `v0.2.0`. GitHub Actions baut daraus alle Pakete und veröffentlicht sie. Jedes Release muss die Fenster-Version für Windows, macOS und Linux sowie die Befehlszeile für Windows und Linux enthalten. Fehlt ein Paket, bricht `release.yml` vor dem Veröffentlichen ab.

## Lizenz

GPL-3.0, siehe [LICENSE](LICENSE). Enthält [mutagen](https://github.com/quodlibet/mutagen) (GPL-2.0-or-later), [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2) (MIT) und [fpcalc](https://github.com/acoustid/chromaprint) (LGPL/MIT).
