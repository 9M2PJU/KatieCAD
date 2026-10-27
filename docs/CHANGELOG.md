# Änderungen

## 1.0.4
- Suchen und Ersetzen über das ganze Projekt (alle Blätter)
- Eigenschaften übertragen (Layer, Farbe, Linientyp, Stärke, Texthöhe) von einem Objekt auf andere
- Layerfenster: „Bereinigen“ löscht alle nicht verwendeten Layer

## 1.0.3
- Info-Fenster: Maskottchen links neben den Texten (Datei `KatieCAD_Maskottchen.png`)
- Info-Fenster lässt sich nur noch einmal öffnen (erneutes Öffnen holt das vorhandene nach vorn)
- Neues Tastenkürzel Strg+B: öffnet die Blockliste (Blockauswahl)
- Schriftkopf „Standard (eingebaut)“ entfernt (identisch mit „Example A3“); es gibt nur noch die Vorlagen aus dem Ordner title_blocks
- Linux: eigene Menüleiste ohne Grab statt der Tk-Menüleiste – aufgeklappte Menüs schließen sich bei Fokuswechsel, Klick daneben und ESC (Windows/macOS unverändert; alte Menüs mit `KATIECAD_NATIVE_MENU=1`)
- Querverweise: gleicher Name über mehrere Blätter wird als Kette aufgelöst (abgehend → nächstes Blatt, ankommend → vorheriges Blatt), `L1.1`/`L1.2` sind nicht mehr nötig
- Koordinatenfeld: Beschriftung um 0,1 mm kleiner (PDF-Druck wirkte dicker)
- Menü: „Stutzen“ und „Brechen“ stehen jetzt unter Bearbeiten statt unter Einfügen
- Schraffur wie in AutoCAD: ohne Auswahl direkt in einen umschlossenen Bereich klicken (kreuzende Linien erlaubt), mehrere Bereiche nacheinander
- Strecken: wurden Objekte vorher mit einem überkreuzenden Fenster markiert, entfällt das zweite Aufziehen; gestreckt werden nur die markierten Objekte
- Querverweis „abgehend West“ / „ankommend Ost“: Bezeichnung steht an der Pfeilspitze bzw. -basis, der Verweis dahinter
- Automatische Elektro-Layer: Geräte → E_DEVICES, Leitungen/Verbindungen/Querverweise → E_LINES, Kabel → E_CABLE, Klemmen → E_CLAMPS, einzelne Pins → E_PIN (statt Layer 0); Layer werden bei Bedarf angelegt
- Koordinatenfeld: Auswahl DIN A4 (6 × 4) oder DIN A3 (8 × 5, 395 × 252,59 mm) oder eigene Werte
- Querverweis: Texthöhen von Bezeichnung und Zielangabe einstellbar (Standard jetzt 2,5 / 1,5 mm), Texte per Griff verschiebbar, Position zurücksetzbar
- Dokumentation: Deckblatt, Inhaltsverzeichnis und Listen wahlweise in DIN A4 oder DIN A3 (Inhalte skaliert)
- Blattliste: mehrere Blätter markieren (Strg/Umschalt + Klick), gemeinsam verschieben und löschen
- Fix: „Dokumentation erzeugen“ zeigt Fehler jetzt in einem Fenster an und schreibt sie ins Log, statt still nichts zu tun
- Querverweis: Bezeichnung und Zielangabe stehen standardmäßig in einer Zeile nebeneinander
- Klemmen: Klemmennummer (NUM) von 1,0 auf 1,75 mm vergrößert
- Texte frei verschiebbar (gelbe Griffe) bei Klemmen, Masken, Kabeln, Pins und Geräteblöcken (je Exemplar); Rechtsklick › Textpositionen zurücksetzen
- Koordinatenfeld: Beschriftung bleibt im Druck innerhalb ihres Streifens

## 1.0.2
- Einbauort pro Blatt (Blatt-Eigenschaften, F2): erscheint im Schriftfeld (`EINBAUORT` / `PLACE`) und unterscheidet Geräte-, Klemmen- und Kabellisten
- Menü: „Block/Gerät einfügen“ steht über „Block erzeugen“
- Fix: Maßtext der Bemaßung stand versetzt und ist jetzt zentriert über der Maßlinie
- Radius-/Durchmesser-Bemaßung klarer benannt (DR / DD)
- Klemmenplan: Spalte „Klemme (NUM)“ zwischen „Anschluss oben“ und „Anschluss unten“, neue Spalte „Brücke“ mit Grafik für verbundene Klemmen (nur erste Klemme einer Brücke zeigt das Ziel)
- Klemmenplan: an Potentialschienen (PE, N, …) steht nur noch der Potentialname statt aller Klemmen
- Klemmenplan: jede Klemmleiste beginnt auf einem eigenen Blatt
- Klemmenplan-Blätter heißen „Klemmenplan <Klemmleiste>“ (z. B. „Klemmenplan X1“)
- Inhaltsverzeichnis: „Art“ und „Beschreibung“ sind jetzt Blatt-Eigenschaften (F2); Standard-Art bleibt „Schaltplan", der Kunde wird nicht mehr als Beschreibung verwendet
- Block-Browser: Symbolbibliothek erscheint nur noch einmal („Symbole“ / „symbols“); ein zweiter, älterer Eintrag „symbols“ wird ausgeblendet
- Fix Projektprüfung: Klemmen ohne eigene IND erben die Klemmleiste wie im Klemmenplan (keine falschen „mehrfach vergeben“-Fehler); gleiche Kennzeichen an verschiedenen Einbauorten gelten nicht als doppelt
- Info-Fenster: neuer Untertitel mit Bezug zur Elektrotechnik
- PDF-Import (Datei > PDF importieren…): Vektorlinien, Kreise, Text und Flächen, PDF-Layer werden zu KatieCAD-Layern (eigener Leser auf Basis von pypdf, BSD-Lizenz; die MIT-Lizenz bleibt unberührt)
- Bildimport (Datei > Bild importieren…): Bilder werden in der Zeichnung gespeichert, im PDF ausgegeben und beim DXF-Export als Datei neben die DXF geschrieben
- PDF-Export schreibt die KatieCAD-Layer als PDF-Layer (in Acrobat, Bluebeam, Browser-Viewern ein-/ausblendbar; wieder importierbar)
- Schraffur: Auswahlfeld (Linien/Vollfläche) mit Abstand und Winkel in einem Dialog statt Texteingabe
- Info-Fenster kompakter, passt sich dem Inhalt an
- Info-Fenster: Log-Button öffnet die Log-Datei im Editor (keine Reiter mehr)

## 1.0.1
- Kontaktspiegel für Hauptgeräte (rechts neben dem Symbol oder unter dem Relais), frei verschiebbar
- Projektprüfung: doppelte Geräte, Querverweise (mit „extern“), Klemmen, offene Anschlüsse
- Eigenschaftenfenster (Strg+1) für gemischte Auswahlen, auch im Rechtsklickmenü
- Skalieren und Spiegeln von Objekten, Blöcken und Geräten
- Ganzes Projekt als eine DXF-Datei exportieren (4 Blätter pro Zeile)
- Infofenster mit Änderungsprotokoll und Programmprotokoll
- Fix: Kabel gingen beim Blattwechsel verloren
- Fix: Rechtsklickmenü unter Linux/Wayland, Logo im Infofenster unter Linux
- Fix: macOS-Info zeigt die richtige Version

## 1.0.0
- Erstes Release: 2D-CAD, Blöcke, Projekte mit Blättern, Schaltpläne, Querverweise, Klemmen, Kabel,
  Reports, Schriftfeld-Automatik, DXF/DWG-Import und -Export, Installer für Windows, Linux und macOS
