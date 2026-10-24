# KatieCAD

KatieCAD is a lightweight CAD system built with Python and Tkinter, aimed primarily at electrical engineering—especially switchgear construction, distribution boards, and building installation. Projects can contain multiple drawings that are edited side by side. It deliberately adds electrical-specific features such as cross-references and wires, and is gradually gaining real electrical “intelligence” for generating device lists, terminal plans, and similar outputs (currently work in progress). At the same time, it remains a general-purpose CAD with the familiar basics: you can draw freely without using project mode, and create and save blocks individually.

![Screenshot1](Shot1.png)

![Screenshot2](Shot2.png)

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
- **DWG import** (via `ezdwg`)
- **Bilingual UI:** German and English (switchable at runtime)

## Requirements

- **Python 3.10+** (required by `ezdwg`)
- `tkinter` (included in standard Python on Windows/macOS; on Linux install `python3-tk`)

The following packages are installed automatically via `requirements.txt`:
- `ezdxf` – for DXF import/export
- `ezdwg` – for DWG import

## Installation

```bash
git clone https://github.com/Merecete/KatieCAD.git
cd KatieCAD

# Recommended: use a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

pip install -r requirements.txt

python main.py
