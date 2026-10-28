import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.common.i18n as I; I.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
from katiecad.model.core import Rechteck, Koerper3D, Gruppe3D
from katiecad.model import geom3d as G, szene3d as S
import katiecad.ui.app as A
import katiecad.ui.ansicht3d as W
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

# bodies
q = W.koerper_bauen("quader", {"breite": 40, "tiefe": 30, "hoehe": 20}, 10, 10, 0)
check(q.bbox3()[2] == 0 and abs(q.bbox3()[5] - 20) < 1e-9, "Quader Hoehe")
for art, par in (("zylinder", {"radius": 5, "hoehe": 9}), ("kegel", {"radius": 5, "hoehe": 9}),
                 ("pyramide", {"ecken": 5, "breite": 10, "tiefe": 8, "hoehe": 7}), ("kugel", {"radius": 6})):
    k = W.koerper_bauen(art, par, 0, 0, 0)
    check(len(k.netz().kanten) > 3, art)
# hidden line: box iso
k = G.Kamera(); k.ansicht_setzen("iso_so")
s, v = G.sichtbare_linien([q.netz()], k, 400, 300)
check(len(v) >= 3 and len(s) >= 9, "verdeckte Kanten")
nz = q.netz()
s2, v2 = G.sichtbare_linien([nz], k, 400, 300, zeichnen={id(nz)})
check(len(s2) == len(s), "zeichnen-Filter")
s3, _ = G.sichtbare_linien([nz], k, 400, 300, zeichnen=set())
check(not s3, "leerer Filter")
# round trip
g = Gruppe3D([q, W.koerper_bauen("kugel", {"radius": 3}, 0, 0, 0)], name="B")
d = g.to_dict()
a = A.CadApp.__new__(A.CadApp)
g2 = a._dict_zu_element(d)
check(isinstance(g2, Gruppe3D) and len(g2.teile) == 2, "Gruppe round trip")
# extrude / group
r = Rechteck(0, 0, 10, 10)
liste = [r]
neu = S.extrudieren(liste, [r], 15)
check(len(neu) == 1 and isinstance(liste[0], Koerper3D) and abs(liste[0].hoehe - 15) < 1e-9, "extrudieren")
# icons
from katiecad.ui import icons as IC
for n in ("ansicht3d", "k_quader", "k_zylinder", "k_kegel", "k_pyramide", "k_kugel", "extrudieren",
          "loch", "block3d", "aufloesen3d", "wuerfel", "persp", "einpassen3d", "iso3d", "hoehe3d"):
    check(n in IC.NAMEN and (not IC.PIL_OK or IC.icon_png(n, "#c29bff")), "Icon " + n)
# holes
z = core.zylinder(0, 0, 10, 0, 20)
check(S.loch_ziele([z]) == [z], "Loch-Ziel")
check(S.loch_setzen(z, 2, 0, 3, None), "Loch setzen")
check(not S.loch_setzen(z, 50, 0, 3, None), "Loch ausserhalb")
check(len(z.netze()) == 2 and len(z.aufgeloest()) > 2, "Loch im Netz/Plan")
z.verschieben(5, 0, 2)
check(abs(z.loecher[0][0] - 7) < 1e-9, "Loch verschiebt mit")
z2 = a._dict_zu_element(z.to_dict())
check(len(z2.loecher) == 1 and z2.loecher[0][3] is None, "Loch Round-Trip")
z.loch_hinzufuegen(5, 0, 1, 4)
nz = z.netze()[2]
check(abs(nz.bbox()[5] - (2 + 20)) < 1e-6 and abs(nz.bbox()[2] - 18) < 1e-6, "Sackloch Tiefe")
# menu / commands
check(core.BEFEHLE.get("QUADER") == "3d:neu:quader" and core.BEFEHLE.get("3D") == "3d:oeffnen", "Befehle")
# i18n keys used by the window exist in both languages
import re
src = open(os.path.join(os.path.dirname(W.__file__), "ansicht3d.py"), encoding="utf-8").read()
src += open(os.path.join(os.path.dirname(A.__file__), "app.py"), encoding="utf-8").read()
for spr in ("de", "en"):
    T = I.TEXTE[spr]
    for key in [k for k in re.findall(r'tr\("(d3\.[a-z_.0-9]+|menu\.3d[a-z_.]*)"', src) if not k.endswith(".")]:
        check(key in T, f"{spr}: {key}")
    for art in W.PARAMETER:
        check("d3.neu." + art in T and "menu.3d." + art in T, art)
        for p in W.PARAMETER[art]:
            check("d3.dlg." + p in T, p)
    for n in ("ansicht3d", "k_quader", "k_zylinder", "k_kegel", "k_pyramide", "k_kugel", "extrudieren",
              "loch", "block3d", "aufloesen3d", "wuerfel", "persp", "einpassen3d", "iso3d", "hoehe3d"):
        check("tb.wz." + n in T, "tooltip " + n)
    for f in G.WUERFEL_FLAECHEN:
        check("d3.ansicht." + f in T, f)
    check("menu.3d.loch" in T and "d3.neu.loch" in T, "loch")
print(f"test_3d - {ok} Checks bestanden")
