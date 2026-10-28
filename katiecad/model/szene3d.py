# -*- coding: utf-8 -*-
"""
katiecad/model/szene3d.py - Scene logic of the 3D wireframe view (NO Tkinter).

Collects the 3D bodies and the flat 2D drawing of a sheet, picks objects,
and does the maths of the 3D manipulator (X/Y/Z arrows).
"""

import math

from katiecad.model.core import (Koerper3D, Gruppe3D, Linie, Rechteck, Polylinie, Kreis,
                                 Bogen, ZUSAMMENGESETZT, bogen_punkte, bogen_sweep,
                                 profil_aus_element, extrusion)
from katiecad.model import geom3d as G

KOERPER_TYPEN = (Koerper3D, Gruppe3D)


def ist_3d(el):
    return isinstance(el, KOERPER_TYPEN)


def koerper_netze(elemente):
    """[(top-level element, Netz)] of all 3D bodies."""
    out = []
    for el in elemente:
        if ist_3d(el):
            for nz in el.netze():
                out.append((el, nz))
    return out


def flache_zuege(el):
    """2D polylines [(points, closed)] of a 2D element or composite (3D bodies
    are skipped: they are drawn as solids)."""
    if ist_3d(el):
        return []
    if isinstance(el, Linie):
        return [([(el.x1, el.y1), (el.x2, el.y2)], False)]
    if isinstance(el, Rechteck):
        return [([(el.x1, el.y1), (el.x2, el.y1), (el.x2, el.y2), (el.x1, el.y2)], True)]
    if isinstance(el, Polylinie):
        return [(list(el.punkte), bool(el.geschlossen))] if len(el.punkte) >= 2 else []
    if isinstance(el, Kreis):
        n = 48
        return [([(el.cx + el.r * math.cos(2 * math.pi * i / n),
                   el.cy + el.r * math.sin(2 * math.pi * i / n)) for i in range(n)], True)]
    if isinstance(el, Bogen):
        sw = bogen_sweep(el.start, el.ende)
        n = max(8, int(sw / 6))
        return [(bogen_punkte(el.cx, el.cy, el.r, el.start, el.ende, n), False)]
    if isinstance(el, ZUSAMMENGESETZT):
        out = []
        for k in el.aufgeloest():
            out.extend(flache_zuege(k))
        return out
    return []


def szene_punkte(elemente):
    """All 3D points of the scene (2D shapes at z = 0) for 'zoom extents'."""
    pts = []
    for _el, nz in koerper_netze(elemente):
        pts.extend(nz.punkte)
    for el in elemente:
        for zug, _c in flache_zuege(el):
            pts.extend((x, y, 0.0) for (x, y) in zug)
    return pts


def _abstand_zug(kamera, cx, cy, mx, my, zug, geschlossen):
    pts = list(zug) + ([zug[0]] if geschlossen and len(zug) > 2 else [])
    best = None
    for a, b in zip(pts, pts[1:]):
        seg = kamera.proj_segment((a[0], a[1], 0.0), (b[0], b[1], 0.0), cx, cy)
        if seg is None:
            continue
        d = G.abstand_punkt_segment(mx, my, seg[0], seg[1])
        if best is None or d < best:
            best = d
    return best


def pick(elemente, kamera, cx, cy, mx, my, tol=8.0):
    """Object under the screen point: 3D bodies first, then 2D shapes."""
    best, bd = None, None
    for el, nz in koerper_netze(elemente):
        d = G.abstand_zu_netz(nz, kamera, cx, cy, mx, my)
        if d is not None and d <= tol and (bd is None or d < bd):
            best, bd = el, d
    if best is not None:
        return best
    for el in reversed(elemente):
        if ist_3d(el):
            continue
        for zug, geschlossen in flache_zuege(el):
            d = _abstand_zug(kamera, cx, cy, mx, my, zug, geschlossen)
            if d is not None and d <= tol and (bd is None or d < bd):
                best, bd = el, d
    return best


def auswahl_zentrum3(auswahl):
    """Centre of the bounding box of the selection in 3D (2D shapes at z = 0)."""
    xs, ys, zs = [], [], []
    for el in auswahl:
        if ist_3d(el):
            b = el.bbox3()
            if b:
                xs += [b[0], b[3]]; ys += [b[1], b[4]]; zs += [b[2], b[5]]
        elif hasattr(el, "bbox"):
            b = el.bbox()
            xs += [b[0], b[2]]; ys += [b[1], b[3]]; zs += [0.0]
    if not xs:
        return None
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)


def extrudierbar(el):
    return (not ist_3d(el)) and profil_aus_element(el) is not None


# --------------------------------------------------------------------------
# Manipulator (axes X / Y / Z)
# --------------------------------------------------------------------------
ACHSEN = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}


def achsen_info(kamera, zentrum, cx, cy, laenge_px=70.0):
    """For each axis: {"von": (x, y), "bis": (x, y), "dir": (ux, uy) unit vector
    on the screen, "px_pro_mm": scale along the axis}. Axes pointing at the
    viewer (almost zero length on screen) are left out."""
    p0 = kamera.proj(zentrum, cx, cy)
    if p0 is None:
        return {}
    L = laenge_px / max(kamera.skala, 1e-9)
    out = {}
    for name, a in ACHSEN.items():
        q = (zentrum[0] + a[0] * L, zentrum[1] + a[1] * L, zentrum[2] + a[2] * L)
        p1 = kamera.proj(q, cx, cy)
        if p1 is None:
            continue
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        l = math.hypot(dx, dy)
        if l < 12.0:
            continue
        out[name] = {"von": (p0[0], p0[1]), "bis": (p1[0], p1[1]),
                     "dir": (dx / l, dy / l), "px_pro_mm": l / L}
    return out


def manip_treffer(infos, mx, my, tol=7.0):
    best, bd = None, None
    for name, i in infos.items():
        d = G.abstand_punkt_segment(mx, my, i["von"], i["bis"])
        if d <= tol and (bd is None or d < bd):
            best, bd = name, d
    return best


def verschiebung_mm(info, dx_px, dy_px, raster=None):
    """Signed distance along the axis for a mouse movement of (dx, dy) pixels."""
    mm = (dx_px * info["dir"][0] + dy_px * info["dir"][1]) / info["px_pro_mm"]
    if raster and raster > 0:
        mm = round(mm / raster) * raster
    return mm


def verschieben_achse(auswahl, achse, mm):
    a = ACHSEN[achse]
    for el in auswahl:
        if hasattr(el, "verschieben"):
            if ist_3d(el):
                el.verschieben(a[0] * mm, a[1] * mm, a[2] * mm)
            elif achse != "z":
                el.verschieben(a[0] * mm, a[1] * mm)


def gruppe_bilden(elemente, auswahl, name="3D-Block"):
    """Puts the selected 3D bodies into one Gruppe3D (replaces them in `elemente`).
    Returns the group or None."""
    teile = [e for e in auswahl if ist_3d(e)]
    if len(teile) < 2:
        return None
    ids = {id(t) for t in teile}
    pos = min(i for i, e in enumerate(elemente) if id(e) in ids)
    rest = [e for e in elemente if id(e) not in ids]
    g = Gruppe3D(teile, name, layer=teile[0].layer, farbe=teile[0].farbe,
                 linientyp=teile[0].linientyp, eig_farbe=teile[0].eig_farbe,
                 staerke=teile[0].staerke)
    rest.insert(min(pos, len(rest)), g)
    elemente[:] = rest
    return g


def gruppe_aufloesen(elemente, gruppen):
    """Replaces the groups by their parts; returns the freed parts."""
    frei = []
    for g in gruppen:
        if not isinstance(g, Gruppe3D) or g not in elemente:
            continue
        i = next(k for k, e in enumerate(elemente) if e is g)
        elemente[i:i + 1] = g.teile
        frei.extend(g.teile)
    return frei


def extrudieren(elemente, ziele, hoehe, z0=0.0, original_behalten=False):
    """Replaces the closed 2D shapes `ziele` by prisms of the given (signed) height."""
    neu = []
    for el in ziele:
        k = extrusion(el, hoehe, z0)
        if k is None:
            continue
        if not original_behalten:
            for i, e in enumerate(elemente):
                if e is el:
                    elemente[i] = k
                    break
        else:
            elemente.append(k)
        neu.append(k)
    return neu
