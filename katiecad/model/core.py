# -*- coding: utf-8 -*-
"""
katiecad/model/core.py - Datenmodell, Geometrie und PDF-Ausgabe.
Enthaelt KEIN Tkinter und keine GUI-Logik.

NEU (Block-Unterstuetzung, Schritt 1):
  - BlockDefinition   Vorlage eines Blocks (Name + Elemente relativ zum Basispunkt)
  - BlockReferenz     Eingefuegter Block (Position, Skalierung, Winkel + tiefe Kopie)
  - BlockBibliothek   Globale, zeichnungsuebergreifende Blockbibliothek (blocks.json)
  - BEFEHLE erweitert: BLOCK/B, INSERT/I, BLOCKLISTE/BL
NEU: Radius- und Durchmesser-Bemaßung (DIMRADIUS/DIMDIAMETER).
NEU (Elektro-Basis): AttributDefinition + BlockReferenz.attribute
     (Funktionstexte wie Name, Geraetetyp, Leistung ...).
"""

import math, sys, zlib
from copy import deepcopy

from katiecad.common.i18n import tr, SPRACHE


# ============================================================
# Farbschema
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
# Konstanten
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
# Oberflaechen-Schrift je Plattform (Segoe UI gibt es nur unter Windows)
UI_SCHRIFT = ("Segoe UI" if sys.platform.startswith("win")
              else "Helvetica Neue" if sys.platform == "darwin"
              else "DejaVu Sans")
TEXT_ZEILE = 1.65
CAD_VERSALHOEHE = 0.72
LW_PX_FAKTOR = 6.5
BEM_RICHTUNGEN = ("horizontal", "vertikal", "ausgerichtet",
                  "radius", "durchmesser")

# Toleranz fuer "Punkt liegt auf Objekt" (in Modell-mm)
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
# Geometrie-Hilfen
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
    """Dreht (px, py) um (cx, cy) um winkel_deg.

    ACHTUNG Konvention: Das Modell hat Y nach oben; diese Formel dreht dort
    bei POSITIVEM winkel_deg im UHRZEIGERSINN. Die Dreh-Werkzeuge uebergeben
    deshalb -winkel (CCW-Wunsch). Alle drehen()-Methoden, die zusaetzlich ein
    Winkelfeld pflegen (Text, Bogen, Schraffur, Block, Querverweis), muessen
    das Feld daher mit  `- winkel_deg`  fortschreiben; die Winkelfelder selbst
    sind ueberall mathematisch (gegen den Uhrzeigersinn positiv)."""
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
    """Anzeige eines Verweisziels. o = Blattnummer oder (Blatt, "Spalte/Zeile").
    Beispiel: (1, "3/B") -> "1/3/B"; (2, "") -> "2"."""
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
# NEU: Stutzen (TRIM) und Brechen (BREAK) - Geometrie-Helfer
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
# Befehlszeile (beide Sprachen immer verfügbar)
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
    "RECHTECK": "tool:rechteck", "REC": "tool:rechteck", "RECTANG": "tool:rechteck",
    "TEXT": "tool:text", "T": "tool:text",
    "BEMASSUNG": "tool:bemassung", "BEM": "tool:bemassung", "DIM": "tool:bemassung",
    # NEU: Spezial-Bemaßung Radius / Durchmesser
    "DIMRADIUS":   "bem:radius", "DR": "bem:radius",
    "RADIUS":      "bem:radius", "RBEM": "bem:radius",
    "DIMDIAMETER": "bem:durchmesser", "DD": "bem:durchmesser",
    "DURCHMESSER": "bem:durchmesser", "DIA": "bem:durchmesser",
    "STUTZEN": "tool:stutzen", "TRIM": "tool:stutzen", "TR": "tool:stutzen",
    "BRECHEN": "tool:brechen", "BREAK": "tool:brechen", "BR": "tool:brechen",
    # --- NEU: Blockbefehle ---
    "BLOCK": "block:neu", "B": "block:neu", "BLOCKNEU": "block:neu",
    "INSERT": "block:einfuegen", "EINFUEGENBLOCK": "block:einfuegen",
    "I": "block:einfuegen", "BLOCKEINFUEGEN": "block:einfuegen",
    "BLOCKLISTE": "block:liste", "BL": "block:liste",
    "BLOCKVERWALTEN": "block:liste",
    # --- NEU: Block aufloesen (EXPLODE) ---
    "EXPLODE": "block:explode", "X": "block:explode",
    "AUFLOESEN": "block:explode", "BLOCKAUFLOESEN": "block:explode",
}


# ============================================================
# Minimaler PDF-Schreiber
# ============================================================
_HELV = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
         556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
         1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
         667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
         333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
         556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]


def pdf_textbreite(s, schriftgroesse):
    w = 0
    for ch in s:
        o = ord(ch)
        if 32 <= o <= 126:
            w += _HELV[o - 32]
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
        self.ops.append(" ".join(o))

    def flaeche(self, pts, farbe="#000000"):
        if len(pts) < 3:
            return
        r, g, b = _pdf_rgb(farbe)
        o = ["q", "%.4f %.4f %.4f rg" % (r, g, b), "%.4f %.4f m" % pts[0]]
        for p in pts[1:]:
            o.append("%.4f %.4f l" % p)
        o.append("f")
        o.append("Q")
        self.ops.append(" ".join(o))

    def text(self, x, y, inhalt, hoehe, winkel=0.0, farbe="#000000", mitte=False):
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
                w = pdf_textbreite(z, fs)
                ox -= ex[0] * w / 2 + ey[0] * hoehe / 2
                oy -= ex[1] * w / 2 + ey[1] * hoehe / 2
            self.ops.append(
                "BT /F1 %.4f Tf %.4f %.4f %.4f rg %.6f %.6f %.6f %.6f %.4f %.4f Tm (%s) Tj ET"
                % (fs, r, g, b, ex[0], ex[1], -ex[1], ex[0], ox, oy, _pdf_str(z)))

    def to_bytes(self):
        return pdf_mehrseitig([self])


def pdf_mehrseitig(seiten):
    """Schreibt eine PDF-Datei mit einer Seite pro PdfSeite-Objekt."""
    if not seiten:
        raise ValueError("Keine Seiten")
    n = len(seiten)
    objs = {}
    kids = " ".join("%d 0 R" % (4 + 2 * i) for i in range(n))
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, n)).encode("latin-1")
    objs[3] = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
               b"/Encoding /WinAnsiEncoding >>")
    for i, sp in enumerate(seiten):
        pid, cid = 4 + 2 * i, 5 + 2 * i
        inhalt = ("%.9f 0 0 %.9f 0 0 cm\n" % (sp.MM, sp.MM)
                  + "\n".join(sp.ops)).encode("latin-1")
        strom = zlib.compress(inhalt)
        w, h = sp.b * sp.MM, sp.h * sp.MM
        objs[pid] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.3f %.3f] "
                     "/Contents %d 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
                     % (w, h, cid)).encode("latin-1")
        objs[cid] = (b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(strom)
                     + strom + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offs = []
    total = 3 + 2 * n
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
# Layer
# ============================================================
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
# Elemente
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
        """Startpunkt, Bogenmitte und Endpunkt in Modellkoordinaten."""
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
        """Kreisbogen durch Start s_, Mitte m_ und Ende e_ (wie AutoCAD:
        zwei Punkte bleiben stehen, der gezogene bestimmt Radius/Lage)."""
        ax, ay = s_
        bx, by = m_
        qx, qy = e_
        d = 2.0 * (ax * (by - qy) + bx * (qy - ay) + qx * (ay - by))
        if abs(d) < 1e-9:
            return False                        # (fast) gerade - kein Kreis
        a2, b2, q2 = ax * ax + ay * ay, bx * bx + by * by, qx * qx + qy * qy
        ux = (a2 * (by - qy) + b2 * (qy - ay) + q2 * (ay - by)) / d
        uy = (a2 * (qx - bx) + b2 * (ax - qx) + q2 * (bx - ax)) / d
        r = math.hypot(ax - ux, ay - uy)
        if not (1e-6 < r < 1e7):
            return False
        a_s = math.degrees(math.atan2(ay - uy, ax - ux))
        a_e = math.degrees(math.atan2(qy - uy, qx - ux))
        # Durchlaufsinn s -> m -> e: > 0 = gegen den Uhrzeigersinn
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
            if voll:                            # Vollkreis: Radius / Winkel
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
        self.x1, self.y1 = punkte_drehen(self.x1, self.y1, cx, cy, winkel_deg)
        self.x2, self.y2 = punkte_drehen(self.x2, self.y2, cx, cy, winkel_deg)


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
        # Echte Zeichenbreiten (Helvetica/Arial-Metrik, identisch zum PDF):
        # "A" ist breiter als "1". Eine feste Breite pro Zeichen liess Texte
        # ueber den Einfuegepunkt hinausragen.
        fs = self.hoehe / CAD_VERSALHOEHE
        w = max(max(pdf_textbreite(z, fs) for z in zeilen),
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
                 text_offset_x=0.0, text_offset_y=0.0, **kw):
        super().__init__("bemassung", **kw)
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
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

        # NEU: Wenn die Linie schräg ist, nehmen wir automatisch den Winkel der Linie
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

    def wert(self):
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

        # ---------- Radius / Durchmesser ----------
        C, P = (self.x1, self.y1), (self.x2, self.y2)
        rad = math.hypot(P[0] - C[0], P[1] - C[1])
        if rad < 1e-9:
            return res
        u = ((P[0] - C[0]) / rad, (P[1] - C[1]) / rad)

        if r == "radius":
            # Kleines Mittelkreuz (proportional, aber nicht größer als der Kreis)
            k = min(0.5 * h, rad * 0.4)
            res["linien"].append((C[0] - k, C[1], C[0] + k, C[1]))
            res["linien"].append((C[0], C[1] - k, C[0], C[1] + k))

            # Messlinie vom Zentrum zum Bogenpunkt
            res["linien"].append((C[0], C[1], P[0], P[1]))

            # Pfeil am Bogen, zeigt nach außen (zur Messstelle)
            res["pfeile"].append((P[0], P[1], math.atan2(u[1], u[0]), pf))

            # Textposition: manuell (tx/ty) oder aus mx/my
            if manuell:
                c = (self.tx, self.ty)
            else:
                c = (self.mx, self.my)
                d_center = math.hypot(c[0] - C[0], c[1] - C[1])
                if d_center < h:
                    c = (P[0] + u[0] * (tgap + h),
                         P[1] + u[1] * (tgap + h))

            # Führungslinie, wenn der Text außerhalb des Bogens steht
            d_p = math.hypot(c[0] - P[0], c[1] - P[1])
            if d_p > h * 0.8:
                res["linien"].append((P[0], P[1], c[0], c[1]))

            res["text"] = (txt, c[0], c[1], 0.0, tw, h)
            res["mitte"] = ((C[0] + P[0]) / 2, (C[1] + P[1]) / 2)

        else:  # durchmesser
            Q = (2 * C[0] - P[0], 2 * C[1] - P[1])

            # Linie durch den ganzen Kreis, Pfeile an beiden Enden
            res["linien"].append((P[0], P[1], Q[0], Q[1]))
            res["pfeile"].append((P[0], P[1], math.atan2(u[1], u[0]), pf))
            res["pfeile"].append((Q[0], Q[1], math.atan2(-u[1], -u[0]), pf))

            # Textschräge an die Messlinie anpassen (in [-90, +90])
            a_deg = math.degrees(math.atan2(u[1], u[0]))
            if a_deg > 90.0 + 1e-9:
                a_deg -= 180.0
            elif a_deg <= -90.0 + 1e-9:
                a_deg += 180.0
            ar = math.radians(a_deg)
            up = (-math.sin(ar), math.cos(ar))   # senkrecht zur Messlinie

            # Textposition: bei manuell tx/ty, sonst mittig über/unter Zentrum
            if manuell:
                c = (self.tx, self.ty)
            else:
                # Seite anhand der Maus-Klickposition bestimmen
                seite = 1.0 if ((self.mx - C[0]) * up[0] +
                                (self.my - C[1]) * up[1]) >= 0 else -1.0
                c = (C[0] + up[0] * (tgap + h / 2) * seite,
                     C[1] + up[1] * (tgap + h / 2) * seite)

            # Führungslinie vom nächstgelegenen Pfeil zum Text,
            # wenn der Text außerhalb des Kreises liegt
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
        self.mx += dx; self.my += dy
        if self.tx is not None and self.ty is not None:
            self.tx += dx; self.ty += dy

    def griffe(self):
        g = self.geometrie()
        mx, my = g["mitte"] if g["mitte"] else (self.mx, self.my)
        gr = [("p1", self.x1, self.y1), ("p2", self.x2, self.y2),
              ("mass", mx, my)]
        if g["text"]:
            gr.append(("text", g["text"][1], g["text"][2]))
        return gr

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p1":
            self.x1, self.y1 = x, y
        elif griff_id == "p2":
            self.x2, self.y2 = x, y
        elif griff_id == "mass":
            self.mx, self.my = x, y
        elif griff_id == "text":
            self.tx, self.ty = x, y

    def drehen(self, cx, cy, winkel_deg):
        self.x1, self.y1 = punkte_drehen(self.x1, self.y1, cx, cy, winkel_deg)
        self.x2, self.y2 = punkte_drehen(self.x2, self.y2, cx, cy, winkel_deg)
        self.mx, self.my = punkte_drehen(self.mx, self.my, cx, cy, winkel_deg)
        if self.tx is not None and self.ty is not None:
            self.tx, self.ty = punkte_drehen(self.tx, self.ty, cx, cy, winkel_deg)
        if self.richtung in ("horizontal", "vertikal"):
            self.richtung = "ausgerichtet"


class Viewport(Element):
    def __init__(self, x, y, breite, hoehe,
                 modell_zentrum_x=0.0, modell_zentrum_y=0.0,
                 zoom=1.0, gesperrt=False, **kw):
        super().__init__("viewport", **kw)
        self.x, self.y = x, y
        self.breite, self.hoehe = breite, hoehe
        self.modell_zentrum_x = modell_zentrum_x
        self.modell_zentrum_y = modell_zentrum_y
        self.zoom = zoom
        self.gesperrt = bool(gesperrt)
        self.aktiv = False

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
# NEU: Block-Unterstuetzung
# ============================================================
class AttributDefinition(Text):
    """Attributdefinition (wie ATTDEF in AutoCAD).

    Ein Text, der Teil einer Blockdefinition wird. Beim Einfuegen des
    Blocks bekommt jede Referenz einen eigenen Wert pro Attribut-Tag
    (z.B. NAME, GERAETETYP, LEISTUNG), der spaeter editierbar ist.

    Im normalen Zeichnungsbereich wird nur der Tag als Platzhalter
    angezeigt; in einer BlockReferenz wird stattdessen der Wert
    dargestellt (siehe BlockReferenz.aufgeloest()).
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
        """Normales Text-Element mit dem gegebenen Wert (oder None, wenn
        das Attribut unsichtbar oder leer ist)."""
        if not self.sichtbar or wert is None or str(wert) == "":
            return None
        return Text(self.x, self.y, str(wert), self.hoehe, self.winkel,
                    self.schriftart, einfuegepunkt=self.einfuegepunkt,
                    layer=self.layer, farbe=self.farbe,
                    linientyp=self.linientyp, eig_farbe=self.eig_farbe,
                    staerke=self.staerke)


def _attribut_defs(elemente):
    """AttributDefinitionen + feste Felder (IND/TYP/PER/NUM) von Masken."""
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
    """Benannte Vorlage eines Blocks.

    Die Elemente werden in *lokalen* Koordinaten gespeichert, d.h.
    bereits relativ zum Basispunkt (Basispunkt = (0, 0) im lokalen System).
    Das erleichtert das spaetere Transformieren beim Einfuegen enorm.
    """

    def __init__(self, name, basispunkt, elemente):
        self.name = name
        self.basispunkt = tuple(basispunkt)
        self.elemente = list(elemente)

    def attribut_definitionen(self):
        """Alle Attribute dieser Blockdefinition (inkl. der festen Felder
        von Elektro-Maske / Klemme)."""
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
    """Ein eingefuegter Block.

    Haelt eine *tiefe Kopie* der Definitionselemente (relativ zum
    Basispunkt). So bleibt die Zeichnung autark und Aenderungen an der
    Definition wirken sich nicht rueckwirkend auf platzierte Instanzen aus
    (bewusst einfach gehalten - echtes AutoCAD verhaelt sich anders, aber
    fuer unsere Zwecke ist diese Semantik klarer und robuster).
    """

    def __init__(self, x, y, block_name, elemente,
                 skalierung=1.0, winkel=0.0, attribute=None,
                 ausgeblendet=None, **kw):
        super().__init__("block", **kw)
        self.x, self.y = x, y
        self.block_name = block_name
        # tiefe Kopie, damit die Referenz wirklich eigenstaendig ist
        self.elemente = [deepcopy(e) for e in elemente]
        self.skalierung = float(skalierung) if skalierung else 1.0
        self.winkel = float(winkel) if winkel else 0.0
        # Attributwerte dieser Instanz: {TAG: Wert}
        self.attribute = dict(attribute) if attribute else {}
        for ad in self.attribut_definitionen():
            self.attribute.setdefault(ad.tag, ad.wert)
        # Tags, deren Text in DIESER Instanz nicht angezeigt wird
        self.ausgeblendet = set(ausgeblendet or [])
        self._cache = None          # (Signatur, aufgeloeste Kinder)
        self.refs = []              # Geraete-Verweise (Blattnummern), berechnet

    # ---- Attribute ---------------------------------------------
    def attribut_definitionen(self):
        return _attribut_defs(self.elemente)

    def geraet_maske(self):
        """Elektro-Maske dieses Blocks (Geraet) oder None."""
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
        """Uebernimmt Werte {TAG: Wert} (nur bekannte Tags)."""
        bekannt = {ad.tag for ad in self.attribut_definitionen()}
        for tag, wert in werte.items():
            if tag in bekannt:
                self.attribute[tag] = str(wert)

    # ---- Transformation ----------------------------------------
    def _welt_pts(self, lx, ly):
        """Lokale Koordinaten (relativ zum Basispunkt) -> Weltkoordinaten.
        Beruecksichtigt Skalierung, Drehung (positiver Winkel = gegen den
        Uhrzeigersinn, wie bei Text-/Bogenwinkeln) und Translation."""
        s = self.skalierung
        a = math.radians(self.winkel)
        ca, sa = math.cos(a), math.sin(a)
        px, py = lx * s, ly * s
        return (self.x + px * ca - py * sa,
                self.y + px * sa + py * ca)

    def _transformiere(self, el):
        """Transformiert ein Kind-Element *in place* vom lokalen ins
        Weltkoordinatensystem."""
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
            # Gedrehtes Rechteck -> Polylinie (achsenparalleles Rechteck
            # kann nach Drehung nicht mehr als Rechteck dargestellt werden)
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
        elif isinstance(el, Text):
            el.x, el.y = self._welt_pts(el.x, el.y)
            el.hoehe *= self.skalierung
            el.winkel = (el.winkel + self.winkel) % 360.0
            if isinstance(el, Verbindungspunkt):
                el.radius *= self.skalierung
        elif isinstance(el, Querverweis):
            el.x, el.y = self._welt_pts(el.x, el.y)
            el.richtung = round((el.richtung + self.winkel) / 90.0) * 90 % 360
        elif isinstance(el, Schraffur):
            # (fehlte bisher: Schraffuren blieben beim Einfuegen am Ursprung)
            el.punkte = [self._welt_pts(x, y) for (x, y) in el.punkte]
            el.winkel = (el.winkel + self.winkel) % 360.0
            el.abstand *= self.skalierung
        elif isinstance(el, (_FestMaske, Koordinatenfeld)):
            el.x, el.y = self._welt_pts(el.x, el.y)      # Texte bleiben waagerecht
        elif isinstance(el, Verbindung):
            el.x, el.y = self._welt_pts(el.x, el.y)
            el.ausrichtung = (el.ausrichtung + int(round(self.winkel / 90.0))) % 4
        elif isinstance(el, Bemassung):
            el.x1, el.y1 = self._welt_pts(el.x1, el.y1)
            el.x2, el.y2 = self._welt_pts(el.x2, el.y2)
            el.mx, el.my = self._welt_pts(el.mx, el.my)
            if el.tx is not None and el.ty is not None:
                el.tx, el.ty = self._welt_pts(el.tx, el.ty)
            el.hoehe *= self.skalierung
            el.pfeil *= self.skalierung
            # Richtung "horizontal"/"vertikal" wird nach Drehung zu
            # "ausgerichtet", sonst wuerde sie falsch aussehen.
            if self.winkel % 360.0 not in (0.0, 180.0):
                if el.richtung in ("horizontal", "vertikal"):
                    el.richtung = "ausgerichtet"

    def aufgeloest(self):
        """Liefert die transformierten Kind-Elemente als flache Liste."""
        # Ergebnis wird zwischengespeichert: Snap, Zeichnen und Treffertests
        # rufen das pro Mausbewegung auf - ohne Cache entstehen dabei
        # tausende tiefe Kopien (Speicherdruck bei vielen Symbolen).
        # Die Liste ist NUR LESEND zu verwenden (Aufloesen: vorher kopieren).
        sig = (self.x, self.y, self.skalierung, self.winkel,
               tuple(sorted(self.attribute.items())),
               tuple(sorted(self.ausgeblendet)), tuple(self.refs))
        if self._cache is not None and self._cache[0] == sig:
            return self._cache[1]
        out = []
        for el in self.elemente:
            k = deepcopy(el)
            self._transformiere(k)
            if isinstance(k, _FestMaske):
                # Maske/Klemme: Werte kommen aus den Attributen der Instanz
                k.werte = {t: str(self.attribute.get(t, k.werte.get(t, "")))
                           for t in k.FELDER}
                k.ausgeblendet = set(self.ausgeblendet) & set(k.FELDER)
                k.refs = list(self.refs)
                k.platzhalter = False
                out.append(k)
                continue
            if isinstance(k, Verbindungspunkt):
                # Verbindungspunkt: Kreis + Beschriftung bleiben ein Element,
                # die Beschriftung kommt aus dem Attributwert der Instanz.
                k.wert = str(self.attribute.get(k.tag, k.wert))
                k.inhalt = k.wert
                if k.tag in self.ausgeblendet:
                    k.sichtbar = False
                out.append(k)
                continue
            if isinstance(k, AttributDefinition):
                if k.tag in self.ausgeblendet:
                    continue
                k = k.als_text(self.attribute.get(k.tag, k.wert))
                if k is None:
                    continue
            out.append(k)
        self._cache = (sig, out)
        return out

    # ---- Element-API -------------------------------------------
    def bbox(self):
        xs, ys = [], []
        for el in self.elemente:
            if isinstance(el, AttributDefinition) and not el.sichtbar:
                continue
            b = el.bbox()
            for (lx, ly) in ((b[0], b[1]), (b[2], b[1]),
                             (b[2], b[3]), (b[0], b[3])):
                wx, wy = self._welt_pts(lx, ly)
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
        return [("p", self.x, self.y)]

    def griff_bewegen(self, griff_id, x, y):
        self.x, self.y = x, y

    def to_dict(self):
        d = super().to_dict()
        d.pop("_cache", None)
        d.pop("refs", None)
        d["ausgeblendet"] = sorted(self.ausgeblendet)
        # Kinder als dicts ablegen (nicht die Objekte selbst)
        d["elemente"] = [e.to_dict() for e in self.elemente]
        return d


# ============================================================
# NEU: Globale Blockbibliothek (blocks.json)
# ============================================================
class BlockBibliothek:
    """Zeichnungsuebergreifende Blockbibliothek.

    Speichert Blockdefinitionen in einer benutzerspezifischen JSON-Datei
    (analog zu katiecad/common/config.py). Beim Start werden bestehende Bloecke
    geladen; bei Aenderungen wird die Datei sofort aktualisiert.
    """

    DATEI = "blocks.json"

    def __init__(self, element_factory):
        self._element_factory = element_factory
        self._definitionen = {}
        self._laden()

    # ---- Pfad (plattformgerecht, gleiche Logik wie katiecad.common.config) ----
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
    """Schraffur ueber einer geschlossenen Kontur.

    WICHTIG: Der Elementtyp (self.typ) bleibt "schraffur", damit
    Speichern/Laden/Kopieren/Undo (_dict_zu_element) das Element
    erkennen. Das Fuellmuster steht in self.muster ("solid"/"linien").
    Der Parameter `typ="solid"|"linien"` wird aus Kompatibilitaetsgruenden
    (alter Import-Code, alte Dateien) weiterhin als Alias akzeptiert.
    """
    MUSTER = ("solid", "linien")

    def __init__(self, punkte, muster="solid", winkel=45.0, abstand=5.0,
                 typ=None, **kw):
        super().__init__("schraffur", **kw)
        if typ in self.MUSTER:          # Alias / Altformat
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
        """Berechnet die Schnittpunkte fuer die Linien-Schraffur (Scanline)."""
        if self.muster != "linien" or len(self.punkte) < 3:
            return []
        abstand = max(float(self.abstand or 0), 0.05)   # Endlosschleife vermeiden

        # Die Scanlines laufen im gedrehten System waagerecht. Hin-Drehung
        # um -winkel, Rueck-Drehung um +winkel => Linienrichtung (cos w, sin w),
        # d.h. 45 Grad zeigt bei y-oben nach rechts oben ("/").
        rad = math.radians(self.winkel)
        ca, sa = math.cos(rad), math.sin(rad)
        rot_pts = [(x * ca + y * sa, -x * sa + y * ca) for (x, y) in self.punkte]
        min_y = min(p[1] for p in rot_pts)
        max_y = max(p[1] for p in rot_pts)
        if (max_y - min_y) / abstand > 20000:           # absurd dichte Schraffur
            return []

        rad_back = math.radians(-self.winkel)
        cb, sb = math.cos(rad_back), math.sin(rad_back)
        linien = []
        # halber Abstand als Start: Linien liegen nicht exakt auf Eckpunkten
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
# Konturerkennung fuer Schraffuren
# ------------------------------------------------------------
def _kreis_polygon(cx, cy, r, n=None):
    if n is None:
        n = int(max(48, min(360, r * 4)))
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def konturen_aus_elementen(elemente, tol=0.05):
    """Findet geschlossene Konturen in einer Elementliste.

    Rueckgabe: Liste von (punkte, quell_elemente).
      - Kreis, Rechteck, geschlossene Polylinie -> je eine eigene Kontur
      - Linie, Bogen, offene Polylinie          -> werden an ihren
        Endpunkten (Abstand <= tol) zu Ketten verbunden; nur Ketten,
        die sich schliessen, ergeben eine Kontur.
    """
    ergebnis = []
    offene = []                                   # (punkte, quelle)
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
# Layout (ein Zeichnungsblatt mit eigenem Format, Hintergrund
# und eigenen Layout-Elementen — analog zu AutoCAD-Layouts)
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
# NEU (Elektro): Leitung, Verbindungspunkt, Querverweis
# ============================================================
LEITUNG_FARBE = "#ff0000"
# ANNAHME: 0.35 mm (Standard-Strichstaerke). Wunsch war "3.5" - das waere eine
# 3.5 mm breite Linie. Hier zentral aendern, falls wirklich gewollt.
LEITUNG_STAERKE = 0.35


class Leitung(Linie):
    """Rote Verbindungslinie zwischen zwei Anschlusspunkten.
    auto=True: wird automatisch erzeugt/entfernt (siehe
    katiecad.electrical.logic.leitungen_automatisch)."""

    def __init__(self, x1, y1, x2, y2, auto=False, **kw):
        kw.setdefault("farbe", LEITUNG_FARBE)
        kw.setdefault("eig_farbe", True)
        kw.setdefault("staerke", LEITUNG_STAERKE)
        super().__init__(x1, y1, x2, y2, **kw)
        self.typ = "leitung"
        self.auto = bool(auto)


class Verbindungspunkt(AttributDefinition):
    """Anschlusspunkt: Kreis (Durchmesser 1 mm) + Beschriftung rechts davon
    (Texthoehe 2.0 mm).

    Der Kreis wird nur im Modell gezeichnet; Layout und PDF zeigen nur die
    Beschriftung. In Bloecken verhaelt er sich wie ein Attribut: der Text
    (self.wert) ist je Blockinstanz editierbar.
    """
    DURCHMESSER = 1.0
    TEXT_HOEHE = 2.0
    TEXT_ABSTAND = 1.0          # Abstand Kreisrand -> Text (mm)

    def __init__(self, x, y, inhalt=None, hoehe=2.0, winkel=0.0,
                 schriftart="Arial", einfuegepunkt=None, tag="VP",
                 prompt="", wert="", sichtbar=True, radius=0.5, **kw):
        super().__init__(x, y, inhalt, hoehe, winkel, schriftart,
                         "mitte_links", tag=tag, prompt=prompt, wert=wert,
                         sichtbar=sichtbar, **kw)
        self.typ = "vpunkt"
        self.radius = float(radius)
        self.wert = "" if wert is None else str(wert)
        self.inhalt = self.wert

    def text_element(self):
        """Beschriftung als normales Text-Element (oder None)."""
        if not self.sichtbar or self.wert == "":
            return None
        a = math.radians(self.winkel)
        d = self.radius + self.TEXT_ABSTAND
        return Text(self.x + d * math.cos(a), self.y + d * math.sin(a),
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
        """Treffer auf den Kreis oder die Beschriftung."""
        if math.hypot(x - self.x, y - self.y) <= max(self.radius, tol):
            return True
        t = self.text_element()
        return bool(t and t.punkt_im_rahmen(x, y, tol))


def vp_tags_eindeutig(elemente):
    """Vergibt fuer alle Verbindungspunkte einer Blockdefinition eindeutige
    Tags (VP1, VP2, ...), damit jeder einen eigenen Wert je Instanz hat."""
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
    """Pfeilsymbol fuer Verweise zwischen Stromlaufplan-Blaettern.

    Pfeil 2 x 5 mm, Einfuegepunkt = Mitte der Pfeilbasis.
    richtung: 0 = Ost, 90 = Nord, 180 = West, 270 = Sued (Pfeilspitze).
    art:      "abgehend"  -> Text hinter der Pfeilspitze
              "ankommend" -> Text hinter der Pfeilbasis
    text:     editierbare Kennung (z. B. "L1")
    ziel:     (nicht gespeichert) Blattnummern der Gegenstuecke mit gleichem
              Text; wird von der Anwendung berechnet.
    """
    ARTEN = ("abgehend", "ankommend")
    BREITE = 2.0
    LAENGE = 5.0
    ABSTAND = 1.0
    TEXT_HOEHE = 2.0            # Kennung
    ZIEL_HOEHE = 1.0            # Zielangabe
    _VEKTOR = {0: (1.0, 0.0), 90: (0.0, 1.0), 180: (-1.0, 0.0), 270: (0.0, -1.0)}

    def __init__(self, x, y, text="", art="abgehend", richtung=0, **kw):
        kw.setdefault("eig_farbe", True)
        super().__init__("querverweis", **kw)
        self.x, self.y = x, y
        self.text = str(text or "")
        self.art = art if art in self.ARTEN else "abgehend"
        self.richtung = int(round(float(richtung) / 90.0) * 90) % 360
        self.ziel = []

    def to_dict(self):
        d = super().to_dict()
        d.pop("ziel", None)
        return d

    def ziel_text(self):
        if not self.ziel or not self.text.strip():
            return ""
        return "(" + tr("qv.blatt") + " " + ", ".join(ort_text(o) for o in self.ziel) + ")"

    def basis_punkt(self):
        """Anschluss an der Pfeilbasis (= Einfuegepunkt)."""
        return (self.x, self.y)

    def spitze_punkt(self):
        """Anschluss an der Pfeilspitze."""
        dx, dy = self._VEKTOR[self.richtung]
        return (self.x + dx * self.LAENGE, self.y + dy * self.LAENGE)

    def pfeil_punkte(self):
        dx, dy = self._VEKTOR[self.richtung]
        nx, ny = -dy, dx
        h = self.BREITE / 2.0
        return [(self.x + nx * h, self.y + ny * h),
                (self.x - nx * h, self.y - ny * h),
                (self.x + dx * self.LAENGE, self.y + dy * self.LAENGE)]

    def aufgeloest(self):
        """Pfeil (Schraffur solid) + Text(e) als einfache Elemente."""
        out = [Schraffur(self.pfeil_punkte(), "solid", layer=self.layer,
                         farbe=LEITUNG_FARBE, eig_farbe=True)]
        dx, dy = self._VEKTOR[self.richtung]
        a = 0.0 if self.richtung in (0, 180) else 90.0
        ex, ey = math.cos(math.radians(a)), math.sin(math.radians(a))
        nx, ny = -ey, ex                       # "oben" im Textsystem
        if self.art == "abgehend":
            sx, sy = dx, dy
            qx = self.x + dx * (self.LAENGE + self.ABSTAND)
            qy = self.y + dy * (self.LAENGE + self.ABSTAND)
        else:
            sx, sy = -dx, -dy
            qx = self.x - dx * self.ABSTAND
            qy = self.y - dy * self.ABSTAND
        horiz = "links" if (ex * sx + ey * sy) > 0 else "rechts"
        ziel = self.ziel_text()
        stil = dict(layer=self.layer, farbe=self.farbe,
                    linientyp=self.linientyp, eig_farbe=self.eig_farbe)
        if self.text.strip():
            v = 1.3 if ziel else 0.0
            out.append(Text(qx + nx * v, qy + ny * v, self.text,
                            self.TEXT_HOEHE, a, "Arial",
                            einfuegepunkt="mitte_" + horiz, **stil))
        if ziel:
            v = -1.1
            out.append(Text(qx + nx * v, qy + ny * v, ziel,
                            self.ZIEL_HOEHE, a, "Arial",
                            einfuegepunkt="mitte_" + horiz, **stil))
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

    def griffe(self):
        return [("p", self.x, self.y)]

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p":
            self.x, self.y = x, y



# ============================================================
# NEU (Elektro): Verbindung, Elektro-Maske, Klemme
# ============================================================
class Verbindung(Element):
    """Leitungsverbindung (rot, gehoert fest zur Leitung) mit 2, 3 oder 4
    Anschluessen wie in Eplan.

    art 2: Ecke      - Arme in zwei benachbarte Richtungen
    art 3: T-Stueck  - drei Arme, einer fehlt
    art 4: Kreuzung  - vier Arme, optional mit Punkt (= verbunden)
    ausrichtung (0..3, gegen den Uhrzeigersinn, 0 = Ost):
        art 2: Arme bei  a*90  und  a*90+90
        art 3/4: gerader Arm bei a*90, Knickarm gegenueber (siehe _lokal)
    Die Armenden sind die Anschlusspunkte fuer Leitungen."""
    ARM = 2.5
    PUNKT_RADIUS = 1.25
    ARTEN = (2, 3, 4)
    _V = {0: (1.0, 0.0), 90: (0.0, 1.0), 180: (-1.0, 0.0), 270: (0.0, -1.0)}

    def __init__(self, x, y, art=2, ausrichtung=0, punkt=True, **kw):
        kw.setdefault("farbe", LEITUNG_FARBE)
        kw.setdefault("eig_farbe", True)
        kw.setdefault("staerke", LEITUNG_STAERKE)
        super().__init__("verbindung", **kw)
        self.x, self.y = float(x), float(y)
        self.art = int(art) if int(art) in self.ARTEN else 2
        self.ausrichtung = int(ausrichtung) % 4
        self.punkt = bool(punkt)

    def _lokal(self):
        """Linienzuege (lokal, ausrichtung 0) und Armenden (x, y, richtung)
        wie in Eplan. U = ARM.
        art 2: Ecke (Arme Ost + Nord)
        art 3/4 ohne Punkt: gerader Arm nach Ost, gegenueberliegender Arm
          laeuft mit einem Knick (45 Grad) auf die senkrechte Durchgangs-
          linie; art 3 hat die Durchgangslinie nur nach Nord, art 4 nach
          Nord und Sued.  Ausrichtung dreht das Ganze um a*90 Grad.
        art 4 mit Punkt: Kreuz mit ausgefuelltem Punkt."""
        u = self.ARM
        if self.art == 2:
            return ([[(u, 0.0), (0.0, 0.0), (0.0, u)]],
                    [(u, 0.0, 0), (0.0, u, 90)])
        if self.art == 4 and self.punkt:
            return ([[(u, 0.0), (-u, 0.0)], [(0.0, u), (0.0, -u)]],
                    [(u, 0.0, 0), (0.0, u, 90), (-u, 0.0, 180), (0.0, -u, 270)])
        zuege = [[(0.0, 0.0), (u, 0.0)],                      # gerader Arm
                 [(-u, 0.0), (-0.5 * u, 0.0), (0.0, 0.5 * u)]]  # Knickarm
        enden = [(u, 0.0, 0), (-u, 0.0, 180), (0.0, u, 90)]
        if self.art == 4:
            zuege.append([(0.0, u), (0.0, -u)])
            enden.append((0.0, -u, 270))
        else:
            zuege.append([(0.0, 0.0), (0.0, u)])
        return zuege, enden

    def _welt(self, px, py):
        w = self.ausrichtung * math.pi / 2.0
        c, sn = round(math.cos(w)), round(math.sin(w))
        return (self.x + px * c - py * sn, self.y + px * sn + py * c)

    def arme(self):
        """Richtungen (Grad) der Anschluesse."""
        return [(d + self.ausrichtung * 90) % 360
                for (_x, _y, d) in self._lokal()[1]]

    def anschluesse(self):
        """Armenden (x, y, richtung)."""
        out = []
        for (px, py, d) in self._lokal()[1]:
            wx, wy = self._welt(px, py)
            out.append((wx, wy, (d + self.ausrichtung * 90) % 360))
        return out

    def aufgeloest(self):
        st = dict(layer=self.layer, farbe=self.farbe,
                  linientyp=self.linientyp, eig_farbe=self.eig_farbe,
                  staerke=self.staerke)
        out = []
        for zug in self._lokal()[0]:
            pts = [self._welt(px, py) for (px, py) in zug]
            for a, b in zip(pts, pts[1:]):
                out.append(Linie(a[0], a[1], b[0], b[1], **st))
        if self.art == 4 and self.punkt:
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
        self.ausrichtung = (self.ausrichtung + int(round(-winkel_deg / 90.0))) % 4

    def griffe(self):
        return [("p", self.x, self.y)]

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p":
            self.x, self.y = x, y


class _FestMaske(Element):
    """Basis fuer Elemente mit FEST vorgegebenen Textfeldern (nur ausfuellbar,
    nicht in ihrem Aufbau veraenderbar): Elektro-Maske und Klemme."""
    FELDER = ()
    ZEILEN = ()            # (tag, dx, dy, hoehe, anker)

    def __init__(self, typ, x, y, werte=None, ausgeblendet=None,
                 platzhalter=True, **kw):
        super().__init__(typ, **kw)
        self.x, self.y = float(x), float(y)
        self.werte = {t: "" for t in self.FELDER}
        for t, v in (werte or {}).items():
            if t in self.FELDER:
                self.werte[t] = "" if v is None else str(v)
        self.ausgeblendet = {t for t in (ausgeblendet or []) if t in self.FELDER}
        self.platzhalter = bool(platzhalter)     # leere Felder als <TAG> zeigen
        self.refs = []                           # Blattnummern (berechnet)

    def to_dict(self):
        d = super().to_dict()
        d.pop("refs", None)
        d["werte"] = dict(self.werte)
        d["ausgeblendet"] = sorted(self.ausgeblendet)
        return d

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
        out = []
        for tag, dx, dy, h, anker in self.ZEILEN:
            if tag in self.ausgeblendet:
                continue
            w = self.werte.get(tag, "")
            if w == "":
                if not ph:
                    continue
                w = "<" + tag + ">"
            out.append(Text(self.x + dx, self.y + dy, w, h, 0.0, "Arial",
                            einfuegepunkt=anker, **st))
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
        return [("p", self.x, self.y)]

    def griff_bewegen(self, griff_id, x, y):
        if griff_id == "p":
            self.x, self.y = x, y


class ElektroMaske(_FestMaske):
    """Basis fuer Elektrogeraete: <IND> (2.5), <TYP>, <PER>, <REF> (je 1.5).

    Der Einfuegepunkt (x, y) ist die UNTERE RECHTE Ecke der Maske; alle
    Texte sind rechtsbuendig und wachsen nach oben, damit die Maske an ein
    Symbol 'angehaengt' werden kann.  REF steht ganz unten und waechst mit
    der Zahl der Verweise nach oben (die uebrigen Zeilen ruecken mit).

    IND/TYP/PER werden ausgefuellt. REF entsteht automatisch: Geraete mit
    gleichem PER verweisen aufeinander (Hauptsymbol -> alle Hilfsbausteine,
    Hilfsbaustein -> nur das Hauptsymbol), siehe katiecad.electrical.logic."""
    FELDER = ("IND", "TYP", "PER")
    ROLLEN = ("haupt", "hilfs")
    HOEHEN = {"IND": 2.5, "TYP": 1.5, "PER": 1.5}
    REF_HOEHE = 1.5
    ABSTAND = {"PER": 1.1, "TYP": 2.0, "IND": 3.0}   # Mitte zu Mitte nach oben
    ZEILEN = ()

    def __init__(self, x, y, werte=None, rolle="haupt", **kw):
        super().__init__("maske", x, y, werte, **kw)
        self.rolle = rolle if rolle in self.ROLLEN else "haupt"

    def aufgeloest(self, platzhalter=None):
        """Leere Felder bleiben leer. Nur auf dem Bildschirm (platzhalter)
        erscheint ein kleines Kreuz, solange die Maske gar keinen Text hat,
        damit sie auffindbar und markierbar bleibt. REF erscheint nur, wenn
        es Verweise gibt."""
        ph = self.platzhalter if platzhalter is None else platzhalter
        st = self._stil()
        refs = ["(%s %s)" % (tr("qv.blatt"), ort_text(o)) for o in self.refs]
        ref = Text(self.x, self.y, "\n".join(refs) if refs else "REF",
                   self.REF_HOEHE, 0.0, "Arial",
                   einfuegepunkt="unten_rechts", **st)
        out = [ref] if refs else []
        y = ref.bbox()[3]                # Oberkante der (reservierten) REF-Zeile
        for tag in ("PER", "TYP", "IND"):
            y += self.ABSTAND[tag]       # Mitte der jeweiligen Zeile
            w = self.werte.get(tag, "")
            if tag in self.ausgeblendet or w == "":
                continue
            out.append(Text(self.x, y, w, self.HOEHEN[tag], 0.0, "Arial",
                            einfuegepunkt="mitte_rechts", **st))
        if not out and ph:
            r = 0.8
            out.append(Linie(self.x - r, self.y, self.x + r, self.y, staerke=0.25, **st))
            out.append(Linie(self.x, self.y - r, self.x, self.y + r, staerke=0.25, **st))
        return out


class Klemme(_FestMaske):
    """Klemme: sichtbarer Kreis mit zwei Anschluessen (oben / unten) und den
    festen Feldern <IND> (2.5), <TYP>, <PER> (1.5) und <NUM> (1.0)."""
    FELDER = ("IND", "TYP", "PER", "NUM")
    DURCHMESSER = 2.0
    # Beschriftung: rechtsbuendig direkt links neben dem Kreis. IND steht auf
    # Hoehe der Kreismitte, TYP und PER darunter.
    ZEILEN = (("IND", -3.0, 0.0, 2.5, "mitte_rechts"),
              ("TYP", -3.0, -3.0, 1.5, "mitte_rechts"),
              ("PER", -3.0, -5.5, 1.5, "mitte_rechts"),
              ("NUM", 2.0, 0.0, 1.0, "mitte_links"))

    def __init__(self, x, y, werte=None, **kw):
        super().__init__("klemme", x, y, werte, **kw)

    def aufgeloest(self, platzhalter=None):
        # Leere Felder bleiben leer (Klemmen sollen eng gereiht werden koennen)
        return _FestMaske.aufgeloest(self, False)

    def anschluss_oben(self):
        return (self.x, self.y + self.DURCHMESSER / 2.0)

    def anschluss_unten(self):
        return (self.x, self.y - self.DURCHMESSER / 2.0)

    def _zusatz(self, ph, st):
        return [Kreis(self.x, self.y, self.DURCHMESSER / 2.0,
                      staerke=0.25, **st)]


# Elemente, die sich aus einfachen Elementen zusammensetzen (aufgeloest())
class Koordinatenfeld(Element):
    """Zonenraster (Koordinatensystem) eines Schaltplan-Blattes.

    (x, y) ist die linke untere Ecke des Zeichenbereichs `breite` x `hoehe`
    (Standard: DIN-A4-Blattrahmen ohne Schriftkopf = Viewport-Groesse bei 1:1).
    Oben stehen die Spaltennummern 1..spalten, links die Zeilenbuchstaben
    A.. (A = oben). Der gestrichelte Umriss (nur in der Modellansicht) zeigt
    die Viewport-Flaeche; er erscheint weder im Layout noch im Druck/DXF.
    Das Feld wird nur per Klick auf seinen Rahmen markiert, nie durch ein
    Auswahlrechteck (NUR_KLICK)."""
    NUR_KLICK = True
    INSET = 1.0                       # Abstand Rahmen <-> Viewport-Umriss
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

    # ---- Geometrie
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
        """-> "Spalte/Zeile" (z.B. "2/B") oder None ausserhalb des Feldes."""
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

    # ---- Darstellung
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
        linie(cx1, y1, cx1, y2)             # Trennung Zeilen-Beschriftung
        linie(x1, cy2, x2, cy2)             # Trennung Spalten-Beschriftung
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
        for i in range(self.spalten):
            out.append(Text(cx1 + (i + 0.5) * bw, (cy2 + y2) / 2.0,
                            self.spalten_name(i), self.text_hoehe, 0.0, "Arial",
                            einfuegepunkt="mitte_zentriert", **tst))
        for j in range(self.zeilen):
            out.append(Text((x1 + cx1) / 2.0, cy2 - (j + 0.5) * bh,
                            self.zeilen_name(j), self.text_hoehe, 0.0, "Arial",
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
        """Linienzuege, auf denen ein Klick das Feld markiert (Rahmen und
        Umriss, nicht das Innere)."""
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


ZUSAMMENGESETZT = (BlockReferenz, Querverweis, Verbindung, ElektroMaske, Klemme,
                   Koordinatenfeld)
