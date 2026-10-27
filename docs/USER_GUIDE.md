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

**Find and replace (Ctrl+F, Edit > Find and replace, command `FIND`):** enter the search text and the new text and choose the scope *Current sheet* or *Whole project*. KatieCAD lists all hits with sheet, object type and field and shows the new text next to it. It searches texts, dimension texts, cross references, masks (IND/TYP/PER ...), terminals, cables, pins and block attributes (so also the designation of devices). **Double-click a hit** to jump to the object: KatieCAD opens the sheet if needed, selects the object and zooms to it; the search window stays open and moves aside. Optional: match case, whole words only. *Replace selected* changes only the highlighted rows, *Replace all* all of them. Changes in the open sheet can be undone with Ctrl+Z; changes in other sheets are saved immediately and cannot be undone there (KatieCAD asks first).

**Match properties (Edit > Match properties, command `MA`):** click the source object first, then the target objects one after another. Layer, colour, line type and line weight are copied; for texts also height and font, for hatches angle and spacing. ESC or right-click ends.

**Purge layers:** in the layer window ("Layers...") **Purge** deletes all layers no object uses - in a project across all sheets (also layouts and blocks). Layer 0 and the active layer stay. KatieCAD asks first with the list. Ctrl+Z undoes it only for the open sheet; the other sheets are saved immediately.

**Hatching like AutoCAD:** with nothing selected, choose Insert > Hatch, set pattern, spacing and angle, then click straight into an enclosed area. KatieCAD finds the smallest region around the click point (lines may cross; circles, rectangles and polylines count too) and hatches it. Click several areas one after another; ESC or right-click ends. If a closed boundary is already selected, that one is hatched as before.

**Stretch with a preselection:** if you selected objects beforehand with a crossing window (right-to-left), **Stretch** (`STR`) jumps straight to the base point - no second window needed. Only the selected objects are stretched. With another kind of preselection (e.g. single click) the selection is kept and you only drag the window.

## 5. Projects and sheets

A **project** is a folder with a project file (`*.katieprj`), one file per sheet
(`Blatt_001.cadjson` …) and a folder `Bloecke` for block files.

**Project** menu:

- **Create project…**: choose a name and location. The first sheet is created.
- **Open / save / close / rename… / delete project…**
- **New sheet, duplicate sheet, sheet properties (F2: name and installation location), delete sheet**
- **Print sheets / as PDF…**
- **Create / update documentation…** and **Export lists as CSV…** (see section 9)

In the **side bar**, one click switches the sheet. The current sheet is saved
automatically. A double click renames a sheet. Select several sheets with **Ctrl** or **Shift** + click
to move them together with the arrow buttons or delete them with "−" (while several
sheets are selected, the current sheet stays open). Undo is kept per sheet.

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
- **Insert block/device (I)** opens the block browser. A double click on a block places it
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

**Automatic layers:** electrical objects no longer go to layer 0 but to layers KatieCAD creates on demand: **E_DEVICES** (devices), **E_LINES** (wires, junctions, cross references), **E_CABLE** (cable definitions), **E_CLAMPS** (terminals) and **E_PIN** (single pins as long as they are not combined into a device; inside a device they belong to E_DEVICES). Existing objects stay unchanged; the layers can be hidden or recoloured like any other.

### Building blocks

| Element | Purpose |
|---|---|
| **Pin** (PIN) | Connection point with a label (e.g. `1`, `2`, `A1`). Wires end here. |
| **Electrical mask** (MASKE) | Label field of a device: **IND** (equipment identifier, e.g. `K1`), **TYP** (type), **PER** (description). **REF** fills itself in. |
| **Junction** (VERBINDUNG) | Corner, T-piece or crossing. In the dialog tick the directions (North/West/East/South) that get a wire connection (at least 2) and optionally "With dot" (= electrically connected). The dot also works for a T-piece with 3 directions; a 4-direction crossing without a dot is only a wire crossing. |
| **Cross reference** (QV) | Arrow that continues a current path on another sheet. Same text = belongs together. |
| **Terminal** (KLEMME) | Terminal block with two connections (top/bottom) and the fields IND (terminal strip), TYP, PER, NUM (number). |
| **Cable** (KABEL) | Horizontal line with a label. Where a vertical wire crosses it, a core marker (L1, L2, L3, N, PE …) appears automatically; the designation can be changed. |
| **Coordinate field** (FELD) | Column/row grid of the sheet, so that references can be given as "sheet/column/row". In the dialog choose **DIN A4** (287 × 164 mm, 6 × 4), **DIN A3** (395 × 252.59 mm, 8 × 5) or enter your own values. |

### Ready-made symbols

The block browser (**Blocks > Insert block/device**, key `I`) contains an entry
**symbols** (the symbol library) with basic symbols (contacts, push buttons, fuses, breakers,
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
5. Place it with **Insert block/device (I)** or **Electrical > Load device from file…**.
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

**Chain over several sheets:** you do not need `L1.1`, `L1.2` ... With the same name an *outgoing* arrow points to the *incoming* arrow on the **next** sheet, an *incoming* one to the *outgoing* one on the **previous** sheet (left to right, in sheet order). So `L1` can run from sheet 1 over 2 and 3 to 4 and each arrow names only its neighbour. If there is no matching partner in that direction, all other places with this name are shown as before.

At the end of a wire, place a **cross reference** (type *outgoing* or *incoming*,
direction, text, e.g. `L1`) and place one with the same text on the other sheet. The
target (sheet/column/row) is shown automatically. For the lists, KatieCAD follows the
current path across such pairs when there is exactly one outgoing and at least one
incoming arrow with the same text. A potential such as `L1` that occurs in many
places stays an end point.

**Cross-reference texts:** the identifier (e.g. `L1`) and the target note (e.g. "(Sheet 6/1/D)") stand side by side on one line by default and have default heights of 2.5 mm and 1.5 mm. In the cross-reference dialog (double-click) you set both heights separately. Both texts can also be moved with their yellow grips. **Reset text positions** in the dialog puts them back to the default position.

**Moving texts freely:** The labels of terminals, masks (IND/TYP/PER/REF), cables, pins and device blocks can be moved as well. Select the object and drag the yellow grip at the text. For an inserted device the move applies to that one instance only. **Reset text positions** in the right-click menu puts the texts back to their default position. Since 1.0.3 the terminal number (NUM) is more readable at 1.75 mm.

### Terminals and cables

- Place the terminals side by side. **NUM** counts up by itself on the next
  placement. You only need to enter the terminal strip (IND) on the first terminal of
  a row; the terminals to its right in the same row take it over.
- Place the **cable** with two clicks (start, end) across the vertical wires. The end
  can be extended later with its grip. CAB is the identifier of the cable (e.g. `W1`).

## 9. Generating documentation

**Project > Create / update documentation…** creates ordinary sheets in the
project, in either **DIN A4** or **DIN A3** (chosen in the dialog; on A3 areas, texts and row heights are scaled to fit):

- **cover sheet** and **table of contents** (in front of the drawing sheets)
- **device list**, **terminal diagram** and **cable plan** (behind them)

In the dialog you choose the sheets, the title block template and the project data
(plant, customer, order number, drawing number, company, drawn / checked by,
revision, date) and the sheet format. The report sheets are rebuilt completely on every run. Manual
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
| F2 | Sheet properties (name, installation location) |
| F3 / F7 / F8 / F9 | Object snap / show grid / ortho / grid snap |
| F4 | Show / hide side bar |
| Ctrl+B | Open the block list (block selection) |
| Ctrl+F | Find and replace |
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

**Linux - menu bar:** on Linux KatieCAD draws its own menu bar (a click opens it; a click elsewhere, ESC or switching to another program closes it; F10 and the arrow keys work). To get the standard Tk menus start with `KATIECAD_NATIVE_MENU=1 python3 main.py`.

## Project check / contact mirror
**Project › Check project…** checks all drawing sheets: duplicate main devices and cables, auxiliary parts without a main device, duplicate terminals, cross references that occur more than twice / have no counterpart / use the same arrow type twice, and open terminal connections. Double-click a finding to jump to it. Mark cross references that intentionally have no counterpart (supply, handover) with **Handover / external** in the cross-reference dialog.

**Contact mirror:** In the device dialog (edit attributes or device mask) choose *Display*: reference list, contact mirror right of the symbol, or - for relays - below. The contacts are taken from the auxiliary parts with the same identifier; make/break/changeover is derived from the pin labels (13/14, 21/22, 11/12/14 ...).

**Moving the contact mirror:** Select the device - a yellow grip appears at the upper left of the mirror. Drag it to move the mirror freely; the position stays relative to the device. It is reset when the display mode is changed.

## Properties (Ctrl+1)
Edit › Properties opens a window for the current selection, also mixed (lines, texts, symbols ...): layer, colour (or "By layer"), linetype, line weight and - as soon as texts are included - text height, angle and font. Differing values show as *VARIES*; a change applies at once to all selected objects.

## Scale and mirror
**Edit › Scale** (command `SCALE`/`SC`, also in the right-click menu): select objects, Enter, pick the base point, enter the factor (e.g. `2` or `0.5`). Blocks are scaled with their size; fixed-size electrical elements (junctions, cross references, masks, terminals) keep their size and only move to the new position.

**Edit › Mirror** (command `MIRROR`/`MI`, also in the right-click menu): select objects, Enter, pick two points of the mirror line (live preview), then decide whether the originals are deleted. Texts stay readable (not mirrored); blocks including pins and labels are mirrored correctly and remain devices.

## Whole project as one DXF file
**Project › Export project as one DXF…** evaluates all sheets like printing (layout with frame, title block and viewports) and places them side by side in one DXF file: 4 sheets per row, then a new row. Every sheet is on its own layer (`Blatt_01` ...), plus `Blattgrenze` and `Blattnamen`.

## Info window and log
Help › About shows the logo, version and license. **License** opens the license text; **Log** opens the log file (`katiecad-log.txt` in the KatieCAD settings folder) in your default text editor – useful for error reports. The previous session's log is kept as `katiecad-log.txt.old`.

## Installation location (sheet properties)
Press **F2**, double-click a sheet or right-click > *Sheet properties…* to set the sheet name and its **installation location** (e.g. "Panel UV1"). It applies to every object on the sheet automatically and is not copied into the objects: change it and the title block and lists follow at once. In the title block an attribute with the tag `PLACE` (German `EINBAUORT`) shows it. The device, terminal and cable lists get a *Location* column (only if at least one sheet has a location); the same equipment identifier at different locations counts as different devices. Report sheets have no location.

Dimensions: **Insert > Radius dimension (DR)** and **Diameter dimension (DD)** - click a circle or arc, then the text position.

## Terminal diagram: bridges
Column order: terminal strip, location, type, **connection top, terminal (NUM), bridge, connection bottom**, sheet/column/row. Terminals of the same strip that you wire together on the top or bottom side count as a bridge: the *Bridge* column shows a line with dots at the connected terminals (overlapping bridges use separate lanes). The target then appears only on the first terminal of the bridge; the other cells stay empty. The column only appears if at least one bridge exists.

If a terminal sits on a potential rail (e.g. PE or N), "connection top/bottom" shows only the potential name. Requirement: the net contains a free connection point or cross reference named exactly like the terminal (NUM).

In the terminal diagram every terminal strip (per location) starts on its own sheet; long strips continue on following sheets.
The terminal diagram sheets are named after their terminal strip, e.g. "Klemmenplan X1" (with a location, placed first: "Klemmenplan +1 -X1"; several sheets for one strip: "... X1 2/3"). This also applies to the table of contents and the title block.

In **Sheet properties (F2)** you also set the **sheet type** (circuit diagram, panel layout, overview, layout or custom text) and a **description**. Both appear in the table of contents; without an entry the type is "Circuit diagram" and the description stays empty.

## Importing a PDF
**File > Import PDF...** reads one page of a PDF as vector geometry (not as a picture). Choose the page and a **scale factor** (1 = paper size; enter 50 for a 1:50 plot). If the PDF contains layers (as written by AutoCAD or BricsCAD with "include layer information"), they become KatieCAD layers with the same names; layers hidden in the PDF stay hidden. Without layers everything goes onto layer "PDF". Imported: lines, polylines, rectangles, curves, circles, text and solid fills. Not imported: raster images (e.g. scanned PDFs), hatch patterns, dash line types and clipping. Text sometimes arrives in fragments. The import only uses freely licensed libraries (pypdf); KatieCAD stays MIT-licensed. To try it from source: `pip install pypdf` (also in `requirements.txt`).

## Importing an image

Note: PDF export writes KatieCAD layers as PDF layers. You can toggle them in PDF viewers and re-import such a PDF into KatieCAD with the same layer names.
**File > Import image...** inserts a photo or graphic (PNG, JPG, BMP, GIF, TIFF). The image is stored inside the drawing, so the original file is no longer needed. Resize with the yellow corner grip or **Scale**; move, rotate and mirror work as for other objects. Large images are reduced to at most 2400 pixels on the long side. Images appear in PDF output; on DXF export the image file is written next to the DXF file. Project DXF export does not include images.
