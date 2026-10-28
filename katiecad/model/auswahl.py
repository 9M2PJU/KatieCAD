# -*- coding: utf-8 -*-
"""
katiecad/model/auswahl.py - Quick select: filter elements by properties (MIT).
"""


def eig_wert(el, eigenschaft, layers=None):
    """Value of one property of an element (for filtering/listing)."""
    if eigenschaft == "typ":
        return getattr(el, "typ", "")
    if eigenschaft == "layer":
        return getattr(el, "layer", "")
    if eigenschaft == "linientyp":
        return getattr(el, "linientyp", "")
    if eigenschaft == "farbe":
        if getattr(el, "eig_farbe", False) or layers is None:
            return getattr(el, "farbe", "")
        l = layers.get(getattr(el, "layer", None))
        return l.farbe if l is not None else getattr(el, "farbe", "")
    return None


def schnellauswahl(elemente, kriterien, layers=None, negiert=False):
    """kriterien: {"typ": ..., "layer": ..., "farbe": ..., "linientyp": ...};
    entries with value None/"" are ignored. All given criteria must match
    (AND); negiert=True selects everything that does NOT match."""
    aktiv = {k: v for k, v in kriterien.items() if v}
    out = []
    for el in elemente:
        passt = all(eig_wert(el, k, layers) == v for k, v in aktiv.items())
        if passt != bool(negiert):
            out.append(el)
    return out


def vorhandene_werte(elemente, eigenschaft, layers=None):
    """Sorted distinct values of a property in the given elements."""
    return sorted({eig_wert(e, eigenschaft, layers) for e in elemente} - {None, ""})
