import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.common.i18n as I; I.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
from katiecad.model.core import Rechteck, Koerper3D, Gruppe3D
from katiecad.model import geom3d as G, szene3d as S
import katiecad.ui.app as A
import katiecad.ui.ansicht3d as W
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

# bodies
q = W.koerper_bauen("quader", {"breite": 40, "tiefe": 30, "hoehe": 20}, 10, 10, 0)
check(q.bbox3()[2] == 0 and abs(q.bbox3()[5] - 20) < 1e-9, "Quader Hoehe")
for art, par in (("zylinder", {"radius": 5, "hoehe": 9}), ("kegel", {"radius": 5, "hoehe": 9}),
                 ("pyramide", {"ecken": 5, "breite": 10, "tiefe": 8, "hoehe": 7}), ("kugel", {"radius": 6})):
    k = W.koerper_bauen(art, par, 0, 0, 0)
    check(len(k.netz().kanten) > 3, art)
# hidden line: box iso
k = G.Kamera(); k.ansicht_setzen("iso_so")
s, v = G.sichtbare_linien([q.netz()], k, 400, 300)
check(len(v) >= 3 and len(s) >= 9, "verdeckte Kanten")
nz = q.netz()
s2, v2 = G.sichtbare_linien([nz], k, 400, 300, zeichnen={id(nz)})
check(len(s2) == len(s), "zeichnen-Filter")
s3, _ = G.sichtbare_linien([nz], k, 400, 300, zeichnen=set())
check(not s3, "leerer Filter")
# round trip
g = Gruppe3D([q, W.koerper_bauen("kugel", {"radius": 3}, 0, 0, 0)], name="B")
d = g.to_dict()
a = A.CadApp.__new__(A.CadApp)
g2 = a._dict_zu_element(d)
check(isinstance(g2, Gruppe3D) and len(g2.teile) == 2, "Gruppe round trip")
# extrude / group
r = Rechteck(0, 0, 10, 10)
liste = [r]
neu = S.extrudieren(liste, [r], 15)
check(len(neu) == 1 and isinstance(liste[0], Koerper3D) and abs(liste[0].hoehe - 15) < 1e-9, "extrudieren")
# icons
from katiecad.ui import icons as IC
for n in ("raster3d", "flaeche3d", "skizze_kreis", "skizze_rechteck", "skizze_poly", "ebene0",
          "bem3d", "mass3d"):
    check(n in IC.NAMEN and (not IC.PIL_OK or IC.icon_png(n, "#c29bff")), "Icon " + n)
for n in ("ansicht3d", "k_quader", "k_zylinder", "k_kegel", "k_pyramide", "k_kugel", "extrudieren",
          "loch", "block3d", "aufloesen3d", "wuerfel", "persp", "einpassen3d", "iso3d", "hoehe3d"):
    check(n in IC.NAMEN and (not IC.PIL_OK or IC.icon_png(n, "#c29bff")), "Icon " + n)
# holes
z = core.zylinder(0, 0, 10, 0, 20)
check(S.loch_ziele([z]) == [z], "Loch-Ziel")
check(S.loch_setzen(z, 2, 0, 3, None), "Loch setzen")
check(not S.loch_setzen(z, 50, 0, 3, None), "Loch ausserhalb")
check(len(z.netze()) == 2 and len(z.aufgeloest()) > 2, "Loch im Netz/Plan")
z.verschieben(5, 0, 2)
check(abs(z.loecher[0][0] - 7) < 1e-9, "Loch verschiebt mit")
z2 = a._dict_zu_element(z.to_dict())
check(len(z2.loecher) == 1 and z2.loecher[0][3] is None, "Loch Round-Trip")
z.loch_hinzufuegen(5, 0, 1, 4)
nz = z.netze()[2]
check(abs(nz.bbox()[5] - (2 + 20)) < 1e-6 and abs(nz.bbox()[2] - 18) < 1e-6, "Sackloch Tiefe")
# work plane, sketch, bore, pocket
box = core.quader(0, 0, 40, 30, 0, 20)
szene = [box]
nz = box.netz()
oben = [f for f in nz.flaechen if all(abs(nz.punkte[i][2] - 20) < 1e-9 for i in f)][0]
e = G.ebene_von_flaeche([nz.punkte[i] for i in oben], box.zentrum3())
check(abs(G.ebene_basis(e)[2][2] - 1) < 1e-9 and abs(e[2] - 20) < 1e-9, "Ebene Oberseite")
sk = core.Skizze3D("kreis", e, [20, 15, 5])
szene.append(sk)
check(S.host_finden(szene, e) is box, "Host gefunden")
check(S.skizze_in_ausschnitt(szene, sk, None) and len(szene) == 1 and len(box.netze()) == 2, "Bohrung")
check(abs(box.netze()[1].bbox()[2]) < 1e-6 and abs(box.netze()[1].bbox()[5] - 20) < 1e-6, "Bohrung durchgehend")
b2 = Koerper3D(**{k: v for k, v in box.to_dict().items() if k != "typ"})
check(len(b2.ausschnitte) == 1, "Ausschnitt Round-Trip")
sk2 = core.Skizze3D("rechteck", e, [2, 2, 8, 8])
szene.append(sk2)
neu = S.extrudieren(szene, [sk2], -5)[0]
check(S.extrusion_abschliessen(szene, neu) and len(box.ausschnitte) == 2, "Tasche")
sk3 = core.Skizze3D("rechteck", e, [2, 2, 8, 8])
neu = S.extrudieren([sk3], [sk3], 6)[0]
check(abs(neu.bbox3()[5] - 26) < 1e-6, "Aufsatz nach oben")
check(S.parameter_setzen(box, {"breite": 50, "hoehe": 10}) and abs(box.bbox3()[3] - 50) < 1e-6, "Massaenderung")
kr = core.zylinder(0, 0, 10, 0, 5)
S.parameter_setzen(kr, {"radius": 20})
check(abs(kr.bbox3()[3] - 20) < 1e-6, "Radius aendern")
sk4 = core.Skizze3D("kreis", e, [0, 0, 3]); S.parameter_setzen(sk4, {"radius": 7})
check(sk4.daten[2] == 7, "Skizzenradius")
bm = core.Bemassung3D((0, 0, 0), (30, 40, 0), (0, 0, 5))
check(bm.wert_text() == "50.00" and len(S.zuege3(bm)) >= 3, "Bemassung3D")
bm2 = a._dict_zu_element(bm.to_dict())
check(isinstance(bm2, core.Bemassung3D) and bm2.p2 == (30.0, 40.0, 0.0), "Bemassung3D Round-Trip")
sk5 = a._dict_zu_element(sk.to_dict())
check(isinstance(sk5, core.Skizze3D) and sk5.daten == [20.0, 15.0, 5.0], "Skizze Round-Trip")
# body with its own plane survives move / mirror
pl = core.extrusion(sk3, 6)
pl.verschieben(1, 2, 3); pl.drehen(0, 0, 90); pl.skalieren(0, 0, 2); pl.spiegeln(0, 0, 1, 0)
check(pl.bbox3() is not None and len(pl.netze()) == 1, "Koerper mit Ebene transformieren")
# viewport 3D
vp = core.Viewport(10, 10, 120, 90)
els = [core.quader(0, 0, 40, 30, 0, 20), core.Rechteck(0, 0, 40, 30)]
S.vp_ansicht_setzen(vp, els, 45, 35.264)
check(vp.ansicht3d and vp.zoom > 0, "Viewport 3D gesetzt")
kam = S.vp_kamera(vp, vp.zoom)
lin, txt = S.szene_segmente(els, kam, 0.0, 0.0)
check(len(lin) >= 12, "Viewport Segmente")
check(S.clip_segment(((-10, 5), (10, 5)), (0, 0, 5, 10)) == ((0.0, 5.0), (5.0, 5.0)), "Clip")
check(S.clip_segment(((-10, 50), (10, 50)), (0, 0, 5, 10)) is None, "Clip aussen")
vp2 = a._dict_zu_element(vp.to_dict())
check(vp2.ansicht3d["yaw"] == 45.0, "Viewport Round-Trip")
from katiecad.fileio import pdf as PDF
class _L:
    def __init__(s): s.farbe = "#000000"; s.staerke = 0.35; s.sichtbar = True
seite = PDF.PdfSeite(297, 210)
PDF._pdf_viewport(seite, vp, els + [core.Bemassung3D((0, 0, 0), (40, 0, 0), (0, 0, -5))],
                  {"0": _L()}, False, True, 1.0, True)
check(len(seite.to_bytes()) > 500, "PDF mit 3D-Viewport")
# toolbar docking (pure helpers)
from katiecad.ui import toolbar_dock as TD
check(TD.ziel_position(0.95, 0.5) == "rechts" and TD.ziel_position(0.5, 0.9) == "unten"
      and TD.ziel_position(0.5, 0.05) == "oben" and TD.ziel_position(0.5, 0.5, "unten") == "unten",
      "Docking-Zielposition")
check(TD.spalten_zeilen(50, 700) == 19 and TD.spalten_zeilen(50, 100) == 6, "Spaltenzahl")
check({"menu.ansicht.tb", "menu.ansicht.tb_oben", "menu.ansicht.tb_unten",
       "menu.ansicht.tb_rechts", "tb.griff"} <= set(I.TEXTE["de"]) & set(I.TEXTE["en"]), "Docking i18n")
# menu / commands
check(core.BEFEHLE.get("QUADER") == "3d:neu:quader" and core.BEFEHLE.get("3D") == "3d:oeffnen", "Befehle")
# i18n keys used by the window exist in both languages
import re
src = open(os.path.join(os.path.dirname(W.__file__), "ansicht3d.py"), encoding="utf-8").read()
src += open(os.path.join(os.path.dirname(A.__file__), "app.py"), encoding="utf-8").read()
for spr in ("de", "en"):
    T = I.TEXTE[spr]
    for key in [k for k in re.findall(r'tr\("(d3\.[a-z_.0-9]+|menu\.3d[a-z_.]*)"', src) if not k.endswith((".", "_"))]:
        check(key in T, f"{spr}: {key}")
    for art in W.PARAMETER:
        check("d3.neu." + art in T and "menu.3d." + art in T, art)
        for p in W.PARAMETER[art]:
            check("d3.dlg." + p in T, p)
    for n in ("ansicht3d", "k_quader", "k_zylinder", "k_kegel", "k_pyramide", "k_kugel", "extrudieren",
              "loch", "block3d", "aufloesen3d", "wuerfel", "persp", "einpassen3d", "iso3d", "hoehe3d"):
        check("tb.wz." + n in T, "tooltip " + n)
    for f in G.WUERFEL_FLAECHEN:
        check("d3.ansicht." + f in T, f)
    for n in ("iso_so", "iso_sw", "iso_no", "iso_nw", "oben", "vorne", "hinten", "links", "rechts", "unten"):
        check("d3.vp." + n in T, "vp " + n)
    for k in ("menue", "fenster", "aus", "nicht_aktivierbar"):
        check("d3.vp." + k in T, "vp " + k)
    check("menu.3d.loch" in T and "d3.neu.loch" in T and "menu.3d.mass" in T, "loch")
    for m in W.Ansicht3D.MODI:
        check("d3.modus." + m in T, "modus " + m)
    for m in ("kreis", "rechteck", "poly"):
        check("d3.msg.skizze_" + m in T, "skizze " + m)
    for n in ("raster3d", "flaeche3d", "skizze_kreis", "skizze_rechteck", "skizze_poly", "ebene0",
              "bem3d", "mass3d"):
        check("tb.wz." + n in T, "tooltip " + n)

# ---- snap candidates, line sketch, toolbars per department (v1.1.0, round 3) ----
from katiecad.model.core import Kreis as _Kr, Linie as _Li
_kand = S.fang_kandidaten([core.quader(0, 0, 40, 30, 0, 20), _Kr(5, 5, 3), _Li(0, 0, 10, 0)])
_arten = {a for _p, a in _kand}
check(_arten == {"end", "mitte", "zentrum"}, "Fangarten end/mitte/zentrum")
check(any(a == "zentrum" and p == (5.0, 5.0, 0.0) for p, a in _kand), "Kreis-Zentrum als Fangpunkt")
check(any(a == "mitte" and p == (20.0, 0.0, 0.0) for p, a in _kand), "Kantenmitte als Fangpunkt")
_kam = G.Kamera(yaw=-45.0, pitch=35.264)
_q = _kam.proj((40.0, 0.0, 20.0), 400, 300)
_r = S.fang_suche([core.quader(0, 0, 40, 30, 0, 20)], _kam, 400, 300, _q[0] + 3, _q[1] + 2)
check(_r is not None and _r[1] == "end" and _r[0] == (40.0, 0.0, 20.0), "fang_suche Ecke")
_ln = core.Skizze3D("linie", G.BODEN_EBENE, [0, 0, 30, 40])
check(len(_ln.profil()) == 2 and not _ln.geschlossen() and not S.extrudierbar(_ln), "Linien-Skizze")
check(len(_ln.aufgeloest()) == 1 and S.zuege3(_ln)[0][1] is False, "Linie offen")
_ln.spiegeln(0, 0, 1, 0)
check(_ln.daten == [0, 0, 30, -40], "Linie spiegeln")
_d = core.Skizze3D("linie", G.BODEN_EBENE, [1, 2, 3, 4]).to_dict(); _d.pop("typ", None)
check(core.Skizze3D(**_d).daten == [1, 2, 3, 4] and core.Skizze3D(**_d).form == "linie", "Linie Round-Trip")
check(TD.LEISTEN == ("werkzeug", "elektro", "3d") and set(TD.CONFIG_KEY) == set(TD.LEISTEN),
      "drei Werkzeugleisten")
for k in ("menu.ansicht.tb_werkzeug", "menu.ansicht.tb_elektro", "menu.ansicht.tb_3d", "d3.vp.waehlen",
          "d3.vp.an", "d3.fang.end", "d3.fang.mitte", "d3.fang.zentrum", "d3.fang.raster",
          "d3.modus.linie", "d3.msg.skizze_linie", "tb.wz.skizze_linie"):
    for T in (I.TEXTE["de"], I.TEXTE["en"]):
        check(k in T, k)
_k0 = G.Kamera(yaw=0, pitch=0)
_el0 = [core.quader(0, 0, 40, 100, 0, 20)]
_q0 = _k0.proj((0, 0, 20), 400, 300)
_f0 = S.flaeche_pick(_el0, _k0, 400, 300, _q0[0], _q0[1])
check(_f0 is not None and abs(G.ebene_basis(_f0[1])[2][1]) > 0.99, "Fläche an Ecke in Frontansicht")
check({"menu.ansicht.tb_vor", "menu.ansicht.tb_zurueck"} <= set(I.TEXTE["de"]) & set(I.TEXTE["en"]), "tb Reihenfolge i18n")
check(callable(TD.ToolbarDockMixin.toolbar_vor) and callable(TD.ToolbarDockMixin.toolbar_verschieben), "tb Reihenfolge")

# ---- round 4: rotate, round edges, dashed cut-outs, selection window, host by position ----
_k = core.quader(0, 0, 40, 30, 0, 20)
_k.loch_hinzufuegen(20, 15, 4, None)
_k.drehen3((20, 15, 10), (1, 0, 0), 90)
_b = _k.bbox3()
check(abs(_b[2] - -5) < 1e-6 and abs(_b[5] - 25) < 1e-6 and len(_k.loecher) == 0 and len(_k.ausschnitte) == 1,
      "3D drehen um X (Loch wird Ausschnitt)")
_g = core.Gruppe3D([core.quader(0, 0, 10, 10, 0, 10), core.quader(20, 0, 30, 10, 0, 10)])
check(S.drehen3d([_g], (0, 0, 0), (0, 0, 1), 90) == 1 and abs(_g.bbox3()[0] - -10) < 1e-6, "Gruppe drehen um Z")
check(S.drehen3d([Rechteck(0, 0, 10, 10)], (0, 0, 0), (1, 0, 0), 90) == 0, "2D nur um Z drehbar")
_r = core.quader(0, 0, 40, 30, 0, 20)
check(_r.kanten_abrunden(5) and sum(_r.glatt) == 20 and len(_r.profil) == 28, "Kanten abrunden")
_d = _r.to_dict(); _d.pop("typ", None)
check(core.Koerper3D(**_d).glatt == _r.glatt, "glatt Round-Trip")
check(not core.zylinder(0, 0, 10, 10, 20).kanten_abrunden(2), "Zylinder nicht abrundbar")
_p, _gl = G.profil_abrunden([(0, 0), (10, 0), (10, 10), (0, 10)], 100)
check(len(_p) == 28, "Radius wird begrenzt")
_h = core.quader(0, 0, 40, 30, 0, 20)
_h.ausschnitt_hinzufuegen((10, 0, 20, 1, 0, 0, 0, 0, 1), [(0, 0), (5, 0), (5, 5)], None, False)
_typen = {l.linientyp for l in _h.aufgeloest()}
check("Strichlinie (verdeckt)" in _typen, "Durchbruch an Seitenfläche in 2D gestrichelt")
_h2 = core.quader(0, 0, 40, 30, 0, 20)
_h2.ausschnitt_hinzufuegen((10, 10, 20, 1, 0, 0, 0, 1, 0), [(0, 0), (5, 0), (5, 5)], None, False)
check("Strichlinie (verdeckt)" not in {l.linientyp for l in _h2.aufgeloest()}, "Durchbruch von oben bleibt voll")
_ka = G.Kamera(yaw=-45.0, pitch=35.264)
_els = [core.quader(0, 0, 10, 10, 0, 10), core.quader(100, 0, 110, 10, 0, 10)]
_pp = [_ka.proj(p, 0, 0) for p in ((0, 0, 0), (10, 10, 10), (10, 0, 0), (0, 10, 10))]
_rect = (min(q[0] for q in _pp) - 2, min(q[1] for q in _pp) - 2, max(q[0] for q in _pp) + 2, max(q[1] for q in _pp) + 2)
check(S.auswahl_im_rahmen(_els, _ka, 0, 0, _rect, False) == [_els[0]], "Rahmen komplett")
check(S.auswahl_im_rahmen(_els, _ka, 0, 0, _rect, True) == [_els[0]], "Rahmen berührt")
_a = core.quader(0, 0, 40, 30, 0, 10); _b2 = core.quader(60, 0, 100, 30, 0, 10)
_sk = core.Skizze3D("kreis", (0, 0, 10, 1, 0, 0, 0, 1, 0), [80, 15, 5])
S.skizze_in_ausschnitt([_a, _b2, _sk], _sk, None)
check(len(_a.ausschnitte) == 0 and len(_b2.ausschnitte) == 1, "Loch im richtigen Körper bei gleicher Ebene")
for k in ("tb.wz.drehen3d", "tb.wz.abrunden3d", "tb.wz.manip_pivot", "menu.3d.drehen", "menu.3d.abrunden",
          "menu.3d.pivot", "menu.3d.pivot_zentrum", "menu.bearbeiten.manip_pivot", "menu.bearbeiten.manip_zentrum",
          "msg.manip.pivot", "msg.manip.pivot_ok", "msg.manip.pivot_zentriert", "d3.modus.pivot", "d3.msg.pivot_ok",
          "d3.drehen.titel", "d3.drehen.achse", "d3.drehen.winkel", "d3.msg.gedreht", "d3.msg.nichts_drehbar",
          "d3.abrunden.titel", "d3.abrunden.radius", "d3.msg.abgerundet", "d3.msg.nichts_abrundbar",
          "d3.msg.markiert"):
    check(k in I.TEXTE["de"] and k in I.TEXTE["en"], k)
check(core.BEFEHLE.get("3DDREHEN") == "3d:drehen" and core.BEFEHLE.get("3DABRUNDEN") == "3d:abrunden"
      and core.BEFEHLE.get("3DPIVOT") == "3d:pivot", "Befehle drehen/abrunden/pivot")
_o = core.quader(0, 0, 40, 30, 0, 20)
check(_o.kanten_oben_unten(5, True, False) and _o.r_oben == 5 and abs(_o.bbox3()[5] - 20) < 1e-9, "obere Kanten abrunden")
check(len(_o.netz().kanten) > len(core.quader(0, 0, 40, 30, 0, 20).netz().kanten), "Schichtlinien")
_o2 = core.quader(0, 0, 40, 30, 0, 20); _o2.kanten_oben_unten(100, True, True)
check(0 < _o2.r_oben <= 10.0 and _o2.r_unten == _o2.r_oben, "Radius oben+unten begrenzt")
_d2 = _o.to_dict(); _d2.pop("typ", None)
check(core.Koerper3D(**_d2).r_oben == 5, "r_oben Round-Trip")
check(W.WERKZEUG_3D == {"linie": "linie", "polylinie": "poly", "kreis": "kreis", "rechteck": "rechteck", "bemassung": "bem", "text": "text"},
      "Werkzeug-Zuordnung 3D")
check(len(G.profil_einruecken([(0, 0), (10, 0), (10, 10), (0, 10)], 2)) == 4, "Profil einrücken")
_t = core.Text3D((1, 2, 3), "Hallo", 4)
_td = _t.to_dict(); _td.pop("typ", None)
check(core.Text3D(**_td).p == (1.0, 2.0, 3.0) and _t.aufgeloest()[0].inhalt == "Hallo", "Text3D Round-Trip/2D-Text")
_t.verschieben(1, 1, 1); check(_t.p == (2.0, 3.0, 4.0), "Text3D verschieben")
check(isinstance(_t, S.RAUM_TYPEN) and S.ist_3d(_t) is False, "Text3D ist Raumelement")
for k in ("d3.modus.text", "d3.modus.messen", "d3.msg.mess_ok", "d3.msg.nur_2d"):
    check(k in I.TEXTE["de"] and k in I.TEXTE["en"], k)
for k in ("dlg.prop.breite", "dlg.prop.hoehe", "dlg.prop.anker", "dlg.prop.anker_ecke", "dlg.prop.anker_mitte"):
    check(k in I.TEXTE["de"] and k in I.TEXTE["en"], k)
print(f"test_3d - {ok} Checks bestanden")
