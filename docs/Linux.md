# Music Renamer unter Linux

Von der Installation bis zur Deinstallation. Wie die drei Arbeitsschritte im Fenster funktionieren, steht in der [Bedienungsanleitung](Bedienung.md), die Befehlszeile in der [Befehlsreferenz](Befehlszeile.md).

## Inhalt

- [Welche Pakete gibt es?](#welche-pakete-gibt-es)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Erster Start mit Fenster](#erster-start-mit-fenster)
- [Erster Start in der Befehlszeile](#erster-start-in-der-befehlszeile)
- [Update](#update)
- [Lange Läufe und Standby](#lange-läufe-und-standby)
- [Wo liegen die Daten?](#wo-liegen-die-daten)
- [Deinstallation](#deinstallation)
- [Wenn etwas nicht klappt](#wenn-etwas-nicht-klappt)

## Welche Pakete gibt es?

| Paket | Für wen | Aufruf |
|---|---|---|
| `music-renamer` | Desktop mit Fenster | Anwendungsmenü oder `music-renamer` |
| `music-renamer-cli` | Terminal und Server, ohne Grafikbibliotheken | `music-renamer-cli` |

Du kannst eines oder beide installieren. Auf demselben Rechner und mit demselben Benutzer teilen sich beide Treffer und Verlauf. Du kannst also in der Befehlszeile suchen und im Fenster prüfen.

## Voraussetzungen

- Debian 12 oder neuer, Ubuntu 22.04 oder neuer, oder ein System mit gleicher Basis wie Linux Mint. Geprüft sind Debian 12 und 13 sowie Ubuntu 22.04 und 24.04.
- Prozessor `amd64` oder `arm64`. `arm64` passt zum Beispiel auf einen Raspberry Pi mit 64-Bit-System.

Deinen Prozessor zeigt dieser Befehl:

```bash
dpkg --print-architecture
```

Für andere Systeme wie Fedora oder Arch gibt es kein Paket.

## Installation

Lade die passende Datei von der [Release-Seite](https://github.com/phillhf/music-renamer/releases/latest). Im Terminal geht das so, setze dabei die aktuelle Version und deinen Prozessor ein.

Fenster-Version:

```bash
wget https://github.com/phillhf/music-renamer/releases/download/v0.17.0/music-renamer_0.17.0_amd64.deb
```

```bash
sudo apt install ./music-renamer_0.17.0_amd64.deb
```

Befehlszeile:

```bash
wget https://github.com/phillhf/music-renamer/releases/download/v0.17.0/music-renamer-cli_0.17.0_amd64.deb
```

```bash
sudo apt install ./music-renamer-cli_0.17.0_amd64.deb
```

**Wichtig:** Das `./` vor dem Dateinamen muss sein, sonst sucht `apt` im Internet nach dem Paket. Nutze `apt`, nicht `dpkg -i`, denn nur `apt` installiert die nötigen Abhängigkeiten mit.

Die Meldung, der Download werde „ohne Sandbox“ ausgeführt, kannst du ignorieren.

Die Klangerkennung `fpcalc` ist in den `amd64`-Paketen enthalten. Für `arm64` installiert `apt` automatisch `libchromaprint-tools` mit.

Zur Kontrolle kannst du die Prüfsumme vergleichen. Lade dafür auch die Datei `.deb.sha256` und starte im selben Ordner:

```bash
sha256sum -c music-renamer_0.17.0_amd64.deb.sha256
```

## Erster Start mit Fenster

1. Starte **Music Renamer** aus dem Anwendungsmenü oder mit dem Befehl `music-renamer`.
2. Klicke bei **Sammlung** auf **Auswählen …** und wähle deinen Musikordner. Nutze zum Ausprobieren erst einen kleinen Unterordner.
3. Erstelle eine Sicherung und arbeite die drei Schritte nacheinander ab:
   1. **Dubletten:** Links **1. Dubletten aussortieren** wählen und **2. Prüfen und ausführen** klicken. Prüfe die Liste und klicke auf **Ausgewählte ausführen**.
   2. **Metadaten:** Mit **Weiter zu Schritt 2** zur nächsten Seite, **Fehlende Cover einbetten** und **Fehlende Songtexte einbetten** ankreuzen, dann **2. Prüfen und ausführen** klicken. Prüfe die Liste und führe sie aus.
   3. **Umbenennen:** Mit **Weiter zu Schritt 3** zur nächsten Seite, Zielordner wählen, bei **Ordner** ankreuzen, wie sortiert werden soll, zum Beispiel nach Zeitraum, und **2. Prüfen und ausführen** klicken. Prüfe die neuen Namen und führe sie aus.

Hat etwas nicht gepasst, nimmst du es über **Verlauf** wieder zurück. Zum schnellen Umbenennen einzelner Dateien öffnest du links **Schnell umbenennen** und ziehst sie aus dem Dateimanager ins Fenster. Alle Optionen erklärt die [Bedienungsanleitung](Bedienung.md).

## Erster Start in der Befehlszeile

Ohne `--apply` wird nichts geändert, mit `--apply` sofort ausgeführt, ohne Rückfrage. Den vollständigen Ablauf mit allen Optionen zeigt die [Befehlsreferenz](Befehlszeile.md#der-komplette-ablauf-für-eine-sammlung). Für einen kurzen Test:

```bash
music-renamer-cli tags ~/Musik --limit 20
```

Die Berichte liegen danach unter `~/.local/share/Music Renamer/berichte`.

## Update

**Fenster-Version:** Beim Start prüft das Programm, ob es eine neue Version gibt, und fragt nach. Bestätigst du, lädt es das Paket und prüft die Prüfsumme. Das System fragt dann nach deinem Passwort, installiert das Paket und startet das Programm neu. Auch **Updates** löst das aus.

**Befehlszeile:** Dieser Befehl zeigt, ob es eine neue Version gibt:

```bash
music-renamer-cli update
```

Installiere die neue Version dann wie unter [Installation](#installation), die alte wird dabei ersetzt. Das gilt auch, wenn das automatische Update der Fenster-Version nicht klappt.

Einstellungen, Treffer, Berichte und Verlauf bleiben erhalten.

## Lange Läufe und Standby

Große Sammlungen brauchen Tage.

Damit ein Desktop nicht einschläft, startest du die Befehlszeile so:

```bash
systemd-inhibit --what=sleep:idle music-renamer-cli tags ~/Musik --cover --songtexte
```

Dasselbe geht für das Fenster:

```bash
systemd-inhibit --what=sleep:idle music-renamer
```

Auf einem Server lässt du den Befehl in `tmux` laufen, die Schritte stehen in der [Befehlsreferenz](Befehlszeile.md#lange-läufe).

Im Standby steht das Programm still, danach läuft es von selbst weiter. Auch nach Abbrechen, Absturz oder Neustart geht nichts verloren: Starte den Schritt einfach noch einmal.

## Wo liegen die Daten?

Alles liegt unter `~/.local/share/Music Renamer`, oder unter `$XDG_DATA_HOME/Music Renamer`, wenn die Variable gesetzt ist. Die Programme selbst liegen in `/opt/music-renamer` und `/opt/music-renamer-cli`.

| Ordner oder Datei | Inhalt |
|---|---|
| `berichte` | CSV-Berichte |
| `data` | Sammlung, gespeicherte Treffer, Änderungsprotokolle |
| `einstellungen.json` | Einstellungen der Fenster-Version, auch AcoustID-Key und Discogs-Token im Klartext |
| `genre-regeln.json` | eigene Genre-Zuordnungen |

Die Daten gehören dem jeweiligen Benutzer. Starte das Programm also nicht mit `sudo`, sonst liegen Treffer und Verlauf bei `root`. Lässt du den Lauf auf einem Server als eigener Benutzer laufen, braucht dieser Schreibrechte auf die Musik.

## Deinstallation

```bash
sudo apt remove music-renamer music-renamer-cli
```

Hast du nur ein Paket installiert, nennst du nur dieses. Deine Musik und der Dubletten-Ordner bleiben unberührt, die Daten in deinem Benutzerordner ebenfalls. Wenn du sie auch löschen willst:

```bash
rm -r ~/".local/share/Music Renamer"
```

## Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| `E: Paket kann nicht gefunden werden` | Das `./` vor dem Dateinamen fehlt, oder du bist nicht im Download-Ordner |
| `GLIBC_… not found` beim Start | Das System ist zu alt, nötig sind Debian 12 oder Ubuntu 22.04 |
| `Exec format error` oder „falsche Architektur“ | Du hast das falsche Paket. `dpkg --print-architecture` zeigt das richtige |
| Das automatische Update meldet einen Fehler | Es nennt den passenden `sudo apt install`-Befehl. Ist `pkexec` nicht installiert, geht es nur so |
| `Permission denied` bei Dateien | Dein Benutzer braucht Schreibrechte auf die Musik. Nutze nicht `sudo`, sondern prüfe die Rechte |
| Ziehen ins Fenster geht nicht | Unter Wayland hängt das am Desktop und ist nicht getestet. Nutze Schritt 3 oder melde dich zum Vergleich in einer X11-Sitzung an |
| Kein Fenster, `no display name` | Es gibt keine grafische Sitzung, zum Beispiel per SSH. Nutze `music-renamer-cli` |
| Klangerkennung fehlt auf `arm64` | Installiere sie mit `sudo apt install libchromaprint-tools` |
| Abspielen in der Prüfansicht geht nicht | Lege im Dateimanager einen Standard-Player für den Dateityp fest |

Weitere Hilfe findest du in der [Bedienungsanleitung](Bedienung.md#wenn-etwas-nicht-klappt). Fehler kannst du auf [GitHub melden](https://github.com/phillhf/music-renamer/issues).
