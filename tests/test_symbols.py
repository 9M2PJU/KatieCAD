import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401  (installs the tkinter stand-in)
import katiecad.ui.app as A
import katiecad.model.core as core
from katiecad.model.blocks import block_laden, symbol_ordner, vorschau_geometrie

ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

a = A.CadApp.__new__(A.CadApp)
files = sorted(glob.glob(os.path.join(symbol_ordner(), "*", "*.katieblock")))
check(len(files) >= 30, "symbol library has files: %d" % len(files))
names = set()
for f in files:
    d = block_laden(f, a._dict_zu_element)
    n = os.path.basename(f)
    check(d.name not in names, "unique name " + d.name); names.add(d.name)
    masks = [e for e in d.elemente if isinstance(e, core.ElektroMaske)]
    pins = [e for e in d.elemente if isinstance(e, core.Verbindungspunkt)]
    if "Earth" in d.name or "Chassis" in d.name:
        check(not masks and len(pins) == 1, n + ": connection symbol has one pin and no mask")
    else:
        check(len(masks) == 1, n + ": exactly one mask")
    check(len(pins) >= 1, n + ": has pins")
    tags = [p.tag for p in pins]
    check(len(set(tags)) == len(tags), n + ": unique pin tags")
    check(all(p.wert for p in pins), n + ": pins are labelled")
    g = vorschau_geometrie(d)
    check(g["bbox"] is not None, n + ": preview geometry")
a.projekt = None
A.lade_konfiguration = lambda: {}
w = a._block_wurzeln()
check(any(os.path.normpath(p_) == os.path.normpath(symbol_ordner()) for _n, p_ in w), "block browser lists the symbol library")
print(ok, "Checks bestanden")
