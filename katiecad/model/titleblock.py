# -*- coding: utf-8 -*-
"""
katiecad/model/titleblock.py - Title block templates (no Tkinter).

A title block template is an ordinary KatieCAD drawing (*.cadjson) that is
stored in the folder ``title_blocks/`` (next to main.py, and/or in a folder
``title_blocks/`` inside the project folder).

Rules for a template drawing
  * Only the MODEL elements of the file are used.
  * The drawing's origin (0, 0) is the LOWER RIGHT corner of the sheet frame.
    The title block therefore extends to the left (x <= 0) and upwards (y >= 0).
  * Attribute definitions (ATTDEF) become fillable fields. The tags in
    RESERVED are filled in automatically and stay up to date:
        PAGE   sheet number          PAGES  number of sheets in the project
        SHEET  sheet name            PROJECT project name
        DATE   today                 SCALE  scale of the first viewport
        FORMAT paper format (e.g. A3)
"""

import json
import math
import os
import datetime

from katiecad.model.core import (
    BlockReferenz, Viewport, Linie, Rechteck, Text, AttributDefinition,
    FARBEN, massstab_text,
)

PREFIX = "TITLEBLOCK:"
FOLDER_NAME = "title_blocks"
RESERVED = ("PAGE", "PAGES", "SHEET", "PROJECT", "DATE", "SCALE", "FORMAT")

MARGIN_LEFT = 20.0        # mm, binding margin (A3 and larger)
MARGIN_OTHER = 5.0        # mm, top / right / bottom
A4_SIZE = (297, 210)      # landscape A4
A4_MARGIN_LEFT = 5.0      # mm, A4: punched margin is at the TOP
A4_MARGIN_TOP = 15.0      # mm


# ---------------------------------------------------------------
# Frame geometry
# ---------------------------------------------------------------
def margins(width, height):
    """(left, top, right, bottom) of the sheet frame in mm.
    A4: 5 mm left, 15 mm top (punched margin), 5 mm right/bottom.
    All other formats: 20 mm left, 5 mm elsewhere."""
    if (round(width), round(height)) == A4_SIZE:
        return (A4_MARGIN_LEFT, A4_MARGIN_TOP, MARGIN_OTHER, MARGIN_OTHER)
    return (MARGIN_LEFT, MARGIN_OTHER, MARGIN_OTHER, MARGIN_OTHER)


def frame_rects(width, height):
    """((paper edge), (inner frame)) as (x1, y1, x2, y2) in mm."""
    left, top, right, bottom = margins(width, height)
    return ((0.0, 0.0, width, height),
            (left, bottom, width - right, height - top))


def old_frame_rects(width, height):
    """Inner frames drawn by earlier versions (to be replaced)."""
    return [(10.0, 5.0, width - 5.0, height - 5.0),     # 10 mm left margin
            (20.0, 5.0, width - 5.0, height - 5.0),     # 20 mm left, also on A4
            (5.0, 15.0, width - 5.0, height - 15.0)]    # A4 frame


def block_origin(width, height):
    """Where the template's (0, 0) is placed: lower right corner of the frame."""
    _l, _t, right, bottom = margins(width, height)
    return (width - right, bottom)


# ---------------------------------------------------------------
# Template files
# ---------------------------------------------------------------
def program_folder():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, FOLDER_NAME)


def template_folders(project_folder=None):
    folders = [program_folder()]
    if project_folder:
        folders.append(os.path.join(project_folder, FOLDER_NAME))
    return folders


def list_templates(folders):
    """[(display name, path)] sorted by name. A project template overrides a
    program template with the same name."""
    found = {}
    for folder in folders:
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for n in names:
            if n.lower().endswith(".cadjson"):
                found[os.path.splitext(n)[0]] = os.path.join(folder, n)
    return sorted(found.items(), key=lambda kv: kv[0].lower())


def load_template(path, element_factory):
    """Model elements of a template file (list). Raises OSError/ValueError."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("not a KatieCAD drawing")
    out = []
    for d in data.get("elemente", []):
        if not isinstance(d, dict):
            continue
        el = element_factory(d)
        if el is not None and not isinstance(el, Viewport):
            out.append(el)
    if not out:
        raise ValueError("template contains no elements")
    return out


def template_data(elements):
    """Minimal drawing dict (can be opened in KatieCAD) for `elements`."""
    return {"einheit": "mm", "layers": [], "elemente": [e.to_dict() for e in elements],
            "layouts": [], "aktives_layout": 0, "ansicht": "modell"}


# ---------------------------------------------------------------
# Built-in default template
# ---------------------------------------------------------------
def default_elements(lang="en"):
    de = lang == "de"
    L = {"project": "Projekt" if de else "Project",
         "title": "Titel" if de else "Title",
         "date": "Datum" if de else "Date",
         "drawn": "Gezeichnet" if de else "Drawn by",
         "sheet": "Blatt" if de else "Sheet",
         "scale": "Maßstab" if de else "Scale",
         "page": "Seite" if de else "Page"}
    thick = {"layer": "0", "farbe": FARBEN["cyan"], "eig_farbe": True,
             "linientyp": "Volllinie (breit)", "staerke": 0.7}
    thin = {"layer": "0", "farbe": FARBEN["cyan"], "eig_farbe": True,
            "linientyp": "Volllinie (schmal)", "staerke": 0.35}
    el = [Rechteck(-180, 0, 0, 40, **thick),
          Linie(-180, 20, 0, 20, **thin),
          Linie(-110, 20, -110, 40, **thin),
          Linie(-40, 20, -40, 40, **thin),
          Linie(-140, 0, -140, 20, **thin),
          Linie(-70, 0, -70, 20, **thin),
          Linie(-40, 0, -40, 20, **thin)]
    # (x0, y0 of the cell, label, tag, prompt)
    cells = [(-180, 20, L["project"], "PROJECT", L["project"]),
             (-110, 20, L["title"], "TITLE", L["title"]),
             (-40, 20, L["date"], "DATE", L["date"]),
             (-180, 0, L["drawn"], "DRAWN", L["drawn"]),
             (-140, 0, L["sheet"], "SHEET", L["sheet"]),
             (-70, 0, L["scale"], "SCALE", L["scale"]),
             (-40, 0, L["page"], "PAGE", L["page"])]
    for x0, y0, label, tag, prompt in cells:
        el.append(Text(x0 + 1.5, y0 + 18.5, label, 2.0, 0.0, "Arial",
                       einfuegepunkt="oben_links", **thin))
        el.append(AttributDefinition(x0 + 2.0, y0 + 4.0, None, 4.0, 0.0, "Arial",
                                     "unten_links", tag=tag, prompt=prompt,
                                     wert="", **thin))
    el.append(Text(-26.5, 4.0, "/", 4.0, 0.0, "Arial", "unten_links", **thin))
    el.append(AttributDefinition(-23.5, 4.0, None, 4.0, 0.0, "Arial", "unten_links",
                                 tag="PAGES", prompt=L["page"] + " (total)",
                                 wert="", **thin))
    return el


# ---------------------------------------------------------------
# Block reference + automatic fields
# ---------------------------------------------------------------
def is_title_block(el):
    return isinstance(el, BlockReferenz) and str(el.block_name).startswith(PREFIX)


def make_block(name, elements, width, height, **style):
    x, y = block_origin(width, height)
    return BlockReferenz(x, y, PREFIX + name, elements, **style)


def make_info(project, sheet_index, lang="en", paper_format="", today=None):
    """Values for the reserved tags (SCALE is determined per layout)."""
    today = today or datetime.date.today()
    if project is not None:
        nr = sheet_index + 1
        total = len(project.blaetter)
        sheet = project.blaetter[sheet_index].name if 0 <= sheet_index < total else ""
        proj = project.name
    else:
        nr, total, sheet, proj = 1, 1, "", ""
    date = today.strftime("%d.%m.%Y") if lang == "de" else today.strftime("%Y-%m-%d")
    short = (paper_format or "").split(" ")[0]
    return {"PAGE": str(nr), "PAGES": str(total), "SHEET": sheet,
            "PROJECT": proj, "DATE": date, "FORMAT": short}


def refresh_fields(layout_elements, info, fallback_scale=""):
    """Writes the automatic values into all title blocks of a layout.
    Returns the number of changed values."""
    vps = [e for e in layout_elements if isinstance(e, Viewport)]
    scale = massstab_text(vps[0].zoom) if vps else fallback_scale
    values = dict(info)
    values["SCALE"] = scale
    changed = 0
    for el in layout_elements:
        if not is_title_block(el):
            continue
        for ad in el.attribut_definitionen():
            if ad.tag in RESERVED and ad.tag in values:
                new = str(values[ad.tag])
                if el.attribute.get(ad.tag) != new:
                    el.attribute[ad.tag] = new
                    changed += 1
    return changed
