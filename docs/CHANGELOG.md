# Änderungen

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
