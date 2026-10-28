# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import stub  # noqa
from katiecad.model.core import Querverweis, ElektroMaske, Klemme, Kabel
from katiecad.electrical.pruefung import pruefe


def M(per, rolle="haupt", x=0):
    m = ElektroMaske(x, 0, {"IND": per}, rolle=rolle)
    return m


def texte(b):
    return [(f.stufe, f.text) for f in b]


def test_haupt_doppelt():
    b = pruefe([(0, "A", [M("K1")]), (1, "B", [M("K1"), M("K2")])])
    assert sum(1 for f in b if f.stufe == "fehler") == 2


def test_klemmen_leiste_geerbt():
    from katiecad.model.core import Klemme
    ks = [Klemme(20, 100, {"IND": "-X10", "NUM": "1"}), Klemme(30, 100, {"NUM": "2"}),
          Klemme(60, 100, {"IND": "-X11", "NUM": "1"}), Klemme(70, 100, {"NUM": "2"})]
    b = pruefe([(0, "A", ks)])
    assert not [f for f in b if f.stufe == "fehler"], b
    ks2 = [Klemme(20, 100, {"IND": "-X10", "NUM": "1"}), Klemme(30, 100, {"NUM": "1"})]
    assert sum(1 for f in pruefe([(0, "A", ks2)]) if f.stufe == "fehler") == 2


def test_einbauort_trennt():
    b = pruefe([(0, "A", [M("K1")]), (1, "B", [M("K1")])], {0: "UV1", 1: "UV2"})
    assert not [f for f in b if f.stufe == "fehler"]
    b = pruefe([(0, "A", [M("K1")]), (1, "B", [M("K1")])], {0: "UV1", 1: "UV1"})
    assert sum(1 for f in b if f.stufe == "fehler") == 2


def test_hilfs():
    b = pruefe([(0, "A", [M("K9", "hilfs"), M("K1"), M("K1", "hilfs")])])
    assert len([f for f in b if f.stufe == "fehler"]) == 1


def test_qv():
    q = lambda t, a="abgehend", e=False: Querverweis(0, 0, t, a, 0, extern=e)
    b = pruefe([(0, "A", [q("L1"), q("N", e=True), q("X"), q("Y"), q("Y")]),
                (1, "B", [q("L1", "ankommend"), q("X", "ankommend"), q("X", "ankommend")])])
    fehler = [f.text for f in b if f.stufe == "fehler"]
    warn = [f.text for f in b if f.stufe == "warnung"]
    assert any("X" in t for t in fehler)          # 3x
    assert not any("L1" in t for t in fehler)
    assert not any("„N“" in t or '"N"' in t for t in fehler)
    assert len(warn) == 2                          # Y twice abgehend


def test_klemme():
    k = lambda: Klemme(0, 0, {"IND": "X1", "NUM": "1"})
    b = pruefe([(0, "A", [k(), k()])])
    assert len([f for f in b if f.stufe == "fehler"]) == 2
    assert any(f.stufe == "hinweis" for f in b)


def test_kontaktspiegel():
    from katiecad.electrical.logic import (kontakt_art, geraete, geraete_referenzen)
    from katiecad.model.core import Text
    assert kontakt_art(["13", "14"]) == "schliesser"
    assert kontakt_art(["21", "22"]) == "oeffner"
    assert kontakt_art(["11", "12", "14"]) == "wechsler"
    assert kontakt_art(["A1", "A2"]) == "spule"
    m = M("K1")
    eig = geraete([m], 1)
    andere = {2: [("K1", "hilfs", "K1", "3/B", ["13", "14"]),
                  ("K1", "hilfs", "K1", "", ["A1", "A2"]),
                  ("K1", "hilfs", "K1", "4", ["21", "22"])]}
    geraete_referenzen(eig, 1, andere)
    assert len(m.kontakte) == 2 and m.kontakte[0][1] == ("13", "14")
    texte_liste = [e.inhalt for e in m.aufgeloest(False) if isinstance(e, Text)]
    assert any("Blatt" in t or "Sheet" in t for t in texte_liste)
    for mode in ("rechts", "unten"):
        m.spiegel = mode
        el = m.aufgeloest(False)
        t = [e.inhalt for e in el if isinstance(e, Text)]
        assert "13" in t and "14" in t and not any("Blatt" in x or "Sheet" in x for x in t)
    d = m.to_dict()
    assert "kontakte" not in d and d["spiegel"] == "unten"
    m2 = ElektroMaske(0, 0, {"IND": "K1"}, rolle="hilfs", spiegel="rechts")
    m2.kontakte = [("schliesser", ("13", "14"), 2)]
    assert not m2._spiegel_aktiv()


def test_eigenschaften():
    from katiecad.model.core import Linie, Text
    from katiecad.model.eigenschaften import gemeinsame, anwenden, VERSCHIEDEN
    l = Linie(0, 0, 1, 1, staerke=0.35)
    t = Text(0, 0, "x", 2.0)
    g = gemeinsame([l, t])
    assert g["layer"] == "0" and "hoehe" in g and g["hoehe"] == 2.0
    anwenden([l, t], "layer", "Schrift")
    anwenden([l, t], "farbe", "#ff0000")
    anwenden([l, t], "hoehe", 3.5)
    anwenden([l, t], "staerke", 0.7)
    assert l.layer == t.layer == "Schrift" and l.farbe == "#ff0000" and l.eig_farbe
    assert t.hoehe == 3.5 and not hasattr(l, "hoehe") and l.staerke == t.staerke == 0.7
    anwenden([l, t], "farbe", None)
    assert not l.eig_farbe and not t.eig_farbe
    assert gemeinsame([l, Linie(0, 0, 1, 1, staerke=0.35)])["staerke"] == VERSCHIEDEN
    assert "hoehe" not in gemeinsame([l])


def test_spiegel_griff():
    from katiecad.model.core import BlockReferenz, Linie, Rechteck
    m = ElektroMaske(-4, -5, {"IND": "K1"}, rolle="haupt", spiegel="unten")
    b = BlockReferenz(10, 20, "B", [Rechteck(-5, -7.5, 5, 7.5), m])
    b.kontakte = [("schliesser", ("13", "14"), 2)]
    g = dict((i, (x, y)) for i, x, y in b.griffe())
    assert "sp" in g
    x0, y0 = g["sp"]
    assert abs(x0 - (10 - 7.5)) < 1e-6 and abs(y0 - (20 - 7.5 - 6)) < 1e-6
    b.griff_bewegen("sp", x0 + 3, y0 - 4)
    assert (b.sp_dx, b.sp_dy) == (3, -4)
    g2 = dict((i, (x, y)) for i, x, y in b.griffe())
    assert abs(g2["sp"][0] - (x0 + 3)) < 1e-6
    d = b.to_dict()
    assert d["sp_dx"] == 3 and "kontakte" not in d
    b2 = BlockReferenz(**{k: v for k, v in d.items() if k not in ("typ",)} | {"elemente": [Rechteck(-5,-7.5,5,7.5), m]}) if False else None


def test_kabel_rundreise():
    import json
    import katiecad.ui.app as A
    from katiecad.electrical.logic import geraete, geraete_referenzen
    from katiecad.model.core import Kabel, Klemme
    k = Kabel(0, 0, {"CAB": "W1"}, laenge=20)
    kl = Klemme(5, 5, {"IND": "X1", "NUM": "1"})
    geraete_referenzen(geraete([k, kl], 1), 1, {})
    d = json.loads(json.dumps(k.to_dict()))
    assert "kontakte" not in d
    d["kontakte"] = []                       # file written by 1.0.1
    class T: pass
    r = A.CadApp._dict_zu_element(T(), d)
    assert isinstance(r, Kabel) and r.laenge == 20


def test_skalieren_spiegeln():
    import math, json
    from katiecad.model.core import (Linie, Kreis, Bogen, Rechteck, Polylinie, Text,
                                     BlockReferenz, Querverweis, Verbindung, Kabel,
                                     Verbindungspunkt, punkt_spiegeln)
    l = Linie(1, 1, 3, 1); l.skalieren(0, 0, 2); assert (l.x1, l.x2, l.y1) == (2, 6, 2)
    k = Kreis(1, 1, 2); k.skalieren(1, 1, 3); assert k.r == 6 and (k.cx, k.cy) == (1, 1)
    t = Text(2, 2, "a", 2.0); t.skalieren(0, 0, 0.5); assert t.hoehe == 1.0 and t.x == 1
    assert punkt_spiegeln(1, 2, 0, 0, 1, 0) == (1, -2)
    q = Querverweis(0, 0, "L1", "abgehend", 0); q.spiegeln(0, 0, 0, 1); assert q.richtung == 180
    v = Verbindung(0, 0, arme=[0, 90], punkt=True); v.spiegeln(0, 0, 0, 1)
    assert v.arme == [90, 180]
    kb = Kabel(0, 0, {"CAB": "W"}, laenge=10); kb.spiegeln(0, 0, 0, 1); assert kb.x == -10
    r = Rechteck(0, 0, 2, 1); r.spiegeln(0, 0, 0, 1); assert isinstance(r, Rechteck)
    r2 = Rechteck(0, 0, 2, 1); r2.spiegeln(0, 0, 1, 1); assert isinstance(r2, Polylinie)
    b = BlockReferenz(0, 0, "B", [Linie(1, 0, 3, 0), Verbindungspunkt(3, 0, "1", 2.0, 0.0, "Arial", "mitte_links", tag="VP1", wert="1")])
    b.spiegeln(5, 0, 5, 10)
    g = [e for e in b.aufgeloest() if isinstance(e, Linie)][0]
    assert abs(g.x1 - 9) < 1e-9 and abs(g.x2 - 7) < 1e-9 and b.gespiegelt
    vp = [e for e in b.aufgeloest() if isinstance(e, Verbindungspunkt)][0]
    assert abs(vp.x - 7) < 1e-9 and vp.einfuegepunkt == "mitte_rechts"
    d = json.loads(json.dumps(b.to_dict()))
    assert d["gespiegelt"] is True
    b.skalieren(0, 0, 2)
    assert b.skalierung == 2 and abs(b.x - 20) < 1e-9
    bb = b.bbox()
    assert bb[0] < bb[2]
    b.spiegeln(0, 0, 1, 0)       # back about another axis: stays consistent
    assert b.gespiegelt is False


def test_dxf_projekt_und_log():
    import sys
    from katiecad.fileio.dxf_projekt import (DxfSeite, dxf_projekt_schreiben,
                                             gitter_positionen)
    from katiecad.common import logbuch

    class Ent:
        def __init__(self, k, a): self.k, self.a = k, a
        def set_placement(self, *a, **kw): self.p = a
        class paths:
            @staticmethod
            def add_polyline_path(*a, **kw): pass
    class Msp:
        def __init__(self): self.e = []
        def add_lwpolyline(self, pts, close=False, dxfattribs=None):
            self.e.append(("poly", pts, close, dxfattribs))
        def add_text(self, t, dxfattribs=None):
            e = Ent("text", dxfattribs); self.e.append(("text", t, dxfattribs)); return e
        def add_hatch(self, dxfattribs=None):
            self.e.append(("hatch",)); return Ent("hatch", dxfattribs)
    class Doc:
        def __init__(self): self.layers = Layers(); self.m = Msp()
        def modelspace(self): return self.m
    class Layers(dict):
        def add(self, n, color=7): self[n] = color
    seiten = []
    for i in range(6):
        s = DxfSeite(297, 210)
        s.linie([(0, 0), (10, 10)], 0.35, "#ff0000")
        s.flaeche([(0, 0), (5, 0), (5, 5)], "#000000")
        s.text(1, 1, "a\nb", 2.0)
        seiten.append(("S%d" % i, s))
    d = Doc()
    dxf_projekt_schreiben(d, seiten, spalten=4, abstand=50)
    polys = [e for e in d.m.e if e[0] == "poly" and e[3]["layer"] == "Blattgrenze"]
    assert len(polys) == 6
    assert polys[4][1][0] == (0, -260)          # 5th sheet: new row
    assert polys[3][1][0] == (3 * 347, 0)       # 4th sheet: 4th column
    assert sum(1 for e in d.m.e if e[0] == "text" and e[2]["layer"].startswith("Blatt_")) == 12

    logbuch.leeren()
    alt = sys.stdout
    logbuch.installieren()
    print("[KatieCAD] Testeintrag")
    sys.stderr.write("Boese\n")
    t = logbuch.text()
    assert "Testeintrag" in t and "Boese" in t and logbuch.anzahl_fehler() >= 1
    sys.stdout, sys.stderr = alt, sys.__stderr__
    import tempfile, os
    td = tempfile.mkdtemp()
    logbuch._datei_oeffnen(td, "Kopf")
    logbuch.eintragen("Dateieintrag")
    assert logbuch.pfad() and "Dateieintrag" in open(logbuch.pfad(), encoding="utf-8").read()
    logbuch._datei_oeffnen(td, "Kopf2")
    assert os.path.exists(logbuch.pfad() + ".old")
    logbuch._datei.close(); logbuch._datei = None


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("OK")
