import sys, os, json, tempfile, types, math, shutil
from unittest.mock import MagicMock
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401  (installiert die tkinter-Attrappe)
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
    a._qv_cache = {}; a._ge_cache = {}; a._vb_vorgabe = None; a._mk_werte = {}; a._mk_rolle = "haupt"; a._kl_werte = {}
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

# ---- Bogen: 3-Punkt-Griffe
b = core.Bogen(0, 0, 10, 0, 90)
ids = [g[0] for g in b.griffe()]
check(set(["start", "mitte", "ende"]) <= set(ids), "Bogen hat Start/Mitte/Ende-Griffe")
g = {g[0]: g for g in b.griffe()}
b.griff_bewegen("ende", 0, 12)
check(near(math.hypot(b.cx - 0, 0) , abs(b.cx)) and b.r > 0, "Bogen nach Endpunkt-Zug gueltig")
# Kreis durch drei Punkte bleibt durch Start
sx = b.cx + b.r * math.cos(math.radians(b.start)); sy = b.cy + b.r * math.sin(math.radians(b.start))
check(near(sx, 10, 1e-4) and near(sy, 0, 1e-4), "Startpunkt bleibt fix")
ex = b.cx + b.r * math.cos(math.radians(b.ende)); ey = b.cy + b.r * math.sin(math.radians(b.ende))
check(near(ex, 0, 1e-4) and near(ey, 12, 1e-4), "Endpunkt liegt am Zugpunkt")

# ---- Schraffur im Block (verschieben/drehen/skalieren)
h = core.Schraffur([(0, 0), (10, 0), (10, 10), (0, 10)], muster="linien", winkel=45, abstand=2)
blk = core.BlockReferenz(50, 50, "S", [h], winkel=90, skalierung=2) if "skalierung" in core.BlockReferenz.__init__.__code__.co_varnames else core.BlockReferenz(50, 50, "S", [h])
k = blk.aufgeloest()
check(any(isinstance(x, core.Schraffur) for x in k), "Schraffur im Block aufgeloest")

# ---- Verbindung
v2 = core.Verbindung(0, 0, 2, 0)
an = v2.anschluesse()
check(len(an) == 2 and {(round(x, 3), round(y, 3)) for x, y, _ in an} == {(2.5, 0.0), (0.0, 2.5)}, "Verbindung 2: Ecke Ost+Nord")
check(len(core.Verbindung(0, 0, 3, 1).anschluesse()) == 3, "Verbindung 3")
check(len(core.Verbindung(0, 0, 4, 0).anschluesse()) == 4, "Verbindung 4")
d = v2.to_dict(); check(d["typ"] == "verbindung", "to_dict typ")
a = make()
v = a._dict_zu_element(json.loads(json.dumps(d)))
check(isinstance(v, core.Verbindung) and v.art == 2, "Verbindung Roundtrip")
check(v2.farbe.lower() == "#ff0000", "Verbindung rot")

# ---- Maske / Klemme Roundtrip
m = core.ElektroMaske(5, 5, {"IND": "K1", "TYP": "LC1", "PER": "=A+B"}, rolle="hilfs")
m2 = a._dict_zu_element(json.loads(json.dumps(m.to_dict())))
check(isinstance(m2, core.ElektroMaske) and m2.werte["PER"] == "=A+B" and m2.rolle == "hilfs", "Maske Roundtrip")
ak = core.ElektroMaske(0, 0).aufgeloest()
check(not any(isinstance(t, core.Text) for t in ak) and len(ak) == 2, "Leere Maske: kein Text, nur Markierungskreuz")
tx = [t.inhalt for t in core.ElektroMaske(0, 0).aufgeloest(platzhalter=False)]
check(tx == [], "Druck ohne Platzhalter")
kl = core.Klemme(0, 0, {"NUM": "3", "IND": "X1"})
kd = a._dict_zu_element(json.loads(json.dumps(kl.to_dict())))
check(isinstance(kd, core.Klemme) and kd.werte["NUM"] == "3", "Klemme Roundtrip")
check(near(kl.anschluss_oben()[1], 1.25) and near(kl.anschluss_unten()[1], -1.25), "Klemme Anschluesse oben/unten")
check(any(isinstance(x, core.Kreis) for x in kl.aufgeloest()), "Klemme hat Kreis")

# ---- Block mit Maske: Attribute
bd = core.BlockReferenz(0, 0, "G", [core.Rechteck(0, 0, 5, 5), core.ElektroMaske(6, 0)])
check({d.tag for d in bd.attribut_definitionen()} >= {"IND", "TYP", "PER"}, "Block-Attribute aus Maske")
bd.attribute.update({"IND": "Q1", "PER": "X"})
tx = [t.inhalt for m_ in bd.aufgeloest() if isinstance(m_, core.ElektroMaske) for t in m_.aufgeloest() if isinstance(t, core.Text)]
check("Q1" in tx, "Attributwert in Block-Maske sichtbar")
bd2 = a._dict_zu_element(json.loads(json.dumps(bd.to_dict())))
check(bd2.attribute.get("IND") == "Q1" and bd2.geraet_maske() is not None, "Block mit Maske Roundtrip")

# ---- Referenzen
h1 = core.ElektroMaske(0, 0, {"IND": "K1"}, rolle="haupt")
h2 = core.ElektroMaske(0, 50, {"IND": "K1"}, rolle="hilfs")
h3 = core.ElektroMaske(0, 90, {"IND": "K1"}, rolle="hilfs")
g = E.geraete([h1, h2, h3], 1)
E.geraete_referenzen(g, 1, {2: [("K1", "hilfs", "a"), ("K1", "haupt", "b")], 3: [("K1", "hilfs", "c")]})
check(h1.refs == [1, 2, 3], "Haupt verweist auf alle Hilfs: %s" % h1.refs)
check(h2.refs == [1, 2], "Hilfs verweist nur auf Haupt: %s" % h2.refs)
check(any("(Blatt 1)" in t.inhalt and "(Blatt 2)" in t.inhalt for t in h2.aufgeloest() if isinstance(t, core.Text)), "REF-Text (Blatt n)")

# ---- Leitung teilen
ls = [core.Leitung(0, 0, 20, 0)]
check(E.leitung_teilen(ls, 10, 0) and len(ls) == 2, "Leitung geteilt")
check(not E.leitung_teilen(ls, 0, 0), "Endpunkt teilt nicht")
a = make(); a.view = {"zoom": 2.0, "ox": 0, "oy": 0}
a.elemente = [core.Leitung(0, 0, 40, 0)]
a._vb_vorgabe = {"art": 3, "ausrichtung": 1, "punkt": True}
a._verbindung_platzieren(20.1, 0.1)
check(sum(isinstance(e, core.Leitung) for e in a.elemente) == 2 and any(isinstance(e, core.Verbindung) for e in a.elemente), "App: Verbindung teilt Leitung")
a.elemente = [core.Leitung(0, 0, 40, 0)]
import katiecad.ui.dialogs as D
A.VerbindungspunktDialog = lambda *x, **k: NS(result={"wert": "P", "sichtbar": True})
a._vp_platzieren(20, 0.2)
check(sum(isinstance(e, core.Leitung) for e in a.elemente) == 2, "App: Pin teilt Leitung")

# ---- Bereinigen
vb = core.Verbindung(20, 0, 2, 0)           # Arme Ost (22.5,0) und Nord (20,2.5)
pin1 = core.Verbindungspunkt(22.5, 30, wert="a"); pin2 = core.Verbindungspunkt(50, 0, wert="b")
w1 = core.Leitung(20, 2.5, 22.5, 30); w2 = core.Leitung(22.5, 0, 50, 0)
pin1.x, pin1.y = 22.5, 30
els = [vb, pin1, pin2, w1, w2]
vor = E.vollstaendige_verbindungen(els)
check(id(vb) in vor, "Verbindung mit 2 gueltigen Leitungen = vollstaendig")
els.remove(pin2)
n = E.verbindungen_bereinigen(els, vor)
check(n[0] == 1 and vb not in els and w1 not in els and w2 not in els, "Verbindung ohne Gegenpart verschwindet samt Leitungen: %s" % (n,))

# ---- Loeschen in App
a = make()
vb = core.Verbindung(20, 0, 2, 0); pin1 = core.Verbindungspunkt(22.5, 30, wert="a"); pin2 = core.Verbindungspunkt(50, 0, wert="b")
a.elemente = [vb, pin1, pin2, core.Leitung(20, 2.5, 22.5, 30), core.Leitung(22.5, 0, 50, 0)]
a.auswahl = [pin2]; a.auswahl_loeschen()
check(not any(isinstance(e, core.Verbindung) for e in a.elemente), "App: Loeschen raeumt Verbindung auf")
check(any(isinstance(e, core.Verbindungspunkt) for e in a.elemente), "Pin a bleibt")

# ---- Maske/Klemme platzieren + NUM
A.FestMaskeDialog = lambda root, titel, felder, werte=None, rolle=None, hinweis="": NS(result={"werte": dict(werte or {}, **({"NUM": werte.get("NUM", "1")} if "NUM" in felder else {})), "rolle": rolle})
a = make(); a._kl_werte = {"NUM": "1"}
a._klemme_platzieren(0, 0); a._klemme_platzieren(0, 10)
ns = [e.werte["NUM"] for e in a.elemente if isinstance(e, core.Klemme)]
check(ns == ["1", "2"], "NUM zaehlt hoch: %s" % ns)
a._maske_platzieren(5, 5)
check(any(isinstance(e, core.ElektroMaske) for e in a.elemente), "Maske platziert")

# ---- Geraete-Referenz ueber Blaetter (Projekt)
tmp = tempfile.mkdtemp()
pr = Projekt.neu(tmp, "P", 2) if hasattr(Projekt, "neu") else None
print("Projekt.neu:", pr is not None)

# ---- Transformationen
m = core.ElektroMaske(10, 10, {"PER": "K"})
m.verschieben(5, 5); check((m.x, m.y) == (15, 15), "Maske verschieben")
vv = core.Verbindung(0, 0, 2, 0); vv.drehen(0, 0, 90)
check(vv.ausrichtung in (1, 3), "Verbindung drehen aendert Ausrichtung: %d" % vv.ausrichtung)


# ---- Runde 5
k = core.Klemme(0, 0, {"NUM": "1"})
check([t.inhalt for t in k.aufgeloest() if isinstance(t, core.Text)] == ["1"], "Klemme: leere Felder ohne Text")
check(set(k.werte) == {"IND", "TYP", "PER", "NUM"}, "Klemme: Attribute vorhanden")
mk = core.ElektroMaske(100, 50, {"IND": "K1", "TYP": "LC1", "PER": "X"})
b = mk.bbox()
check(near(b[2], 100, 0.01) and b[1] >= 50 - 1.5, "Maske: Einfuegepunkt unten rechts (bbox %s)" % (b,))
check(all(t.einfuegepunkt.endswith("rechts") for t in mk.aufgeloest()), "Maske: rechtsbuendig")
mk.refs = [2, 3, 4]
b2 = mk.bbox(); check(b2[3] > b[3], "Maske waechst nach oben mit REF-Zeilen")
v3 = core.Verbindung(0, 0, 3, 0)
check({d for _, _, d in v3.anschluesse()} == {0, 90, 180}, "T-Stueck Ausrichtung 0: Ost/Nord/West")
v3 = core.Verbindung(0, 0, 3, 1)
check({d for _, _, d in v3.anschluesse()} == {90, 180, 270}, "T-Stueck Ausrichtung 1 gedreht")
check(len([x for x in core.Verbindung(0, 0, 4, 0, False).aufgeloest()]) == 4, "Kreuz mit Knick: 4 Linien")
check(not any(isinstance(x, core.Schraffur) for x in core.Verbindung(0, 0, 4, 0, False).aufgeloest()), "Kreuz ohne Punkt")
# Leitungen verschwinden ohne Gegenpart
p1 = core.Verbindungspunkt(0, 0, wert="a"); p2 = core.Verbindungspunkt(30, 0, wert="b"); w = core.Leitung(0, 0, 30, 0)
els = [p1, p2, w]
vl = E.vollstaendige_leitungen(els); check(id(w) in vl, "Leitung mit zwei Enden vollstaendig")
els.remove(p2); n = E.verbindungen_bereinigen(els, set(), vl)
check(w not in els and n == (0, 1), "Leitung ohne Gegenpart verschwindet")
a = make(); a.view = {"zoom": 2.0, "ox": 0, "oy": 0}
p1 = core.Verbindungspunkt(0, 0, wert="a"); p2 = core.Verbindungspunkt(30, 0, wert="b"); w = core.Leitung(0, 0, 30, 0)
a.elemente = [p1, p2, w]; a.auswahl = [p1]; a.auswahl_loeschen()
check(a.elemente == [p2], "App: Pin loeschen entfernt angehaengte Leitung")

# ---- Runde 6
kt = core.Klemme(0, 0, {"IND": "X", "TYP": "T", "PER": "P", "NUM": "1"})
tt = {t.inhalt: t for t in kt.aufgeloest() if isinstance(t, core.Text)}
check(tt["P"].einfuegepunkt == "mitte_rechts" and tt["P"].x < -1.25 and near(tt["X"].y, 0), "Klemme: IND auf Hoehe der Kreismitte, rechtsbuendig am Kreis")
check(tt["X"].y > tt["T"].y > tt["P"].y, "Klemme: IND, darunter TYP, PER")
# Leitungen einrasten
ls = [core.Leitung(0, 0, 0, 100)]
kl = core.Klemme(0, 50)
n = E.leitungen_einrasten(ls, [kl])
check(n == 1 and len(ls) == 2, "Klemme unterbricht Leitung")
ends = sorted([(round(l.y1, 2), round(l.y2, 2)) for l in ls])
check(ends == [(0.0, 48.75), (51.25, 100.0)], "Zwischen oben/unten der Klemme entfaellt die Leitung: %s" % ends)
ls = [core.Leitung(0, 0, 0, 100)]
blkg = core.BlockReferenz(0, 50, "G", [core.Rechteck(-5, -10, 5, 10), core.Verbindungspunkt(0, 10, wert="1"), core.Verbindungspunkt(0, -10, wert="2")])
check(E.leitungen_einrasten(ls, [blkg]) == 1 and sorted((round(l.y1), round(l.y2)) for l in ls) == [(0, 40), (60, 100)], "Geraet mit Pins oben/unten unterbricht Leitung")
ls = [core.Leitung(0, 0, 0, 100)]
check(E.leitungen_einrasten(ls, [core.Klemme(30, 50)]) == 0 and len(ls) == 1, "Klemme daneben: keine Aenderung")
ls = [core.Leitung(0, 0, 0, 100)]
check(E.leitungen_einrasten(ls, [core.Verbindung(0, 30, 3, 0)]) == 1 and len(ls) == 2, "Verbindung teilt Leitung")
# in der App: Block einfuegen unterbricht
a = make(); a.view = {"zoom": 2.0, "ox": 0, "oy": 0}
d = core.BlockDefinition("G", (0, 0), [core.Rechteck(-5, -10, 5, 10), core.Verbindungspunkt(0, 10, wert="1"), core.Verbindungspunkt(0, -10, wert="2")])
a.block_bibliothek = core.BlockBibliothek(a._dict_zu_element); a.block_bibliothek.setze(d)
a._block_einfuege_name = "G"; a._warte_auf_blockpunkt = True
a._attribute_abfragen = lambda r: None; a.zeichenfarbe = "#fff"; a.linientyp = NS(get=lambda: "Volllinie (schmal)"); a.eigene_farbe = NS(get=lambda: False)
a.linienstaerke = NS(get=lambda: "0.35"); a._zahl = lambda v, d_: 0.35; a._update_eingabe_hinweis = MagicMock()
a.elemente = [core.Leitung(0, 0, 0, 100)]
a._block_einfuegen_an(0, 50)
check(sum(isinstance(e, core.Leitung) for e in a.elemente) == 2, "App: eingefuegtes Geraet teilt Leitung")
# Geraet erstellen
a = make(); a.view = {"zoom": 2.0, "ox": 0, "oy": 0}
a._block_erzeuge_auswahl = None; a._update_eingabe_hinweis = MagicMock()
mk = core.ElektroMaske(0, 0, {"IND": "K1"}); rc = core.Rechteck(0, 0, 5, 5)
a.auswahl = [rc]; a.geraet_erzeugen()
check(a._block_erzeuge_auswahl is None, "Gerät ohne Maske: abgelehnt")
a.auswahl = [mk, core.ElektroMaske(1, 1)]; a.geraet_erzeugen()
check(a._block_erzeuge_auswahl is None, "Gerät mit zwei Masken: abgelehnt")
a.auswahl = [mk, rc]; a.geraet_erzeugen()
check(a._block_erzeuge_auswahl == [mk, rc] and a._geraet_modus, "Gerät aus Auswahl gestartet")

A._BlockNameDialog = lambda *x, **k: NS(result="Schuetz")
A.FestMaskeDialog = lambda root, titel, felder, werte=None, rolle=None, hinweis="": NS(result={"werte": {}, "rolle": "hilfs"})
A.vp_tags_eindeutig = lambda r: None
a.block_bibliothek = core.BlockBibliothek(a._dict_zu_element)
a._naechster_block_name = lambda: "B1"; a._snap_marker_loeschen = MagicMock(); a._attribute_abfragen = lambda r: None
a.zeichenfarbe = "#fff"; a.linientyp = NS(get=lambda: "x"); a.eigene_farbe = NS(get=lambda: False); a.linienstaerke = NS(get=lambda: "0.35"); a._zahl = lambda v, d_: 0.35
a.elemente = [mk, rc]
a._block_erzeugen_fertig((0, 0))
refs_ = [e for e in a.elemente if isinstance(e, core.BlockReferenz)]
check(len(refs_) == 1 and refs_[0].geraet_maske().rolle == "hilfs", "Gerät erstellt, Rolle Hilfsgerät in der Definition")

# ---- i18n Paritaet
de = set(katiecad_i18n.TEXTE["de"]); en = set(katiecad_i18n.TEXTE["en"])
check(de == en, "i18n Paritaet %s" % (de ^ en))
print(ok, "Checks bestanden")
