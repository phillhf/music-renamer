# Befehlszeile

Alle Befehle und Optionen von Music Renamer an einem Ort. Die Bedienung mit Fenster steht in der [Bedienungsanleitung](Bedienung.md).

## Inhalt

- [So rufst du das Programm auf](#so-rufst-du-das-programm-auf)
- [Die Grundregel: Vorschau, dann --apply](#die-grundregel-vorschau-dann---apply)
- [Übersicht aller Befehle](#übersicht-aller-befehle)
- [dubletten](#dubletten)
- [tags](#tags)
- [umbenennen](#umbenennen)
- [undo](#undo)
- [update](#update)
- [Key und Token](#key-und-token)
- [Der komplette Ablauf für eine Sammlung](#der-komplette-ablauf-für-eine-sammlung)
- [Lange Läufe](#lange-läufe)
- [Dateien und Berichte](#dateien-und-berichte)
- [Unterschiede zum Fenster](#unterschiede-zum-fenster)

## So rufst du das Programm auf

| System | Aufruf | Einrichtung |
|---|---|---|
| Debian, Ubuntu | `music-renamer-cli` | Paket `music-renamer-cli`, siehe [Linux](Linux.md) |
| Windows | `music-renamer-cli` | Option **Befehlszeile hinzufügen** im Setup, siehe [Windows](Windows.md#befehlszeile-unter-windows) |
| macOS | `python3 -m musicrenamer` | nur aus dem Quellcode, siehe [macOS](macOS.md#befehlszeile-auf-dem-mac) |

Das Image für macOS enthält nur die Version mit Fenster. In dieser Anleitung steht überall `music-renamer-cli`. Auf dem Mac ersetzt du das durch den Aufruf aus der Tabelle, Optionen und Verhalten sind gleich.

Hilfe direkt im Terminal gibt es zu jedem Befehl, mit Beispielen und einem Link auf diese Anleitung:

```bash
music-renamer-cli --help
```

```bash
music-renamer-cli tags --help
```

## Die Grundregel: Vorschau, dann --apply

**Ohne `--apply` wird nichts an deiner Musik geändert.** Das Programm schreibt nur einen Bericht, den du prüfen kannst.

**Mit `--apply` wird sofort ausgeführt.** Anders als im Fenster gibt es keine Prüfansicht und keine Rückfrage. Sieh dir also vorher immer den Bericht an.

Pfade mit Leerzeichen und Muster gehören in Anführungszeichen:

```bash
music-renamer-cli tags "/mnt/nas/Meine Musik"
```

## Übersicht aller Befehle

| Befehl | Wirkung |
|---|---|
| `dubletten ORDNER` | findet Dubletten und verschiebt sie mit `--apply` |
| `tags ORDNER` | sucht Metadaten und schreibt sie mit `--apply` |
| `umbenennen ORDNER` | benennt und sortiert Dateien mit `--apply` |
| `undo` | nimmt den letzten ausgeführten Schritt zurück |
| `update` | prüft, ob es eine neue Version gibt |

| Option | Befehl | Wirkung |
|---|---|---|
| `--apply` | `dubletten`, `tags`, `umbenennen` | führt die Änderungen wirklich aus |
| `--ziel ORDNER` | `dubletten` | anderer Zielordner statt `<Sammlung>/Dubletten` |
| `--klang` | `dubletten` | vergleicht am Klang, langsam |
| `--aehnlich` | `dubletten` | verschiebt auch ähnliche Treffer |
| `--ueberschreiben` | `tags` | ersetzt auch vorhandene Tags |
| `--limit N` | `tags` | bearbeitet nur die ersten N Dateien |
| `--genauigkeit WERT` | `tags` | Mindestwert der Klangerkennung |
| `--cover` | `tags` | bettet fehlende Cover ein |
| `--songtexte` | `tags` | bettet fehlende Songtexte ein |
| `--genres` | `tags` | vereinheitlicht Genres |
| `--muster MUSTER` | `umbenennen` | Aufbau von Dateiname und Ordnern |
| `-h`, `--help` | alle | zeigt die Hilfe |

## dubletten

Findet doppelte Dateien. Die beste Datei jeder Gruppe bleibt liegen, die anderen wandern in einen Ordner. Gelöscht wird nichts.

```bash
music-renamer-cli dubletten ORDNER [--apply] [--klang] [--aehnlich] [--ziel ZIELORDNER]
```

| Option | Bedeutung |
|---|---|
| ohne Option | findet nur exakte Dubletten: gleiche Audiodaten, auch bei anderen Tags oder Namen |
| `--klang` | findet zusätzlich dieselbe Aufnahme in anderer Bitrate oder anderem Format. Jede Datei wird einmal analysiert, etwa eine Sekunde je Datei. Einen Key braucht das nicht, aber `fpcalc` |
| `--aehnlich` | verschiebt auch Treffer mit gleichem Interpret und Titel und höchstens 2 Sekunden Längenunterschied. Ohne die Option stehen sie nur als „nur gemeldet“ im Bericht |
| `--ziel ORDNER` | anderer Zielordner, Standard ist `<Sammlung>/Dubletten` |

Behalten wird die Datei mit der höchsten Bitrate. Danach zählen in dieser Reihenfolge: kein Kopie-Name wie `Song (2)` oder `Song - Kopie`, mehr gefüllte Tags, kürzerer Pfad.

Lege einen eigenen Zielordner mit `--ziel` außerhalb der Sammlung an. Nur `<Sammlung>/Dubletten` wird von den anderen Schritten automatisch ausgelassen.

**Beispiele**

Nur nachsehen:

```bash
music-renamer-cli dubletten ~/Musik
```

Exakte Dubletten verschieben:

```bash
music-renamer-cli dubletten ~/Musik --apply
```

Am Klang vergleichen, erst als Vorschau:

```bash
music-renamer-cli dubletten ~/Musik --klang
```

Am Klang vergleichen und auch ähnliche Treffer in einen eigenen Ordner verschieben:

```bash
music-renamer-cli dubletten ~/Musik --klang --aehnlich --ziel ~/Dubletten --apply
```

Bericht: `dubletten.csv`.

## tags

Sucht online nach Metadaten und ergänzt sie. Standardmäßig werden nur leere Felder und Platzhalter wie „Track 01“ gefüllt.

```bash
music-renamer-cli tags ORDNER [--apply] [--cover] [--songtexte] [--genres] [--ueberschreiben] [--genauigkeit WERT] [--limit N]
```

| Option | Bedeutung |
|---|---|
| `--cover` | bettet fehlende Cover ein. Vorhandene bleiben |
| `--songtexte` | bettet fehlende Songtexte ein. Vorhandene bleiben |
| `--genres` | führt Genres wie „Synth-Pop“ auf eine kurze Liste zurück, auch bei schon getaggten Dateien |
| `--ueberschreiben` | ersetzt auch vorhandene Tags durch die gefundenen. Cover und Songtexte bleiben trotzdem |
| `--genauigkeit WERT` | Mindestwert der Klangerkennung: `streng` (95 %), `normal` (85 %, Standard), `locker` (70 %) oder eine Zahl von 1 bis 100, zum Beispiel `92` oder `92,5`. Der Wert gilt nur für die Klangerkennung, nicht für die Suche über den Namen, dort gelten fest 85 % |
| `--limit N` | nimmt nur die ersten N Dateien, zum Ausprobieren |

Die Vorschau sucht bereits online und speichert jeden Treffer. Sie kann also lange dauern, aber der Lauf mit `--apply` danach nutzt die Treffer und ist schnell. Cover und Songtexte werden erst bei `--apply` geladen.

**Beispiele**

Mit 50 Dateien ausprobieren:

```bash
music-renamer-cli tags ~/Musik --limit 50
```

Vorschau für die ganze Sammlung:

```bash
music-renamer-cli tags ~/Musik --cover --songtexte
```

Ausführen, mit denselben Optionen:

```bash
music-renamer-cli tags ~/Musik --cover --songtexte --apply
```

Alles nutzen, mit strenger Klangerkennung:

```bash
music-renamer-cli tags ~/Musik --cover --songtexte --genres --genauigkeit streng --apply
```

Vorhandene Tags ersetzen, nur mit Vorsicht:

```bash
music-renamer-cli tags ~/Musik --ueberschreiben
```

Berichte: `tags-vorschau.csv` zeigt alle geplanten Änderungen, `nicht-gefunden.csv` alle Dateien ohne sicheren Treffer.

Eigene Genre-Zuordnungen stehen in der Datei `genre-regeln.json` im [Datenordner](#dateien-und-berichte). Über die Befehlszeile wird sie nicht von selbst angelegt, du erstellst sie bei Bedarf so:

```json
{
  "neue deutsche welle": "Pop",
  "krautrock": "Rock"
}
```

## umbenennen

Benennt Dateien nach ihren Tags und sortiert sie auf Wunsch in Ordner.

```bash
music-renamer-cli umbenennen ORDNER [--apply] [--muster "MUSTER"]
```

Verfügbare Platzhalter:

| Platzhalter | Inhalt | Wenn er fehlt |
|---|---|---|
| `{artist}` | Interpret | Datei wird übersprungen |
| `{title}` | Titel | Datei wird übersprungen |
| `{album}` | Album | wird zu „Unbekanntes Album“ |
| `{albumartist}` | Album-Interpret | nimmt `{artist}` |
| `{year}` | Jahr | bleibt leer |
| `{genre}` | Genre | bleibt leer |
| `{track}` | Tracknummer, immer zweistellig: `03` | bleibt leer |

Ein `/` im Muster erzeugt Ordner, dann wird die **ganze Sammlung** ab dem angegebenen Ordner neu sortiert und leere Ordner werden entfernt. Ohne `/` bleibt jede Datei in ihrem Ordner, Standard ist `{artist} - {title}`.

| Muster | Ergebnis |
|---|---|
| `{artist} - {title}` | `Queen - Bohemian Rhapsody.mp3` |
| `{track} - {title}` | `11 - Bohemian Rhapsody.mp3` |
| `{artist}/{album}/{track} - {title}` | `Queen/A Night at the Opera/11 - Bohemian Rhapsody.mp3` |
| `{albumartist}/{year} - {album}/{track} - {title}` | `Queen/1975 - A Night at the Opera/11 - Bohemian Rhapsody.mp3` |

Zeichen, die Dateisysteme nicht erlauben, werden entfernt. Ist ein Name schon vergeben, kommt ` (2)` dazu. Vorhandene Dateien werden nie überschrieben.

**Beispiele**

Vorschau mit dem Standardmuster:

```bash
music-renamer-cli umbenennen ~/Musik
```

Ausführen:

```bash
music-renamer-cli umbenennen ~/Musik --apply
```

Die ganze Sammlung nach Interpret und Album sortieren, erst als Vorschau:

```bash
music-renamer-cli umbenennen ~/Musik --muster "{artist}/{album}/{track} - {title}"
```

Dasselbe ausführen:

```bash
music-renamer-cli umbenennen ~/Musik --muster "{artist}/{album}/{track} - {title}" --apply
```

Bericht: `umbenennen-vorschau.csv`.

## undo

Nimmt den **letzten** ausgeführten Schritt zurück, ohne Rückfrage. Verschobene Dateien gehen an ihren alten Platz, Tags bekommen ihren alten Wert, eingebettete Cover und Songtexte werden entfernt.

```bash
music-renamer-cli undo
```

Ein weiterer Aufruf nimmt den Schritt davor zurück. Dasselbe Protokoll nutzt auch das Fenster: Was dort unter „Verlauf“ steht, nimmt `undo` genauso zurück, solange derselbe Benutzer arbeitet.

Liegt am alten Platz inzwischen eine andere Datei, wird nichts überschrieben. Das Programm nennt die Datei, und du kannst das Problem lösen und `undo` erneut aufrufen.

## update

Prüft, ob es auf GitHub eine neue Version gibt, und zeigt den Link. Installiert wird dabei nichts.

```bash
music-renamer-cli update
```

Unter Windows bringt das Update der Fenster-Version oder das neue Setup auch die Befehlszeile mit, unter Linux installierst du das neue Paket wie in [Linux](Linux.md#update) beschrieben.

## Key und Token

Die Befehlszeile liest beide aus Umgebungsvariablen, nicht aus den Einstellungen des Fensters.

| Variable | Wofür | Wo es ihn gibt |
|---|---|---|
| `ACOUSTID_KEY` | Klangerkennung für Dateien ohne brauchbaren Namen | kostenlos auf [acoustid.org](https://acoustid.org/new-application) |
| `DISCOGS_TOKEN` | zweite Quelle, wenn MusicBrainz nichts findet | kostenlos unter [Discogs-Einstellungen](https://www.discogs.com/settings/developers) |

Linux und macOS, gilt für das aktuelle Terminal:

```bash
export ACOUSTID_KEY="dein-key"
```

```bash
export DISCOGS_TOKEN="dein-token"
```

Windows PowerShell, dauerhaft ab dem nächsten neuen Terminal:

```powershell
setx ACOUSTID_KEY "dein-key"
```

```powershell
setx DISCOGS_TOKEN "dein-token"
```

Ohne Key meldet das Programm „Ohne AcoustID-Key läuft die Suche nur über Name und Tags“. Alles andere funktioniert trotzdem.

## Der komplette Ablauf für eine Sammlung

Erstelle vorher eine Sicherung. Das Programm verändert deine Dateien, und `undo` ersetzt keine Sicherung.

1. Dubletten ansehen, Bericht prüfen:

   ```bash
   music-renamer-cli dubletten ~/Musik
   ```

2. Dubletten verschieben:

   ```bash
   music-renamer-cli dubletten ~/Musik --apply
   ```

3. Metadaten mit wenigen Dateien ausprobieren:

   ```bash
   music-renamer-cli tags ~/Musik --limit 50 --cover --songtexte
   ```

4. Metadaten für alles suchen, Bericht prüfen:

   ```bash
   music-renamer-cli tags ~/Musik --cover --songtexte
   ```

5. Metadaten schreiben:

   ```bash
   music-renamer-cli tags ~/Musik --cover --songtexte --apply
   ```

6. Umbenennen ansehen, Bericht prüfen:

   ```bash
   music-renamer-cli umbenennen ~/Musik --muster "{artist}/{album}/{track} - {title}"
   ```

7. Umbenennen ausführen:

   ```bash
   music-renamer-cli umbenennen ~/Musik --muster "{artist}/{album}/{track} - {title}" --apply
   ```

Die Reihenfolge ist wichtig: Erst wenn die Tags stimmen, entstehen gute Dateinamen.

## Lange Läufe

MusicBrainz erlaubt eine Anfrage pro Sekunde, große Sammlungen brauchen also Tage. Das Programm ist dafür gebaut:

- **Fortschritt:** Etwa alle 30 Sekunden steht der Stand mit Restzeit im Terminal.
- **Verbindung weg:** Das Programm meldet „Achtung: keine Verbindung“, pausiert ohne Zeitlimit und läuft von selbst weiter.
- **Abbrechen:** Mit Strg+C beendest du den Lauf. Dabei kann eine technische Fehlermeldung erscheinen, das ist unkritisch. Gefundene Treffer sind gespeichert.
- **Fortsetzen:** Starte denselben Befehl noch einmal. Bekannte Titel werden übersprungen, und das Programm meldet, wie viele es übernommen hat.

Auf einem Server läuft der Befehl am besten in `tmux`, dann überlebt er das Abmelden:

```bash
tmux new -s musik
```

Darin startest du den Befehl. Mit Strg+B und danach D trennst du dich, mit diesem Befehl kommst du zurück:

```bash
tmux attach -t musik
```

Ohne `tmux` geht es mit `nohup`, die Ausgabe steht dann in `lauf.log`:

```bash
nohup music-renamer-cli tags ~/Musik --cover --songtexte > lauf.log 2>&1 &
```

## Dateien und Berichte

| System | Datenordner |
|---|---|
| Linux | `~/.local/share/Music Renamer`, oder `$XDG_DATA_HOME/Music Renamer`, wenn gesetzt |
| Windows | `%LOCALAPPDATA%\Music Renamer` |
| macOS | `~/Library/Application Support/Music Renamer` |

| Datei | Inhalt |
|---|---|
| `berichte/dubletten.csv` | alle Dubletten mit Aktion |
| `berichte/tags-vorschau.csv` | geplante Metadaten mit Quelle und Trefferwert |
| `berichte/nicht-gefunden.csv` | Dateien ohne sicheren Treffer |
| `berichte/umbenennen-vorschau.csv` | alte und neue Namen |
| `berichte/defekte-dateien.csv` | Dateien, die sich nicht lesen ließen |
| `data/mp3org.sqlite` | Sammlung und gespeicherte Treffer |
| `data/journal-*.jsonl` | Protokolle für `undo` |
| `genre-regeln.json` | eigene Genre-Zuordnungen |

Die Berichte sind CSV-Dateien mit Semikolon und lassen sich direkt in Excel oder LibreOffice öffnen. Jeder Lauf überschreibt den Bericht des gleichen Schritts. Lösche den Ordner `data` nicht während oder zwischen Läufen, sonst muss die Suche von vorne beginnen und `undo` geht nicht mehr.

## Unterschiede zum Fenster

| | Fenster | Befehlszeile |
|---|---|---|
| Prüfansicht vor dem Ausführen | ja | nein |
| Zurücknehmen | beliebig weit über „Verlauf“ | Schritt für Schritt mit `undo` |
| Tag-Editor | ja | nein |
| Dateien einzeln per Ziehen umbenennen | ja | nein, `umbenennen` arbeitet immer mit einem ganzen Ordner |
| Sprache | Deutsch oder Englisch | Deutsch |
| Key und Token | gespeichert in den Einstellungen | Umgebungsvariablen |
| Update installieren | im Programm | von Hand, unter Windows zusammen mit dem Fenster |
