# -*- coding: utf-8 -*-
"""
katiecad/fileio/dxf_projekt.py - Whole project as ONE DXF file.

All sheets are evaluated exactly like when printing (layout with frame,
title block and viewports) and placed side by side in the model space of
one DXF file: N sheets per row, then a new row. Contains NO Tkinter.
"""
import math

from katiecad.model.core import (ZEICHNUNGSFORMATE, clip_polyline,
                                 TEXT_ZEILE)
from katiecad.fileio.pdf import pdf_seite_erzeugen

VALID_LW = (0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90,
            100, 106, 120, 140, 158, 200, 211)


def _clip_flaeche(pts, rect):
    """Sutherland-Hodgman: polygon clipped to a rectangle."""
    xmin, ymin, xmax, ymax = rect

    def runde(poly, inside, schnitt):
        out = []
        for i, cur in enumerate(poly):
            prev = poly[i - 1]
            ci, pi = inside(cur), inside(prev)
            if ci:
                if not pi:
                    out.append(schnitt(prev, cur))
                out.append(cur)
            elif pi:
                out.append(schnitt(prev, cur))
        return out

    def sx(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / ((b[0] - a[0]) or 1e-12))

    def sy(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / ((b[1] - a[1]) or 1e-12), y)

    poly = list(pts)
    for inside, sch in ((lambda p: p[0] >= xmin, sx(xmin)),
                        (lambda p: p[0] <= xmax, sx(xmax)),
                        (lambda p: p[1] >= ymin, sy(ymin)),
                        (lambda p: p[1] <= ymax, sy(ymax))):
        if not poly:
            break
        poly = runde(poly, inside, sch)
    return poly


class DxfSeite:
    """Collects the drawing operations of one sheet (same interface as
    PdfSeite), clipped to the viewports."""

    def __init__(self, breite_mm, hoehe_mm):
        self.b, self.h = float(breite_mm), float(hoehe_mm)
        self.ops = []
        self._clips = []

    def clip_start(self, x1, y1, x2, y2):
        self._clips.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))

    def clip_ende(self):
        if self._clips:
            self._clips.pop()

    def _clip(self):
        return self._clips[-1] if self._clips else None

    def linie(self, pts, breite, farbe="#000000", dash=None, geschlossen=False):
        if len(pts) < 2:
            return
        c = self._clip()
        if c is None:
            self.ops.append(("l", list(pts), breite, farbe, dash, geschlossen))
            return
        pts = list(pts)
        if geschlossen:
            if all(c[0] <= x <= c[2] and c[1] <= y <= c[3] for x, y in pts):
                self.ops.append(("l", pts, breite, farbe, dash, True))
                return
            pts = pts + [pts[0]]
        for teil in clip_polyline(pts, c):
            self.ops.append(("l", teil, breite, farbe, dash, False))

    def flaeche(self, pts, farbe="#000000"):
        if len(pts) < 3:
            return
        c = self._clip()
        poly = _clip_flaeche(pts, c) if c else list(pts)
        if len(poly) >= 3:
            self.ops.append(("f", poly, farbe))

    def text(self, x, y, inhalt, hoehe, winkel=0.0, farbe="#000000", mitte=False):
        c = self._clip()
        if c and not (c[0] <= x <= c[2] and c[1] <= y <= c[3]):
            return
        self.ops.append(("t", x, y, inhalt, hoehe, winkel, farbe, mitte))


def _rgb(hexfarbe):
    try:
        h = hexfarbe.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return (0, 0, 0)


def _farbattribute(hexfarbe):
    rgb = _rgb(hexfarbe)
    if rgb == (0, 0, 0):
        return {"color": 7}                   # black on white / white on black
    return {"true_color": (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]}


def _lineweight(breite_mm):
    h = int(round(breite_mm * 100))
    return min(VALID_LW, key=lambda v: abs(v - h))


def gitter_positionen(n, zelle_b, zelle_h, spalten=4, abstand=50.0):
    """Lower left corner of every sheet: `spalten` per row, rows downwards."""
    out = []
    for i in range(n):
        r, c = divmod(i, spalten)
        out.append((c * (zelle_b + abstand), -r * (zelle_h + abstand)))
    return out


def seiten_sammeln(kontexte, vp_rahmen=False):
    """kontexte: [(name, ctx)] -> ([(name, DxfSeite)], skipped names)."""
    seiten, uebersprungen = [], []
    for name, ctx in kontexte:
        try:
            seiten.append((name, pdf_seite_erzeugen(
                ctx, "layout", True, vp_rahmen, seite_klasse=DxfSeite)))
        except Exception:
            uebersprungen.append(name)
    return seiten, uebersprungen


def dxf_projekt_schreiben(doc, seiten, spalten=4, abstand=50.0):
    """Places the collected sheets into the model space of `doc`."""
    from katiecad.common.i18n import tr
    msp = doc.modelspace()
    if not seiten:
        return
    zb = max(s.b for _n, s in seiten)
    zh = max(s.h for _n, s in seiten)
    pos = gitter_positionen(len(seiten), zb, zh, spalten, abstand)
    for nm in ("Blattgrenze", "Blattnamen"):
        if nm not in doc.layers:
            doc.layers.add(nm, color=8 if nm == "Blattgrenze" else 7)
    for idx, ((name, s), (ox, oy)) in enumerate(zip(seiten, pos), 1):
        layer = "Blatt_%02d" % idx
        if layer not in doc.layers:
            doc.layers.add(layer, color=7)
        msp.add_lwpolyline([(ox, oy), (ox + s.b, oy), (ox + s.b, oy + s.h),
                            (ox, oy + s.h)], close=True,
                           dxfattribs={"layer": "Blattgrenze", "color": 8})
        msp.add_text(name, dxfattribs={"layer": "Blattnamen", "height": 5.0}
                     ).set_placement((ox, oy + s.h + 4.0))
        for op in s.ops:
            k = op[0]
            if k == "l":
                _, pts, breite, farbe, dash, geschl = op
                att = {"layer": layer, "lineweight": _lineweight(breite)}
                att.update(_farbattribute(farbe))
                msp.add_lwpolyline([(x + ox, y + oy) for x, y in pts],
                                   close=bool(geschl), dxfattribs=att)
            elif k == "f":
                _, pts, farbe = op
                h = msp.add_hatch(dxfattribs={"layer": layer,
                                              **_farbattribute(farbe)})
                h.paths.add_polyline_path([(x + ox, y + oy) for x, y in pts],
                                          is_closed=True)
            else:
                _, x, y, inhalt, hoehe, winkel, farbe, mitte = op
                _text_schreiben(msp, layer, inhalt, x + ox, y + oy, hoehe,
                                winkel, farbe, mitte)


def _text_schreiben(msp, layer, inhalt, x, y, hoehe, winkel, farbe, mitte):
    a = math.radians(winkel)
    ey = (-math.sin(a), math.cos(a))
    zeilen = inhalt.split("\n") or [""]
    n = len(zeilen)
    for i, z in enumerate(zeilen):
        if not z:
            continue
        up = (n - 1 - i) * TEXT_ZEILE * hoehe
        px, py = x + ey[0] * up, y + ey[1] * up
        att = {"layer": layer, "height": hoehe, "rotation": winkel}
        att.update(_farbattribute(farbe))
        t = msp.add_text(z, dxfattribs=att)
        if mitte:
            try:
                from ezdxf.enums import TextEntityAlignment as A
                t.set_placement((px, py), align=A.MIDDLE_CENTER)
                continue
            except Exception:
                pass
        t.set_placement((px, py))
