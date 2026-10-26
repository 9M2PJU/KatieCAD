# Changes

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
