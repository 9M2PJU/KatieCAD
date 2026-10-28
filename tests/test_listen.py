import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.electrical.logic as L
from katiecad.reports import netz as N, daten as D, seiten as S, daten_listen as DL
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

VP = core.Verbindungspunkt
def geraet(x, y, ind, typ="", pin_o="1", pin_u="2", rolle="haupt"):
    sym = [core.Rechteck(-5, -5, 5, 5), VP(0, 5, wert=pin_o, tag="P1"), VP(0, -5, wert=pin_u, tag="P2"),
           core.ElektroMaske(8, 0, rolle=rolle)]
    b = core.BlockReferenz(x, y, "Sym", sym)
    b.attribute.update({"IND": ind, "TYP": typ, "PER": ""})
    return b

feld = core.Koordinatenfeld(0, 0, 287, 164, 6, 4)
# sheet 1: connector X5 (pins 1,2) wired to K1 (A1,A2); K1 also connected to potential +24V via cross reference
x5 = geraet(40, 100, "X5", "Stecker 2-pol", "1", "2")
k1 = geraet(40, 40, "K1", "3RT2015", "A1", "A2")
q1 = core.Querverweis(40, 140, "+24V", "ankommend", 270)
w1 = core.Leitung(40, 95, 40, 45)         # X5 pin2 -> K1 pin A1
el1 = [feld, x5, k1, q1, w1]
L.leitungen_automatisch(el1)
# sheet 2: second K1 contact with cross reference + 24V and outgoing reference
k9 = geraet(40, 40, "K9", "3RT2015", "A1", "A2")
q2 = core.Querverweis(40, 140, "+24V", "ankommend", 270)
q3 = core.Querverweis(100, 140, "S1", "abgehend", 90)
el2 = [core.Koordinatenfeld(0, 0, 287, 164, 6, 4), k9, q2, q3]
bl = [(0, el1), (1, el2)]
nr = lambda i: i + 1
n = N.Netz.aufbauen(bl)

vl = DL.verbindungsliste(n, bl, nr, {0: "Verteiler", 1: ""})
check(any({"X5:2", "K1:A1"} == {z["von"], z["nach"]} for z in vl), f"Verbindungsliste: {[(z['von'], z['nach']) for z in vl]}")
check(all(z["pos"] == str(i + 1) for i, z in enumerate(vl)), "Verbindungsliste: Nummerierung")

kat = [{"typ": "3rt2015", "hersteller": "Siemens", "bestellnr": "3RT2015-1BB41", "beschreibung": "Schütz"}]
sl = DL.stueckliste(bl, nr, n, kat)
z = [r for r in sl if r["typ"] == "3RT2015"][0]
check(z["anzahl"] == "2" and z["hersteller"] == "Siemens" and z["bestellnr"] == "3RT2015-1BB41" and z["kennzeichen"] == ["K1", "K9"], f"Stueckliste: {z}")
check(any(r["typ"] == "Stecker 2-pol" and r["hersteller"] == "" for r in sl), "Stueckliste: Typ ohne Katalogeintrag")
check(DL.typen_der_projekte(bl, nr, n) == ["3RT2015", "Stecker 2-pol"], f"Typen: {DL.typen_der_projekte(bl, nr, n)}")

qv = DL.querverweisliste(n, bl, nr)
check([r["name"] for r in qv] == ["+24V", "S1"], f"Querverweisliste: {qv}")
r24 = qv[0]
check(r24["anzahl"] == "2" and len(r24["ankommend"]) == 2 and r24["abgehend"] == [], "Querverweisliste: +24V zweimal ankommend")

pot = DL.potenzialuebersicht(n, bl, nr)
check(any(r["potenzial"] == "+24V" for r in pot), f"Potenziale: {pot}")

sts = DL.steckeruebersicht(n, bl, nr, {0: "Verteiler"})
check(all(r["stecker"] == "X5" for r in sts) and [r["pin"] for r in sts] == ["1", "2"], f"Stecker: {sts}")
check(sts[1]["ziele"] == ["K1:A1"] and sts[0]["einbauort"] == "Verteiler", f"Stecker Ziele: {sts[1]}")
check(DL.ist_stecker("-X5") and DL.ist_stecker("+A1-X5") and not DL.ist_stecker("K1") and DL.ist_stecker("P1", "Rundstecker"), "ist_stecker")

et = DL.etikettenliste(bl, nr, n, None)
check({r["etikett"] for r in et} >= {"K1", "K9", "X5"}, f"Etiketten: {[r['etikett'] for r in et]}")

rv = DL.revisionsuebersicht({"rev": [{"stand": "A", "aenderung": "Erstausgabe", "name": "KC", "datum": "01.01.26"}, {}, {"stand": "", "aenderung": ""}]})
check(len(rv) == 1 and rv[0]["aenderung"] == "Erstausgabe", "Revisionen: leere Zeilen entfallen")
check(DL.revisionsuebersicht(None) == [], "Revisionen: keine Daten")

# whole pipeline through the report generator
vorne, hinten = S.berichte_erzeugen([S.BlattInfo("B1", el1, "", "Verteiler"), S.BlattInfo("B2", el2)], "Demo",
                                    {"rev": [{"stand": "A", "aenderung": "x", "name": "y", "datum": "z"}]},
                                    set(S.TYPEN), None, "de", katalog=kat)
typen = [p.typ for p in hinten]
for t in S.LISTEN:
    check(t in typen, "Bericht erzeugt: " + t)
tab = S.tabellen_fuer_export([(0, el1), (1, el2)], nr, katalog=kat, projektdaten={"rev": [{"stand": "A"}]})
check(set(tab) == set(S.LISTEN) and len(tab["stueckliste"][1]) >= 2 and len(tab["revisionen"][1]) == 1, "Export-Tabellen vollstaendig")
check(any(s.key == "hersteller" for s in tab["stueckliste"][0]), "Stueckliste hat Herstellerspalte")


# ---- automatische Nummerierung
import katiecad.electrical.nummerierung as NU
check(NU.zerlegen("-K12") == ("-K", 12) and NU.zerlegen("-K") == ("-K", None) and NU.zerlegen("K?") == ("K", None)
      and NU.zerlegen("") == (None, None) and NU.zerlegen("IND") == (None, None), "Nummerierung: zerlegen")
a1 = geraet(10, 10, "-K", "3RT"); a2 = geraet(30, 10, "-K5", "3RT"); a3 = geraet(50, 10, "-K?", "3RT")
a4 = geraet(10, 50, "-Q", "LS"); a5 = geraet(70, 10, "-K", "HILF", rolle="hilfs"); a6 = geraet(90, 10, "", "x")
dict_blatt = [{"typ": "block", "x": 10, "y": 10, "attribute": {"IND": "-K"},
               "elemente": [{"typ": "maske", "rolle": "haupt"}]},
              {"typ": "maske", "x": 0, "y": 0, "rolle": "haupt", "werte": {"IND": "-F7"}}]
aend, ohne = NU.plan([(0, [a1, a2, a3, a4, a5, a6]), (1, dict_blatt)])
neu = {id(h): n for h, k, a, n, b in aend}
check(neu[id(a1.attribute)] == "-K6" and neu[id(a3.attribute)] == "-K7", f"Nummerierung: Reihenfolge links->rechts: {[(a, n) for h, k, a, n, b in aend]}")
check(neu[id(dict_blatt[0]["attribute"])] == "-K8", "Nummerierung: JSON-Blatt faehrt fort")
check(neu[id(a4.attribute)] == "-Q1", "Nummerierung: neues Praefix beginnt bei 1")
check(id(a5.attribute) not in neu and id(a2.attribute) not in neu, "Nummerierung: Hilfsteil und vorhandene Nummer bleiben")
check(ohne == 1, "Nummerierung: Geraet ohne Kennzeichen gezaehlt")
aend, _o = NU.plan([(0, [a1, a2, a3]), (1, dict_blatt)], {0})
check(all(b == 0 for *_x, b in aend) and len(aend) == 2, "Nummerierung: nur Zielblatt")
NU.anwenden(aend)
check(a1.attribute["IND"] == "-K6" and dict_blatt[0]["attribute"]["IND"] == "-K", "Nummerierung: anwenden")
b = geraet(0, 0, "-K", "x"); b2 = geraet(0, 30, "-K", "x")
aend, _o = NU.plan([(0, [b, b2])])
check([n for _h, _k, _a, n, _b in aend] == ["-K1", "-K2"] and aend[0][0] is b2.attribute, "Nummerierung: oben vor unten")

de = set(katiecad_i18n.TEXTE["de"]); en = set(katiecad_i18n.TEXTE["en"])
check(de == en, "i18n Paritaet %s" % (de ^ en))
for t in S.TYPEN:
    check("rep." + t in de, "i18n rep." + t)
print(ok, "Checks bestanden")
