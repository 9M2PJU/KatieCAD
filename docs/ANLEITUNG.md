# KatieCAD – Kurzanleitung (Deutsch)

> English version: [USER_GUIDE.md](USER_GUIDE.md)

KatieCAD ist ein 2D-CAD mit Elektro-Erweiterung. Diese Anleitung zeigt, wo du die
Grundfunktionen findest. Sie ist als Auffrischung gedacht, wenn du das Programm
länger nicht benutzt hast oder zum ersten Mal siehst.

## Inhalt

1. [Starten](#1-starten)
2. [Das Fenster im Überblick](#2-das-fenster-im-überblick)
3. [Navigieren, Fangen, Befehlszeile](#3-navigieren-fangen-befehlszeile)
4. [Zeichnen und Bearbeiten](#4-zeichnen-und-bearbeiten)
5. [Projekte und Blätter](#5-projekte-und-blätter)
6. [Modell, Layout, Rahmen, Druck](#6-modell-layout-rahmen-druck)
7. [Blöcke und Attribute](#7-blöcke-und-attribute)
8. [Elektro: einen Schaltplan zeichnen](#8-elektro-einen-schaltplan-zeichnen)
9. [Dokumentation erzeugen](#9-dokumentation-erzeugen)
10. [Import und Export](#10-import-und-export)
11. [Tastenkürzel](#11-tastenkürzel)
12. [Tipps und häufige Fragen](#12-tipps-und-häufige-fragen)

---

## 1. Starten

```
python main.py
```

oder `python -m katiecad`. Optional installierst du die Zusatzpakete mit
`pip install -r requirements.txt` (nötig für DXF/DWG-Import und DXF-Export). Unter
Linux brauchst du außerdem `python3-tk`.

Die Sprache wechselst du im Menü **Sprache** (Deutsch / English). Sie wird
gespeichert.

## 2. Das Fenster im Überblick

| Bereich | Was es tut |
|---|---|
| **Menüleiste** | Datei, Projekt, Bearbeiten, Einfügen, Ansicht, Blöcke, Elektro, Sprache, Hilfe |
| **Werkzeugleisten** (oben) | Zeichenwerkzeuge (Auswahl, Linie, Polylinie, Kreis, Bogen, Rechteck, Text, Bemaßung, Stutzen, Brechen) und die Elektro-Werkzeuge (Pin, Verbindung, Querverweis, Maske, Klemme, Kabel, …). Dazu Layer, Linienart, Linienstärke, Farbe, Einheit, Maßstab, Zoom. |
| **Seitenleiste** (links, F4 blendet sie aus/ein) | Rückgängig / Wiederholen und die Blattliste des Projekts |
| **Zeichenfläche** | Hier zeichnest du. Das Modell ist die Zeichnung in 1:1, das Layout das Papierblatt. |
| **Eingabezeile** | Unter der Zeichenfläche. Hier tippst du Befehle und Koordinaten. |
| **Statusleiste** | Mauskoordinaten, Zoom, Layer, Auswahl, Hinweise zum aktuellen Werkzeug und die Schalter für Objektfang, Raster und Ortho |

Der Hinweis in der Statusleiste sagt dir immer, was das aktive Werkzeug als
Nächstes erwartet. **ESC** bricht den aktuellen Vorgang ab.

## 3. Navigieren, Fangen, Befehlszeile

**Mit der Maus**

- Mausrad: zoomen (zum Mauszeiger hin).
- Rechte Maustaste gedrückt halten und ziehen: Ansicht verschieben.
- Rechter Klick ohne Ziehen (Werkzeug „Auswahl“): Kontextmenü.
- Doppelklick mit der mittleren oder rechten Taste: alles anzeigen (Zoom Grenzen).
  Mit der Taste **G** geht es auch.

**Fangen und Hilfen** (Schalter in der Statusleiste, auch per Taste)

| Taste | Funktion |
|---|---|
| F3 | Objektfang (Endpunkt, Mittelpunkt, Zentrum, Schnittpunkt, Quadrant, Lot, Nächster) |
| F7 | Raster anzeigen |
| F8 | Ortho (nur waagerecht / senkrecht) |
| F9 | Rasterfang |

**Eingabezeile.** Du kannst Koordinaten als `x,y` eingeben und Befehle tippen,
zum Beispiel `L` (Linie), `K` (Kreis), `REC` (Rechteck), `T` (Text),
`M` (Verschieben), `KO` (Kopieren), `RO` (Drehen), `AR` (Reihe), `STR` (Strecken),
`TR` (Stutzen), `BR` (Brechen), `ZG` (Zoom Grenzen), `U` (Rückgängig),
`B` (Block erzeugen), `I` (Block/Gerät einfügen), `X` (Block auflösen).
Die Befehle gibt es auch auf Englisch.

## 4. Zeichnen und Bearbeiten

1. Wähle ein Werkzeug (Leiste oder Menü **Einfügen**), klicke Punkte in die
   Zeichnung oder tippe Koordinaten in die Eingabezeile.
2. Mit dem Werkzeug **Auswahl** markierst du Objekte: Klick auf ein Objekt, oder
   ein Rahmen aufziehen. *Von links nach rechts* markiert nur Objekte, die komplett
   im Rahmen liegen. *Von rechts nach links* markiert alles, was den Rahmen berührt.
   Weitere Objekte kommen zur Auswahl hinzu; **ESC** hebt sie auf.
3. Markierte Objekte bearbeitest du über das Menü **Bearbeiten**: Kopieren,
   Ausschneiden, Einfügen, Duplizieren, Verschieben, Kopieren mit Basispunkt,
   Drehen, Strecken, Reihe/Anordnung, Löschen (Entf).
4. Die gelben Griffe an einem markierten Objekt ziehst du, um es zu verändern.
5. Doppelklick auf ein Objekt öffnet dessen Bearbeitungsdialog (Blockattribute, Pin, Querverweis, Verbindung, Maske, Klemme, Kabel, Koordinatenfeld …). Auf einen Viewport aktiviert er ihn.
6. **Rückgängig** (Strg+Z) und **Wiederholen** (Strg+Y) stehen auch in der
   Seitenleiste.

Weitere Zeichenhilfen: **Bemaßung** (Menü Einfügen: **Radius-Bemaßung (DR)** und **Durchmesser-Bemaßung (DD)**: Kreis oder Bogen anklicken, dann die Textposition),
**Schraffur auf Auswahl** (Menü Einfügen), **Layer** (Schaltfläche „Layer…“)
und Farbe, Linienart und Linienstärke in der Werkzeugleiste.

**Schraffur wie in AutoCAD:** Ist nichts markiert, wählst du im Menü Einfügen › Schraffur Muster, Abstand und Winkel und klickst dann direkt in einen umschlossenen Bereich. KatieCAD findet die kleinste Fläche um den Klickpunkt (Linien dürfen sich kreuzen, Kreise, Rechtecke und Polylinien zählen mit) und schraffiert sie. Du kannst nacheinander mehrere Bereiche anklicken; ESC oder Rechtsklick beendet. Ist bereits eine geschlossene Kontur markiert, wird wie bisher diese schraffiert.

**Strecken mit Vorauswahl:** Hast du Objekte vorher mit einem überkreuzenden Fenster (von rechts nach links) markiert, springt **Strecken** (`STR`) gleich zur Basispunkt-Abfrage – das Fenster muss nicht noch einmal aufgezogen werden. Gestreckt werden dann nur die markierten Objekte. Bei anderer Vorauswahl (z. B. Einzelklick) bleibt die Auswahl erhalten und du ziehst nur noch das Fenster auf.

## 5. Projekte und Blätter

Ein **Projekt** ist ein Ordner mit einer Projektdatei (`*.katieprj`), einer Datei
pro Blatt (`Blatt_001.cadjson` …) und einem Ordner `Bloecke` für Blockdateien.

Menü **Projekt**:

- **Projekt erstellen…**: Name und Speicherort wählen. Das erste Blatt wird angelegt.
- **Projekt öffnen… / speichern / schließen / umbenennen… / löschen…**
- **Neues Blatt, Blatt duplizieren, Blatt-Eigenschaften (F2: Name und Einbauort), Blatt löschen**
- **Blätter drucken / als PDF…**
- **Dokumentation erzeugen / aktualisieren…** und **Listen als CSV exportieren…**
  (siehe Abschnitt 9)

In der **Seitenleiste** wechselst du mit einem Klick das Blatt. Das aktuelle Blatt
wird dabei automatisch gespeichert. Doppelklick benennt ein Blatt um. Mit **Strg** oder **Umschalt** + Klick markierst du
mehrere Blätter und kannst sie gemeinsam mit den Pfeiltasten verschieben oder mit „−“ löschen
(beim Markieren mehrerer Blätter bleibt das aktuelle Blatt geöffnet). Rückgängig gilt je Blatt.

Ohne Projekt arbeitest du in einer einzelnen Zeichnung (Menü **Datei**: Neu,
Öffnen, Speichern …).

## 6. Modell, Layout, Rahmen, Druck

- **Modell** (Menü **Ansicht**): die eigentliche Zeichnung in Originalgröße (mm).
- **Layout**: das Papierblatt (z. B. DIN A4 quer). Dort liegen Rahmen, Schriftkopf
  und **Viewports**, das sind Fenster auf das Modell mit eigenem Maßstab.
  Ein Viewport wird mit **Einfügen > Viewport platzieren** angelegt.
- **Einfügen > Rahmen + Schriftkopf…**: setzt Blattrand und Schriftkopf aus einer
  Vorlage. Eigene Schriftköpfe sind normale Zeichnungen (`*.cadjson`) im Ordner
  `title_blocks/`; ihr Nullpunkt ist die untere rechte Ecke des Blattrandes. Felder
  wie `PAGE`, `PAGES`, `SHEET`, `PROJECT`, `DATE`, `SCALE`, `FORMAT` füllen sich
  automatisch. Mit **Projekt > Projekteigenschaften…** trägst du Kunde, Gezeichnet/Geprüft,
  Zeichnungsnummer und den Änderungsindex (4 Zeilen mit Stand, Änderung, Name, Datum) einmal
  ein; sie erscheinen in den Schriftköpfen aller Blätter. Der Titel besteht aus Kunde,
  Projektname und Blattname; das Blattformat folgt dem gewählten Layout-Format. Die
  Feldnamen (z. B. `KUNDE`, `GEZEICHNET`, `REV1_STAND`) stehen in `title_blocks/README.md`.
- **Einfügen > Zeichnung als Schriftkopf-Vorlage speichern…** legt aus einer
  Zeichnung eine neue Vorlage an.
- **Datei > Drucken** (Strg+P) und **Projekt > Blätter drucken / als PDF…**
  erzeugen ein PDF (mehrere Blätter in einer Datei) oder öffnen die Druckvorschau.

## 7. Blöcke und Attribute

Ein **Block** ist eine wiederverwendbare Gruppe von Objekten (zum Beispiel ein
Symbol). Menü **Blöcke**:

- **Block erzeugen (B)**: Objekte markieren, `B` drücken, Basispunkt klicken,
  Namen und Speicherort wählen.
- **Block/Gerät einfügen (I)** öffnet den Block-Browser. Doppelklick auf einen Block
  setzt ihn in die Zeichnung. Die Blöcke sind normale Dateien (`*.katieblock`) in
  den Ordnern, die der Browser anzeigt (auch der Projektordner `Bloecke`).
- **Blockliste (BL)**, **Block auflösen (X)** zerlegt einen Block wieder.
- **Block als Datei speichern / aus Datei laden**.
- **Attribut definieren (ATTDEF)**: ein Textfeld im Symbol, dessen Wert je
  eingefügtem Block verschieden ist. Markiere es zusammen mit der Symbolgeometrie
  und erzeuge den Block. Beim Einfügen fragt KatieCAD die Werte ab.
  **Attribute bearbeiten (ATTEDIT)** ändert sie später.

## 8. Elektro: einen Schaltplan zeichnen

Alle Werkzeuge stehen im Menü **Elektro** und in der Werkzeugleiste.

**Automatische Layer:** Elektro-Objekte landen nicht auf Layer 0, sondern automatisch auf eigenen Layern, die KatieCAD bei Bedarf anlegt: **E_DEVICES** (Geräte), **E_LINES** (Leitungen, Verbindungen, Querverweise), **E_CABLE** (Kabeldefinitionen), **E_CLAMPS** (Klemmen) und **E_PIN** (einzelne Pins, solange sie nicht in einem Gerät zusammengefügt sind; im Gerät gehören sie zu E_DEVICES). Bereits vorhandene Objekte bleiben unverändert; die Layer lassen sich wie alle anderen ein-/ausblenden und umfärben.

### Bausteine

| Baustein | Zweck |
|---|---|
| **Pin** (PIN) | Anschlusspunkt mit Bezeichnung (z. B. `1`, `2`, `A1`). Hier enden Leitungen. |
| **Elektro-Maske** (MASKE) | Beschriftungsfeld eines Geräts: **IND** (Betriebsmittelkennzeichen, z. B. `K1`), **TYP**, **PER** (Benennung). **REF** füllt sich selbst. |
| **Verbindung** (VERBINDUNG) | Ecke, T-Stück oder Kreuzung. Im Dialog hakst du die Richtungen (Nord/West/Ost/Süd) an, in denen eine Leitung angeschlossen wird (mindestens 2), und wählst optional „Mit Punkt“ (= elektrisch verbunden). Der Punkt geht auch beim T-Stück mit 3 Richtungen; eine Kreuzung mit 4 Richtungen ohne Punkt ist nur eine Überkreuzung. |
| **Querverweis** (QV) | Pfeil, der einen Stromweg zu einem anderen Blatt weiterführt. Gleicher Text = zusammengehörig. |
| **Klemme** (KLEMME) | Reihenklemme mit zwei Anschlüssen (oben/unten) und den Feldern IND (Klemmleiste), TYP, PER, NUM (Nummer). |
| **Kabel** (KABEL) | Waagerechte Linie mit Beschriftung. Wo eine senkrechte Leitung sie kreuzt, entsteht automatisch ein Aderstrich (L1, L2, L3, N, PE …), die Bezeichnung ist änderbar. |
| **Koordinatenfeld** (FELD) | Spalten-/Zeilenraster des Blatts, damit Verweise als „Blatt/Spalte/Zeile“ angegeben werden. Im Dialog wählst du **DIN A4** (287 × 164 mm, 6 × 4) oder **DIN A3** (395 × 252,59 mm, 8 × 5) oder gibst eigene Werte ein. |

### Fertige Symbole

Im Block-Browser (**Blöcke > Block/Gerät einfügen**, Taste `I`) gibt es den Eintrag
**Symbole** (die Symbolbibliothek) mit Grundsymbolen (Kontakte, Taster, Sicherungen,
Schutzschalter, Spulen, Motoren, Bauteile, Messgeräte …). Doppelklick setzt ein
Symbol; Maske und Pins sind schon vorbereitet. Die Liste steht in
`symbols/README.md`.

### Ein Gerät anlegen

1. Zeichne das Symbol (Linien, Rechtecke …) und setze die **Pins** daran.
2. Setze eine **Elektro-Maske** daneben. Wähle die Art: **Hauptgerät** (z. B. Spule)
   oder **Hilfsgerät** (z. B. Hilfskontakt).
3. Markiere Symbol, Pins und Maske **zusammen**. Der Auswahlrahmen muss auch den
   Text der Maske ganz enthalten, denn der liegt links über dem Anker der Maske.
4. **Elektro > Gerät aus Auswahl erstellen…**, Basispunkt klicken, Namen vergeben,
   Haupt-/Hilfsgerät bestätigen. Das Gerät liegt danach als Block vor und wird
   beim Speichern als Datei im Block-Ordner abgelegt.
5. Platzieren kannst du es mit **Block/Gerät einfügen (I)** oder **Elektro > Gerät aus
   Datei laden…**. Beim Einfügen fragt das Programm IND, TYP, PER und die Pin-Namen
   ab.

Geräte mit **gleichem IND** gehören zusammen: Das Hauptgerät zeigt in REF die
Blätter aller Hilfsgeräte, ein Hilfsgerät zeigt das Hauptgerät. So bekommst du zum
Beispiel eine Spule `K1` auf Blatt 3 und ihre Kontakte `K1` auf den Blättern 5 und 6.
Dabei darf jedes Gerät nur **eine** Maske enthalten. Bei Geräten mit mehreren
Kontakten legst du jeden Kontakt als eigenes Hilfsgerät an.

### Leitungen

- **Automatisch:** Liegen zwei Anschlusspunkte (Pins, Verbindungen, Klemmen,
  Querverweise) genau waagerecht oder senkrecht untereinander und passen ihre
  Richtungen, entsteht die rote Leitung von selbst. Sie verschwindet wieder, wenn
  du einen der Punkte wegnimmst.
- **Von Hand:** Werkzeug **Leitung zeichnen (LEITUNG)**, dann nacheinander zwei
  Anschlüsse anklicken.
- Setzt du einen Pin, ein Gerät, eine Klemme oder eine Verbindung **auf** eine
  bestehende Leitung, wird die Leitung dort unterbrochen und angeschlossen.
- Doppelklick auf eine Verbindung ändert die Richtungen und den Punkt.

### Blattübergreifend: Querverweise

**Kette über mehrere Blätter:** Du musst nicht `L1.1`, `L1.2` … schreiben. Mit gleichem Namen zeigt ein *abgehender* Pfeil auf den *ankommenden* Pfeil auf dem **nächsten** Blatt, ein *ankommender* auf den *abgehenden* des **vorherigen** Blattes (links nach rechts, in Blattreihenfolge). So läuft `L1` von Blatt 1 über 2 und 3 nach 4, und jeder Pfeil nennt nur seinen Nachbarn. Gibt es in dieser Richtung keinen passenden Partner, werden wie bisher alle anderen Stellen mit diesem Namen angezeigt.

Setze am Ende einer Leitung einen **Querverweis** (Art *abgehend* oder
*ankommend*, Richtung, Text, z. B. `L1`) und auf dem anderen Blatt einen mit
gleichem Text. Das Ziel (Blatt/Spalte/Zeile) erscheint automatisch. Für die Listen
verfolgt KatieCAD den Strompfad über solche Paare hinweg, wenn es genau einen
abgehenden und mindestens einen ankommenden Pfeil mit demselben Text gibt. Ein
Potential wie `L1`, das an vielen Stellen vorkommt, bleibt ein Endpunkt.

**Texte des Querverweises:** Bezeichnung (z. B. `L1`) und Zielangabe (z. B. „(Blatt 6/1/D)“) stehen standardmäßig in einer Zeile nebeneinander und haben Standardhöhen von 2,5 mm und 1,5 mm. Im Querverweis-Dialog (Doppelklick) stellst du beide Höhen getrennt ein. Beide Texte lassen sich außerdem an ihrem gelben Griff verschieben. Mit **Textpositionen zurücksetzen** im Dialog stehen sie wieder in der Standardlage.

**Texte frei verschieben:** Auch bei Klemmen, Masken (IND/TYP/PER/REF), Kabeln, Pins und Geräteblöcken lassen sich die Beschriftungen verschieben. Markiere das Objekt und ziehe den gelben Griff am jeweiligen Text. Bei einem eingefügten Gerät gilt die Verschiebung nur für dieses eine Exemplar. Im Rechtsklickmenü setzt **Textpositionen zurücksetzen** die Texte wieder in die Standardlage. Die Klemmennummer (NUM) ist seit 1.0.3 mit 1,75 mm besser lesbar.

### Klemmen und Kabel

- Setze die Klemmen nebeneinander. **NUM** zählt beim nächsten Setzen selbst hoch.
  Die Klemmleiste (IND) musst du nur an der ersten Klemme einer Reihe eintragen;
  die Klemmen rechts davon in derselben Reihe übernehmen sie.
- Das **Kabel** setzt du mit zwei Klicks (Anfang, Ende) quer über die senkrechten
  Leitungen. Das Ende lässt sich später am Griff verlängern. CAB ist die Kennung des
  Kabels (z. B. `W1`).

## 9. Dokumentation erzeugen

**Projekt > Dokumentation erzeugen / aktualisieren…** erstellt als normale
Blätter im Projekt, wahlweise in **DIN A4** oder **DIN A3** (Auswahl im Dialog; bei A3 werden Flächen, Texte und Zeilenhöhen passend skaliert):

- **Deckblatt** und **Inhaltsverzeichnis** (vor den Zeichnungsblättern)
- **Geräteliste**, **Klemmenplan** und **Kabelplan** (dahinter)

Im Dialog wählst du die gewünschten Blätter, die Schriftkopf-Vorlage und die
Projektdaten (Anlage, Kunde, Auftragsnummer, Zeichnungsnummer, Firma, gezeichnet /
geprüft von, Revision, Datum) und das Blattformat. Die Berichtsblätter werden bei jedem Lauf komplett
neu erzeugt. Handänderungen darin gehen verloren, deine Zeichnungsblätter bleiben
unverändert.

- Die Listen entstehen aus den Masken (IND/TYP/PER), den Klemmen, den Kabeln und
  den Leitungen dazwischen. Fundstellen stehen als Blatt/Spalte/Zeile.
- **Listen als CSV exportieren…** schreibt dieselben Tabellen für Excel
  (Semikolon-getrennt, UTF-8).
- **Spalten anpassen:** Kopiere `report_templates/geraete.example.json` und
  benenne sie zu `geraete.json`, `klemmen.json`, `kabel.json` oder `inhalt.json` um.
  Mehr dazu in `report_templates/README.md`.

## 10. Import und Export

- **Datei > Import DXF… / Import DWG…** liest fremde Zeichnungen ein, **Export DXF… / Export DWG…**
  schreibt sie. DXF geht direkt. DWG-Import funktioniert ohne Zusatzprogramm (eingebautes `ezdwg`). Für schwierige Dateien kannst du
  optional den kostenlosen **ODA File Converter** (opendesign.com/guestfiles/oda_file_converter) installieren;
  KatieCAD nutzt ihn dann automatisch (Neustart nötig) und liest genauer. **Export DWG** braucht diesen Konverter, **Export DXF** nicht.
- **Datei > Export DXF…** schreibt die Zeichnung als DXF.
- PDF: siehe Abschnitt 6.

## 11. Tastenkürzel

| Taste | Funktion |
|---|---|
| Strg+S | Speichern (im Projekt ohne Nachfrage) |
| Strg+P | Drucken |
| Strg+Z / Strg+Y | Rückgängig / Wiederholen |
| Strg+C / Strg+X / Strg+V | Kopieren / Ausschneiden / Einfügen |
| Strg+Umschalt+C | Kopieren mit Basispunkt |
| Strg+D | Duplizieren (mit Versatz) |
| Strg+A | Alles markieren |
| Entf | Auswahl löschen |
| ESC | Abbrechen / Auswahl aufheben |
| F2 | Blatt-Eigenschaften (Name, Einbauort) |
| F3 / F7 / F8 / F9 | Objektfang / Raster anzeigen / Ortho / Rasterfang |
| F4 | Seitenleiste ein-/ausblenden |
| G | Alles anzeigen (Zoom Grenzen) |
| B / I / BL / X | Block erzeugen / einfügen / Blockliste / auflösen (in der Eingabezeile) |

Auf dem Mac gilt Cmd statt Strg.

## 12. Tipps und häufige Fragen

- **„Gerät aus Auswahl erstellen“ meldet, die Maske fehle:** Die Maske muss mit
  markiert sein. Ziehe den Rahmen von links nach rechts so groß, dass ihr Text ganz
  darin liegt. Steckt die Maske schon in einem platzierten Block, löse ihn zuerst
  auf (X).
- **Eine Leitung entsteht nicht:** Die Anschlusspunkte müssen exakt untereinander
  oder nebeneinander liegen und ihre Richtungen müssen passen. Schalte den
  Objektfang (F3) ein, um genau zu treffen.
- **In den Listen steht „→ L1“ o. Ä.:** Der Weg endet an einem Querverweis ohne
  eindeutiges Gegenstück (oder an einem Potential wie L1). Das ist gewollt.
- **Klemmen erscheinen ohne Klemmleiste:** Trage IND an der ersten Klemme der Reihe
  ein; die rechts daneben übernehmen sie.
- **Nur ein Dialog gleichzeitig:** Öffnest du einen neuen Dialog, schließt der alte.
- **Sicherung:** Zeichnungsblätter werden beim Blattwechsel automatisch gespeichert.
  Mit Strg+S sicherst du das Projekt jederzeit.

## Projekt prüfen / Kontaktspiegel

**Projekt › Projekt prüfen…** prüft alle Zeichnungsblätter: doppelte Hauptgeräte und Kabel, Hilfsteile ohne Hauptgerät,
doppelte Klemmen, Querverweise mit mehr als zwei Vorkommen / ohne Gegenstück / mit gleicher Pfeilart, offene Klemmenanschlüsse.
Doppelklick auf einen Befund springt zur Stelle. Querverweise, die bewusst ohne Gegenstück bleiben (Einspeisung, Übergabe),
im Querverweis-Dialog mit **Übergabe / extern** markieren.

**Kontaktspiegel:** Im Geräte-Dialog (Attribute bearbeiten bzw. Betriebsmittelmaske) unter *Darstellung* wählen:
Referenzliste, Kontaktspiegel rechts vom Symbol oder – für Relais – unterhalb. Die Kontakte werden aus den Hilfsteilen mit
gleichem Kennzeichen ermittelt; Schließer/Öffner/Wechsler aus den Pin-Bezeichnungen (13/14, 21/22, 11/12/14 …).

**Kontaktspiegel verschieben:** Das Gerät markieren – am Kontaktspiegel erscheint ein gelber Griff (oben links). Ziehen verschiebt den Spiegel frei; die Lage bleibt relativ zum Gerät erhalten. Beim Wechsel der Darstellung wird die Position zurückgesetzt.

## Eigenschaften (Strg+1)
Bearbeiten › Eigenschaften öffnet ein Fenster für die aktuelle Auswahl – auch gemischt (Linien, Texte, Symbole …): Layer, Farbe (oder „Von Layer“), Linientyp, Linienstärke und – sobald Texte dabei sind – Texthöhe, Winkel und Schriftart. Unterschiedliche Werte zeigt das Feld als *VERSCHIEDEN*; eine Änderung gilt sofort für alle gewählten Objekte.

## Skalieren und Spiegeln
**Bearbeiten › Skalieren** (Befehl `SKALIEREN`/`SC`, auch im Rechtsklickmenü): Objekte wählen, Enter, Basispunkt klicken, Faktor eingeben (z. B. `2` oder `0,5`). Blöcke werden mit ihrer Größe skaliert; fest dimensionierte Elektro-Elemente (Verbindungen, Querverweise, Masken, Klemmen) behalten ihre Größe und wandern nur an die neue Position.

**Bearbeiten › Spiegeln** (Befehl `SPIEGELN`/`MI`, auch im Rechtsklickmenü): Objekte wählen, Enter, zwei Punkte der Spiegelachse klicken (Vorschau live), dann entscheiden, ob die Originale gelöscht werden. Texte bleiben lesbar (nicht gespiegelt), Blöcke inklusive Pins und Beschriftung werden korrekt gespiegelt und bleiben Geräte.

## Projekt als eine DXF-Datei
**Projekt › Projekt als eine DXF exportieren…** wertet alle Blätter wie beim Drucken aus (Layout mit Rahmen, Schriftfeld und Viewports) und legt sie in einer DXF-Datei nebeneinander ab: 4 Blätter pro Zeile, dann eine neue Zeile. Jedes Blatt liegt auf einem eigenen Layer (`Blatt_01` …), dazu `Blattgrenze` und `Blattnamen`.

## Info-Fenster und Log
Hilfe › Info zeigt Logo, Version und Lizenz. Mit **Lizenz** öffnest du den Lizenztext, mit **Log** öffnet sich die Log-Datei (`katiecad-log.txt` im KatieCAD-Einstellungsordner) im Standard-Editor – hilfreich bei Fehlermeldungen. Die Datei der vorherigen Sitzung bleibt als `katiecad-log.txt.old` erhalten.

## Einbauort (Blatt-Eigenschaften)
Mit **F2**, Doppelklick auf ein Blatt oder Rechtsklick > *Blatt-Eigenschaften…* legst du Blattname und **Einbauort** (z. B. „Verteiler UV1“) fest. Der Einbauort gilt automatisch für alle Objekte auf dem Blatt und wird nicht in die Objekte kopiert: Ändert man ihn, ziehen Schriftfeld und Listen sofort nach. Im Schriftkopf füllt ihn ein Attribut mit dem Tag `EINBAUORT` (englisch `PLACE`). In der Geräte-, Klemmen- und Kabelliste erscheint die Spalte *Einbauort* (nur, wenn mindestens ein Blatt einen hat); gleiche Betriebsmittelkennzeichen an verschiedenen Einbauorten zählen als verschiedene Geräte. Berichtsblätter haben keinen Einbauort.

## Klemmenplan: Brücken
Spaltenfolge: Klemmleiste, Einbauort, Typ, **Anschluss oben, Klemme (NUM), Brücke, Anschluss unten**, Blatt/Spalte/Zeile. Klemmen derselben Leiste, die du oben oder unten direkt miteinander verbindest, gelten als Brücke: In der Spalte *Brücke* erscheint eine Linie mit Punkten an den verbundenen Klemmen (überlappende Brücken liegen in getrennten Bahnen). Das Ziel der Verbindung steht dann nur in der ersten Klemme der Brücke, bei den übrigen bleibt die Zelle leer. Die Spalte erscheint nur, wenn mindestens eine Brücke vorhanden ist.

Hängt eine Klemme an einer Potentialschiene (z. B. PE oder N), steht in „Anschluss oben/unten“ nur der Potentialname. Voraussetzung: Im Netz gibt es einen freien Anschlusspunkt oder Querverweis, der genauso heißt wie die Klemme (NUM).

Im Klemmenplan beginnt jede Klemmleiste (je Einbauort) auf einem eigenen Blatt; lange Leisten laufen auf Folgeblätter.
Die Klemmenplan-Blätter heißen nach ihrer Klemmleiste, z. B. „Klemmenplan X1“ (bei Einbauort zuerst: „Klemmenplan +1 -X1“, bei mehreren Blättern einer Leiste: „… X1 2/3“). Das gilt auch im Inhaltsverzeichnis und im Schriftfeld.

Im Dialog **Blatt-Eigenschaften (F2)** legst du außerdem die **Art des Blatts** (Schaltplan, Gestellansicht, Übersicht, Layout oder eigener Text) und eine **Beschreibung** fest. Beides erscheint im Inhaltsverzeichnis; ohne Eintrag gilt „Schaltplan“ bzw. bleibt die Beschreibung leer.

## PDF importieren
**Datei > PDF importieren…** liest eine Seite eines PDFs als Vektorgeometrie ein (nicht als Bild). Du wählst die Seite und einen **Maßstabsfaktor** (1 = Papiergröße; für einen Plot 1:50 gibst du 50 ein). Enthält das PDF Layer (wie sie AutoCAD oder BricsCAD mit „Layer in PDF übernehmen“ schreiben), werden daraus KatieCAD-Layer mit denselben Namen; im PDF ausgeblendete Layer bleiben ausgeblendet. Ohne Layer landet alles auf dem Layer „PDF“. Übernommen werden Linien, Polylinien, Rechtecke, Kurven, Kreise, Texte und gefüllte Flächen. Nicht übernommen werden Rasterbilder (z. B. gescannte PDFs), Schraffurmuster, Strichlinientypen und Beschnitt. Texte kommen teils als einzelne Textstücke an. Der Import nutzt nur frei lizenzierte Bibliotheken (pypdf), die MIT-Lizenz von KatieCAD bleibt unverändert. Zum Ausprobieren: `pip install pypdf` (steht auch in `requirements.txt`).

## Bild importieren
**Datei > Bild importieren…** fügt ein Foto oder eine Grafik (PNG, JPG, BMP, GIF, TIFF) ein. Das Bild wird in der Zeichnung gespeichert, die Originaldatei wird also nicht mehr gebraucht. Die Größe änderst du am gelben Eckgriff oder mit **Skalieren**; verschieben, drehen und spiegeln gehen wie bei anderen Objekten. Große Bilder werden auf höchstens 2400 Pixel Kantenlänge verkleinert. Im PDF-Export erscheint das Bild, beim DXF-Export wird die Bilddatei neben die DXF-Datei geschrieben. Der Projekt-DXF-Export enthält keine Bilder.

Hinweis: Beim PDF-Export (Drucken als PDF) werden die KatieCAD-Layer als PDF-Layer mitgeschrieben. Solche PDFs kannst du in PDF-Programmen layerweise ein- und ausblenden und in KatieCAD wieder mit denselben Layernamen importieren.
