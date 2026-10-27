# -*- coding: utf-8 -*-
"""
katiecad/electrical/suchen.py - Find and replace texts (MIT).

Works on element objects (the open sheet) AND on the plain dicts of the
JSON sheet files (all other sheets of the project): the field names of the
dicts equal the attribute names of the elements.

Searched fields:
  text          Text.inhalt
  bemassung     Bemassung.text_override
  querverweis   Querverweis.text
  maske/klemme/kabel   every value of `werte` (IND, TYP, PER, NUM, CAB ...)
  vpunkt        pin designation `wert`
  block         attribute values of the instance (they include the mask
                fields IND/TYP/PER ... and the pin labels of a device);
                the block contents themselves are not searched
"""

import re

_FELDER = {
    "text": ("inhalt",),
    "bemassung": ("text_override",),
    "querverweis": ("text",),
    "vpunkt": ("wert",),
}
_WERTE = ("maske", "klemme", "kabel")


def _typ(el):
    return el.get("typ") if isinstance(el, dict) else getattr(el, "typ", None)


def _lies(halter, key):
    return halter.get(key) if isinstance(halter, dict) else getattr(halter, key, None)


def _schreibe(halter, key, wert):
    if isinstance(halter, dict):
        halter[key] = wert
    else:
        setattr(halter, key, wert)


class Treffer:
    """One place where the search text occurs."""
    __slots__ = ("blatt", "element", "art", "feld", "halter", "key", "text")

    def __init__(self, element, art, feld, halter, key):
        self.blatt = 0
        self.element = element
        self.art = art
        self.feld = feld
        self.halter = halter
        self.key = key
        self.text = _lies(halter, key)

    def setzen(self, neu):
        _schreibe(self.halter, self.key, neu)
        self.text = neu


def _muster(such, gross=False, wort=False):
    p = re.escape(such)
    if wort:
        p = r"(?<!\w)" + p + r"(?!\w)"
    return re.compile(p, 0 if gross else re.IGNORECASE)


def ersetzt(text, such, neu, gross=False, wort=False):
    """-> text with all occurrences replaced."""
    return _muster(such, gross, wort).sub(lambda m: neu, text)


def _felder_von(el):
    """Yields (art, feld, halter, key) of all text fields of one element."""
    typ = _typ(el)
    if typ in _FELDER:
        for k in _FELDER[typ]:
            yield typ, k, el, k
    elif typ in _WERTE:
        werte = _lies(el, "werte")
        if isinstance(werte, dict):
            for k in list(werte):
                yield typ, k, werte, k
    elif typ == "block":
        attr = _lies(el, "attribute")
        if isinstance(attr, dict):
            for k in list(attr):
                yield "block", k, attr, k


def suche(elemente, such, gross=False, wort=False):
    """All occurrences of `such` in a list of elements (objects or dicts)."""
    if not such:
        return []
    pat = _muster(such, gross, wort)
    out = []
    for el in elemente:
        for art, feld, halter, key in _felder_von(el):
            text = _lies(halter, key)
            if isinstance(text, str) and pat.search(text):
                out.append(Treffer(el, art, feld, halter, key))
    return out


def ersetze(treffer, such, neu, gross=False, wort=False):
    """Replaces in all given hits; returns the number of changed fields."""
    n = 0
    for t in treffer:
        t.text = _lies(t.halter, t.key)           # current value
        if isinstance(t.text, str):
            alt = t.text
            nt = ersetzt(alt, such, neu, gross, wort)
            if nt != alt:
                t.setzen(nt)
                n += 1
    return n


def suche_projekt(projekt, aktive_elemente, such, gross=False, wort=False,
                  ganzes_projekt=True, lade=None):
    """Searches the open sheet (live element objects) and, if wanted, all
    other sheets of the project (their JSON files).

    projekt: Projekt or None; lade(pfad) -> dict or None.
    Returns (hits, daten): daten = {sheet index: loaded JSON dict} of the
    other sheets, needed to write the changes back."""
    treffer, daten = [], {}
    aktiv = projekt.aktiv if projekt is not None else 0
    for t in suche(aktive_elemente, such, gross, wort):
        t.blatt = aktiv
        treffer.append(t)
    if projekt is not None and ganzes_projekt and lade is not None:
        for i in range(len(projekt.blaetter)):
            if i == aktiv:
                continue
            d = lade(projekt.blatt_pfad(i))
            if not isinstance(d, dict):
                continue
            hits = suche(d.get("elemente", []), such, gross, wort)
            if hits:
                daten[i] = d
                for t in hits:
                    t.blatt = i
                treffer.extend(hits)
    treffer.sort(key=lambda t: t.blatt)
    return treffer, daten
