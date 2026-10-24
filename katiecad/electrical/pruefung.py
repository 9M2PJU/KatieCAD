# -*- coding: utf-8 -*-
"""
katiecad/electrical/pruefung.py - Project checks (NO Tkinter).

pruefe(blaetter) -> list of Befund. `blaetter` is a list of
(sheet_index, sheet_name, [elements]).
"""

from collections import defaultdict

from katiecad.model.core import (Querverweis, BlockReferenz, ElektroMaske,
                                 Kabel, Klemme, Leitung)
from katiecad.common.i18n import tr
from katiecad.electrical.logic import REF_FELD, _pos, _nahe

FEHLER, WARNUNG, HINWEIS = "fehler", "warnung", "hinweis"
STUFEN = (FEHLER, WARNUNG, HINWEIS)


class Befund:
    __slots__ = ("stufe", "text", "blatt", "blatt_name", "x", "y")

    def __init__(self, stufe, text, blatt, blatt_name, x, y):
        self.stufe, self.text = stufe, text
        self.blatt, self.blatt_name, self.x, self.y = blatt, blatt_name, x, y

    def __repr__(self):
        return f"Befund({self.stufe}, {self.text!r}, {self.blatt_name})"


def _geraet_daten(el):
    """-> (per, rolle) of a device element or None."""
    if isinstance(el, ElektroMaske):
        return el.werte.get(REF_FELD, "").strip(), el.rolle
    if isinstance(el, BlockReferenz):
        m = el.geraet_maske()
        if m is not None:
            return str(el.attribute.get(REF_FELD, "")).strip(), m.rolle
    return None


def pruefe(blaetter):
    res = []

    def add(stufe, key, blatt, el, **kw):
        x, y = _pos(el)
        res.append(Befund(stufe, tr(key, **kw), blatt[0], blatt[1], x, y))

    haupt = defaultdict(list)       # per -> [(sheet, el)]
    hilfs = []
    kabel = defaultdict(list)
    klemmen = defaultdict(list)
    qvs = defaultdict(list)
    for b in blaetter:
        _i, _n, elemente = b
        for el in elemente:
            g = _geraet_daten(el)
            if g is not None:
                per, rolle = g
                if rolle == "haupt":
                    if not per:
                        add(WARNUNG, "pr.haupt_ohne_ind", b, el)
                    else:
                        haupt[per].append((b, el))
                elif rolle == "hilfs" and per:
                    hilfs.append((per, b, el))
            elif isinstance(el, Kabel):
                c = el.werte.get("CAB", "").strip()
                if c:
                    kabel[c].append((b, el))
            elif isinstance(el, Klemme):
                ind = el.werte.get("IND", "").strip()
                num = el.werte.get("NUM", "").strip()
                if ind or num:
                    klemmen[(ind, num)].append((b, el))
                _klemme_offen(el, elemente, b, res)
            elif isinstance(el, Querverweis) and el.text.strip():
                qvs[el.text.strip()].append((b, el))

    for per, liste in haupt.items():
        if len(liste) > 1:
            for b, el in liste:
                add(FEHLER, "pr.haupt_doppelt", b, el, per=per, n=len(liste))
    for c, liste in kabel.items():
        if len(liste) > 1:
            for b, el in liste:
                add(FEHLER, "pr.kabel_doppelt", b, el, per=c, n=len(liste))
    for per, b, el in hilfs:
        if per not in haupt:
            add(FEHLER, "pr.hilfs_ohne_haupt", b, el, per=per)
    for (ind, num), liste in klemmen.items():
        if len(liste) > 1:
            for b, el in liste:
                add(FEHLER, "pr.klemme_doppelt", b, el, ind=ind, num=num)
    for t, liste in qvs.items():
        n = len(liste)
        if n > 2:
            for b, el in liste:
                add(FEHLER, "pr.qv_mehrfach", b, el, text=t, n=n)
        elif n == 2:
            (b1, e1), (b2, e2) = liste
            if e1.art == e2.art:
                for b, el in liste:
                    add(WARNUNG, "pr.qv_gleiche_art", b, el, text=t,
                        art=tr("dlg.qv.art." + el.art))
        else:
            b, el = liste[0]
            if not el.extern:
                add(FEHLER, "pr.qv_ohne_gegenstueck", b, el, text=t)
    rang = {s: i for i, s in enumerate(STUFEN)}
    res.sort(key=lambda f: (rang[f.stufe], f.blatt, f.text))
    return res


def _klemme_offen(k, elemente, b, res):
    enden = []
    for l in elemente:
        if isinstance(l, Leitung):
            enden.append((l.x1, l.y1))
            enden.append((l.x2, l.y2))
    for name, p in (("oben", k.anschluss_oben()), ("unten", k.anschluss_unten())):
        if not any(_nahe(p, e) for e in enden):
            nm = (k.werte.get("IND", "") + ":" + k.werte.get("NUM", "")).strip(":")
            res.append(Befund(HINWEIS, tr("pr.klemme_offen", name=nm or "-",
                                          seite=tr("pr.seite." + name)),
                              b[0], b[1], k.x, k.y))


def bericht_text(befunde):
    """Plain-text report."""
    if not befunde:
        return tr("pr.ok")
    zeilen = []
    for f in befunde:
        zeilen.append(f"[{tr('pr.stufe.' + f.stufe)}] {f.blatt_name}: {f.text}")
    return "\n".join(zeilen)
