# -*- coding: utf-8 -*-
"""
katiecad/model/core.py - Data model, geometry and PDF output.
Contains NO Tkinter and no GUI logic.

NEW (block support, step 1):
  - BlockDefinition   template of a block (name + elements relative to the base point)
  - BlockReferenz     inserted block (position, scale, angle + deep copy)
  - BlockBibliothek   global block library shared across drawings (blocks.json)
  - BEFEHLE extended: BLOCK/B, INSERT/I, BLOCKLISTE/BL
NEW: radius and diameter dimensioning (DIMRADIUS/DIMDIAMETER).
NEW (electrical base): AttributDefinition + BlockReferenz.attribute
     (function texts such as name, device type, power ...).
"""

import math, sys, zlib
from copy import deepcopy

from katiecad.common.i18n import tr, SPRACHE
from katiecad.model.geom2d import ellipse_punkte, spline_punkte
from katiecad.model.geom3d import (prisma_netz_gerundet, profil_abrunden, v_rotieren, punkt_rotieren, prisma_netz, pyramide_netz, kugel_netz, kreis_profil,
                                   rechteck_profil, netz_abbilden, ebene_punkt, ebene_basis, BODEN_EBENE, v_cross)


# ============================================================
# Colour scheme
# ============================================================
FARBEN = {
    "bg_dunkel":    "#120a1f",
    "bg_mittel":    "#1c132d",
    "bg_hell":      "#281c3d",
    "bg_hover":     "#362452",
    "rand":         "#4a396b",
    "text":         "#d8d0e8",
    "text_dim":     "#8b7ea8",
    "text_hell":    "#ffffff",
    "cyan":         "#c29bff",
    "cyan_dunkel":  "#805ad5",
    "magenta":      "#ff2d95",
    "gruen":        "#39ff14",
    "gelb":         "#ffe600",
    "rot":          "#ff1744",
    "orange":       "#ff9500",
    "select_bg":    "#321f5c",
    "select_fg":    "#e2d4ff",
}


# ============================================================
# Constants
# ============================================================
EINHEITEN = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}

ZEICHNUNGSFORMATE = {
    "A4 (297x210)":  (297, 210),
    "A3 (420x297)":  (420, 297),
    "A2 (594x420)":  (594, 420),
    "A1 (841x594)":  (841, 594),
    "A0 (1189x841)": (1189, 841),
}

MASSSTAEBE = ["1:1", "1:2", "1:5", "1:10", "1:20", "1:50",
              "1:100", "1:200", "2:1", "5:1", "10:1"]

LINIENTYPEN = {
    "Volllinie (breit)":        {"dash": None,           "farbe": "#ffffff"},
    "Volllinie (schmal)":       {"dash": None,           "farbe": "#ffffff"},
    "Strichlinie (verdeckt)":   {"dash": (6, 4),         "farbe": "#b886fb"},
    "Strichpunktlinie (Achse)": {"dash": (12, 4, 3, 4),  "farbe": "#ff2d95"},
    "Freihandlinie":            {"dash": (2, 3),         "farbe": "#8b7ea8"},
    "Schraffur":                {"dash": (2, 2),         "farbe": "#8b7ea8"},
}

RASTER_GROESSEN = [1, 2, 5, 10, 20, 25, 50, 100]

BG_PRESETS = {
    "Standard":     "#120a1f",
    "Weiß (Papier)":        "#ffffff",
    "Schwarz (CAD-Dunkel)": "#1e1e1e",
    "Dunkelgrau":           "#333333",
    "Hellgrau":             "#e8e8e8",
    "Blau (klassisch)":     "#003366",
    "Beige (Sepia)":        "#f4ecd8",
}

SCHRIFTARTEN = ["Arial", "Courier New", "Times New Roman",
                "Consolas", "Verdana", "Tahoma", "Segoe UI"]

LINIENSTAERKEN = [0.13, 0.18, 0.25, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0]

GRIFF_RADIUS = 5
GRIFF_GROESSE_MM = 3.0
MIN_VP_GROESSE = 10.0
PASTE_OFFSET_MM = 10.0

TEXT_BREITE = 0.72
# UI font per platform (Segoe UI exists only on Windows)
UI_SCHRIFT = ("Segoe UI" if sys.platform.startswith("win")
              else "Helvetica Neue" if sys.platform == "darwin"
              else "DejaVu Sans")
TEXT_ZEILE = 1.65
CAD_VERSALHOEHE = 0.72
LW_PX_FAKTOR = 6.5
BEM_RICHTUNGEN = ("horizontal", "vertikal", "ausgerichtet",
                  "radius", "durchmesser", "winkel")

# Tolerance for "point lies on object" (in model mm)
TRIM_TOL = 1e-6


def ist_dunkel(hexfarbe):
    try:
        hexc = hexfarbe.lstrip("#")
        r = int(hexc[0:2], 16)
        g = int(hexc[2:4], 16)
        b = int(hexc[4:6], 16)
        return (r * 0.299 + g * 0.587 + b * 0.114) < 128
    except Exception:
        return False


# ============================================================
# Geometry helpers
# ============================================================
def norm360(a):
    return a % 360.0


def bogen_sweep(start, ende):
    s = (ende - start) % 360.0
    return 360.0 if s < 1e-9 else s


def bogen_punkte(cx, cy, r, start, ende, n):
    sweep = bogen_sweep(start, ende)
    n = max(2, int(n))
    pts = []
    for i in range(n + 1):
        a = math.radians(start + sweep * i / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def winkel_im_bogen(winkel, start, ende, eps=1e-6):
    return (winkel - start) % 360.0 <= bogen_sweep(start, ende) + eps


def kreis_aus_3_punkten(p1, p2, p3):
    ax, ay = p1
    bx, by = p2
    cx, cy = p3
    kreuz = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    skala = max(math.hypot(bx - ax, by - ay) * math.hypot(cx - ax, cy - ay), 1e-12)
    if abs(kreuz) / skala < 1e-9:
        return None
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    a2, b2, c2 = ax * ax + ay * ay, bx * bx + by * by, cx * cx + cy * cy
    ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d
    uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d
    return ux, uy, math.hypot(ax - ux, ay - uy)


def bogen_aus_3_punkten(p1, p2, p3):
    k = kreis_aus_3_punkten(p1, p2, p3)
    if k is None:
        return None
    cx, cy, r = k
    kreuz = (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
    a1 = norm360(math.degrees(math.atan2(p1[1] - cy, p1[0] - cx)))
    a3 = norm360(math.degrees(math.atan2(p3[1] - cy, p3[0] - cx)))
    if kreuz > 0:
        return cx, cy, r, a1, a3
    return cx, cy, r, a3, a1


def bogen_mitte_start_ende(c, s, e, richtung="auto"):
    r = math.hypot(s[0] - c[0], s[1] - c[1])
    if r < 1e-9:
        return None
    a_s = norm360(math.degrees(math.atan2(s[1] - c[1], s[0] - c[0])))
    a_e = norm360(math.degrees(math.atan2(e[1] - c[1], e[0] - c[0])))
    if richtung == "ccw":
        start, ende = a_s, a_e
    elif richtung == "cw":
        start, ende = a_e, a_s
    elif (a_e - a_s) % 360.0 <= 180.0:
        start, ende = a_s, a_e
    else:
        start, ende = a_e, a_s
    sw = bogen_sweep(start, ende)
    if sw < 0.01 or sw > 359.99:
        return None
    return r, start, ende


def abstand_punkt_segment(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 < 1e-18:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def naechster_punkt_segment(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 < 1e-18:
        return x1, y1
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return x1 + t * dx, y1 + t * dy


def clip_segment(x1, y1, x2, y2, xmin, ymin, xmax, ymax):
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - xmin), (dx, xmax - x1),
                 (-dy, y1 - ymin), (dy, ymax - y1)):
        if abs(p) < 1e-12:
            if q < 0:
                return None
        else:
            t = q / p
            if p < 0:
                if t > t1:
                    return None
                if t > t0:
                    t0 = t
            else:
                if t < t0:
                    return None
                if t < t1:
                    t1 = t
    return (x1 + t0 * dx, y1 + t0 * dy, x1 + t1 * dx, y1 + t1 * dy)


def clip_polyline(pts, rect):
    xmin, ymin, xmax, ymax = rect
    if all(xmin <= x <= xmax and ymin <= y <= ymax for (x, y) in pts):
        return [list(pts)] if len(pts) >= 2 else []
    out, cur = [], []
    for i in range(len(pts) - 1):
        seg = clip_segment(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                           xmin, ymin, xmax, ymax)
        if seg is None:
            if len(cur) >= 2:
                out.append(cur)
            cur = []
            continue
        a, b = (seg[0], seg[1]), (seg[2], seg[3])
        if cur and abs(cur[-1][0] - a[0]) < 1e-6 and abs(cur[-1][1] - a[1]) < 1e-6:
            cur.append(b)
        else:
            if len(cur) >= 2:
                out.append(cur)
            cur = [a, b]
    if len(cur) >= 2:
        out.append(cur)
    return out


def gedrehtes_rechteck(cx, cy, w, h, winkel_deg):
    a = math.radians(winkel_deg)
    ex = (math.cos(a), math.sin(a))
    ey = (-math.sin(a), math.cos(a))
    pts = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        pts.append((cx + sx * w / 2 * ex[0] + sy * h / 2 * ey[0],
                    cy + sx * w / 2 * ex[1] + sy * h / 2 * ey[1]))
    return pts


def punkt_in_gedrehtem_rechteck(px, py, cx, cy, w, h, winkel_deg, tol=0.0):
    a = math.radians(-winkel_deg)
    dx, dy = px - cx, py - cy
    lx = dx * math.cos(a) - dy * math.sin(a)
    ly = dx * math.sin(a) + dy * math.cos(a)
    return abs(lx) <= w / 2 + tol and abs(ly) <= h / 2 + tol


def punkte_drehen(px, py, cx, cy, winkel_deg):
    """Rotates (px, py) about (cx, cy) by winkel_deg.

    CAUTION, convention: the model has Y pointing up; this formula rotates
    CLOCKWISE there for a POSITIVE winkel_deg. The rotate tools therefore
    pass -winkel (CCW wish). All drehen() methods that additionally keep an
    angle field (text, arc, hatching, block, cross reference) must therefore
    update that field with  `- winkel_deg`; the angle fields themselves are
    mathematical everywhere (counter-clockwise positive)."""
    a = math.radians(winkel_deg)
    ca, sa = math.cos(a), math.sin(a)
    dx, dy = px - cx, py - cy
    return (cx + dx * ca + dy * sa,
            cy - dx * sa + dy * ca)


def bem_zahl(wert, dez, komma=True):
    s = f"{wert:.{max(0, int(dez))}f}"
    return s.replace(".", ",") if komma else s


def parse_massstab(text):
    a, b = text.replace(",", ".").split(":")
    a, b = float(a), float(b)
    if a <= 0 or b <= 0:
        raise ValueError("Massstab muss positiv sein")
    return a / b


def ort_text(o):
    """Display of a reference target. o = sheet number or (sheet, "column/row").
    Example: (1, "3/B") -> "1/3/B"; (2, "") -> "2"."""
    if isinstance(o, (tuple, list)):
        blatt, feld = o[0], (o[1] if len(o) > 1 else "")
        return f"{blatt}/{feld}" if feld else str(blatt)
    return str(o)


def massstab_text(zoom):
    if zoom <= 0:
        return "?"
    if zoom >= 1.0:
        return f"{zoom:g}:1" if abs(zoom - round(zoom)) > 1e-6 else f"{int(round(zoom))}:1"
    n = 1.0 / zoom
    return f"1:{int(round(n))}" if abs(n - round(n)) < 1e-6 else f"1:{n:.2f}"


def normmassstab_unter(zoom, liste):
    werte = sorted({parse_massstab(t) for t in liste})
    kand = [w for w in werte if w <= zoom * (1 + 1e-9)]
    return kand[-1] if kand else zoom


def lot_fuss(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return (x1, y1)
    t = ((px - x1) * dx + (py - y1) * dy) / L2
    return (x1 + t * dx, y1 + t * dy)


def linien_schnitt(x1, y1, x2, y2, x3, y3, x4, y4):
    d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if abs(d) < 1e-9:
        return None
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
    u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def bbox_enthalten(aussen, innen):
    ax1, ay1, ax2, ay2 = aussen
    bx1, by1, bx2, by2 = innen
    return ax1 <= bx1 and ay1 <= by1 and ax2 >= bx2 and ay2 >= by2


def bbox_ueberlappt(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1)


# ============================================================
# NEW: trim (TRIM) and break (BREAK) - geometry helpers
# ============================================================
def _punkt_auf_segment_param(px, py, x1, y1, x2, y2, tol=TRIM_TOL):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 < 1e-18:
        d = math.hypot(px - x1, py - y1)
        if d <= tol:
            return 0.0, d
        return None
    t = ((px - x1) * dx + (py - y1) * dy) / L2
    if t < -tol or t > 1.0 + tol:
        return None
    nx, ny = x1 + t * dx, y1 + t * dy
    d = math.hypot(px - nx, py - ny)
    if d > tol:
        return None
    return t, d


def trim_linie(x1, y1, x2, y2, treffer_punkte, klick_punkt):
    if not treffer_punkte:
        return [(x1, y1, x2, y2)]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    if L < TRIM_TOL:
        return [(x1, y1, x2, y2)]
    ux, uy = dx / L, dy / L
    werte = []
    for (px, py) in treffer_punkte:
        t = ((px - x1) * ux + (py - y1) * uy)
        if -TRIM_TOL <= t <= L + TRIM_TOL:
            werte.append(max(0.0, min(L, t)))
    if not werte:
        return [(x1, y1, x2, y2)]
    tk = (klick_punkt[0] - x1) * ux + (klick_punkt[1] - y1) * uy
    tk = max(0.0, min(L, tk))
    werte = sorted(set(werte))
    links = max([w for w in werte if w <= tk] or [0.0])
    rechts = min([w for w in werte if w >= tk] or [L])
    stuecke = []
    if links > TRIM_TOL:
        ex = x1 + ux * links
        ey = y1 + uy * links
        stuecke.append((x1, y1, ex, ey))
    if L - rechts > TRIM_TOL:
        sx = x1 + ux * rechts
        sy = y1 + uy * rechts
        stuecke.append((sx, sy, x2, y2))
    return stuecke


def trim_polylinie(punkte, geschlossen, treffer_punkte, klick_punkt):
    if len(punkte) < 2:
        return [(punkte, geschlossen)]
    segs = []
    n = len(punkte)
    for i in range(n - 1):
        segs.append((punkte[i], punkte[i + 1], i, False))
    if geschlossen and n >= 3:
        segs.append((punkte[-1], punkte[0], n - 1, True))
    schnitte = [[] for _ in segs]
    for (px, py) in treffer_punkte:
        for idx, (a, b, _i, _cl) in enumerate(segs):
            erg = _punkt_auf_segment_param(px, py, a[0], a[1], b[0], b[1])
            if erg is not None:
                schnitte[idx].append(erg[0])
    klick_seg = None
    klick_t = None
    klick_dist = None
    for idx, (a, b, _i, _cl) in enumerate(segs):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < TRIM_TOL:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        t = ((klick_punkt[0] - a[0]) * ux + (klick_punkt[1] - a[1]) * uy)
        if -TRIM_TOL <= t <= L + TRIM_TOL:
            tt = max(0.0, min(1.0, t / L))
            nx, ny = a[0] + (b[0] - a[0]) * tt, a[1] + (b[1] - a[1]) * tt
            d = math.hypot(klick_punkt[0] - nx, klick_punkt[1] - ny)
            if klick_dist is None or d < klick_dist:
                klick_seg = idx
                klick_t = tt
                klick_dist = d
    if klick_seg is None:
        return [(punkte, geschlossen)]
    ss = sorted(set(schnitte[klick_seg]))
    links = max([w for w in ss if w <= klick_t] or [0.0])
    rechts = min([w for w in ss if w >= klick_t] or [1.0])
    if not geschlossen:
        seg_a, seg_b, _i, _cl = segs[klick_seg]
        links_p = (seg_a[0] + (seg_b[0] - seg_a[0]) * links,
                   seg_a[1] + (seg_b[1] - seg_a[1]) * links)
        rechts_p = (seg_a[0] + (seg_b[0] - seg_a[0]) * rechts,
                    seg_a[1] + (seg_b[1] - seg_a[1]) * rechts)
        teile = []
        stueck1 = list(punkte[:klick_seg + 1])
        if links > TRIM_TOL:
            stueck1.append(links_p)
        if len(stueck1) >= 2:
            teile.append((stueck1, False))
        if rechts < 1.0 - TRIM_TOL:
            stueck2 = [rechts_p] + list(punkte[klick_seg + 1:])
            if len(stueck2) >= 2:
                teile.append((stueck2, False))
        return teile
    else:
        seg_a, seg_b, seg_i, _cl = segs[klick_seg]
        links_p = (seg_a[0] + (seg_b[0] - seg_a[0]) * links,
                   seg_a[1] + (seg_b[1] - seg_a[1]) * links)
        rechts_p = (seg_a[0] + (seg_b[0] - seg_a[0]) * rechts,
                    seg_a[1] + (seg_b[1] - seg_a[1]) * rechts)
        kette = [rechts_p]
        idx = (seg_i + 1) % n
        for _ in range(n + 1):
            kette.append(punkte[idx])
            if idx == klick_seg % n and len(kette) > 1:
                break
            idx = (idx + 1) % n
        if len(kette) >= 2:
            kette.append(links_p)
        sauber = []
        for p in kette:
            if not sauber or (abs(p[0] - sauber[-1][0]) > TRIM_TOL or
                              abs(p[1] - sauber[-1][1]) > TRIM_TOL):
                sauber.append(p)
        if len(sauber) >= 2:
            return [(sauber, False)]
        return []


def trim_bogen(cx, cy, r, start, ende, treffer_punkte, klick_punkt):
    if not treffer_punkte:
        return [(start, ende)]
    winkel = []
    for (px, py) in treffer_punkte:
        d = math.hypot(px - cx, py - cy)
        if abs(d - r) <= TRIM_TOL * 10:
            w = norm360(math.degrees(math.atan2(py - cy, px - cx)))
            if winkel_im_bogen(w, start, ende, 1e-3):
                winkel.append(w)
    if not winkel:
        return [(start, ende)]
    winkel = sorted(set(round(w, 6) for w in winkel))
    sweep_start = norm360(start)
    sweep_end = sweep_start + bogen_sweep(start, ende)
    kd = math.hypot(klick_punkt[0] - cx, klick_punkt[1] - cy)
    kw = norm360(math.degrees(math.atan2(klick_punkt[1] - cy,
                                        klick_punkt[0] - cx)))
    rel = []
    for w in winkel:
        rel_w = norm360(w - sweep_start)
        if rel_w <= sweep_end - sweep_start + 1e-6:
            rel.append((rel_w, w))
    rel.sort()
    rel_k = norm360(kw - sweep_start)
    links_w = 0.0
    rechts_w = sweep_end - sweep_start
    for (rw, _w) in rel:
        if rw <= rel_k + 1e-6:
            links_w = max(links_w, rw)
        if rw >= rel_k - 1e-6:
            rechts_w = min(rechts_w, rw)
    stuecke = []
    if links_w > 1e-6:
        stuecke.append((norm360(sweep_start), norm360(sweep_start + links_w)))
    if (sweep_end - sweep_start) - rechts_w > 1e-6:
        stuecke.append((norm360(sweep_start + rechts_w), norm360(sweep_end)))
    return stuecke


def kreis_zu_bogen(cx, cy, r, p1, p2):
    a1 = norm360(math.degrees(math.atan2(p1[1] - cy, p1[0] - cx)))
    a2 = norm360(math.degrees(math.atan2(p2[1] - cy, p2[0] - cx)))
    if abs(a1 - a2) < 1e-6:
        return None
    return (cx, cy, r, a2, a1)


def teile_bogen_durch_winkel(start, ende, winkel_liste):
    sw = bogen_sweep(start, ende)
    if not winkel_liste:
        return [(start, ende)]
    rel = []
    for w in winkel_liste:
        rw = (w - start) % 360.0
        if rw <= sw + 1e-6 and rw >= -1e-6:
            rel.append(round(rw, 6))
    rel = sorted(set(rel))
    if not rel:
        return [(start, ende)]
    rel = [0.0] + [w for w in rel if 1e-6 < w < sw - 1e-6] + [sw]
    stuecke = []
    for i in range(len(rel) - 1):
        a = rel[i]
        b = rel[i + 1]
        if b - a > 1e-6:
            stuecke.append((norm360(start + a), norm360(start + b)))
    return stuecke


# ============================================================
# Command line (both languages always available)
# ============================================================
BEFEHLE = {
    "RASTER": "raster", "GRID": "raster",
    "FANG": "fang", "SNAP": "fang", "RASTERFANG": "fang",
    "OFANG": "ofang", "OSNAP": "ofang", "OBJEKTFANG": "ofang",
    "ORTHO": "ortho",
    "VERSCHIEBEN": "move", "V": "move", "MOVE": "move", "M": "move",
    "KOPIEREN": "copy", "KO": "copy", "COPY": "copy", "CO": "copy", "CP": "copy",
    "COPYBASE": "copybase", "KOPIERENBASIS": "copybase",
    "KOPIERENMITBASISPUNKT": "copybase", "KOPIERENMITBASIS": "copybase",
    "REIHE": "array", "ARRAY": "array", "AR": "array", "ANORDNUNG": "array",
    "DREHEN": "rotate", "DREHE": "rotate", "ROTATE": "rotate", "RO": "rotate",
    "SKALIEREN": "scale", "SKALIERE": "scale", "SCALE": "scale", "SC": "scale",
    "SPIEGELN": "mirror", "SPIEGELE": "mirror", "MIRROR": "mirror", "MI": "mirror",
    "STRECKEN": "stretch", "STRETCH": "stretch", "STR": "stretch", "ST": "stretch",
    "EINFÜGEN": "paste", "EINFUEGEN": "paste", "PASTE": "paste",
    "DRUCKEN": "druck", "PLOT": "druck", "PRINT": "druck",
    "U": "undo", "UNDO": "undo", "RÜCKGÄNGIG": "undo", "RUECKGAENGIG": "undo",
    "REDO": "redo", "WIEDERHOLEN": "redo", "WIEDERHERSTELLEN": "redo",
    "VP": "tool:vpunkt", "VERBINDUNGSPUNKT": "tool:vpunkt",
    "LEITUNG": "tool:leitung",
    "QV": "tool:querverweis", "QUERVERWEIS": "tool:querverweis",
    "PIN": "tool:vpunkt", "VERBINDUNG": "tool:verbindung",
    "MASKE": "tool:maske", "ELEKTROMASKE": "tool:maske",
    "KLEMME": "tool:klemme",
    "FTEXT": "tool:ftext", "FUNKTIONSTEXT": "tool:ftext",
    "SUCHEN": "suchen", "FIND": "suchen", "ERSETZEN": "suchen", "SU": "suchen",
    "EU": "matchprop", "MA": "matchprop", "MATCHPROP": "matchprop",
    "EIGENSCHAFTENUEBERTRAGEN": "matchprop", "EIGENSCHAFTENÜBERTRAGEN": "matchprop",
    "MESS": "messen", "MESSEN": "messen", "DI": "messen", "DIST": "messen",
    "DISTANZ": "messen", "MEASURE": "messen",
    "NUMMERIEREN": "nummerieren", "AUTONUM": "nummerieren", "GERAETENUMMERN": "nummerieren",
    "QSELECT": "schnellauswahl", "SCHNELLAUSWAHL": "schnellauswahl", "QS": "schnellauswahl",
    "VERSATZ": "versatz", "OFFSET": "versatz", "O": "versatz",
    "LAENGE": "laenge", "LÄNGE": "laenge", "LENGTHEN": "laenge", "LEN": "laenge",
    "MANIP": "manip", "MANIPULATOR": "manip", "MP": "manip",
    "3D": "3d:oeffnen", "3DANSICHT": "3d:oeffnen", "3DVIEW": "3d:oeffnen",
    "QUADER": "3d:neu:quader", "BOX": "3d:neu:quader",
    "SCHRANK": "3d:neu:schrank", "CABINET": "3d:neu:schrank",
    "PYRAMIDE": "3d:neu:pyramide", "PYRAMID": "3d:neu:pyramide",
    "ZYLINDER": "3d:neu:zylinder", "CYLINDER": "3d:neu:zylinder",
    "KEGEL": "3d:neu:kegel", "CONE": "3d:neu:kegel",
    "KUGEL": "3d:neu:kugel", "SPHERE": "3d:neu:kugel",
    "EXTRUDIEREN": "3d:extrudieren", "EXT": "3d:extrudieren", "EXTRUDE": "3d:extrudieren",
    "LOCH": "3d:loch", "BOHRUNG": "3d:loch", "HOLE": "3d:loch",
    "3DMASS": "3d:mass", "MASSE": "3d:mass",
    "3DDREHEN": "3d:drehen", "3DROTATE": "3d:drehen", "DREHEN3D": "3d:drehen",
    "3DABRUNDEN": "3d:abrunden", "3DFILLET": "3d:abrunden",
    "3DPIVOT": "3d:pivot", "MANIPVERSETZEN": "3d:pivot",
    "3DBLOCK": "3d:block", "3DAUFLOESEN": "3d:aufloesen",
    "AUSRICHTEN": "ausrichten:links", "ALIGN": "ausrichten:links",
    "AUSLINKS": "ausrichten:links", "AUSRECHTS": "ausrichten:rechts",
    "AUSOBEN": "ausrichten:oben", "AUSUNTEN": "ausrichten:unten",
    "AUSMITTEH": "ausrichten:mitte_h", "AUSMITTEV": "ausrichten:mitte_v",
    "ABRUNDEN": "abrunden", "FILLET": "abrunden", "F": "abrunden",
    "FASE": "fase", "CHAMFER": "fase", "CHA": "fase",
    "ATTDEF": "attdef", "ATTRIBUT": "attdef", "ATTRIBUTDEFINITION": "attdef",
    "ATTEDIT": "attedit", "ATTRIBUTEBEARBEITEN": "attedit",
    "BLOCKSPEICHERN": "block:speichern", "WBLOCK": "block:speichern",
    "BLOCKLADEN": "block:laden",
    "BLATT": "blatt:neu", "BLATTNEU": "blatt:neu",
    "LÖSCHEN": "delete", "LOESCHEN": "delete", "DEL": "delete", "ERASE": "delete",
    "ZG": "zg", "ZOOMGRENZEN": "zg",
    "LINIE": "tool:linie", "LINE": "tool:linie", "L": "tool:linie",
    "POLYLINIE": "tool:polylinie", "PL": "tool:polylinie", "PLINE": "tool:polylinie",
    "KREIS": "tool:kreis", "CIRCLE": "tool:kreis", "K": "tool:kreis",
    "BOGEN": "tool:bogen", "ARC": "tool:bogen", "A": "tool:bogen",
    "ELLIPSE": "tool:ellipse", "EL": "tool:ellipse",
    "SPLINE": "tool:spline", "SPL": "tool:spline",
    "RECHTECK": "tool:rechteck", "REC": "tool:rechteck", "RECTANG": "tool:rechteck",
    "TEXT": "tool:text", "T": "tool:text",
    "BEMASSUNG": "tool:bemassung", "BEM": "tool:bemassung", "DIM": "tool:bemassung",
    # NEW: special dimensioning radius / diameter
    "DIMRADIUS":   "bem:radius", "DR": "bem:radius",
    "RADIUS":      "bem:radius", "RBEM": "bem:radius",
    "DIMDIAMETER": "bem:durchmesser", "DD": "bem:durchmesser",
    "KETTE": "bem:kette", "KETTENBEM": "bem:kette", "DIMCONTINUE": "bem:kette",
    "WINKEL": "bem:winkel", "WINKELBEM": "bem:winkel", "ANGULAR": "bem:winkel",
    "WINKELLINIEN": "bem:winkel_linien",
    "DURCHMESSER": "bem:durchmesser", "DIA": "bem:durchmesser",
    "STUTZEN": "tool:stutzen", "TRIM": "tool:stutzen", "TR": "tool:stutzen",
    "BRECHEN": "tool:brechen", "BREAK": "tool:brechen", "BR": "tool:brechen",
    # --- NEW: block commands ---
    "BLOCK": "block:neu", "B": "block:neu", "BLOCKNEU": "block:neu",
    "INSERT": "block:einfuegen", "EINFUEGENBLOCK": "block:einfuegen",
    "I": "block:einfuegen", "BLOCKEINFUEGEN": "block:einfuegen",
    "BLOCKLISTE": "block:liste", "BL": "block:liste",
    "BLOCKVERWALTEN": "block:liste",
    # --- NEW: explode block (EXPLODE) ---
    "EXPLODE": "block:explode", "X": "block:explode",
    "AUFLOESEN": "block:explode", "BLOCKAUFLOESEN": "block:explode",
}


# ============================================================
# Minimal PDF writer
# ============================================================
_HELV = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
         556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
         1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
         667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
         333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
         556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]


_HELV_FETT = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
              556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
              975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
              667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
              333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
              611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584]

FETT_MARKE = "|b"          # bold text: font name + marker ("Arial|b")


def schrift_fett(s):
    """True if the font string carries the bold marker."""
    return str(s).endswith(FETT_MARKE)


def schrift_name(s):
    """Font name without the bold marker."""
    s = str(s)
    return s[:-len(FETT_MARKE)] if s.endswith(FETT_MARKE) else s


def schrift_setzen(name, fett):
    return schrift_name(name) + (FETT_MARKE if fett else "")


def pdf_textbreite(s, schriftgroesse, fett=False):
    tab = _HELV_FETT if fett else _HELV
    w = 0
    for ch in s:
        o = ord(ch)
        if 32 <= o <= 126:
            w += tab[o - 32]
        elif ch == "\u00d8":
            w += 778
        else:
            w += 556
    return w * schriftgroesse / 1000.0


def _pdf_str(s):
    b = s.encode("cp1252", "replace").decode("latin-1")
    return b.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_rgb(hexfarbe):
    try:
        h = hexfarbe.lstrip("#")
        return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except Exception:
        return (0.0, 0.0, 0.0)


class PdfSeite:
    MM = 72.0 / 25.4

    def __init__(self, breite_mm, hoehe_mm):
        self.b, self.h = float(breite_mm), float(hoehe_mm)
        self.ops = []
        self.ebene = None        # current layer name (-> PDF optional content)
        self.ebenen = []         # layer names in order of first use

    def _op(self, op):
        if self.ebene:
            if self.ebene not in self.ebenen:
                self.ebenen.append(self.ebene)
            op = "/OC /OC%d BDC %s EMC" % (self.ebenen.index(self.ebene) + 1, op)
        self.ops.append(op)

    def clip_start(self, x1, y1, x2, y2):
        self.ops.append("q %.4f %.4f %.4f %.4f re W n" % (x1, y1, x2 - x1, y2 - y1))

    def clip_ende(self):
        self.ops.append("Q")

    def linie(self, pts, breite, farbe="#000000", dash=None, geschlossen=False):
        if len(pts) < 2:
            return
        r, g, b = _pdf_rgb(farbe)
        o = ["q", "%.4f w" % max(breite, 0.02), "1 J 1 j",
             "%.4f %.4f %.4f RG" % (r, g, b)]
        o.append(("[%s] 0 d" % " ".join("%.3f" % d for d in dash)) if dash else "[] 0 d")
        o.append("%.4f %.4f m" % pts[0])
        for p in pts[1:]:
            o.append("%.4f %.4f l" % p)
        o.append("s" if geschlossen else "S")
        o.append("Q")
        self._op(" ".join(o))

    def flaeche(self, pts, farbe="#000000"):
        if len(pts) < 3:
            return
        r, g, b = _pdf_rgb(farbe)
        o = ["q", "%.4f %.4f %.4f rg" % (r, g, b), "%.4f %.4f m" % pts[0]]
        for p in pts[1:]:
            o.append("%.4f %.4f l" % p)
        o.append("f")
        o.append("Q")
        self._op(" ".join(o))

    def text(self, x, y, inhalt, hoehe, winkel=0.0, farbe="#000000", mitte=False,
             fett=False):
        fs = hoehe / CAD_VERSALHOEHE
        a = math.radians(winkel)
        ex, ey = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        zeilen = inhalt.split("\n") or [""]
        n = len(zeilen)
        r, g, b = _pdf_rgb(farbe)
        for i, z in enumerate(zeilen):
            up = (n - 1 - i) * TEXT_ZEILE * hoehe
            ox, oy = x + ey[0] * up, y + ey[1] * up
            if mitte:
                w = pdf_textbreite(z, fs, fett)
                ox -= ex[0] * w / 2 + ey[0] * hoehe / 2
                oy -= ex[1] * w / 2 + ey[1] * hoehe / 2
            self._op(
                "BT /%s %.4f Tf %.4f %.4f %.4f rg %.6f %.6f %.6f %.6f %.4f %.4f Tm (%s) Tj ET"
                % ("F2" if fett else "F1", fs, r, g, b, ex[0], ex[1], -ex[1], ex[0], ox, oy, _pdf_str(z)))

    def bild(self, x, y, breite, hoehe, daten, format, pw, ph):
        """Places an image (lower left corner x/y in mm)."""
        if not hasattr(self, "bilder"):
            self.bilder = []
        name = "Im%d" % (len(self.bilder) + 1)
        self.bilder.append((name, daten, format, pw, ph))
        self._op("q %.4f 0 0 %.4f %.4f %.4f cm /%s Do Q"
                        % (breite, hoehe, x, y, name))

    def to_bytes(self):
        return pdf_mehrseitig([self])


def _pdf_bild_objekte(daten, format, pw, ph):
    """-> list of PDF object bodies (bytes) for one image: [image, (smask)].
    Object numbers inside are written as %(smask)d and filled in by the caller."""
    import base64
    roh = base64.b64decode(daten)
    if format == "jpeg":
        return [(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
                 b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                 b"/Length %d >>\nstream\n" % (pw, ph, len(roh))) + roh + b"\nendstream"]
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(roh)).convert("RGBA")
    rgb = zlib.compress(im.convert("RGB").tobytes())
    alpha = zlib.compress(im.getchannel("A").tobytes())
    return [(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
             b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode "
             b"/SMask %%(smask)d 0 R /Length %d >>\nstream\n" % (pw, ph, len(rgb)))
            + rgb + b"\nendstream",
            (b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
             b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "
             b"/Length %d >>\nstream\n" % (pw, ph, len(alpha))) + alpha + b"\nendstream"]


def pdf_mehrseitig(seiten):
    """Writes a PDF file with one page per PdfSeite object."""
    if not seiten:
        raise ValueError("Keine Seiten")
    n = len(seiten)
    objs = {}
    kids = " ".join("%d 0 R" % (4 + 2 * i) for i in range(n))
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, n)).encode("latin-1")
    objs[3] = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
               b"/Encoding /WinAnsiEncoding >>")
    objs[4 + 2 * n] = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
                       b"/Encoding /WinAnsiEncoding >>")
    fett_nr = 4 + 2 * n
    naechste = 5 + 2 * n                    # first free object number (images)
    ocg = {}                                # layer name -> object number
    for sp in seiten:
        for nm in sp.ebenen:
            if nm not in ocg:
                ocg[nm] = naechste
                naechste += 1
    for i, sp in enumerate(seiten):
        pid, cid = 4 + 2 * i, 5 + 2 * i
        inhalt = ("%.9f 0 0 %.9f 0 0 cm\n" % (sp.MM, sp.MM)
                  + "\n".join(sp.ops)).encode("latin-1")
        strom = zlib.compress(inhalt)
        w, h = sp.b * sp.MM, sp.h * sp.MM
        xobj = ""
        for name, daten, fmt, pw, ph in getattr(sp, "bilder", []):
            teile = _pdf_bild_objekte(daten, fmt, pw, ph)
            nr = naechste
            naechste += len(teile)
            if len(teile) == 2:
                teile[0] = teile[0].replace(b"%(smask)d", b"%d" % (nr + 1))
            for k, t in enumerate(teile):
                objs[nr + k] = t
            xobj += "/%s %d 0 R " % (name, nr)
        res = "/Font << /F1 3 0 R /F2 %d 0 R >>" % fett_nr + (" /XObject << %s>>" % xobj if xobj else "")
        if sp.ebenen:
            res += " /Properties << %s>>" % "".join(
                "/OC%d %d 0 R " % (k + 1, ocg[nm]) for k, nm in enumerate(sp.ebenen))
        objs[pid] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.3f %.3f] "
                     "/Contents %d 0 R /Resources << %s >> >>"
                     % (w, h, cid, res)).encode("latin-1")
        objs[cid] = (b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(strom)
                     + strom + b"\nendstream")
    if ocg:
        refs = " ".join("%d 0 R" % nr for nr in ocg.values())
        objs[1] = ("<< /Type /Catalog /Pages 2 0 R /OCProperties << /OCGs [%s] "
                   "/D << /Order [%s] /ON [%s] >> >> >>" % (refs, refs, refs)
                   ).encode("latin-1")
        for nm, nr in ocg.items():
            hexname = ("\ufeff" + nm).encode("utf-16-be").hex().upper()
            objs[nr] = ("<< /Type /OCG /Name <%s> >>" % hexname).encode("latin-1")
    out = bytearray((b"%PDF-1.5" if ocg else b"%PDF-1.4") + b"\n%\xe2\xe3\xcf\xd3\n")
    offs = []
    total = naechste - 1
    for i in range(1, total + 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + objs[i] + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (total + 1)
    for o in offs:
        out += b"%010d 00000 n \n" % o
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (total + 1, xref))
    return bytes(out)


# ============================================================
# Layers
# ============================================================
# Layers that are created and used automatically for electrical objects
E_DEVICES, E_LINES, E_CABLE, E_CLAMPS, E_PIN = (
    "E_DEVICES", "E_LINES", "E_CABLE", "E_CLAMPS", "E_PIN")
FTEXT_LAYER = "F-Text"       # function texts (see electrical/funktion.py)
ELEKTRO_LAYER = {            # name -> (colour, line weight)
    E_DEVICES: ("#c29bff", 0.35),
    E_LINES: ("#ff2d2d", 0.35),
    E_CABLE: ("#c29bff", 0.35),
    E_CLAMPS: ("#c29bff", 0.35),
    E_PIN: ("#c29bff", 0.35),
    FTEXT_LAYER: ("#ff9f43", 0.35),
}


class Layer:
    def __init__(self, name, farbe="#c29bff", staerke=0.35, sichtbar=True):
        self.name = name
        self.farbe = farbe
        self.staerke = staerke
        self.sichtbar = sichtbar

    def to_dict(self):
        return {"name": self.name, "farbe": self.farbe,
                "staerke": self.staerke, "sichtbar": self.sichtbar}


# ============================================================
# Elements
# ============================================================
class Element:
    def __init__(self, typ, layer="0", farbe="#c29bff",
                 linientyp="Volllinie (schmal)", eig_farbe=False,
                 staerke=None):
        self.typ = typ
        self.layer = layer
        self.farbe = farbe
        self.linientyp = linientyp
        self.eig_farbe = eig_farbe
        self.staerke = staerke
        self.id = None

    def to_dict(self):
        d = self.__dict__.copy()
        d.pop("id", None)
        return d

    def bbox(self):
        return (0, 0, 0, 0)

    def verschieben(self, dx, dy):
        pass

    def griffe(self):
        return []

    def griff_bewegen(self, griff_id, x, y):
        pass

    def drehen(self, cx, cy, winkel_deg):
        pass


class Linie(Element):
    def __init__(self, x1, y1, x2, y2, **kw):
        super().__init__("linie", **kw)
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2

    def bbox(self):
        return (min(self.x1, self.x2), min(self.y1, self.y2),
                max(self.x1, self.x2), max(self.y1, self.y2))

    def verschieben(self, dx, dy):
        self.x1 += dx; self.y1 += dy
        self.x2 += dx; self.y2 += dy

    def griffe(self):
        return [("p1", self.x1, self.y1),
                ("p2", self.x2, self.y2),
                ("mid", (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)]

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p1":
            self.x1, self.y1 = x, y
        elif griff_id == "p2":
            self.x2, self.y2 = x, y
        elif griff_id == "mid":
            mx, my = (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2
            dx, dy = x - mx, y - my
            self.x1 += dx; self.y1 += dy
            self.x2 += dx; self.y2 += dy

    def drehen(self, cx, cy, winkel_deg):
        self.x1, self.y1 = punkte_drehen(self.x1, self.y1, cx, cy, winkel_deg)
        self.x2, self.y2 = punkte_drehen(self.x2, self.y2, cx, cy, winkel_deg)


class Kreis(Element):
    def __init__(self, cx, cy, r, **kw):
        super().__init__("kreis", **kw)
        self.cx, self.cy, self.r = cx, cy, r

    def bbox(self):
        return (self.cx - self.r, self.cy - self.r,
                self.cx + self.r, self.cy + self.r)

    def verschieben(self, dx, dy):
        self.cx += dx; self.cy += dy

    def griffe(self):
        return [("c", self.cx, self.cy),
                ("r", self.cx + self.r, self.cy)]

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "c":
            self.cx, self.cy = x, y
        elif griff_id == "r":
            self.r = max(0.001, math.hypot(x - self.cx, y - self.cy))

    def drehen(self, cx, cy, winkel_deg):
        self.cx, self.cy = punkte_drehen(self.cx, self.cy, cx, cy, winkel_deg)


class Bogen(Element):
    def __init__(self, cx, cy, r, start, ende, **kw):
        super().__init__("bogen", **kw)
        self.cx, self.cy, self.r = cx, cy, r
        self.start, self.ende = start, ende

    def bbox(self):
        return (self.cx - self.r, self.cy - self.r,
                self.cx + self.r, self.cy + self.r)

    def verschieben(self, dx, dy):
        self.cx += dx; self.cy += dy

    def _drei_punkte(self):
        """Start point, arc centre and end point in model coordinates."""
        mitte = self.start + bogen_sweep(self.start, self.ende) / 2.0
        def p(w):
            a = math.radians(w)
            return (self.cx + self.r * math.cos(a), self.cy + self.r * math.sin(a))
        return p(self.start), p(mitte), p(self.ende)

    def griffe(self):
        s_, m_, e_ = self._drei_punkte()
        return [("c", self.cx, self.cy),
                ("start", s_[0], s_[1]),
                ("mitte", m_[0], m_[1]),
                ("ende", e_[0], e_[1])]

    def _aus_drei_punkten(self, s_, m_, e_):
        """Arc through start s_, centre m_ and end e_ (as in AutoCAD:
        two points stay fixed, the dragged one determines radius/position)."""
        ax, ay = s_
        bx, by = m_
        qx, qy = e_
        d = 2.0 * (ax * (by - qy) + bx * (qy - ay) + qx * (ay - by))
        if abs(d) < 1e-9:
            return False                        # (almost) straight - not a circle
        a2, b2, q2 = ax * ax + ay * ay, bx * bx + by * by, qx * qx + qy * qy
        ux = (a2 * (by - qy) + b2 * (qy - ay) + q2 * (ay - by)) / d
        uy = (a2 * (qx - bx) + b2 * (ax - qx) + q2 * (bx - ax)) / d
        r = math.hypot(ax - ux, ay - uy)
        if not (1e-6 < r < 1e7):
            return False
        a_s = math.degrees(math.atan2(ay - uy, ax - ux))
        a_e = math.degrees(math.atan2(qy - uy, qx - ux))
        # Direction of travel s -> m -> e: > 0 = counter-clockwise
        orient = (bx - ax) * (qy - by) - (by - ay) * (qx - bx)
        if orient > 0:
            self.start, self.ende = a_s % 360.0, a_e % 360.0
        else:
            self.start, self.ende = a_e % 360.0, a_s % 360.0
        self.cx, self.cy, self.r = ux, uy, r
        return True

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "c":
            self.cx, self.cy = x, y
        elif griff_id in ("start", "mitte", "ende"):
            voll = bogen_sweep(self.start, self.ende) >= 359.99
            if voll:                            # Full circle: radius / angle
                if griff_id == "mitte":
                    self.r = max(0.001, math.hypot(x - self.cx, y - self.cy))
                elif griff_id == "start":
                    self.start = math.degrees(math.atan2(y - self.cy, x - self.cx)) % 360.0
                else:
                    self.ende = math.degrees(math.atan2(y - self.cy, x - self.cx)) % 360.0
                return
            s_, m_, e_ = self._drei_punkte()
            if griff_id == "start":
                s_ = (x, y)
            elif griff_id == "mitte":
                m_ = (x, y)
            else:
                e_ = (x, y)
            self._aus_drei_punkten(s_, m_, e_)
        elif griff_id == "r":
            self.r = max(0.001, math.hypot(x - self.cx, y - self.cy))

    def drehen(self, cx, cy, winkel_deg):
        self.cx, self.cy = punkte_drehen(self.cx, self.cy, cx, cy, winkel_deg)
        self.start = (self.start - winkel_deg) % 360.0
        self.ende = (self.ende - winkel_deg) % 360.0


class Rechteck(Element):
    def __init__(self, x1, y1, x2, y2, **kw):
        super().__init__("rechteck", **kw)
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2

    def bbox(self):
        return (min(self.x1, self.x2), min(self.y1, self.y2),
                max(self.x1, self.x2), max(self.y1, self.y2))

    def verschieben(self, dx, dy):
        self.x1 += dx; self.y1 += dy
        self.x2 += dx; self.y2 += dy

    def griffe(self):
        return [("p1", self.x1, self.y1),
                ("p2", self.x2, self.y1),
                ("p3", self.x2, self.y2),
                ("p4", self.x1, self.y2),
                ("mid", (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)]

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p1":
            self.x1, self.y1 = x, y
        elif griff_id == "p2":
            self.x2, self.y1 = x, y
        elif griff_id == "p3":
            self.x2, self.y2 = x, y
        elif griff_id == "p4":
            self.x1, self.y2 = x, y
        elif griff_id == "mid":
            mx, my = (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2
            dx, dy = x - mx, y - my
            self.x1 += dx; self.y1 += dy
            self.x2 += dx; self.y2 += dy

    def drehen(self, cx, cy, winkel_deg):
        if abs(winkel_deg / 90.0 - round(winkel_deg / 90.0)) < 1e-9:
            # multiples of 90 degrees: the rectangle stays axis-parallel
            self.x1, self.y1 = punkte_drehen(self.x1, self.y1, cx, cy, winkel_deg)
            self.x2, self.y2 = punkte_drehen(self.x2, self.y2, cx, cy, winkel_deg)
            return
        # any other angle: all four corners are rotated -> closed polyline
        # (rotating only two corners deformed the rectangle)
        pts = [punkte_drehen(x, y, cx, cy, winkel_deg) for (x, y) in
               ((self.x1, self.y1), (self.x2, self.y1),
                (self.x2, self.y2), (self.x1, self.y2))]
        neu = Polylinie(pts, geschlossen=True, layer=self.layer,
                        farbe=self.farbe, linientyp=self.linientyp,
                        eig_farbe=self.eig_farbe, staerke=self.staerke)
        self.__class__ = Polylinie
        self.__dict__.clear()
        self.__dict__.update(neu.__dict__)


class Polylinie(Element):
    def __init__(self, punkte, geschlossen=False, **kw):
        super().__init__("polylinie", **kw)
        self.punkte = [tuple(p) for p in punkte]
        self.geschlossen = geschlossen

    def bbox(self):
        if not self.punkte:
            return (0, 0, 0, 0)
        xs = [p[0] for p in self.punkte]
        ys = [p[1] for p in self.punkte]
        return (min(xs), min(ys), max(xs), max(ys))

    def verschieben(self, dx, dy):
        self.punkte = [(x + dx, y + dy) for (x, y) in self.punkte]

    def griffe(self):
        return [(f"p{i}", x, y) for i, (x, y) in enumerate(self.punkte)]

    def griff_bewegen(self, griff_id, x, y):
        if not griff_id.startswith("p"):
            return
        try:
            idx = int(griff_id[1:])
        except ValueError:
            return
        if 0 <= idx < len(self.punkte):
            self.punkte[idx] = (x, y)

    def drehen(self, cx, cy, winkel_deg):
        self.punkte = [punkte_drehen(x, y, cx, cy, winkel_deg)
                       for (x, y) in self.punkte]


class Ellipse(Polylinie):
    """Ellipse as a closed polyline (regenerated from its parameters):
    centre, semi-axes a (direction `rot`, degrees) and b (perpendicular)."""

    def __init__(self, cx, cy, a, b, rot=0.0, punkte=None, geschlossen=True, **kw):
        super().__init__([], True, **kw)
        self.typ = "ellipse"
        self.cx, self.cy, self.a, self.b, self.rot = cx, cy, a, b, rot
        self.neu_berechnen()

    def neu_berechnen(self):
        n = int(max(48, min(256, 24 + 12 * math.log2(1 + max(self.a, self.b)))))
        self.punkte = ellipse_punkte(self.cx, self.cy, max(self.a, 1e-9),
                                     max(self.b, 1e-9), self.rot, n)

    def verschieben(self, dx, dy):
        self.cx += dx; self.cy += dy
        self.punkte = [(x + dx, y + dy) for (x, y) in self.punkte]

    def griffe(self):
        r = math.radians(self.rot)
        c, s_ = math.cos(r), math.sin(r)
        return [("c", self.cx, self.cy),
                ("a", self.cx + self.a * c, self.cy + self.a * s_),
                ("b", self.cx - self.b * s_, self.cy + self.b * c)]

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "c":
            self.verschieben(x - self.cx, y - self.cy)
            return
        dx, dy = x - self.cx, y - self.cy
        d = math.hypot(dx, dy)
        if d < 1e-9:
            return
        if griff_id == "a":
            self.a = d
            self.rot = math.degrees(math.atan2(dy, dx)) % 360.0
        elif griff_id == "b":
            self.b = d
            self.rot = (math.degrees(math.atan2(dy, dx)) - 90.0) % 360.0
        self.neu_berechnen()

    def drehen(self, cx, cy, winkel_deg):
        self.cx, self.cy = punkte_drehen(self.cx, self.cy, cx, cy, winkel_deg)
        self.rot = (self.rot + winkel_deg) % 360.0
        self.neu_berechnen()


class Spline(Polylinie):
    """Smooth curve through the support points `stuetz` (Catmull-Rom),
    stored as a polyline in `punkte`."""

    def __init__(self, stuetz, geschlossen=False, punkte=None, **kw):
        super().__init__([], geschlossen, **kw)
        self.typ = "spline"
        self.stuetz = [tuple(p) for p in stuetz]
        self.neu_berechnen()

    def neu_berechnen(self):
        self.punkte = spline_punkte(self.stuetz, self.geschlossen)

    def verschieben(self, dx, dy):
        self.stuetz = [(x + dx, y + dy) for (x, y) in self.stuetz]
        self.punkte = [(x + dx, y + dy) for (x, y) in self.punkte]

    def griffe(self):
        return [(f"s{i}", x, y) for i, (x, y) in enumerate(self.stuetz)]

    def griff_bewegen(self, griff_id, x, y):
        if not griff_id.startswith("s"):
            return
        try:
            i = int(griff_id[1:])
        except ValueError:
            return
        if 0 <= i < len(self.stuetz):
            self.stuetz[i] = (x, y)
            self.neu_berechnen()

    def drehen(self, cx, cy, winkel_deg):
        self.stuetz = [punkte_drehen(x, y, cx, cy, winkel_deg)
                       for (x, y) in self.stuetz]
        self.neu_berechnen()


class Text(Element):
    EINFUEGEPUNKTE = (
        "oben_links", "oben_zentriert", "oben_rechts",
        "mitte_links", "mitte_zentriert", "mitte_rechts",
        "unten_links", "unten_zentriert", "unten_rechts",
    )
    STANDARD_EINFUEGEPUNKT = "unten_links"

    def __init__(self, x, y, inhalt, hoehe=3.5, winkel=0.0,
                 schriftart="Arial", einfuegepunkt=None, **kw):
        super().__init__("text", **kw)
        self.x, self.y = x, y
        self.inhalt = inhalt
        self.hoehe = hoehe
        self.winkel = winkel
        self.schriftart = schriftart
        if einfuegepunkt not in self.EINFUEGEPUNKTE:
            einfuegepunkt = self.STANDARD_EINFUEGEPUNKT
        self.einfuegepunkt = einfuegepunkt

    def masse(self):
        zeilen = self.inhalt.split("\n") or [""]
        # Real character widths (Helvetica/Arial metrics, identical to the PDF):
        # "A" is wider than "1". A fixed width per character let texts
        # protrude beyond the insertion point.
        fs = self.hoehe / CAD_VERSALHOEHE
        w = max(max(pdf_textbreite(z, fs, schrift_fett(self.schriftart)) for z in zeilen),
                TEXT_BREITE * self.hoehe)
        h = (len(zeilen) - 1) * TEXT_ZEILE * self.hoehe + 1.4 * self.hoehe
        return w, h

    def _versatz_lokal(self, w, h):
        vertikal, horizontal = self.einfuegepunkt.split("_")
        if horizontal == "links":
            dx = 0.0
        elif horizontal == "zentriert":
            dx = -w / 2.0
        else:
            dx = -w
        unterlaenge = 0.3 * self.hoehe
        if vertikal == "unten":
            dy = unterlaenge
        elif vertikal == "mitte":
            dy = -(h - unterlaenge) / 2.0
        else:
            dy = -(h - 0.3 * self.hoehe)
        return dx, dy

    def ecken_welt(self):
        w, h = self.masse()
        dx, dy = self._versatz_lokal(w, h)
        a = math.radians(self.winkel)
        ex = (math.cos(a), math.sin(a))
        ey = (-math.sin(a), math.cos(a))
        ux = self.x + dx * ex[0] + dy * ey[0]
        uy = self.y + dx * ex[1] + dy * ey[1]
        ecken = []
        for sx, sy in ((0, 0), (w, 0), (w, h), (0, h)):
            ecken.append((ux + sx * ex[0] + sy * ey[0],
                          uy + sx * ex[1] + sy * ey[1]))
        return ecken

    def rahmen(self):
        return self.ecken_welt()

    def bbox(self):
        pts = self.rahmen()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def punkt_im_rahmen(self, px, py, tol=0.0):
        w, h = self.masse()
        dx, dy = self._versatz_lokal(w, h)
        a = math.radians(-self.winkel)
        rel_x, rel_y = px - self.x, py - self.y
        lx = rel_x * math.cos(a) - rel_y * math.sin(a)
        ly = rel_x * math.sin(a) + rel_y * math.cos(a)
        return (dx - tol <= lx <= dx + w + tol and
                dy - tol <= ly <= dy + h + tol)

    def verschieben(self, dx, dy):
        self.x += dx; self.y += dy

    def griffe(self):
        return [("p", self.x, self.y)]

    def griff_bewegen(self, griff_id, x, y):
        self.x, self.y = x, y

    def drehen(self, cx, cy, winkel_deg):
        self.x, self.y = punkte_drehen(self.x, self.y, cx, cy, winkel_deg)
        self.winkel = (self.winkel - winkel_deg) % 360.0


class Bemassung(Element):
    def __init__(self, x1, y1, x2, y2, mx=None, my=None,
                 richtung="ausgerichtet", text_override="",
                 tx=None, ty=None, hoehe=2.5, pfeil=2.5, dez=2,
                 offset=10.0, offset_x=0.0, offset_y=0.0,
                 text_offset_x=0.0, text_offset_y=0.0, x3=None, y3=None, **kw):
        super().__init__("bemassung", **kw)
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        # angle dimension: (x1,y1) = vertex, (x2,y2)/(x3,y3) = points on the
        # two legs, (mx,my) = point on the dimension arc (radius and sector)
        self.x3, self.y3 = x3, y3
        self.richtung = richtung if richtung in BEM_RICHTUNGEN else "ausgerichtet"
        self.text_override = text_override or ""
        self.hoehe = float(hoehe)
        self.pfeil = float(pfeil)
        self.dez = int(dez)
        self.tx, self.ty = tx, ty
        if mx is None or my is None:
            mx, my = self._alte_massposition(offset, offset_x, offset_y)
        self.mx, self.my = mx, my

    def _alte_massposition(self, offset, offset_x, offset_y):
        if self.richtung == "horizontal":
            ay = self.y1 + offset if self.y2 >= self.y1 else self.y1 - offset
            return ((self.x1 + self.x2) / 2 + offset_x, ay + offset_y)
        if self.richtung == "vertikal":
            ax = self.x1 + offset if self.x2 >= self.x1 else self.x1 - offset
            return (ax + offset_x, (self.y1 + self.y2) / 2 + offset_y)
        if self.richtung in ("radius", "durchmesser"):
            return (self.x2, self.y2)
        if self.richtung == "winkel":
            return (self.x2, self.y2)
        dx, dy = self.x2 - self.x1, self.y2 - self.y1
        L = math.hypot(dx, dy)
        if L < 1e-9:
            return (self.x1, self.y1)
        nx, ny = -dy / L, dx / L
        return ((self.x1 + self.x2) / 2 + nx * offset + offset_x,
                (self.y1 + self.y2) / 2 + ny * offset + offset_y)

    @staticmethod
    def linear_richtung(p1, p2, m):
        dx, dy = abs(p2[0] - p1[0]), abs(p2[1] - p1[1])

        # NEW: if the line is slanted, the line angle is used automatically
        if dx > 1e-6 and dy > 1e-6:
            return "ausgerichtet"

        cx, cy = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ex = abs(m[0] - cx) - dx / 2
        ey = abs(m[1] - cy) - dy / 2
        r = "horizontal" if ey >= ex else "vertikal"

        if r == "horizontal" and dx < 1e-9 < dy:
            r = "vertikal"
        elif r == "vertikal" and dy < 1e-9 < dx:
            r = "horizontal"
        return r

    def _winkel_daten(self):
        """Angle dimension -> (a0, sweep, R) in degrees/mm or None.
        The sector is the one in which the dimension arc point lies."""
        if self.richtung != "winkel" or self.x3 is None or self.y3 is None:
            return None
        c = (self.x1, self.y1)
        R = math.hypot(self.mx - c[0], self.my - c[1])
        if (math.hypot(self.x2 - c[0], self.y2 - c[1]) < 1e-9
                or math.hypot(self.x3 - c[0], self.y3 - c[1]) < 1e-9):
            return None
        a1 = math.degrees(math.atan2(self.y2 - c[1], self.x2 - c[0])) % 360.0
        a2 = math.degrees(math.atan2(self.y3 - c[1], self.x3 - c[0])) % 360.0
        if R < 1e-9:
            am = (a1 + ((a2 - a1) % 360.0) / 2.0) % 360.0
            R = 0.5 * min(math.hypot(self.x2 - c[0], self.y2 - c[1]),
                          math.hypot(self.x3 - c[0], self.y3 - c[1]))
        else:
            am = math.degrees(math.atan2(self.my - c[1], self.mx - c[0])) % 360.0
        if (am - a1) % 360.0 <= (a2 - a1) % 360.0:
            return a1, (a2 - a1) % 360.0, R
        return a2, (a1 - a2) % 360.0, R

    def wert(self):
        if self.richtung == "winkel":
            w = self._winkel_daten()
            return w[1] if w else 0.0
        d = math.hypot(self.x2 - self.x1, self.y2 - self.y1)
        if self.richtung == "radius":
            return d
        if self.richtung == "durchmesser":
            return 2 * d
        if self.richtung == "horizontal":
            return abs(self.x2 - self.x1)
        if self.richtung == "vertikal":
            return abs(self.y2 - self.y1)
        return d

    def text(self, faktor=1.0, komma=True):
        if self.richtung == "winkel":
            s = bem_zahl(self.wert(), self.dez, komma) + "\u00b0"
            if self.text_override:
                return (self.text_override.replace("<>", s)
                        if "<>" in self.text_override else self.text_override)
            return s
        s = bem_zahl(self.wert() / faktor, self.dez, komma)
        if self.richtung == "radius":
            s = "R" + s
        elif self.richtung == "durchmesser":
            s = "\u00d8" + s
        if self.text_override:
            if "<>" in self.text_override:
                return self.text_override.replace("<>", s)
            return self.text_override
        return s

    def geometrie(self, faktor=1.0, komma=True):
        h = max(0.05, self.hoehe)
        pf = max(0.05, self.pfeil)
        s = h / 2.5
        gap, ueber, tgap = 0.625 * s, 1.25 * s, 0.625 * s
        txt = self.text(faktor, komma)
        tw = max(max(pdf_textbreite(z, h / CAD_VERSALHOEHE)
                     for z in txt.split("\n")), TEXT_BREITE * h)
        res = {"linien": [], "pfeile": [], "text": None, "mitte": None}
        manuell = self.tx is not None and self.ty is not None
        r = self.richtung

        if r in ("horizontal", "vertikal", "ausgerichtet"):
            p1, p2, m = (self.x1, self.y1), (self.x2, self.y2), (self.mx, self.my)
            if r == "horizontal":
                n, a_deg = (0.0, 1.0), 0.0
            elif r == "vertikal":
                n, a_deg = (1.0, 0.0), 90.0
            else:
                L0 = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                if L0 < 1e-9:
                    return res
                n = (-(p2[1] - p1[1]) / L0, (p2[0] - p1[0]) / L0)
                a_deg = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
                if a_deg > 90.0 + 1e-9:
                    a_deg -= 180.0
                elif a_deg <= -90.0 + 1e-9:
                    a_deg += 180.0

            def fuss(p):
                d = (m[0] - p[0]) * n[0] + (m[1] - p[1]) * n[1]
                return (p[0] + n[0] * d, p[1] + n[1] * d)

            a, b = fuss(p1), fuss(p2)
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 1e-9:
                return res
            t = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)

            for p, q in ((p1, a), (p2, b)):
                dx, dy = q[0] - p[0], q[1] - p[1]
                dist = math.hypot(dx, dy)
                if dist > gap + 1e-9:
                    ux, uy = dx / dist, dy / dist
                    res["linien"].append((p[0] + ux * gap, p[1] + uy * gap,
                                          q[0] + ux * ueber, q[1] + uy * ueber))

            innen = L >= 2.2 * pf
            ext = 0.0 if innen else 1.5 * pf
            res["linien"].append((a[0] - t[0] * ext, a[1] - t[1] * ext,
                                  b[0] + t[0] * ext, b[1] + t[1] * ext))
            if innen:
                res["pfeile"].append((a[0], a[1], math.atan2(-t[1], -t[0]), pf))
                res["pfeile"].append((b[0], b[1], math.atan2(t[1], t[0]), pf))
            else:
                res["pfeile"].append((a[0], a[1], math.atan2(t[1], t[0]), pf))
                res["pfeile"].append((b[0], b[1], math.atan2(-t[1], -t[0]), pf))

            ar = math.radians(a_deg)
            up = (-math.sin(ar), math.cos(ar))
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            res["mitte"] = mid
            if manuell:
                c = (self.tx, self.ty)
            elif tw + 2 * tgap <= L:
                c = (mid[0] + up[0] * (tgap + h / 2), mid[1] + up[1] * (tgap + h / 2))
            else:
                d = ext + tgap + tw / 2
                c = (b[0] + t[0] * d + up[0] * (tgap + h / 2),
                     b[1] + t[1] * d + up[1] * (tgap + h / 2))
            res["text"] = (txt, c[0], c[1], a_deg, tw, h)
            return res

        if r == "winkel":
            wd = self._winkel_daten()
            if wd is None:
                return res
            a0, sw, R = wd
            C = (self.x1, self.y1)
            a_end = a0 + sw
            for ang in (a0, a_end):
                u = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
                # extension line along the leg up to the arc (only if the
                # leg point lies inside the arc radius)
                for q in ((self.x2, self.y2), (self.x3, self.y3)):
                    aq = math.degrees(math.atan2(q[1] - C[1], q[0] - C[0]))
                    if abs(((aq - ang) + 180.0) % 360.0 - 180.0) < 1e-6:
                        dq = math.hypot(q[0] - C[0], q[1] - C[1])
                        if dq < R - gap:
                            res["linien"].append(
                                (C[0] + u[0] * (dq + gap), C[1] + u[1] * (dq + gap),
                                 C[0] + u[0] * (R + ueber), C[1] + u[1] * (R + ueber)))
                        elif dq > R:
                            res["linien"].append(
                                (C[0] + u[0] * R, C[1] + u[1] * R,
                                 C[0] + u[0] * (R + ueber), C[1] + u[1] * (R + ueber)))
                        break
            n = max(8, int(sw / 3.0) + 1)
            pts = [(C[0] + R * math.cos(math.radians(a0 + sw * i / n)),
                    C[1] + R * math.sin(math.radians(a0 + sw * i / n)))
                   for i in range(n + 1)]
            for i in range(n):
                res["linien"].append((pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]))
            res["pfeile"].append((pts[0][0], pts[0][1],
                                  math.radians(a0 - 90.0), pf))
            res["pfeile"].append((pts[-1][0], pts[-1][1],
                                  math.radians(a_end + 90.0), pf))
            am = math.radians(a0 + sw / 2.0)
            res["mitte"] = (C[0] + R * math.cos(am), C[1] + R * math.sin(am))
            t_deg = (a0 + sw / 2.0 - 90.0)
            t_deg = (t_deg + 180.0) % 360.0 - 180.0
            if t_deg > 90.0 + 1e-9:
                t_deg -= 180.0
            elif t_deg <= -90.0 + 1e-9:
                t_deg += 180.0
            if manuell:
                c = (self.tx, self.ty)
            else:
                d = R + tgap + h / 2
                c = (C[0] + d * math.cos(am), C[1] + d * math.sin(am))
            res["text"] = (txt, c[0], c[1], t_deg, tw, h)
            return res

        # ---------- Radius / diameter -------------
        C, P = (self.x1, self.y1), (self.x2, self.y2)
        rad = math.hypot(P[0] - C[0], P[1] - C[1])
        if rad < 1e-9:
            return res
        u = ((P[0] - C[0]) / rad, (P[1] - C[1]) / rad)

        if r == "radius":
            # Small centre cross (proportional, but not larger than the circle)
            k = min(0.5 * h, rad * 0.4)
            res["linien"].append((C[0] - k, C[1], C[0] + k, C[1]))
            res["linien"].append((C[0], C[1] - k, C[0], C[1] + k))

            # Measurement line from the centre to the arc point
            res["linien"].append((C[0], C[1], P[0], P[1]))

            # Arrow on the arc, pointing outwards (towards the measured point)
            res["pfeile"].append((P[0], P[1], math.atan2(u[1], u[0]), pf))

            # Text position: manual (tx/ty) or from mx/my
            if manuell:
                c = (self.tx, self.ty)
            else:
                c = (self.mx, self.my)
                d_center = math.hypot(c[0] - C[0], c[1] - C[1])
                if d_center < h:
                    c = (P[0] + u[0] * (tgap + h),
                         P[1] + u[1] * (tgap + h))

            # Leader line if the text is outside the arc
            d_p = math.hypot(c[0] - P[0], c[1] - P[1])
            if d_p > h * 0.8:
                res["linien"].append((P[0], P[1], c[0], c[1]))

            res["text"] = (txt, c[0], c[1], 0.0, tw, h)
            res["mitte"] = ((C[0] + P[0]) / 2, (C[1] + P[1]) / 2)

        else:  # diameter
            Q = (2 * C[0] - P[0], 2 * C[1] - P[1])

            # Line through the whole circle, arrows at both ends
            res["linien"].append((P[0], P[1], Q[0], Q[1]))
            res["pfeile"].append((P[0], P[1], math.atan2(u[1], u[0]), pf))
            res["pfeile"].append((Q[0], Q[1], math.atan2(-u[1], -u[0]), pf))

            # Adjust text slant to the measurement line (in [-90, +90])
            a_deg = math.degrees(math.atan2(u[1], u[0]))
            if a_deg > 90.0 + 1e-9:
                a_deg -= 180.0
            elif a_deg <= -90.0 + 1e-9:
                a_deg += 180.0
            ar = math.radians(a_deg)
            up = (-math.sin(ar), math.cos(ar))   # perpendicular to the measurement line

            # Text position: manual tx/ty, otherwise centred above/below the centre
            if manuell:
                c = (self.tx, self.ty)
            else:
                # Determine the side from the mouse click position
                seite = 1.0 if ((self.mx - C[0]) * up[0] +
                                (self.my - C[1]) * up[1]) >= 0 else -1.0
                c = (C[0] + up[0] * (tgap + h / 2) * seite,
                     C[1] + up[1] * (tgap + h / 2) * seite)

            # Leader line from the nearest arrow to the text
            # if the text is outside the circle
            d_center = math.hypot(c[0] - C[0], c[1] - C[1])
            if d_center > rad + h * 0.3:
                d_p = math.hypot(c[0] - P[0], c[1] - P[1])
                d_q = math.hypot(c[0] - Q[0], c[1] - Q[1])
                arrow = P if d_p < d_q else Q
                res["linien"].append((arrow[0], arrow[1], c[0], c[1]))

            res["text"] = (txt, c[0], c[1], a_deg, tw, h)
            res["mitte"] = C

        return res

    def bbox(self):
        g = self.geometrie()
        xs, ys = [], []
        for l in g["linien"]:
            xs += [l[0], l[2]]; ys += [l[1], l[3]]
        for p in g["pfeile"]:
            xs.append(p[0]); ys.append(p[1])
        if g["text"]:
            _, cx, cy, ang, w, h = g["text"]
            for (x, y) in gedrehtes_rechteck(cx, cy, w, h, ang):
                xs.append(x); ys.append(y)
        if not xs:
            return (min(self.x1, self.x2), min(self.y1, self.y2),
                    max(self.x1, self.x2), max(self.y1, self.y2))
        return (min(xs), min(ys), max(xs), max(ys))

    def verschieben(self, dx, dy):
        self.x1 += dx; self.y1 += dy
        self.x2 += dx; self.y2 += dy
        if self.x3 is not None and self.y3 is not None:
            self.x3 += dx; self.y3 += dy
        self.mx += dx; self.my += dy
        if self.tx is not None and self.ty is not None:
            self.tx += dx; self.ty += dy

    def griffe(self):
        g = self.geometrie()
        mx, my = g["mitte"] if g["mitte"] else (self.mx, self.my)
        gr = [("p1", self.x1, self.y1), ("p2", self.x2, self.y2),
              ("mass", mx, my)]
        if self.x3 is not None and self.y3 is not None:
            gr.insert(2, ("p3", self.x3, self.y3))
        if g["text"]:
            gr.append(("text", g["text"][1], g["text"][2]))
        return gr

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p1":
            self.x1, self.y1 = x, y
        elif griff_id == "p2":
            self.x2, self.y2 = x, y
        elif griff_id == "p3":
            self.x3, self.y3 = x, y
        elif griff_id == "mass":
            self.mx, self.my = x, y
        elif griff_id == "text":
            self.tx, self.ty = x, y

    def drehen(self, cx, cy, winkel_deg):
        self.x1, self.y1 = punkte_drehen(self.x1, self.y1, cx, cy, winkel_deg)
        self.x2, self.y2 = punkte_drehen(self.x2, self.y2, cx, cy, winkel_deg)
        if self.x3 is not None and self.y3 is not None:
            self.x3, self.y3 = punkte_drehen(self.x3, self.y3, cx, cy, winkel_deg)
        self.mx, self.my = punkte_drehen(self.mx, self.my, cx, cy, winkel_deg)
        if self.tx is not None and self.ty is not None:
            self.tx, self.ty = punkte_drehen(self.tx, self.ty, cx, cy, winkel_deg)
        if self.richtung in ("horizontal", "vertikal"):
            self.richtung = "ausgerichtet"


class Bild(Element):
    """Raster image (imported PNG/JPG ...). Lower left corner x/y, size in mm.
    The picture data is stored in the element (base64, `format` = jpeg|png)."""

    def __init__(self, x, y, breite, hoehe, daten="", format="jpeg",
                 pw=1, ph=1, **kw):
        super().__init__("bild", **kw)
        self.x, self.y = float(x), float(y)
        self.breite, self.hoehe = float(breite), float(hoehe)
        self.daten = daten
        self.format = format
        self.pw, self.ph = int(pw), int(ph)

    def bbox(self):
        return (self.x, self.y, self.x + self.breite, self.y + self.hoehe)

    def rahmen(self):
        return [(self.x, self.y), (self.x + self.breite, self.y),
                (self.x + self.breite, self.y + self.hoehe),
                (self.x, self.y + self.hoehe)]

    def verschieben(self, dx, dy):
        self.x += dx; self.y += dy

    def griffe(self):
        return [("ecke", self.x + self.breite, self.y + self.hoehe),
                ("mitte", self.x + self.breite / 2, self.y + self.hoehe / 2)]

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "ecke":              # resize, aspect ratio stays
            b = max(0.1, x - self.x)
            self.hoehe = b * self.ph / float(self.pw)
            self.breite = b
        elif griff_id == "mitte":
            self.x = x - self.breite / 2
            self.y = y - self.hoehe / 2


class Viewport(Element):
    def __init__(self, x, y, breite, hoehe,
                 modell_zentrum_x=0.0, modell_zentrum_y=0.0,
                 zoom=1.0, gesperrt=False, ansicht3d=None, **kw):
        super().__init__("viewport", **kw)
        self.x, self.y = x, y
        self.breite, self.hoehe = breite, hoehe
        self.modell_zentrum_x = modell_zentrum_x
        self.modell_zentrum_y = modell_zentrum_y
        self.zoom = zoom
        self.gesperrt = bool(gesperrt)
        self.aktiv = False
        # None = normal 2D view; dict {"yaw", "pitch", "persp", "zielz", "abstand"} = 3D wireframe
        self.ansicht3d = dict(ansicht3d) if ansicht3d else None

    def bbox(self):
        return (self.x, self.y, self.x + self.breite, self.y + self.hoehe)

    def to_dict(self):
        d = super().to_dict()
        d.pop("aktiv", None)
        return d

    def verschieben(self, dx, dy):
        self.x += dx; self.y += dy

    def drehen(self, cx, cy, winkel_deg):
        mx = self.x + self.breite / 2
        my = self.y + self.hoehe / 2
        nx, ny = punkte_drehen(mx, my, cx, cy, winkel_deg)
        self.x = nx - self.breite / 2
        self.y = ny - self.hoehe / 2


# ============================================================
# NEW: block support
# ============================================================
class AttributDefinition(Text):
    """Attribute definition (like ATTDEF in AutoCAD).

    A text that becomes part of a block definition. When the block is
    inserted, each reference gets its own value per attribute tag
    (e.g. NAME, DEVICETYPE, POWER), which can be edited later.

    In the normal drawing area only the tag is shown as a placeholder;
    in a BlockReferenz the value is shown instead (see
    BlockReferenz.aufgeloest()).
    """

    def __init__(self, x, y, inhalt=None, hoehe=3.5, winkel=0.0,
                 schriftart="Arial", einfuegepunkt=None,
                 tag="ATTR", prompt="", wert="", sichtbar=True, **kw):
        tag = str(tag or "ATTR").strip().upper().replace(" ", "_")
        if inhalt is None:
            inhalt = "<" + tag + ">"
        super().__init__(x, y, inhalt, hoehe, winkel, schriftart,
                         einfuegepunkt, **kw)
        self.typ = "attdef"
        self.tag = tag
        self.prompt = prompt or tag
        self.wert = wert if wert is not None else ""
        self.sichtbar = bool(sichtbar)

    def als_text(self, wert):
        """Normal text element with the given value (or None if
        the attribute is invisible or empty)."""
        if not self.sichtbar or wert is None or str(wert) == "":
            return None
        return Text(self.x, self.y, str(wert), self.hoehe, self.winkel,
                    self.schriftart, einfuegepunkt=self.einfuegepunkt,
                    layer=self.layer, farbe=self.farbe,
                    linientyp=self.linientyp, eig_farbe=self.eig_farbe,
                    staerke=self.staerke)


def _attribut_defs(elemente):
    """AttributDefinitionen + fixed fields (IND/TYP/PER/NUM) of masks."""
    out = [e for e in elemente if isinstance(e, AttributDefinition)]
    vorhanden = {a.tag for a in out}
    for e in elemente:
        if isinstance(e, _FestMaske):
            for t in e.FELDER:
                if t not in vorhanden:
                    out.append(AttributDefinition(0, 0, None, 2.5, tag=t,
                                                  prompt=t, wert=e.werte.get(t, "")))
                    vorhanden.add(t)
    return out


class BlockDefinition:
    """Named template of a block.

    The elements are stored in *local* coordinates, i.e. already relative
    to the base point (base point = (0, 0) in the local system).
    This greatly simplifies transforming them later on insertion.
    """

    def __init__(self, name, basispunkt, elemente):
        self.name = name
        self.basispunkt = tuple(basispunkt)
        self.elemente = list(elemente)

    def attribut_definitionen(self):
        """All attributes of this block definition (incl. the fixed fields
        of electrical mask / terminal)."""
        return _attribut_defs(self.elemente)

    def to_dict(self):
        return {
            "name": self.name,
            "basispunkt": list(self.basispunkt),
            "elemente": [e.to_dict() for e in self.elemente],
        }

    @classmethod
    def from_dict(cls, d, element_factory):
        els = []
        for ed in d.get("elemente", []):
            el = element_factory(ed)
            if el is not None:
                els.append(el)
        return cls(d.get("name", "Block"),
                   tuple(d.get("basispunkt", (0.0, 0.0))),
                   els)


class BlockReferenz(Element):
    """An inserted block.

    Holds a *deep copy* of the definition elements (relative to the base
    point). This keeps the drawing self-contained, and changes to the
    definition do not retroactively affect placed instances (deliberately
    kept simple - real AutoCAD behaves differently, but for our purposes
    these semantics are clearer and more robust).
    """

    def __init__(self, x, y, block_name, elemente,
                 skalierung=1.0, winkel=0.0, attribute=None,
                 ausgeblendet=None, sp_dx=0.0, sp_dy=0.0, gespiegelt=False,
                 text_versatz=None, **kw):
        super().__init__("block", **kw)
        # Free text positions of THIS instance: {"M:IND": [dx, dy], "V:VP1": ...,
        # "A:TAG": ...}; M = mask/terminal field, V = pin label, A = attribute
        self.text_versatz = {str(k): [float(v[0]), float(v[1])]
                             for k, v in (text_versatz or {}).items()}
        self._anker = {}          # automatic text positions (computed)
        self.gespiegelt = bool(gespiegelt)     # mirrored about the local y axis
        self.sp_dx, self.sp_dy = float(sp_dx), float(sp_dy)   # contact mirror offset
        self.x, self.y = x, y
        self.block_name = block_name
        # deep copy so that the reference is truly independent
        self.elemente = [deepcopy(e) for e in elemente]
        self.skalierung = float(skalierung) if skalierung else 1.0
        self.winkel = float(winkel) if winkel else 0.0
        # Attribute values of this instance: {TAG: value}
        self.attribute = dict(attribute) if attribute else {}
        for ad in self.attribut_definitionen():
            self.attribute.setdefault(ad.tag, ad.wert)
        # Tags whose text is not displayed in THIS instance
        self.ausgeblendet = set(ausgeblendet or [])
        self._cache = None          # (signature, resolved children)
        self.refs = []              # Device references (sheet numbers), computed
        self.kontakte = []          # Contact mirror entries (art, pins, ort), computed

    # ---- Attributes --------------------------------------------
    def attribut_definitionen(self):
        return _attribut_defs(self.elemente)

    def geraet_maske(self):
        """Electrical mask of this block (device) or None."""
        for e in self.elemente:
            if isinstance(e, ElektroMaske):
                return e
        return None

    def attribut_wert(self, tag):
        return self.attribute.get(tag, "")

    def setze_ausgeblendet(self, tags):
        bekannt = {ad.tag for ad in self.attribut_definitionen()}
        self.ausgeblendet = {t for t in tags if t in bekannt}

    def setze_attribute(self, werte):
        """Takes over values {TAG: value} (known tags only)."""
        bekannt = {ad.tag for ad in self.attribut_definitionen()}
        for tag, wert in werte.items():
            if tag in bekannt:
                self.attribute[tag] = str(wert)

    # ---- Transformation ----------------------------------------
    def _welt_pts(self, lx, ly):
        """Local coordinates (relative to the base point) -> world coordinates.
        Takes scaling, rotation (positive angle = counter-clockwise, as with
        text/arc angles) and translation into account."""
        s = self.skalierung
        a = math.radians(self.winkel)
        ca, sa = math.cos(a), math.sin(a)
        px, py = lx * s, ly * s
        return (self.x + px * ca - py * sa,
                self.y + px * sa + py * ca)

    def _transformiere(self, el):
        """Transforms a child element *in place* from the local to the
        world coordinate system."""
        if isinstance(el, Linie):
            el.x1, el.y1 = self._welt_pts(el.x1, el.y1)
            el.x2, el.y2 = self._welt_pts(el.x2, el.y2)
        elif isinstance(el, Kreis):
            el.cx, el.cy = self._welt_pts(el.cx, el.cy)
            el.r *= self.skalierung
        elif isinstance(el, Bogen):
            el.cx, el.cy = self._welt_pts(el.cx, el.cy)
            el.r *= self.skalierung
            el.start = (el.start + self.winkel) % 360.0
            el.ende = (el.ende + self.winkel) % 360.0
        elif isinstance(el, Rechteck):
            # Rotated rectangle -> polyline (an axis-parallel rectangle
            # can no longer be represented as a rectangle after rotation)
            p1 = self._welt_pts(el.x1, el.y1)
            p2 = self._welt_pts(el.x2, el.y1)
            p3 = self._welt_pts(el.x2, el.y2)
            p4 = self._welt_pts(el.x1, el.y2)
            neu = Polylinie([p1, p2, p3, p4], geschlossen=True,
                            layer=el.layer, farbe=el.farbe,
                            linientyp=el.linientyp,
                            eig_farbe=el.eig_farbe, staerke=el.staerke)
            el.__class__ = Polylinie
            el.__dict__.clear()
            el.__dict__.update(neu.__dict__)
        elif isinstance(el, Polylinie):
            el.punkte = [self._welt_pts(x, y) for (x, y) in el.punkte]
            if isinstance(el, (Ellipse, Spline)):
                # parameters would be stale after the transformation
                for _k in ("cx", "cy", "a", "b", "rot", "stuetz"):
                    el.__dict__.pop(_k, None)
                el.typ = "polylinie"
                el.__class__ = Polylinie
        elif isinstance(el, Text):
            el.x, el.y = self._welt_pts(el.x, el.y)
            el.hoehe *= self.skalierung
            el.winkel = (el.winkel + self.winkel) % 360.0
            if isinstance(el, Verbindungspunkt):
                el.radius *= self.skalierung
                if el.richtungen is not None:
                    el.richtungen = sorted(
                        {int(round((r + self.winkel) / 90.0)) * 90 % 360
                         for r in el.richtungen})
        elif isinstance(el, Querverweis):
            el.x, el.y = self._welt_pts(el.x, el.y)
            el.richtung = round((el.richtung + self.winkel) / 90.0) * 90 % 360
        elif isinstance(el, Schraffur):
            # (was missing before: hatchings stayed at the origin on insertion)
            el.punkte = [self._welt_pts(x, y) for (x, y) in el.punkte]
            el.winkel = (el.winkel + self.winkel) % 360.0
            el.abstand *= self.skalierung
        elif isinstance(el, (_FestMaske, Koordinatenfeld)):
            el.x, el.y = self._welt_pts(el.x, el.y)      # Texts stay horizontal
        elif isinstance(el, Verbindung):
            el.x, el.y = self._welt_pts(el.x, el.y)
            el.arme = Verbindung.arme_normieren(
                [d + self.winkel for d in el.arme])
            el.ausrichtung = (el.ausrichtung + int(round(self.winkel / 90.0))) % 4
        elif isinstance(el, Bemassung):
            el.x1, el.y1 = self._welt_pts(el.x1, el.y1)
            el.x2, el.y2 = self._welt_pts(el.x2, el.y2)
            el.mx, el.my = self._welt_pts(el.mx, el.my)
            if el.tx is not None and el.ty is not None:
                el.tx, el.ty = self._welt_pts(el.tx, el.ty)
            el.hoehe *= self.skalierung
            el.pfeil *= self.skalierung
            # Direction "horizontal"/"vertical" becomes, after rotation,
            # "aligned", otherwise it would look wrong.
            if self.winkel % 360.0 not in (0.0, 180.0):
                if el.richtung in ("horizontal", "vertikal"):
                    el.richtung = "ausgerichtet"

    def aufgeloest(self):
        """Returns the transformed child elements as a flat list."""
        # Result is cached: snapping, drawing and hit tests
        # call this on every mouse movement - without a cache thousands
        # of deep copies would be created (memory pressure with many symbols).
        # The list is READ-ONLY (when resolving: copy first).
        sig = (self.x, self.y, self.skalierung, self.winkel,
               tuple(sorted(self.attribute.items())),
               tuple(sorted(self.ausgeblendet)), tuple(self.refs),
               tuple((a, tuple(p), tuple(o) if isinstance(o, (tuple, list)) else o)
                     for a, p, o in self.kontakte),
               self.sp_dx, self.sp_dy, self.gespiegelt,
               tuple(sorted((k, tuple(v)) for k, v in self.text_versatz.items())))
        if self._cache is not None and self._cache[0] == sig:
            return self._cache[1]
        out = []
        self._anker = {}
        tv = self.text_versatz
        for el in self.elemente:
            k = deepcopy(el)
            if self.gespiegelt:
                k.spiegeln(0.0, 0.0, 0.0, 1.0)   # about the local y axis
            self._transformiere(k)
            if isinstance(k, _FestMaske):
                # Mask/terminal: values come from the attributes of the instance
                k.werte = {t: str(self.attribute.get(t, k.werte.get(t, "")))
                           for t in k.FELDER}
                k.ausgeblendet = set(self.ausgeblendet) & set(k.FELDER)
                k.refs = list(self.refs)
                k.kontakte = list(self.kontakte)
                k.platzhalter = False
                k.versatz = {t[2:]: v for t, v in tv.items() if t.startswith("M:")}
                k.aufgeloest(False)               # fills the automatic positions
                for t, (ax, ay) in k._anker.items():
                    self._anker["M:" + t] = (ax, ay)
                out.append(k)
                continue
            if isinstance(k, Verbindungspunkt):
                # Connection point: circle + label remain one element,
                # the label comes from the attribute value of the instance.
                k.wert = str(self.attribute.get(k.tag, k.wert))
                k.inhalt = k.wert
                if k.tag in self.ausgeblendet:
                    k.sichtbar = False
                if k.sichtbar and k.wert != "":
                    self._anker["V:" + k.tag] = k.text_anker()
                if "V:" + k.tag in tv:
                    k.text_dx, k.text_dy = tv["V:" + k.tag]
                out.append(k)
                continue
            if isinstance(k, AttributDefinition):
                if k.tag in self.ausgeblendet:
                    continue
                tag = k.tag
                k = k.als_text(self.attribute.get(k.tag, k.wert))
                if k is None:
                    continue
                self._anker["A:" + tag] = (k.x, k.y)
                if "A:" + tag in tv:
                    k.x += tv["A:" + tag][0]
                    k.y += tv["A:" + tag][1]
            out.append(k)
        # Symbol bbox + mirror offset for the device masks of this instance
        geo = [e.bbox() for e in out
               if isinstance(e, (Linie, Kreis, Bogen, Rechteck, Polylinie))]
        sbb = (min(b[0] for b in geo), min(b[1] for b in geo),
               max(b[2] for b in geo), max(b[3] for b in geo)) if geo else None
        for e in out:
            if isinstance(e, ElektroMaske):
                e.sym_bbox = sbb
                e.sp_dx, e.sp_dy = self.sp_dx, self.sp_dy
        self._cache = (sig, out)
        return out

    def _maske_welt(self):
        for e in self.aufgeloest():
            if isinstance(e, ElektroMaske) and e._spiegel_aktiv():
                return e
        return None

    # ---- Element API -------------------------------------------
    def bbox(self):
        xs, ys = [], []
        for el in self.elemente:
            if isinstance(el, AttributDefinition) and not el.sichtbar:
                continue
            b = el.bbox()
            for (lx, ly) in ((b[0], b[1]), (b[2], b[1]),
                             (b[2], b[3]), (b[0], b[3])):
                wx, wy = self._welt_pts(-lx if self.gespiegelt else lx, ly)
                xs.append(wx); ys.append(wy)
        if not xs:
            return (self.x, self.y, self.x, self.y)
        return (min(xs), min(ys), max(xs), max(ys))

    def verschieben(self, dx, dy):
        self.x += dx; self.y += dy

    def drehen(self, cx, cy, winkel_deg):
        self.x, self.y = punkte_drehen(self.x, self.y, cx, cy, winkel_deg)
        self.winkel = (self.winkel - winkel_deg) % 360.0

    def griffe(self):
        g = [("p", self.x, self.y)]
        m = self._maske_welt()
        if m is not None:
            ox, oy = m.spiegel_ursprung()
            g.append(("sp", ox, oy))
        self.aufgeloest()                  # fills the automatic text positions
        for key, (ax, ay) in self._anker.items():
            dx, dy = self.text_versatz.get(key, (0.0, 0.0))
            g.append(("t:" + key, ax + dx, ay + dy))
        return g

    def texte_zuruecksetzen(self):
        self.text_versatz = {}

    def griff_bewegen(self, griff_id, x, y):
        if griff_id.startswith("t:"):
            self.aufgeloest()
            a = self._anker.get(griff_id[2:])
            if a is not None:
                self.text_versatz[griff_id[2:]] = [x - a[0], y - a[1]]
            return
        if griff_id == "sp":
            m = self._maske_welt()
            if m is not None:
                bx, by = m.spiegel_ursprung(False)
                self.sp_dx, self.sp_dy = x - bx, y - by
            return
        self.x, self.y = x, y

    def to_dict(self):
        d = super().to_dict()
        d.pop("_cache", None)
        d.pop("refs", None)
        d.pop("kontakte", None)
        d.pop("_anker", None)
        d["text_versatz"] = {k: list(v) for k, v in self.text_versatz.items()}
        d["ausgeblendet"] = sorted(self.ausgeblendet)
        # Store children as dicts (not the objects themselves)
        d["elemente"] = [e.to_dict() for e in self.elemente]
        return d


# ============================================================
# NEW: global block library (blocks.json)
# ============================================================
class BlockBibliothek:
    """Block library shared across drawings.

    Stores block definitions in a user-specific JSON file (analogous to
    katiecad/common/config.py). Existing blocks are loaded at start-up;
    on changes the file is updated immediately.
    """

    DATEI = "blocks.json"

    def __init__(self, element_factory):
        self._element_factory = element_factory
        self._definitionen = {}
        self._laden()

    # ---- Path (platform-appropriate, same logic as katiecad.common.config) ----
    @staticmethod
    def _verzeichnis():
        import os, sys
        if sys.platform.startswith("win"):
            basis = os.environ.get("APPDATA") or os.path.expanduser("~")
            return os.path.join(basis, "KatieCAD")
        if sys.platform == "darwin":
            return os.path.expanduser("~/Library/Application Support/KatieCAD")
        basis = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return os.path.join(basis, "KatieCAD")

    @classmethod
    def pfad(cls):
        import os
        return os.path.join(cls._verzeichnis(), cls.DATEI)

    # ---- I/O ---------------------------------------------------
    def _laden(self):
        import json, os
        pfad = self.pfad()
        try:
            with open(pfad, "r", encoding="utf-8") as f:
                daten = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(daten, list):
            return
        for dd in daten:
            try:
                d = BlockDefinition.from_dict(dd, self._element_factory)
                self._definitionen[d.name] = d
            except Exception as e:
                print(f"[KatieCAD] Block konnte nicht geladen werden: {e}")

    def _speichern(self):
        import json, os
        pfad = self.pfad()
        try:
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            daten = [d.to_dict() for d in self._definitionen.values()]
            tmp = pfad + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(daten, f, indent=2, ensure_ascii=False)
            os.replace(tmp, pfad)
        except OSError as e:
            print(f"[KatieCAD] Blockbibliothek konnte nicht gespeichert werden: {e}")

    # ---- API ---------------------------------------------------
    def namen(self):
        return sorted(self._definitionen.keys())

    def __contains__(self, name):
        return name in self._definitionen

    def __len__(self):
        return len(self._definitionen)

    def get(self, name):
        return self._definitionen.get(name)

    def setze(self, definition, persistieren=True):
        self._definitionen[definition.name] = definition
        if persistieren:
            self._speichern()

    def loesche(self, name):
        if name in self._definitionen:
            del self._definitionen[name]
            self._speichern()
            return True
        return False


class Schraffur(Element):
    """Hatching over a closed contour.

    IMPORTANT: the element type (self.typ) stays "schraffur" so that
    save/load/copy/undo (_dict_zu_element) recognise the element. The fill
    pattern is stored in self.muster ("solid"/"linien").
    The parameter `typ="solid"|"linien"` is still accepted as an alias for
    compatibility reasons (old import code, old files).
    """
    MUSTER = ("solid", "linien")

    def __init__(self, punkte, muster="solid", winkel=45.0, abstand=5.0,
                 typ=None, **kw):
        super().__init__("schraffur", **kw)
        if typ in self.MUSTER:          # Alias / legacy format
            muster = typ
        self.punkte = [tuple(p) for p in punkte]
        self.muster = muster if muster in self.MUSTER else "solid"
        self.winkel = winkel
        self.abstand = abstand

    def bbox(self):
        if not self.punkte:
            return (0, 0, 0, 0)
        xs = [p[0] for p in self.punkte]
        ys = [p[1] for p in self.punkte]
        return (min(xs), min(ys), max(xs), max(ys))

    def verschieben(self, dx, dy):
        self.punkte = [(x + dx, y + dy) for (x, y) in self.punkte]

    def drehen(self, cx, cy, winkel_deg):
        self.punkte = [punkte_drehen(x, y, cx, cy, winkel_deg) for (x, y) in self.punkte]
        self.winkel = (self.winkel - winkel_deg) % 360.0

    def griffe(self):
        return [(f"p{i}", x, y) for i, (x, y) in enumerate(self.punkte)]

    def griff_bewegen(self, griff_id, x, y):
        if not griff_id.startswith("p"): return
        try:
            idx = int(griff_id[1:])
            if 0 <= idx < len(self.punkte):
                self.punkte[idx] = (x, y)
        except ValueError:
            pass

    def geometrie_linien(self):
        """Computes the intersection points for the line hatching (scan line)."""
        if self.muster != "linien" or len(self.punkte) < 3:
            return []
        abstand = max(float(self.abstand or 0), 0.05)   # Avoid an endless loop

        # The scan lines run horizontally in the rotated system. Forward rotation
        # by -angle, back-rotation by +angle => line direction (cos w, sin w),
        # i.e. 45 degrees points up-right ("/") with y up.
        rad = math.radians(self.winkel)
        ca, sa = math.cos(rad), math.sin(rad)
        rot_pts = [(x * ca + y * sa, -x * sa + y * ca) for (x, y) in self.punkte]
        min_y = min(p[1] for p in rot_pts)
        max_y = max(p[1] for p in rot_pts)
        if (max_y - min_y) / abstand > 20000:           # absurdly dense hatching
            return []

        rad_back = math.radians(-self.winkel)
        cb, sb = math.cos(rad_back), math.sin(rad_back)
        linien = []
        # half the spacing as start: lines do not lie exactly on corner points
        y = min_y + abstand / 2.0 if (max_y - min_y) > abstand else min_y
        while y <= max_y:
            schnitte = []
            for i in range(len(rot_pts)):
                p1 = rot_pts[i]
                p2 = rot_pts[(i + 1) % len(rot_pts)]
                if (p1[1] <= y < p2[1]) or (p2[1] <= y < p1[1]):
                    t = (y - p1[1]) / (p2[1] - p1[1])
                    schnitte.append(p1[0] + t * (p2[0] - p1[0]))
            schnitte.sort()
            for i in range(0, len(schnitte) - 1, 2):
                x1, x2 = schnitte[i], schnitte[i + 1]
                linien.append(((x1 * cb + y * sb, -x1 * sb + y * cb),
                               (x2 * cb + y * sb, -x2 * sb + y * cb)))
            y += abstand
        return linien


# ------------------------------------------------------------
# Contour detection for hatchings
# ------------------------------------------------------------
def _kreis_polygon(cx, cy, r, n=None):
    if n is None:
        n = int(max(48, min(360, r * 4)))
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def bereich_an_punkt(elemente, punkt, tol=0.05):
    """Finds the smallest closed region around `punkt` that is bounded by
    lines, arcs, circles, rectangles and polylines (they may cross each
    other, like AutoCAD's "pick internal point").
    Returns (points, source element) or None."""
    segs = []                                     # (a, b, source)

    def kette(pts, quelle, zu=False):
        pts = list(pts)
        for i in range(len(pts) - 1):
            segs.append((pts[i], pts[i + 1], quelle))
        if zu and len(pts) > 2:
            segs.append((pts[-1], pts[0], quelle))

    for el in elemente:
        if isinstance(el, Kreis):
            kette(_kreis_polygon(el.cx, el.cy, el.r), el, True)
        elif isinstance(el, Rechteck):
            kette([(el.x1, el.y1), (el.x2, el.y1), (el.x2, el.y2),
                   (el.x1, el.y2)], el, True)
        elif isinstance(el, Polylinie):
            kette(el.punkte, el, bool(el.geschlossen))
        elif isinstance(el, Linie):
            kette([(el.x1, el.y1), (el.x2, el.y2)], el)
        elif isinstance(el, Bogen):
            sw = bogen_sweep(el.start, el.ende)
            n = int(max(8, min(360, sw / 3.0)))
            kette(bogen_punkte(el.cx, el.cy, el.r, el.start, el.ende, n), el)
    segs = [sg for sg in segs
            if math.hypot(sg[1][0] - sg[0][0], sg[1][1] - sg[0][1]) > 1e-9]
    if not segs or len(segs) > 4000:
        return None

    # split every segment at crossings / T-junctions
    schnitt = [[0.0, 1.0] for _ in segs]
    bb = [(min(a[0], b[0]) - tol, min(a[1], b[1]) - tol,
           max(a[0], b[0]) + tol, max(a[1], b[1]) + tol) for a, b, _ in segs]
    for i in range(len(segs)):
        a, b, _ = segs[i]
        rx, ry = b[0] - a[0], b[1] - a[1]
        li = math.hypot(rx, ry)
        for j in range(len(segs)):
            if i == j:
                continue
            if (bb[i][2] < bb[j][0] or bb[j][2] < bb[i][0]
                    or bb[i][3] < bb[j][1] or bb[j][3] < bb[i][1]):
                continue
            c, d, _ = segs[j]
            sx, sy = d[0] - c[0], d[1] - c[1]
            den = rx * sy - ry * sx
            if abs(den) > 1e-12:
                t = ((c[0] - a[0]) * sy - (c[1] - a[1]) * sx) / den
                u = ((c[0] - a[0]) * ry - (c[1] - a[1]) * rx) / den
                lj = math.hypot(sx, sy)
                if -tol / li <= t <= 1 + tol / li and -tol / lj <= u <= 1 + tol / lj:
                    schnitt[i].append(min(1.0, max(0.0, t)))
            else:                                  # collinear touching ends
                for q in (c, d):
                    t = ((q[0] - a[0]) * rx + (q[1] - a[1]) * ry) / (li * li)
                    dist = abs((q[0] - a[0]) * ry - (q[1] - a[1]) * rx) / li
                    if 0.0 < t < 1.0 and dist <= tol:
                        schnitt[i].append(t)

    knoten = {}
    koords = []

    def nid(pt):
        k = (round(pt[0] / tol), round(pt[1] / tol))
        for dx in (0, -1, 1):
            for dy in (0, -1, 1):
                v = knoten.get((k[0] + dx, k[1] + dy))
                if v is not None:
                    return v
        knoten[k] = len(koords)
        koords.append(pt)
        return knoten[k]

    kanten = {}                                    # (u, v) -> source
    for (a, b, q), ts in zip(segs, schnitt):
        ts = sorted(set(ts))
        ids = [nid((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
               for t in ts]
        for u, v in zip(ids, ids[1:]):
            if u != v:
                kanten[(u, v)] = q
                kanten[(v, u)] = q
    nachbarn = {}
    for (u, v) in kanten:
        nachbarn.setdefault(u, []).append(v)

    def winkel(u, v):
        return math.atan2(koords[v][1] - koords[u][1], koords[v][0] - koords[u][0])

    for u in nachbarn:
        nachbarn[u].sort(key=lambda v, u=u: winkel(u, v))

    px, py = punkt
    treffer = []
    for (u, v) in kanten:
        if u > v:
            continue
        (x1, y1), (x2, y2) = koords[u], koords[v]
        if (y1 > py) == (y2 > py):
            continue
        x = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
        if x > px:
            treffer.append((x, u, v))
    treffer.sort()
    for _, u, v in treffer:
        a, b = koords[u], koords[v]
        if (b[0] - a[0]) * (py - a[1]) - (b[1] - a[1]) * (px - a[0]) < 0:
            u, v = v, u                            # point on the left
        start = (u, v)
        kante = start
        schleife = []
        ok = False
        for _ in range(len(kanten) + 2):
            schleife.append(kante[0])
            x, y = kante
            nb = nachbarn[y]
            nxt = nb[(nb.index(x) - 1) % len(nb)]   # next edge clockwise
            kante = (y, nxt)
            if kante == start:
                ok = True
                break
        if not ok:
            continue
        pts = [koords[k] for k in schleife]
        if len(pts) < 3:
            continue
        flaeche = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            flaeche += x1 * y2 - x2 * y1
        if flaeche <= 0:
            continue                               # outer boundary of an island
        inside = False
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
        if inside:
            return pts, kanten[(schleife[0], schleife[1])]
    return None


def konturen_aus_elementen(elemente, tol=0.05):
    """Finds closed contours in an element list.

    Returns: list of (points, source_elements).
      - circle, rectangle, closed polyline -> one contour each
      - line, arc, open polyline           -> joined into chains at their
        end points (distance <= tol); only chains that close yield a
        contour.
    """
    ergebnis = []
    offene = []                                   # (points, source)
    for el in elemente:
        if isinstance(el, Kreis):
            ergebnis.append((_kreis_polygon(el.cx, el.cy, el.r), [el]))
        elif isinstance(el, Rechteck):
            ergebnis.append(([(el.x1, el.y1), (el.x2, el.y1),
                              (el.x2, el.y2), (el.x1, el.y2)], [el]))
        elif isinstance(el, Polylinie):
            if el.geschlossen and len(el.punkte) >= 3:
                ergebnis.append((list(el.punkte), [el]))
            elif len(el.punkte) >= 2:
                offene.append((list(el.punkte), el))
        elif isinstance(el, Linie):
            offene.append(([(el.x1, el.y1), (el.x2, el.y2)], el))
        elif isinstance(el, Bogen):
            sw = bogen_sweep(el.start, el.ende)
            n = int(max(8, min(360, sw / 3.0)))
            offene.append((bogen_punkte(el.cx, el.cy, el.r, el.start, el.ende, n), el))

    def nah(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

    rest = list(offene)
    while rest:
        pts, quelle = rest.pop(0)
        pts = list(pts)
        quellen = [quelle]
        erweitert = True
        while erweitert:
            erweitert = False
            if len(pts) > 2 and nah(pts[0], pts[-1]):
                break
            for i, (p2, q2) in enumerate(rest):
                if nah(pts[-1], p2[0]):
                    pts += p2[1:]
                elif nah(pts[-1], p2[-1]):
                    pts += list(reversed(p2))[1:]
                elif nah(pts[0], p2[-1]):
                    pts = p2[:-1] + pts
                elif nah(pts[0], p2[0]):
                    pts = list(reversed(p2))[:-1] + pts
                else:
                    continue
                quellen.append(q2)
                rest.pop(i)
                erweitert = True
                break
        if len(pts) > 3 and nah(pts[0], pts[-1]):
            ergebnis.append((pts[:-1], quellen))
    return ergebnis


# ============================================================
# Layout (a drawing sheet with its own format, background
# and its own layout elements - analogous to AutoCAD layouts)
# ============================================================
class Layout:
    STANDARD_FORMAT = "A3 (420x297)"
    STANDARD_BG = "#1c132d"

    def __init__(self, name="Layout1", format=None, bg=None,
                 elemente=None, view=None):
        self.name = name
        self.format = format or self.STANDARD_FORMAT
        self.bg = bg or self.STANDARD_BG
        self.elemente = list(elemente) if elemente else []
        self.view = dict(view) if view else {"zoom": 1.5, "ox": 150, "oy": 700}

    def to_dict(self):
        return {
            "name": self.name,
            "format": self.format,
            "bg": self.bg,
            "elemente": [e.to_dict() for e in self.elemente],
            "view": dict(self.view),
        }

    @classmethod
    def from_dict(cls, d, element_factory):
        lay = cls(
            name=d.get("name", "Layout1"),
            format=d.get("format", cls.STANDARD_FORMAT),
            bg=d.get("bg", cls.STANDARD_BG),
            view=d.get("view"),
        )
        for ed in d.get("elemente", []):
            el = element_factory(ed)
            if el is not None:
                if isinstance(el, Viewport):
                    el.aktiv = False
                lay.elemente.append(el)
        return lay



# ============================================================
# NEW (electrical): wire, connection point, cross reference
# ============================================================
LEITUNG_FARBE = "#ff0000"
# ASSUMPTION: 0.35 mm (default line width). The wish was "3.5" - that would be a
# 3.5 mm wide line. Change centrally here if really intended.
LEITUNG_STAERKE = 0.35


class Leitung(Linie):
    """Red connecting line between two connection points.
    auto=True: is created/removed automatically (see
    katiecad.electrical.logic.leitungen_automatisch)."""

    def __init__(self, x1, y1, x2, y2, auto=False, **kw):
        kw.setdefault("farbe", LEITUNG_FARBE)
        kw.setdefault("eig_farbe", True)
        kw.setdefault("staerke", LEITUNG_STAERKE)
        super().__init__(x1, y1, x2, y2, **kw)
        self.typ = "leitung"
        self.auto = bool(auto)


class Verbindungspunkt(AttributDefinition):
    """Connection point: circle (diameter 1 mm) + label to its right
    (text height 2.0 mm).

    The circle is drawn only in the model; layout and PDF show only the
    label. In blocks it behaves like an attribute: the text
    (self.wert) is editable per block instance.
    """
    DURCHMESSER = 1.0
    TEXT_HOEHE = 2.0
    TEXT_ABSTAND = 1.0          # Distance circle edge -> text (mm)

    def __init__(self, x, y, inhalt=None, hoehe=2.0, winkel=0.0,
                 schriftart="Arial", einfuegepunkt=None, tag="VP",
                 prompt="", wert="", sichtbar=True, radius=0.5,
                 richtungen=None, text_dx=0.0, text_dy=0.0, **kw):
        super().__init__(x, y, inhalt, hoehe, winkel, schriftart,
                         "mitte_links", tag=tag, prompt=prompt, wert=wert,
                         sichtbar=sichtbar, **kw)
        self.typ = "vpunkt"
        self.text_dx, self.text_dy = float(text_dx), float(text_dy)  # label offset
        # Active connection directions (0 east, 90 north, 180 west, 270 south).
        # None = not set (older files): free -> all, in the device
        # -> nearest outer edge of the symbol.
        self.richtungen = (None if richtungen is None else
                           sorted({int(round(float(r) / 90.0)) * 90 % 360
                                   for r in richtungen}))
        self.radius = float(radius)
        self.wert = "" if wert is None else str(wert)
        self.inhalt = self.wert

    def drehen(self, cx, cy, winkel_deg):
        super().drehen(cx, cy, winkel_deg)
        if self.richtungen is not None:
            self.richtungen = sorted({int(round((r - winkel_deg) / 90.0)) * 90 % 360
                                      for r in self.richtungen})

    def text_anker(self):
        """Automatic position of the label (without the user offset)."""
        a = math.radians(self.winkel)
        d = self.radius + self.TEXT_ABSTAND
        return (self.x + d * math.cos(a), self.y + d * math.sin(a))

    def griffe(self):
        g = super().griffe()
        if self.sichtbar and self.wert != "":
            ax, ay = self.text_anker()
            g.append(("t", ax + self.text_dx, ay + self.text_dy))
        return g

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "t":
            ax, ay = self.text_anker()
            self.text_dx, self.text_dy = x - ax, y - ay
        else:
            super().griff_bewegen(griff_id, x, y)

    def texte_zuruecksetzen(self):
        self.text_dx = self.text_dy = 0.0

    def text_element(self):
        """Label as a normal text element (or None)."""
        if not self.sichtbar or self.wert == "":
            return None
        ax, ay = self.text_anker()
        return Text(ax + self.text_dx, ay + self.text_dy,
                    self.wert, self.hoehe, self.winkel, self.schriftart,
                    einfuegepunkt="mitte_links", layer=self.layer,
                    farbe=self.farbe, linientyp=self.linientyp,
                    eig_farbe=self.eig_farbe, staerke=self.staerke)

    def rahmen(self):
        t = self.text_element()
        if t is not None:
            return t.rahmen()
        r = max(self.radius, 0.5)
        return [(self.x - r, self.y - r), (self.x + r, self.y - r),
                (self.x + r, self.y + r), (self.x - r, self.y + r)]

    def bbox(self):
        pts = list(self.rahmen())
        r = self.radius
        pts += [(self.x - r, self.y - r), (self.x + r, self.y + r)]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def trifft(self, x, y, tol):
        """Hit on the circle or the label."""
        if math.hypot(x - self.x, y - self.y) <= max(self.radius, tol):
            return True
        t = self.text_element()
        return bool(t and t.punkt_im_rahmen(x, y, tol))


def vp_tags_eindeutig(elemente):
    """Assigns unique tags (VP1, VP2, ...) to all connection points of a block
    definition so that each has its own value per instance."""
    belegt = {e.tag for e in elemente
              if isinstance(e, AttributDefinition)
              and not isinstance(e, Verbindungspunkt)}
    n = 1
    for e in elemente:
        if isinstance(e, Verbindungspunkt):
            while f"VP{n}" in belegt:
                n += 1
            e.tag = f"VP{n}"
            e.prompt = f"{tr('vp.prompt')} {n}"
            belegt.add(e.tag)
            n += 1


class Querverweis(Element):
    """Arrow symbol for references between schematic sheets.

    Arrow 2 x 5 mm, insertion point = centre of the arrow base.
    richtung: 0 = east, 90 = north, 180 = west, 270 = south (arrow tip).
    art:      "abgehend"  -> text behind the arrow tip
              "ankommend" -> text behind the arrow base
    text:     editable identifier (e.g. "L1")
    ziel:     (not saved) sheet numbers of the counterparts with the same
              text; computed by the application.
    """
    ARTEN = ("abgehend", "ankommend")
    BREITE = 2.0
    LAENGE = 5.0
    ABSTAND = 1.0
    TEXT_HOEHE = 2.5            # Identifier (default height)
    ZIEL_HOEHE = 1.5            # Target specification (default height)
    _VEKTOR = {0: (1.0, 0.0), 90: (0.0, 1.0), 180: (-1.0, 0.0), 270: (0.0, -1.0)}

    def __init__(self, x, y, text="", art="abgehend", richtung=0,
                 extern=False, text_hoehe=None, ziel_hoehe=None,
                 text_dx=0.0, text_dy=0.0, ziel_dx=0.0, ziel_dy=0.0, **kw):
        kw.setdefault("eig_farbe", True)
        super().__init__("querverweis", **kw)
        self.x, self.y = x, y
        self.extern = bool(extern)     # handover/external: no counterpart needed
        self.text = str(text or "")
        self.art = art if art in self.ARTEN else "abgehend"
        self.richtung = int(round(float(richtung) / 90.0) * 90) % 360
        self.ziel = []
        # Optional own text heights (None = default) and text offsets (mm,
        # relative to the automatic position)
        self.text_hoehe = float(text_hoehe) if text_hoehe else None
        self.ziel_hoehe = float(ziel_hoehe) if ziel_hoehe else None
        self.text_dx, self.text_dy = float(text_dx), float(text_dy)
        self.ziel_dx, self.ziel_dy = float(ziel_dx), float(ziel_dy)

    def to_dict(self):
        d = super().to_dict()
        d.pop("ziel", None)
        return d

    def hoehe_text(self):
        return self.text_hoehe or self.TEXT_HOEHE

    def hoehe_ziel(self):
        return self.ziel_hoehe or self.ZIEL_HOEHE

    def texte_zuruecksetzen(self):
        self.text_dx = self.text_dy = self.ziel_dx = self.ziel_dy = 0.0

    def ziel_text(self):
        if not self.ziel or not self.text.strip():
            return ""
        return "(" + tr("qv.blatt") + " " + ", ".join(ort_text(o) for o in self.ziel) + ")"

    def basis_punkt(self):
        """Connection at the arrow base (= insertion point)."""
        return (self.x, self.y)

    def spitze_punkt(self):
        """Connection at the arrow tip."""
        dx, dy = self._VEKTOR[self.richtung]
        return (self.x + dx * self.LAENGE, self.y + dy * self.LAENGE)

    def pfeil_punkte(self):
        dx, dy = self._VEKTOR[self.richtung]
        nx, ny = -dy, dx
        h = self.BREITE / 2.0
        return [(self.x + nx * h, self.y + ny * h),
                (self.x - nx * h, self.y - ny * h),
                (self.x + dx * self.LAENGE, self.y + dy * self.LAENGE)]

    GAP = 1.0                   # Distance identifier <-> target note (same line)

    def _text_lage(self):
        """-> (angle, anchor key, (tx, ty), (zx, zy)): automatic positions of
        identifier and target text (without the user offsets). Both texts
        stand on ONE line: 'L1 (Sheet 6/1/D)'; the target note follows the
        identifier in reading direction."""
        dx, dy = self._VEKTOR[self.richtung]
        a = 0.0 if self.richtung in (0, 180) else 90.0
        ex, ey = math.cos(math.radians(a)), math.sin(math.radians(a))
        if self.art == "abgehend":
            sx, sy = dx, dy
            qx = self.x + dx * (self.LAENGE + self.ABSTAND)
            qy = self.y + dy * (self.LAENGE + self.ABSTAND)
        else:
            sx, sy = -dx, -dy
            qx = self.x - dx * self.ABSTAND
            qy = self.y - dy * self.ABSTAND
        links = (ex * sx + ey * sy) > 0
        ziel = self.ziel_text()
        tx, ty, zx, zy = qx, qy, qx, qy
        if ziel and self.text.strip():
            wi = pdf_textbreite(self.text, self.hoehe_text() / CAD_VERSALHOEHE)
            wz = pdf_textbreite(ziel, self.hoehe_ziel() / CAD_VERSALHOEHE)
            if links:                          # text runs away from the arrow
                zx, zy = qx + ex * (wi + self.GAP), qy + ey * (wi + self.GAP)
            else:                              # text ends at the arrow:
                # identifier next to the arrow, target note further away
                zx, zy = qx - ex * (wi + self.GAP), qy - ey * (wi + self.GAP)
        return (a, "mitte_" + ("links" if links else "rechts"),
                (tx, ty), (zx, zy))

    def aufgeloest(self):
        """Arrow (solid hatching) + text(s) as simple elements."""
        out = [Schraffur(self.pfeil_punkte(), "solid", layer=self.layer,
                         farbe=LEITUNG_FARBE, eig_farbe=True)]
        a, anker, (tx, ty), (zx, zy) = self._text_lage()
        ziel = self.ziel_text()
        stil = dict(layer=self.layer, farbe=self.farbe,
                    linientyp=self.linientyp, eig_farbe=self.eig_farbe)
        if self.text.strip():
            out.append(Text(tx + self.text_dx, ty + self.text_dy, self.text,
                            self.hoehe_text(), a, "Arial",
                            einfuegepunkt=anker, **stil))
        if ziel:
            out.append(Text(zx + self.ziel_dx, zy + self.ziel_dy, ziel,
                            self.hoehe_ziel(), a, "Arial",
                            einfuegepunkt=anker, **stil))
        return out

    def bbox(self):
        xs, ys = [], []
        for k in self.aufgeloest():
            b = k.bbox()
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
        return (min(xs), min(ys), max(xs), max(ys))

    def verschieben(self, dx, dy):
        self.x += dx
        self.y += dy

    def drehen(self, cx, cy, winkel_deg):
        self.x, self.y = punkte_drehen(self.x, self.y, cx, cy, winkel_deg)
        self.richtung = int(round((self.richtung - winkel_deg) / 90.0) * 90) % 360
        for k in ("text", "ziel"):             # offsets turn with the symbol
            ox, oy = punkte_drehen(getattr(self, k + "_dx"), getattr(self, k + "_dy"),
                                   0.0, 0.0, winkel_deg)
            setattr(self, k + "_dx", ox)
            setattr(self, k + "_dy", oy)

    def griffe(self):
        _, _, (tx, ty), (zx, zy) = self._text_lage()
        g = [("p", self.x, self.y)]
        if self.text.strip():
            g.append(("t", tx + self.text_dx, ty + self.text_dy))
        if self.ziel_text():
            g.append(("z", zx + self.ziel_dx, zy + self.ziel_dy))
        return g

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p":
            self.x, self.y = x, y
        elif griff_id in ("t", "z"):
            _, _, (tx, ty), (zx, zy) = self._text_lage()
            bx, by = (tx, ty) if griff_id == "t" else (zx, zy)
            k = "text" if griff_id == "t" else "ziel"
            setattr(self, k + "_dx", x - bx)
            setattr(self, k + "_dy", y - by)



# ============================================================
# NEW (electrical): junction, electrical mask, terminal
# ============================================================
class Verbindung(Element):
    """Wire junction (red, firmly belongs to the wire).

    The junction is described by the set of directions in which an arm
    leaves the centre (``arme``: any subset of 0/90/180/270 degrees with
    at least two entries; 0 = east, 90 = north, ...) and a dot flag.
      2 arms: corner or straight piece
      3 arms: T-piece, in any direction, with or without dot
      4 arms: crossing; with dot = connected, without dot = the wires
              only cross (opposite arms are connected)
    The arm ends are the connection points for wires.

    Legacy files (keys art / ausrichtung / punkt) are converted on load:
      art 2: arms at a*90 and a*90+90
      art 3: arms at a*90, a*90+90 and a*90+180
      art 4: all four arms; the dot only counted for art 4."""
    ARM = 2.5
    PUNKT_RADIUS = 1.25
    RICHTUNGEN = (0, 90, 180, 270)

    def __init__(self, x, y, art=None, ausrichtung=0, punkt=True,
                 arme=None, **kw):
        kw.setdefault("farbe", LEITUNG_FARBE)
        kw.setdefault("eig_farbe", True)
        kw.setdefault("staerke", LEITUNG_STAERKE)
        super().__init__("verbindung", **kw)
        self.x, self.y = float(x), float(y)
        if arme is None:                       # legacy description
            art = int(art) if art in (2, 3, 4) else 2
            a = int(ausrichtung) % 4
            arme = ([a * 90, a * 90 + 90] if art == 2 else
                    [a * 90, a * 90 + 90, a * 90 + 180] if art == 3 else
                    [0, 90, 180, 270])
            punkt = bool(punkt) and art == 4
            if art != 4:
                a = 0
            ausrichtung = a
        self.arme = self.arme_normieren(arme)
        self.punkt = bool(punkt)
        # Only used by the 4-arm crossing WITHOUT dot: the kinked arm
        # points to  ausrichtung*90 + 180  (as before).
        self.ausrichtung = int(ausrichtung) % 4

    @classmethod
    def arme_normieren(cls, arme):
        """Sorted, valid, unique directions; falls back to a corner."""
        out = sorted({int(round(float(r) / 90.0)) * 90 % 360 for r in arme})
        return out if len(out) >= 2 else [0, 90]

    @property
    def art(self):
        """Number of connections (2, 3 or 4)."""
        return len(self.arme)

    def _welt(self, px, py):
        return (self.x + px, self.y + py)

    def arme_enden(self):
        u = self.ARM
        return [(u * math.cos(math.radians(d)), u * math.sin(math.radians(d)), d)
                for d in self.arme]

    def anschluesse(self):
        """Arm ends (x, y, direction)."""
        out = []
        for (px, py, d) in self.arme_enden():
            wx, wy = self._welt(round(px, 9), round(py, 9))
            out.append((wx, wy, d))
        return out

    def _zuege(self):
        """Polylines in world coordinates, as in Eplan.
        With dot: plain straight arms.  Without dot:
          2 arms: corner / straight piece
          3 arms: T-piece - the arm opposite the missing direction is the
                  stem; of the two side arms one is straight and one runs
                  with a kink (45 degrees) onto the stem
          4 arms: crossing - through-line + straight arm + kinked arm"""
        u = self.ARM
        c = (self.x, self.y)

        def vec(d, f=1.0):
            r = math.radians(d)
            return (round(self.x + f * u * math.cos(r), 9),
                    round(self.y + f * u * math.sin(r), 9))

        arme = self.arme
        if len(arme) == 2:
            return [[vec(arme[0]), c, vec(arme[1])]]
        if self.punkt:
            return [[c, vec(d)] for d in arme]

        def kink(s):                 # kinked arm towards stem direction s
            k = (s + 90) % 360
            return [vec(k), vec(k, 0.5), vec(s, 0.5)]

        if len(arme) == 3:
            fehlt = [d for d in self.RICHTUNGEN if d not in arme][0]
            s = (fehlt + 180) % 360
            return [[c, vec((s - 90) % 360)], [c, vec(s)], kink(s)]
        s = (self.ausrichtung * 90 + 180 - 90) % 360
        return [[c, vec((s - 90) % 360)], [vec(s), vec((s + 180) % 360)], kink(s)]

    def aufgeloest(self):
        st = dict(layer=self.layer, farbe=self.farbe,
                  linientyp=self.linientyp, eig_farbe=self.eig_farbe,
                  staerke=self.staerke)
        out = []
        for zug in self._zuege():
            for a, b in zip(zug, zug[1:]):
                out.append(Linie(a[0], a[1], b[0], b[1], **st))
        if self.punkt and len(self.arme) >= 3:
            r = self.PUNKT_RADIUS
            pts = [(self.x + r * math.cos(2 * math.pi * i / 16),
                    self.y + r * math.sin(2 * math.pi * i / 16)) for i in range(16)]
            out.append(Schraffur(pts, "solid", layer=self.layer,
                                 farbe=self.farbe, eig_farbe=True))
        return out

    def bbox(self):
        xs = [self.x] + [a[0] for a in self.anschluesse()]
        ys = [self.y] + [a[1] for a in self.anschluesse()]
        return (min(xs), min(ys), max(xs), max(ys))

    def verschieben(self, dx, dy):
        self.x += dx
        self.y += dy

    def drehen(self, cx, cy, winkel_deg):
        self.x, self.y = punkte_drehen(self.x, self.y, cx, cy, winkel_deg)
        self.arme = self.arme_normieren(
            [d - winkel_deg for d in self.arme])
        self.ausrichtung = (self.ausrichtung + int(round(-winkel_deg / 90.0))) % 4

    def griffe(self):
        return [("p", self.x, self.y)]

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p":
            self.x, self.y = x, y


class _FestMaske(Element):
    """Base for elements with FIXED text fields (fill-in only, structure
    cannot be changed): electrical mask and terminal."""
    FELDER = ()
    ZEILEN = ()            # (tag, dx, dy, height, anchor)

    def __init__(self, typ, x, y, werte=None, ausgeblendet=None,
                 platzhalter=True, versatz=None, **kw):
        super().__init__(typ, **kw)
        self.x, self.y = float(x), float(y)
        # Free text positions: {TAG: [dx, dy]} relative to the automatic position
        self.versatz = {str(k): [float(v[0]), float(v[1])]
                        for k, v in (versatz or {}).items()}
        self._anker = {}              # automatic text positions (computed)
        self.werte = {t: "" for t in self.FELDER}
        for t, v in (werte or {}).items():
            if t in self.FELDER:
                self.werte[t] = "" if v is None else str(v)
        self.ausgeblendet = {t for t in (ausgeblendet or []) if t in self.FELDER}
        self.platzhalter = bool(platzhalter)     # show empty fields as <TAG>
        self.refs = []                           # Sheet numbers (computed)

    def to_dict(self):
        d = super().to_dict()
        d.pop("refs", None)
        d.pop("kontakte", None)         # computed, never saved
        d.pop("sym_bbox", None)
        d.pop("_anker", None)
        d["werte"] = dict(self.werte)
        d["ausgeblendet"] = sorted(self.ausgeblendet)
        d["versatz"] = {k: list(v) for k, v in self.versatz.items()}
        return d

    def _t(self, tag, x, y, inhalt, hoehe, anker, st):
        """Text of the field `tag` at its automatic position (x, y) plus the
        user offset; the automatic position is remembered for the grip."""
        self._anker[tag] = (x, y)
        dx, dy = self.versatz.get(tag, (0.0, 0.0))
        return Text(x + dx, y + dy, inhalt, hoehe, 0.0, "Arial",
                    einfuegepunkt=anker, **st)

    def text_griffe(self, praefix="t:"):
        """Grips of the movable texts: [(id, x, y)] (after aufgeloest())."""
        out = []
        for tag, (ax, ay) in self._anker.items():
            dx, dy = self.versatz.get(tag, (0.0, 0.0))
            out.append((praefix + tag, ax + dx, ay + dy))
        return out

    def text_bewegen(self, tag, x, y):
        a = self._anker.get(tag)
        if a is not None:
            self.versatz[tag] = [x - a[0], y - a[1]]

    def texte_zuruecksetzen(self):
        self.versatz = {}

    def setze_werte(self, werte):
        for t, v in werte.items():
            if t in self.FELDER:
                self.werte[t] = str(v)

    def _stil(self):
        return dict(layer=self.layer, farbe=self.farbe,
                    linientyp=self.linientyp, eig_farbe=self.eig_farbe)

    def _zusatz(self, ph, st):
        return []

    def aufgeloest(self, platzhalter=None):
        ph = self.platzhalter if platzhalter is None else platzhalter
        st = self._stil()
        self._anker = {}
        out = []
        for tag, dx, dy, h, anker in self.ZEILEN:
            if tag in self.ausgeblendet:
                continue
            w = self.werte.get(tag, "")
            if w == "":
                if not ph:
                    continue
                w = "<" + tag + ">"
            out.append(self._t(tag, self.x + dx, self.y + dy, w, h, anker, st))
        out.extend(self._zusatz(ph, st))
        return out

    def bbox(self):
        xs, ys = [self.x], [self.y]
        for k in self.aufgeloest(True):
            b = k.bbox()
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
        return (min(xs), min(ys), max(xs), max(ys))

    def verschieben(self, dx, dy):
        self.x += dx
        self.y += dy

    def drehen(self, cx, cy, winkel_deg):
        self.x, self.y = punkte_drehen(self.x, self.y, cx, cy, winkel_deg)

    def griffe(self):
        self.aufgeloest(True)             # fills the text positions
        return [("p", self.x, self.y)] + self.text_griffe()

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p":
            self.x, self.y = x, y
        elif griff_id.startswith("t:"):
            self.aufgeloest(True)
            self.text_bewegen(griff_id[2:], x, y)


class ElektroMaske(_FestMaske):
    """Base for electrical devices: <IND> (2.5), <TYP>, <PER>, <REF> (1.5 each).

    The insertion point (x, y) is the LOWER RIGHT corner of the mask; all
    texts are right-aligned and grow upwards so that the mask can be
    'attached' to a symbol.  REF is at the very bottom and grows upwards
    with the number of references (the other lines move up with it).

    IND/TYP/PER are filled in. REF is created automatically: devices with
    the same PER refer to each other (main symbol -> all auxiliary parts,
    auxiliary part -> only the main symbol), see katiecad.electrical.logic."""
    FELDER = ("IND", "TYP", "PER")
    ROLLEN = ("haupt", "hilfs")
    SPIEGEL = ("liste", "rechts", "unten")      # reference list / contact mirror
    HOEHEN = {"IND": 2.5, "TYP": 1.5, "PER": 1.5}
    REF_HOEHE = 1.5
    ABSTAND = {"PER": 1.1, "TYP": 2.0, "IND": 3.0}   # centre to centre upwards
    ZEILEN = ()

    def __init__(self, x, y, werte=None, rolle="haupt", spiegel="liste",
                 sp_dx=0.0, sp_dy=0.0, **kw):
        super().__init__("maske", x, y, werte, **kw)
        self.rolle = rolle if rolle in self.ROLLEN else "haupt"
        self.spiegel = spiegel if spiegel in self.SPIEGEL else "liste"
        self.sp_dx, self.sp_dy = float(sp_dx), float(sp_dy)   # mirror offset
        self.kontakte = []        # (art, pins, ort) of the auxiliary parts (computed)
        self.sym_bbox = None      # bbox of the symbol (set by the block), computed

    def to_dict(self):
        d = super().to_dict()
        d.pop("kontakte", None)
        d.pop("sym_bbox", None)
        return d

    def _spiegel_aktiv(self):
        return (self.spiegel != "liste" and self.rolle == "haupt"
                and bool(self.kontakte))

    # ---- Contact mirror ------------------------------------------
    @staticmethod
    def _pin_rollen(art, pins):
        """Pin labels sorted by role. make/break: (top, bottom);
        changeover: (common, break, make)."""
        ps = [str(p).strip() for p in pins if str(p).strip()]
        if art == "wechsler":
            d = {p[-1]: p for p in ps if p[-1:].isdigit()}
            return (d.get("1", ""), d.get("2", ""), d.get("4", ""))
        ps = sorted(ps, key=lambda p: (p[-1:], p))
        return (ps[0] if ps else "", ps[1] if len(ps) > 1 else "")

    def spiegel_ursprung(self, mit_versatz=True):
        """Upper left corner of the mirror (default: beside / below the
        symbol, depending on the mode) plus the user offset."""
        bb = self.sym_bbox
        if bb is None:
            bb = (self.x, self.y, self.x, self.y)
        if self.spiegel == "rechts":
            ox, oy = bb[2] + 5.0, bb[3]
        else:
            ox, oy = (bb[0] + bb[2]) / 2.0 - 7.5, bb[1] - 6.0
        if mit_versatz:
            ox, oy = ox + self.sp_dx, oy + self.sp_dy
        return ox, oy

    def _txt(self, x, y, s, st, anker="unten_links"):
        return Text(x, y, s, 1.5, 0.0, "Arial", einfuegepunkt=anker, **st)

    def _kontakt_h(self, ox, oy, art, pins, ort, st):
        """Horizontal contact (below a relay). oy = upper edge of the row.
        -> (elements, row height)"""
        L = lambda x1, y1, x2, y2: Linie(x1, y1, x2, y2, staerke=0.35, **st)
        out = []
        r = self._pin_rollen(art, pins)
        if art == "wechsler":
            ys = oy - 4.5
            com, nc, no = r
            out += [L(ox, ys, ox + 5, ys), L(ox + 10, ys, ox + 15, ys),
                    L(ox, ys + 3, ox + 5, ys + 3), L(ox + 5, ys, ox + 5, ys + 2),
                    L(ox + 10, ys, ox + 4, ys + 2),
                    self._txt(ox, ys, nc, st), self._txt(ox + 10, ys, com, st),
                    self._txt(ox, ys + 3, no, st)]
            hoehe, ym = 4.5, ys + 1.5
        elif art in ("schliesser", "oeffner"):
            ys = oy - 2.0
            out += [L(ox, ys, ox + 5, ys), L(ox + 10, ys, ox + 15, ys),
                    self._txt(ox, ys, r[0], st), self._txt(ox + 10, ys, r[1], st)]
            if art == "schliesser":
                out.append(L(ox + 10, ys, ox + 5, ys - 2))
            else:
                out += [L(ox + 5, ys, ox + 5, ys + 2), L(ox + 10, ys, ox + 4, ys + 2)]
            hoehe, ym = 4.0, ys
        else:
            ys = oy - 2.0
            out.append(self._txt(ox, ys, "/".join(p for p in pins if p), st))
            hoehe, ym = 2.0, ys
        out.append(self._txt(ox + 17.0, ym - 0.7, "(" + ort_text(ort) + ")", st))
        return out, hoehe

    def _kontakt_v(self, ox, oy, art, pins, ort, st):
        """Vertical contact (beside the device). oy = upper edge.
        -> (elements, column width)"""
        L = lambda x1, y1, x2, y2: Linie(x1, y1, x2, y2, staerke=0.35, **st)
        out = []
        r = self._pin_rollen(art, pins)
        cx = ox + 4.0
        yt = oy - 2.5                  # top stem begins
        yb = yt - 15.0                 # bottom stem ends
        if art in ("schliesser", "oeffner", "wechsler"):
            out += [L(cx, yt, cx, yt - 5), L(cx, yt - 10, cx, yb)]
            if art == "schliesser":
                out.append(L(cx - 2.5, yt - 5, cx, yt - 10))
                out += [self._txt(cx + 0.8, yt + 0.55, r[0], st),
                        self._txt(cx + 0.8, yb - 2.0, r[1], st)]
                breite = 8.0
            else:
                out += [L(cx, yt - 5, cx + 3, yt - 5), L(cx + 2, yt - 4, cx, yt - 10)]
                if art == "oeffner":
                    out += [self._txt(cx + 0.8, yt + 0.55, r[0], st),
                            self._txt(cx + 0.8, yb - 2.0, r[1], st)]
                    breite = 9.0
                else:
                    com, nc, no = r
                    out += [L(cx + 5, yt, cx + 5, yt - 5),
                            self._txt(cx + 0.8, yt + 0.55, nc, st),
                            self._txt(cx + 5.8, yt + 0.55, no, st),
                            self._txt(cx + 0.8, yb - 2.0, com, st)]
                    breite = 14.0
        else:
            out.append(self._txt(cx + 0.8, yt, "/".join(p for p in pins if p), st))
            breite = 9.0
        out.append(self._txt(cx + 0.8, yb - 4.3, "(" + ort_text(ort) + ")", st))
        return out, max(breite, 10.0)

    def _spiegel_elemente(self, st):
        """Contact mirror: below the relay (horizontal contacts, one below
        the other) or beside the device (vertical contacts in a row)."""
        out = []
        ox, oy = self.spiegel_ursprung()
        if self.spiegel == "unten":
            for art, pins, ort in self.kontakte:
                el, h = self._kontakt_h(ox, oy, art, pins, ort, st)
                out.extend(el)
                oy -= h + 3.0
        else:
            for art, pins, ort in self.kontakte:
                el, b = self._kontakt_v(ox, oy, art, pins, ort, st)
                out.extend(el)
                ox += b + 3.0
        return out

    def griffe(self):
        g = _FestMaske.griffe(self)
        if self._spiegel_aktiv():
            ox, oy = self.spiegel_ursprung()
            g.append(("sp", ox, oy))
        return g

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "sp":
            bx, by = self.spiegel_ursprung(False)
            self.sp_dx, self.sp_dy = x - bx, y - by
        else:
            _FestMaske.griff_bewegen(self, griff_id, x, y)

    def aufgeloest(self, platzhalter=None):
        """Empty fields stay empty. Only on screen (platzhalter) a small cross
        appears as long as the mask has no text at all, so that it remains
        findable and selectable. REF appears only if there are references."""
        ph = self.platzhalter if platzhalter is None else platzhalter
        st = self._stil()
        self._anker = {}
        refs = ["(%s %s)" % (tr("qv.blatt"), ort_text(o)) for o in self.refs]
        ref = Text(self.x, self.y, "\n".join(refs) if refs else "REF",
                   self.REF_HOEHE, 0.0, "Arial",
                   einfuegepunkt="unten_rechts", **st)
        mirror = self._spiegel_aktiv()
        out = []
        if refs and not mirror:
            out.append(self._t("REF", self.x, self.y, ref.inhalt, self.REF_HOEHE,
                               "unten_rechts", st))
        if mirror:
            out.extend(self._spiegel_elemente(st))
        y = ref.bbox()[3]                # Top edge of the (reserved) REF line
        for tag in ("PER", "TYP", "IND"):
            y += self.ABSTAND[tag]       # Centre of the respective line
            w = self.werte.get(tag, "")
            if tag in self.ausgeblendet or w == "":
                continue
            out.append(self._t(tag, self.x, y, w, self.HOEHEN[tag],
                               "mitte_rechts", st))
        if not out and ph:
            r = 0.8
            out.append(Linie(self.x - r, self.y, self.x + r, self.y, staerke=0.25, **st))
            out.append(Linie(self.x, self.y - r, self.x, self.y + r, staerke=0.25, **st))
        return out


class Kabel(_FestMaske):
    """Cable: horizontal line that is dragged to the right. To its left the
    mask <CAB> (2.5), <TYP> and <REF> (1.5 each). Where a vertical wire
    crosses the line, a core marking stroke with a designation (L1, L2,
    L3, N, PE, 6, 7 ...) is created automatically, changeable per core.

    (x, y) = left end of the line, `laenge` = length to the right.
    CAB behaves like IND for devices (identifier for later lists);
    REF is created automatically from other cables with the same CAB.
    kreuzungen: (not saved) x positions of the crossings, computed by
    katiecad.electrical.logic.kabel_kreuzungen.
    adern: {distance from cable start ("%.1f"): designation} (changes)."""
    FELDER = ("CAB", "TYP")
    HOEHEN = {"CAB": 2.5, "TYP": 1.5}
    REF_HOEHE = 1.5
    ADER_HOEHE = 2.0
    STRICH = 1.25                     # half stroke length (45 degrees)
    TEXT_ABSTAND = 1.2                # Mask <-> cable start
    ADER_NAMEN = ("L1", "L2", "L3", "N", "PE")
    ZEILEN = ()

    def __init__(self, x, y, werte=None, laenge=40.0, adern=None, **kw):
        super().__init__("kabel", x, y, werte, **kw)
        self.laenge = max(1.0, float(laenge))
        self.adern = {str(k): str(v) for k, v in (adern or {}).items()}
        self.kreuzungen = []

    def to_dict(self):
        d = super().to_dict()
        d.pop("kreuzungen", None)
        d["adern"] = dict(self.adern)
        return d

    @staticmethod
    def ader_schluessel(abstand):
        return "%.1f" % abstand

    def ader_name(self, index, abstand):
        n = self.adern.get(self.ader_schluessel(abstand))
        if n:
            return n
        return (self.ADER_NAMEN[index] if index < len(self.ADER_NAMEN)
                else str(index + 1))

    def adern_liste(self):
        """[(key, current designation)] of the crossings found."""
        out = []
        for i, cx in enumerate(sorted(self.kreuzungen)):
            a = cx - self.x
            out.append((self.ader_schluessel(a), self.ader_name(i, a)))
        return out

    def aufgeloest(self, platzhalter=None):
        ph = self.platzhalter if platzhalter is None else platzhalter
        st = self._stil()
        self._anker = {}
        out = [Linie(self.x, self.y, self.x + self.laenge, self.y, **st)]
        tx = self.x - self.TEXT_ABSTAND
        for tag, dy, anker in (("CAB", 0.6, "unten_rechts"),
                               ("TYP", -1.2, "mitte_rechts")):
            w = self.werte.get(tag, "")
            if tag in self.ausgeblendet:
                continue
            if w == "":
                if not ph:
                    continue
                w = "<" + tag + ">"
            out.append(self._t(tag, tx, self.y + dy, w, self.HOEHEN[tag], anker, st))
        refs = ["(%s %s)" % (tr("qv.blatt"), ort_text(o)) for o in self.refs]
        if refs:                                  # REF only if there is something
            out.append(self._t("REF", tx, self.y - 2.3, "\n".join(refs),
                               self.REF_HOEHE, "oben_rechts", st))
        h = self.STRICH
        for i, cx in enumerate(sorted(self.kreuzungen)):
            if not (self.x < cx <= self.x + self.laenge):
                continue
            out.append(Linie(cx - h, self.y - h, cx + h, self.y + h, **st))
            out.append(Text(cx + h + 0.3, self.y + 1.0,
                            self.ader_name(i, cx - self.x), self.ADER_HOEHE,
                            0.0, "Arial", einfuegepunkt="unten_links", **st))
        return out

    def bbox(self):
        xs, ys = [self.x, self.x + self.laenge], [self.y]
        for k in self.aufgeloest(True):
            b = k.bbox()
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
        return (min(xs), min(ys), max(xs), max(ys))

    def griffe(self):
        self.aufgeloest(True)
        return ([("p", self.x, self.y), ("e", self.x + self.laenge, self.y)]
                + self.text_griffe())

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p":
            self.x, self.y = x, y
        elif griff_id == "e":
            self.laenge = max(1.0, x - self.x)
        elif griff_id.startswith("t:"):
            self.aufgeloest(True)
            self.text_bewegen(griff_id[2:], x, y)


class Klemme(_FestMaske):
    """Terminal: visible circle with two connections (top / bottom) and the
    fixed fields <IND> (2.5), <TYP>, <PER> (1.5) and <NUM> (1.75)."""
    FELDER = ("IND", "TYP", "PER", "NUM")
    DURCHMESSER = 2.0
    # Label: right-aligned directly left of the circle. IND is at the
    # height of the circle centre, TYP and PER below it.
    ZEILEN = (("IND", -3.0, 0.0, 2.5, "mitte_rechts"),
              ("TYP", -3.0, -3.0, 1.5, "mitte_rechts"),
              ("PER", -3.0, -5.5, 1.5, "mitte_rechts"),
              ("NUM", 2.0, 0.0, 1.75, "mitte_links"))

    def __init__(self, x, y, werte=None, **kw):
        super().__init__("klemme", x, y, werte, **kw)

    def aufgeloest(self, platzhalter=None):
        # Empty fields stay empty (terminals should be able to sit close together)
        return _FestMaske.aufgeloest(self, False)

    def anschluss_oben(self):
        return (self.x, self.y + self.DURCHMESSER / 2.0)

    def anschluss_unten(self):
        return (self.x, self.y - self.DURCHMESSER / 2.0)

    def _zusatz(self, ph, st):
        return [Kreis(self.x, self.y, self.DURCHMESSER / 2.0,
                      staerke=0.25, **st)]


# Elements composed of simple elements (aufgeloest())
class Koordinatenfeld(Element):
    """Zone grid (coordinate system) of a schematic sheet.

    (x, y) is the lower left corner of the drawing area `breite` x `hoehe`
    (default: DIN A4 sheet frame without title block = viewport size at 1:1).
    At the top are the column numbers 1..spalten, on the left the row letters
    A.. (A = top). The dashed outline (model view only) shows the viewport
    area; it appears neither in the layout nor in print/DXF.
    The field is selected only by clicking its frame, never by a selection
    rectangle (NUR_KLICK)."""
    NUR_KLICK = True
    INSET = 1.0                       # Distance frame <-> viewport outline
    UMRISS_FARBE = "#8b7ea8"

    def __init__(self, x, y, breite=287.0, hoehe=164.0, spalten=6, zeilen=4,
                 rand=5.0, text_hoehe=3.5, raster=False, **kw):
        kw.setdefault("staerke", 0.35)
        super().__init__("koordinatenfeld", **kw)
        self.x, self.y = float(x), float(y)
        self.breite, self.hoehe = float(breite), float(hoehe)
        self.spalten = max(1, min(int(spalten), 99))
        self.zeilen = max(1, min(int(zeilen), 26))
        self.rand = float(rand)
        self.text_hoehe = float(text_hoehe)
        self.raster = bool(raster)

    # Geometry
    def umriss_rect(self):
        return (self.x, self.y, self.x + self.breite, self.y + self.hoehe)

    def rahmen_rect(self):
        i = self.INSET
        return (self.x + i, self.y + i,
                self.x + self.breite - i, self.y + self.hoehe - i)

    def zellen_rect(self):
        x1, y1, x2, y2 = self.rahmen_rect()
        return (x1 + self.rand, y1, x2, y2 - self.rand)

    def spalten_name(self, i):
        return str(i + 1)

    def zeilen_name(self, j):
        return chr(ord("A") + j)

    def zone(self, px, py):
        """-> "column/row" (e.g. "2/B") or None outside the field."""
        ux1, uy1, ux2, uy2 = self.umriss_rect()
        if not (ux1 <= px <= ux2 and uy1 <= py <= uy2):
            return None
        cx1, cy1, cx2, cy2 = self.zellen_rect()
        bw = (cx2 - cx1) / self.spalten
        bh = (cy2 - cy1) / self.zeilen
        if bw <= 0 or bh <= 0:
            return None
        i = int(math.floor((px - cx1) / bw))
        j = int(math.floor((cy2 - py) / bh))
        i = max(0, min(self.spalten - 1, i))
        j = max(0, min(self.zeilen - 1, j))
        return f"{self.spalten_name(i)}/{self.zeilen_name(j)}"

    # Appearance
    def aufgeloest(self, umriss=False):
        st = dict(layer=self.layer, farbe=self.farbe,
                  linientyp="Volllinie (schmal)", eig_farbe=self.eig_farbe,
                  staerke=self.staerke)
        out = []

        def linie(a, b, c, d):
            out.append(Linie(a, b, c, d, **st))

        x1, y1, x2, y2 = self.rahmen_rect()
        cx1, cy1, cx2, cy2 = self.zellen_rect()
        linie(x1, y1, x2, y1); linie(x2, y1, x2, y2)
        linie(x2, y2, x1, y2); linie(x1, y2, x1, y1)
        linie(cx1, y1, cx1, y2)             # Separation of row labels
        linie(x1, cy2, x2, cy2)             # Separation of column labels
        bw = (cx2 - cx1) / self.spalten
        bh = (cy2 - cy1) / self.zeilen
        for k in range(1, self.spalten):
            xx = cx1 + k * bw
            linie(xx, y1 if self.raster else cy2, xx, y2)
        for k in range(1, self.zeilen):
            yy = cy2 - k * bh
            linie(x1, yy, x2 if self.raster else cx1, yy)
        tst = dict(layer=self.layer, farbe=self.farbe,
                   eig_farbe=self.eig_farbe)
        # The labels must stay inside the label strip (width `rand`): at most
        # 60 % of the strip height, so that nothing touches the lines in print.
        # (minus 0.1 mm: the PDF output renders the strokes slightly bolder)
        th = max(0.5, min(self.text_hoehe, 0.6 * min(self.rand, (y2 - cy2))) - 0.1)
        for i in range(self.spalten):
            out.append(Text(cx1 + (i + 0.5) * bw, (cy2 + y2) / 2.0,
                            self.spalten_name(i), th, 0.0, "Arial",
                            einfuegepunkt="mitte_zentriert", **tst))
        for j in range(self.zeilen):
            out.append(Text((x1 + cx1) / 2.0, cy2 - (j + 0.5) * bh,
                            self.zeilen_name(j), th, 0.0, "Arial",
                            einfuegepunkt="mitte_zentriert", **tst))
        if umriss:
            ust = dict(layer=self.layer, farbe=self.UMRISS_FARBE,
                       linientyp="Strichlinie (verdeckt)", eig_farbe=True,
                       staerke=0.18)
            a, b, c, d = self.umriss_rect()
            for (p, q, r, t) in ((a, b, c, b), (c, b, c, d),
                                 (c, d, a, d), (a, d, a, b)):
                out.append(Linie(p, q, r, t, **ust))
        return out

    def auswahl_linien(self):
        """Polylines on which a click selects the field (frame and outline, not
        the interior)."""
        out = []
        for rect in (self.umriss_rect(), self.rahmen_rect()):
            a, b, c, d = rect
            out.append([(a, b), (c, b), (c, d), (a, d), (a, b)])
        return out

    def bbox(self):
        return self.umriss_rect()

    def verschieben(self, dx, dy):
        self.x += dx
        self.y += dy

    def griffe(self):
        return [("p", self.x, self.y)]

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p":
            self.x, self.y = x, y

    def drehen(self, cx, cy, winkel_deg):
        self.x, self.y = punkte_drehen(self.x, self.y, cx, cy, winkel_deg)


# ============================================================
# 3D bodies (wireframe)
# ============================================================
def _ebene_drehen(e, cx, cy, wd):
    ox, oy = punkte_drehen(e[0], e[1], cx, cy, wd)
    ux, uy = punkte_drehen(e[3], e[4], 0.0, 0.0, wd)
    vx, vy = punkte_drehen(e[6], e[7], 0.0, 0.0, wd)
    return (ox, oy, e[2], ux, uy, e[5], vx, vy, e[8])


def _ebene_verschieben(e, dx, dy, dz):
    return (e[0] + dx, e[1] + dy, e[2] + dz) + tuple(e[3:])


def _ebene_skalieren(e, cx, cy, f):
    ox, oy = _skal_pt(e[0], e[1], cx, cy, f)
    return (ox, oy, e[2] * f) + tuple(e[3:])


def _ebene_spiegeln(e, ax, ay, bx, by):
    """Mirrored frame; v is negated so that the normal keeps its meaning
    (the local y coordinates of the geometry must be negated by the caller)."""
    ox, oy = punkt_spiegeln(e[0], e[1], ax, ay, bx, by)
    ux, uy = punkt_spiegeln(e[3], e[4], 0.0, 0.0, bx - ax, by - ay)
    vx, vy = punkt_spiegeln(e[6], e[7], 0.0, 0.0, bx - ax, by - ay)
    return (ox, oy, e[2], ux, uy, e[5], -vx, -vy, -e[8])


def _ebene_tuple(e):
    return None if e is None else tuple(float(v) for v in e)


class Koerper3D(Element):
    """Simple 3D body for the wireframe view.

    art "prisma":   base polygon `profil` extruded from z0 by `hoehe` (may be
                    negative = downwards): box, cylinder, extruded 2D shapes.
    art "pyramide": base polygon at z0, apex at z0 + hoehe above `spitze`
                    (default centre): pyramid, cone.
    art "kugel":    sphere `kugel` = (cx, cy, cz, r).
    `rund`: base is a circle/ellipse (only a few vertical edges are drawn).
    `ebene`: optional work plane (9-tuple, see geom3d) - the body is then
             built in the local coordinates of that plane (body on a face).
    `ausschnitte`: cut-outs (holes, pockets) in any plane:
             {"ebene": 9-tuple, "profil": [(x, y)...], "tiefe": mm | None
              (None = through), "rund": bool}.
    In the 2D drawing the body appears as its plan view (top view)."""
    ARTEN = ("prisma", "pyramide", "kugel")

    def __init__(self, art="prisma", profil=None, z0=0.0, hoehe=10.0, spitze=None,
                 rund=False, kugel=None, bez="", loecher=None, ebene=None,
                 ausschnitte=None, glatt=None, r_oben=0.0, r_unten=0.0, **kw):
        super().__init__("koerper3d", **kw)
        self.r_oben, self.r_unten = float(r_oben or 0.0), float(r_unten or 0.0)
        self.glatt = [bool(g) for g in glatt] if glatt else None
        self.art = art if art in self.ARTEN else "prisma"
        self.profil = [(float(p[0]), float(p[1])) for p in (profil or [])]
        self.z0, self.hoehe = float(z0), float(hoehe)
        self.spitze = None if spitze is None else (float(spitze[0]), float(spitze[1]))
        self.rund = bool(rund)
        self.kugel = None if kugel is None else tuple(float(v) for v in kugel)
        self.bez = bez
        self.ebene = _ebene_tuple(ebene)
        # holes (bores): (x, y, radius, depth); depth None = through all
        self.loecher = [(float(l[0]), float(l[1]), float(l[2]),
                         None if l[3] is None else float(l[3])) for l in (loecher or [])]
        self.ausschnitte = []
        for a in (ausschnitte or []):
            self.ausschnitte.append({
                "ebene": _ebene_tuple(a["ebene"]),
                "profil": [(float(p[0]), float(p[1])) for p in a["profil"]],
                "tiefe": None if a.get("tiefe") is None else float(a["tiefe"]),
                "rund": bool(a.get("rund", False))})

    # ---- geometry ---------------------------------------------------------
    def netz(self):
        if self.art == "kugel" and self.kugel:
            return kugel_netz(*self.kugel)
        if self.art == "pyramide":
            nz = pyramide_netz(self.profil, self.z0, self.hoehe, self.spitze, self.rund)
        else:
            nz = prisma_netz_gerundet(self.profil, self.z0, self.hoehe, self.rund, self.glatt,
                                      self.r_unten, self.r_oben)
        return netz_abbilden(nz, self.ebene) if self.ebene else nz

    def _loch_netz(self, loch):
        x, y, r, tiefe = loch
        oben = max(self.z0, self.z0 + self.hoehe)
        unten = min(self.z0, self.z0 + self.hoehe)
        h = (oben - unten) if tiefe is None else min(abs(tiefe), oben - unten)
        return prisma_netz(kreis_profil(x, y, r, 24), oben - h, h, True)

    def _ausschnitt_netz(self, a, host):
        e = a["ebene"]
        tiefe = a["tiefe"]
        if tiefe is None:                      # through: up to the far side of the host
            tiefe = max([G_dot_tiefe(e, p) for p in host.punkte] or [0.0])
        tiefe = max(tiefe, 1e-3)
        return netz_abbilden(prisma_netz(a["profil"], 0.0, -tiefe, a["rund"]), e)

    def netze(self):
        host = self.netz()
        out = [host]
        if self.art == "prisma":
            if not self.ebene:
                out.extend(self._loch_netz(l) for l in self.loecher)
            out.extend(self._ausschnitt_netz(a, host) for a in self.ausschnitte)
        return out

    def loch_hinzufuegen(self, x, y, r, tiefe=None):
        self.loecher.append((float(x), float(y), float(r),
                             None if tiefe is None else abs(float(tiefe))))

    def ausschnitt_hinzufuegen(self, ebene, profil, tiefe=None, rund=False):
        self.ausschnitte.append({"ebene": _ebene_tuple(ebene),
                                 "profil": [(float(x), float(y)) for (x, y) in profil],
                                 "tiefe": None if tiefe is None else abs(float(tiefe)),
                                 "rund": bool(rund)})

    def koerper(self):
        return [self]

    def bbox3(self):
        return self.netz().bbox()

    def bbox(self):
        if self.art == "kugel" and self.kugel:
            cx, cy, _cz, r = self.kugel
            return (cx - r, cy - r, cx + r, cy + r)
        if self.ebene:
            b = self.bbox3()
            return (b[0], b[1], b[3], b[4]) if b else (0, 0, 0, 0)
        if not self.profil:
            return (0, 0, 0, 0)
        xs = [p[0] for p in self.profil]; ys = [p[1] for p in self.profil]
        if self.spitze:
            xs.append(self.spitze[0]); ys.append(self.spitze[1])
        return (min(xs), min(ys), max(xs), max(ys))

    def zentrum3(self):
        b = self.bbox3()
        if b is None:
            return (0.0, 0.0, 0.0)
        return ((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2)

    def aufgeloest(self):
        """Plan view as 2D lines (for the normal drawing, picking and DXF)."""
        kw = dict(layer=self.layer, farbe=self.farbe, linientyp=self.linientyp,
                  eig_farbe=self.eig_farbe, staerke=self.staerke)
        if self.art == "kugel" and self.kugel:
            return [Kreis(self.kugel[0], self.kugel[1], self.kugel[3], **kw)]
        out, gesehen = [], set()
        if self.art == "prisma" and not self.ebene:
            for (x, y, r, _t) in self.loecher:
                out.append(Kreis(x, y, r, **kw))
        alle = self.netze()
        n_loch = 0 if self.ebene else len(self.loecher)
        gestrichelt = dict(kw, linientyp="Strichlinie (verdeckt)")
        netze = [(alle[0], kw)]
        for a, nz in zip(self.ausschnitte, alle[1 + n_loch:]):
            oben = ebene_basis(a["ebene"])[2][2] > 0.99          # opens to the top: visible
            netze.append((nz, kw if oben else gestrichelt))
        for nz, stil in netze:
            for (i, j) in nz.kanten:
                a, b = nz.punkte[i], nz.punkte[j]
                if math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-9:
                    continue
                key = tuple(sorted(((round(a[0], 6), round(a[1], 6)),
                                    (round(b[0], 6), round(b[1], 6)))))
                if key in gesehen:
                    continue
                gesehen.add(key)
                out.append(Linie(a[0], a[1], b[0], b[1], **stil))
        return out

    # ---- transformations -------------------------------------------------
    def _ausschnitte_map(self, f):
        for a in self.ausschnitte:
            f(a)

    def verschieben(self, dx, dy, dz=0.0):
        if self.ebene:
            self.ebene = _ebene_verschieben(self.ebene, dx, dy, dz)
        else:
            self.profil = [(x + dx, y + dy) for (x, y) in self.profil]
            if self.spitze:
                self.spitze = (self.spitze[0] + dx, self.spitze[1] + dy)
            if self.kugel:
                self.kugel = (self.kugel[0] + dx, self.kugel[1] + dy, self.kugel[2] + dz,
                              self.kugel[3])
            self.z0 += dz
            self.loecher = [(x + dx, y + dy, r, t) for (x, y, r, t) in self.loecher]
        for a in self.ausschnitte:
            a["ebene"] = _ebene_verschieben(a["ebene"], dx, dy, dz)

    def drehen(self, cx, cy, winkel_deg):
        if self.ebene:
            self.ebene = _ebene_drehen(self.ebene, cx, cy, winkel_deg)
        else:
            self.loecher = [punkte_drehen(x, y, cx, cy, winkel_deg) + (r, t)
                            for (x, y, r, t) in self.loecher]
            self.profil = [punkte_drehen(x, y, cx, cy, winkel_deg) for (x, y) in self.profil]
            if self.spitze:
                self.spitze = punkte_drehen(self.spitze[0], self.spitze[1], cx, cy, winkel_deg)
            if self.kugel:
                x, y = punkte_drehen(self.kugel[0], self.kugel[1], cx, cy, winkel_deg)
                self.kugel = (x, y, self.kugel[2], self.kugel[3])
        for a in self.ausschnitte:
            a["ebene"] = _ebene_drehen(a["ebene"], cx, cy, winkel_deg)

    def skalieren(self, cx, cy, f):
        if self.ebene:
            self.ebene = _ebene_skalieren(self.ebene, cx, cy, f)
            self.profil = [(x * f, y * f) for (x, y) in self.profil]
            if self.spitze:
                self.spitze = (self.spitze[0] * f, self.spitze[1] * f)
        else:
            self.profil = [_skal_pt(x, y, cx, cy, f) for (x, y) in self.profil]
            if self.spitze:
                self.spitze = _skal_pt(self.spitze[0], self.spitze[1], cx, cy, f)
            if self.kugel:
                x, y = _skal_pt(self.kugel[0], self.kugel[1], cx, cy, f)
                self.kugel = (x, y, self.kugel[2] * f, self.kugel[3] * f)
            self.loecher = [_skal_pt(x, y, cx, cy, f) + (r * f, None if t is None else t * f)
                            for (x, y, r, t) in self.loecher]
        self.z0 *= f
        self.hoehe *= f
        self.r_oben *= f
        self.r_unten *= f
        for a in self.ausschnitte:
            a["ebene"] = _ebene_skalieren(a["ebene"], cx, cy, f)
            a["profil"] = [(x * f, y * f) for (x, y) in a["profil"]]
            if a["tiefe"] is not None:
                a["tiefe"] *= f

    def spiegeln(self, ax, ay, bx, by):
        if self.ebene:
            self.ebene = _ebene_spiegeln(self.ebene, ax, ay, bx, by)
            self.profil = [(x, -y) for (x, y) in self.profil]
            if self.spitze:
                self.spitze = (self.spitze[0], -self.spitze[1])
        else:
            self.loecher = [punkt_spiegeln(x, y, ax, ay, bx, by) + (r, t)
                            for (x, y, r, t) in self.loecher]
            self.profil = [punkt_spiegeln(x, y, ax, ay, bx, by) for (x, y) in self.profil]
            if self.spitze:
                self.spitze = punkt_spiegeln(self.spitze[0], self.spitze[1], ax, ay, bx, by)
            if self.kugel:
                x, y = punkt_spiegeln(self.kugel[0], self.kugel[1], ax, ay, bx, by)
                self.kugel = (x, y, self.kugel[2], self.kugel[3])
        for a in self.ausschnitte:
            a["ebene"] = _ebene_spiegeln(a["ebene"], ax, ay, bx, by)
            a["profil"] = [(x, -y) for (x, y) in a["profil"]]

    def _ebene_aktivieren(self):
        """Gives a body without work plane the ground plane (legacy vertical holes become
        cut-outs) so that it can be rotated freely."""
        if self.ebene or self.art == "kugel":
            return
        oben = max(self.z0, self.z0 + self.hoehe)
        for (x, y, r, t) in self.loecher:
            self.ausschnitte.append({"ebene": (0.0, 0.0, oben, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
                                     "profil": kreis_profil(x, y, r, 24),
                                     "tiefe": None if t is None else float(t), "rund": True})
        self.loecher = []
        self.ebene = BODEN_EBENE

    def drehen3(self, p0, achse, winkel_deg):
        """Rotates the body about the axis through p0 with direction `achse`."""
        def ebene_rot(e):
            o = punkt_rotieren(e[:3], p0, achse, winkel_deg)
            u = v_rotieren(e[3:6], achse, winkel_deg)
            v = v_rotieren(e[6:9], achse, winkel_deg)
            return tuple(o) + tuple(u) + tuple(v)
        if self.art == "kugel" and self.kugel:
            c = punkt_rotieren(self.kugel[:3], p0, achse, winkel_deg)
            self.kugel = (c[0], c[1], c[2], self.kugel[3])
        else:
            self._ebene_aktivieren()
            self.ebene = ebene_rot(self.ebene)
        for a in self.ausschnitte:
            a["ebene"] = ebene_rot(a["ebene"])

    def kanten_oben_unten(self, r, oben=True, unten=False):
        """Rounds the top and/or bottom perimeter edges. True if done."""
        if self.art != "prisma" or len(self.profil) < 3 or r <= 0:
            return False
        xs = [p[0] for p in self.profil]; ys = [p[1] for p in self.profil]
        grenze = 0.45 * min(max(xs) - min(xs), max(ys) - min(ys))
        r = min(r, grenze, abs(self.hoehe) / (2 if (oben and unten) else 1))
        if r <= 1e-9:
            return False
        # z0 is the bottom for a positive height; for a negative one the "top" lies below z0
        if self.hoehe >= 0:
            if oben: self.r_oben = r
            if unten: self.r_unten = r
        else:
            if oben: self.r_unten = r
            if unten: self.r_oben = r
        return True

    def kanten_abrunden(self, r, n=6):
        """Rounds the vertical edges (corners of the base polygon). True if done."""
        if self.art != "prisma" or self.rund or len(self.profil) < 3 or r <= 0:
            return False
        self.profil, self.glatt = profil_abrunden(self.profil, r, n)
        return True

    def hoehe_setzen(self, h):
        """Push/pull: new signed height (apex / top face moves)."""
        if self.art in ("prisma", "pyramide"):
            self.hoehe = float(h)

    def to_dict(self):
        d = super().to_dict()
        d["profil"] = [list(p) for p in self.profil]
        d["glatt"] = list(self.glatt) if self.glatt else None
        d["r_oben"], d["r_unten"] = self.r_oben, self.r_unten
        d["spitze"] = list(self.spitze) if self.spitze else None
        d["kugel"] = list(self.kugel) if self.kugel else None
        d["loecher"] = [list(l) for l in self.loecher]
        d["ebene"] = list(self.ebene) if self.ebene else None
        d["ausschnitte"] = [{"ebene": list(a["ebene"]), "profil": [list(p) for p in a["profil"]],
                             "tiefe": a["tiefe"], "rund": a["rund"]} for a in self.ausschnitte]
        return d


def G_dot_tiefe(e, p):
    """Distance of point p behind the plane e (along -normal); > 0 inside the body."""
    u = (e[3], e[4], e[5]); v = (e[6], e[7], e[8])
    w = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    return (e[0] - p[0]) * w[0] + (e[1] - p[1]) * w[1] + (e[2] - p[2]) * w[2]


class Gruppe3D(Element):
    """'3D block': several 3D bodies handled as one object (overview only,
    NOT a device with an electrical function)."""

    def __init__(self, teile=None, name="3D-Block", **kw):
        super().__init__("gruppe3d", **kw)
        self.name = name
        self.teile = []
        for t in (teile or []):
            if isinstance(t, dict):
                t = dict(t)
                typ = t.pop("typ", "koerper3d")
                t = Gruppe3D(**t) if typ == "gruppe3d" else Koerper3D(**t)
            self.teile.append(t)

    def koerper(self):
        out = []
        for t in self.teile:
            out.extend(t.koerper())
        return out

    def netze(self):
        out = []
        for t in self.teile:
            out.extend(t.netze())
        return out

    def bbox3(self):
        bs = [b for b in (t.bbox3() for t in self.teile) if b]
        if not bs:
            return None
        return (min(b[0] for b in bs), min(b[1] for b in bs), min(b[2] for b in bs),
                max(b[3] for b in bs), max(b[4] for b in bs), max(b[5] for b in bs))

    def bbox(self):
        bs = [t.bbox() for t in self.teile]
        if not bs:
            return (0, 0, 0, 0)
        return (min(b[0] for b in bs), min(b[1] for b in bs),
                max(b[2] for b in bs), max(b[3] for b in bs))

    def zentrum3(self):
        b = self.bbox3()
        if b is None:
            return (0.0, 0.0, 0.0)
        return ((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2)

    def aufgeloest(self):
        out = []
        for t in self.teile:
            out.extend(t.aufgeloest())
        return out

    def verschieben(self, dx, dy, dz=0.0):
        for t in self.teile:
            t.verschieben(dx, dy, dz)

    def drehen(self, cx, cy, winkel_deg):
        for t in self.teile:
            t.drehen(cx, cy, winkel_deg)

    def drehen3(self, p0, achse, winkel_deg):
        for t in self.teile:
            t.drehen3(p0, achse, winkel_deg)

    def skalieren(self, cx, cy, f):
        for t in self.teile:
            t.skalieren(cx, cy, f)

    def spiegeln(self, ax, ay, bx, by):
        for t in self.teile:
            t.spiegeln(ax, ay, bx, by)

    def to_dict(self):
        d = {k: v for k, v in self.__dict__.items() if k not in ("id", "teile")}
        d["teile"] = [t.to_dict() for t in self.teile]
        return d


class Skizze3D(Element):
    """2D shape drawn on a work plane in space (a face of a 3D body or the
    ground plane). Used to pull up (extrude) or to cut a hole / pocket."""
    FORMEN = ("kreis", "rechteck", "polylinie", "linie")

    def __init__(self, form="kreis", ebene=None, daten=None, **kw):
        super().__init__("skizze3d", **kw)
        self.form = form if form in self.FORMEN else "kreis"
        self.ebene = _ebene_tuple(ebene) or BODEN_EBENE
        self.daten = [list(d) if isinstance(d, (list, tuple)) else float(d)
                      for d in (daten or [])]

    def profil(self):
        d = self.daten
        if self.form == "kreis" and len(d) >= 3:
            return kreis_profil(d[0], d[1], d[2], 32)
        if self.form == "rechteck" and len(d) >= 4:
            x1, x2 = sorted((d[0], d[2])); y1, y2 = sorted((d[1], d[3]))
            return rechteck_profil(x1, y1, x2, y2)
        if self.form == "polylinie":
            return [(float(p[0]), float(p[1])) for p in d]
        if self.form == "linie" and len(d) >= 4:
            return [(float(d[0]), float(d[1])), (float(d[2]), float(d[3]))]
        return []

    def geschlossen(self):
        return self.form != "linie"

    def rund(self):
        return self.form == "kreis"

    def zug3(self):
        return [ebene_punkt(self.ebene, x, y) for (x, y) in self.profil()]

    def aufgeloest(self):
        kw = dict(layer=self.layer, farbe=self.farbe, linientyp=self.linientyp,
                  eig_farbe=self.eig_farbe, staerke=self.staerke)
        pts = self.zug3()
        paare = zip(pts, pts[1:] + (pts[:1] if self.geschlossen() else []))
        return [Linie(a[0], a[1], b[0], b[1], **kw)
                for a, b in paare
                if math.hypot(a[0] - b[0], a[1] - b[1]) > 1e-9]

    def bbox(self):
        pts = self.zug3()
        if not pts:
            return (0, 0, 0, 0)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def zentrum3(self):
        pts = self.zug3()
        if not pts:
            return tuple(self.ebene[:3])
        n = len(pts)
        return tuple(sum(p[i] for p in pts) / n for i in range(3))

    def verschieben(self, dx, dy, dz=0.0):
        self.ebene = _ebene_verschieben(self.ebene, dx, dy, dz)

    def drehen(self, cx, cy, winkel_deg):
        self.ebene = _ebene_drehen(self.ebene, cx, cy, winkel_deg)

    def drehen3(self, p0, achse, winkel_deg):
        e = self.ebene
        self.ebene = (tuple(punkt_rotieren(e[:3], p0, achse, winkel_deg))
                      + tuple(v_rotieren(e[3:6], achse, winkel_deg))
                      + tuple(v_rotieren(e[6:9], achse, winkel_deg)))

    def skalieren(self, cx, cy, f):
        self.ebene = _ebene_skalieren(self.ebene, cx, cy, f)
        if self.form == "polylinie":
            self.daten = [[p[0] * f, p[1] * f] for p in self.daten]
        else:
            self.daten = [v * f for v in self.daten]

    def spiegeln(self, ax, ay, bx, by):
        self.ebene = _ebene_spiegeln(self.ebene, ax, ay, bx, by)
        d = self.daten
        if self.form == "kreis" and len(d) >= 3:
            self.daten = [d[0], -d[1], d[2]]
        elif self.form in ("rechteck", "linie") and len(d) >= 4:
            self.daten = [d[0], -d[1], d[2], -d[3]]
        else:
            self.daten = [[p[0], -p[1]] for p in d]

    def to_dict(self):
        d = super().to_dict()
        d["ebene"] = list(self.ebene)
        d["daten"] = [list(v) if isinstance(v, (list, tuple)) else v for v in self.daten]
        return d


class Text3D(Element):
    """Text in the 3D model. With a work plane (`ebene`: 9-tuple, axes u/v used) the text lies
    on that plane as stroke text, lower left corner at `p`, rotated by `winkel` degrees within
    the plane. Without a plane (older files) it is a label that faces the viewer.
    In the 2D drawing it appears as ordinary text (vertical planes: as lines)."""

    def __init__(self, p=(0, 0, 0), inhalt="", hoehe=3.5, ebene=None, winkel=0.0, **kw):
        super().__init__("text3d", **kw)
        self.p = tuple(float(v) for v in p)
        self.inhalt = inhalt
        self.hoehe = float(hoehe)
        self.ebene = _ebene_tuple(ebene)
        self.winkel = float(winkel)

    def zentrum3(self):
        return self.p

    def _achsen(self):
        """In-plane axes (u, v) including the rotation `winkel`."""
        e = self.ebene or BODEN_EBENE
        u, v = tuple(e[3:6]), tuple(e[6:9])
        if abs(self.winkel) > 1e-9:
            w = v_cross(u, v)
            u, v = v_rotieren(u, w, self.winkel), v_rotieren(v, w, self.winkel)
        return u, v

    def zuege3(self):
        """3D polylines of the stroke text (empty for the viewer-facing variant)."""
        if self.ebene is None:
            return []
        from katiecad.model.strichschrift import text_zuege
        u, v = self._achsen()
        p = self.p
        return [[(p[0] + x * u[0] + y * v[0], p[1] + x * u[1] + y * v[1],
                  p[2] + x * u[2] + y * v[2]) for (x, y) in zug]
                for zug in text_zuege(self.inhalt, self.hoehe)]

    def _kw(self):
        return dict(layer=self.layer, farbe=self.farbe, linientyp=self.linientyp,
                    eig_farbe=self.eig_farbe, staerke=self.staerke)

    def _flach_oben(self):
        if self.ebene is None:
            return True
        n = v_cross(tuple(self.ebene[3:6]), tuple(self.ebene[6:9]))
        return abs(n[2]) > 0.99

    def _text2d(self):
        w = 0.0
        if self.ebene is not None:
            u, _v = self._achsen()
            w = math.degrees(math.atan2(u[1], u[0]))
            n = v_cross(tuple(self.ebene[3:6]), tuple(self.ebene[6:9]))
            if n[2] < 0:
                w = 0.0
        return Text(self.p[0], self.p[1], self.inhalt, hoehe=self.hoehe, winkel=w, **self._kw())

    def aufgeloest(self):
        if self._flach_oben():
            return [self._text2d()]
        out = []
        for zug in self.zuege3():                 # vertical text: its strokes seen from above
            for a, b in zip(zug, zug[1:]):
                if math.hypot(a[0] - b[0], a[1] - b[1]) > 1e-9:
                    out.append(Linie(a[0], a[1], b[0], b[1], **self._kw()))
        return out

    def bbox(self):
        bs = [el.bbox() for el in self.aufgeloest()]
        if not bs:
            return (self.p[0], self.p[1], self.p[0], self.p[1])
        return (min(b[0] for b in bs), min(b[1] for b in bs),
                max(b[2] for b in bs), max(b[3] for b in bs))

    def verschieben(self, dx, dy, dz=0.0):
        self.p = (self.p[0] + dx, self.p[1] + dy, self.p[2] + dz)

    def drehen(self, cx, cy, winkel_deg):
        x, y = punkte_drehen(self.p[0], self.p[1], cx, cy, winkel_deg)
        self.p = (x, y, self.p[2])
        if self.ebene is not None:
            self.ebene = (self.p + tuple(v_rotieren(self.ebene[3:6], (0, 0, 1), winkel_deg))
                          + tuple(v_rotieren(self.ebene[6:9], (0, 0, 1), winkel_deg)))

    def drehen3(self, p0, achse, winkel_deg):
        self.p = tuple(punkt_rotieren(self.p, p0, achse, winkel_deg))
        if self.ebene is not None:
            self.ebene = (self.p + tuple(v_rotieren(self.ebene[3:6], achse, winkel_deg))
                          + tuple(v_rotieren(self.ebene[6:9], achse, winkel_deg)))

    def skalieren(self, cx, cy, f):
        x, y = _skal_pt(self.p[0], self.p[1], cx, cy, f)
        self.p = (x, y, self.p[2] * f)
        self.hoehe *= f

    def spiegeln(self, ax, ay, bx, by):
        x, y = punkt_spiegeln(self.p[0], self.p[1], ax, ay, bx, by)
        self.p = (x, y, self.p[2])

    def to_dict(self):
        d = super().to_dict()
        d["p"] = list(self.p)
        d["ebene"] = list(self.ebene) if self.ebene is not None else None
        return d


class Bemassung3D(Element):
    """Dimension between two points in space, drawn offset by `versatz`
    (a 3D vector). In the 2D plan it appears projected."""

    def __init__(self, p1=(0, 0, 0), p2=(0, 0, 0), versatz=(0, 0, 0), faktor=1.0,
                 dezimal=2, text="", **kw):
        super().__init__("bemassung3d", **kw)
        self.p1 = tuple(float(v) for v in p1)
        self.p2 = tuple(float(v) for v in p2)
        self.versatz = tuple(float(v) for v in versatz)
        self.faktor = float(faktor) or 1.0
        self.dezimal = int(dezimal)
        self.text = text

    def laenge(self):
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(self.p1, self.p2)))

    def wert_text(self):
        if self.text:
            return self.text
        return f"{self.laenge() / self.faktor:.{self.dezimal}f}"

    def zuege3(self):
        """3D polylines: two extension lines + the dimension line with arrow heads."""
        a = tuple(self.p1[i] + self.versatz[i] for i in range(3))
        b = tuple(self.p2[i] + self.versatz[i] for i in range(3))
        out = []
        if any(abs(v) > 1e-9 for v in self.versatz):
            out.append([self.p1, a]); out.append([self.p2, b])
        out.append([a, b])
        L = self.laenge()
        if L > 1e-9:
            d = tuple((b[i] - a[i]) / L for i in range(3))
            pf = min(L * 0.12, 3.0)                      # arrow length
            n = _normale_zu(d)
            for (pt, sg) in ((a, 1.0), (b, -1.0)):
                base = tuple(pt[i] + sg * d[i] * pf for i in range(3))
                for s2 in (1.0, -1.0):
                    out.append([pt, tuple(base[i] + s2 * n[i] * pf * 0.3 for i in range(3))])
        return out

    def text_pos3(self):
        return tuple((self.p1[i] + self.p2[i]) / 2 + self.versatz[i] for i in range(3))

    def aufgeloest(self):
        kw = dict(layer=self.layer, farbe=self.farbe, linientyp=self.linientyp,
                  eig_farbe=self.eig_farbe, staerke=self.staerke)
        out = []
        for zug in self.zuege3():
            for a, b in zip(zug, zug[1:]):
                if math.hypot(a[0] - b[0], a[1] - b[1]) > 1e-9:
                    out.append(Linie(a[0], a[1], b[0], b[1], **kw))
        t = self.text_pos3()
        out.append(Text(t[0], t[1], self.wert_text(), 2.5, 0.0, "Arial",
                        einfuegepunkt="mitte_zentriert", **kw))
        return out

    def bbox(self):
        pts = [self.p1, self.p2] + [tuple(self.p1[i] + self.versatz[i] for i in range(3)),
                                    tuple(self.p2[i] + self.versatz[i] for i in range(3))]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def zentrum3(self):
        return self.text_pos3()

    def verschieben(self, dx, dy, dz=0.0):
        self.p1 = (self.p1[0] + dx, self.p1[1] + dy, self.p1[2] + dz)
        self.p2 = (self.p2[0] + dx, self.p2[1] + dy, self.p2[2] + dz)

    def drehen(self, cx, cy, winkel_deg):
        def r(p):
            x, y = punkte_drehen(p[0], p[1], cx, cy, winkel_deg)
            return (x, y, p[2])
        self.p1, self.p2 = r(self.p1), r(self.p2)
        vx, vy = punkte_drehen(self.versatz[0], self.versatz[1], 0.0, 0.0, winkel_deg)
        self.versatz = (vx, vy, self.versatz[2])

    def drehen3(self, p0, achse, winkel_deg):
        self.p1 = tuple(punkt_rotieren(self.p1, p0, achse, winkel_deg))
        self.p2 = tuple(punkt_rotieren(self.p2, p0, achse, winkel_deg))
        self.versatz = tuple(v_rotieren(self.versatz, achse, winkel_deg))

    def skalieren(self, cx, cy, f):
        def sk(p):
            x, y = _skal_pt(p[0], p[1], cx, cy, f)
            return (x, y, p[2] * f)
        self.p1, self.p2 = sk(self.p1), sk(self.p2)
        self.versatz = tuple(v * f for v in self.versatz)

    def spiegeln(self, ax, ay, bx, by):
        def sp(p):
            x, y = punkt_spiegeln(p[0], p[1], ax, ay, bx, by)
            return (x, y, p[2])
        self.p1, self.p2 = sp(self.p1), sp(self.p2)
        vx, vy = punkt_spiegeln(self.versatz[0], self.versatz[1], 0.0, 0.0, bx - ax, by - ay)
        self.versatz = (vx, vy, self.versatz[2])

    def to_dict(self):
        d = super().to_dict()
        for k in ("p1", "p2", "versatz"):
            d[k] = list(d[k])
        return d


def _normale_zu(d):
    """Any unit vector perpendicular to d."""
    h = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
    n = (d[1] * h[2] - d[2] * h[1], d[2] * h[0] - d[0] * h[2], d[0] * h[1] - d[1] * h[0])
    l = math.sqrt(sum(v * v for v in n)) or 1.0
    return tuple(v / l for v in n)


def profil_aus_element(el):
    """Base polygon of a closed 2D shape for extruding: (profil, rund) or None."""
    if isinstance(el, Rechteck):
        x1, x2 = sorted((el.x1, el.x2)); y1, y2 = sorted((el.y1, el.y2))
        return rechteck_profil(x1, y1, x2, y2), False
    if isinstance(el, Kreis):
        return kreis_profil(el.cx, el.cy, el.r, 32), True
    if isinstance(el, Polylinie) and el.geschlossen and len(el.punkte) >= 3:
        rund = isinstance(el, (Ellipse, Spline))
        pts = list(el.punkte)
        if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-9:
            pts = pts[:-1]
        return pts, rund
    return None


def extrusion(el, hoehe, z0=0.0):
    """Koerper3D from a closed 2D element (None if not possible)."""
    if isinstance(el, Skizze3D):
        if len(el.profil()) < 3:
            return None
        return Koerper3D("prisma", el.profil(), z0, hoehe, rund=el.rund(), bez="Extrusion",
                         ebene=el.ebene, layer=el.layer, farbe=el.farbe,
                         linientyp=el.linientyp, eig_farbe=el.eig_farbe, staerke=el.staerke)
    pr = profil_aus_element(el)
    if pr is None:
        return None
    return Koerper3D("prisma", pr[0], z0, hoehe, rund=pr[1], bez="Extrusion",
                     layer=el.layer, farbe=el.farbe, linientyp=el.linientyp,
                     eig_farbe=el.eig_farbe, staerke=el.staerke)


def quader(x1, y1, x2, y2, z0, hoehe, **kw):
    x1, x2 = sorted((x1, x2)); y1, y2 = sorted((y1, y2))
    return Koerper3D("prisma", rechteck_profil(x1, y1, x2, y2), z0, hoehe, bez="Quader", **kw)


def zylinder(cx, cy, r, z0, hoehe, n=32, **kw):
    return Koerper3D("prisma", kreis_profil(cx, cy, r, n), z0, hoehe, rund=True,
                     bez="Zylinder", **kw)


def kegel(cx, cy, r, z0, hoehe, n=32, **kw):
    return Koerper3D("pyramide", kreis_profil(cx, cy, r, n), z0, hoehe, rund=True,
                     bez="Kegel", **kw)


def pyramide(cx, cy, z0, hoehe, ecken=4, breite=20.0, tiefe=20.0, **kw):
    if ecken == 4:
        prof = rechteck_profil(cx - breite / 2, cy - tiefe / 2, cx + breite / 2, cy + tiefe / 2)
    else:
        prof = kreis_profil(cx, cy, breite / 2, max(3, int(ecken)), 90.0)
    return Koerper3D("pyramide", prof, z0, hoehe, bez="Pyramide", **kw)


def kugel(cx, cy, cz, r, **kw):
    return Koerper3D("kugel", [], 0.0, 0.0, kugel=(cx, cy, cz, r), bez="Kugel", **kw)


ZUSAMMENGESETZT = (BlockReferenz, Querverweis, Verbindung, ElektroMaske, Klemme,
                   Kabel, Koordinatenfeld, Koerper3D, Gruppe3D, Skizze3D, Bemassung3D, Text3D)


# ============================================================
# Scaling and mirroring of all element types
# ============================================================
def punkt_spiegeln(px, py, ax, ay, bx, by):
    """Reflects the point (px, py) about the line through (ax, ay), (bx, by)."""
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-18:
        return px, py
    t = ((px - ax) * dx + (py - ay) * dy) / l2
    fx, fy = ax + t * dx, ay + t * dy
    return 2 * fx - px, 2 * fy - py


def _phi(ax, ay, bx, by):
    return math.degrees(math.atan2(by - ay, bx - ax))


def _r90(d):
    return int(round(d / 90.0)) * 90 % 360


def _achsparallel(phi):
    return abs(phi / 90.0 - round(phi / 90.0)) < 1e-6


def _skal_pt(x, y, cx, cy, f):
    return cx + (x - cx) * f, cy + (y - cy) * f


def _inst(cls, **methods):
    for name, fn in methods.items():
        setattr(cls, name, fn)


# ---- scaling --------------------------------------------------
def _sk_linie(e, cx, cy, f):
    e.x1, e.y1 = _skal_pt(e.x1, e.y1, cx, cy, f)
    e.x2, e.y2 = _skal_pt(e.x2, e.y2, cx, cy, f)


def _sk_kreis(e, cx, cy, f):
    e.cx, e.cy = _skal_pt(e.cx, e.cy, cx, cy, f)
    e.r *= f


def _sk_poly(e, cx, cy, f):
    e.punkte = [_skal_pt(x, y, cx, cy, f) for (x, y) in e.punkte]


def _sk_text(e, cx, cy, f):
    e.x, e.y = _skal_pt(e.x, e.y, cx, cy, f)
    e.hoehe *= f
    if isinstance(e, Verbindungspunkt):
        e.radius *= f


def _sk_schraffur(e, cx, cy, f):
    _sk_poly(e, cx, cy, f)
    e.abstand *= f


def _sk_bem(e, cx, cy, f):
    e.x1, e.y1 = _skal_pt(e.x1, e.y1, cx, cy, f)
    e.x2, e.y2 = _skal_pt(e.x2, e.y2, cx, cy, f)
    if e.x3 is not None and e.y3 is not None:
        e.x3, e.y3 = _skal_pt(e.x3, e.y3, cx, cy, f)
    e.mx, e.my = _skal_pt(e.mx, e.my, cx, cy, f)
    if e.tx is not None and e.ty is not None:
        e.tx, e.ty = _skal_pt(e.tx, e.ty, cx, cy, f)
    e.hoehe *= f
    e.pfeil *= f


def _sk_block(e, cx, cy, f):
    e.x, e.y = _skal_pt(e.x, e.y, cx, cy, f)
    e.skalierung *= f
    e.sp_dx *= f
    e.sp_dy *= f


def _sk_pos(e, cx, cy, f):
    """Fixed-size electrical elements: only the position is scaled."""
    e.x, e.y = _skal_pt(e.x, e.y, cx, cy, f)


def _sk_kabel(e, cx, cy, f):
    _sk_pos(e, cx, cy, f)
    e.laenge = max(1.0, e.laenge * f)


def _sk_kf(e, cx, cy, f):
    _sk_pos(e, cx, cy, f)
    e.breite *= f
    e.hoehe *= f


def _sk_rechteck(e, cx, cy, f):
    e.x1, e.y1 = _skal_pt(e.x1, e.y1, cx, cy, f)
    e.x2, e.y2 = _skal_pt(e.x2, e.y2, cx, cy, f)


# ---- mirroring ------------------------------------------------
def _sp_linie(e, ax, ay, bx, by):
    e.x1, e.y1 = punkt_spiegeln(e.x1, e.y1, ax, ay, bx, by)
    e.x2, e.y2 = punkt_spiegeln(e.x2, e.y2, ax, ay, bx, by)


def _sp_kreis(e, ax, ay, bx, by):
    e.cx, e.cy = punkt_spiegeln(e.cx, e.cy, ax, ay, bx, by)


def _sp_bogen(e, ax, ay, bx, by):
    _sp_kreis(e, ax, ay, bx, by)
    phi = _phi(ax, ay, bx, by)
    e.start, e.ende = (2 * phi - e.ende) % 360.0, (2 * phi - e.start) % 360.0


def _sp_poly(e, ax, ay, bx, by):
    e.punkte = [punkt_spiegeln(x, y, ax, ay, bx, by) for (x, y) in e.punkte]


def _sp_rechteck(e, ax, ay, bx, by):
    phi = _phi(ax, ay, bx, by)
    if _achsparallel(phi):
        e.x1, e.y1 = punkt_spiegeln(e.x1, e.y1, ax, ay, bx, by)
        e.x2, e.y2 = punkt_spiegeln(e.x2, e.y2, ax, ay, bx, by)
        return
    pts = [punkt_spiegeln(x, y, ax, ay, bx, by) for (x, y) in
           ((e.x1, e.y1), (e.x2, e.y1), (e.x2, e.y2), (e.x1, e.y2))]
    neu = Polylinie(pts, geschlossen=True, layer=e.layer, farbe=e.farbe,
                    linientyp=e.linientyp, eig_farbe=e.eig_farbe,
                    staerke=e.staerke)
    e.__class__ = Polylinie
    e.__dict__.clear()
    e.__dict__.update(neu.__dict__)


_ANKER_TAUSCH = {"links": "rechts", "rechts": "links",
                 "oben": "unten", "unten": "oben"}


def _sp_text(e, ax, ay, bx, by):
    e.x, e.y = punkt_spiegeln(e.x, e.y, ax, ay, bx, by)
    phi = _phi(ax, ay, bx, by) % 180.0
    ep = e.einfuegepunkt
    if ep and "_" in ep:
        zeile, spalte = ep.split("_", 1)
        if abs(phi - 90.0) < 1e-6:            # left <-> right (text stays readable)
            spalte = _ANKER_TAUSCH.get(spalte, spalte)
        elif phi < 1e-6 or abs(phi - 180.0) < 1e-6:
            zeile = _ANKER_TAUSCH.get(zeile, zeile)
        e.einfuegepunkt = zeile + "_" + spalte
    if isinstance(e, Verbindungspunkt) and e.richtungen is not None:
        p2 = _phi(ax, ay, bx, by)
        e.richtungen = sorted({_r90(2 * p2 - r) for r in e.richtungen})


def _sp_schraffur(e, ax, ay, bx, by):
    _sp_poly(e, ax, ay, bx, by)
    e.winkel = (2 * _phi(ax, ay, bx, by) - e.winkel) % 360.0


def _sp_bem(e, ax, ay, bx, by):
    e.x1, e.y1 = punkt_spiegeln(e.x1, e.y1, ax, ay, bx, by)
    e.x2, e.y2 = punkt_spiegeln(e.x2, e.y2, ax, ay, bx, by)
    if e.x3 is not None and e.y3 is not None:
        e.x3, e.y3 = punkt_spiegeln(e.x3, e.y3, ax, ay, bx, by)
    e.mx, e.my = punkt_spiegeln(e.mx, e.my, ax, ay, bx, by)
    if e.tx is not None and e.ty is not None:
        e.tx, e.ty = punkt_spiegeln(e.tx, e.ty, ax, ay, bx, by)
    if not _achsparallel(_phi(ax, ay, bx, by)) and e.richtung in ("horizontal", "vertikal"):
        e.richtung = "ausgerichtet"


def _sp_block(e, ax, ay, bx, by):
    phi = _phi(ax, ay, bx, by)
    e.x, e.y = punkt_spiegeln(e.x, e.y, ax, ay, bx, by)
    e.winkel = (2 * phi - e.winkel + 180.0) % 360.0
    e.gespiegelt = not e.gespiegelt
    e.sp_dx, e.sp_dy = punkt_spiegeln(e.sp_dx, e.sp_dy, 0.0, 0.0,
                                      bx - ax, by - ay)


def _sp_pos(e, ax, ay, bx, by):
    e.x, e.y = punkt_spiegeln(e.x, e.y, ax, ay, bx, by)


def _sp_qv(e, ax, ay, bx, by):
    _sp_pos(e, ax, ay, bx, by)
    e.richtung = _r90(2 * _phi(ax, ay, bx, by) - e.richtung)


def _sp_verbindung(e, ax, ay, bx, by):
    _sp_pos(e, ax, ay, bx, by)
    phi = _phi(ax, ay, bx, by)
    s_alt = e.ausrichtung * 90 + 90
    e.arme = Verbindung.arme_normieren([2 * phi - d for d in e.arme])
    e.ausrichtung = (_r90(2 * phi - s_alt) - 90) // 90 % 4


def _sp_kabel(e, ax, ay, bx, by):
    x1, y1 = punkt_spiegeln(e.x, e.y, ax, ay, bx, by)
    x2, _ = punkt_spiegeln(e.x + e.laenge, e.y, ax, ay, bx, by)
    e.x, e.y = min(x1, x2), y1


def _sp_kf(e, ax, ay, bx, by):
    x1, y1 = punkt_spiegeln(e.x, e.y, ax, ay, bx, by)
    x2, y2 = punkt_spiegeln(e.x + e.breite, e.y + e.hoehe, ax, ay, bx, by)
    e.x, e.y = min(x1, x2), min(y1, y2)


_inst(Element, skalieren=lambda e, cx, cy, f: None,
      spiegeln=lambda e, ax, ay, bx, by: None)
_inst(Linie, skalieren=_sk_linie, spiegeln=_sp_linie)
_inst(Kreis, skalieren=_sk_kreis, spiegeln=_sp_kreis)
_inst(Bogen, skalieren=_sk_kreis, spiegeln=_sp_bogen)
_inst(Rechteck, skalieren=_sk_rechteck, spiegeln=_sp_rechteck)
_inst(Polylinie, skalieren=_sk_poly, spiegeln=_sp_poly)


def _sk_ellipse(e, cx, cy, f):
    e.cx, e.cy = _skal_pt(e.cx, e.cy, cx, cy, f)
    e.a *= f
    e.b *= f
    e.neu_berechnen()


def _sp_ellipse(e, ax, ay, bx, by):
    e.cx, e.cy = punkt_spiegeln(e.cx, e.cy, ax, ay, bx, by)
    e.rot = (2 * _phi(ax, ay, bx, by) - e.rot) % 360.0
    e.neu_berechnen()


def _sk_spline(e, cx, cy, f):
    e.stuetz = [_skal_pt(x, y, cx, cy, f) for (x, y) in e.stuetz]
    e.neu_berechnen()


def _sp_spline(e, ax, ay, bx, by):
    e.stuetz = [punkt_spiegeln(x, y, ax, ay, bx, by) for (x, y) in e.stuetz]
    e.neu_berechnen()


_inst(Ellipse, skalieren=_sk_ellipse, spiegeln=_sp_ellipse)
_inst(Spline, skalieren=_sk_spline, spiegeln=_sp_spline)
_inst(Text, skalieren=_sk_text, spiegeln=_sp_text)
_inst(Schraffur, skalieren=_sk_schraffur, spiegeln=_sp_schraffur)
_inst(Bemassung, skalieren=_sk_bem, spiegeln=_sp_bem)
_inst(BlockReferenz, skalieren=_sk_block, spiegeln=_sp_block)
_inst(Querverweis, skalieren=_sk_pos, spiegeln=_sp_qv)
_inst(Verbindung, skalieren=_sk_pos, spiegeln=_sp_verbindung)
_inst(_FestMaske, skalieren=_sk_pos, spiegeln=_sp_pos)
_inst(Kabel, skalieren=_sk_kabel, spiegeln=_sp_kabel)
_inst(Koordinatenfeld, skalieren=_sk_kf, spiegeln=_sp_kf)
_inst(Bild, skalieren=_sk_kf, spiegeln=_sp_kf)
