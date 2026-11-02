# Music Renamer auf dem Mac

Von der Installation bis zur Deinstallation. Wie die drei Arbeitsschritte im Programm funktionieren, steht in der [Bedienungsanleitung](Bedienung.md).

## Inhalt

- [Welches Paket brauchst du?](#welches-paket-brauchst-du)
- [Installation](#installation)
- [Erster Start](#erster-start)
- [Deine erste Sammlung aufräumen](#deine-erste-sammlung-aufräumen)
- [Update](#update)
- [Lange Läufe und Ruhezustand](#lange-läufe-und-ruhezustand)
- [Wo liegen die Daten?](#wo-liegen-die-daten)
- [Deinstallation](#deinstallation)
- [Befehlszeile auf dem Mac](#befehlszeile-auf-dem-mac)
- [Wenn etwas nicht klappt](#wenn-etwas-nicht-klappt)

## Welches Paket brauchst du?

Öffne das Apfel-Menü und wähle **Über diesen Mac**.

| Dort steht | Datei |
|---|---|
| Chip: Apple M1, M2, M3 oder neuer | `Music-Renamer-x.y.z-macOS-arm64.dmg` |
| Prozessor: Intel | `Music-Renamer-x.y.z-macOS-intel.dmg` |

## Installation

1. Öffne die [Release-Seite](https://github.com/phillhf/music-renamer/releases/latest), klappe **Assets** auf und lade die passende Datei.
2. Öffne die `.dmg`-Datei per Doppelklick.
3. Ziehe **Music Renamer** im geöffneten Fenster auf den Ordner **Applications**.
4. Wirf das Image im Finder aus.

Die Klangerkennung `fpcalc` ist bereits enthalten.

## Erster Start

Die App ist nicht von Apple beglaubigt, das würde eine kostenpflichtige Mitgliedschaft erfordern. Deshalb blockiert macOS den ersten Start.

1. Öffne Music Renamer aus dem Programme-Ordner. macOS meldet, dass die App nicht geöffnet werden kann. Klicke auf **Fertig** oder **OK**.
2. Öffne **Systemeinstellungen** → **Datenschutz & Sicherheit**.
3. Scrolle nach unten zu **Sicherheit**. Dort steht ein Hinweis zu Music Renamer. Klicke auf **Trotzdem öffnen**.
4. Bestätige mit deinem Passwort oder Touch ID.

Das ist nur einmal nötig. Klappt es so nicht, entfernst du die Download-Markierung im Terminal:

```bash
xattr -dr com.apple.quarantine "/Applications/Music Renamer.app"
```

Beim ersten Zugriff auf Ordner wie Musik, Dokumente oder externe Laufwerke fragt macOS nach der Erlaubnis. Stimme zu, sonst sieht das Programm keine Dateien. Ändern lässt sich das unter **Systemeinstellungen** → **Datenschutz & Sicherheit** → **Dateien und Ordner**.

Klicke dann bei **Sammlung** auf **Auswählen …** und wähle deinen Musikordner, zum Beispiel `Musik`. Nutze zum Ausprobieren erst einen kleinen Unterordner.

## Deine erste Sammlung aufräumen

Erstelle zuerst eine Sicherung, dann geht es in dieser Reihenfolge:

1. **Dubletten:** Bei Schritt 1 auf **Prüfen und ausführen** klicken. Prüfe die Liste und klicke auf **Ausgewählte ausführen**. Dubletten liegen danach im Ordner `Dubletten` in deiner Sammlung.
2. **Metadaten:** Bei Schritt 2 **Fehlende Cover einbetten** und **Fehlende Songtexte einbetten** ankreuzen, dann auf **Prüfen und ausführen** klicken. Bei großen Sammlungen dauert das lange. Prüfe die Liste und führe sie aus.
3. **Umbenennen:** Bei Schritt 3 das Muster wählen und auf **Prüfen und ausführen** klicken. Prüfe die neuen Namen und führe sie aus.

Hat etwas nicht gepasst, nimmst du es über **Verlauf** wieder zurück. Alle Optionen erklärt die [Bedienungsanleitung](Bedienung.md).

Zum schnellen Umbenennen einzelner Dateien ziehst du sie aus dem Finder direkt ins Fenster.

Die Musikbibliothek der App **Musik** verwaltet ihre Dateien selbst. Bearbeite sie besser nicht direkt, sonst stimmen deren Einträge nicht mehr. Music Renamer ist für normale Ordner gedacht.

## Update

Beim Start prüft das Programm, ob es eine neue Version gibt, und fragt nach. Bestätigst du, lädt es das Image und öffnet es, das Programm schließt sich dann.

Ziehe Music Renamer aus dem Image wieder auf **Applications** und bestätige das Ersetzen. Das ist der einzige Unterschied zu Windows: Den letzten Schritt machst du von Hand. Einstellungen, Treffer, Berichte und Verlauf bleiben erhalten.

## Lange Läufe und Ruhezustand

Große Sammlungen brauchen Tage. Damit der Mac nicht einschläft, startest du im Terminal diesen Befehl und lässt das Fenster offen:

```bash
caffeinate -i
```

Mit Ctrl+C beendest du ihn wieder. Lass ein MacBook am Netzteil, und klappe es nicht zu, wenn kein externer Bildschirm angeschlossen ist.

Im Ruhezustand steht das Programm still, danach läuft es von selbst weiter. Auch nach Abbrechen oder Absturz geht nichts verloren: Starte den Schritt einfach noch einmal.

## Wo liegen die Daten?

Alles liegt unter `~/Library/Application Support/Music Renamer`. Im Finder erreichst du das über **Gehe zu** → **Gehe zum Ordner** und diesen Pfad.

| Ordner oder Datei | Inhalt |
|---|---|
| `berichte` | CSV-Berichte, auch über **Berichte öffnen** erreichbar |
| `data` | Sammlung, gespeicherte Treffer, Änderungsprotokolle |
| `einstellungen.json` | deine Einstellungen, auch AcoustID-Key und Discogs-Token im Klartext |
| `genre-regeln.json` | eigene Genre-Zuordnungen |

## Deinstallation

1. Lege **Music Renamer** aus dem Programme-Ordner in den Papierkorb.
2. Wenn du auch die Daten entfernen willst, lösche den Ordner `~/Library/Application Support/Music Renamer`.

Deine Musik und der Dubletten-Ordner bleiben unberührt.

## Befehlszeile auf dem Mac

Das Image enthält nur die Version mit Fenster. Die Befehlszeile läuft auf dem Mac aus dem Quellcode, das braucht niemand für die normale Nutzung.

1. Installiere Python 3.13 oder neuer von [python.org](https://www.python.org/downloads/) oder mit [Homebrew](https://brew.sh).
2. Lade auf der [Release-Seite](https://github.com/phillhf/music-renamer/releases/latest) **Source code (zip)** und entpacke die Datei, zum Beispiel in deinen Benutzerordner als `music-renamer`.
3. Wechsle im Terminal in den Ordner:

   ```bash
   cd ~/music-renamer
   ```

4. Lege eine eigene Python-Umgebung an:

   ```bash
   python3 -m venv .venv
   ```

5. Aktiviere sie. Das ist in jedem neuen Terminal nötig:

   ```bash
   source .venv/bin/activate
   ```

6. Installiere die Abhängigkeiten:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

7. Probiere es aus:

   ```bash
   python3 -m musicrenamer --help
   ```

Ein Beispiel:

```bash
python3 -m musicrenamer tags ~/Music/Sammlung --cover --songtexte
```

Alle Befehle stehen in der [Befehlsreferenz](Befehlszeile.md). Für die Klangerkennung (`--klang` und AcoustID-Key) installierst du `fpcalc` mit Homebrew:

```bash
brew install chromaprint
```

## Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| „Kann nicht geöffnet werden“ | Siehe [Erster Start](#erster-start) |
| „Ist beschädigt“ | macOS meint damit meist die fehlende Beglaubigung. Nutze den `xattr`-Befehl aus [Erster Start](#erster-start). Hilft das nicht, lade die Datei neu |
| Die App startet sofort wieder zu | Prüfe, ob du das richtige Paket für deinen Prozessor hast |
| Sammlung erscheint leer | Erlaube den Zugriff unter **Datenschutz & Sicherheit** → **Dateien und Ordner** |
| Externe Festplatte ist schreibgeschützt | Unter macOS sind NTFS-Laufwerke nur lesbar. Nutze eine Festplatte in APFS oder exFAT |
| Das Update ersetzt die App nicht | Beende Music Renamer und ziehe es erneut auf **Applications** |

Weitere Hilfe findest du in der [Bedienungsanleitung](Bedienung.md#wenn-etwas-nicht-klappt). Fehler kannst du auf [GitHub melden](https://github.com/phillhf/music-renamer/issues).
