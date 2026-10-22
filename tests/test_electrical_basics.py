import sys, os, json, tempfile, shutil, types, zlib, math, re
from unittest.mock import MagicMock
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401  (installiert die tkinter-Attrappe)
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.ui.app as A
import katiecad.fileio.pdf as P
from katiecad.electrical.logic import *
from katiecad.model.project import Projekt

holder = types.SimpleNamespace(); holder._dict_zu_element = lambda d: A.CadApp._dict_zu_element(holder, d)
fac = holder._dict_zu_element
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1
def near(a, b, t=1e-9): return abs(a - b) < t

# ---------- Schraffur-Winkel ----------
for w, soll in ((45, +1), (-45, -1)):
    sh = core.Schraffur([(0, 0), (20, 0), (20, 20), (0, 20)], "linien", winkel=w, abstand=3)
    L = sh.geometrie_linien()
    check(len(L) > 3, "Schraffurlinien vorhanden")
    for (p1, p2) in L:
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        check(abs(abs(dx) - abs(dy)) < 1e-6 and dx * dy * soll > 0, f"Winkel {w}: Richtung ({dx:.2f},{dy:.2f})")
sh = core.Schraffur([(0, 0), (20, 0), (20, 20), (0, 20)], "linien", winkel=0, abstand=4)
check(all(near(p1[1], p2[1], 1e-6) for p1, p2 in sh.geometrie_linien()), "0 Grad waagerecht")
sh = core.Schraffur([(0, 0), (20, 0), (20, 20), (0, 20)], "linien", winkel=90, abstand=4)
check(all(near(p1[0], p2[0], 1e-6) for p1, p2 in sh.geometrie_linien()), "90 Grad senkrecht")
sh = core.Schraffur([(0, 0), (20, 0), (20, 20), (0, 20)], "linien", winkel=30, abstand=4)
p1, p2 = sh.geometrie_linien()[3]
check(near(math.degrees(math.atan2(p2[1]-p1[1], p2[0]-p1[0])) % 180, 30, 1e-6), "30 Grad exakt")
# drehen konsistent: Schraffur um 90 gedreht -> Linien drehen mit
sh = core.Schraffur([(0, 0), (20, 0), (20, 20), (0, 20)], "linien", winkel=0, abstand=4)
sh.drehen(10, 10, 90)
check(all(near(p1[0], p2[0], 1e-6) for p1, p2 in sh.geometrie_linien()), "drehen konsistent")

# ---------- Drehkonvention: Winkelfelder drehen mit der Geometrie ----------
CCW90 = -90          # so ruft das Dreh-Werkzeug auf (-Winkel)
t = core.Text(10, 0, "x", 3.5, 0.0); t.drehen(0, 0, CCW90)
check(near(t.x, 0, 1e-9) and near(t.y, 10, 1e-9) and near(t.winkel, 90), "Text: Position (0,10) und Winkel 90 (CCW)")
bg = core.Bogen(10, 0, 5, 0, 90); bg.drehen(0, 0, CCW90)
check(near(bg.cy, 10) and near(bg.start, 90) and near(bg.ende, 180), "Bogen dreht mit")
sh = core.Schraffur([(0, 0), (20, 0), (20, 20), (0, 20)], "linien", winkel=0, abstand=4)
sh.drehen(0, 0, -30)
p1, p2 = sh.geometrie_linien()[2]
check(near(math.degrees(math.atan2(p2[1]-p1[1], p2[0]-p1[0])) % 180, 30, 1e-6) and near(sh.winkel, 30), "Schraffur dreht mit (30 Grad CCW)")
blk = core.BlockReferenz(0, 0, "B", [core.Linie(10, 0, 20, 0)], winkel=90.0)
l = blk.aufgeloest()[0]
check(near(l.x1, 0) and near(l.y1, 10) and near(l.x2, 0) and near(l.y2, 20), "Block winkel +90 = CCW")
blk = core.BlockReferenz(0, 0, "B", [core.Text(10, 0, "x", 3.5, 0.0)], winkel=90.0)
t = blk.aufgeloest()[0]
check(near(t.x, 0) and near(t.y, 10) and near(t.winkel, 90), "Text im gedrehten Block dreht mit")
blk = core.BlockReferenz(0, 0, "B", [core.Querverweis(10, 0, "L", "abgehend", 0)], winkel=90.0)
q = blk.aufgeloest()[0]
check(near(q.x, 0) and near(q.y, 10) and q.richtung == 90, "Querverweis im gedrehten Block")
blk.drehen(0, 0, CCW90)
check(near(blk.x, 0) and near(blk.winkel, 180), "Block drehen: Winkel 90+90")

# ---------- Querverweis-Geometrie ----------
def kinder(qv):
    k = qv.aufgeloest()
    return k[0], [t for t in k[1:]]
qv = core.Querverweis(0, 0, "L1", "abgehend", 0)
pf, tx = kinder(qv)
pts = pf.punkte
check(near(pts[2][0], 5) and near(pts[2][1], 0), "Ost: Spitze bei 5 mm")
check(near(abs(pts[0][1] - pts[1][1]), 2) and near(pts[0][0], 0), "Basis 2 mm breit, Mitte im Einfuegepunkt")
check(len(tx) == 1 and tx[0].einfuegepunkt == "mitte_links" and near(tx[0].x, 6) and near(tx[0].y, 0), "abgehend Ost, ohne Ziel: Text hinter Spitze")
qv.ziel = [2]
_, tx = kinder(qv)
check(len(tx) == 2 and tx[0].inhalt == "L1" and tx[1].inhalt == "(Blatt 2)" and tx[0].y > 0 > tx[1].y and tx[1].hoehe < tx[0].hoehe, "L1 oben, Ziel kleiner darunter")
qv = core.Querverweis(10, 20, "L1", "abgehend", 180); qv.ziel = [1]
pf, tx = kinder(qv)
check(near(pf.punkte[2][0], 5) and tx[0].einfuegepunkt == "mitte_rechts" and near(tx[0].x, 4), "abgehend West: rechtsbuendig an der Spitze")
qv = core.Querverweis(0, 0, "L1", "abgehend", 90); qv.ziel = [3]
pf, tx = kinder(qv)
check(near(pf.punkte[2][1], 5) and tx[0].winkel == 90 and tx[0].einfuegepunkt == "mitte_links" and near(tx[0].y, 6) and tx[0].x < 0 < tx[1].x, "abgehend Nord: Text hochkant, L1 links, Ziel rechts")
qv = core.Querverweis(0, 0, "L1", "abgehend", 270); qv.ziel = [3]
pf, tx = kinder(qv)
check(near(pf.punkte[2][1], -5) and tx[0].einfuegepunkt == "mitte_rechts" and near(tx[0].y, -6), "abgehend Sued: Text endet an der Spitze")
# ankommend: Text an der Basis
qv = core.Querverweis(0, 0, "L1", "ankommend", 180); qv.ziel = [2]
pf, tx = kinder(qv)
check(near(pf.punkte[2][0], -5) and tx[0].einfuegepunkt == "mitte_links" and near(tx[0].x, 1), "ankommend (Spitze links): Text rechts der Basis")
qv = core.Querverweis(0, 0, "L1", "ankommend", 0); qv.ziel = [2]
pf, tx = kinder(qv)
check(tx[0].einfuegepunkt == "mitte_rechts" and near(tx[0].x, -1), "ankommend (Spitze rechts): Text links der Basis")
qv = core.Querverweis(0, 0, "L1", "ankommend", 90); qv.ziel = [2]
pf, tx = kinder(qv)
check(tx[0].einfuegepunkt == "mitte_rechts" and near(tx[0].y, -1) and tx[0].winkel == 90, "ankommend Nord: Text unter der Basis")
check(pf.farbe == core.LEITUNG_FARBE and pf.muster == "solid", "Pfeil rot, gefuellt")
# Rundlauf & Transformationen
qv = core.Querverweis(3, 4, "A1", "ankommend", 90)
q2 = fac(json.loads(json.dumps(qv.to_dict())))
check(isinstance(q2, core.Querverweis) and (q2.text, q2.art, q2.richtung, q2.x) == ("A1", "ankommend", 90, 3) and q2.ziel == [], "Roundtrip")
check("ziel" not in qv.to_dict(), "Ziel wird nicht gespeichert")
qv.drehen(0, 0, -90); check(qv.richtung == 180, "drehen (Werkzeug-Konvention -a = CCW) aendert Richtung")
qv.verschieben(1, 1); b = qv.bbox(); check(b[2] > b[0] and b[3] > b[1], "bbox")
check(core.Querverweis(0, 0, "x", "foo", 40).richtung == 0 and core.Querverweis(0, 0, "x", "foo", 40).art == "abgehend", "Eingaben normalisiert")

# ---------- Ziele ----------
a = core.Querverweis(0, 0, "L1"); b = core.Querverweis(0, 0, "L2"); c = core.Querverweis(0, 0, "")
querverweis_ziele([a, b, c], 1, {2: ["L1", "L3"], 3: ["L1"]})
check(a.ziel == [2, 3] and b.ziel == [] and c.ziel == [], "Ziele ueber mehrere Blaetter")
check(a.ziel_text() == "(Blatt 2, 3)" and b.ziel_text() == "", "Zieltext")
d = core.Querverweis(5, 5, "L1")
querverweis_ziele([a, d], 1, {})
check(a.ziel == [1] and d.ziel == [1], "gleiches Blatt: eigenes Blatt als Ziel")
querverweis_ziele([a], 1, {})
check(a.ziel == [], "einzeln: kein Ziel")
x1, x2 = [core.Querverweis(0, 0, "L1")], [core.Querverweis(0, 0, " L1 ")]
ziele_fuer_alle_blaetter({1: x1, 2: x2})
check(x1[0].ziel == [2] and x2[0].ziel == [1], "ziele_fuer_alle_blaetter (Leerzeichen egal)")
check(qv_texte_aus_blattdaten({"elemente": [{"typ": "querverweis", "text": "L1"}, {"typ": "linie"}]}) == ["L1"], "Texte aus JSON")
check([naechste_bezeichnung(z) for z in ("13", "A1", "PE", "", "X09")] == ["14", "A2", "PE", "", "X10"], "naechste_bezeichnung")

# ---------- Verbindungspunkt / Leitung ----------
vp = core.Verbindungspunkt(10, 10, wert="13")
check(vp.typ == "vpunkt" and vp.hoehe == 2.0 and vp.radius == 0.5 and near(vp.radius * 2, 1.0), "VP Standardwerte: d=1 mm, Text 2.0")
t = vp.text_element()
check(t.inhalt == "13" and t.hoehe == 2.0 and t.x > 10 and near(t.y, 10) and t.einfuegepunkt == "mitte_links", "Beschriftung rechts vom Punkt")
check(core.Verbindungspunkt(0, 0, wert="").text_element() is None, "ohne Text keine Beschriftung")
v2 = fac(json.loads(json.dumps(vp.to_dict())))
check(isinstance(v2, core.Verbindungspunkt) and v2.wert == "13", "VP Roundtrip")
check(vp.trifft(10.2, 10, 0.1) and vp.trifft(t.x + 0.5, 10, 0.1) and not vp.trifft(50, 50, 1), "VP Treffer")
l = core.Leitung(0, 0, 10, 0)
check(l.farbe == "#ff0000" and l.staerke == core.LEITUNG_STAERKE and l.eig_farbe and isinstance(l, core.Linie), "Leitung rot")
l2 = fac(json.loads(json.dumps(l.to_dict())))
check(isinstance(l2, core.Leitung) and l2.x2 == 10 and l2.typ == "leitung", "Leitung Roundtrip")

# VP im Block
sym = core.Rechteck(-5, -5, 5, 5)
p1 = core.Verbindungspunkt(-5, 0, wert="A1"); p2 = core.Verbindungspunkt(5, 0, wert="A2")
nm = core.AttributDefinition(0, 8, None, 3.5, tag="VP1", wert="-Q1")       # Kollision mit VP1 absichtlich
els = [sym, p1, p2, nm]
core.vp_tags_eindeutig(els)
check([e.tag for e in els[1:3]] == ["VP2", "VP3"] and els[3].tag == "VP1", "Tags eindeutig")
d = core.BlockDefinition("K", (0, 0), els)
ref = core.BlockReferenz(100, 50, "K", d.elemente, skalierung=2.0, winkel=90.0)
check(ref.attribute == {"VP2": "A1", "VP3": "A2", "VP1": "-Q1"}, "VP-Werte als Attribute")
ref.setze_attribute({"VP2": "13"})
vps = [k for k in ref.aufgeloest() if isinstance(k, core.Verbindungspunkt)]
check(len(vps) == 2 and vps[0].wert == "13" and vps[1].wert == "A2", "Instanzwert in aufgeloest")
check(near(vps[0].x, 100) and near(vps[0].y, 40) and near(vps[0].radius, 1.0) and near(vps[0].hoehe, 4.0) and near(vps[0].winkel, 90), "VP transformiert (Drehung 90, Skal. 2)")
check(len(verbindungspunkte([ref])) == 2 and naechster_vp([ref], 100.3, 40.2, 1.0).wert == "13" and naechster_vp([ref], 0, 0, 1) is None, "VP-Suche im Block")
r2 = fac(json.loads(json.dumps(ref.to_dict())))
check(r2.attribute["VP2"] == "13" and len(r2.attribut_definitionen()) == 3, "Block mit VP Roundtrip")
check(ref.bbox()[2] >= ref.bbox()[0], "bbox Block mit VP")

# ---------- PDF ----------
def seite_text(pdf_bytes):
    out = []
    for m in re.finditer(rb"stream\n(.*?)\nendstream", pdf_bytes, re.S):
        out.append(zlib.decompress(m.group(1)).decode("latin-1"))
    return out
def ctx(elemente, layouts=None):
    layers = {"0": core.Layer("0", "#000000", 0.35), "Schrift": core.Layer("Schrift", "#000000", 0.35)}
    lay = layouts or [core.Layout("Layout1", core.Layout.STANDARD_FORMAT, "#1c132d")]
    return types.SimpleNamespace(elemente=elemente, layers=layers, layouts=lay, aktives_layout=0,
                                 _einh_faktor=lambda: 1.0, dezimalkomma=types.SimpleNamespace(get=lambda: False))
q = core.Querverweis(50, 50, "L1", "abgehend", 0, layer="Schrift", farbe="#000000", eig_farbe=True); q.ziel = [2]
vpe = core.Verbindungspunkt(80, 50, wert="PE", layer="0", farbe="#000000", eig_farbe=True)
le = core.Leitung(20, 20, 60, 20, layer="0")
c1 = ctx([q, vpe, le, core.Linie(0, 0, 10, 10, layer="0")])
pdf, uebersp = P.pdf_mehrseitig_erzeugen([("001 A", c1), ("002 B", ctx([core.Linie(0, 0, 5, 5, layer="0")])), ("003 leer", ctx([]))], "modell", True, False)
check(b"/Count 2" in pdf and uebersp == ["003 leer"], f"2 Seiten, leeres Modell uebersprungen {uebersp}")
st = seite_text(pdf)
check(len(st) == 2 and "(L1) Tj" in st[0] and "\\(Blatt 2\\)" in st[0] and "(PE) Tj" in st[0], "Querverweis-Text + VP-Beschriftung im PDF")
check("1.0000 0.0000 0.0000 rg" in st[0] and " f" in st[0], "roter Pfeil gefuellt")
check("1.0000 0.0000 0.0000 RG" in st[0], "rote Leitung (farbig)")
check(st[0].count(" re W n") == 0, "Modell: keine Clip-Region")
# Layout mit Viewport -> Verbindungspunkt: nur Text, kein Kreis
lay = core.Layout("Layout1", core.Layout.STANDARD_FORMAT, "#1c132d")
lay.elemente.append(core.Viewport(10, 10, 200, 100, 80, 50, 1.0, layer="0"))
pdf2, _ = P.pdf_mehrseitig_erzeugen([("x", ctx([vpe], [lay]))], "layout", False, False)
s2 = seite_text(pdf2)[0]
check("(PE) Tj" in s2, "Layout/Viewport: VP-Beschriftung sichtbar")
n_kreis_linien = len(re.findall(r"\bs\b", s2))   # geschlossene Pfade (Kreis waere 's')
check(n_kreis_linien == 0, "Layout/Viewport: kein VP-Kreis")
# Einzelseite unveraendert funktionsfaehig
b1 = P.pdf_erzeugen(c1, "modell", False, False)
check(b1.startswith(b"%PDF-1.4") and b"/Count 1" in b1 and b1.rstrip().endswith(b"%%EOF"), "Einzel-PDF")
# xref-Offsets stimmig
m = re.search(rb"startxref\n(\d+)", pdf)
check(pdf[int(m.group(1)):].startswith(b"xref"), "xref-Offset korrekt")
offs = re.findall(rb"(\d{10}) 00000 n", pdf)
check(all(pdf[int(o):].split(b" ")[1] == b"0" and b"obj" in pdf[int(o):int(o) + 12] for o in offs), "Objekt-Offsets korrekt")
print(f"{ok} Checks bestanden")
