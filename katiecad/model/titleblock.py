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
    Aliases (German / other templates): SEITE = PAGE, SEITEN = PAGES,
    SIZE / BLATTFORMAT / PAPIERFORMAT = FORMAT.
    From Project > Project properties (on every sheet):
        GEZEICHNET / DRAWN (+ _DATUM / _DATE), GEPRUEFT / VERIFIED (+ _DATUM),
        ZEICHNUNGSNUMMER / DRAWINGNUMBER, FIRMA / COMPANY, KUNDE / CUSTOMER,
        AUFTRAG / ORDER, ANLAGE / PLANT, REVISION
        REV1_STAND/AENDERUNG/NAME/DATUM ... REV4_*   (English: INDEX, CHANGE,
        NAME, DATE)
        TITLE / TITEL = customer - project - sheet name; the parts alone are
        TITEL1 / TITEL2 / TITEL3 (TITLE1..3)
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
# Keys of the project data -> tags in the title block (German / English).
# They are filled in automatically on EVERY sheet (Project > Project
# properties); empty values never overwrite what was typed in by hand.
DATA_TAGS = {
    "gezeichnet": ("GEZEICHNET", "DRAWN"),
    "gezeichnet_datum": ("GEZEICHNET_DATUM", "DRAWN_DATE"),
    "geprueft": ("GEPRUEFT", "VERIFIED"),
    "geprueft_datum": ("GEPRUEFT_DATUM", "VERIFIED_DATE"),
    "zeichnungsnummer": ("ZEICHNUNGSNUMMER", "DRAWINGNUMBER"),
    "firma": ("FIRMA", "COMPANY"),
    "kunde": ("KUNDE", "CUSTOMER"),
    "auftrag": ("AUFTRAG", "ORDER"),
    "anlage": ("ANLAGE", "PLANT"),
    "revision": ("REVISION",),
}
REV_ROWS = 4                                   # rows of the revision table
REV_FIELDS = (("stand", ("STAND", "INDEX")),   # project key -> tag suffixes
              ("aenderung", ("AENDERUNG", "CHANGE")),
              ("name", ("NAME",)),
              ("datum", ("DATUM", "DATE")))
FORMAT_TAGS = ("FORMAT", "SIZE", "BLATTFORMAT", "PAPIERFORMAT", "PAPER")
TITLE_TAGS = ("TITLE", "TITEL")                # kunde - project - sheet
TITLE_PARTS = (("TITEL1", "TITLE1"), ("TITEL2", "TITLE2"), ("TITEL3", "TITLE3"))
TITLE_SEPARATOR = " - "


def rev_tags(row):
    """All tag spellings of revision row 1..REV_ROWS: {key: (tags)}.
    German: REV1_STAND, REV1_AENDERUNG, REV1_NAME, REV1_DATUM
    English: REV1_INDEX, REV1_CHANGE, REV1_NAME, REV1_DATE"""
    return {k: tuple("REV%d_%s" % (row, sfx) for sfx in sfxs)
            for k, sfxs in REV_FIELDS}


def _alle_data_tags():
    out = set()
    for tags in DATA_TAGS.values():
        out.update(tags)
    for r in range(1, REV_ROWS + 1):
        for tags in rev_tags(r).values():
            out.update(tags)
    return out


_BASIS = {"PAGE", "PAGES", "SHEET", "PROJECT", "DATE", "SCALE", "SEITE",
          "SEITEN"} | set(FORMAT_TAGS)
_TITEL = set(TITLE_TAGS) | {t for pair in TITLE_PARTS for t in pair}
DATA_ONLY = frozenset(_alle_data_tags())        # empty value = keep as is
RESERVED = tuple(sorted(_BASIS | _TITEL | DATA_ONLY))


def norm_tag(tag):
    """Tolerant spelling of a tag: upper case, umlauts resolved, only letters
    and digits  ('Geprüft_Datum' -> 'GEPRUEFTDATUM', 'Rev-1 Stand' -> 'REV1STAND')."""
    t = str(tag or "").upper()
    for a, b in (("Ä", "AE"), ("Ö", "OE"), ("Ü", "UE"), ("ß", "SS"), ("ẞ", "SS")):
        t = t.replace(a, b)
    return "".join(c for c in t if c.isalnum())


def _norm_extra():
    """More accepted spellings of the revision fields, e.g. STAND1, INDEX1,
    AENDERUNG1, REV1STAND, STAND_REV1  (all compared after norm_tag)."""
    out = {}
    for r in range(1, REV_ROWS + 1):
        for key, sfxs in REV_FIELDS:
            for f in sfxs + ("STAND",) * (key == "stand") \
                    + ("DATUM",) * (key == "datum"):
                for form in ("%s%d", "REV%d%s", "%sREV%d", "REV%s%d", "%s_%d"):
                    name = form % ((f, r) if form in ("%s%d", "%sREV%d", "REV%s%d",
                                                      "%s_%d") else (r, f))
                    out[norm_tag(name)] = ("REV%d_%s" % (r, sfxs[0]))
    return out


_NORM_ALIAS = _norm_extra()
NORM_RESERVED = {norm_tag(t) for t in RESERVED} | set(_NORM_ALIAS)


def is_auto_tag(tag):
    """True if the attribute with this tag is filled in automatically."""
    return norm_tag(tag) in NORM_RESERVED

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


def daten_werte(daten, projekt, sheet, lang="en", today=None):
    """Tag values from the project data (title block fields of every sheet).
    Title: customer, then project name, then sheet name."""
    daten = daten or {}
    today = today or datetime.date.today()
    kurz = today.strftime("%d.%m.%Y") if lang == "de" else today.strftime("%Y-%m-%d")
    d = dict(daten)
    if d.get("gezeichnet") or d.get("datum"):
        d["gezeichnet_datum"] = (d.get("gezeichnet_datum") or d.get("datum")
                                 or kurz)
    if d.get("geprueft") or d.get("geprueft_datum"):
        d["geprueft_datum"] = d.get("geprueft_datum") or d.get("datum") or kurz
    out = {}
    for key, tags in DATA_TAGS.items():
        v = str(d.get(key, "") or "")
        if v:
            for t in tags:
                out[t] = v
    rev = d.get("rev")
    rev = rev if isinstance(rev, list) else []
    for r in range(1, REV_ROWS + 1):
        zeile = rev[r - 1] if r - 1 < len(rev) and isinstance(rev[r - 1], dict) else {}
        for key, tags in rev_tags(r).items():
            v = str(zeile.get(key, "") or "")
            if v:
                for t in tags:
                    out[t] = v
    kunde = str(d.get("kunde", "") or "")
    proj = str(d.get("anlage", "") or projekt or "")
    teile = [kunde, proj, sheet or ""]
    for (de, en), v in zip(TITLE_PARTS, teile):
        out[de] = out[en] = v
    kombi = TITLE_SEPARATOR.join(t for t in teile if t)
    for t in TITLE_TAGS:
        out[t] = kombi
    return out


def info_values(nr, total, sheet, project, lang="en", paper_format="", today=None,
                daten=None):
    """Values for the reserved tags from plain numbers / names."""
    today = today or datetime.date.today()
    date = today.strftime("%d.%m.%Y") if lang == "de" else today.strftime("%Y-%m-%d")
    short = (paper_format or "").split(" ")[0]
    out = daten_werte(daten, project, sheet, lang, today)
    out.update({"PAGE": str(nr), "PAGES": str(total), "SHEET": sheet,
                "PROJECT": project, "DATE": date,
                "SEITE": str(nr), "SEITEN": str(total)})
    for t in FORMAT_TAGS:
        out[t] = short
    return out


def make_info(project, sheet_index, lang="en", paper_format="", today=None):
    """Values for the reserved tags (SCALE is determined per layout)."""
    daten = None
    if project is not None:
        nr = sheet_index + 1
        total = len(project.blaetter)
        sheet = project.blaetter[sheet_index].name if 0 <= sheet_index < total else ""
        proj = project.name
        daten = project.daten
    else:
        nr, total, sheet, proj = 1, 1, "", ""
    return info_values(nr, total, sheet, proj, lang, paper_format, today, daten)


def refresh_fields(layout_elements, info, fallback_scale=""):
    """Writes the automatic values into all title blocks of a layout.
    Returns the number of changed values."""
    vps = [e for e in layout_elements if isinstance(e, Viewport)]
    scale = massstab_text(vps[0].zoom) if vps else fallback_scale
    values = dict(info)
    values["SCALE"] = scale
    norm = {}
    for k, v in values.items():
        norm[norm_tag(k)] = (k, v)
    for nk, kanon in _NORM_ALIAS.items():          # tolerant revision spellings
        if kanon in values:
            norm.setdefault(nk, (kanon, values[kanon]))
    changed = 0
    for el in layout_elements:
        if not is_title_block(el):
            continue
        for ad in el.attribut_definitionen():
            hit = norm.get(norm_tag(ad.tag))
            if hit is None:
                continue
            key, val = hit
            new = str(val)
            if key in DATA_ONLY and not new:
                continue                         # keep manual entries
            if el.attribute.get(ad.tag) != new:
                el.attribute[ad.tag] = new
                changed += 1
    return changed
