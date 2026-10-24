# -*- coding: utf-8 -*-
"""
katiecad/model/eigenschaften.py - Common properties of a mixed selection
(NO Tkinter). Used by the properties palette (Ctrl+1).
"""
from katiecad.model.core import Text, Viewport

VERSCHIEDEN = "*"          # marker for "values differ"
ALLGEMEIN = ("layer", "farbe", "linientyp", "staerke")
TEXTFELDER = ("hoehe", "schriftart", "winkel", "einfuegepunkt")


def _ziele(auswahl):
    return [e for e in auswahl if not isinstance(e, Viewport)]


def _wert(el, feld):
    if feld == "farbe":
        return el.farbe if el.eig_farbe else None      # None = by layer
    return getattr(el, feld)


def gemeinsame(auswahl):
    """-> {field: value | VERSCHIEDEN}; text fields only if the selection
    contains text. farbe None = 'by layer'."""
    z = _ziele(auswahl)
    out = {}
    if not z:
        return out
    felder = list(ALLGEMEIN)
    texte = [e for e in z if isinstance(e, Text)]
    for f in felder:
        werte = {_wert(e, f) for e in z}
        out[f] = werte.pop() if len(werte) == 1 else VERSCHIEDEN
    for f in TEXTFELDER:
        if texte:
            werte = {getattr(e, f) for e in texte}
            out[f] = werte.pop() if len(werte) == 1 else VERSCHIEDEN
    return out


def anwenden(auswahl, feld, wert):
    """Sets `feld` on all affected elements. farbe: hex or None (by layer);
    staerke: float or None. Returns the number of changed elements."""
    n = 0
    for e in _ziele(auswahl):
        if feld in TEXTFELDER:
            if not isinstance(e, Text):
                continue
            setattr(e, feld, float(wert) if feld in ("hoehe", "winkel") else wert)
        elif feld == "farbe":
            if wert is None:
                e.eig_farbe = False
            else:
                e.farbe, e.eig_farbe = wert, True
        elif feld in ALLGEMEIN:
            setattr(e, feld, wert)
        else:
            continue
        n += 1
    return n
