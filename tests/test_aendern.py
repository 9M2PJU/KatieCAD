import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.ui.app as A
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

class Var:
    def __init__(self): self.v = ""
    def set(self, v): self.v = v
    def get(self): return self.v

a = A.CadApp.__new__(A.CadApp)
a.status = Var(); a.letzter = None
a._snapshot = lambda: None; a.redraw = lambda: None; a._clear_temp = lambda: None
a._einh_faktor = lambda: 1.0
a.einheit = Var(); a.einheit.set("mm")
a._einrasten = lambda *x: 0
a._cmd_pending = None

# ---- Ausrichten
b = [(0, 0, 10, 10), (20, 5, 30, 25), (5, 40, 9, 44)]
check([d[0] for d in a.ausrichten_delta(b, "links")] == [0, -20, -5], "links")
check([d[0] for d in a.ausrichten_delta(b, "rechts")] == [20, 0, 21], "rechts")
check([d[1] for d in a.ausrichten_delta(b, "unten")] == [0, -5, -40], "unten")
check([d[1] for d in a.ausrichten_delta(b, "oben")] == [34, 19, 0], "oben")
check(abs(a.ausrichten_delta(b, "mitte_h")[0][0] - 10) < 1e-9, "mitte_h")
l1, l2 = core.Linie(0, 0, 10, 0), core.Linie(30, 5, 40, 5)
a.auswahl = [l1, l2]
a.ausrichten("links")
check((l2.x1, l2.x2, l1.x1) == (0, 10, 0), "ausrichten verschiebt Objekte")
a.auswahl = [l1]; a.ausrichten("links"); check("zwei" in a.status.get(), "ausrichten braucht 2 Objekte")

# ---- Laenge aendern
ln = core.Linie(0, 0, 100, 0)
a._laenge = {"el": ln, "ende": 2, "fest": (0.0, 0.0), "u": (1.0, 0.0), "laenge": 100.0}
a._laenge_eingabe("-20")
check(abs(ln.x2 - 80) < 1e-9 and a._laenge["el"] is None, f"-20 kuerzt: {ln.x2}")
a._laenge = {"el": ln, "ende": 2, "fest": (0.0, 0.0), "u": (1.0, 0.0), "laenge": 80.0}
a._laenge_eingabe("+5,5"); check(abs(ln.x2 - 85.5) < 1e-9, f"+5,5 verlaengert: {ln.x2}")
a._laenge = {"el": ln, "ende": 2, "fest": (0.0, 0.0), "u": (1.0, 0.0), "laenge": 85.5}
a._laenge_eingabe("=50"); check(abs(ln.x2 - 50) < 1e-9, "=50 setzt Laenge")
a._laenge = {"el": ln, "ende": 1, "fest": (50.0, 0.0), "u": (-1.0, 0.0), "laenge": 50.0}
a._laenge_eingabe("10"); check(abs(ln.x1 + 10) < 1e-9 and ln.x2 == 50, f"anderes Ende: {ln.x1}")
a._laenge = {"el": ln, "ende": 2, "fest": (0.0, 0.0), "u": (1.0, 0.0), "laenge": 50.0}
a._laenge_eingabe("-60"); check(ln.x2 == 50 and a._laenge["el"] is ln, "zu kurz wird abgelehnt")
check(abs(a._laenge_aus_punkt((70, 33)) - 70) < 1e-9, "Projektion auf die Linienrichtung")

# ---- Manipulator: Achsenbindung
check(a.achse_projektion((10, 20), (55, 77), "x") == (55, 20), "Achse X behaelt Y")
check(a.achse_projektion((10, 20), (55, 77), "y") == (10, 77), "Achse Y behaelt X")
check(a.achse_projektion((10, 20), (55, 77), None) == (55, 77), "frei")
a._op = {"typ": "move", "stufe": "ziel", "basis": (10, 20), "objekte": [], "achse": "x"}
check(a._op_achse((99, 99)) == (99, 20), "_op_achse")
a._op = None; check(a._op_achse((1, 2)) == (1, 2), "ohne Operation unveraendert")
check(core.BEFEHLE["MANIP"] == "manip" and core.BEFEHLE["LAENGE"] == "laenge" and core.BEFEHLE["AUSRECHTS"] == "ausrichten:rechts", "Befehle")
de = set(katiecad_i18n.TEXTE["de"]); en = set(katiecad_i18n.TEXTE["en"])
check(de == en, "i18n Paritaet %s" % (de ^ en))
print(ok, "Checks bestanden")
