# -*- coding: utf-8 -*-
"""
katiecad/model/szene3d.py - Scene logic of the 3D wireframe view (NO Tkinter).

Collects the 3D bodies and the flat 2D drawing of a sheet, picks objects,
and does the maths of the 3D manipulator (X/Y/Z arrows).
"""

import math

from katiecad.model.core import (Koerper3D, Gruppe3D, Skizze3D, Bemassung3D, Linie, Rechteck,
                                 Polylinie, Kreis, Bogen, ZUSAMMENGESETZT, bogen_punkte,
                                 bogen_sweep, profil_aus_element, extrusion)
from katiecad.model import geom3d as G

KOERPER_TYPEN = (Koerper3D, Gruppe3D)


RAUM_TYPEN = (Koerper3D, Gruppe3D, Skizze3D, Bemassung3D)


def ist_3d(el):
    return isinstance(el, KOERPER_TYPEN)


def ist_raum(el):
    """Elements with real 3D coordinates (bodies, sketches on planes, 3D dimensions)."""
    return isinstance(el, RAUM_TYPEN)


def zuege3(el):
    """3D polylines [(points, closed)] of every non-body element (2D shapes at z = 0)."""
    if isinstance(el, Skizze3D):
        pts = el.zug3()
        return [(pts, True)] if len(pts) >= 2 else []
    if isinstance(el, Bemassung3D):
        return [(z, False) for z in el.zuege3()]
    return [([(x, y, 0.0) for (x, y) in zug], closed) for zug, closed in flache_zuege(el)]


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
        if ist_3d(el):
            continue
        for zug, _c in zuege3(el):
            pts.extend(zug)
    return pts


def _abstand_zug(kamera, cx, cy, mx, my, zug, geschlossen):
    pts = list(zug) + ([zug[0]] if geschlossen and len(zug) > 2 else [])
    best = None
    for a, b in zip(pts, pts[1:]):
        seg = kamera.proj_segment(a, b, cx, cy)
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
        for zug, geschlossen in zuege3(el):
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
        elif ist_raum(el):
            c = el.zentrum3()
            xs.append(c[0]); ys.append(c[1]); zs.append(c[2])
        elif hasattr(el, "bbox"):
            b = el.bbox()
            xs += [b[0], b[2]]; ys += [b[1], b[3]]; zs += [0.0]
    if not xs:
        return None
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)


def extrudierbar(el):
    if isinstance(el, Skizze3D):
        return len(el.profil()) >= 3
    return (not ist_raum(el)) and profil_aus_element(el) is not None


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
            if ist_raum(el):
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


# --------------------------------------------------------------------------
# Holes (bores)
# --------------------------------------------------------------------------
def loch_ziele(auswahl):
    """Prism bodies of the selection (also inside 3D blocks) that can get a hole."""
    out = []
    for el in auswahl:
        if ist_3d(el):
            out.extend(k for k in el.koerper() if k.art == "prisma")
    return out


def loch_oben_z(koerper):
    return max(koerper.z0, koerper.z0 + koerper.hoehe)


def loch_setzen(koerper, x, y, r, tiefe=None):
    """Adds a hole; False if the centre lies outside the base polygon."""
    if koerper.art != "prisma" or r <= 0:
        return False
    if koerper.profil and not G.punkt_in_polygon(x, y, koerper.profil):
        return False
    koerper.loch_hinzufuegen(x, y, r, tiefe)
    return True


# --------------------------------------------------------------------------
# Faces, work planes, sketches
# --------------------------------------------------------------------------
def flaeche_pick(elemente, kamera, cx, cy, mx, my):
    """Face of a body under the screen point -> (body, plane, face points) or None."""
    o, d = kamera.strahl(mx, my, cx, cy)
    best = None
    for el in elemente:
        if not ist_3d(el):
            continue
        for k in el.koerper():
            nz = k.netz()
            tr_ = G.flaeche_treffer(nz, o, d)
            if tr_ is None or (best is not None and tr_[0] >= best[0]):
                continue
            pts = [nz.punkte[i] for i in nz.flaechen[tr_[1]]]
            e = G.ebene_von_flaeche(pts, k.zentrum3())
            if e is not None:
                best = (tr_[0], k, e, pts)
    if best is None:
        return None
    return best[1], best[2], best[3]


def punkt_auf_ebene(kamera, cx, cy, mx, my, ebene, raster=None):
    """Local plane coordinates (x, y) under the screen point (grid snapped) or None."""
    o, d = kamera.strahl(mx, my, cx, cy)
    p = G.strahl_auf_ebene(ebene, o, d)
    if p is None:
        return None
    if raster and raster > 0:
        p = (round(p[0] / raster) * raster, round(p[1] / raster) * raster)
    return p


def fang_punkt(elemente, kamera, cx, cy, mx, my, tol=12.0):
    """Nearest vertex of the scene (body corners, 2D end points) within `tol` pixels."""
    best, bd = None, tol
    kand = []
    for _el, nz in koerper_netze(elemente):
        kand.extend(nz.punkte)
    for el in elemente:
        if ist_3d(el) or isinstance(el, Bemassung3D):
            continue
        for zug, _c in zuege3(el):
            kand.extend(zug)
    for p in kand:
        q = kamera.proj(p, cx, cy)
        if q is None:
            continue
        d = math.hypot(q[0] - mx, q[1] - my)
        if d < bd:
            best, bd = p, d
    return best


def host_finden(elemente, ebene):
    """Body whose face lies in the work plane `ebene` (and contains its origin / sketch)."""
    u, v, w = G.ebene_basis(ebene)
    for el in elemente:
        if not ist_3d(el):
            continue
        for k in el.koerper():
            if k.art != "prisma":
                continue
            nz = k.netz()
            zen = k.zentrum3()
            for f in nz.flaechen:
                pts = [nz.punkte[i] for i in f]
                e2 = G.ebene_von_flaeche(pts, zen)
                if e2 is None:
                    continue
                w2 = G.ebene_basis(e2)[2]
                if G.v_dot(w, w2) < 0.999:
                    continue
                if abs(G.v_dot(G.v_sub(tuple(ebene[:3]), tuple(e2[:3])), w2)) > 1e-3:
                    continue
                return k
    return None


def skizze_in_ausschnitt(elemente, skizze, tiefe=None):
    """Cuts the sketch into the body it lies on (hole / pocket); True if done."""
    host = host_finden(elemente, skizze.ebene)
    prof = skizze.profil()
    if host is None or len(prof) < 3:
        return False
    host.ausschnitt_hinzufuegen(skizze.ebene, prof, tiefe, skizze.rund())
    for i, e in enumerate(elemente):
        if e is skizze:
            del elemente[i]
            break
    return True


def extrusion_abschliessen(elemente, koerper):
    """After pulling a sketch downwards (negative height) the prism becomes a
    pocket of the body it was sitting on. True if converted."""
    if not isinstance(koerper, Koerper3D) or not koerper.ebene or koerper.hoehe >= -1e-9:
        return False
    host = host_finden([e for e in elemente if e is not koerper], koerper.ebene)
    if host is None:
        return False
    host.ausschnitt_hinzufuegen(koerper.ebene, koerper.profil, abs(koerper.hoehe), koerper.rund)
    for i, e in enumerate(elemente):
        if e is koerper:
            del elemente[i]
            break
    return True


# --------------------------------------------------------------------------
# Dimensions of a body (size editing)
# --------------------------------------------------------------------------
def _profil_art(k):
    pr = k.profil
    if len(pr) == 4:
        xs = sorted(set(round(p[0], 6) for p in pr)); ys = sorted(set(round(p[1], 6) for p in pr))
        if len(xs) == 2 and len(ys) == 2:
            return "rechteck"
    if k.rund and len(pr) >= 8:
        return "kreis"
    return "frei"


def parameter(el):
    """[(key, value_mm)] that can be edited for a body / sketch; [] if none."""
    if isinstance(el, Koerper3D):
        if el.art == "kugel" and el.kugel:
            return [("radius", el.kugel[3])]
        art = _profil_art(el)
        out = []
        if art == "rechteck":
            xs = [p[0] for p in el.profil]; ys = [p[1] for p in el.profil]
            out += [("breite", max(xs) - min(xs)), ("tiefe", max(ys) - min(ys))]
        elif art == "kreis":
            cx = sum(p[0] for p in el.profil) / len(el.profil)
            cy = sum(p[1] for p in el.profil) / len(el.profil)
            out.append(("radius", max(math.hypot(p[0] - cx, p[1] - cy) for p in el.profil)))
        else:
            out.append(("faktor", 100.0))
        if el.art in ("prisma", "pyramide"):
            out.append(("hoehe", abs(el.hoehe)))
        return out
    if isinstance(el, Skizze3D):
        d = el.daten
        if el.form == "kreis" and len(d) >= 3:
            return [("radius", d[2])]
        if el.form == "rechteck" and len(d) >= 4:
            return [("breite", abs(d[2] - d[0])), ("tiefe", abs(d[3] - d[1]))]
    return []


def parameter_setzen(el, par):
    """Applies the values of `par` (key -> mm); bodies keep their lower left corner /
    centre. Returns True if something changed."""
    if isinstance(el, Skizze3D):
        d = el.daten
        if el.form == "kreis" and "radius" in par and par["radius"] > 0:
            d[2] = par["radius"]
            return True
        if el.form == "rechteck" and len(d) >= 4:
            x1, x2 = sorted((d[0], d[2])); y1, y2 = sorted((d[1], d[3]))
            w = par.get("breite", x2 - x1); t = par.get("tiefe", y2 - y1)
            if w <= 0 or t <= 0:
                return False
            el.daten = [x1, y1, x1 + w, y1 + t]
            return True
        return False
    if not isinstance(el, Koerper3D):
        return False
    ok = False
    if el.art == "kugel" and el.kugel and par.get("radius", 0) > 0:
        el.kugel = (el.kugel[0], el.kugel[1], el.kugel[2], par["radius"])
        ok = True
    elif el.profil:
        art = _profil_art(el)
        xs = [p[0] for p in el.profil]; ys = [p[1] for p in el.profil]
        fx = fy = 1.0
        ax, ay = min(xs), min(ys)
        if art == "rechteck":
            w0, t0 = max(xs) - min(xs), max(ys) - min(ys)
            fx = par.get("breite", w0) / w0 if w0 > 1e-12 else 1.0
            fy = par.get("tiefe", t0) / t0 if t0 > 1e-12 else 1.0
        elif art == "kreis":
            ax = sum(xs) / len(xs); ay = sum(ys) / len(ys)
            r0 = max(math.hypot(p[0] - ax, p[1] - ay) for p in el.profil)
            fx = fy = par.get("radius", r0) / r0 if r0 > 1e-12 else 1.0
        else:
            ax = sum(xs) / len(xs); ay = sum(ys) / len(ys)
            fx = fy = par.get("faktor", 100.0) / 100.0
        if fx > 0 and fy > 0 and (abs(fx - 1) > 1e-12 or abs(fy - 1) > 1e-12):
            el.profil = [(ax + (x - ax) * fx, ay + (y - ay) * fy) for (x, y) in el.profil]
            if el.spitze:
                el.spitze = (ax + (el.spitze[0] - ax) * fx, ay + (el.spitze[1] - ay) * fy)
            ok = True
    if el.art in ("prisma", "pyramide") and par.get("hoehe", 0) > 0:
        el.hoehe = math.copysign(par["hoehe"], el.hoehe if el.hoehe else 1.0)
        ok = True
    return ok


# --------------------------------------------------------------------------
# 3D view inside a layout viewport
# --------------------------------------------------------------------------
def vp_ansicht_setzen(vp, elemente, yaw, pitch, persp=False):
    """Switches viewport `vp` to the 3D wireframe view and fits it to the model."""
    k = G.Kamera(yaw=yaw, pitch=pitch, perspektive=persp)
    pts = szene_punkte(elemente)
    if pts:
        k.anpassen(pts, vp.breite, vp.hoehe, rand=max(2.0, min(vp.breite, vp.hoehe) * 0.05))
        vp.zoom = k.skala
        vp.modell_zentrum_x, vp.modell_zentrum_y = k.ziel[0], k.ziel[1]
        zielz, abstand = k.ziel[2], k.abstand
    else:
        zielz, abstand = 0.0, 1500.0
    vp.ansicht3d = {"yaw": float(yaw), "pitch": float(pitch), "persp": bool(persp),
                    "zielz": float(zielz), "abstand": float(abstand)}


def vp_kamera(vp, skala):
    a = vp.ansicht3d or {}
    return G.Kamera(yaw=a.get("yaw", -45.0), pitch=a.get("pitch", 35.264),
                    ziel=(vp.modell_zentrum_x, vp.modell_zentrum_y, a.get("zielz", 0.0)),
                    abstand=a.get("abstand", 1500.0), skala=skala,
                    perspektive=bool(a.get("persp")))


def szene_segmente(elemente, kamera, cx, cy, sichtbar=None):
    """Projected wireframe of the scene: ([(element, ((x1, y1), (x2, y2))...)], [(element, (x, y), text)])."""
    linien, texte = [], []
    for el in elemente:
        if sichtbar is not None and not sichtbar(el):
            continue
        if ist_3d(el):
            for nz in el.netze():
                for (i, j) in nz.kanten:
                    seg = kamera.proj_segment(nz.punkte[i], nz.punkte[j], cx, cy)
                    if seg:
                        linien.append((el, seg))
            continue
        for zug, geschlossen in zuege3(el):
            pts = list(zug) + ([zug[0]] if geschlossen and len(zug) > 2 else [])
            for a, b in zip(pts, pts[1:]):
                seg = kamera.proj_segment(a, b, cx, cy)
                if seg:
                    linien.append((el, seg))
        if isinstance(el, Bemassung3D):
            q = kamera.proj(el.text_pos3(), cx, cy)
            if q:
                texte.append((el, (q[0], q[1]), el.wert_text()))
    return linien, texte


def clip_segment(seg, rect):
    """Liang-Barsky: segment clipped to rect (x1, y1, x2, y2) or None."""
    (x0, y0), (x1, y1) = seg
    xmin, ymin, xmax, ymax = rect
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - xmin), (dx, xmax - x0), (-dy, y0 - ymin), (dy, ymax - y0)):
        if abs(p) < 1e-12:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            if t > t1:
                return None
            t0 = max(t0, t)
        else:
            if t < t0:
                return None
            t1 = min(t1, t)
    return ((x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy))
