# -*- coding: utf-8 -*-
"""
katiecad/ui/icons.py - Toolbar icons drawn by code (MIT).

Simple line pictograms, rendered with Pillow at 8x size and scaled down
(smooth edges, no image files needed). `icon_png(name, farbe)` returns
PNG bytes; the application turns them into tk.PhotoImage objects.
Coordinates of the drawings: 0..100 (y downwards).
"""

import io
import math

try:
    from PIL import Image, ImageDraw
    PIL_OK = True
except ImportError:                       # without Pillow the toolbar keeps its texts
    PIL_OK = False

from katiecad.model.geom2d import spline_punkte

SS = 8                                    # supersampling
STRICH = 7.0                              # line width (of 100)


def _l(d, pts, w=STRICH, farbe=None, f=1.0):
    d.line([(x * f, y * f) for x, y in pts], fill=farbe, width=max(1, int(w * f)),
           joint="curve")
    r = w * f / 2.0
    for x, y in (pts[0], pts[-1]):                      # round ends
        d.ellipse([x * f - r, y * f - r, x * f + r, y * f + r], fill=farbe)


def _punkt(d, x, y, r, farbe, f):
    d.ellipse([(x - r) * f, (y - r) * f, (x + r) * f, (y + r) * f], fill=farbe)


def _zeichne(name, d, c, f):
    """Draws icon `name` with colour c; f = scale factor (px per unit)."""
    w = STRICH
    L = lambda pts, ww=w: _l(d, pts, ww, c, f)
    P = lambda x, y, r=5.5: _punkt(d, x, y, r, c, f)
    if name == "auswahl":
        L([(26, 12), (26, 82), (43, 66), (55, 90), (65, 85), (53, 62), (76, 62), (26, 12)])
    elif name == "linie":
        L([(20, 80), (80, 20)]); P(20, 80); P(80, 20)
    elif name == "polylinie":
        L([(14, 76), (36, 34), (58, 66), (86, 24)])
        for x, y in ((14, 76), (36, 34), (58, 66), (86, 24)):
            P(x, y, 5)
    elif name == "kreis":
        d.ellipse([18 * f, 18 * f, 82 * f, 82 * f], outline=c, width=int(w * f))
    elif name == "bogen":
        d.arc([14 * f, 30 * f, 86 * f, 102 * f], 195, 345, fill=c, width=int(w * f))
        P(20, 54, 5); P(80, 54, 5)
    elif name == "ellipse":
        d.ellipse([10 * f, 28 * f, 90 * f, 72 * f], outline=c, width=int(w * f))
    elif name == "spline":
        stuetz = [(12, 66), (32, 30), (52, 52), (70, 74), (88, 34)]
        L(spline_punkte(stuetz, False, 14))
        for x, y in stuetz:
            P(x, y, 4.5)
    elif name == "rechteck":
        d.rectangle([18 * f, 26 * f, 82 * f, 74 * f], outline=c, width=int(w * f))
    elif name == "text":
        L([(20, 24), (80, 24)]); L([(50, 24), (50, 84)])
    elif name == "bemassung":
        L([(16, 22), (16, 70)], 5); L([(84, 22), (84, 70)], 5)
        L([(16, 56), (84, 56)], 5)
        d.polygon([(16 * f, 56 * f), (32 * f, 46 * f), (32 * f, 66 * f)], fill=c)
        d.polygon([(84 * f, 56 * f), (68 * f, 46 * f), (68 * f, 66 * f)], fill=c)
    elif name == "stutzen":
        L([(64, 12), (64, 88)])
        L([(10, 50), (54, 50)])
        for x in (72, 82, 92):                         # removed rest, dashed
            L([(x, 50), (x + 3, 50)], 5)
    elif name == "brechen":
        L([(8, 50), (36, 50)]); L([(64, 50), (92, 50)])
        L([(30, 36), (42, 64)], 5); L([(58, 36), (70, 64)], 5)
    elif name == "suchen":
        d.ellipse([16 * f, 14 * f, 62 * f, 60 * f], outline=c, width=int(w * f))
        L([(54, 54), (86, 86)], 9)
    elif name in ("zoom_plus", "zoom_minus"):
        d.ellipse([12 * f, 12 * f, 66 * f, 66 * f], outline=c, width=int(w * f))
        L([(58, 58), (88, 88)], 9)
        L([(26, 39), (52, 39)], 6)
        if name == "zoom_plus":
            L([(39, 26), (39, 52)], 6)
    elif name == "zoom_grenzen":
        d.ellipse([6 * f, 10 * f, 54 * f, 58 * f], outline=c, width=int(w * f))
        L([(48, 52), (60, 64)], 8)
        L([(18, 34), (42, 34)], 5); L([(30, 22), (30, 46)], 5)
        d.arc([64 * f, 46 * f, 96 * f, 88 * f], 0, 315, fill=c, width=int(6 * f))
        L([(80, 67), (96, 67)], 6)
    elif name == "reset":
        d.arc([18 * f, 18 * f, 82 * f, 82 * f], 180, 300, fill=c, width=int(w * f))
        d.arc([18 * f, 18 * f, 82 * f, 82 * f], 0, 120, fill=c, width=int(w * f))
        for ang in (300, 120):
            a = math.radians(ang)
            px, py = 50 + 32 * math.cos(a), 50 + 32 * math.sin(a)
            tx, ty = -math.sin(a), math.cos(a)
            nx, ny = -ty, tx
            d.polygon([((px + tx * 12) * f, (py + ty * 12) * f),
                       ((px - tx * 4 + nx * 11) * f, (py - ty * 4 + ny * 11) * f),
                       ((px - tx * 4 - nx * 11) * f, (py - ty * 4 - ny * 11) * f)],
                      fill=c)
    # ---- electrical
    elif name == "laenge":
        L([(10, 62), (66, 62)]); P(10, 62)
        L([(66, 62), (90, 62)], 5)
        d.polygon([(90 * f, 62 * f), (74 * f, 52 * f), (74 * f, 72 * f)], fill=c)
        L([(10, 30), (10, 46)], 5); L([(50, 30), (50, 46)], 5)
        L([(10, 38), (50, 38)], 4)
    elif name == "manip":
        L([(18, 78), (82, 78)]); L([(18, 78), (18, 14)])
        d.polygon([(90 * f, 78 * f), (74 * f, 68 * f), (74 * f, 88 * f)], fill=c)
        d.polygon([(18 * f, 6 * f), (8 * f, 22 * f), (28 * f, 22 * f)], fill=c)
        d.rectangle([34 * f, 40 * f, 54 * f, 60 * f], outline=c, width=int(6 * f))
    elif name == "ftext":
        L([(14, 26), (86, 26)], 5); L([(14, 50), (70, 50)], 5); L([(14, 74), (50, 74)], 5)
        d.polygon([(62 * f, 62 * f), (92 * f, 74 * f), (62 * f, 86 * f)], fill=c)
    elif name == "vpunkt":
        d.ellipse([36 * f, 36 * f, 64 * f, 64 * f], outline=c, width=int(w * f))
        L([(8, 50), (36, 50)]); L([(64, 50), (92, 50)])
    elif name == "verbindung":
        L([(10, 50), (90, 50)]); L([(50, 10), (50, 90)]); P(50, 50, 13)
    elif name == "querverweis":
        L([(8, 50), (58, 50)])
        d.polygon([(58 * f, 28 * f), (92 * f, 50 * f), (58 * f, 72 * f)], fill=c)
    elif name == "maske":
        d.rectangle([14 * f, 20 * f, 86 * f, 80 * f], outline=c, width=int(w * f))
        L([(28, 38), (72, 38)], 5); L([(28, 50), (58, 50)], 5); L([(28, 62), (66, 62)], 5)
    elif name == "klemme":
        L([(50, 8), (50, 30)]); L([(50, 70), (50, 92)])
        d.rectangle([30 * f, 30 * f, 70 * f, 70 * f], outline=c, width=int(w * f))
        P(50, 50, 7)
    elif name == "kabel":
        d.rectangle([8 * f, 38 * f, 92 * f, 58 * f], outline=c, width=int(w * f))
        for x in (28, 50, 72):
            L([(x, 8), (x, 38)], 5); L([(x, 58), (x, 92)], 5)
    elif name == "koordinatenfeld":
        d.rectangle([14 * f, 14 * f, 86 * f, 86 * f], outline=c, width=int(w * f))
        for p in (38, 62):
            L([(p, 14), (p, 86)], 4); L([(14, p), (86, p)], 4)
    # ---- 3D
    elif name in ("ansicht3d", "wuerfel"):
        hx = [(50, 8), (88, 29), (88, 71), (50, 92), (12, 71), (12, 29), (50, 8)]
        L(hx, 6)
        if name == "wuerfel":
            d.polygon([(50 * f, 8 * f), (88 * f, 29 * f), (50 * f, 50 * f), (12 * f, 29 * f)], fill=c)
        L([(50, 50), (50, 92)], 5); L([(50, 50), (12, 29)], 5); L([(50, 50), (88, 29)], 5)
    elif name == "k_quader":
        d.rectangle([12 * f, 38 * f, 62 * f, 88 * f], outline=c, width=int(6 * f))
        d.rectangle([34 * f, 14 * f, 88 * f, 64 * f], outline=c, width=int(5 * f))
        L([(12, 38), (34, 14)], 5); L([(62, 38), (88, 14)], 5); L([(62, 88), (88, 64)], 5)
    elif name == "k_zylinder":
        d.ellipse([20 * f, 8 * f, 80 * f, 34 * f], outline=c, width=int(6 * f))
        d.arc([20 * f, 62 * f, 80 * f, 90 * f], 0, 180, fill=c, width=int(6 * f))
        L([(20, 21), (20, 76)], 6); L([(80, 21), (80, 76)], 6)
    elif name == "k_kegel":
        d.ellipse([14 * f, 62 * f, 86 * f, 90 * f], outline=c, width=int(6 * f))
        L([(50, 8), (14, 76)], 6); L([(50, 8), (86, 76)], 6)
    elif name == "k_pyramide":
        L([(50, 8), (12, 72)], 6); L([(50, 8), (50, 90)], 5); L([(50, 8), (88, 66)], 6)
        L([(12, 72), (50, 90), (88, 66)], 6); L([(12, 72), (56, 52), (88, 66)], 4)
    elif name == "k_kugel":
        d.ellipse([12 * f, 12 * f, 88 * f, 88 * f], outline=c, width=int(6 * f))
        d.ellipse([12 * f, 38 * f, 88 * f, 62 * f], outline=c, width=int(4 * f))
        d.ellipse([36 * f, 12 * f, 64 * f, 88 * f], outline=c, width=int(4 * f))
    elif name == "extrudieren":
        L([(10, 84), (58, 84), (90, 66), (42, 66), (10, 84)], 5)
        L([(50, 58), (50, 18)], 6)
        d.polygon([(50 * f, 6 * f), (34 * f, 26 * f), (66 * f, 26 * f)], fill=c)
    elif name == "loch":
        d.rectangle([10 * f, 24 * f, 90 * f, 84 * f], outline=c, width=int(6 * f))
        d.ellipse([34 * f, 38 * f, 66 * f, 62 * f], outline=c, width=int(6 * f))
        L([(34, 50), (34, 84)], 4); L([(66, 50), (66, 84)], 4)
    elif name == "block3d":
        for a, b in (((8, 8), (30, 8)), ((70, 8), (92, 8)), ((8, 92), (30, 92)), ((70, 92), (92, 92)),
                     ((8, 8), (8, 30)), ((8, 70), (8, 92)), ((92, 8), (92, 30)), ((92, 70), (92, 92))):
            L([a, b], 5)
        d.rectangle([22 * f, 48 * f, 50 * f, 76 * f], outline=c, width=int(6 * f))
        d.rectangle([48 * f, 24 * f, 76 * f, 52 * f], outline=c, width=int(6 * f))
    elif name == "aufloesen3d":
        d.rectangle([8 * f, 56 * f, 38 * f, 86 * f], outline=c, width=int(6 * f))
        d.rectangle([62 * f, 12 * f, 92 * f, 42 * f], outline=c, width=int(6 * f))
        L([(46, 56), (56, 46)], 5)
        d.polygon([(60 * f, 42 * f), (46 * f, 44 * f), (58 * f, 56 * f)], fill=c)
    elif name == "raster3d":
        for t in (14, 38, 62, 86):
            L([(t, 14), (t, 86)], 4); L([(14, t), (86, t)], 4)
    elif name == "flaeche3d":
        d.polygon([(50 * f, 8 * f), (88 * f, 29 * f), (50 * f, 50 * f), (12 * f, 29 * f)], fill=c)
        L([(12, 29), (12, 71), (50, 92), (88, 71), (88, 29)], 5); L([(50, 50), (50, 92)], 5)
    elif name == "skizze_kreis":
        L([(8, 78), (30, 52), (92, 52), (70, 78), (8, 78)], 4)
        d.ellipse([34 * f, 22 * f, 66 * f, 54 * f], outline=c, width=int(6 * f))
    elif name == "skizze_rechteck":
        L([(8, 78), (30, 52), (92, 52), (70, 78), (8, 78)], 4)
        d.rectangle([34 * f, 14 * f, 74 * f, 46 * f], outline=c, width=int(6 * f))
    elif name == "skizze_linie":
        L([(8, 78), (30, 52), (92, 52), (70, 78), (8, 78)], 4)
        L([(30, 46), (74, 14)], 7)
        d.ellipse([24 * f, 40 * f, 36 * f, 52 * f], fill=c)
        d.ellipse([68 * f, 8 * f, 80 * f, 20 * f], fill=c)
    elif name == "drehen3d":
        d.arc([14 * f, 14 * f, 86 * f, 86 * f], 40, 320, fill=c, width=int(7 * f))
        d.polygon([(86 * f, 30 * f), (96 * f, 54 * f), (68 * f, 48 * f)], fill=c)
        P(50, 50, 7)
    elif name == "abrunden3d":
        L([(14, 86), (14, 40)], 7); L([(60, 86), (86, 86)], 7)
        d.arc([14 * f, 14 * f, 86 * f, 86 * f], 180, 270, fill=c, width=int(7 * f))
        L([(14, 40), (14, 40)], 7); L([(50, 14), (86, 14)], 7); L([(86, 14), (86, 86)], 7)
        L([(14, 86), (60, 86)], 7)
    elif name == "manip_pivot":
        L([(14, 70), (70, 70)], 6); L([(14, 70), (14, 14)], 6)
        d.ellipse([58 * f, 58 * f, 82 * f, 82 * f], outline=c, width=int(6 * f))
        L([(70, 50), (70, 90)], 4); L([(50, 70), (90, 70)], 4)
    elif name == "skizze_poly":
        L([(8, 78), (30, 52), (92, 52), (70, 78), (8, 78)], 4)
        L([(30, 46), (46, 12), (74, 30), (62, 46), (30, 46)], 6)
    elif name == "ebene0":
        L([(8, 74), (30, 46), (92, 46), (70, 74), (8, 74)], 5)
        L([(40, 60), (40, 12)], 6)
        d.polygon([(40 * f, 4 * f), (28 * f, 20 * f), (52 * f, 20 * f)], fill=c)
    elif name == "bem3d":
        L([(14, 80), (14, 36)], 4); L([(86, 80), (86, 36)], 4)
        L([(14, 48), (86, 48)], 5)
        d.polygon([(14 * f, 48 * f), (30 * f, 38 * f), (30 * f, 58 * f)], fill=c)
        d.polygon([(86 * f, 48 * f), (70 * f, 38 * f), (70 * f, 58 * f)], fill=c)
        L([(30, 90), (70, 90)], 4); L([(30, 84), (30, 96)], 3); L([(70, 84), (70, 96)], 3)
    elif name == "mass3d":
        d.rectangle([14 * f, 38 * f, 62 * f, 86 * f], outline=c, width=int(6 * f))
        L([(62, 38), (84, 16)], 5); L([(62, 86), (84, 64)], 5); L([(84, 16), (84, 64)], 5)
        L([(14, 38), (36, 16), (84, 16)], 5)
        L([(70, 50), (92, 50)], 4)
        d.polygon([(96 * f, 50 * f), (84 * f, 42 * f), (84 * f, 58 * f)], fill=c)
    elif name == "persp":
        d.rectangle([6 * f, 14 * f, 94 * f, 86 * f], outline=c, width=int(5 * f))
        d.rectangle([36 * f, 38 * f, 64 * f, 62 * f], outline=c, width=int(5 * f))
        L([(6, 14), (36, 38)], 4); L([(94, 14), (64, 38)], 4)
        L([(6, 86), (36, 62)], 4); L([(94, 86), (64, 62)], 4)
    elif name == "einpassen3d":
        for pts in (((10, 34), (10, 10), (34, 10)), ((66, 10), (90, 10), (90, 34)),
                    ((10, 66), (10, 90), (34, 90)), ((66, 90), (90, 90), (90, 66))):
            L(list(pts), 6)
        d.rectangle([34 * f, 34 * f, 66 * f, 66 * f], outline=c, width=int(5 * f))
    elif name == "iso3d":
        L([(50, 58), (50, 10)], 6); L([(50, 58), (12, 82)], 6); L([(50, 58), (88, 82)], 6)
        P(50, 58, 8)
    elif name == "hoehe3d":
        L([(50, 14), (50, 86)], 6)
        d.polygon([(50 * f, 4 * f), (34 * f, 24 * f), (66 * f, 24 * f)], fill=c)
        d.polygon([(50 * f, 96 * f), (34 * f, 76 * f), (66 * f, 76 * f)], fill=c)
        L([(18, 50), (82, 50)], 4)
    else:
        d.ellipse([30 * f, 30 * f, 70 * f, 70 * f], outline=c, width=int(w * f))


NAMEN = ("auswahl", "linie", "polylinie", "kreis", "bogen", "ellipse", "spline",
         "rechteck", "text", "bemassung", "stutzen", "brechen",
         "vpunkt", "verbindung", "querverweis", "maske", "klemme", "kabel",
         "koordinatenfeld", "suchen", "zoom_plus", "zoom_minus",
         "zoom_grenzen", "reset", "ftext", "laenge", "manip",
         "ansicht3d", "wuerfel", "k_quader", "k_zylinder", "k_kegel", "k_pyramide",
         "k_kugel", "extrudieren", "loch", "block3d", "aufloesen3d", "persp",
         "einpassen3d", "iso3d", "hoehe3d", "raster3d", "flaeche3d", "skizze_kreis",
         "skizze_rechteck", "skizze_linie", "skizze_poly", "ebene0", "bem3d", "mass3d", "drehen3d", "abrunden3d", "manip_pivot")


def icon_png(name, farbe, groesse=26):
    """PNG bytes of the icon `name` in colour `farbe` ('#rrggbb') or None
    without Pillow."""
    if not PIL_OK:
        return None
    gross = groesse * SS
    img = Image.new("RGBA", (gross, gross), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _zeichne(name, d, farbe, gross / 100.0)
    img = img.resize((groesse, groesse), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
