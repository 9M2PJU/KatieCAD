# Changes

## 1.0.3
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
