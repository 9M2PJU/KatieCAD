# KatieCAD

A lightweight 2D CAD drawing tool built with Python and Tkinter, featuring
core drawing, editing and dimensioning tools, plus DXF import/export.

![KatieCAD Screenshot](docs/screenshot.png)  
<!-- Replace with an actual screenshot of your app -->

## Features

- **Drawing tools:** Line, Polyline, Circle, Arc, Rectangle, Text
- **Editing tools:** Move, Copy, Rotate, Stretch, Array, Grip editing
- **Object snap:** Endpoint, Midpoint, Center, Intersection, Quadrant,
  Perpendicular, Nearest
- **Layers & styles:** Layer management, line types, line weights,
  element colors
- **Dimensions:** Linear, aligned, radius, diameter, decimal comma toggle
- **Layout view:** Paper space with viewports, standard scales, title block
- **DXF import/export** (via `ezdxf`)
- **Bilingual UI:** German and English (switchable at runtime)

## Requirements

- Python **3.8+**
- `tkinter` (included in standard Python on Windows/macOS; on Linux install
  `python3-tk` via your package manager)

Optional:

- `ezdxf` for DXF import/export
- `ezdwg` for DWG import (rarely needed, may require manual build)

## Installation

```bash
git clone https://github.com/Merecete/KatieCAD.git
cd KatieCAD

# Recommended: use a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

pip install -r requirements.txt
