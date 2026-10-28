import sys, os, json, tempfile, shutil, types, zlib, re, math
from unittest.mock import MagicMock
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401  (installs the tkinter stand-in)
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.ui.app as A
from katiecad.model.project import Projekt
NS = types.SimpleNamespace
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

tmp = tempfile.mkdtemp()
A.lade_konfiguration = lambda: {}
A.speichere_konfiguration = lambda d: None
mb = MagicMock(); A.messagebox = mb

class T(A.CadApp):
    view = {"zoom": 2.0, "ox": 0, "oy": 0}

def make():
    a = T.__new__(T)
    a.root = MagicMock(); a.status = MagicMock(); a.seitenleiste = MagicMock(); a.entry_eingabe = MagicMock()
    a._dirty = False; a.projekt = None
    a._undo_stack = []; a._redo_stack = []; a._undo_max = 50; a._undo_pro_blatt = {}
    a._leitung_p1 = None; a._leitung_dialog = MagicMock(); a._qv_vorgabe = None; a._vp_letzte_bez = ""; a._vp_text_anzeigen = True; a._qv_cache = {}
    a.elemente = []; a.layers = a._standard_layers(); a.layouts = [core.Layout("Layout1", core.Layout.STANDARD_FORMAT, "#1c132d")]
    a.aktives_layout = 0
    a._einh_faktor = lambda: 1.0
    a.dezimalkomma = NS(get=lambda: False)
    a.aktiver_layer = NS(get=lambda: "0")
    a.text_schriftart = NS(get=lambda: "Arial")
    a._layer_daten = lambda: {"layer": "0", "farbe": "#c29bff", "linientyp": "Volllinie (schmal)", "eig_farbe": False, "staerke": None}
    a._ziel_liste = lambda: a.elemente
    a._ist_layout = lambda: False
    a._zustand = lambda: {"n": len(a.elemente)}
    a.redraw = MagicMock(); a._clear_temp = MagicMock()
    return a

# ---------- Wire ----------
a = make()
vp1 = core.Verbindungspunkt(10, 10, wert="1"); vp2 = core.Verbindungspunkt(60, 10, wert="2")
blk = core.BlockReferenz(100, 100, "K", [core.Rechteck(-5, -5, 5, 5), core.Verbindungspunkt(0, 5, wert="X1")])
a.elemente = [vp1, vp2, blk]
a._leitung_klick(500, 500); check(a._leitung_p1 is None and a.status.set.called, "Klick ins Leere: kein Punkt")
a._leitung_klick(10.3, 10.2); check(a._leitung_p1 is not None and (a._leitung_p1.x, a._leitung_p1.y) == (10, 10), "1. Punkt gewaehlt")
a._leitung_dialog.setze.assert_called()
a._leitung_klick(10.0, 10.1); check(len(a.elemente) == 3, "gleicher Punkt: keine Leitung")
a._leitung_klick(60.2, 9.9)
l = [e for e in a.elemente if isinstance(e, core.Leitung)]
check(len(l) == 1 and (l[0].x1, l[0].y1, l[0].x2, l[0].y2) == (10, 10, 60, 10), "Leitung zwischen den zwei Punkten")
check(l[0].farbe == "#ff0000" and l[0].staerke == core.LEITUNG_STAERKE, "Leitung rot")
check(a._leitung_p1 is None and a._undo_stack and a._dirty, "Zurueckgesetzt fuer naechste Leitung, undo-faehig")
a._leitung_klick(100, 105)                       # Connection point INSIDE the block
check(a._leitung_p1 is not None and "X1" in a._leitung_p1.name, "VP in Block wird gefunden")
a._leitung_klick(10, 10)
l = [e for e in a.elemente if isinstance(e, core.Leitung)]
check(len(l) == 2 and (l[1].x1, l[1].y1) == (100, 105), "Leitung zu Block-VP")
a.layers["0"].sichtbar = False
check(naechster := A.naechster_vp(a.elemente, 10, 10, 2, a._el_sichtbar) is None, "VP auf unsichtbarem Layer wird nicht gewaehlt")
a.layers["0"].sichtbar = True
a._ist_layout = lambda: True; n = len(a.elemente); a._leitung_klick(10, 10); check(len(a.elemente) == n and a._leitung_p1 is None, "im Layout inaktiv")
a._ist_layout = lambda: False

# ---------- Place connection point ----------
a = make()
A.VerbindungspunktDialog = lambda parent, wert, sichtbar, titel=None, richtungen=None: NS(result=None)
a.aktives_werkzeug = NS(set=lambda v: None); a._werkzeug_gewechselt = lambda: None
a._vp_vorgabe = None; a._vp_platzieren(1, 1)
check(not any(isinstance(e, core.Verbindungspunkt) for e in a.elemente), "VP: Abbruch im Dialog legt nichts an")
A.VerbindungspunktDialog = lambda parent, wert, sichtbar, titel=None, richtungen=None: NS(result={"wert": "13", "sichtbar": True})
a._vp_starten(); a._vp_platzieren(5, 5); a._vp_platzieren(8, 5)
vps = [e for e in a.elemente if isinstance(e, core.Verbindungspunkt)]
check([v.wert for v in vps] == ["13", "14"] and a._vp_letzte_bez == "14", "VP: erst konfigurieren, dann setzen (Nummer zaehlt weiter)")
vps[1].sichtbar = False
check(vps[0].sichtbar and vps[1].text_element() is None and vps[0].text_element() is not None, "VP: Text optional ausblendbar")
check(vps[0].hoehe == 2.0 and vps[0].radius == 0.5, "VP: 2.0 mm Text, 1 mm Kreis")
A.VerbindungspunktDialog = lambda parent, wert, sichtbar, titel=None, richtungen=None: NS(result={"wert": "neu", "sichtbar": False})
a._vp_bearbeiten(vps[0]); check(vps[0].wert == "neu" and vps[0].inhalt == "neu" and not vps[0].sichtbar, "VP bearbeiten (Text ausblenden)")

# ---------- Place cross reference ----------
a = make(); a._qv_vorgabe = {"art": "ankommend", "richtung": 270, "text": "L1"}
a._qv_platzieren(20, 30)
q = a.elemente[0]
check(isinstance(q, core.Querverweis) and (q.art, q.richtung, q.text, q.x, q.y) == ("ankommend", 270, "L1", 20, 30) and q.eig_farbe, "Querverweis platziert")
A.QuerverweisDialog = lambda parent, vor: NS(result={"art": "abgehend", "richtung": 90, "text": "N"})
a._qv_bearbeiten(q); check((q.art, q.richtung, q.text) == ("abgehend", 90, "N"), "Querverweis bearbeiten")

# ---------- Targets across the project ----------
a = make()
p = Projekt.erstellen("Anlage", tmp)
b1 = p.blatt_hinzufuegen("Einspeisung"); b2 = p.blatt_hinzufuegen("Abgang"); b3 = p.blatt_hinzufuegen("Leer")
def blattdaten(elems):
    return {"einheit": "mm", "layers": [], "elemente": [e.to_dict() for e in elems],
            "layouts": [core.Layout("Layout1", core.Layout.STANDARD_FORMAT, "#1c132d").to_dict()],
            "aktives_layout": 0, "ansicht": "modell"}
def schreibe(b, elems): json.dump(blattdaten(elems), open(p.blatt_pfad(b), "w"))
schreibe(b1, [core.Querverweis(0, 0, "L1", "abgehend", 0), core.Linie(0, 0, 10, 10)])
schreibe(b2, [core.Querverweis(0, 0, "L1", "ankommend", 0), core.Querverweis(5, 5, "N", "abgehend", 0)])
schreibe(b3, [core.Linie(0, 0, 1, 1)])
p.speichern()
a.projekt = p; p.aktiv = 0
qa = core.Querverweis(0, 0, "L1", "abgehend", 0); qn = core.Querverweis(5, 0, "N", "abgehend", 0)
a.elemente = [qa, qn, core.Linie(0, 0, 10, 10)]
a._querverweise_aktualisieren()
bl = lambda x: [o[0] if isinstance(o, (tuple, list)) else o for o in x]
check(bl(qa.ziel) == [2] and bl(qn.ziel) == [2], f"Blatt 1 zeigt Ziel Blatt 2: {qa.ziel} {qn.ziel}")
p.aktiv = 1
q2 = core.Querverweis(0, 0, "L1", "ankommend", 0); a.elemente = [q2]
schreibe(b1, [core.Querverweis(0, 0, "L1", "abgehend", 0)])            # File changes -> cache invalidation
a._querverweise_aktualisieren(); check(bl(q2.ziel) == [1], "Blatt 2 zeigt Ziel Blatt 1")
schreibe(b1, [core.Linie(0, 0, 1, 1)])
a._querverweise_aktualisieren(); check(bl(q2.ziel) == [], "Gegenstueck entfernt -> Ziel leer (Cache aktualisiert)")
schreibe(b1, [core.Querverweis(0, 0, "L1", "abgehend", 0)])
a.projekt = None; a.elemente = [core.Querverweis(0, 0, "L1"), core.Querverweis(9, 9, "L1")]
a._querverweise_aktualisieren(); check(bl(a.elemente[0].ziel) == [1], "ohne Projekt: gleiches Blatt")

# ---------- Multi-sheet PDF ----------
a = make(); a.projekt = p; p.aktiv = 0
qa = core.Querverweis(10, 10, "L1", "abgehend", 0, layer="Schrift", farbe="#000000", eig_farbe=True)
a.elemente = [qa, core.Linie(0, 0, 50, 50, layer="0")]
out = os.path.join(tmp, "alle.pdf")
A.ProjektDruckDialog = lambda parent, proj: NS(result=("pdf", [0, 1, 2], "modell", True, False))
A.filedialog = MagicMock(); A.filedialog.asksaveasfilename.return_value = out
mb.reset_mock()
a.projekt_drucken()
pdf = open(out, "rb").read()
check(b"/Count 3" in pdf, "3 Seiten in EINER Datei")
st = [zlib.decompress(m.group(1)).decode("latin-1") for m in re.finditer(rb"stream\n(.*?)\nendstream", pdf, re.S)]
check("\\(Blatt 2\\)" in st[0] and "\\(Blatt 1\\)" in st[1], "Querverweis-Ziele in den PDF-Seiten (aktives Blatt aus Speicher, andere aus Datei)")
check(b"/Count" in pdf and not mb.showinfo.called, "keine Warnung")
# Selection only sheets 2 and 3 + empty layout sheet
A.ProjektDruckDialog = lambda parent, proj: NS(result=("pdf", [1, 2], "layout", False, True))
a.projekt_drucken(); pdf = open(out, "rb").read(); check(b"/Count 2" in pdf, "Auswahl-Teilmenge (Layout-Modus)")
# Empty model is skipped and reported
schreibe(b3, [])
A.ProjektDruckDialog = lambda parent, proj: NS(result=("pdf", [0, 2], "modell", False, False))
mb.reset_mock(); a.projekt_drucken(); pdf = open(out, "rb").read()
check(b"/Count 1" in pdf and mb.showinfo.called, "leeres Blatt uebersprungen + Meldung")
# Defective sheet file
open(p.blatt_pfad(b2), "w").write("{kaputt")
A.ProjektDruckDialog = lambda parent, proj: NS(result=("pdf", [0, 1], "modell", False, False))
mb.reset_mock(); a.projekt_drucken(); pdf = open(out, "rb").read()
check(b"/Count 1" in pdf and mb.showinfo.called, "defektes Blatt uebersprungen + Meldung")
# Cancel
A.ProjektDruckDialog = lambda parent, proj: NS(result=None); os.remove(out); a.projekt_drucken(); check(not os.path.exists(out), "Abbrechen schreibt nichts")
# Without project
a.projekt = None; a.projekt_drucken(); check(True, "ohne Projekt harmlos")

# ---------- Rename sheet (any sheet) ----------
a = make(); a.projekt = p; p.aktiv = 0
A.BlattEigenschaftenDialog = lambda *args, **kw: NS(result=("Neuer Name", "", "", ""))
a.blatt_umbenennen(2)
check(p.blaetter[2].name == "Neuer Name" and p.blaetter[0].name == "Einspeisung", "Nicht-aktives Blatt umbenannt")
check(Projekt.laden(p.projektdatei).blaetter[2].name == "Neuer Name", "Umbenennung gespeichert")
a.blatt_umbenennen(); A.BlattEigenschaftenDialog = lambda *args, **kw: NS(result=("", "", "", ""))
a.blatt_umbenennen(1); check(p.blaetter[1].name == "Abgang" and mb.showinfo.called, "Leerer Name abgelehnt")
shutil.rmtree(tmp, ignore_errors=True)

# ---- Rename project
from katiecad.model.project import ProjektFehler as _PF
_t = tempfile.mkdtemp()
_p = Projekt.erstellen("Alt", _t); _p.blatt_hinzufuegen("B1")
open(_p.blatt_pfad(0), "w").write("{}"); _p.speichern()
_mit = _p.umbenennen("Neu1")
_ok = (_mit and _p.name == "Neu1" and os.path.basename(_p.ordner) == "Neu1"
       and os.path.isfile(os.path.join(_t, "Neu1", "Neu1.katieprj"))
       and not os.path.exists(os.path.join(_t, "Alt")) and os.path.isfile(_p.blatt_pfad(0)))
assert _ok, "Projekt umbenennen (Datei+Ordner)"
assert Projekt.laden(_p.projektdatei).name == "Neu1" and len(Projekt.laden(_p.projektdatei).blaetter) == 1
os.makedirs(os.path.join(_t, "Belegt"))
for _bad, _code in (("", "leer"), ("a/b", "zeichen"), ("Belegt", "existiert")):
    try:
        _p.umbenennen(_bad); assert False, _bad
    except _PF as _e:
        assert str(_e) == _code, (_bad, str(_e))
assert _p.name == "Neu1" and os.path.isdir(os.path.join(_t, "Neu1"))
assert _p.umbenennen("Neu1") is False
# Folder is named differently from the project: only the file is renamed
_q = Projekt.erstellen("Q", _t); _q.ordner = os.path.join(_t, "Q"); os.rename(_q.projektdatei, os.path.join(_t, "Q", "Q.katieprj"))
_os_ = os.path.join(_t, "Q"); os.rename(_os_, os.path.join(_t, "Sonstwie")); _q.ordner = os.path.join(_t, "Sonstwie")
assert _q.umbenennen("Q2") is False and os.path.isfile(os.path.join(_t, "Sonstwie", "Q2.katieprj"))
print("Projekt umbenennen OK")

# ---- Only one dialog at a time
import katiecad.ui.dialogs as _D
class _FD:
    def __init__(self, master=None): self.master = master; self.alive = True
    def winfo_exists(self): return self.alive
    def destroy(self): self.alive = False
    def __str__(self): return "d%d" % id(self)
_D._OFFENE_DIALOGE[:] = []
_a = _FD(); _D._schliesse_andere_dialoge(_a)
_b = _FD(); _D._schliesse_andere_dialoge(_b)
assert not _a.alive and _b.alive, "new dialog closes the old one"
_c = _FD(master=_b); _D._schliesse_andere_dialoge(_c)
assert _b.alive and _c.alive, "child dialog keeps its parent open"
_d = _FD(); _D._schliesse_andere_dialoge(_d)
assert not _b.alive and not _c.alive and _d.alive
print("Dialog singleton OK")
print(f"{ok} Checks bestanden")
