import sys, os, json, types, zlib, re, math
from unittest.mock import MagicMock
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401  (installs the tkinter stand-in)
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.ui.app as A
from katiecad.electrical.logic import *
NS = types.SimpleNamespace
holder = NS(); holder._dict_zu_element = lambda d: A.CadApp._dict_zu_element(holder, d)
fac = holder._dict_zu_element
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1
near = lambda a, b, t=1e-6: abs(a - b) < t

# ---------- Text width: real character widths ----------
h = 3.5
w16a = core.Text(0, 0, "16A", h).masse()[0]; w111 = core.Text(0, 0, "111", h).masse()[0]; wxxx = core.Text(0, 0, "XXX", h).masse()[0]
check(w16a > w111 and wxxx > w16a, f"A breiter als 1: {w111:.2f} < {w16a:.2f} < {wxxx:.2f}")
fs = h / core.CAD_VERSALHOEHE
check(near(w16a, core.pdf_textbreite("16A", fs)), "masse() == PDF-Breite")
for anker, soll_x in (("unten_rechts", 0.0), ("mitte_rechts", 0.0), ("oben_rechts", 0.0)):
    t = core.Text(0, 0, "16A", h, einfuegepunkt=anker)
    check(near(t.bbox()[2], soll_x), f"{anker}: Text endet exakt am Einfuegepunkt")
t = core.Text(0, 0, "16A", h, einfuegepunkt="unten_zentriert")
b = t.bbox(); check(near((b[0] + b[2]) / 2, 0), "zentriert: Mitte im Einfuegepunkt")
t = core.Text(0, 0, "16A", h, einfuegepunkt="unten_links"); check(near(t.bbox()[0], 0), "links beginnt am Einfuegepunkt")
t = core.Text(0, 0, "", h); check(t.masse()[0] > 0, "leerer Text hat Mindestbreite")
t = core.Text(0, 0, "ab\nlanger Text", 2.0); check(near(t.masse()[0], core.pdf_textbreite("langer Text", 2.0 / core.CAD_VERSALHOEHE)), "mehrzeilig: breiteste Zeile")
# rotated right-aligned text
t = core.Text(5, 5, "16A", h, winkel=90, einfuegepunkt="unten_rechts"); b = t.bbox()
check(near(b[3], 5), "rotierter Text endet am Einfuegepunkt")
# Dimensioning uses the same metrics (no crash, plausible text)
bm = core.Bemassung("linear", 0, 0, 100, 0, 0, 10) if hasattr(core.Bemassung, "__init__") else None

# ---------- Cross reference: fonts 1 mm smaller ----------
q = core.Querverweis(0, 0, "L1", "abgehend", 0); q.ziel = [2]
k = q.aufgeloest()
check(near(k[1].hoehe, 2.5) and near(k[2].hoehe, 1.5), "Kennung 2.5 mm, Ziel 1.5 mm")
# own heights and moved texts
_q = Querverweis(0, 0, "L1", "abgehend", 0); _q.ziel = [(2, "A", "")] if False else []
_q.text_hoehe = 4.0
check(near(_q.aufgeloest()[1].hoehe, 4.0), "Querverweis eigene Texthoehe")
_t0 = _q.aufgeloest()[1]; _x0, _y0 = _t0.x, _t0.y
check(any(g[0] == "t" for g in _q.griffe()), "Querverweis Text-Griff")
_q.griff_bewegen("t", _x0 + 3, _y0 + 2)
_t1 = _q.aufgeloest()[1]
check(near(_t1.x, _x0 + 3) and near(_t1.y, _y0 + 2), "Querverweis Text verschiebbar")
_q.texte_zuruecksetzen()
check(near(_q.aufgeloest()[1].x, _x0), "Querverweis Textposition zuruecksetzen")
_d = _q.to_dict(); _d.pop("typ"); check(Querverweis(**_d).text_hoehe == 4.0, "Querverweis Texthoehe gespeichert")
check(near(k[1].y, k[2].y) and k[2].x > k[1].x, "Kennung und Ziel in einer Zeile")
check(near(q.basis_punkt()[0], 0) and near(q.spitze_punkt()[0], 5), "Basis/Spitze")
q = core.Querverweis(1, 2, "L1", "abgehend", 90); check(near(q.spitze_punkt()[0], 1) and near(q.spitze_punkt()[1], 7), "Spitze bei Nord")

# ---------- Connection points ----------
vp = core.Verbindungspunkt(10, 10, wert="A1")
q = core.Querverweis(50, 10, "L1", "ankommend", 0)
blk = core.BlockReferenz(100, 100, "K", [core.Rechteck(-5, -5, 5, 5), core.Verbindungspunkt(0, 5, wert="X1")])
aps = anschlusspunkte([vp, q, blk, core.Linie(0, 0, 1, 1)])
koord = sorted((a.x, a.y) for a in aps)
check(len(aps) == 4 and koord == [(10, 10), (50, 10), (55, 10), (100, 105)], f"4 Anschluesse: VP, Basis, Spitze, Block-VP {koord}")
check(any("Basis" in a.name for a in aps) and any("Spitze" in a.name for a in aps), "Namen unterscheiden Basis/Spitze")
check(naechster_anschluss([q], 55.2, 10.1, 1.0).name.endswith("(Spitze)") and naechster_anschluss([q], 52.5, 10, 1.0) is None, "nur an Basis und Spitze, nicht in der Mitte")
unsichtbar = anschlusspunkte([vp, q], sichtbar=lambda e: e is not q); check(len(unsichtbar) == 1, "Filter sichtbar")

# ---------- Hide per instance ----------
nm = core.AttributDefinition(0, 8, None, 3.5, tag="NAME", wert="-Q1")
v1 = core.Verbindungspunkt(-5, 0, wert="A1"); v2 = core.Verbindungspunkt(5, 0, wert="A2")
els = [core.Rechteck(-5, -5, 5, 5), v1, v2, nm]; core.vp_tags_eindeutig(els)
ref = core.BlockReferenz(0, 0, "K", els)
texte = lambda r: sorted(k.inhalt for k in r.aufgeloest() if isinstance(k, core.Text) and not isinstance(k, core.Verbindungspunkt))
check(texte(ref) == ["-Q1"] and all(v.text_element() is not None for v in verbindungspunkte([ref])), "Standard: alles sichtbar")
ref.setze_ausgeblendet({"NAME", "VP1", "UNBEKANNT"})
check(ref.ausgeblendet == {"NAME", "VP1"}, "nur bekannte Tags")
check(texte(ref) == [] and sorted((v.wert, v.text_element() is None) for v in verbindungspunkte([ref])) == [("A1", True), ("A2", False)],
      "NAME und Text von VP1 ausgeblendet, Kreis/VP bleiben")
check(len(verbindungspunkte([ref])) == 2, "ausgeblendeter VP bleibt Anschlusspunkt")
r2 = fac(json.loads(json.dumps(ref.to_dict())))
check(r2.ausgeblendet == {"NAME", "VP1"} and "_cache" not in ref.to_dict(), "Roundtrip, Cache wird nicht gespeichert")
ref.setze_ausgeblendet(set()); check(texte(ref) == ["-Q1"], "wieder einblenden")
# Original elements of the instance are not modified
check(all(v.sichtbar for v in ref.attribut_definitionen()), "Definition unveraendert")

# ---------- aufgeloest() cache ----------
r = core.BlockReferenz(0, 0, "K", els)
a1 = r.aufgeloest(); a2 = r.aufgeloest()
check(a1 is a2, "Cache: zweiter Aufruf liefert dieselbe Liste (keine neuen Kopien)")
r.verschieben(5, 0) if hasattr(r, "verschieben") else None
a3 = r.aufgeloest(); check(a3 is not a1, "Verschieben invalidiert")
xs = sorted(round(k.bbox()[0], 3) for k in a3); xs1 = sorted(round(k.bbox()[0], 3) for k in a1); check(xs != xs1, "Positionen aktualisiert")
r.setze_attribute({"NAME": "X"}); check(r.aufgeloest() is not a3 and "X" in texte(r), "Attributaenderung invalidiert")
r.winkel = 90; a4 = r.aufgeloest(); check(a4 is not None and r.aufgeloest() is a4, "Drehen invalidiert, danach wieder gecacht")
# Independent copies (explode path)
import copy
k0 = copy.deepcopy(r.aufgeloest()[0]); k0.verschieben(100, 0); check(near(r.aufgeloest()[0].bbox()[0], r.aufgeloest()[0].bbox()[0]) and r.aufgeloest()[0].bbox()[0] != k0.bbox()[0], "deepcopy entkoppelt")

# ---------- Undo compression / memory budget ----------
class T(A.CadApp): pass
a = T.__new__(T); a._undo_max = 50; a._undo_stack = []; a._redo_stack = []; a._undo_pro_blatt = {}
a._mark_dirty = lambda: None; a._aktualisiere_undo_redo = lambda: None
kl = {"elemente": [{"typ": "linie"}] * 10, "layouts": [], "layers": []}
check(a._snap_pack(kl) is kl and a._snap_unpack(kl) is kl, "kleine Zustaende unkomprimiert")
gross = {"elemente": [core.Linie(i, i, i + 1, i + 2).to_dict() for i in range(20000)], "layouts": [], "layers": []}
p = a._snap_pack(gross)
roh = len(json.dumps(gross))
check(isinstance(p, tuple) and p[0] == "z" and len(p[1]) < roh / 8, f"gross: komprimiert {roh//1024} KB -> {len(p[1])//1024} KB")
check(a._snap_unpack(p) == gross, "verlustfreier Roundtrip")
for _ in range(60): a._push_undo(gross)
check(len(a._undo_stack) == max(8, 150000 // 20000) == 8, f"Tiefe bei 20000 Elementen: {len(a._undo_stack)}")
for _ in range(80): a._push_undo(kl)
check(len(a._undo_stack) == 50, "kleine Zeichnung: volle Tiefe 50")
# Undo/redo with compressed state
a2 = T.__new__(T); a2._undo_max = 50; a2._undo_stack = []; a2._redo_stack = []; a2._undo_pro_blatt = {}
a2._mark_dirty = lambda: None; a2._aktualisiere_undo_redo = lambda: None; a2.status = MagicMock()
zustand = {"v": gross}
a2._zustand = lambda: zustand["v"]; a2._zustand_wiederherstellen = lambda s: zustand.__setitem__("v", s)
klein = {"elemente": [], "layouts": [], "layers": []}
a2._push_undo(gross); zustand["v"] = klein
a2.undo(); check(zustand["v"] == gross and isinstance(a2._redo_stack[-1], dict), "undo entpackt grossen Zustand")
a2.redo(); check(zustand["v"] == klein, "redo")
# Sheet stack limited
for i in range(10): a._undo_stack, a._redo_stack = [i], []; a._stacks_merken(f"p{i}")
check(len(a._undo_pro_blatt) == 4 and list(a._undo_pro_blatt) == ["p6", "p7", "p8", "p9"], "nur 4 Blatt-Historien im Speicher")

# ---------- Menu: Electrical after Blocks ----------
src = open(A.__file__, encoding="utf-8").read()
order = [m.group(1) for m in re.finditer(r'menubar\.add_cascade\(label=tr\("menu\.(\w+)"\)', src)]
check(order.index("elektro") == order.index("bloecke") + 1, f"Menue-Reihenfolge: {order}")
# ---------- Platform ----------
check("Segoe UI" not in src.replace('UI_SCHRIFT = ', ''), "keine fest verdrahtete Windows-Schrift mehr")
check(not re.search(r"(?<![a-z])tk\.Button\(", src), "keine tk.Button (Farbe wird unter macOS ignoriert)")
check('c.bind(f"<Button-{r}>"' in src and "BTN_RECHTS" in src, "Maustasten plattformabhaengig")
check(core.UI_SCHRIFT in ("Segoe UI", "Helvetica Neue", "DejaVu Sans"), "UI_SCHRIFT")
print(f"{ok} Checks bestanden")

# ---- free text positions (mask, terminal, pin, device block) ----
_kl = core.Klemme(0, 0, {"IND": "-X1", "NUM": "L1"})
_g = dict((gid, (gx, gy)) for gid, gx, gy in _kl.griffe())
check("t:NUM" in _g and "t:IND" in _g, "Klemme: Text-Griffe")
_n0 = [e for e in _kl.aufgeloest(False) if getattr(e, "inhalt", None) == "L1"][0]
_kl.griff_bewegen("t:NUM", _g["t:NUM"][0] + 4, _g["t:NUM"][1] - 2)
_n1 = [e for e in _kl.aufgeloest(False) if getattr(e, "inhalt", None) == "L1"][0]
check(near(_n1.x, _n0.x + 4) and near(_n1.y, _n0.y - 2), "Klemme: NUM verschiebbar")
check(near(_n1.hoehe, 1.75), "Klemme NUM 1.75 mm")
_d = _kl.to_dict(); _d.pop("typ"); check(core.Klemme(**_d).versatz["NUM"] == [4.0, -2.0], "Klemme: Versatz gespeichert")
_kl.texte_zuruecksetzen(); check(not _kl.versatz, "Klemme: Texte zuruecksetzen")
_m = core.ElektroMaske(0, 0, {"IND": "K1", "TYP": "T", "PER": "P"})
_gm = dict((gid, (gx, gy)) for gid, gx, gy in _m.griffe())
check({"t:IND", "t:TYP", "t:PER"} <= set(_gm), "Maske: Text-Griffe")
_m.griff_bewegen("t:IND", _gm["t:IND"][0] - 3, _gm["t:IND"][1] + 3)
_i0 = [e for e in _m.aufgeloest(False) if getattr(e, "inhalt", None) == "K1"][0]
check(near(_i0.x, _gm["t:IND"][0] - 3), "Maske: IND verschiebbar")
_vp = core.Verbindungspunkt(5, 5, wert="13")
_gv = dict((gid, (gx, gy)) for gid, gx, gy in _vp.griffe())
check("t" in _gv, "Pin: Text-Griff")
_vp.griff_bewegen("t", _gv["t"][0] + 2, _gv["t"][1] + 1)
check(near(_vp.text_element().x, _gv["t"][0] + 2), "Pin: Beschriftung verschiebbar")
# device block: texts of the instance
_blk = core.BlockReferenz(0, 0, "G", [core.Linie(0, 0, 5, 0), core.Verbindungspunkt(0, 0, tag="VP1", wert="1"),
                                      core.ElektroMaske(5, 5, {"IND": "Q1"})])
_gb = dict((gid, (gx, gy)) for gid, gx, gy in _blk.griffe())
check("t:V:VP1" in _gb and "t:M:IND" in _gb, f"Block: Text-Griffe {sorted(_gb)}")
_blk.griff_bewegen("t:V:VP1", _gb["t:V:VP1"][0] + 3, _gb["t:V:VP1"][1])
_vt = [e for e in _blk.aufgeloest() if isinstance(e, core.Verbindungspunkt)][0].text_element()
check(near(_vt.x, _gb["t:V:VP1"][0] + 3), "Block: Pin-Text je Instanz verschiebbar")
_blk.griff_bewegen("t:M:IND", _gb["t:M:IND"][0] - 2, _gb["t:M:IND"][1] - 2)
_ind = [t for e in _blk.aufgeloest() if isinstance(e, core.ElektroMaske) for t in e.aufgeloest(False) if getattr(t, "inhalt", None) == "Q1"][0]
check(near(_ind.x, _gb["t:M:IND"][0] - 2), "Block: Masken-Text je Instanz verschiebbar")
_bd = _blk.to_dict(); _bd.pop("typ")
check(_bd["text_versatz"].get("V:VP1") and "_anker" not in _bd, "Block: Versatz gespeichert")
_blk.texte_zuruecksetzen(); check(not _blk.text_versatz, "Block: Texte zuruecksetzen")
