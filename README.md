# KatieCAD

**KatieCAD is an open-source electrical CAD for switchgear construction, distribution boards and building installation, built with Python and Tkinter.**

It covers the complete workflow of an electrical project: draw circuit diagrams across several sheets, connect devices with wires, let cross references and device designations be generated automatically, and produce the documentation (cover sheet, table of contents, device list, terminal plan, cable plan) at the push of a button. At the same time it is a full 2D CAD with simple 3D modelling: you can draw freely without a project, build bodies in 3D, create, save and reuse your own blocks, and print 2D and 3D views on the same sheet.

KatieCAD brings everything you need for daily work into one tool: electrical diagrams with automatic documentation, a complete 2D CAD and simple 3D modelling, ready to use, free and open source.

![Screenshot1](Screenshots/Screenshot1.png)

![Screenshot2](Screenshots/Screenshot2.png)

![Screenshot3](Screenshots/Screenshot3.png)

![Screenshot4](Screenshots/Screenshot4.png)

![Screenshot5](Screenshots/Screenshot5.png)

## Features

### Electrical engineering
- **Projects with several sheets** – edited side by side, with title blocks and automatic fields
- **Wires, pins and junctions** – T-pieces, corners and crossings (with or without dot); wires are traced across sheets
- **Cross references** between sheets (outgoing / incoming)
- **Devices with electrical mask** – designation (IND), type (TYP) and function (PER); main and auxiliary contacts, automatic device references
- **Terminals and cables**, coordinate field, automatic wiring of connected points
- **Symbol library** with about 40 standard symbols (contactors, relays, fuses, switches, motors, transformers, …) and your own block library with a block browser
- **Documentation generator:** cover sheet, table of contents, device list, terminal plan, cable plan; customisable columns via `report_templates/`, CSV export and PDF output

### General CAD
- **Drawing tools:** Line, Polyline, Circle, Arc, Ellipse, Spline, Rectangle, Text, Hatching
- **Editing tools:** Move, Copy, Rotate, Stretch, Array, Trim, Break, Fillet/Chamfer, Offset, Grip editing, selection windows (window / crossing)
- **Object snap:** Endpoint, Midpoint, Center, Intersection, Quadrant, Perpendicular, Nearest; ortho mode and input line (`500,1000`, `@dx,dy`, `length<angle`)
- **Layers & styles:** Layer management, line types, line weights, element colours
- **Dimensions:** Linear, aligned, radius, diameter, decimal comma toggle; distance measuring
- **Blocks with attributes:** create, save (`*.katieblock`) and reuse
- **Layout view:** Paper space with viewports, standard scales, title block
- **DXF import/export** (via `ezdxf`), **DWG import** (via `ezdwg`)
- **Bilingual UI:** German and English (switchable at runtime)
- **Freely dockable toolbars:** separate bars for tools, electrical and 3D – top, bottom or right, in any order

### Simple 3D modelling
- **3D view in the same window** (wireframe, orthographic or perspective) with view cube, orbit/pan/zoom and a grid on the work plane
- **Bodies:** box, cylinder, cone, pyramid, sphere; sizes editable afterwards; pull up 2D shapes like in AutoCAD (extrude, bores and pockets)
- **Drawing directly on faces** with the normal tools (Line, Polyline, Circle, Rectangle, Dimension, Text) – with highlighted faces, visible snap markers, ortho and typed values
- **Rotate** about any axis, **round edges** (top, bottom, vertical), relocatable **manipulator** (pivot point)
- **3D dimensions, 3D text and distance measuring** between any two points in space
- **3D blocks** to group bodies; hidden cut-outs are shown dashed in the 2D view
- **3D views in the layout:** show a viewport as a 3D view and print it to scale or export it as PDF

## Download

Ready-made installers for **Windows**, **Linux** (`.deb` / `.tar.gz`) and **macOS** are available on the [Releases](../../releases) page.

### Linux one-liners

**Debian/Ubuntu** (`.deb` from the Releases page):

```bash
sudo apt install ./KatieCAD-*-Linux-*.deb
katiecad
```

**Arch Linux** ([`katiecad-git`](https://aur.archlinux.org/packages/katiecad-git), tracks `main`):

```bash
yay -S katiecad-git
katiecad
```

## Run from source

Requirements:
- **Python 3.10+**
- `tkinter` (included in standard Python on Windows/macOS; on Linux install `python3-tk`)

```bash
git clone https://github.com/Merecete/KatieCAD.git
cd KatieCAD

## Windows:

python -m venv .venv

.venv\Scripts\activate

pip install -r requirements.txt

python main.py


## Linux/macOS:

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

python3 main.py
```

`requirements.txt` installs `ezdxf` (DXF) and `ezdwg` (DWG) and the other dependencies.

## Documentation

- [User guide (English)](docs/USER_GUIDE.md) · [Anleitung (Deutsch)](docs/ANLEITUNG.md)

## License

KatieCAD is released under the [MIT License](LICENSE).
