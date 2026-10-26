# -*- coding: utf-8 -*-
"""
katiecad/fileio/pdf_import.py - Own PDF reader (vector import, NO Tkinter).

Reads the drawing commands of a PDF page and turns them into KatieCAD
elements. Only the BSD-licensed `pypdf` is used (no AGPL code), so KatieCAD
stays MIT-licensed.

What is recognised
  * Layers: "optional content groups" (OCG) as written by AutoCAD, BricsCAD,
    LibreCAD ... ("Layers" in the PDF reader). Every group becomes a KatieCAD
    layer (hidden groups stay hidden); drawing without layers -> layer "PDF".
  * Lines, polylines, rectangles, Bezier curves (flattened), circles (four
    curves), solid fills (-> hatch, "solid"), text (with ToUnicode maps).
  * Form XObjects (nested), page rotation, colours (grey/RGB/CMYK).
What is NOT imported: raster images (counted in the report), shadings,
clipping paths, dash patterns.

Unit: 1 PDF point = 0.3528 mm (paper size); `faktor` scales further
(e.g. 50 for a plot at 1:50).
"""

import math
import re
from collections import Counter

from katiecad.model.core import (Layer, Linie, Kreis, Polylinie, Rechteck, Text,
                                 Schraffur)
from katiecad.fileio.cad_import import ImportErgebnis

try:
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    PYPDF_OK = True
except ImportError:                                    # pragma: no cover
    PdfReader = ContentStream = None
    PYPDF_OK = False

PT_MM = 25.4 / 72.0
MAX_ELEMENTE = 400000
KURVEN_SCHRITTE = 10
KAPPA_TOL = 0.02                 # tolerance for circle detection (relative)
KAPPA = 0.5522847498


# ------------------------------------------------------------------
# Matrices (a b c d e f), PDF convention: [x y 1] * M
# ------------------------------------------------------------------
def mal(m, n):
    """m applied first, then n."""
    return (m[0] * n[0] + m[1] * n[2], m[0] * n[1] + m[1] * n[3],
            m[2] * n[0] + m[3] * n[2], m[2] * n[1] + m[3] * n[3],
            m[4] * n[0] + m[5] * n[2] + n[4], m[4] * n[1] + m[5] * n[3] + n[5])


def anwenden(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def _zahlen(ops):
    out = []
    for o in ops:
        try:
            out.append(float(o))
        except (TypeError, ValueError):
            pass
    return out


# ------------------------------------------------------------------
# Colours
# ------------------------------------------------------------------
def _hex(r, g, b):
    c = lambda v: max(0, min(255, int(round(v * 255))))
    return "#%02x%02x%02x" % (c(r), c(g), c(b))


def farbe_aus(werte):
    """1 value = grey, 3 = RGB, 4 = CMYK -> (r, g, b) 0..1."""
    w = [max(0.0, min(1.0, v)) for v in werte]
    if len(w) == 1:
        return (w[0],) * 3
    if len(w) == 3:
        return tuple(w)
    if len(w) == 4:
        c, m, y, k = w
        return ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
    return (0.0, 0.0, 0.0)


def _hell(rgb):
    return 0.3 * rgb[0] + 0.59 * rgb[1] + 0.11 * rgb[2]


def anzeige_farbe(rgb):
    """Colour for the dark KatieCAD background: black/dark -> light."""
    if _hell(rgb) < 0.28:
        return "#e8e0ff"
    return _hex(*rgb)


# ------------------------------------------------------------------
# Fonts: ToUnicode
# ------------------------------------------------------------------
class Schrift:
    def __init__(self, fobj=None):
        self.zwei_byte = False
        self.map = {}
        if fobj is None:
            return
        try:
            fobj = fobj.get_object()
            self.zwei_byte = fobj.get("/Subtype") == "/Type0"
            tu = fobj.get("/ToUnicode")
            if tu is not None:
                self._cmap(tu.get_object().get_data().decode("latin-1"))
        except Exception:
            pass

    def _cmap(self, text):
        if "begincodespacerange" in text:
            m = re.search(r"begincodespacerange\s*<([0-9A-Fa-f]+)>", text)
            if m:
                self.zwei_byte = len(m.group(1)) >= 4
        for blk in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
            for a, b in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
                self.map[int(a, 16)] = self._uni(b)
        for blk in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
            for a, b, c in re.findall(
                    r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
                lo, hi, start = int(a, 16), int(b, 16), int(c, 16)
                basis = self._uni(c)
                for i in range(min(hi - lo + 1, 65536)):
                    self.map[lo + i] = (chr(start + i) if len(basis) == 1
                                        else basis[:-1] + chr(ord(basis[-1]) + i))
            for a, b, arr in re.findall(
                    r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", blk, re.S):
                for i, h in enumerate(re.findall(r"<([0-9A-Fa-f]+)>", arr)):
                    self.map[int(a, 16) + i] = self._uni(h)

    @staticmethod
    def _uni(h):
        try:
            return bytes.fromhex(h).decode("utf-16-be")
        except Exception:
            return ""

    def dekodieren(self, roh):
        if isinstance(roh, str):
            roh = roh.encode("latin-1", "replace")
        if self.zwei_byte:
            codes = [(roh[i] << 8) | roh[i + 1] for i in range(0, len(roh) - 1, 2)]
        else:
            codes = list(roh)
        out = []
        for c in codes:
            if c in self.map:
                out.append(self.map[c])
            elif not self.map and not self.zwei_byte:
                out.append(bytes([c]).decode("cp1252", "replace"))
            elif c >= 32 and not self.zwei_byte:
                out.append(chr(c))
        return "".join(out)


# ------------------------------------------------------------------
# Interpreter
# ------------------------------------------------------------------
class _Zustand:
    __slots__ = ("ctm", "breite", "strich", "fuell", "oc")

    def __init__(self, ctm):
        self.ctm = ctm
        self.breite = 1.0
        self.strich = (0.0, 0.0, 0.0)
        self.fuell = (0.0, 0.0, 0.0)
        self.oc = None

    def kopie(self):
        z = _Zustand(self.ctm)
        z.breite, z.strich, z.fuell, z.oc = self.breite, self.strich, self.fuell, self.oc
        return z


class PdfImporter:
    def __init__(self, reader, layers, faktor=1.0):
        self.reader = reader
        self.layers = layers
        self.faktor = faktor
        self.erg = ImportErgebnis()
        self.elemente = self.erg.elemente
        self.ocg_name = {}              # id(object) -> name
        self.ocg_aus = set()            # names of hidden groups
        self.farben = {}                # layer -> Counter of colours
        self.neue = {}                  # name -> Layer (not yet registered)
        self.schriften = {}
        self._ocg_lesen()

    # ---- Layers (optional content) -----------------------------------
    def _ocg_lesen(self):
        try:
            root = self.reader.trailer["/Root"]
            ocp = root.get("/OCProperties")
            if ocp is None:
                return
            ocp = ocp.get_object()
            gruppen = [g.get_object() for g in ocp.get("/OCGs", [])]
            for g in gruppen:
                self.ocg_name[id(g)] = str(g.get("/Name", "PDF-Layer"))
            d = ocp.get("/D")
            if d is not None:
                d = d.get_object()
                for g in d.get("/OFF", []) or []:
                    self.ocg_aus.add(str(g.get_object().get("/Name", "")))
                if str(d.get("/BaseState", "/ON")) == "/OFF":
                    an = {str(g.get_object().get("/Name", ""))
                          for g in d.get("/ON", []) or []}
                    self.ocg_aus |= {str(g.get("/Name", "")) for g in gruppen} - an
        except Exception:
            pass

    def _oc_name(self, objekt):
        """Layer name of an /OC entry (OCG or OCMD)."""
        try:
            o = objekt.get_object()
            if o.get("/Type") == "/OCMD":
                gr = o.get("/OCGs")
                if gr is None:
                    return None
                gr = gr.get_object()
                if isinstance(gr, list):
                    gr = gr[0].get_object() if gr else None
                if gr is None:
                    return None
                o = gr
            return str(o.get("/Name", "")) or None
        except Exception:
            return None

    def _layer(self, name):
        name = (name or "PDF").strip() or "PDF"
        if name not in self.neue:
            if name in self.layers:                 # same name: use it
                self.neue[name] = self.layers[name]
            else:
                l = Layer(name, "#c29bff", 0.35, name not in self.ocg_aus)
                self.neue[name] = l
                self.layers[name] = l
                self.erg.neue_layer.append(name)
        return name

    # ---- Output -----------------------------------------------------------
    def _add(self, el, layer, rgb):
        if len(self.elemente) >= MAX_ELEMENTE:
            if not self.erg.hinweise or "Limit" not in self.erg.hinweise[-1]:
                self.erg.hinweise.append(
                    f"Limit: only the first {MAX_ELEMENTE} elements were imported.")
            return
        el.layer = layer
        el.eig_farbe = False
        self.farben.setdefault(layer, Counter())[anzeige_farbe(rgb)] += 1
        self.elemente.append(el)

    def _pt(self, m, x, y):
        px, py = anwenden(m, x, y)
        return (px * PT_MM * self.faktor, py * PT_MM * self.faktor)

    def _staerke(self, st):
        s = math.sqrt(abs(st.ctm[0] * st.ctm[3] - st.ctm[1] * st.ctm[2]))
        mm = st.breite * s * PT_MM * self.faktor
        if mm <= 0:
            return None
        return max(0.13, min(1.0, round(mm, 2)))

    # ---- Run -----------------------------------------------------------
    def seite(self, page, basis):
        res = page.get("/Resources")
        res = res.get_object() if res is not None else {}
        try:
            cs = ContentStream(page.get_contents(), self.reader)
        except Exception as e:
            raise RuntimeError(f"PDF content could not be read: {e}")
        self._lauf(cs.operations, res, _Zustand(basis), 0)

    def _schrift(self, res, name):
        key = (id(res), name)
        if key not in self.schriften:
            try:
                f = res["/Font"][name]
            except Exception:
                f = None
            self.schriften[key] = Schrift(f)
        return self.schriften[key]

    def _lauf(self, ops, res, st, tiefe):
        stapel = []
        oc_stapel = []                    # one entry per BDC (name | None)
        pfad, aktuell, pos = [], None, (0.0, 0.0)
        tm = tlm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        schrift, groesse, tl, tc, tw = Schrift(), 1.0, 0.0, 0.0, 0.0
        tz = 1.0
        text_teile = []

        def layer_jetzt():
            for n in reversed(oc_stapel):
                if n:
                    return self._layer(n)
            return self._layer(st.oc)

        def neuer_pfad():
            nonlocal pfad, aktuell
            pfad, aktuell = [], None

        def neu_unterpfad(p):
            nonlocal aktuell
            aktuell = {"pts": [p], "kurven": [], "zu": False}
            pfad.append(aktuell)

        def zeichne(strich, fuell):
            lay = layer_jetzt()
            m = st.ctm
            for sp in pfad:
                pts = [self._pt(m, *p) for p in sp["pts"]]
                if len(pts) < 2:
                    continue
                kreis = self._kreis(sp, m) if sp["zu"] or len(sp["kurven"]) == 4 else None
                if kreis is not None and not fuell:
                    k = Kreis(*kreis, staerke=self._staerke(st))
                    self._add(k, lay, st.strich)
                    continue
                if fuell and not strich and len(pfad) == 1 and len(pts) >= 3:
                    if _hell(st.fuell) < 0.97:            # white = background
                        self._add(Schraffur(pts, "solid"), lay, st.fuell)
                    continue
                rgb = st.strich if strich else st.fuell
                if strich or fuell:
                    stae = self._staerke(st) if strich else None
                    if (len(pts) == 2 and not sp["zu"]):
                        self._add(Linie(*pts[0], *pts[1], staerke=stae), lay, rgb)
                    else:
                        self._add(Polylinie(pts, geschlossen=sp["zu"], staerke=stae),
                                  lay, rgb)

        for operanden, op in ops:
            op = op.decode("latin-1") if isinstance(op, bytes) else str(op)
            try:
                if op == "q":
                    stapel.append(st.kopie())
                elif op == "Q":
                    if stapel:
                        st = stapel.pop()
                elif op == "cm":
                    z = _zahlen(operanden)
                    if len(z) == 6:
                        st.ctm = mal(tuple(z), st.ctm)
                elif op == "w":
                    z = _zahlen(operanden)
                    if z:
                        st.breite = z[0]
                elif op in ("G", "RG", "K"):
                    st.strich = farbe_aus(_zahlen(operanden))
                elif op in ("g", "rg", "k"):
                    st.fuell = farbe_aus(_zahlen(operanden))
                elif op in ("SC", "SCN"):
                    z = _zahlen(operanden)
                    if z:
                        st.strich = farbe_aus(z)
                elif op in ("sc", "scn"):
                    z = _zahlen(operanden)
                    if z:
                        st.fuell = farbe_aus(z)
                # ---- marked content / layers
                elif op == "BDC":
                    name = None
                    if len(operanden) == 2 and str(operanden[0]) == "/OC":
                        prop = operanden[1]
                        try:
                            if isinstance(prop, str) or hasattr(prop, "startswith"):
                                prop = res["/Properties"][prop]
                        except Exception:
                            prop = None
                        name = self._oc_name(prop) if prop is not None else None
                    oc_stapel.append(name)
                elif op == "BMC":
                    oc_stapel.append(None)
                elif op == "EMC":
                    if oc_stapel:
                        oc_stapel.pop()
                # ---- path
                elif op == "m":
                    z = _zahlen(operanden)
                    pos = (z[0], z[1])
                    neu_unterpfad(pos)
                elif op == "l":
                    z = _zahlen(operanden)
                    if aktuell is None:
                        neu_unterpfad((z[0], z[1]))
                    else:
                        aktuell["pts"].append((z[0], z[1]))
                    pos = (z[0], z[1])
                elif op in ("c", "v", "y"):
                    z = _zahlen(operanden)
                    if aktuell is None:
                        neu_unterpfad(pos)
                    p0 = aktuell["pts"][-1]
                    if op == "c":
                        p1, p2, p3 = (z[0], z[1]), (z[2], z[3]), (z[4], z[5])
                    elif op == "v":
                        p1, p2, p3 = p0, (z[0], z[1]), (z[2], z[3])
                    else:
                        p1, p2, p3 = (z[0], z[1]), (z[2], z[3]), (z[2], z[3])
                    for i in range(1, KURVEN_SCHRITTE + 1):
                        t = i / KURVEN_SCHRITTE
                        u = 1 - t
                        aktuell["pts"].append((
                            u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
                    aktuell["kurven"].append((p0, p1, p2, p3))
                    pos = p3
                elif op == "re":
                    x, y, w, h = _zahlen(operanden)[:4]
                    neu_unterpfad((x, y))
                    aktuell["pts"] += [(x + w, y), (x + w, y + h), (x, y + h)]
                    aktuell["zu"] = True
                    aktuell["rechteck"] = (x, y, x + w, y + h)
                    pos = (x, y)
                elif op == "h":
                    if aktuell is not None:
                        aktuell["zu"] = True
                        if len(aktuell["pts"]) > 2 and aktuell["pts"][0] == aktuell["pts"][-1]:
                            aktuell["pts"].pop()
                elif op in ("S", "s", "f", "F", "f*", "B", "B*", "b", "b*"):
                    if op in ("s", "b", "b*") and aktuell is not None:
                        aktuell["zu"] = True
                    zeichne(strich=op in ("S", "s", "B", "B*", "b", "b*"),
                            fuell=op in ("f", "F", "f*", "B", "B*", "b", "b*"))
                    neuer_pfad()
                elif op == "n":
                    neuer_pfad()
                # ---- text
                elif op == "BT":
                    tm = tlm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                elif op == "Tf":
                    schrift = self._schrift(res, operanden[0])
                    groesse = float(operanden[1])
                elif op == "TL":
                    tl = float(operanden[0])
                elif op == "Tz":
                    tz = float(operanden[0]) / 100.0
                elif op in ("Td", "TD"):
                    z = _zahlen(operanden)
                    if op == "TD":
                        tl = -z[1]
                    tlm = mal((1, 0, 0, 1, z[0], z[1]), tlm)
                    tm = tlm
                elif op == "Tm":
                    tm = tlm = tuple(_zahlen(operanden))
                elif op == "T*":
                    tlm = mal((1, 0, 0, 1, 0, -tl), tlm)
                    tm = tlm
                elif op in ("Tj", "TJ", "'", '"'):
                    if op in ("'", '"'):
                        tlm = mal((1, 0, 0, 1, 0, -tl), tlm)
                        tm = tlm
                    teile = operanden[-1] if op != "TJ" else operanden[0]
                    if op != "TJ":
                        teile = [teile]
                    s, versatz = "", 0.0
                    for t in teile:
                        if isinstance(t, (int, float)) or hasattr(t, "as_numeric"):
                            try:
                                v = float(t)
                                if v < -250:               # large gap = space
                                    s += " "
                                versatz -= v / 1000.0 * groesse * tz
                            except Exception:
                                pass
                        else:
                            roh = bytes(t) if isinstance(t, (bytes, bytearray)) else str(t).encode("latin-1", "replace")
                            txt = schrift.dekodieren(roh)
                            s += txt
                    if s.strip():
                        full = mal(tm, st.ctm)
                        x0, y0 = full[4], full[5]
                        hs = math.hypot(full[2], full[3]) * groesse
                        wi = math.degrees(math.atan2(full[1], full[0]))
                        if hs > 1e-6:
                            h_mm = hs * 0.716 * PT_MM * self.faktor
                            t_el = Text(x0 * PT_MM * self.faktor, y0 * PT_MM * self.faktor,
                                        s.strip(), round(h_mm, 3), round(wi, 3),
                                        "Arial", einfuegepunkt="unten_links")
                            self._add(t_el, layer_jetzt(), st.fuell)
                    # advance (rough: 0.5 em per character)
                    tm = mal((1, 0, 0, 1, (len(s) * 0.5 * groesse + versatz) * tz, 0), tm)
                # ---- XObjects
                elif op == "Do" and tiefe < 8:
                    self._xobject(res, operanden[0], st, layer_jetzt, tiefe)
                elif op == "BI":
                    self.erg.uebersprungen["Bild"] += 1
            except (IndexError, ValueError, TypeError, KeyError):
                self.erg.fehler += 1

    def _xobject(self, res, name, st, layer_jetzt, tiefe):
        try:
            xo = res["/XObject"][name].get_object()
        except Exception:
            return
        if xo.get("/Subtype") != "/Form":
            self.erg.uebersprungen["Bild"] += 1
            return
        sub = _Zustand(st.ctm)
        sub.breite, sub.strich, sub.fuell = st.breite, st.strich, st.fuell
        sub.oc = layer_jetzt()
        if "/OC" in xo:
            n = self._oc_name(xo["/OC"])
            if n:
                sub.oc = n
        m = xo.get("/Matrix")
        if m is not None:
            z = _zahlen(list(m))
            if len(z) == 6:
                sub.ctm = mal(tuple(z), sub.ctm)
        r = xo.get("/Resources")
        r = r.get_object() if r is not None else res
        try:
            cs = ContentStream(xo, self.reader)
        except Exception:
            return
        self._lauf(cs.operations, r, sub, tiefe + 1)

    # ---- Circle detection ----------------------------------------------
    def _kreis(self, sp, m):
        k = sp["kurven"]
        if len(k) != 4:
            return None
        ends = [c[0] for c in k]
        xs = [p[0] for p in ends]
        ys = [p[1] for p in ends]
        cx, cy = sum(xs) / 4, sum(ys) / 4
        r = [math.hypot(p[0] - cx, p[1] - cy) for p in ends]
        rm = sum(r) / 4
        if rm < 1e-6 or max(abs(v - rm) for v in r) > KAPPA_TOL * rm:
            return None
        # control point distances (kappa) show a real circle, no diamond
        for p0, p1, p2, p3 in k:
            if abs(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) - KAPPA * rm) > 0.05 * rm:
                return None
        px, py = self._pt(m, cx, cy)
        sx = math.hypot(m[0], m[1]) * PT_MM * self.faktor
        return (px, py, rm * sx)


# ------------------------------------------------------------------
def seitenzahl(pfad):
    if not PYPDF_OK:
        raise RuntimeError("pypdf is not installed:  pip install pypdf")
    return len(PdfReader(pfad).pages)


def importiere_pdf(pfad, layers, seite=1, faktor=1.0):
    """Imports one page of a PDF -> ImportErgebnis (elements in mm, origin =
    lower left corner of the page). `layers` (dict) is extended."""
    if not PYPDF_OK:
        raise RuntimeError("pypdf is not installed:  pip install pypdf")
    reader = PdfReader(pfad)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise RuntimeError("The PDF is password protected.")
    if not (1 <= seite <= len(reader.pages)):
        raise RuntimeError(f"Page {seite} does not exist (1-{len(reader.pages)}).")
    page = reader.pages[seite - 1]
    mb = [float(v) for v in page.mediabox]
    x0, y0, x1, y1 = mb[0], mb[1], mb[2], mb[3]
    rot = int(page.get("/Rotate", 0) or 0) % 360
    basis = (1.0, 0.0, 0.0, 1.0, -x0, -y0)
    b, h = x1 - x0, y1 - y0
    if rot == 90:
        basis = mal(basis, (0, -1, 1, 0, 0, b))
    elif rot == 180:
        basis = mal(basis, (-1, 0, 0, -1, b, h))
    elif rot == 270:
        basis = mal(basis, (0, 1, -1, 0, h, 0))
    imp = PdfImporter(reader, layers, float(faktor) or 1.0)
    imp.seite(page, basis)
    # layer colour = most frequent colour of its elements
    for name, cnt in imp.farben.items():
        lay = imp.neue.get(name)
        if lay is not None and name in imp.erg.neue_layer:
            lay.farbe = cnt.most_common(1)[0][0]
    erg = imp.erg
    erg.quelle = "pypdf"
    if not imp.ocg_name:
        erg.hinweise.append("The PDF contains no layers - everything is on layer 'PDF'.")
    return erg
