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
    # ---- electrical
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
    else:
        d.ellipse([30 * f, 30 * f, 70 * f, 70 * f], outline=c, width=int(w * f))


NAMEN = ("auswahl", "linie", "polylinie", "kreis", "bogen", "ellipse", "spline",
         "rechteck", "text", "bemassung", "stutzen", "brechen",
         "vpunkt", "verbindung", "querverweis", "maske", "klemme", "kabel",
         "koordinatenfeld", "suchen")


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
