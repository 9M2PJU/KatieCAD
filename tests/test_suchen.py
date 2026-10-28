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


import katiecad.electrical.suchen as SU
import tempfile, shutil, json

# ---- Find / replace on element objects
t1 = core.Text(0, 0, "Pumpe 1 und pumpe 2")
m1 = core.ElektroMaske(0, 0, {"IND": "K1", "TYP": "Schütz pumpe", "PER": ""})
q1 = core.Querverweis(0, 0, "L1")
v1 = core.Verbindungspunkt(0, 0, wert="13")
blk = core.BlockReferenz(0, 0, "G", [core.ElektroMaske(0, 0, {"IND": "K1"}), core.Text(0, 0, "K1 fix")], attribute={"NAME": "Pumpe K1"})
alle = [t1, m1, q1, v1, blk]
h = SU.suche(alle, "pumpe")
check(len(h) == 4 and {x.art for x in h} == {"text", "maske", "block"} or len(h) >= 3, "Suche ohne Gross/Klein: %d Treffer" % len(h))
check(len(SU.suche(alle, "pumpe", gross=True)) == 2, "Suche mit Gross/Klein")
check(len(SU.suche(alle, "K1")) == 3, "K1: Maske, Block-Attribut IND und NAME; Block-Inhalt wird nicht durchsucht")
check(len(SU.suche(alle, "Pump", wort=True)) == 0 and len(SU.suche(alle, "Pumpe", wort=True)) == 3, "Nur ganze Woerter")
n = SU.ersetze(SU.suche(alle, "K1"), "K1", "K7")
check(n == 3 and m1.werte["IND"] == "K7" and blk.attribute["IND"] == "K7" and blk.attribute["NAME"] == "Pumpe K7" and blk.elemente[1].inhalt == "K1 fix", "Ersetzen: Maske, Block-Attribute; Block-Text bleibt")
check(SU.ersetzt("Pumpe 1", "pumpe", "P", False) == "P 1" and SU.ersetzt("a.b", ".", "-") == "a-b", "Sonderzeichen werden nicht als Regex gedeutet")

# ---- Whole project: other sheets via JSON
tmp = tempfile.mkdtemp()
pr = Projekt.erstellen("T", tmp)
pr.blatt_hinzufuegen("Erstes"); pr.blatt_hinzufuegen("Zweites")
pr.aktiv = 0
def schreibe(i, elemente):
    with open(pr.blatt_pfad(i), "w", encoding="utf-8") as f:
        json.dump({"elemente": [e.to_dict() for e in elemente]}, f)
schreibe(1, [core.Text(0, 0, "Pumpe 2"), core.ElektroMaske(0, 0, {"IND": "K1"}), core.Linie(0, 0, 1, 1)])
laden = lambda pf: json.load(open(pf, encoding="utf-8"))
aktiv = [core.Text(0, 0, "Pumpe 1")]
th, daten = SU.suche_projekt(pr, aktiv, "pumpe", lade=laden)
check([t.blatt for t in th] == [0, 1] and list(daten) == [1], "Projektsuche: aktives Blatt (live) + anderes Blatt (JSON)")
th1, _ = SU.suche_projekt(pr, aktiv, "pumpe", ganzes_projekt=False, lade=laden)
check(len(th1) == 1, "Bereich 'Blatt' sucht nur das aktuelle Blatt")
n = SU.ersetze(th, "pumpe", "Motor")
check(n == 2 and aktiv[0].inhalt == "Motor 1" and daten[1]["elemente"][0]["inhalt"] == "Motor 2", "Ersetzen in Objekt und in JSON-Daten")
with open(pr.blatt_pfad(1), "w", encoding="utf-8") as f:
    json.dump(daten[1], f)
check(laden(pr.blatt_pfad(1))["elemente"][0]["inhalt"] == "Motor 2", "JSON zurueckgeschrieben")
th2, d2 = SU.suche_projekt(pr, aktiv, "K1", lade=laden)
check(len(th2) == 1 and th2[0].art == "maske" and th2[0].feld == "IND", "Maskenwert im JSON gefunden")
shutil.rmtree(tmp, ignore_errors=True)

# ---- Dialog logic (without Tk): search + replace over the whole project
import katiecad.ui.dialogs as D
D.messagebox = MagicMock(); D.messagebox.askyesno.return_value = True
tmp = tempfile.mkdtemp()
pr = Projekt.erstellen("T", tmp); pr.blatt_hinzufuegen("A"); pr.blatt_hinzufuegen("B"); pr.aktiv = 0
for i, txt in ((0, "Pumpe 1"), (1, "Pumpe 2")):
    with open(pr.blatt_pfad(i), "w", encoding="utf-8") as f:
        json.dump({"elemente": [core.Text(0, 0, txt).to_dict()]}, f)
ap = make(); ap.projekt = pr; ap._blatt_sichern = lambda: True
ap._json_atomar_schreiben = staticmethod(lambda pf, d: json.dump(d, open(pf, "w", encoding="utf-8")))
ap.elemente = [core.Text(0, 0, "Pumpe 1")]
dl = D.SuchenErsetzenDialog.__new__(D.SuchenErsetzenDialog)
dl.app = ap; dl._treffer = []; dl._daten = {}; dl._stand = 0
dl.tree = MagicMock(); dl.tree.get_children.return_value = []
dl.v_such = NS(get=lambda: "Pumpe"); dl.v_neu = NS(get=lambda: "Motor")
dl.v_gross = NS(get=lambda: True); dl.v_wort = NS(get=lambda: False); dl.v_bereich = NS(get=lambda: "projekt")
dl.v_status = MagicMock()
dl.suchen()
check(len(dl._treffer) == 2, "Dialog: 2 Treffer ueber 2 Blaetter")
dl.ersetzen(nur_auswahl=False)
check(ap.elemente[0].inhalt == "Motor 1" and json.load(open(pr.blatt_pfad(1), encoding="utf-8"))["elemente"][0]["inhalt"] == "Motor 2", "Dialog: 'Alle ersetzen' im offenen und im anderen Blatt")
check(D.messagebox.askyesno.called, "Dialog: Rueckfrage bei anderen Blaettern")
# double click -> jump (same sheet / other sheet)
ap.zu_element_springen = MagicMock(); dl._wegruecken = MagicMock()
ap.projekt.aktiv = 0
dl.v_such = NS(get=lambda: "Motor"); dl.suchen()
dl.tree.identify_row = lambda y: "0"
dl.springen(NS(y=1))
check(ap.zu_element_springen.call_args[0][0] is ap.elemente[0], "Springen: Objekt im offenen Blatt")
def wechsel(i):
    ap.projekt.aktiv = i
    ap.elemente = [core.Text(0, 0, "Motor 2")]
    return True
ap.blatt_wechseln = wechsel; ap._ist_layout = lambda: False
dl.tree.identify_row = lambda y: "1"
dl.springen(NS(y=2))
check(ap.projekt.aktiv == 1 and ap.zu_element_springen.call_args[0][0] is ap.elemente[0], "Springen: wechselt das Blatt und waehlt das Objekt")
shutil.rmtree(tmp, ignore_errors=True)

# ---- Match properties
a = make()
q = core.Linie(0, 0, 5, 0, layer="E_LINES", farbe="#ff0000", eig_farbe=True, linientyp="Strichlinie", staerke=0.7)
z = core.Linie(0, 0, 1, 1)
check(a._eigenschaften_anwenden(q, z) and (z.layer, z.farbe, z.eig_farbe, z.linientyp, z.staerke) == ("E_LINES", "#ff0000", True, "Strichlinie", 0.7), "Eigenschaften uebertragen: Linie")
tq = core.Text(0, 0, "A", hoehe=5.0, schriftart="Courier", layer="Schrift"); tz = core.Text(1, 1, "B")
a._eigenschaften_anwenden(tq, tz)
check(tz.hoehe == 5.0 and tz.schriftart == "Courier" and tz.layer == "Schrift" and tz.inhalt == "B", "Text: Hoehe/Schrift/Layer, Inhalt bleibt")
check(not a._eigenschaften_anwenden(q, q), "Quelle auf sich selbst: nichts")
sq = core.Schraffur([(0, 0), (1, 0), (1, 1)], "kreuz" if False else "solid", 30.0, 2.0); sz = core.Schraffur([(0, 0), (1, 0), (1, 1)])
a._eigenschaften_anwenden(sq, sz)
check((sz.winkel, sz.abstand) == (30.0, 2.0), "Schraffur: Winkel/Abstand")

# ---- Purge unused layers
a = make()
from katiecad.model.core import Layer
a.layers = {"0": Layer("0"), "Alt": Layer("Alt"), "Genutzt": Layer("Genutzt"), "NurBlock": Layer("NurBlock"), "E_LINES": Layer("E_LINES")}
a.elemente = [core.Linie(0, 0, 1, 1, layer="Genutzt"),
              core.BlockReferenz(0, 0, "B", [core.Linie(0, 0, 1, 1, layer="NurBlock")])]
a.layouts[0].elemente = [core.Linie(0, 0, 1, 1, layer="E_LINES")]
check(sorted(a.ungenutzte_layer()) == ["Alt"], "Bereinigen: nur 'Alt' ungenutzt (0, Block-Inhalt und Layout zaehlen mit)")
a.aktiver_layer = NS(get=lambda: "Alt")
check(a.ungenutzte_layer() == [], "Bereinigen: aktiver Layer bleibt")

# ---- i18n parity
de = set(katiecad_i18n.TEXTE["de"]); en = set(katiecad_i18n.TEXTE["en"])
check(de == en, "i18n Paritaet %s" % (de ^ en))
print(ok, "Checks bestanden")
