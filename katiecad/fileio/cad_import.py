# -*- coding: utf-8 -*-
"""
katiecad/fileio/cad_import.py - Robust DXF/DWG import for KatieCAD.
Contains NO Tkinter. Called by CadApp.import_dxf / import_dwg.

Supported (DXF):
  LINE, CIRCLE, ARC, ELLIPSE, SPLINE, LWPOLYLINE, POLYLINE (2D/3D, with
  bulges), TEXT, MTEXT, ATTRIB, HATCH, SOLID/TRACE, 3DFACE, LEADER,
  MLEADER, DIMENSION (as geometry), INSERT/MINSERT (resolved,
  also nested).
In addition: layer colours (ACI/RGB), layers off/frozen, line types,
line weights, units ($INSUNITS -> mm), OCS (extrusion -Z),
damaged files via ezdxf.recover.

DWG: converted to DXF via the ODA File Converter (via ezdxf.addons.odafc) or
LibreDWG (dwg2dxf); ezdwg only as a last resort.
"""

import math
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

from katiecad.model.core import (
    FARBEN, Layer, Linie, Kreis, Bogen, Polylinie, Text, Schraffur,
)

try:
    import ezdxf
    from ezdxf import recover as _recover
    EZDXF_OK = True
except ImportError:                                   # pragma: no cover
    ezdxf = None
    _recover = None
    EZDXF_OK = False

# $INSUNITS -> millimetres
_EINHEIT_MM = {
    1: 25.4,        # inch
    2: 304.8,       # foot
    4: 1.0,         # mm
    5: 10.0,        # cm
    6: 1000.0,      # m
    7: 1.0e6,       # km
    8: 0.0254,      # microinch
    9: 0.0254e-3,   # mil -> (rare)
    10: 914.4,      # Yard
    13: 1.0e-3,     # micrometre
    14: 100.0,      # dm
}

_ALIGN_MAP = {
    "LEFT": "unten_links", "CENTER": "unten_zentriert", "RIGHT": "unten_rechts",
    "BOTTOM_LEFT": "unten_links", "BOTTOM_CENTER": "unten_zentriert",
    "BOTTOM_RIGHT": "unten_rechts",
    "MIDDLE_LEFT": "mitte_links", "MIDDLE_CENTER": "mitte_zentriert",
    "MIDDLE_RIGHT": "mitte_rechts", "MIDDLE": "mitte_zentriert",
    "TOP_LEFT": "oben_links", "TOP_CENTER": "oben_zentriert",
    "TOP_RIGHT": "oben_rechts",
}
_MTEXT_ATTACH = {
    1: "oben_links", 2: "oben_zentriert", 3: "oben_rechts",
    4: "mitte_links", 5: "mitte_zentriert", 6: "mitte_rechts",
    7: "unten_links", 8: "unten_zentriert", 9: "unten_rechts",
}

# Entities that are decomposed into basic elements via virtual_entities()
_EXPLODE = ("INSERT", "DIMENSION", "ARC_DIMENSION", "LARGE_RADIAL_DIMENSION",
            "MLEADER", "MULTILEADER", "MLINE")
_IGNORIERT_LEISE = {"POINT", "XLINE", "RAY", "VIEWPORT", "ATTDEF",
                    "SEQEND", "VERTEX"}


# ============================================================
# Helper functions
# ============================================================
def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(max(0, min(255, c))) for c in rgb)


def _aci_hex(aci):
    """ACI -> hex. 7 (white/black) -> application default colour."""
    if aci == 7:
        return FARBEN["cyan"]
    try:
        from ezdxf import colors
        return _hex(colors.aci2rgb(int(aci)))
    except Exception:
        return FARBEN["cyan"]


def _linientyp_name(name):
    n = (name or "").upper()
    if not n or n in ("CONTINUOUS", "BYLAYER", "BYBLOCK"):
        return "Volllinie (schmal)"
    if any(k in n for k in ("CENTER", "PHANTOM", "DASHDOT", "DIVIDE",
                            "ACAD_ISO04", "ACAD_ISO05", "ACAD_ISO10")):
        return "Strichpunktlinie (Achse)"
    if any(k in n for k in ("DASH", "HIDDEN", "ACAD_ISO02", "ACAD_ISO03")):
        return "Strichlinie (verdeckt)"
    if "DOT" in n:
        return "Freihandlinie"
    return "Volllinie (schmal)"


def _cleanup_text(s):
    if not s:
        return ""
    s = (s.replace("%%d", "°").replace("%%D", "°")
          .replace("%%p", "±").replace("%%P", "±")
          .replace("%%c", "Ø").replace("%%C", "Ø")
          .replace("%%%", "%"))
    return s.replace("\r\n", "\n").replace("\r", "\n")


def _extrusion_z(e):
    try:
        if e.dxf.hasattr("extrusion"):
            return float(e.dxf.extrusion[2])
    except Exception:
        pass
    return 1.0


# ============================================================
# Converter
# ============================================================
class DxfImporter:
    """Converts an ezdxf document into KatieCAD elements."""

    def __init__(self, doc, layers, einheit_auto=True):
        self.doc = doc
        self.layers = layers              # dict name -> layer (extended as needed)
        self.elemente = []
        self.uebersprungen = Counter()
        self.fehler = 0
        self.neue_layer = []
        self.faktor = 1.0
        if einheit_auto:
            try:
                u = int(doc.header.get("$INSUNITS", 0) or 0)
                self.faktor = _EINHEIT_MM.get(u, 1.0)
            except Exception:
                self.faktor = 1.0
        self._layer_lt = {}
        self._layer_aus = set()
        self._layer_lesen()

    # ---- Layers ------------------------------------------------
    def _layer_lesen(self):
        try:
            for l in self.doc.layers:
                name = l.dxf.name
                aus = False
                try:
                    aus = l.is_off() or l.is_frozen()
                except Exception:
                    pass
                if aus:
                    self._layer_aus.add(name)
                self._layer_lt[name] = _linientyp_name(l.dxf.get("linetype", ""))
                if name in self.layers:
                    continue
                farbe = FARBEN["cyan"]
                try:
                    if l.dxf.hasattr("true_color"):
                        farbe = _hex(ezdxf.colors.int2rgb(l.dxf.true_color))
                    else:
                        farbe = _aci_hex(abs(l.dxf.get("color", 7)))
                except Exception:
                    pass
                staerke = 0.35
                try:
                    lw = l.dxf.get("lineweight", -3)
                    if lw and lw > 0:
                        staerke = max(0.13, min(2.0, lw / 100.0))
                except Exception:
                    pass
                self.layers[name] = Layer(name, farbe, staerke,
                                          sichtbar=not aus)
                self.neue_layer.append(name)
        except Exception as ex:
            print(f"[Import] Layertabelle nicht lesbar: {ex}")

    def _sicher_layer(self, name):
        if name not in self.layers:
            self.layers[name] = Layer(name, FARBEN["cyan"], 0.35)
            self.neue_layer.append(name)

    # ---- Common attributes -------------------------------------
    def _attr(self, e):
        layer = "0"
        try:
            layer = e.dxf.get("layer", "0") or "0"
        except Exception:
            pass
        self._sicher_layer(layer)
        kw = {"layer": layer, "farbe": FARBEN["cyan"],
              "linientyp": self._layer_lt.get(layer, "Volllinie (schmal)")}
        try:
            lt = e.dxf.get("linetype", "BYLAYER")
            if lt and lt.upper() not in ("BYLAYER", "BYBLOCK"):
                kw["linientyp"] = _linientyp_name(lt)
        except Exception:
            pass
        try:
            if e.dxf.hasattr("true_color"):
                kw["farbe"] = _hex(ezdxf.colors.int2rgb(e.dxf.true_color))
                kw["eig_farbe"] = True
            else:
                aci = e.dxf.get("color", 256)
                if aci not in (0, 256) and 1 <= aci <= 255:
                    kw["farbe"] = _aci_hex(aci)
                    kw["eig_farbe"] = True
        except Exception:
            pass
        try:
            lw = e.dxf.get("lineweight", -1)
            if lw and lw > 0:
                kw["staerke"] = max(0.13, min(2.0, lw / 100.0))
        except Exception:
            pass
        return kw

    def _p(self, v):
        return (float(v[0]) * self.faktor, float(v[1]) * self.faktor)

    # ---- Main loop ---------------------------------------------
    def importiere(self, entitaeten, tiefe=0):
        for e in entitaeten:
            try:
                self._entity(e, tiefe)
            except Exception as ex:
                self.fehler += 1
                print(f"[Import] {self._typ(e)} nicht importiert: "
                      f"{type(ex).__name__}: {ex}")

    @staticmethod
    def _typ(e):
        try:
            return e.dxftype()
        except Exception:
            return "?"

    def _entity(self, e, tiefe):
        typ = self._typ(e)
        try:
            if e.dxf.get("invisible", 0):
                return
        except Exception:
            pass

        if typ in _EXPLODE:
            if tiefe > 8:
                self.uebersprungen[typ + " (zu tief)"] += 1
                return
            self.importiere(list(e.virtual_entities()), tiefe + 1)
            if typ == "INSERT":
                try:                               # visible attributes
                    self.importiere(list(e.attribs), tiefe + 1)
                except Exception:
                    pass
            return

        m = getattr(self, "_c_" + typ.lower(), None)
        if m is None:
            if typ not in _IGNORIERT_LEISE:
                self.uebersprungen[typ] += 1
            return
        if m(e):
            return
        self.uebersprungen[typ] += 1

    # ---- Simple geometry ---------------------------------------
    def _add(self, el):
        self.elemente.append(el)
        return True

    def _c_line(self, e):
        s, en = self._p(e.dxf.start), self._p(e.dxf.end)
        return self._add(Linie(s[0], s[1], en[0], en[1], **self._attr(e)))

    def _c_circle(self, e):
        c = e.dxf.center
        z = _extrusion_z(e)
        if abs(abs(z) - 1.0) > 1e-6:
            return self._via_pfad(e)
        cx, cy = self._p(c)
        if z < 0:
            cx = -cx
        return self._add(Kreis(cx, cy, e.dxf.radius * self.faktor,
                               **self._attr(e)))

    def _c_arc(self, e):
        z = _extrusion_z(e)
        if abs(abs(z) - 1.0) > 1e-6:
            return self._via_pfad(e)
        cx, cy = self._p(e.dxf.center)
        s, en = e.dxf.start_angle, e.dxf.end_angle
        if z < 0:
            cx = -cx
            s, en = 180.0 - en, 180.0 - s
        return self._add(Bogen(cx, cy, e.dxf.radius * self.faktor,
                               s % 360.0, en % 360.0, **self._attr(e)))

    def _punkte_zu_poly(self, e, pts, geschlossen):
        pts = [self._p(p) for p in pts]
        if len(pts) < 2:
            return False
        return self._add(Polylinie(pts, geschlossen=bool(geschlossen),
                                   **self._attr(e)))

    def _via_pfad(self, e, geschlossen=None):
        """Generic way: ezdxf.path (returns WCS points)."""
        from ezdxf import path as ezpath
        p = ezpath.make_path(e)
        dist = max(self._groesse(e) / 800.0, 1e-9)
        ok = False
        for sub in p.sub_paths():
            pts = list(sub.flattening(dist))
            if len(pts) >= 2:
                geschl = (geschlossen if geschlossen is not None
                          else sub.is_closed)
                ok = self._punkte_zu_poly(e, pts, geschl) or ok
        return ok

    @staticmethod
    def _groesse(e):
        try:
            from ezdxf import bbox
            b = bbox.extents([e])
            return max(b.size.x, b.size.y, 1e-9)
        except Exception:
            return 1000.0

    # ---- Curves ------------------------------------------------
    def _c_ellipse(self, e):
        dist = max(self._groesse(e) / 800.0, 1e-9)
        pts = list(e.flattening(dist))
        tau = 2 * math.pi
        voll = abs((e.dxf.end_param - e.dxf.start_param) - tau) < 1e-6
        return self._punkte_zu_poly(e, pts, voll)

    def _c_spline(self, e):
        dist = max(self._groesse(e) / 1000.0, 1e-9)
        pts = list(e.flattening(dist))
        if len(pts) < 2:
            return False
        return self._punkte_zu_poly(e, pts, getattr(e, "closed", False))

    # ---- Polylines ---------------------------------------------
    def _c_lwpolyline(self, e):
        raw = list(e.get_points("xyb"))
        if any(abs(b) > 1e-9 for (_, _, b) in raw):
            # Bulges -> lines + arcs
            self.importiere(list(e.virtual_entities()), 1)
            return True
        pts = list(e.vertices_in_wcs())
        return self._punkte_zu_poly(e, pts, e.closed)

    def _c_polyline(self, e):
        if e.is_polygon_mesh or e.is_poly_face_mesh:
            return False
        if e.is_2d_polyline and any(
                abs(v.dxf.get("bulge", 0.0)) > 1e-9 for v in e.vertices):
            self.importiere(list(e.virtual_entities()), 1)
            return True
        try:
            pts = list(e.points_in_wcs())
        except Exception:
            pts = [v.dxf.location for v in e.vertices]
        return self._punkte_zu_poly(e, pts, e.is_closed)

    # ---- Areas -------------------------------------------------
    def _c_solid(self, e):
        d = e.dxf
        v = [d.vtx0, d.vtx1, d.vtx3 if d.hasattr("vtx3") else d.vtx2, d.vtx2]
        pts = []
        for p in v:
            q = self._p(p)
            if not pts or (abs(q[0] - pts[-1][0]) > 1e-12 or
                           abs(q[1] - pts[-1][1]) > 1e-12):
                pts.append(q)
        if len(pts) < 3:
            return False
        return self._add(Schraffur(pts, muster="solid", **self._attr(e)))

    _c_trace = _c_solid

    def _c_3dface(self, e):
        d = e.dxf
        pts = [self._p(p) for p in (d.vtx0, d.vtx1, d.vtx2, d.vtx3)]
        return self._add(Polylinie(pts, geschlossen=True, **self._attr(e)))

    def _c_leader(self, e):
        return self._punkte_zu_poly(e, list(e.vertices), False)

    def _c_hatch(self, e):
        from ezdxf import path as ezpath
        dist = max(self._groesse(e) / 800.0, 1e-9)
        polys = []
        for sub in ezpath.make_path(e).sub_paths():
            pts = [self._p(p) for p in sub.flattening(dist)]
            if len(pts) >= 3:
                polys.append(pts)
        if not polys:
            return False

        def flaeche(pts):
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            return (max(xs) - min(xs)) * (max(ys) - min(ys))
        polys.sort(key=flaeche, reverse=True)
        aussen = polys[0]
        xs = [p[0] for p in aussen]
        ys = [p[1] for p in aussen]
        diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
        kw = self._attr(e)
        solid = bool(e.dxf.get("solid_fill", 0))
        winkel = 45.0
        try:
            if not solid:
                winkel = float(e.pattern.lines[0].angle) if e.pattern else 45.0
        except Exception:
            pass
        abstand = max(diag / 25.0, 1e-6)
        self._add(Schraffur(aussen, muster="solid" if solid else "linien",
                            winkel=winkel, abstand=abstand, **kw))
        for ins in polys[1:]:                     # Islands as outline
            self._add(Polylinie(ins, geschlossen=True, **self._attr(e)))
        return True

    # ---- Text --------------------------------------------------
    def _text_el(self, e, inhalt, pos, hoehe, winkel, ep):
        inhalt = _cleanup_text(inhalt)
        if not inhalt.strip():
            return True
        x, y = self._p(pos)
        return self._add(Text(x, y, inhalt, max(hoehe * self.faktor, 1e-6),
                              float(winkel or 0.0), "Arial",
                              einfuegepunkt=ep, **self._attr(e)))

    def _c_text(self, e):
        align, p1, p2 = e.get_placement()
        name = getattr(align, "name", str(align))
        ep = _ALIGN_MAP.get(name, "unten_links")
        pos = p1
        return self._text_el(e, e.dxf.text, pos, e.dxf.get("height", 3.5),
                             e.dxf.get("rotation", 0.0), ep)

    _c_attrib = _c_text

    def _c_mtext(self, e):
        try:
            inhalt = e.plain_text()
        except Exception:
            inhalt = e.text
        try:
            winkel = e.get_rotation()
        except Exception:
            winkel = e.dxf.get("rotation", 0.0)
        ep = _MTEXT_ATTACH.get(e.dxf.get("attachment_point", 1), "oben_links")
        return self._text_el(e, inhalt, e.dxf.insert,
                             e.dxf.get("char_height", 3.5), winkel, ep)


# ============================================================
# Reading files
# ============================================================
def dxf_lesen(pfad):
    """Reads DXF; falls back to ezdxf.recover on errors.
    Returns: (doc, hints:list[str])"""
    hinweise = []
    try:
        return ezdxf.readfile(pfad), hinweise
    except (ezdxf.DXFStructureError, UnicodeDecodeError, ezdxf.DXFError):
        doc, auditor = _recover.readfile(pfad)
        if auditor.has_errors:
            hinweise.append(f"{len(auditor.errors)} reparierte Fehler")
        return doc, hinweise


def _oda_pfad_setzen():
    """Looks for the ODA File Converter in the usual locations (Windows)."""
    if not sys.platform.startswith("win"):
        return
    import glob
    kandidaten = []
    for basis in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                  os.environ.get("ProgramFiles(x86)",
                                 r"C:\Program Files (x86)")):
        kandidaten += glob.glob(os.path.join(basis, "ODA",
                                             "ODAFileConverter*",
                                             "ODAFileConverter.exe"))
    if kandidaten:
        try:
            ezdxf.options.set("odafc-addon", "win_exec_path",
                              sorted(kandidaten)[-1])
        except Exception:
            pass


def dwg_zu_dxf_doc(pfad):
    """Converts DWG -> ezdxf document.
    Order: ODA File Converter, LibreDWG (dwg2dxf).
    Returns: (doc, source) or raises RuntimeError with help text."""
    fehler = []
    # 1) ODA File Converter
    try:
        from ezdxf.addons import odafc
        _oda_pfad_setzen()
        if odafc.is_installed():
            return odafc.readfile(pfad), "ODA File Converter"
        fehler.append("ODA File Converter nicht gefunden")
    except Exception as ex:
        fehler.append(f"ODA: {ex}")
    # 2) LibreDWG
    exe = shutil.which("dwg2dxf")
    if exe:
        try:
            with tempfile.TemporaryDirectory() as td:
                ziel = os.path.join(td, "out.dxf")
                subprocess.run([exe, "-y", "-o", ziel, pfad], check=True,
                               capture_output=True, timeout=300)
                return dxf_lesen(ziel)[0], "LibreDWG"
        except Exception as ex:
            fehler.append(f"LibreDWG: {ex}")
    else:
        fehler.append("LibreDWG (dwg2dxf) nicht gefunden")
    # 3) ezdwg (pure Python package, installed with requirements.txt):
    #    DWG -> temporary DXF, then the normal DXF import
    try:
        doc = _ezdwg_zu_dxf_doc(pfad)
        return doc, "ezdwg"
    except Exception as ex:
        fehler.append(f"ezdwg: {ex}")
    raise RuntimeError("; ".join(fehler))


def _ezdwg_zu_dxf_doc(pfad):
    """Converts a DWG with ezdwg into a DXF file and reads it with ezdxf."""
    import ezdwg
    with tempfile.TemporaryDirectory() as td:
        ziel = os.path.join(td, "out.dxf")
        # No "types" filter: export everything ezdwg supports (a fixed
        # list would drop e.g. old POLYLINE/VERTEX, SOLID or LEADER).
        try:
            ezdwg.to_dxf(pfad, ziel, dxf_version="R2010")
        except TypeError:
            ezdwg.to_dxf(pfad, ziel)
        return dxf_lesen(ziel)[0]


# ---- ezdwg last resort (API not stable -> tolerant) ---------------
def _g(obj, name, default=None):
    """Reads an attribute OR dict entry from e / e.dxf."""
    for quelle in (getattr(obj, "dxf", None), obj):
        if quelle is None:
            continue
        if isinstance(quelle, dict):
            if name in quelle:
                return quelle[name]
        elif hasattr(quelle, name):
            v = getattr(quelle, name)
            return v() if callable(v) else v
    return default


def _xy(p):
    if hasattr(p, "x"):
        return float(p.x), float(p.y)
    return float(p[0]), float(p[1])


def ezdwg_lesen(pfad, layers):
    import ezdwg
    doc = ezdwg.read(pfad)
    msp = doc.modelspace()
    elemente, fehler = [], 0
    try:
        liste = list(msp.query("LINE LWPOLYLINE CIRCLE ARC TEXT MTEXT"))
    except Exception:
        liste = list(msp)
    for e in liste:
        try:
            t = e.dxftype() if callable(getattr(e, "dxftype", None)) \
                else getattr(e, "dxftype", "")
            layer = _g(e, "layer", "0") or "0"
            if layer not in layers:
                layers[layer] = Layer(layer, FARBEN["cyan"], 0.35)
            kw = {"layer": layer, "farbe": FARBEN["cyan"],
                  "linientyp": "Volllinie (schmal)"}
            if t == "LINE":
                a, b = _xy(_g(e, "start")), _xy(_g(e, "end"))
                elemente.append(Linie(a[0], a[1], b[0], b[1], **kw))
            elif t == "CIRCLE":
                c = _xy(_g(e, "center"))
                elemente.append(Kreis(c[0], c[1], float(_g(e, "radius")), **kw))
            elif t == "ARC":
                c = _xy(_g(e, "center"))
                elemente.append(Bogen(c[0], c[1], float(_g(e, "radius")),
                                      float(_g(e, "start_angle")),
                                      float(_g(e, "end_angle")), **kw))
            elif t == "LWPOLYLINE":
                pts = _g(e, "points") or _g(e, "get_points")
                pts = [_xy(p) for p in pts]
                geschl = bool(_g(e, "closed", False)) or bool(
                    int(_g(e, "flags", 0) or 0) & 1)
                elemente.append(Polylinie(pts, geschlossen=geschl, **kw))
            elif t in ("TEXT", "MTEXT"):
                p = _xy(_g(e, "insert"))
                s = _g(e, "text", "") or ""
                h = float(_g(e, "height", None) or _g(e, "char_height", 3.5))
                elemente.append(Text(p[0], p[1], _cleanup_text(s), h, 0.0,
                                     "Arial", **kw))
            else:
                fehler += 1
        except Exception as ex:
            fehler += 1
            print(f"[DWG/ezdwg] Element uebersprungen: {ex}")
    return elemente, fehler


# ============================================================
# Public entry points
# ============================================================
class ImportErgebnis:
    def __init__(self):
        self.elemente = []
        self.uebersprungen = Counter()
        self.fehler = 0
        self.neue_layer = []
        self.faktor = 1.0
        self.quelle = ""
        self.hinweise = []


def importiere_datei(pfad, layers):
    """Reads .dxf or .dwg and returns an ImportErgebnis.
    'layers' (dict) is extended with new layers.
    Raises exceptions with a readable message."""
    ext = os.path.splitext(pfad)[1].lower()
    erg = ImportErgebnis()

    if ext == ".dwg":
        if not EZDXF_OK:
            raise RuntimeError("ezdxf ist nicht installiert (pip install ezdxf).")
        try:
            doc, erg.quelle = dwg_zu_dxf_doc(pfad)
        except RuntimeError as konv_fehler:
            raise RuntimeError(
                "Die DWG-Datei konnte nicht gelesen werden (weder ezdwg noch "
                "ein Konverter war erfolgreich).\n\n"
                "Installiere ggf. den kostenlosen 'ODA File Converter' "
                "(opendesign.com/guestfiles/oda_file_converter) und starte "
                "KatieCAD neu - er wird dann automatisch gefunden.\n"
                "Alternativ: Datei in AutoCAD/LibreCAD/DraftSight als DXF "
                "speichern und den DXF-Import verwenden.\n\n"
                "Details: " + str(konv_fehler))
    else:
        if not EZDXF_OK:
            raise RuntimeError("ezdxf ist nicht installiert (pip install ezdxf).")
        doc, hin = dxf_lesen(pfad)
        erg.hinweise += hin
        erg.quelle = "ezdxf"

    imp = DxfImporter(doc, layers)
    imp.importiere(list(doc.modelspace()))
    erg.elemente = imp.elemente
    erg.uebersprungen = imp.uebersprungen
    erg.fehler = imp.fehler
    erg.neue_layer = imp.neue_layer
    erg.faktor = imp.faktor
    return erg

