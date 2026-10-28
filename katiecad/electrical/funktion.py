# -*- coding: utf-8 -*-
"""
katiecad/electrical/funktion.py - Function texts (NO Tkinter).

A function text is a normal (multi-line) text on the layer "F-Text". It
describes what the devices and terminals "behind" its insertion point are
for. Rule: an object belongs to a function text if it lies on the same sheet
and not to the left of the insertion point (x >= text x - TOL); if several
texts qualify, the nearest one wins. The lists show the text in the column
"Funktion" (device list and terminal diagram).
"""

import math

from katiecad.model.core import Text, FTEXT_LAYER

TOL = 1.0          # mm: objects exactly below the insertion point still count


def funktionstexte(elemente):
    """[(x, y, [lines])] of all function texts of an element list."""
    out = []
    for e in elemente:
        if isinstance(e, Text) and getattr(e, "layer", None) == FTEXT_LAYER:
            zeilen = [z.strip() for z in str(e.inhalt).split("\n") if z.strip()]
            if zeilen:
                out.append((float(e.x), float(e.y), zeilen))
    return out


def funktion_an(texte, x, y):
    """Lines of the function text that applies to the point (x, y); [] if none."""
    beste, bd = None, None
    for tx, ty, zeilen in texte:
        if x < tx - TOL:
            continue
        d = math.hypot(x - tx, y - ty)
        if bd is None or d < bd:
            beste, bd = zeilen, d
    return list(beste) if beste else []


def funktionen_je_blatt(blaetter):
    """{sheet index: function texts}."""
    return {idx: funktionstexte(el) for idx, el in blaetter}
