# -*- coding: utf-8 -*-
"""
katiecad/model/blocks.py - Block definitions as separate files (*.katieblock).
Contains NO Tkinter.

File format (JSON):
    {"format": "katiecad-block", "version": 1, "block": {<BlockDefinition>}}

The definition contains the elements in local coordinates incl.
attribute definitions (AttributDefinition), see katiecad.model.core.
"""

import json
import os

from katiecad.model.core import (
    BlockDefinition, BlockReferenz, ZUSAMMENGESETZT, Linie, Kreis, Bogen,
    Rechteck, Polylinie, Text, Schraffur, Verbindungspunkt, bogen_punkte,
    _FestMaske)
from katiecad.model.project import _UNGUELTIG, BLOCK_ENDUNG

FORMAT_KENNUNG = "katiecad-block"
FORMAT_VERSION = 1


class BlockDateiFehler(Exception):
    pass


def vorschlag_dateiname(blockname):
    """File name (without folder) matching the block name."""
    n = _UNGUELTIG.sub("_", (blockname or "Block").strip()) or "Block"
    return n.rstrip(". ") + BLOCK_ENDUNG


def block_speichern(pfad, definition):
    daten = {"format": FORMAT_KENNUNG, "version": FORMAT_VERSION,
             "block": definition.to_dict()}
    try:
        os.makedirs(os.path.dirname(os.path.abspath(pfad)), exist_ok=True)
        tmp = pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(daten, f, indent=2, ensure_ascii=False)
        os.replace(tmp, pfad)
    except OSError as e:
        raise BlockDateiFehler(str(e))


def block_laden(pfad, element_factory):
    """Reads a block file and returns a BlockDefinition."""
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            daten = json.load(f)
    except (OSError, ValueError) as e:
        raise BlockDateiFehler(str(e))
    if not isinstance(daten, dict):
        raise BlockDateiFehler("kein_block")
    if daten.get("format") == FORMAT_KENNUNG:
        bd = daten.get("block")
    elif "elemente" in daten and "name" in daten:   # bare definition
        bd = daten
    else:
        raise BlockDateiFehler("kein_block")
    if not isinstance(bd, dict):
        raise BlockDateiFehler("kein_block")
    d = BlockDefinition.from_dict(bd, element_factory)
    if not d.elemente:
        raise BlockDateiFehler("leer")
    return d


# ------------------------------------------------------------
# Folder (block files directly in the file system)
# ------------------------------------------------------------
def standard_ordner():
    """Default folder for custom blocks: <user folder>/KatieCAD/Blocks."""
    return os.path.join(os.path.expanduser("~"), "KatieCAD", "Blocks")


def symbol_ordner():
    """Symbol library shipped with the program: <program folder>/symbols."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "symbols")


def unterordner(pfad):
    """Sorted sub-folders (without hidden ones)."""
    try:
        return sorted((n for n in os.listdir(pfad)
                       if not n.startswith(".")
                       and os.path.isdir(os.path.join(pfad, n))),
                      key=str.lower)
    except OSError:
        return []


def blockdateien(pfad):
    """Sorted block files of a folder: [(file_name, full_path)]."""
    try:
        return sorted(((n, os.path.join(pfad, n)) for n in os.listdir(pfad)
                       if n.lower().endswith(BLOCK_ENDUNG)
                       and os.path.isfile(os.path.join(pfad, n))),
                      key=lambda t: t[0].lower())
    except OSError:
        return []


# ------------------------------------------------------------
# Preview geometry (without Tk)
# ------------------------------------------------------------
def _farbe(el):
    f = getattr(el, "farbe", None) if getattr(el, "eig_farbe", False) else None
    if not f or not isinstance(f, str) or not f.startswith("#") or len(f) != 7:
        return "#e8e0ff"
    try:
        r, g, b = int(f[1:3], 16), int(f[3:5], 16), int(f[5:7], 16)
    except ValueError:
        return "#e8e0ff"
    if 0.3 * r + 0.59 * g + 0.11 * b < 70:       # too dark for a dark background
        return "#e8e0ff"
    return f


def _flach(el, out):
    if isinstance(el, _FestMaske):
        for k in el.aufgeloest(True):
            _flach(k, out)
    elif isinstance(el, ZUSAMMENGESETZT):
        for k in el.aufgeloest():
            _flach(k, out)
    else:
        out.append(el)


def vorschau_geometrie(definition):
    """Drawable representation of a BlockDefinition:
    {"linien": [(points, closed, colour)], "texte": [(x, y, text, height,
    colour)], "flaechen": [(points, colour)], "bbox": (x1, y1, x2, y2) or None}."""
    ref = BlockReferenz(0.0, 0.0, definition.name, definition.elemente)
    flach = []
    for k in ref.aufgeloest():
        _flach(k, flach)
    linien, texte, flaechen = [], [], []
    xs, ys = [], []

    def punkte(pts):
        for x, y in pts:
            xs.append(x); ys.append(y)

    for el in flach:
        f = _farbe(el)
        if isinstance(el, Linie):
            pts = [(el.x1, el.y1), (el.x2, el.y2)]
            linien.append((pts, False, f)); punkte(pts)
        elif isinstance(el, Kreis):
            pts = bogen_punkte(el.cx, el.cy, el.r, 0.0, 360.0, 36)
            linien.append((pts, True, f)); punkte(pts)
        elif isinstance(el, Bogen):
            pts = bogen_punkte(el.cx, el.cy, el.r, el.start, el.ende, 36)
            linien.append((pts, False, f)); punkte(pts)
        elif isinstance(el, Rechteck):
            pts = [(el.x1, el.y1), (el.x2, el.y1), (el.x2, el.y2), (el.x1, el.y2)]
            linien.append((pts, True, f)); punkte(pts)
        elif isinstance(el, Polylinie):
            pts = list(el.punkte)
            linien.append((pts, bool(el.geschlossen), f)); punkte(pts)
        elif isinstance(el, Schraffur):
            pts = list(el.punkte)
            if getattr(el, "muster", "") == "solid":
                flaechen.append((pts, f))
            else:
                linien.append((pts, True, f))
            punkte(pts)
        elif isinstance(el, Verbindungspunkt):
            pts = bogen_punkte(el.x, el.y, el.radius, 0.0, 360.0, 16)
            linien.append((pts, True, "#ff6bd6")); punkte(pts)
            t = el.text_element()
            if t is not None:
                b = t.bbox()
                texte.append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, t.inhalt,
                              t.hoehe, f)); punkte([(b[0], b[1]), (b[2], b[3])])
        elif isinstance(el, Text):
            b = el.bbox()
            texte.append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, el.inhalt,
                          el.hoehe, f)); punkte([(b[0], b[1]), (b[2], b[3])])
    bbox = (min(xs), min(ys), max(xs), max(ys)) if xs else None
    return {"linien": linien, "texte": texte, "flaechen": flaechen, "bbox": bbox}
