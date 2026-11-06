# Bedienungsanleitung

So benutzt du Music Renamer mit Fenster. Unter Windows, macOS und Linux sieht das Programm gleich aus und verhält sich gleich. Installation und Besonderheiten stehen in den Anleitungen für [Windows](Windows.md), [macOS](macOS.md) und [Linux](Linux.md), die Befehlszeile in der [Befehlsreferenz](Befehlszeile.md).

## Inhalt

- [Bevor du anfängst](#bevor-du-anfängst)
- [Das Fenster im Überblick](#das-fenster-im-überblick)
- [Vorschau und Prüfen und ausführen](#vorschau-und-prüfen-und-ausführen)
- [Die Prüfansicht](#die-prüfansicht)
- [Schritt 1: Dubletten verschieben](#schritt-1-dubletten-verschieben)
- [Schritt 2: Metadaten ergänzen](#schritt-2-metadaten-ergänzen)
- [Schritt 3: Dateien umbenennen und sortieren](#schritt-3-dateien-umbenennen-und-sortieren)
- [Dateien ins Fenster ziehen](#dateien-ins-fenster-ziehen)
- [Tag-Editor](#tag-editor)
- [Verlauf und Zurücknehmen](#verlauf-und-zurücknehmen)
- [Große Sammlungen und schlechtes Internet](#große-sammlungen-und-schlechtes-internet)
- [Berichte](#berichte)
- [Wenn etwas nicht klappt](#wenn-etwas-nicht-klappt)

## Bevor du anfängst

- **Mach eine Sicherung deiner Musik.** Das Programm verändert Tags und Dateinamen. Du kannst fast alles zurücknehmen, eine Sicherung ersetzt das aber nicht.
- **Unterstützte Formate:** MP3, FLAC, M4A, MP4, OGG, Opus und WMA. In WMA-Dateien lassen sich keine Cover einbetten.
- **Probiere es zuerst an einem kleinen Ordner**, zum Beispiel mit einem einzelnen Album. Wähle ihn als Sammlung aus und führe alle drei Schritte einmal durch.
- **Halte die Reihenfolge 1, 2, 3 ein.** Erst Dubletten aussortieren spart Suchzeit, und gute Dateinamen entstehen erst aus guten Tags.

Das Programm löscht nie Musik. Dubletten werden nur verschoben.

## Das Fenster im Überblick

Das Fenster führt dich Schritt für Schritt:

| Bereich | Wozu |
|---|---|
| **Sammlung** oben | der Ordner mit deiner Musik, alle Unterordner zählen mit. „Auswählen …“ öffnet die Ordnerauswahl. Er gilt für alle Schritte |
| **Schrittliste** links | die drei Schritte in ihrer Reihenfolge. Unter jedem steht, ob und wann er für diese Sammlung zuletzt ausgeführt wurde, während er läuft der Fortschritt in Prozent. Ein Klick öffnet den Schritt |
| **Schritt-Seite** rechts | nur der gewählte Schritt: oben ein Satz, was er tut, darunter seine Optionen und die Knöpfe **1. Vorschau ansehen** und **2. Prüfen und ausführen**. **Weiter zu Schritt …** führt zum nächsten |
| **Schnell umbenennen** links unten | eigene Seite zum Hineinziehen einzelner Dateien |
| **Protokoll** | zeigt, was das Programm tut |
| **Fortschrittsbalken und Abbrechen** | Stand und Restzeit des laufenden Schritts |
| **Verlauf** | ausgeführte Schritte ansehen und zurücknehmen |
| **Berichte öffnen** | öffnet den Ordner mit den CSV-Berichten |
| **Tag-Editor** | Tags von Hand ändern |
| **Genre-Regeln** | eigene Genre-Zuordnungen bearbeiten |
| **Hilfe** | öffnet diese Anleitung im Browser, auch während ein Schritt läuft |
| **Nach Updates suchen** | prüft auf eine neue Version |
| **Sprache** | Deutsch oder Englisch, gilt ab dem nächsten Start |

Als ausgeführt zählt ein Schritt erst, wenn du in der Prüfansicht bestätigt hast. Eine Vorschau oder eine abgebrochene Prüfansicht ändern den Status nicht. Der Status wird je Sammlung gespeichert und ist nach einem Neustart wieder da.

Während ein Schritt läuft, sind die anderen Schaltflächen gesperrt. Es läuft immer nur ein Schritt gleichzeitig. Zwischen den Seiten wechseln kannst du trotzdem.

## Vorschau und Prüfen und ausführen

Jeder Schritt hat zwei Schaltflächen:

- **1. Vorschau ansehen** ändert nichts an deiner Musik. Das Programm rechnet alles durch und schreibt einen Bericht.
- **2. Prüfen und ausführen** zeigt zuerst die Prüfansicht. Geändert wird erst, wenn du dort bestätigst.

## Die Prüfansicht

Hier siehst du jede geplante Änderung, bevor sie passiert. Das Fenster erscheint, sobald das Programm mit Rechnen fertig ist.

| Bedienung | Wirkung |
|---|---|
| Klick auf das Kästchen ☑ | Zeile an- oder abwählen |
| Zeilen markieren und Leertaste | alle markierten Zeilen umschalten |
| **Suchen** | zeigt nur Zeilen mit diesem Text |
| **Alle** und **Keine** | wählt alle sichtbaren Zeilen an oder ab. So kannst du erst suchen und dann gezielt abwählen |
| Doppelklick auf ein Feld | Wert ändern, Enter speichert, Esc verwirft. Geht in Schritt 2 bei den Tag-Feldern und in Schritt 3 beim neuen Namen |
| **Ausgewählte ausführen (Anzahl)** | führt nur die angehakten Zeilen aus |
| **Abbrechen** oder Fenster schließen | nichts wird geändert |

Bei Dubletten kommen drei Schaltflächen dazu. Markiere dafür eine Zeile:

| Bedienung | Wirkung |
|---|---|
| **Datei abspielen** | spielt die Datei, die verschoben werden soll, im Standard-Player |
| **Behaltene abspielen** | spielt die Datei, die bleiben soll |
| **Tauschen** | behält stattdessen die markierte Datei |

## Schritt 1: Dubletten verschieben

Wähle die Sammlung und entscheide dich für die Optionen:

| Option | Bedeutung |
|---|---|
| ohne Häkchen | findet exakte Dubletten: gleiche Audiodaten, auch bei anderen Tags oder Dateinamen. Das ist die sicherste Stufe |
| **Am Klang vergleichen** | findet dieselbe Aufnahme auch in anderer Bitrate oder anderem Format, unabhängig von den Tags. Jede Datei wird einmal analysiert, etwa eine Sekunde je Datei. Das Ergebnis wird gespeichert, ein Key ist nicht nötig |
| **Auch ähnliche Dubletten** | verschiebt auch Dateien mit gleichem Interpret und Titel, deren Länge höchstens 2 Sekunden abweicht. Das kann danebenliegen, also genau prüfen. Ohne Häkchen stehen sie nur im Bericht |

Live-Versionen und Remixe gelten nicht als gleich.

**Welche Datei bleibt?** Die mit der höchsten Bitrate. Danach zählen: kein Kopie-Name wie `Song (2)` oder `Song - Kopie`, mehr gefüllte Tags, kürzerer Pfad.

**Wohin kommen die Dubletten?** In den Ordner `Dubletten` in deiner Sammlung, die Unterordner bleiben erhalten. Aus `C:\Musik\Queen\Song.mp3` wird `C:\Musik\Dubletten\Queen\Song.mp3`. Alle Schritte lassen diesen Ordner aus. Wenn du zufrieden bist, löschst du ihn selbst, das Programm tut es nie.

## Schritt 2: Metadaten ergänzen

Das Programm liest Interpret und Titel aus den Tags, sonst aus dem Dateinamen. Aus `01 Queen - Song.mp3` wird Interpret „Queen“ und Titel „Song“. Damit sucht es online nach dem Rest. Dateien ohne sicheren Treffer bleiben unverändert und stehen in `nicht-gefunden.csv`.

**Welche Daten kommen woher?**

| Daten | Quelle |
|---|---|
| Interpret, Titel | [MusicBrainz](https://musicbrainz.org), optional Discogs |
| Album | MusicBrainz, optional Discogs |
| Tracknummer mit Gesamtzahl, zum Beispiel `4/12` | MusicBrainz |
| CD-Nummer mit Gesamtzahl, zum Beispiel `1/2` | MusicBrainz |
| Label, also die Plattenfirma | MusicBrainz |
| Jahr der Erstveröffentlichung | MusicBrainz, sonst iTunes-Suche, optional Discogs |
| Album-Interpret | MusicBrainz, bei Album-Ordnern aus den Titeln abgeleitet, zum Beispiel „Various Artists“ |
| Genre | MusicBrainz, sonst iTunes-Suche, optional Discogs |
| Cover | [Cover Art Archive](https://coverartarchive.org), 500 Pixel, in die Datei eingebettet |
| Songtexte | [LRCLIB](https://lrclib.net), in die Datei eingebettet |

**Die Optionen**

| Option | Bedeutung |
|---|---|
| **Vorhandene Tags ersetzen** | ersetzt auch gefüllte Felder durch die Angaben von MusicBrainz und korrigiert so zum Beispiel die Schreibweise von Interpreten und Alben. Ohne Häkchen werden nur leere Felder und Platzhalter wie „Track 01“ oder das Genre „Other“ gefüllt. Prüfe die Liste vor dem Ausführen genau |
| **Fehlende Cover einbetten** | vorhandene Cover bleiben immer unberührt |
| **Fehlende Songtexte einbetten** | vorhandene Songtexte bleiben immer unberührt |
| **Genres vereinheitlichen** | führt Varianten wie „Synth-Pop“ auf eine kurze Liste zurück, auch bei schon getaggten Dateien |
| **Erweitert** | klappt die folgenden drei Einstellungen auf. Ist ein Key oder Token eingetragen, ist der Bereich schon offen |
| **Genauigkeit Klangerkennung** | wie sicher ein Treffer am Klang sein muss: Streng (95 %), Normal (85 %) oder Locker (70 %) |
| **eigener Wert** | Zahl von 1 bis 100, hat Vorrang vor der Auswahl |
| **AcoustID-Key** | schaltet die Klangerkennung frei |
| **Discogs-Token** | schaltet Discogs als zweite Quelle frei |

**Mehrere Interpreten:** Steht im Tag eine Liste wie `Dr. Dre/Nate Dogg/Snoop Dogg`, sucht das Programm mit dem ersten Interpreten und ersetzt die Liste durch die Schreibweise von MusicBrainz, zum Beispiel `Dr. Dre feat. Snoop Dogg`. Das passiert auch ohne **Vorhandene Tags ersetzen**. Gäste im Titel wie „Stan (ft. Dido)“ stören die Suche nicht.

**Jahr in den Metadaten:** Das Programm liest das Jahr aus den Tags der Datei, egal ob es im Titel steht. Es liest auch den alten ID3v1-Teil, den Windows in den Eigenschaften ebenfalls zeigt. Ein Jahr, das schon in der Datei steht, wird für die Ordner nach Zeitraum direkt genutzt. Schritt 2 trägt es nur dort ein, wo es fehlt.

**Jahr von MusicBrainz:** Eingetragen wird das Jahr der ersten Veröffentlichung der gefundenen Aufnahme. Passt deine Datei zu einer späteren Fassung, etwa einer Neuaufnahme, steht dort deren Jahr. Prüfe bei Oldies die Jahre in der Prüfansicht.

**Reihenfolge der Suche:** Zuerst MusicBrainz über den Namen, das braucht keinen Key. Findet das nichts, folgt die Klangerkennung und danach Discogs, falls jeweils Key oder Token eingetragen sind.

**Der Trefferwert** in `tags-vorschau.csv` und der Prüfansicht sagt, wie gut Name oder Klang passen, nicht ob Album und Jahr stimmen. Für Treffer über den Namen gilt fest ein Mindestwert von 85 %. Die Genauigkeit lässt sich jederzeit ändern, ohne dass neu analysiert werden muss.

**AcoustID-Key einrichten:** Dateien wie `track01.mp3` ohne Tags lassen sich nur am Klang erkennen.

1. Klappe in Schritt 2 **Erweitert** auf und klicke auf **Key holen**. Die Seite von AcoustID öffnet sich.
2. Melde dich an. Unter **New Application** registrierst du eine **Anwendung**, das ist für private Zwecke kostenlos. Name und Version sind beliebig, zum Beispiel „Music Renamer“ und „1.0“. Die Kontakt-E-Mail ist Pflicht, die Website kannst du leer lassen. Dann **Register** klicken.
3. Kopiere den **API-Key dieser Anwendung** in das Feld **AcoustID-Key**.

Achtung: AcoustID zeigt dir auch einen persönlichen Benutzer-Key, der sieht genauso aus. Den lehnt AcoustID für die Erkennung ab. Dann meldet das Programm einmal „AcoustID lehnt den eingetragenen Key ab“ und sucht ohne Klangerkennung weiter.

Die Einstellungen werden beim Start eines Schritts gespeichert.

**Discogs-Token einrichten:** Erstelle in den [Discogs-Einstellungen](https://www.discogs.com/settings/developers) ein persönliches Token und trage es im Feld **Discogs-Token** ein.

**Alben:** Ein Ordner gilt als Album. Passen mindestens drei Titel und 60 % des Ordners oder mindestens fünf Titel zum selben Album, bekommen sie dieses Album samt Tracknummern und Album-Interpret. Enthält ein Ordner mehrere Alben, werden sie nacheinander erkannt. Schon vollständige Titel im Ordner zählen mit, behalten aber ihre Tags.

**Genre-Regeln:** Die Schaltfläche öffnet eine Textdatei mit eigenen Zuordnungen. Links steht das Genre in Kleinbuchstaben, rechts das Ziel:

```json
{
  "neue deutsche welle": "Pop",
  "krautrock": "Rock"
}
```

Die eigenen Regeln gehen der eingebauten Liste vor.

**Wann wird geladen?** Die Vorschau sucht schon online und speichert jeden Treffer, auch Label und CD-Angaben, je Album nur einmal. Sie kann lange dauern, aber „Prüfen und ausführen“ danach geht dann schnell. Cover und Songtexte werden erst beim Ausführen geladen.

## Schritt 3: Dateien umbenennen und sortieren

**Mach vorher Schritt 2.** Name und Ordner entstehen aus den Metadaten. Ohne Schritt 2 fehlen Jahr, Genre und Cover. Wurde Schritt 2 für die Sammlung noch nicht ausgeführt, fragt das Programm vor dem Umbenennen nach.

**Zielordner:** Bleibt das Feld leer, bleibt alles in der Sammlung. Wählst du einen Ordner, zum Beispiel `D:\Musik sortiert`, wandern alle Dateien mit Interpret und Titel dorthin. Dateien ohne Interpret oder Titel bleiben in der Sammlung. Danach fragt das Programm, ob es den Zielordner als neue Sammlung übernehmen soll, damit die nächsten Schritte dort arbeiten.

**Ordner:** Alle drei sind freiwillig und lassen sich kombinieren. Ohne Häkchen landen alle Dateien direkt im Zielordner.

| Häkchen | Ordner |
|---|---|
| **Nach Zeitraum** | `1980 - 1984`. Wie viele Jahre ein Ordner umfasst, stellst du daneben ein, Standard ist 5, mit 10 entstehen Jahrzehnte. Ohne Jahr: „Unbekanntes Jahr“ |
| **Darin nach Genre** | `Funk`, `Hip-Hop`. Ohne Genre: „Unbekanntes Genre“ |
| **Darin nach Interpret und Album** | `Queen\A Night at the Opera`. Bei Samplern steht dort „Various Artists“, ohne Album „Unbekanntes Album“ |

Mit allen drei Häkchen und einem Zielordner entsteht zum Beispiel:

```
Musik sortiert\
  1980 - 1984\
    Funk\
      Prince\
        Parade\
          04 - Kiss.mp3
  Unbekanntes Jahr\
    Rock\
```

Jedes Genre aus den Tags bekommt einen eigenen Ordner, auch seltene wie „Synth-Pop“. Wer weniger, größere Ordner will, lässt vorher Schritt 2 mit **Genres vereinheitlichen** laufen. Dann wird zum Beispiel Rap zu Hip-Hop und Funk zu R&B.

**Dateiname:** Du wählst ihn aus der Liste oder tippst ihn selbst:

| Platzhalter | Inhalt | Wenn er fehlt |
|---|---|---|
| `{artist}` | Interpret, Listen wie `A/B` werden zu `A feat. B` | Datei wird übersprungen |
| `{title}` | Titel | Datei wird übersprungen |
| `{album}` | Album | wird zu „Unbekanntes Album“ |
| `{albumartist}` | Album-Interpret | nimmt den Interpreten |
| `{year}` | Jahr | bleibt leer |
| `{genre}` | Genre, bei mehreren wie „Hip-Hop; Rap“ das erste | wird zu „Unbekanntes Genre“ |
| `{zeitraum}` | Zeitraum aus dem Jahr, zum Beispiel `1980 - 1984` | wird zu „Unbekanntes Jahr“ |
| `{track}` | Tracknummer, immer zweistellig: `03` | bleibt leer |
| `{disc}` | CD-Nummer, zum Beispiel `1/2` | bleibt leer |
| `{label}` | Label | bleibt leer |

Unter den Einstellungen zeigt das Programm an einem Beispiel, wohin eine Datei käme. So siehst du die Wirkung, bevor du etwas startest.

**Ohne Zielordner und ohne Häkchen** bleibt jede Datei in ihrem Ordner und wird nur umbenannt. Mit einem Häkchen wird die ganze Sammlung neu sortiert, und leere Ordner werden entfernt.

Die Dateien werden verschoben, nicht kopiert. Auf demselben Laufwerk geht das sofort, auf ein anderes Laufwerk muss jede Datei kopiert werden, das dauert bei großen Sammlungen deutlich länger. Bricht dabei eine Kopie ab, etwa weil der Datenträger voll ist, bleibt die Datei an ihrem alten Platz, und es bleibt keine halbe Kopie zurück. Der Zielordner darf nicht im Dubletten-Ordner liegen.

Zeichen, die Dateisysteme nicht erlauben, werden entfernt. Ist ein Name schon vergeben, kommt ` (2)` dazu, vorhandene Dateien werden nie überschrieben. Alles lässt sich im Verlauf zurücknehmen.

## Dateien ins Fenster ziehen

Wenn du nur ein paar Dateien schnell umbenennen willst, brauchst du keine Sammlung.

1. Stelle in Schritt 3 das Muster ein.
2. Ziehe Audiodateien oder Ordner aus dem Explorer, Finder oder Dateimanager ins Fenster. Die Seite **Schnell umbenennen** links zeigt die Ablagefläche, es geht aber überall im Fenster.
3. Prüfe die neuen Namen in der Prüfansicht und bestätige.

Gut zu wissen:

- Interpret und Titel kommen aus den Tags, sonst aus dem Dateinamen. Eine Online-Suche findet dabei nicht statt.
- Die Dateien bleiben in ihrem Ordner. Enthält das Muster Ordner, zählt nur der letzte Teil.
- Dateien, aus denen sich kein Interpret und Titel ableiten lässt, bleiben unverändert. Das betrifft zum Beispiel `track01.mp3` ohne Tags.
- Unterordner gezogener Ordner zählen mit, ein Ordner `Dubletten` direkt darin wird ausgelassen.
- Während ein anderer Schritt läuft, nimmt das Programm nichts an.

## Tag-Editor

Zum Ändern von Tags von Hand. Wähle zuerst eine Sammlung, dann lädt der Editor alle Dateien.

1. Suche über das Feld **Suchen**.
2. Markiere eine oder mehrere Dateien. Mit Strg oder Umschalt markierst du mehrere, auf dem Mac mit Cmd oder Umschalt.
3. Unten stehen die Felder. Bei mehreren Dateien mit unterschiedlichen Werten bleibt ein Feld leer.
4. Fülle nur die Felder, die sich ändern sollen, und klicke auf **Speichern**.

Leere Felder ändern nichts. Einen Tag komplett leeren kannst du hier also nicht. Änderungen stehen im Verlauf und lassen sich zurücknehmen.

## Verlauf und Zurücknehmen

Der **Verlauf** listet alle ausgeführten Schritte mit Datum, Art und Anzahl, auch Änderungen aus dem Tag-Editor.

1. Öffne **Verlauf** und markiere den Schritt.
2. Klicke auf **Zurücknehmen** und bestätige.

Neuere Schritte werden dabei mit zurückgenommen, weil sie darauf aufbauen. Dateien kommen an ihren alten Platz zurück, Tags bekommen ihre alten Werte, eingebettete Cover und Songtexte werden entfernt.

Liegt am alten Platz inzwischen eine andere Datei, wird nichts überschrieben. Das Protokoll im Fenster nennt die Datei, dann kannst du das Problem lösen und es erneut versuchen.

## Große Sammlungen und schlechtes Internet

MusicBrainz erlaubt eine Anfrage pro Sekunde, und eine Datei braucht oft mehrere Anfragen. Rechne bei 10.000 Titeln mit mehreren Stunden, bei 70.000 Titeln mit mehreren Tagen.

**Nichts geht verloren:**

- Jeder Treffer und jedes „nicht gefunden“ wird sofort gespeichert, auch bei Absturz oder Stromausfall.
- Du kannst jederzeit **Abbrechen** oder das Programm schließen. Starte danach denselben Schritt noch einmal. Bekannte Titel werden in kurzer Zeit übersprungen, und das Protokoll meldet, wie viele übernommen wurden.
- Das Einlesen der Sammlung wird alle 500 neu gelesenen Dateien gesichert.

**Wenn die Verbindung abreißt:**

1. Das Programm versucht es dreimal, das dauert etwa 15 Sekunden. Kurze Aussetzer merkst du also nicht.
2. Dann erscheint „Achtung: keine Verbindung zu musicbrainz.org“, und die Statuszeile zeigt, seit wann die Verbindung weg ist.
3. Alle 30 Sekunden prüft das Programm erneut, ohne Zeitlimit.
4. Steht die Verbindung wieder, läuft es von selbst weiter. Du musst nichts tun.

Fällt nur ein Zusatzdienst für Cover, Songtexte, Genres oder Discogs aus, läuft alles weiter, und dieser Dienst wird 10 Minuten ausgelassen. Fehlende Cover und Songtexte holt ein erneuter Lauf nach.

**Wichtig bei großen Läufen:**

- Geschrieben wird erst nach der kompletten Suche und deiner Prüfung. Bis dahin ändert sich an den Dateien nichts.
- Schalte den Standby des Computers für diese Zeit ab, wie, steht in der Anleitung für dein System. Nach dem Aufwachen läuft das Programm zwar weiter, im Standby aber steht es still.
- Ein Eintrag „nicht gefunden“ bleibt gespeichert. Hatte MusicBrainz einen Titel beim ersten Mal nicht, wird er nicht neu gesucht.

## Berichte

**Berichte öffnen** zeigt den Ordner mit den Berichten. Sie öffnen sich direkt in Excel oder LibreOffice. Jeder Lauf überschreibt den Bericht des gleichen Schritts.

| Datei | Inhalt |
|---|---|
| `dubletten.csv` | alle Dubletten mit Aktion: BEHALTEN, VERSCHIEBEN oder nur gemeldet |
| `tags-vorschau.csv` | geplante Metadaten mit Quelle und Trefferwert |
| `nicht-gefunden.csv` | Dateien ohne sicheren Treffer, abgelehnte mit ihrem Trefferwert |
| `umbenennen-vorschau.csv` | alte und neue Namen |
| `defekte-dateien.csv` | Dateien, die sich nicht lesen ließen |

## Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| Viele Dateien in `nicht-gefunden.csv` | Prüfe, ob Interpret und Titel stimmen. Trage einen AcoustID-Key ein, oder setze die Genauigkeit herunter und starte Schritt 2 neu |
| Ein Treffer ist falsch | Wähle die Zeile in der Prüfansicht ab oder korrigiere sie per Doppelklick. Schon geschrieben: über den Verlauf zurücknehmen |
| Eine Datei wird beim Umbenennen übersprungen | Interpret oder Titel fehlen. Schritt 2 oder Tag-Editor nutzen |
| Fehlende Cover oder Songtexte | Nicht jedes Album hat ein Cover und nicht jeder Titel einen Songtext. Das Häkchen muss gesetzt sein, Dateien mit vorhandenem Cover bleiben unverändert |
| „AcoustID lehnt den eingetragenen Key ab“ | Es ist der Benutzer-Key eingetragen. Lege auf acoustid.org eine Anwendung an und trage deren Key ein, siehe AcoustID-Key einrichten |
| „Abbruch: …“ während der Suche | 25 Dateien in Folge wurden abgelehnt, oft liegt es an einem falschen Key. Key prüfen und neu starten, die Treffer sind gespeichert |
| „Fehler bei Datei: …“ im Protokoll | Die Datei ist vielleicht schreibgeschützt oder gerade in einem Player geöffnet. Die anderen Dateien laufen weiter |
| Die Statuszeile meldet „Pausiert“ | Keine Verbindung. Das Programm macht von selbst weiter |
| Datei steht in `defekte-dateien.csv` | Die Datei ist beschädigt oder kein echtes Audioformat. Sie wird in allen Schritten ausgelassen |
| Ziehen ins Fenster geht nicht | Erscheint beim Start „Dateien ablegen ist nicht verfügbar“, nutze Schritt 3. Läuft gerade ein Schritt, warte, bis er fertig ist |
