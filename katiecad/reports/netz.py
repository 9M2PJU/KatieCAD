# -*- coding: utf-8 -*-
"""
katiecad/reports/netz.py - Net tracing across all sheets (NO Tkinter).

A graph is built from the connection points (pins, terminals, junctions,
cross references) and the wires of all sheets. From a terminal side or a
cable end it can then be determined WHERE a wire leads to
(device:pin, terminal, potential reference) - also across junctions, cables
and sheet boundaries.

Rules
  * Pins and terminals are end points: the search does not pass through them.
  * A junction connects all its arms; a crossing (4 arms) without a
    dot connects only opposite arms.
  * Two connection points of different objects that lie exactly on top of
    each other (< 0.1 mm) count as connected.
  * Cross references with the same text continue the wire on another sheet
    if there is exactly ONE outgoing and at least one incoming one
    (or vice versa). Otherwise the cross reference stays an end point
    (e.g. a potential like L1 that occurs in many places).
"""

import math
from collections import defaultdict

from katiecad.model.core import (BlockReferenz, Verbindungspunkt, Verbindung,
                                 Klemme, Querverweis, Leitung, Kabel)

SUCH_TOL = 0.4          # mm: wire end -> connection point
BERUEHRUNG = 0.1        # mm: coinciding connection points
ZELLE = 1.0             # mm: grid size for the neighbourhood search
ADER_TOL = 1.0          # mm: wire -> nearest core crossing of the cable


class Knoten:
    __slots__ = ("blatt", "x", "y", "art", "bes", "kennz", "name", "seite",
                 "kanten", "text", "qv_art", "partner")

    def __init__(self, blatt, x, y, art, bes=None, kennz="", name="",
                 seite="", text="", qv_art=""):
        self.blatt, self.x, self.y, self.art = blatt, x, y, art
        self.bes = bes                  # Owner (element), for comparison
        self.kennz = kennz              # Device / terminal strip
        self.name = name                # Pin or terminal number
        self.seite = seite              # Terminal: "oben" | "unten"
        self.kanten = []
        self.text = text                # Cross-reference text
        self.qv_art = qv_art
        self.partner = []               # Cross-reference counterparts


class Kante:
    __slots__ = ("a", "b", "kabel")

    def __init__(self, a, b, kabel=None):
        self.a, self.b, self.kabel = a, b, kabel   # cable: (CAB, core) | None


def _verbinden(a, b, kabel=None):
    if a is b:
        return None
    k = Kante(a, b, kabel)
    a.kanten.append(k)
    b.kanten.append(k)
    return k


def leisten_ermitteln(klemmen):
    """Terminal strip of every terminal of ONE sheet: {id(terminal): IND}.
    A terminal without IND inherits the strip of the nearest terminal to its
    left in the same row (the strip is usually entered at the first terminal)."""
    reihen = []
    for k in sorted(klemmen, key=lambda c: (c.y, c.x)):
        if reihen and abs(reihen[-1][0] - k.y) <= 0.5:
            reihen[-1][1].append(k)
        else:
            reihen.append([k.y, [k]])
    out = {}
    for _y, reihe in reihen:
        aktuell = ""
        for k in sorted(reihe, key=lambda c: c.x):
            kz = wert_gesetzt(k.werte.get("IND"), "IND")
            if kz:
                aktuell = kz
            out[id(k)] = kz or aktuell
    return out


def wert_gesetzt(wert, tag):
    """Field value without placeholder: empty or equal to the field name ('IND'
    in field IND, as shown by a symbol's template) counts as not filled in."""
    w = ("" if wert is None else str(wert)).strip()
    return "" if w.upper() == str(tag).upper() else w


class Netz:
    def __init__(self):
        self.knoten = []
        self._raster = defaultdict(list)
        self.klemmen = []        # {"obj", "blatt", "oben", "unten"}
        self.kabel = []          # {"obj", "blatt", "adern": [{"name","kanten"}]}
        self._leitung = {}       # id(wire) -> edge

    # ---- Construction ---------------------------------------------
    def _neu(self, blatt, x, y, art, **kw):
        n = Knoten(blatt, x, y, art, **kw)
        self.knoten.append(n)
        self._raster[(blatt, int(math.floor(x / ZELLE)),
                      int(math.floor(y / ZELLE)))].append(n)
        return n

    def _naehe(self, blatt, x, y, tol):
        gx, gy = int(math.floor(x / ZELLE)), int(math.floor(y / ZELLE))
        r = int(math.ceil(tol / ZELLE))
        for ix in range(gx - r, gx + r + 1):
            for iy in range(gy - r, gy + r + 1):
                for k in self._raster.get((blatt, ix, iy), ()):
                    d = math.hypot(k.x - x, k.y - y)
                    if d <= tol:
                        yield d, k

    def _finde(self, blatt, x, y):
        best = min(self._naehe(blatt, x, y, SUCH_TOL), default=None,
                   key=lambda t: t[0])
        return best[1] if best else None

    def _anker(self, blatt, k, bes, kennz):
        if isinstance(k, Verbindungspunkt):
            self._neu(blatt, k.x, k.y, "pin", bes=bes, kennz=kennz,
                      name=(k.wert or "").strip())
        elif isinstance(k, Verbindung):
            arme = [(self._neu(blatt, ax, ay, "verb", bes=bes), d)
                    for (ax, ay, d) in k.anschluesse()]
            kreuzung = len(k.arme) == 4 and not k.punkt
            for i, (a, da) in enumerate(arme):
                for b, db in arme[i + 1:]:
                    if not kreuzung or (da - db) % 360 == 180:
                        _verbinden(a, b)
        elif isinstance(k, Klemme):
            ox, oy = k.anschluss_oben()
            ux, uy = k.anschluss_unten()
            kz = wert_gesetzt(k.werte.get("IND"), "IND")
            nm = wert_gesetzt(k.werte.get("NUM"), "NUM")
            oben = self._neu(blatt, ox, oy, "klemme", bes=bes, kennz=kz,
                             name=nm, seite="oben")
            unten = self._neu(blatt, ux, uy, "klemme", bes=bes, kennz=kz,
                              name=nm, seite="unten")
            self.klemmen.append({"obj": k, "blatt": blatt, "leiste": kz,
                                 "oben": oben, "unten": unten})
        elif isinstance(k, Querverweis):
            if k.art == "abgehend":
                x, y = k.basis_punkt()
            else:
                x, y = k.spitze_punkt()
            self._neu(blatt, x, y, "qv", bes=bes, text=k.text.strip(),
                      qv_art="extern" if k.extern else k.art)

    def _leisten_erben(self, klemmen):
        """Terminals without a terminal strip inherit that of the nearest terminal to
        their left in the same row (the strip is usually entered only at the
        first terminal)."""
        zuordnung = leisten_ermitteln([kl["obj"] for kl in klemmen])
        for kl in klemmen:
            if not kl["leiste"] and zuordnung.get(id(kl["obj"])):
                kl["leiste"] = zuordnung[id(kl["obj"])]
                kl["geerbt"] = True
                kl["oben"].kennz = kl["unten"].kennz = kl["leiste"]

    def blatt_hinzufuegen(self, blatt, elemente):
        """`blatt`: arbitrary key (e.g. 0-based index)."""
        start = len(self.knoten)
        start_kl = len(self.klemmen)
        for el in elemente:
            if isinstance(el, BlockReferenz):
                kz = (wert_gesetzt(el.attribute.get("IND"), "IND")
                      or str(el.block_name))
                for k in el.aufgeloest():
                    self._anker(blatt, k, el, kz)
            else:
                self._anker(blatt, el, el, "")
        self._leisten_erben(self.klemmen[start_kl:])
        neue = self.knoten[start:]
        # coinciding connections of different objects
        for n in neue:
            for _d, m in self._naehe(blatt, n.x, n.y, BERUEHRUNG):
                if m is not n and m.bes is not n.bes and id(m) > id(n):
                    _verbinden(n, m)
        # Wires
        for l in elemente:
            if not isinstance(l, Leitung):
                continue
            a = (self._finde(blatt, l.x1, l.y1)
                 or self._neu(blatt, l.x1, l.y1, "frei"))
            b = (self._finde(blatt, l.x2, l.y2)
                 or self._neu(blatt, l.x2, l.y2, "frei"))
            k = _verbinden(a, b)
            if k is not None:
                self._leitung[id(l)] = k
        self._kabel_adern(blatt, elemente)

    def _kabel_adern(self, blatt, elemente):
        kabel = [k for k in elemente if isinstance(k, Kabel)]
        if not kabel:
            return
        senkrecht = [l for l in elemente if isinstance(l, Leitung)
                     and abs(l.x1 - l.x2) <= 0.05 and id(l) in self._leitung]
        for kb in kabel:
            xs = sorted(kb.kreuzungen)
            adern = [{"name": kb.ader_name(i, cx - kb.x), "x": cx, "kanten": []}
                     for i, cx in enumerate(xs)]
            for l in senkrecht:
                lo, hi = sorted((l.y1, l.y2))
                if not (lo + 0.05 < kb.y < hi - 0.05):
                    continue
                if not (kb.x + 0.05 < l.x1 <= kb.x + kb.laenge + 0.05):
                    continue
                if not adern:
                    continue
                best = min(adern, key=lambda a: abs(a["x"] - l.x1))
                if abs(best["x"] - l.x1) <= ADER_TOL:
                    kante = self._leitung[id(l)]
                    kante.kabel = (kb.werte.get("CAB", "").strip(), best["name"])
                    best["kanten"].append(kante)
            self.kabel.append({"obj": kb, "blatt": blatt, "adern": adern})

    def abschliessen(self):
        """Determine cross-reference counterparts (after the last sheet)."""
        gruppen = defaultdict(list)
        for n in self.knoten:
            if n.art == "qv" and n.text:
                gruppen[n.text].append(n)
        for g in gruppen.values():
            ab = [n for n in g if n.qv_art == "abgehend"]
            an = [n for n in g if n.qv_art == "ankommend"]
            if len(ab) == 1 and an:
                ab[0].partner = list(an)
                for n in an:
                    n.partner = list(ab)
            elif len(an) == 1 and ab:
                an[0].partner = list(ab)
                for n in ab:
                    n.partner = list(an)

    @classmethod
    def aufbauen(cls, blaetter):
        """blaetter: [(key, elements), ...]"""
        netz = cls()
        for schluessel, elemente in blaetter:
            netz.blatt_hinzufuegen(schluessel, elemente)
        netz.abschliessen()
        return netz

    # ---- Queries ----------------------------------------------------
    def ziele(self, start, ohne=()):
        """All end points reachable from `start`.
        -> [(node, cable_infos)], cable_infos = ((CAB, core), ...)
        `ohne`: edges that must not be used."""
        verboten = {id(k) for k in ohne}
        out = []
        gesehen = {id(start)}
        stapel = [(start, ())]
        while stapel:
            n, via = stapel.pop()
            for k in n.kanten:
                if id(k) in verboten:
                    continue
                m = k.b if k.a is n else k.a
                if id(m) in gesehen:
                    continue
                gesehen.add(id(m))
                v = via + ((k.kabel,) if k.kabel else ())
                if m.art in ("pin", "klemme"):
                    out.append((m, v))
                elif m.art == "qv":
                    if m.partner:
                        for p in m.partner:
                            if id(p) not in gesehen:
                                gesehen.add(id(p))
                                stapel.append((p, v))
                    else:
                        out.append((m, v))
                else:
                    stapel.append((m, v))
        return out


def ende_ziele(netz, knoten, kante):
    """Targets at the end of a core/wire `kante` at `knoten`: the end point
    itself (pin, terminal, cross reference) or, if a junction sits there,
    everything attached behind it."""
    if knoten.art in ("pin", "klemme") or (knoten.art == "qv" and not knoten.partner):
        return [(knoten, ())]
    if knoten.art == "qv":
        out = []
        for p in knoten.partner:
            out.extend(netz.ziele(p))
        return out
    return netz.ziele(knoten, ohne=[kante])


def knoten_text(n):
    """Readable name of an end point: 'K1:13', 'X1:3', '→ L1'."""
    if n.art == "qv":
        return "→ " + n.text
    if n.kennz and n.name:
        return f"{n.kennz}:{n.name}"
    return n.kennz or n.name or "?"


def ziele_texte(treffer, eigener_besitzer=None):
    """Sorted, unique texts; cables the path passes through are given
    in brackets: 'K1:13 (W1/L1)'."""
    gesehen = {}
    for n, via in treffer:
        if eigener_besitzer is not None and n.bes is eigener_besitzer:
            continue
        t = knoten_text(n)
        if via:
            t += " (" + " ".join(f"{c}/{a}" if c else a for c, a in via) + ")"
        gesehen.setdefault(t, True)
    return sorted(gesehen, key=natuerlich)


def natuerlich(s):
    """Sort key: 'X10' after 'X2'."""
    import re
    return tuple((0, int(t)) if t.isdigit() else (1, t.lower())
                 for t in re.split(r"(\d+)", str(s)) if t != "")
