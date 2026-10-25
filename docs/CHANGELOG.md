# Änderungen

## 1.0.2
- Einbauort pro Blatt (Blatt-Eigenschaften, F2): erscheint im Schriftfeld (`EINBAUORT` / `PLACE`) und unterscheidet Geräte-, Klemmen- und Kabellisten
- Menü: „Block/Gerät einfügen“ steht über „Block erzeugen“
- Fix: Maßtext der Bemaßung stand versetzt und ist jetzt zentriert über der Maßlinie
- Radius-/Durchmesser-Bemaßung klarer benannt (DR / DD)
- Klemmenplan: Spalte „Klemme (NUM)“ zwischen „Anschluss oben“ und „Anschluss unten“, neue Spalte „Brücke“ mit Grafik für verbundene Klemmen (nur erste Klemme einer Brücke zeigt das Ziel)
- Klemmenplan: an Potentialschienen (PE, N, …) steht nur noch der Potentialname statt aller Klemmen
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
