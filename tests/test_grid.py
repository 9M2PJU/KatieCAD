import sys, os, json, tempfile, shutil, types
from unittest.mock import MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.electrical.logic as L
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
A.messagebox = MagicMock()

class T(A.CadApp):
    view = {"zoom": 2.0, "ox": 0, "oy": 0}

def make():
    a = T.__new__(T)
    a.root = MagicMock(); a.status = MagicMock(); a.entry_eingabe = MagicMock()
    a.canvas = MagicMock(); a.redraw = MagicMock()
    a._dirty = False; a.projekt = None
    a._undo_stack = []; a._redo_stack = []; a._undo_max = 50; a._undo_pro_blatt = {}
    a._qv_cache = {}; a._ge_cache = {}
    a.elemente = []; a.layers = a._standard_layers()
    a.layouts = [core.Layout("Layout1", core.Layout.STANDARD_FORMAT, "#1c132d")]
    a.aktives_layout = 0
    a.auswahl = []; a._op = None
    a._auswahl_rechteck_id = None; a._drag_modus = None; a._auswahl_richtung = None
    a._ist_layout = lambda: False
    return a

# ---------- Geometry ----------
f = core.Koordinatenfeld(0, 0)
check((f.breite, f.hoehe, f.spalten, f.zeilen) == (287.0, 164.0, 6, 4), "Standardgroesse A4 ohne Schriftkopf")
check(f.zone(10, 140) == "1/A", "links oben = 1/A")
check(f.zone(280, 5) == "6/D", "rechts unten = 6/D")
check(f.zone(150, 75) in ("4/B", "3/B", "4/C", "3/C"), "Mitte")
check(f.zone(-1, 0) is None and f.zone(300, 10) is None, "ausserhalb = None")
check(len(f.aufgeloest(False)) < len(f.aufgeloest(True)), "Umriss nur auf Wunsch")
ust = [k for k in f.aufgeloest(True) if getattr(k, "linientyp", "") == "Strichlinie (verdeckt)"]
check(len(ust) == 4 and f.bbox() == (0.0, 0.0, 287.0, 164.0), "gestrichelter Umriss = Viewport-Flaeche")
texte = [k.inhalt for k in f.aufgeloest() if isinstance(k, core.Text)]
check(texte == list("123456") + list("ABCD"), f"Beschriftung {texte}")
f2 = core.Koordinatenfeld(0, 0, raster=True)
laenge = lambda fe: sum(abs(k.x2 - k.x1) + abs(k.y2 - k.y1) for k in fe.aufgeloest() if isinstance(k, core.Linie))
check(laenge(f2) > laenge(f), "Rasterlinien optional")
a = make()
d = f.to_dict()
f3 = a._dict_zu_element(json.loads(json.dumps(d)))
check(isinstance(f3, core.Koordinatenfeld) and f3.to_dict() == d, "Speichern/Laden")
check(core.Koordinatenfeld in core.ZUSAMMENGESETZT and core.Koordinatenfeld.NUR_KLICK, "zusammengesetzt, nur Klick")
check(core.ort_text((1, "1/A")) == "1/1/A" and core.ort_text((2, "")) == "2" and core.ort_text(3) == "3", "ort_text")

# ---------- Selection: window ignores the field ----------
a.elemente = [f, core.Linie(10, 10, 20, 20), core.Linie(50, 50, 60, 60)]
for richtung in ("links", "rechts"):
    t = a._elemente_im_auswahlrechteck((-5, -5, 400, 300), richtung)
    check(f not in t and len(t) == 2, f"Fenster {richtung}: Feld nicht markiert")
check(a._punkt_auf_element(f, 100, 75, 1.0) is False, "Inneres des Feldes ist nicht klickbar")
check(a._punkt_auf_element(f, 100, 0.0, 1.0) and a._punkt_auf_element(f, 100, 163.5, 1.0), "Umriss/Rahmen ist klickbar")

# ---------- Additive selection ----------
l1, l2 = a.elemente[1], a.elemente[2]
def rahmen(x0, y0, x1, y1):             # in mm; zoom 2, y mirrored
    a._auswahl_rechteck_start = (x0 * 2, -y0 * 2, x0, y0)
    a._drag_modus = "auswahl_rechteck"
    a._finalisiere_auswahl_rechteck(NS(x=x1 * 2, y=-y1 * 2))
rahmen(5, 5, 25, 25)
check(a.auswahl == [l1], "erster Rahmen")
rahmen(45, 45, 65, 65)
check(a.auswahl == [l1, l2], "zweiter Rahmen ergaenzt statt zu ersetzen")
rahmen(5, 5, 25, 25)
check(a.auswahl == [l1, l2], "kein Doppeleintrag")
a._auswahl_rechteck_start = (300, -300, 150, 150); a._drag_modus = "auswahl_rechteck"
a._finalisiere_auswahl_rechteck(NS(x=300, y=-300))
check(a.auswahl == [l1, l2], "Klick ins Leere behaelt die Auswahl")
a.aktives_werkzeug = NS(get=lambda: "auswahl")
a._werkzeug_gewechselt = MagicMock()
a._werkzeug_toolbar()
check(a.auswahl == [], "Werkzeug 'Auswahl' hebt die Markierung auf")
a.auswahl = [l1]
a.aktives_werkzeug = NS(get=lambda: "linie", set=lambda v: None)
a._werkzeug_toolbar()
check(a.auswahl == [l1], "anderes Werkzeug (Toolbar-Funktion) loescht nicht selbst")

# ---------- Coordinates in cross references ----------
feld = core.Koordinatenfeld(0, 0)
q_a = core.Querverweis(10, 140, "L1", "abgehend", 0)       # 1/A
q_b = core.Querverweis(200, 20, "L1", "ankommend", 0)      # 5/D (same sheet)
L.querverweis_ziele([feld, q_a, q_b], 1, {})
check(q_a.ziel == [(1, q_b_f := feld.zone(200, 20))] and q_b.ziel == [(1, "1/A")], f"gleiches Blatt: {q_a.ziel} {q_b.ziel}")
check(q_a.ziel_text() == "(Blatt 1/" + q_b_f + ")", q_a.ziel_text())
q = core.Querverweis(10, 140, "N", "abgehend", 0)
L.querverweis_ziele([feld, q], 1, {2: [("N", "3/B"), ("N", "")], 3: ["N"]})
check(q.ziel == [(2, ""), (2, "3/B"), (3, "")] and q.ziel_text() == "(Blatt 2, 2/3/B, 3)", q.ziel_text())
q = core.Querverweis(10, 140, "N", "abgehend", 0)
L.querverweis_ziele([q], 1, {2: [("N", "3/B")]})
check(q.ziel_text() == "(Blatt 2/3/B)", "mit Feld auf Blatt 2, ohne Feld auf Blatt 1")

# ---------- Coordinates across the project (files) ----------
a = make()
p = Projekt.erstellen("Anlage", tmp)
b1 = p.blatt_hinzufuegen("A"); b2 = p.blatt_hinzufuegen("B")
def schreibe(b, elems):
    json.dump({"einheit": "mm", "layers": [], "elemente": [e.to_dict() for e in elems],
               "layouts": [core.Layout("Layout1", core.Layout.STANDARD_FORMAT, "#1c132d").to_dict()],
               "aktives_layout": 0, "ansicht": "modell"}, open(p.blatt_pfad(b), "w"))
schreibe(b1, [core.Koordinatenfeld(0, 0), core.Querverweis(10, 140, "L1", "abgehend", 0),
              core.ElektroMaske(280, 5, {"IND": "-Q1", "PER": "K1"}, rolle="haupt")])
schreibe(b2, [core.Querverweis(0, 0, "L1", "ankommend", 0)])
p.speichern(); a.projekt = p; p.aktiv = 1
qx = core.Querverweis(0, 0, "L1", "ankommend", 0)
hilfs = core.ElektroMaske(100, 20, {"IND": "-Q1", "PER": "K1"}, rolle="hilfs")
a.elemente = [core.Koordinatenfeld(0, 0), qx, hilfs]
a._querverweise_aktualisieren()
check(qx.ziel == [(1, "1/A")] and qx.ziel_text() == "(Blatt 1/1/A)", f"Ziel aus Datei: {qx.ziel}")
a._geraete_aktualisieren()
check(hilfs.refs == [(1, "6/D")], f"REF mit Koordinate aus Datei: {hilfs.refs}")
check(any("1/6/D" in (k.inhalt if isinstance(k, core.Text) else "") for k in hilfs.aufgeloest()), "REF-Text 'Blatt 1/6/D'")
hauptg = core.ElektroMaske(280, 5, {"IND": "-Q1", "PER": "K1"}, rolle="haupt")
schreibe(b2, [hilfs])                      # Sheet 2: auxiliary device, no field
a.projekt = p; p.aktiv = 0
a.elemente = [core.Koordinatenfeld(0, 0), hauptg]
a._geraete_blatt = A.CadApp._geraete_blatt.__get__(a)
a._geraete_aktualisieren()
check(hauptg.refs == [(2, "")], f"Blatt 2 ohne Feld -> nur Blattnummer: {hauptg.refs}")

# ---------- Print/DXF: no outline ----------
from katiecad.fileio import pdf as PDF
check(PDF.Koordinatenfeld is core.Koordinatenfeld, "PDF kennt das Koordinatenfeld")
# ---------- COPYBASE: base point is kept ----------
import inspect
check("_clipboard_mit_basis" not in inspect.getsource(A.CadApp._escape), "ESC loescht den Basispunkt der Zwischenablage nicht")
a = make()
a._paste_aktiv = False; a._paste_vorlagen = []; a._paste_vorschau_ids = []
a._clipboard = [core.Linie(100, 100, 120, 100).to_dict()]
a._clipboard_basispunkt = (0.0, 0.0); a._clipboard_mit_basis = True
a._maus_px = (0, 0); a._paste_vorschau_aktualisieren = MagicMock()
a.einfuegen()
check(a._paste_bezug == (0.0, 0.0), f"Einfuegen nutzt Basispunkt (0,0): {a._paste_bezug}")
shutil.rmtree(tmp, ignore_errors=True)
print(f"{ok} Checks bestanden")
