import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.electrical.logic as L
import katiecad.ui.app as A
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1
VP = core.Verbindungspunkt
txt = lambda k: [t.inhalt for t in k.aufgeloest() if isinstance(t, core.Text)]

# three vertical wires (between pins) cross the cable
el = []
for x in (10, 20, 30):
    el += [VP(x, 0, wert="o"), VP(x, 40, wert="u")]
kb = core.Kabel(0, 20, {"CAB": "W1", "TYP": "3x1,5"}, laenge=40)
el.append(kb)
L.leitungen_automatisch(el); L.kabel_kreuzungen(el)
check(kb.kreuzungen == [10.0, 20.0, 30.0], f"drei Kreuzungen: {kb.kreuzungen}")
t = txt(kb)
check(t[:2] == ["W1", "3x1,5"] and t[-3:] == ["L1", "L2", "L3"], f"Maske und Adern L1-L3: {t}")
check(sum(isinstance(k, core.Linie) for k in kb.aufgeloest()) == 4, "Linie + 3 Striche")
# Wire disappears -> stroke disappears
el = [e for e in el if not (isinstance(e, VP) and e.x == 20)]
L.leitungen_automatisch(el); L.kabel_kreuzungen(el)
check(kb.kreuzungen == [10.0, 30.0] and txt(kb)[-2:] == ["L1", "L2"], "weniger Kreuzungen")
# Wire outside the cable length does not count; ends on the line: no crossing
kb.laenge = 15; L.kabel_kreuzungen(el)
check(kb.kreuzungen == [10.0], "nur innerhalb der Laenge")
kb.laenge = 40
el2 = [VP(50, 0), VP(50, 20), kb]; L.leitungen_automatisch(el2); L.kabel_kreuzungen(el2)
check(50.0 not in kb.kreuzungen, "Leitung endet auf dem Kabel = keine Kreuzung")
# Designations changeable
kb.kreuzungen = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
kb.laenge = 70
names = [n for _k, n in kb.adern_liste()]
check(names == ["L1", "L2", "L3", "N", "PE", "6"], f"Standardnamen: {names}")
kb.adern[kb.ader_schluessel(20.0)] = "L2*"
check(kb.adern_liste()[1][1] == "L2*", "Ader umbenennen")
# Placeholder / empty
leer = core.Kabel(0, 0)
check(txt(leer)[:2] == ["<CAB>", "<TYP>"], "Platzhalter am Bildschirm")
check(txt(core.Kabel(0, 0, platzhalter=False)) == [], "ohne Platzhalter leer")
# Save/load
a = A.CadApp.__new__(A.CadApp)
d = json.loads(json.dumps(kb.to_dict()))
k2 = a._dict_zu_element(d)
check(isinstance(k2, core.Kabel) and k2.laenge == 70 and k2.adern == kb.adern and "kreuzungen" not in d, "Speichern/Laden")
# Grips
kb.griff_bewegen("e", 90, 20)
check(kb.laenge == 90 and kb.griffe()[1][1] == kb.x + 90, "Ende per Griff verlaengern")
kb.griff_bewegen("e", -5, 20)
check(kb.laenge >= 1.0, "Mindestlaenge")
check(core.Kabel in core.ZUSAMMENGESETZT, "zusammengesetztes Element")
# REF via CAB (same sheet + other sheets)
k_a = core.Kabel(0, 0, {"CAB": "W7"}); k_b = core.Kabel(0, 100, {"CAB": "W7"}); k_c = core.Kabel(0, 50, {"CAB": "W9"})
eig = L.geraete([k_a, k_b, k_c], 1)
L.geraete_referenzen(eig, 1, {2: [("W7", "kabel", "", "3/B")]})
check(k_a.refs == [(1, ""), (2, "3/B")] and k_c.refs == [], f"REF aus gleichem CAB: {k_a.refs}")
check(any("Blatt 2/3/B" in x for x in txt(k_a)), "REF-Text mit Koordinate")
d_blatt = {"elemente": [k_a.to_dict()]}
check(L.geraete_aus_blattdaten(d_blatt) == [("W7", "kabel", "", "")], "Kabel aus Blattdaten")
# Duplicate, slightly offset wires (e.g. old hand wire) yield only ONE core
dup = [VP(10, 0), VP(10, 40), core.Leitung(10.02, 0, 10.02, 40), core.Kabel(0, 20, {"CAB": "W1"}, laenge=40)]
L.leitungen_automatisch(dup); L.kabel_kreuzungen(dup)
check(len([e for e in dup if isinstance(e, core.Leitung)]) == 1, "Doppelleitung entfernt")
dup2 = [e for e in dup]; dup2.append(core.Leitung(10.3, 0, 10.3, 40, auto=False)); dup2.append(core.Leitung(10.34, 0, 10.34, 40))
L.kabel_kreuzungen(dup2)
check(len(dup2[-1:]) and dup2[3].kreuzungen == [10.0], f"nahe Kreuzungen = eine Ader: {dup2[3].kreuzungen}")
# REF only with references
check("<REF>" not in txt(core.Kabel(0, 0)) and txt(core.Kabel(0, 0))[:2] == ["<CAB>", "<TYP>"], "REF ohne Verweise nicht sichtbar")
print(f"{ok} Checks bestanden")
