# Changes

## 1.1.0
- Find and replace across the whole project (all sheets); double-click a hit to jump to the object
- Match properties (layer, colour, line type, weight, text height) from one object to others
- Layer window: "Purge" deletes all unused layers (across all sheets in a project)
- Measure between two points (command `MEASURE` / `DI`): distance, dX, dY, angle
- Fillet (`FILLET` / `F`) and chamfer (`CHAMFER`) at the corner of two lines
- New elements ellipse and spline with their own drawing tools (Insert menu, toolbar, commands `ELLIPSE`, `SPLINE`), grips, rotate/scale/mirror, stretch, save/load, DXF export as polyline
- Angle dimension from 3 points or 2 lines (commands `ANGULAR`, `WINKELLINIEN`), grips, scale/mirror/rotate
- Fix: a rectangle was distorted when rotated by arbitrary angles (only two corners were rotated). It now becomes a polyline; in 90° steps it stays a rectangle
- Fillet and chamfer also by clicking rectangles and polylines (corner = that corner only, edge = all corners)
- Offset (`OFFSET` / `O`) for lines, circles, arcs, rectangles and polylines
- Quick select (`QS`) by object type, layer, colour and line type
- Chain dimension (`KETTE`)
- New reports: connection list, parts list (with parts catalogue for manufacturer, order number, description), cross reference list, potential overview, connector overview, label list, revision overview (all also as CSV)
- Project > Parts catalogue...; Project > Number devices automatically (`NUMMERIEREN`)
- Toolbar with icons instead of texts: drawing tools in purple, electrical tools in red; the name appears as a tooltip when the mouse rests on the icon; the active tool is highlighted (without Pillow the texts remain)
- Find and replace as an icon in the toolbar
- "Save block to file" and "Save device to file" merged into one entry "Save block/device to file..." (Blocks menu)
- New symbol category "10 PLC": digital/analogue input and output modules, CPU and single channels; each carries the invisible attribute `SPS` (CPU/DI/DO/AI/AO) and the channel address as pin name - basis for the later PLC list
- PLC: labels of the channel pins now sit to the left of the connection line; extra fields (invisible attributes) controller `STATION`, slot `PLATZ`, per channel symbol `VPn_SYM` and comment `VPn_KOM`
- New **PLC list** (I/O list: controller, module, slot, type, address, data type, symbol, comment, connection, location), also as CSV
- New electrical tool **Function text** (`FTEXT`): multi-line text on the layer "F-Text"; the device list and the terminal diagram show it at the far right in the column "Function" for all devices/terminals behind the insertion point
- "Load device from file..." (Electrical) replaced by "Load block/device from file..." in the Blocks menu (loads the file into the block library)
- Zoom +, Zoom -, Zoom extents and Reset as icons (magnifiers, circular arrows) in the toolbar; the label "Electrical:" is red
- Blocks menu: entry "Block list..." removed (same function as "Insert block/device"; Ctrl+B and `BL` stay)
- A cross reference marked "Handover / external" points nowhere and is never targeted: the same text (e.g. `L1`) can be used any number of times, no `L1.1`, `L2.1` ...
- Change length (`LAENGE`): click a line end, then click the new end or type `+5` / `-5` / `=50`; toolbar icon
- Align (left, right, top, bottom, centre horizontally/vertically) in the Edit menu
- Manipulator (`MANIP`): axis cross on the selection; moves only along the chosen axis (object snap counts only along the axis), distance can be typed, free move via the square
- 3D wireframe in the main view (toolbar group "3D:" after Electrical with icons, menu 3D, `3D`): orbit (middle button), pan (Ctrl+middle), zoom, view cube with direction arrows, perspective, grid on/off; right-click menu and double-click (properties, size, hide layer); pick a face as work plane and draw circle/rectangle/polyline on it, pull it up or cut it into the body as bore/pocket; pull 2D shapes up or down with the Z arrow; create box, cylinder, cone, pyramid, sphere directly; change size afterwards (`3DMASS`); 3D dimensions from any view; 3D view in layout viewports (also in the PDF); 3D manipulator (X/Y/Z); 3D blocks; plain wireframe (no hidden-line removal)
- 3D, round 3: when drawing with Line/Circle/Rectangle/Polyline the **face under the cursor is detected automatically** (highlighted in blue) and drawn on directly - sketches and dimensions no longer end up "in space"; new **Line** tool on the work plane (open sketch)
- 3D, round 4: **selection window** like in 2D (cyan from the left = fully inside, green from the right = touching); **3D rotate** about X/Y/Z (`3DDREHEN`); **round vertical edges** (`3DABRUNDEN`); **manipulator can be moved freely** in 2D and 3D (`3DPIVOT`, Shift+click on the square in 2D) and acts as pivot; cut-outs not open to the top are **dashed** in 2D; the bore goes into the correct body when several faces share a plane
- 3D object snap with **visible markers** (endpoint, midpoint, centre, grid) when sketching and dimensioning
- The 3D grid now uses the status bar switch (grid on/off, F7) and can be shown **dotted**
- Fix: a fast second click was treated as a double click and swallowed in drawing modes / move / manipulator, or opened the properties dialog
- Fix: face detection also directly on edges/corners (front view: draw a line exactly on the body corner); toolbar order can be changed (View > Toolbars > Move forward/back, or drop a grip on another bar)
- Fix: the side bar could not be shown again after hiding it in the 3D view
- Toolbars **per department** (Tools, Electrical, 3D) can be docked separately at the top/bottom/right, wrapping into a new row in a narrow window
- 3D in a layout viewport: the 3D icon in a layout switches the chosen viewport to 3D (instead of replacing the layout area); it can be activated and rotated with the middle mouse button
- The symbol toolbar can be docked at the top, bottom or right (drag the grip or View > Toolbar), the choice is saved
- Text can be **bold** (text dialog, properties, properties palette "Arial fett"); also in the PDF (Helvetica-Bold)
- Terminal diagram: the same function text appears only at the first terminal of a strip
- Manipulator: while moving, the object snap no longer snaps to the moved objects themselves (this blocked vertical moves); the toolbar button stays pressed while the manipulator is active
- Toolbar: "Change length" now sits before "Find and replace"; "Mask" sits after "Function text"
- Version jump to 1.1.0

## 1.0.3
- About window: mascot picture on the left of the texts (file `KatieCAD_Maskottchen.png`)
- The About window can only be opened once (opening it again brings the existing one to the front)
- New shortcut Ctrl+B: opens the block list (block selection)
- Title block "Standard (built-in)" removed (identical to "Example A3"); only the templates from the title_blocks folder remain
- Linux: own menu bar without grab instead of the Tk menu bar - open menus close on focus change, click elsewhere and ESC (Windows/macOS unchanged; old menus with `KATIECAD_NATIVE_MENU=1`)
- Cross references: the same name over several sheets is resolved as a chain (outgoing → next sheet, incoming → previous sheet); `L1.1`/`L1.2` are no longer needed
- Coordinate grid: labels 0.1 mm smaller (PDF print looked bolder)
- Menu: "Trim" and "Break" moved from Insert to Edit
- Hatch like AutoCAD: with nothing selected, click straight into an enclosed area (crossing lines allowed), several areas in a row
- Stretch: if objects were preselected with a crossing window, the second window drag is skipped; only the selected objects are stretched
- Cross reference "outgoing west" / "incoming east": identifier next to the arrow tip/base, the target note behind it
- Automatic electrical layers: devices → E_DEVICES, wires/junctions/cross references → E_LINES, cables → E_CABLE, terminals → E_CLAMPS, single pins → E_PIN (instead of layer 0); layers are created on demand
- Coordinate grid: choose DIN A4 (6 x 4), DIN A3 (8 x 5, 395 x 252.59 mm) or custom values
- Cross reference: text heights of identifier and target note adjustable (new default 2.5 / 1.5 mm), texts movable by grip, position resettable
- Documentation: cover sheet, table of contents and lists in DIN A4 or DIN A3 (content scaled)
- Sheet list: select several sheets (Ctrl/Shift + click) to move and delete them together
- Fix: "Create documentation" now shows errors in a window and writes them to the log instead of silently doing nothing
- Cross reference: identifier and target note stand side by side on one line by default
- Terminals: terminal number (NUM) enlarged from 1.0 to 1.75 mm
- Texts freely movable (yellow grips) for terminals, masks, cables, pins and device blocks (per instance); right-click › Reset text positions
- Coordinate grid: labels stay inside their strip in print

## 1.0.2
- Installation location per sheet (sheet properties, F2): appears in the title block (`EINBAUORT` / `PLACE`) and separates the device, terminal and cable lists
- Menu: "Insert block/device" now sits above "Create block"
- Fix: dimension text was offset; it is now centred above the dimension line
- Radius/diameter dimensions named more clearly (DR / DD)
- Terminal diagram: column "Terminal (NUM)" now sits between "Connection top" and "Connection bottom"; new column "Bridge" with a graphic for terminals wired together (only the first terminal of a bridge shows the target)
- Terminal diagram: on potential rails (PE, N, ...) only the potential name is shown instead of every terminal
- Terminal diagram: every terminal strip starts on its own sheet
- Terminal diagram sheets are named "Klemmenplan <strip>" after the terminal strip (e.g. "Klemmenplan X1")
- Table of contents: "type" and "description" are now sheet properties (F2); default type stays "Circuit diagram", the customer is no longer used as description
- Block browser: the symbol library is listed only once ("Symbole" / "symbols"); a second, older "symbols" entry is hidden
- Fix project check: terminals without their own IND inherit the terminal strip like in the terminal diagram (no false "assigned more than once" errors); the same identifier at different installation locations is not a duplicate
- Info window: new subtitle with a focus on electrical engineering
- PDF import (File > Import PDF...): vector lines, circles, text and fills; PDF layers become KatieCAD layers (own reader based on pypdf, BSD licence; the MIT licence is unaffected)
- Image import (File > Import image...): images are stored inside the drawing, written to PDF output, and saved as a file next to the DXF on DXF export
- PDF export writes KatieCAD layers as PDF layers (toggle them in Acrobat, Bluebeam, etc.; re-importable)
- Hatch: selection box (lines/solid fill) with spacing and angle in one dialog instead of typing
- More compact Info window that fits its content
- Info window: Log button opens the log file in the editor (no tabs)

## 1.0.1
- Contact mirror for main devices (right of the symbol or below the relay), freely movable
- Project check: duplicate devices, cross references (with "external"), terminals, open connections
- Properties window (Ctrl+1) for mixed selections, also in the right-click menu
- Scale and mirror for objects, blocks and devices
- Export the whole project as one DXF file (4 sheets per row)
- Info window with change log and program log
- Fix: cables were lost when switching sheets
- Fix: right-click menu on Linux/Wayland, logo in the info window on Linux
- Fix: macOS info shows the correct version

## 1.0.0
- First release: 2D CAD, blocks, projects with sheets, schematics, cross references, terminals, cables,
  reports, title block automation, DXF/DWG import and export, installers for Windows, Linux and macOS
