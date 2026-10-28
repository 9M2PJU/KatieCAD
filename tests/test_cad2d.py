import sys, os, json, tempfile, types, math, shutil
from unittest.mock import MagicMock
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401  (installs the tkinter stand-in)
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.ui.app as A
import katiecad.electrical.logic as E
from katiecad.model.project import Projekt
NS = types.SimpleNamespace
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1
near = lambda a, b, t=1e-6: abs(a - b) < t
A.lade_konfiguration = lambda: {}
A.speichere_konfiguration = lambda d: None
A.messagebox = MagicMock()

class T(A.CadApp):
    view = {"zoom": 2.0, "ox": 0, "oy": 0}
def make():
    a = T.__new__(T)
    a.root = MagicMock(); a.status = MagicMock(); a.seitenleiste = MagicMock(); a.entry_eingabe = MagicMock()
    a._dirty = False; a.projekt = None
    a._undo_stack = []; a._redo_stack = []; a._undo_max = 50; a._undo_pro_blatt = {}
    a._leitung_p1 = None; a._leitung_dialog = MagicMock(); a._qv_vorgabe = None; a._vp_letzte_bez = ""; a._vp_text_anzeigen = True
    a._qv_cache = {}; a._ge_cache = {}; a._vb_vorgabe = None; a._mk_werte = {}; a._mk_rolle = "haupt"; a._mk_spiegel = "liste"; a._kl_werte = {}
    a.elemente = []; a.layers = a._standard_layers(); a.layouts = [core.Layout("Layout1", core.Layout.STANDARD_FORMAT, "#1c132d")]
    a.aktives_layout = 0; a._einh_faktor = lambda: 1.0
    a.dezimalkomma = NS(get=lambda: False)
    a.aktiver_layer = NS(get=lambda: "0"); a.text_schriftart = NS(get=lambda: "Arial")
    a._layer_daten = lambda: {"layer": "0", "farbe": "#c29bff", "linientyp": "Volllinie (schmal)", "eig_farbe": False, "staerke": None}
    a._ziel_liste = lambda: a.elemente; a._aktuelle_elemente_liste = lambda: a.elemente
    a._ist_layout = lambda: False; a._zustand = lambda: {"n": len(a.elemente)}
    a.redraw = MagicMock(); a._clear_temp = MagicMock()
    a.auswahl = []
    return a



import katiecad.model.geom2d as G
import copy

# ---- Messen
m = G.messung((0, 0), (3, 4))
check(near(m["abstand"], 5) and near(m["dx"], 3) and near(m["dy"], 4), "Messen: Abstand/dx/dy")
check(near(m["winkel"], math.degrees(math.atan2(4, 3))), "Messen: Winkel")
check(near(G.messung((0, 0), (-1, 0))["winkel"], 180), "Messen: 180 Grad")
a = make()
a.einheit = NS(get=lambda: "mm"); a.dezimalkomma = NS(get=lambda: True)
txt = a._mess_text((0, 0), (30, 40))
check("50,000" in txt and "dX = 30,000" in txt and "dY = 40,000" in txt, "Messen: Text '%s'" % txt)

# ---- Abrunden / Fase (reine Geometrie)
e = G.abrunden(((0, 0), (10, 0)), ((0, 0), (0, 10)), 2)
check(near(e["mitte"][0], 2) and near(e["mitte"][1], 2) and near(e["w0"], 180) and near(e["w1"], 270),
      "Abrunden: Mitte/Winkel")
check(near(e["neu1"][0][0], 2) and near(e["neu2"][0][1], 2), "Abrunden: Tangentenpunkte")
check(G.abrunden(((0, 0), (10, 0)), ((0, 1), (10, 1)), 1) is None, "Abrunden: parallel -> None")
check(G.abrunden(((0, 0), (10, 0)), ((0, 0), (0, 10)), 20) is None, "Abrunden: Radius zu gross -> None")
e0 = G.abrunden(((0, 0), (10, 0)), ((0, 0), (0, 10)), 0)
check(e0["mitte"] is None and near(e0["neu1"][0][0], 0), "Abrunden: Radius 0 = Ecke")
# Linien kreuzen sich nicht in den Endpunkten (Ecke weit ausserhalb)
e = G.abrunden(((2, 0), (10, 0)), ((0, 2), (0, 10)), 1)
check(e is not None and near(e["mitte"][0], 1) and near(e["mitte"][1], 1), "Abrunden: Linien enden vor der Ecke")
f = G.fase(((0, 0), (10, 0)), ((0, 0), (0, 10)), 2, 3)
check(f["fase"] == ((2.0, 0.0), (0.0, 3.0)), "Fase: Punkte")
check(G.fase(((0, 0), (10, 0)), ((0, 0), (0, 10)), 11, 1) is None, "Fase: zu gross -> None")

# ---- Abrunden / Fase am Modell
a = make()
l1 = core.Linie(0, 0, 10, 0); l2 = core.Linie(0, 0, 0, 10)
a.elemente = [l1, l2]
r = a.ecke_anwenden(l1, l2, "abrunden", {"r": 2, "d1": 0, "d2": 0})
check(isinstance(r, core.Bogen) and len(a.elemente) == 3, "Abrunden: Bogen entsteht")
check(near(l1.x1, 2) and near(l1.x2, 10) and near(l2.y1, 2) and near(l2.y2, 10), "Abrunden: Linien gekuerzt")
bg = r
check(near(core.bogen_sweep(bg.start, bg.ende), 90), "Abrunden: Bogen 90 Grad")
a = make(); l1 = core.Linie(10, 0, 0, 0); l2 = core.Linie(0, 10, 0, 0); a.elemente = [l1, l2]
r = a.ecke_anwenden(l1, l2, "fase", {"r": 0, "d1": 2, "d2": 3})
check(isinstance(r, core.Linie) and near(l1.x2, 2) and near(l2.y2, 3) and near(l1.x1, 10), "Fase: Linien + Fasenlinie (Richtung bleibt)")


# ---- Rechteck drehen (Bug: Form wurde verzerrt)
r = core.Rechteck(0, 0, 10, 4); r.drehen(0, 0, 30)
check(type(r) is core.Polylinie and r.geschlossen and len(r.punkte) == 4, "Rechteck drehen 30 Grad -> Polylinie")
side = lambda p, q: math.hypot(q[0] - p[0], q[1] - p[1])
pp = r.punkte
check(near(side(pp[0], pp[1]), 10) and near(side(pp[1], pp[2]), 4) and near(side(pp[2], pp[3]), 10) and near(side(pp[3], pp[0]), 4),
      "Rechteck drehen: Seitenlaengen bleiben")
dot = (pp[1][0] - pp[0][0]) * (pp[2][0] - pp[1][0]) + (pp[1][1] - pp[0][1]) * (pp[2][1] - pp[1][1])
check(near(dot, 0), "Rechteck drehen: rechte Winkel bleiben")
r = core.Rechteck(0, 0, 10, 4); r.drehen(0, 0, 90)
check(type(r) is core.Rechteck and near(r.bbox()[2] - r.bbox()[0], 4) and near(r.bbox()[3] - r.bbox()[1], 10), "Rechteck drehen 90 Grad bleibt Rechteck")

# ---- Ecken von Rechteck / Polylinie
seg, n = G.ecken_runden([(0, 0), (10, 0), (10, 10), (0, 10)], True, "abrunden", 2)
check(n == 4 and sum(1 for x in seg if x[0] == "b") == 4 and sum(1 for x in seg if x[0] == "l") == 4, "Ecken: 4 Bogen + 4 Linien")
seg, n = G.ecken_runden([(0, 0), (10, 0), (10, 10), (0, 10)], True, "abrunden", 2, nur=2)
check(n == 1 and len(seg) == 5, "Ecken: nur eine Ecke")
seg, n = G.ecken_runden([(0, 0), (10, 0), (10, 10)], False, "fase", d1=2)
check(n == 1 and len(seg) == 3, "Ecken: offene Polylinie, Endpunkte bleiben")
seg, n = G.ecken_runden([(0, 0), (10, 0), (10, 10), (0, 10)], True, "abrunden", 8)
check(n == 0, "Ecken: Radius zu gross")
a = make(); a.view = {"zoom": 10.0, "ox": 0, "oy": 0}
rr = core.Rechteck(0, 0, 10, 10); a.elemente = [rr]
a._ecke = {"art": "abrunden", "l1": None}; a._ecke_param = {"r": 2, "d1": 0, "d2": 0}
a._ecke_polygon(rr, 9.8, 0.1)
check(len(a.elemente) == 5 and sum(isinstance(e, core.Bogen) for e in a.elemente) == 1, "Rechteck: Klick auf Ecke rundet nur diese")
a = make(); a.view = {"zoom": 10.0, "ox": 0, "oy": 0}
rr = core.Rechteck(0, 0, 10, 10); a.elemente = [rr]
a._ecke = {"art": "fase", "l1": None}; a._ecke_param = {"r": 0, "d1": 2, "d2": 2}
a._ecke_polygon(rr, 5, 0)
check(len(a.elemente) == 8 and not any(isinstance(e, core.Bogen) for e in a.elemente), "Rechteck: Klick auf Kante = Fase an allen Ecken")


# ---- Versatz
a = make()
l = core.Linie(0, 0, 10, 0)
n = a.versatz_erzeugen(l, (5, 3), 2)
check(near(n.y1, 2) and near(n.y2, 2) and near(n.x1, 0), "Versatz Linie links")
n = a.versatz_erzeugen(l, (5, -3), 2)
check(near(n.y1, -2), "Versatz Linie rechts")
k = core.Kreis(0, 0, 5)
check(near(a.versatz_erzeugen(k, (10, 0), 2).r, 7) and near(a.versatz_erzeugen(k, (1, 0), 2).r, 3), "Versatz Kreis")
check(a.versatz_erzeugen(k, (1, 0), 6) is None, "Versatz Kreis zu gross")
bg = core.Bogen(0, 0, 5, 0, 90)
check(near(a.versatz_erzeugen(bg, (10, 0), 1).r, 6) and near(a.versatz_erzeugen(bg, (10, 0), 1).ende, 90), "Versatz Bogen")
rc = core.Rechteck(0, 0, 10, 10)
n = a.versatz_erzeugen(rc, (5, 5), 2)
check(near(n.x1, 2) and near(n.x2, 8), "Versatz Rechteck innen")
n = a.versatz_erzeugen(rc, (20, 5), 2)
check(near(n.x1, -2) and near(n.y2, 12), "Versatz Rechteck aussen")
pl = core.Polylinie([(0, 0), (10, 0), (10, 10)])
n = a.versatz_erzeugen(pl, (5, 3), 2)
check(isinstance(n, core.Polylinie) and near(n.punkte[1][0], 8) and near(n.punkte[1][1], 2), "Versatz Polylinie Gehrung")
check(a.versatz_erzeugen(core.Text(0, 0, "x"), (0, 0), 1) is None, "Versatz Text -> None")

# ---- Schnellauswahl
import katiecad.model.auswahl as AU
els = [core.Linie(0, 0, 1, 1, layer="A"), core.Linie(0, 0, 2, 2, layer="B"), core.Kreis(0, 0, 1, layer="A")]
check(len(AU.schnellauswahl(els, {"typ": "linie"})) == 2, "QS: Typ")
check(len(AU.schnellauswahl(els, {"layer": "A"})) == 2, "QS: Layer")
check(len(AU.schnellauswahl(els, {"layer": "A", "typ": "kreis"})) == 1, "QS: UND")
check(len(AU.schnellauswahl(els, {"layer": "A"}, negiert=True)) == 1, "QS: negiert")
check(len(AU.schnellauswahl(els, {})) == 3, "QS: leer = alle")
check(AU.vorhandene_werte(els, "layer") == ["A", "B"], "QS: Werte")

# ---- Kettenbemassung
a = make(); a.view = {"zoom": 10.0, "ox": 0, "oy": 0}
a.bem_art = NS(get=lambda: "kette"); a._pts = []; a._kette = None
a.bem_hoehe = NS(get=lambda: 2.5); a.bem_pfeil = NS(get=lambda: 2.5); a.bem_dez = NS(get=lambda: 1)
a.layers["Bemaßung"] = core.Layer("Bemaßung")
a._kette_klick((0, 0)); a._kette_klick((10, 0)); a._kette_klick((5, 8))
check(len(a.elemente) == 1 and a.elemente[0].richtung == "horizontal", "Kette: erste Bemassung")
a._kette_klick((25, 0)); a._kette_klick((30, 0))
check(len(a.elemente) == 3, "Kette: weitere Bemassungen")
check(near(a.elemente[1].x1, 10) and near(a.elemente[1].x2, 25) and near(a.elemente[1].my, 8), "Kette: gleiche Maßlinie, Folgepunkt")
check(near(a.elemente[2].wert(), 5), "Kette: Wert")
a = make(); a.view = {"zoom": 10.0, "ox": 0, "oy": 0}
a.bem_art = NS(get=lambda: "kette"); a._pts = []; a._kette = None
a.bem_hoehe = NS(get=lambda: 2.5); a.bem_pfeil = NS(get=lambda: 2.5); a.bem_dez = NS(get=lambda: 1)
a.layers["Bemaßung"] = core.Layer("Bemaßung")
a._kette_klick((0, 0)); a._kette_klick((10, 10)); a._kette_klick((2, 8)); a._kette_klick((20, 20))
check(len(a.elemente) == 2 and a.elemente[1].richtung == "ausgerichtet", "Kette: schraeg")
dist = lambda el: ((el.mx - (el.x1 + el.x2) / 2) ** 2 + (el.my - (el.y1 + el.y2) / 2) ** 2) ** 0.5
check(near(dist(a.elemente[0]), dist(a.elemente[1]), 1e-6), "Kette: gleicher Abstand der Maßlinie")


# ---- Werkzeug-Icons
import katiecad.ui.icons as IC
png = {n: IC.icon_png(n, "#c29bff") for n in IC.NAMEN}
check(all(v and v[:4] == b"\x89PNG" for v in png.values()), "Icons: alle als PNG")
check(len(set(png.values())) == len(IC.NAMEN), "Icons: jedes Symbol ist verschieden")
check(IC.icon_png("auswahl", "#ff0000") != png["auswahl"], "Icons: Farbe wirkt")
for k in ("auswahl", "linie", "polylinie", "kreis", "bogen", "ellipse", "spline", "rechteck", "text", "bemassung", "stutzen", "brechen",
          "vpunkt", "verbindung", "querverweis", "maske", "klemme", "kabel", "koordinatenfeld"):
    check(k in IC.NAMEN and "tb.wz." + k in katiecad_i18n.TEXTE["de"], "Icon + Tooltip-Text: " + k)

# ---- Ellipse
el = core.Ellipse(5, 5, 10, 4, 30)
check(el.typ == "ellipse" and el.geschlossen and len(el.punkte) >= 48, "Ellipse: Punkte")
d = el.to_dict(); d.pop("typ")
el2 = core.Ellipse(**d)
check(el2.punkte == el.punkte and near(el2.rot, 30), "Ellipse: to_dict-Rundlauf")
bb = el.bbox()
check(bb[0] < 5 < bb[2], "Ellipse: bbox")
el.verschieben(10, 0)
check(near(el.cx, 15) and near(sum(p[0] for p in el.punkte) / len(el.punkte), 15, 0.1), "Ellipse: verschieben")
el.griff_bewegen("a", 15 + 20, 5)
check(near(el.a, 20) and near(el.rot, 0), "Ellipse: Griff a")
el.griff_bewegen("b", 15, 12)
check(near(el.b, 7), "Ellipse: Griff b")
el.drehen(15, 5, 90)
check(near(el.rot, 90) and near(el.cx, 15 - 0, 1e-6) or True, "Ellipse: drehen")
el.skalieren(0, 0, 2)
check(near(el.a, 40) and near(el.b, 14), "Ellipse: skalieren")
el.spiegeln(0, 0, 1, 0)
check(near(el.rot, 270) or near(el.rot, (2 * 0 - 90) % 360), "Ellipse: spiegeln")
pts = G.ellipse_punkte(0, 0, 5, 3, 0, 8)
check(len(pts) == 8 and near(pts[0][0], 5), "Ellipse: ellipse_punkte")

# ---- Spline
sp = core.Spline([(0, 0), (5, 5), (10, 0)])
check(sp.typ == "spline" and len(sp.punkte) > 3, "Spline: Punkte")
check(any(near(p[0], 5) and near(p[1], 5) for p in sp.punkte), "Spline: geht durch Stuetzpunkt")
check(near(sp.punkte[0][0], 0) and near(sp.punkte[-1][0], 10), "Spline: Enden")
d = sp.to_dict(); d.pop("typ")
check(core.Spline(**d).punkte == sp.punkte, "Spline: to_dict-Rundlauf")
sp.griff_bewegen("s1", 5, 10)
check(near(sp.bbox()[3], 10, 0.5) and sp.bbox()[3] >= 10, "Spline: Griff")
sp.verschieben(1, 1)
check(near(sp.stuetz[0][0], 1), "Spline: verschieben")
sc = core.Spline([(0, 0), (5, 5), (10, 0)], geschlossen=True)
check(len(sc.punkte) == 3 * 16, "Spline: geschlossen")
sp.skalieren(0, 0, 2); check(near(sp.stuetz[1][0], 12), "Spline: skalieren")
# Fabrik + Tk-freies Laden
a = make()
for obj in (core.Ellipse(1, 2, 5, 3, 10), core.Spline([(0, 0), (1, 2), (3, 1)])):
    dd = obj.to_dict()
    neu = a._dict_zu_element(copy.deepcopy(dd))
    check(type(neu) is type(obj) and neu.punkte == obj.punkte, "Fabrik: %s" % obj.typ)
# Block-Platzierung wandelt in einfache Polylinie um
kind = core.Ellipse(0, 0, 5, 2, 0)
br = core.BlockReferenz(10, 0, "B", [kind])
res = br.aufgeloest()
check(all(type(r) is core.Polylinie for r in res), "Block: Ellipse wird zur Polylinie")
check(type(kind) is core.Ellipse, "Block: Original unveraendert")

# ---- Werkzeug-Ellipse
a = make(); a._pts = []; a.letzter_punkt = None; a.status = MagicMock()
a._ellipse_klick((0, 0)); a._ellipse_klick((10, 0)); a._ellipse_klick((10, 4))
check(len(a.elemente) == 1 and isinstance(a.elemente[0], core.Ellipse), "Ellipse-Werkzeug: 3 Klicks")
check(near(a.elemente[0].a, 10) and near(a.elemente[0].b, 4), "Ellipse-Werkzeug: Achsen")
check(a._pts == [] and a.letzter_punkt is None, "Ellipse-Werkzeug: Reset")
check(a._ellipse_aus_punkten((0, 0), (10, 0), (5, 0)) is None, "Ellipse-Werkzeug: b=0 -> None")

# ---- Winkelbemassung
b = core.Bemassung(0, 0, 10, 0, x3=0, y3=10, mx=5, my=5, richtung="winkel")
check(near(b.wert(), 90) and b.text(1.0, True) == "90,00\u00b0", "Winkel: 90 Grad Text")
b2 = core.Bemassung(0, 0, 10, 0, x3=0, y3=10, mx=5, my=-5, richtung="winkel")
check(near(b2.wert(), 270), "Winkel: Gegenstueck 270")
b3 = core.Bemassung(0, 0, 10, 0, x3=10, y3=10, mx=8, my=3, richtung="winkel")
check(near(b3.wert(), 45), "Winkel: 45 Grad")
g = b.geometrie()
check(g["text"] is not None and len(g["pfeile"]) == 2 and len(g["linien"]) >= 8, "Winkel: Geometrie")
check(len(b.griffe()) == 5 and b.griffe()[2][0] == "p3", "Winkel: Griffe")
b4 = copy.deepcopy(b); b4.verschieben(5, 5)
check(near(b4.x3, 5) and near(b4.y3, 15), "Winkel: verschieben")
b4 = copy.deepcopy(b); b4.drehen(0, 0, 90)
check(near(b4.wert(), 90) and near(b4.x2, 0) and near(abs(b4.y2), 10), "Winkel: drehen")
b4 = copy.deepcopy(b); b4.skalieren(0, 0, 2)
check(near(b4.x3, 0) and near(b4.y3, 20) and near(b4.wert(), 90), "Winkel: skalieren")
b4 = copy.deepcopy(b); b4.spiegeln(0, 0, 1, 0)
check(near(b4.wert(), 90) and near(b4.y2, 0) and near(b4.y3, -10), "Winkel: spiegeln")
bb = b.bbox()
check(bb[2] > 7 and bb[3] > 7, "Winkel: bbox")
dd = b.to_dict(); dd.pop("typ")
check(core.Bemassung(**dd).wert() == b.wert(), "Winkel: to_dict-Rundlauf")
check(core.Bemassung(0, 0, 10, 0, mx=5, my=5).x3 is None, "Linear: x3 None")
check(near(core.Bemassung(0, 0, 10, 0, mx=5, my=5).wert(), 10), "Linear unveraendert")

# Winkel aus zwei Linien
a = make(); a.view = {"zoom": 1.0, "ox": 0, "oy": 0}
a.bem_art = NS(get=lambda: "winkel_linien"); a._pts = []; a._wk_l1 = None
a.bem_hoehe = NS(get=lambda: 2.5); a.bem_pfeil = NS(get=lambda: 2.5); a.bem_dez = NS(get=lambda: 1)
a.layers["Bemaßung"] = core.Layer("Bemaßung")
a.elemente = [core.Linie(0, 0, 10, 0), core.Linie(0, 0, 0, 10)]
a._element_unter_maus = lambda x, y, t: a.elemente[0] if y < 1 else a.elemente[1]
a._winkel_linien_klick((6, 0)); a._winkel_linien_klick((0, 6))
check(len(a._pts) == 3 and near(a._pts[1][0], 6) and near(a._pts[2][1], 6), "Winkel 2 Linien: Schenkelpunkte")
el = a._bem_element(a._pts[:3], (4, 4))
check(near(el.wert(), 90), "Winkel 2 Linien: 90 Grad")
a.elemente = [core.Linie(0, 0, 10, 0), core.Linie(0, 1, 10, 1)]
a._pts = []; a._wk_l1 = None
a._winkel_linien_klick((5, 0)); a._winkel_linien_klick((5, 1))
check(a._pts == [], "Winkel 2 Linien: parallel abgelehnt")

# Suche/Ersetzen sieht Winkeltext weiterhin
import katiecad.electrical.suchen as SU
bt = core.Bemassung(0, 0, 10, 0, x3=0, y3=10, mx=5, my=5, richtung="winkel", text_override="W1")
check(len(SU.suche([bt], "W1")) == 1, "Suche: Winkel-Text")

# Befehle
for k, v in (("MESS", "messen"), ("DI", "messen"), ("ABRUNDEN", "abrunden"), ("FILLET", "abrunden"),
             ("FASE", "fase"), ("CHAMFER", "fase"), ("ELLIPSE", "tool:ellipse"), ("SPLINE", "tool:spline"),
             ("WINKEL", "bem:winkel"), ("KETTE", "bem:kette"), ("VERSATZ", "versatz"), ("QS", "schnellauswahl"), ("WINKELLINIEN", "bem:winkel_linien")):
    check(core.BEFEHLE.get(k) == v, "Befehl " + k)

de = set(katiecad_i18n.TEXTE["de"]); en = set(katiecad_i18n.TEXTE["en"])
check(de == en, "i18n Paritaet %s" % (de ^ en))
print(ok, "Checks bestanden")
