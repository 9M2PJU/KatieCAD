# KatieCAD – Quick Guide (English)

> Deutsche Version: [ANLEITUNG.md](ANLEITUNG.md)

KatieCAD is a 2D CAD program with an electrical-engineering extension. This guide
shows where to find the basic functions. It is meant as a refresher if you have not
used the program for a while, or if you see it for the first time.

## Contents

1. [Starting](#1-starting)
2. [The window at a glance](#2-the-window-at-a-glance)
3. [Navigating, snapping, command line](#3-navigating-snapping-command-line)
4. [Drawing and editing](#4-drawing-and-editing)
5. [Projects and sheets](#5-projects-and-sheets)
6. [Model, layout, frame, printing](#6-model-layout-frame-printing)
7. [Blocks and attributes](#7-blocks-and-attributes)
8. [Electrical: drawing a schematic](#8-electrical-drawing-a-schematic)
9. [Generating documentation](#9-generating-documentation)
10. [Import and export](#10-import-and-export)
11. [Keyboard shortcuts](#11-keyboard-shortcuts)
12. [Tips and frequently asked questions](#12-tips-and-frequently-asked-questions)

---

## 1. Starting

```
python main.py
```

or `python -m katiecad`. Optionally install the extra packages with
`pip install -r requirements.txt` (needed for DXF/DWG import and DXF export). On Linux
you also need `python3-tk`.

Change the language in the **Language** menu (Deutsch / English). It is remembered.

## 2. The window at a glance

| Area | What it does |
|---|---|
| **Menu bar** | File, Project, Edit, Insert, View, Blocks, Electrical, Language, Help |
| **Toolbars** (top) | Drawing tools (Select, Line, Polyline, Circle, Arc, Rectangle, Text, Dimension, Trim, Break) and the electrical tools (Pin, Junction, Cross-ref, Mask, Terminal, Cable, …). Also layer, line type, line weight, colour, unit, scale and zoom. |
| **Side bar** (left, F4 shows/hides it) | Undo / Redo and the sheet list of the project |
| **Drawing area** | This is where you draw. The model is the drawing at 1:1, the layout is the paper sheet. |
| **Input line** | Below the drawing area. Type commands and coordinates here. |
| **Status bar** | Mouse coordinates, zoom, layer, selection, hints for the current tool and the switches for object snap, grid and ortho |

The hint in the status bar always tells you what the active tool expects next.
**ESC** cancels the current operation.

## 3. Navigating, snapping, command line

**With the mouse**

- Mouse wheel: zoom (towards the pointer).
- Hold the right mouse button and drag: pan the view.
- Right click without dragging (tool "Select"): context menu.
- Double click with the middle or right button: show everything (zoom extents).
  The **G** key does the same.

**Snapping and aids** (switches in the status bar, also available as keys)

| Key | Function |
|---|---|
| F3 | Object snap (endpoint, midpoint, centre, intersection, quadrant, perpendicular, nearest) |
| F7 | Show grid |
| F8 | Ortho (horizontal / vertical only) |
| F9 | Grid snap |

**Input line.** You can enter coordinates as `x,y` and type commands, for example
`L` (line), `K` (circle), `REC` (rectangle), `T` (text), `M` (move), `KO` or `CO`
(copy), `RO` (rotate), `AR` (array), `STR` (stretch), `TR` (trim), `BR` (break),
`ZG` (zoom extents), `U` (undo), `B` (create block), `I` (insert block),
`X` (explode block). The commands exist in German and in English.

## 4. Drawing and editing

1. Choose a tool (toolbar or **Insert** menu), click points in the drawing or type
   coordinates in the input line.
2. With the **Select** tool you select objects: click an object or drag a
   rectangle. *Left to right* selects only objects that lie completely inside the
   rectangle. *Right to left* selects everything the rectangle touches. New objects
   are added to the selection; **ESC** clears it.
3. Edit selected objects via the **Edit** menu: copy, cut, paste, duplicate, move,
   copy with base point, rotate, stretch, array, delete (Del).
4. Drag the yellow grips of a selected object to change it.
5. Double clicking an object opens its edit dialog (block attributes, pin, cross
   reference, junction, mask, terminal, cable, coordinate field …). On a viewport it
   activates the viewport.
6. **Undo** (Ctrl+Z) and **Redo** (Ctrl+Y) are also in the side bar.

More drawing aids: **dimensions** (including radius and diameter), **hatch
selection** (Insert menu), **layers** ("Layers…" button) and colour, line type and
line weight in the toolbar.

## 5. Projects and sheets

A **project** is a folder with a project file (`*.katieprj`), one file per sheet
(`Blatt_001.cadjson` …) and a folder `Bloecke` for block files.

**Project** menu:

- **Create project…**: choose a name and location. The first sheet is created.
- **Open / save / close / rename… / delete project…**
- **New sheet, duplicate sheet, rename sheet (F2), delete sheet**
- **Print sheets / as PDF…**
- **Create / update documentation…** and **Export lists as CSV…** (see section 9)

In the **side bar**, one click switches the sheet. The current sheet is saved
automatically. A double click renames a sheet. Undo is kept per sheet.

Without a project you work on a single drawing (**File** menu: New, Open, Save …).

## 6. Model, layout, frame, printing

- **Model** (**View** menu): the actual drawing in full size (mm).
- **Layout**: the paper sheet (e.g. DIN A4 landscape). It holds the frame, the title
  block and **viewports**, which are windows onto the model with their own scale.
  Create a viewport with **Insert > Place viewport**.
- **Insert > Frame + title block…**: places the sheet margin and a title block from a
  template. Your own title blocks are ordinary drawings (`*.cadjson`) in the folder
  `title_blocks/`; their origin is the lower right corner of the sheet frame.
  Fields such as `PAGE`, `PAGES`, `SHEET`, `PROJECT`, `DATE`, `SCALE`, `FORMAT` are
  filled in automatically. With **Project > Project properties…** you enter customer,
  drawn by / checked by, drawing number and the revision table (4 rows: index, change,
  name, date) once; they appear in the title blocks of all sheets. The title is made of
  customer, project name and sheet name; the paper format follows the layout format.
  The field names (e.g. `CUSTOMER`, `DRAWN`, `REV1_INDEX`) are listed in
  `title_blocks/README.md`.
- **Insert > Save drawing as title block template…** turns a drawing into a new
  template.
- **File > Print** (Ctrl+P) and **Project > Print sheets / as PDF…** create a PDF
  (several sheets in one file) or open the print preview.

## 7. Blocks and attributes

A **block** is a reusable group of objects (for example a symbol). **Blocks** menu:

- **Create block (B)**: select objects, press `B`, click the base point, choose a
  name and a save location.
- **Insert block (I)** opens the block browser. A double click on a block places it
  in the drawing. Blocks are ordinary files (`*.katieblock`) in the folders shown by
  the browser (including the project folder `Bloecke`).
- **Block list (BL)**; **Explode block (X)** breaks a block apart again.
- **Save block as file / load block from file**.
- **Define attribute (ATTDEF)**: a text field inside the symbol whose value differs
  per inserted block. Select it together with the symbol geometry and create the
  block. KatieCAD asks for the values on insertion. **Edit attributes (ATTEDIT)**
  changes them later.

## 8. Electrical: drawing a schematic

All tools are in the **Electrical** menu and in the toolbar.

### Building blocks

| Element | Purpose |
|---|---|
| **Pin** (PIN) | Connection point with a label (e.g. `1`, `2`, `A1`). Wires end here. |
| **Electrical mask** (MASKE) | Label field of a device: **IND** (equipment identifier, e.g. `K1`), **TYP** (type), **PER** (description). **REF** fills itself in. |
| **Junction** (VERBINDUNG) | Corner, T-piece or crossing. In the dialog tick the directions (North/West/East/South) that get a wire connection (at least 2) and optionally "With dot" (= electrically connected). The dot also works for a T-piece with 3 directions; a 4-direction crossing without a dot is only a wire crossing. |
| **Cross reference** (QV) | Arrow that continues a current path on another sheet. Same text = belongs together. |
| **Terminal** (KLEMME) | Terminal block with two connections (top/bottom) and the fields IND (terminal strip), TYP, PER, NUM (number). |
| **Cable** (KABEL) | Horizontal line with a label. Where a vertical wire crosses it, a core marker (L1, L2, L3, N, PE …) appears automatically; the designation can be changed. |
| **Coordinate field** (FELD) | Column/row grid of the sheet, so that references can be given as "sheet/column/row". |

### Ready-made symbols

The block browser (**Blocks > Insert block**, key `I`) contains an entry
**Symbol library** with basic symbols (contacts, push buttons, fuses, breakers,
coils, motors, components, meters …). A double click places a symbol; mask and pins
are already prepared. The list is in `symbols/README.md`.

### Creating a device

1. Draw the symbol (lines, rectangles …) and attach the **pins**.
2. Place an **electrical mask** next to it. Choose the kind: **main device** (e.g. a
   coil) or **auxiliary device** (e.g. an auxiliary contact).
3. Select symbol, pins and mask **together**. The selection rectangle must also
   contain the whole text of the mask, which lies to the left above the mask's anchor
   point.
4. **Electrical > Create device from selection…**, click the base point, enter a
   name and confirm main/auxiliary device. The device is now a block and is saved
   as a file in the block folder.
5. Place it with **Insert block (I)** or **Electrical > Load device from file…**.
   On insertion the program asks for IND, TYP, PER and the pin names.

Devices with the **same IND** belong together: the main device shows the sheets of
all auxiliary devices in REF, an auxiliary device shows the main device. This way you
get, for example, a coil `K1` on sheet 3 and its contacts `K1` on sheets 5 and 6.
Each device may contain only **one** mask. For devices with several contacts, create
each contact as its own auxiliary device.

### Wires

- **Automatic:** if two connection points (pins, junctions, terminals, cross
  references) lie exactly above each other or side by side and their directions
  match, the red wire appears by itself. It disappears again if you remove one of
  the points.
- **By hand:** tool **Draw wire (LEITUNG)**, then click two connections one after the
  other.
- If you place a pin, device, terminal or junction **on** an existing wire, the wire
  is interrupted there and connected.
- Double click a junction to change its directions and dot.

### Across sheets: cross references

At the end of a wire, place a **cross reference** (type *outgoing* or *incoming*,
direction, text, e.g. `L1`) and place one with the same text on the other sheet. The
target (sheet/column/row) is shown automatically. For the lists, KatieCAD follows the
current path across such pairs when there is exactly one outgoing and at least one
incoming arrow with the same text. A potential such as `L1` that occurs in many
places stays an end point.

### Terminals and cables

- Place the terminals side by side. **NUM** counts up by itself on the next
  placement. You only need to enter the terminal strip (IND) on the first terminal of
  a row; the terminals to its right in the same row take it over.
- Place the **cable** with two clicks (start, end) across the vertical wires. The end
  can be extended later with its grip. CAB is the identifier of the cable (e.g. `W1`).

## 9. Generating documentation

**Project > Create / update documentation…** creates ordinary A4 sheets in the
project:

- **cover sheet** and **table of contents** (in front of the drawing sheets)
- **device list**, **terminal diagram** and **cable plan** (behind them)

In the dialog you choose the sheets, the title block template and the project data
(plant, customer, order number, drawing number, company, drawn / checked by,
revision, date). The report sheets are rebuilt completely on every run. Manual
changes in them are lost; your drawing sheets stay untouched.

- The lists are built from the masks (IND/TYP/PER), terminals, cables and the wires
  between them. Locations are given as sheet/column/row.
- **Export lists as CSV…** writes the same tables for Excel (semicolon separated,
  UTF-8).
- **Customise columns:** copy `report_templates/geraete.example.json` and rename it
  to `geraete.json`, `klemmen.json`, `kabel.json` or `inhalt.json`. More in
  `report_templates/README.md`.

## 10. Import and export

- **File > Import DXF… / Import DWG…** reads foreign drawings, **Export DXF… / Export DWG…**
  writes them. DXF works directly. DWG import works without extra software (built-in `ezdwg`). For difficult files you can optionally
  install the free **ODA File Converter** (opendesign.com/guestfiles/oda_file_converter);
  KatieCAD then uses it automatically (restart required) and reads more accurately. **Export DWG** needs this converter, **Export DXF** does not.
- **File > Export DXF…** writes the drawing as DXF.
- PDF: see section 6.

## 11. Keyboard shortcuts

| Key | Function |
|---|---|
| Ctrl+S | Save (in a project without prompting) |
| Ctrl+P | Print |
| Ctrl+Z / Ctrl+Y | Undo / Redo |
| Ctrl+C / Ctrl+X / Ctrl+V | Copy / Cut / Paste |
| Ctrl+Shift+C | Copy with base point |
| Ctrl+D | Duplicate (with offset) |
| Ctrl+A | Select all |
| Del | Delete selection |
| ESC | Cancel / clear selection |
| F2 | Rename sheet |
| F3 / F7 / F8 / F9 | Object snap / show grid / ortho / grid snap |
| F4 | Show / hide side bar |
| G | Show everything (zoom extents) |
| B / I / BL / X | Create block / insert / block list / explode (in the input line) |

On the Mac, Cmd replaces Ctrl.

## 12. Tips and frequently asked questions

- **"Create device from selection" says the mask is missing:** the mask must be part
  of the selection. Drag the rectangle left to right and large enough to contain its
  whole text. If the mask is already inside a placed block, explode that block first
  (X).
- **A wire is not created:** the connection points must be exactly aligned and their
  directions must match. Switch on object snap (F3) to hit them precisely.
- **The lists show "→ L1" or similar:** the path ends at a cross reference without
  a unique counterpart (or at a potential such as L1). This is intended.
- **Terminals appear without a terminal strip:** enter IND on the first terminal of
  the row; the ones to its right take it over.
- **Only one dialog at a time:** opening a new dialog closes the previous one.
- **Safety:** drawing sheets are saved automatically when you switch sheets. Use
  Ctrl+S to save the project at any time.

## Projekt prüfen / Kontaktspiegel

**Projekt › Projekt prüfen…** prüft alle Zeichnungsblätter: doppelte Hauptgeräte und Kabel, Hilfsteile ohne Hauptgerät,
doppelte Klemmen, Querverweise mit mehr als zwei Vorkommen / ohne Gegenstück / mit gleicher Pfeilart, offene Klemmenanschlüsse.
Doppelklick auf einen Befund springt zur Stelle. Querverweise, die bewusst ohne Gegenstück bleiben (Einspeisung, Übergabe),
im Querverweis-Dialog mit **Übergabe / extern** markieren.

**Kontaktspiegel:** Im Geräte-Dialog (Attribute bearbeiten bzw. Betriebsmittelmaske) unter *Darstellung* wählen:
Referenzliste, Kontaktspiegel rechts vom Symbol oder – für Relais – unterhalb. Die Kontakte werden aus den Hilfsteilen mit
gleichem Kennzeichen ermittelt; Schließer/Öffner/Wechsler aus den Pin-Bezeichnungen (13/14, 21/22, 11/12/14 …).

