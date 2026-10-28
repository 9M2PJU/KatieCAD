import sys, os, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.model.core as core
from katiecad.model import blocks as B
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

d = core.BlockDefinition("Schuetz", (0, 0), [
    core.Rechteck(-5, -5, 5, 5), core.Linie(0, 5, 0, 10), core.Kreis(0, 0, 2),
    core.Verbindungspunkt(0, 10, wert="A1"), core.Text(8, 0, "K1", 2.5, 0.0),
    core.ElektroMaske(8, -5, {"IND": "-K1"}), core.Klemme(0, -10, {"NUM": "3"})])
g = B.vorschau_geometrie(d)
check(len(g["linien"]) >= 5 and len(g["texte"]) >= 3, f"Vorschau: Linien/Texte {len(g['linien'])}/{len(g['texte'])}")
check(g["bbox"] is not None and g["bbox"][0] < -4.9 and g["bbox"][3] > 9.9, "Vorschau: Ausdehnung")
check(B.vorschau_geometrie(core.BlockDefinition("x", (0, 0), []))["bbox"] is None, "leerer Block")

tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, "Schuetze", "Haupt")); os.makedirs(os.path.join(tmp, ".versteckt"))
B.block_speichern(os.path.join(tmp, "Schuetze", B.vorschlag_dateiname("Schuetz")), d)
B.block_speichern(os.path.join(tmp, "Schuetze", "Haupt", "b.katieblock"), d)
open(os.path.join(tmp, "Schuetze", "notiz.txt"), "w").write("x")
check(B.unterordner(tmp) == ["Schuetze"], "Unterordner ohne versteckte")
check([n for n, _ in B.blockdateien(os.path.join(tmp, "Schuetze"))] == ["Schuetz.katieblock"], "nur Blockdateien")
check(B.unterordner(os.path.join(tmp, "gibts-nicht")) == [] and B.blockdateien("/nix") == [], "fehlende Ordner ok")
fac = lambda dd: core.Rechteck(**{k: v for k, v in dd.items() if k in ("x1", "y1", "x2", "y2")}) if dd.get("typ") == "rechteck" else None
check(B.standard_ordner().endswith(os.path.join("KatieCAD", "Blocks")), "Standardordner")
shutil.rmtree(tmp, ignore_errors=True)
print(f"{ok} Checks bestanden")
