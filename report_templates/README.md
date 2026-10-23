Report templates (Berichtsvorlagen)
The documentation (Project > Create / update documentation...) builds a cover
sheet, a table of contents, a device list, a terminal diagram and a cable plan.
The columns of these tables can be changed without touching the program:
Copy `geraete.example.json` to `geraete.json` (same folder, or into a
`report_templates` folder inside your project folder - the project folder wins).
Edit it. Valid file names: `inhalt.json`, `geraete.json`, `klemmen.json`, `kabel.json`.
Run Create / update documentation again.
```json
{
  "spalten": [
    {"key": "pos",  "titel": "Pos.",  "breite": 6,  "ausrichtung": "r"},
    {"key": "ind",  "titel": "BMK",   "breite": 18, "ausrichtung": "l"},
    {"key": "typ",  "titel": "Typ",   "breite": 40, "ausrichtung": "l"}
  ],
  "textgroesse": 2.5,
  "zeilenhoehe": 6.0
}
```
`breite` is a relative weight; the columns always fill the full width.
`ausrichtung`: `l` (left), `r` (right) or `c` (centre).
`textgroesse` / `zeilenhoehe` in mm. Long cell contents are wrapped or shrunk.
A broken file is ignored (the built-in columns are used).
Available `key` values
Report	Keys
`inhalt` (table of contents)	`nr`, `name`, `beschreibung`, `typ`
`geraete` (device list)	`pos`, `ind`, `typ`, `per`, `anzahl`, `ort` (all locations)
`klemmen` (terminal diagram)	`leiste`, `num`, `typ`, `per`, `oben`, `unten`, `ort`
`kabel` (cable plan)	`cab`, `typ`, `ader`, `von`, `nach`, `ort`
`oben` / `unten` / `von` / `nach` list the targets as `Device:Pin` or
`Strip:Terminal`; if the path runs through a cable core, it is shown in
brackets, e.g. `K1:13 (W1/L1)`.
Notes
Title block: the report sheets use the title block template you choose in the
dialog. Tags filled automatically: `TITEL1` (report name), `TITEL2` (plant),
`TITEL3` (customer), `GEZEICHNET`/`DRAWN`, `GEPRUEFT`/`VERIFIED`,
`ZEICHNUNGSNUMMER`/`DRAWINGNUMBER`, `FIRMA`, `KUNDE`, `AUFTRAG`, `ANLAGE`,
`REVISION` and the page tags `PAGE`/`SEITE`, `PAGES`/`SEITEN`, `FORMAT`/`SIZE`.
The printable area is the A4 frame minus the height of the title block.
