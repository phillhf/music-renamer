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
6. Wähle die Zusatzoptionen und schließe die Installation ab:
   - **Verknüpfung auf dem Desktop anlegen**
   - **Befehlszeile hinzufügen**, wenn du das Programm auch im Terminal nutzen willst, siehe [Befehlszeile unter Windows](#befehlszeile-unter-windows)

Danach findest du das Programm im Startmenü. Die Klangerkennung `fpcalc` ist bereits enthalten, du musst nichts nachinstallieren.

Eine vorhandene Installation erkennt das Setup und aktualisiert sie. Das gilt auch für den alten MP3 Organizer, Einstellungen und Verlauf ziehen dann automatisch um.

Für Administratoren gibt es ein stilles Setup:

```powershell
.\Music-Renamer-Setup-0.18.0.exe /VERYSILENT /DIR="D:\Music Renamer" /TASKS="desktopicon,cli"
```

## Erster Start

1. Starte Music Renamer aus dem Startmenü.
2. Klicke bei **Sammlung** auf **Auswählen …** und wähle deinen Musikordner, zum Beispiel `C:\Musik`.
3. Nutze zum Ausprobieren erst einen kleinen Unterordner wie ein einzelnes Album.

Das Programm fragt beim Start, ob es eine neue Version installieren soll, wenn es eine gibt.

## Deine erste Sammlung aufräumen

Erstelle zuerst eine Sicherung, dann geht es in dieser Reihenfolge:

1. **Dubletten:** Links **1. Dubletten aussortieren** wählen und **2. Prüfen und ausführen** klicken. Prüfe die Liste und klicke auf **Ausgewählte ausführen**. Dubletten liegen danach in `C:\Musik\Dubletten`.
2. **Metadaten:** Mit **Weiter zu Schritt 2** zur nächsten Seite, **Fehlende Cover einbetten** und **Fehlende Songtexte einbetten** ankreuzen, dann **2. Prüfen und ausführen** klicken. Bei großen Sammlungen dauert das lange. Prüfe die Liste und führe sie aus.
3. **Umbenennen:** Mit **Weiter zu Schritt 3** zur nächsten Seite, Zielordner wählen, bei **Ordner** ankreuzen, wie sortiert werden soll, zum Beispiel nach Zeitraum, und **2. Prüfen und ausführen** klicken. Prüfe die neuen Namen und führe sie aus.

Hat etwas nicht gepasst, nimmst du es über **Verlauf** wieder zurück. Alle Optionen erklärt die [Bedienungsanleitung](Bedienung.md).

Zum schnellen Umbenennen einzelner Dateien öffnest du links **Schnell umbenennen** und ziehst sie aus dem Explorer ins Fenster.

## Update

Beim Start prüft das Programm, ob es auf GitHub eine neue Version gibt, und fragt nach. Bestätigst du, lädt es das Setup, prüft die Prüfsumme, installiert es und startet neu. Über **Updates** geht das auch von Hand.

Einstellungen, Treffer, Berichte und Verlauf bleiben erhalten. Die Befehlszeile wird mit aktualisiert, wenn sie installiert ist. Läuft sie dabei gerade, wird sie beendet, und du startest den Befehl danach einfach neu.

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
| `einstellungen.json` | deine Einstellungen, auch ein eigener AcoustID-Key und das Discogs-Token im Klartext |
| `genre-regeln.json` | eigene Genre-Zuordnungen |

## Deinstallation

Über das Startmenü mit **Music Renamer deinstallieren** oder in den Windows-Einstellungen unter **Apps** → **Installierte Apps**.

Die Befehlszeile wird mit entfernt, auch aus dem Pfad. Der Uninstaller fragt, ob auch Einstellungen, Suchergebnisse, Berichte und Änderungsprotokolle entfernt werden sollen. Antworte mit **Nein**, wenn du später weitermachen willst. Deine Musik und der Dubletten-Ordner bleiben in jedem Fall unberührt.

## Befehlszeile unter Windows

Die Befehlszeile ist eine Option im Setup. Sie läuft ohne Python und bringt die Klangerkennung mit.

**Einrichten:**

1. Starte das aktuelle Setup, auch wenn das Programm schon installiert ist.
2. Setze bei den Zusatzoptionen das Häkchen **Befehlszeile hinzufügen**.
3. Schließe die Installation ab und öffne danach **ein neues Terminal**. Offene Fenster kennen den Befehl noch nicht.
4. Probiere es aus:

   ```powershell
   music-renamer-cli --help
   ```

**Beispiele:**

Vorschau:

```powershell
music-renamer-cli tags "C:\Musik" --cover --songtexte
```

Ausführen:

```powershell
music-renamer-cli tags "C:\Musik" --cover --songtexte --apply
```

Ohne `--apply` wird nichts geändert, mit `--apply` sofort ausgeführt, ohne Rückfrage. Alle Befehle stehen in der [Befehlsreferenz](Befehlszeile.md).

Das Programm liegt im Unterordner `cli` des Programmordners, standardmäßig also in `C:\Tools\Music Renamer\cli`, und nutzt dieselben Treffer und denselben Verlauf wie das Fenster. Lass aber nicht beides gleichzeitig laufen.

Die Klangerkennung ist eingebaut. **Ein Discogs-Token dauerhaft speichern**, gilt ab dem nächsten neuen Terminal:

```powershell
setx DISCOGS_TOKEN "dein-token"
```

**Entfernen:** Starte das Setup erneut und nimm das Häkchen heraus. Dann verschwindet nur die Befehlszeile, das Programm bleibt.

## Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| SmartScreen lässt das Setup nicht starten | **Weitere Informationen**, dann **Trotzdem ausführen**. Wird das Blockieren von deiner Firma verwaltet, frage die IT |
| Das Antivirenprogramm meldet das Setup | Unsignierte Programme werden manchmal fälschlich gemeldet. Die Prüfsumme steht in der `.sha256`-Datei auf der Release-Seite, prüfen kannst du sie mit `Get-FileHash .\Music-Renamer-Setup-0.18.0.exe` |
| Dateien lassen sich nicht ändern | Schließe Player, die die Musik gerade nutzen, und prüfe, ob die Dateien schreibgeschützt sind. Das Programm meldet solche Dateien im Protokoll und läuft weiter |
| Pfad zu lang | Sehr tiefe Ordner können die Grenze von Windows überschreiten. Nutze ein kürzeres Muster oder einen kürzeren Sammlungsordner |
| `music-renamer-cli` wird nicht erkannt | Öffne ein neues Terminal. Hilft das nicht, starte das Setup erneut und prüfe das Häkchen **Befehlszeile hinzufügen** |
| Das Update schlägt fehl | Lade das aktuelle Setup von der Release-Seite und installiere es darüber |

Weitere Hilfe findest du in der [Bedienungsanleitung](Bedienung.md#wenn-etwas-nicht-klappt). Fehler kannst du auf [GitHub melden](https://github.com/phillhf/music-renamer/issues).
