import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.electrical.logic as L
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

VP = core.Verbindungspunkt
def wires(el): return sorted((round(l.x1), round(l.y1), round(l.x2), round(l.y2)) for l in el if isinstance(l, core.Leitung))

# two free pins vertically -> wire is created
a, b = VP(10, 10, wert="1"), VP(10, 50, wert="2")
el = [a, b]
n, w, _ = L.leitungen_automatisch(el)
check(wires(el) == [(10, 10, 10, 50)] and n == 1 and all(l.auto for l in el if isinstance(l, core.Leitung)), "senkrechte Leitung entsteht")
l0 = [e for e in el if isinstance(e, core.Leitung)][0]
L.leitungen_automatisch(el)
check([e for e in el if isinstance(e, core.Leitung)] == [l0], "stabil: gleiches Objekt bleibt")
# horizontal
c, d = VP(0, 0), VP(30, 0)
el2 = [c, d]; L.leitungen_automatisch(el2)
check(wires(el2) == [(0, 0, 30, 0)], "waagerechte Leitung")
# offset -> disappears
b.x = 13
L.leitungen_automatisch(el)
check(wires(el) == [], "Versetzen entfernt die Leitung")
b.x = 10
L.leitungen_automatisch(el)
check(wires(el) == [(10, 10, 10, 50)], "zurueck -> entsteht wieder")
# Pin in between -> wire splits
m = VP(10, 30, wert="M"); el.append(m)
L.leitungen_automatisch(el)
check(wires(el) == [(10, 10, 10, 30), (10, 30, 10, 50)], "Pin dazwischen teilt die Leitung")
el.remove(m); L.leitungen_automatisch(el)
check(wires(el) == [(10, 10, 10, 50)], "Pin weg -> wieder eine Leitung")
# Terminal in between: wire ends at the terminal top/bottom, none inside
kl = core.Klemme(10, 30, {"NUM": "1"})
el.append(kl); L.leitungen_automatisch(el)
ob, un = kl.anschluss_oben(), kl.anschluss_unten()
ws = wires(el)
check(ws == sorted([(10, 10, 10, round(un[1])), (10, round(ob[1]), 10, 50)]) and len(ws) == 2, f"Klemme unterbricht: {ws}")
el.remove(kl); L.leitungen_automatisch(el)
check(wires(el) == [(10, 10, 10, 50)], "Klemme weg")
# Device (block) with pins top/bottom: no wire through the device
sym = [core.Rechteck(-5, -5, 5, 5), VP(0, 5, wert="A"), VP(0, -5, wert="B")]
dev = core.BlockReferenz(10, 30, "K", sym)
el.append(dev); L.leitungen_automatisch(el)
check(wires(el) == [(10, 10, 10, 25), (10, 35, 10, 50)], f"Geraet unterbricht: {wires(el)}")
# Devices side by side with pins in the same row: no cross wire
d1 = core.BlockReferenz(100, 100, "K", sym); d2 = core.BlockReferenz(110, 100, "K", sym)
e3 = [d1, d2]; L.leitungen_automatisch(e3)
check(wires(e3) == [], f"Geraete-Pins oben/unten verbinden sich nicht seitlich: {wires(e3)}")
e3.append(VP(100, 130)); L.leitungen_automatisch(e3)
check(wires(e3) == [(100, 105, 100, 130)], "Pin oberhalb -> an obere Geraetepins")
# Junction: only in arm direction
v = core.Verbindung(50, 50, 2, 0, True)     # Arms east + north
p_ost = VP(80, 50); p_west = VP(20, 50)
e4 = [v, p_ost, p_west]; L.leitungen_automatisch(e4)
check(wires(e4) == [(53, 50, 80, 50)] or wires(e4) == [(52, 50, 80, 50)], f"nur Arm Ost: {wires(e4)}")
# Cross reference: connection on the side facing away from the text
q = core.Querverweis(0, 100, "L1", "abgehend", 90)       # Tip up, text above
pq = VP(0, 80)
e5 = [q, pq]; L.leitungen_automatisch(e5)
check(wires(e5) == [(0, 80, 0, 100)], "Querverweis abgehend: Anschluss an der Basis")
q2 = core.Querverweis(0, 100, "L1", "abgehend", 270)     # Tip down
e6 = [q2, VP(0, 80)]; L.leitungen_automatisch(e6)
check(wires(e6) == [], "falsche Seite -> keine Leitung")
# manual legacy wire becomes automatic
man = core.Leitung(10, 10, 10, 50)
e7 = [VP(10, 10), VP(10, 50), man]
L.leitungen_automatisch(e7)
check(wires(e7) == [(10, 10, 10, 50)] and man.auto and e7.count(man) == 1, "Altleitung wird uebernommen")
man2 = core.Leitung(0, 0, 7, 9)                          # slanted, without connection: stays
e8 = [man2]; L.leitungen_automatisch(e8)
check(e8 == [man2], "manuelle Sonderleitung bleibt")
# Save/load keeps auto
import json
dd = json.loads(json.dumps(l0.to_dict())); dd.pop("typ")
check(core.Leitung(**dd).auto is True, "auto-Flag wird gespeichert")
# ---------- Pin directions ----------
pa, pb = VP(0, 0, richtungen=[90]), VP(0, 40, richtungen=[270])
e9 = [pa, pb]; L.leitungen_automatisch(e9)
check(wires(e9) == [(0, 0, 0, 40)], "Nord/Sued aktiv -> Leitung")
pb.richtungen = [0, 90, 180]                      # South deactivated
L.leitungen_automatisch(e9)
check(wires(e9) == [], "Sued deaktiviert -> keine Leitung")
pb.richtungen = [270]; pa.richtungen = []         # Pin without connection
L.leitungen_automatisch(e9)
check(wires(e9) == [], "Pin ganz ohne Anschluss")
ph = [VP(0, 0, richtungen=[0]), VP(30, 0, richtungen=[180]), VP(0, 30, richtungen=[0])]
L.leitungen_automatisch(ph)
check(wires(ph) == [(0, 0, 30, 0)], "nur Ost/West waagerecht, Nord nicht aktiv")
pr = VP(0, 0, richtungen=[90]); pr.drehen(0, 0, 90)
check(pr.richtungen == [0], f"Drehen dreht die Anschlussrichtungen: {pr.richtungen}")
blk = core.BlockReferenz(0, 0, "R", [VP(0, 5, wert="x", richtungen=[90])], winkel=90.0)
check([k for k in blk.aufgeloest() if isinstance(k, VP)][0].richtungen == [180], "Block-Drehung dreht Pin-Richtungen")
pn = VP(5, 5)
check(pn.richtungen is None and VP(**{k: v for k, v in pn.to_dict().items() if k != "typ"}).richtungen is None, "Altwert None bleibt erhalten")
print(f"{ok} Checks bestanden")
