# Music Renamer unter Windows

Von der Installation bis zur Deinstallation. Wie die drei Arbeitsschritte im Programm funktionieren, steht in der [Bedienungsanleitung](Bedienung.md).

## Inhalt

- [Installation](#installation)
- [Erster Start](#erster-start)
- [Deine erste Sammlung aufräumen](#deine-erste-sammlung-aufräumen)
- [Update](#update)
- [Lange Läufe und Standby](#lange-läufe-und-standby)
- [Wo liegen die Daten?](#wo-liegen-die-daten)
- [Deinstallation](#deinstallation)
- [Befehlszeile unter Windows](#befehlszeile-unter-windows)
- [Wenn etwas nicht klappt](#wenn-etwas-nicht-klappt)

## Installation

1. Öffne die [Release-Seite](https://github.com/phillhf/music-renamer/releases/latest) und klappe unten **Assets** auf.
2. Lade `Music-Renamer-Setup-x.y.z.exe`, wobei `x.y.z` die Versionsnummer ist. Die Datei `MP3-Organizer-Setup-…` ist nur für alte Installationen da.
3. Starte die Datei. Adminrechte brauchst du nicht.
4. Der Installer ist nicht signiert, deshalb warnt Windows SmartScreen mit „Der Computer wurde durch Windows geschützt“. Klicke auf **Weitere Informationen** und dann auf **Trotzdem ausführen**.
5. Wähle den Zielordner. Standard ist `C:\Tools\Music Renamer`.
6. Setze auf Wunsch das Häkchen für das Desktop-Symbol und schließe die Installation ab.

Danach findest du das Programm im Startmenü. Die Klangerkennung `fpcalc` ist bereits enthalten, du musst nichts nachinstallieren.

Eine vorhandene Installation erkennt das Setup und aktualisiert sie. Das gilt auch für den alten MP3 Organizer, Einstellungen und Verlauf ziehen dann automatisch um.

Für Administratoren gibt es ein stilles Setup:

```powershell
.\Music-Renamer-Setup-0.10.1.exe /VERYSILENT /DIR="D:\Music Renamer" /TASKS="desktopicon"
```

## Erster Start

1. Starte Music Renamer aus dem Startmenü.
2. Klicke bei **Sammlung** auf **Auswählen …** und wähle deinen Musikordner, zum Beispiel `C:\Musik`.
3. Nutze zum Ausprobieren erst einen kleinen Unterordner wie ein einzelnes Album.

Das Programm fragt beim Start, ob es eine neue Version installieren soll, wenn es eine gibt.

## Deine erste Sammlung aufräumen

Erstelle zuerst eine Sicherung, dann geht es in dieser Reihenfolge:

1. **Dubletten:** Bei Schritt 1 auf **Prüfen und ausführen** klicken. Prüfe die Liste und klicke auf **Ausgewählte ausführen**. Dubletten liegen danach in `C:\Musik\Dubletten`.
2. **Metadaten:** Bei Schritt 2 **Fehlende Cover einbetten** und **Fehlende Songtexte einbetten** ankreuzen, dann auf **Prüfen und ausführen** klicken. Bei großen Sammlungen dauert das lange. Prüfe die Liste und führe sie aus.
3. **Umbenennen:** Bei Schritt 3 das Muster wählen und auf **Prüfen und ausführen** klicken. Prüfe die neuen Namen und führe sie aus.

Hat etwas nicht gepasst, nimmst du es über **Verlauf** wieder zurück. Alle Optionen erklärt die [Bedienungsanleitung](Bedienung.md).

Zum schnellen Umbenennen einzelner Dateien ziehst du sie aus dem Explorer direkt ins Fenster.

## Update

Beim Start prüft das Programm, ob es auf GitHub eine neue Version gibt, und fragt nach. Bestätigst du, lädt es das Setup, prüft die Prüfsumme, installiert es und startet neu. Über **Nach Updates suchen** geht das auch von Hand.

Einstellungen, Treffer, Berichte und Verlauf bleiben erhalten.

## Lange Läufe und Standby

Große Sammlungen brauchen Tage. Damit der Computer nicht einschläft:

1. Öffne **Einstellungen** → **System** → **Netzbetrieb und Akku** (Windows 11) oder **Netzbetrieb und Energiesparen** (Windows 10).
2. Stelle den Standby für den Netzbetrieb auf **Nie**.
3. Lass einen Laptop am Netzteil.

Im Standby steht das Programm still, danach läuft es von selbst weiter. Auch nach Abbrechen, Absturz oder Neustart geht nichts verloren: Starte den Schritt einfach noch einmal.

Der Musikordner auf einem Netzlaufwerk funktioniert, ist aber deutlich langsamer. Besser ist ein lokaler Datenträger.

## Wo liegen die Daten?

Alles liegt unter `%LOCALAPPDATA%\Music Renamer`, also meist `C:\Users\DEINNAME\AppData\Local\Music Renamer`. Tippe den Pfad einfach in die Adresszeile des Explorers.

| Ordner oder Datei | Inhalt |
|---|---|
| `berichte` | CSV-Berichte, auch über **Berichte öffnen** erreichbar |
| `data` | Sammlung, gespeicherte Treffer, Änderungsprotokolle |
| `einstellungen.json` | deine Einstellungen, auch AcoustID-Key und Discogs-Token im Klartext |
| `genre-regeln.json` | eigene Genre-Zuordnungen |

## Deinstallation

Über das Startmenü mit **Music Renamer deinstallieren** oder in den Windows-Einstellungen unter **Apps** → **Installierte Apps**.

Der Uninstaller fragt, ob auch Einstellungen, Suchergebnisse, Berichte und Änderungsprotokolle entfernt werden sollen. Antworte mit **Nein**, wenn du später weitermachen willst. Deine Musik und der Dubletten-Ordner bleiben in jedem Fall unberührt.

## Befehlszeile unter Windows

Das Setup enthält nur die Version mit Fenster. Die Befehlszeile läuft unter Windows aus dem Quellcode, das braucht niemand für die normale Nutzung.

1. Installiere Python 3.13 oder neuer von [python.org](https://www.python.org/downloads/). Setze im Setup das Häkchen **Add python.exe to PATH**.
2. Lade auf der [Release-Seite](https://github.com/phillhf/music-renamer/releases/latest) **Source code (zip)** und entpacke die Datei, zum Beispiel nach `C:\Tools\music-renamer`.
3. Öffne PowerShell und wechsle in den Ordner:

   ```powershell
   cd C:\Tools\music-renamer
   ```

4. Installiere die Abhängigkeiten:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Probiere es aus:

   ```powershell
   python -m musicrenamer --help
   ```

Ein Beispiel:

```powershell
python -m musicrenamer tags "C:\Musik" --cover --songtexte
```

Alle Befehle stehen in der [Befehlsreferenz](Befehlszeile.md). Für die Klangerkennung (`--klang` und AcoustID-Key) lädst du `fpcalc.exe` von den [Chromaprint-Downloads](https://github.com/acoustid/chromaprint/releases) und legst sie im Programmordner unter `tools\fpcalc.exe` ab.

## Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| SmartScreen lässt das Setup nicht starten | **Weitere Informationen**, dann **Trotzdem ausführen**. Wird das Blockieren von deiner Firma verwaltet, frage die IT |
| Das Antivirenprogramm meldet das Setup | Unsignierte Programme werden manchmal fälschlich gemeldet. Die Prüfsumme steht in der `.sha256`-Datei auf der Release-Seite, prüfen kannst du sie mit `Get-FileHash .\Music-Renamer-Setup-0.10.1.exe` |
| Dateien lassen sich nicht ändern | Schließe Player, die die Musik gerade nutzen, und prüfe, ob die Dateien schreibgeschützt sind. Das Programm meldet solche Dateien im Protokoll und läuft weiter |
| Pfad zu lang | Sehr tiefe Ordner können die Grenze von Windows überschreiten. Nutze ein kürzeres Muster oder einen kürzeren Sammlungsordner |
| Das Update schlägt fehl | Lade das aktuelle Setup von der Release-Seite und installiere es darüber |

Weitere Hilfe findest du in der [Bedienungsanleitung](Bedienung.md#wenn-etwas-nicht-klappt). Fehler kannst du auf [GitHub melden](https://github.com/phillhf/music-renamer/issues).
