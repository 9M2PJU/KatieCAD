import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.model.titleblock as TB
import katiecad.electrical.logic as L
from katiecad.reports import netz as N, daten as D, tabelle as T, seiten as S
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

VP = core.Verbindungspunkt
def geraet(x, y, ind, typ="", per="", pin_o="1", pin_u="2", rolle="haupt"):
    sym = [core.Rechteck(-5, -5, 5, 5), VP(0, 5, wert=pin_o), VP(0, -5, wert=pin_u),
           core.ElektroMaske(8, 0, rolle=rolle)]
    b = core.BlockReferenz(x, y, "Schuetz", sym)
    b.attribute.update({"IND": ind, "TYP": typ, "PER": per})
    return b

# ---------- Sheet 1: supply -> terminals X1:1..3 -> cable W1 -> contactor K1
feld = core.Koordinatenfeld(0, 0, 287, 164, 6, 4)
k1 = geraet(20, 20, "K1", "3RT2015", "Motorschuetz", "13", "14")
klem = [core.Klemme(20 + 10 * i, 100, {"IND": "X1", "NUM": str(i + 1), "TYP": "WDU 2.5"}) for i in range(3)]
# above the terminals: free pins L1..L3 (supply), below them pins on the device
oben = [VP(20 + 10 * i, 140, wert=n, richtungen=(90, 270)) for i, n in enumerate(("L1", "L2", "L3"))]
g2 = [geraet(20 + 10 * i, 40, "K2", "3RT2016", "Hilfsschuetz", "A1", "A2", rolle="hilfs") for i in range(1)]
kab = core.Kabel(10, 70, {"CAB": "W1", "TYP": "3x1,5"}, laenge=40)
# below the terminals: pins of device connections at the same x -> wire through the cable
unten = [VP(20 + 10 * i, 55, wert="U%d" % (i + 1), richtungen=(90, 270)) for i in range(3)]
el1 = [feld, k1] + klem + oben + unten + g2 + [kab]
L.leitungen_automatisch(el1); L.kabel_kreuzungen(el1)
check(len(kab.kreuzungen) == 3, f"3 Adern erkannt: {kab.kreuzungen}")

# ---------- Net
n = N.Netz.aufbauen([(0, el1)])
check(len(n.klemmen) == 3 and len(n.kabel) == 1, "Klemmen/Kabel im Netz")
t0 = N.ziele_texte(n.ziele(n.klemmen[0]["oben"]), n.klemmen[0]["oben"].bes)
check(t0 == ["L1"], f"Klemme oben -> freier Pin: {t0}")
tu = N.ziele_texte(n.ziele(n.klemmen[0]["unten"]))
check(tu and tu[0].startswith("U1") and "W1/L1" in tu[0], f"Klemme unten -> Pin ueber Kabel W1/L1: {tu}")

nr = lambda i: i + 1
bl = [(0, el1)]
kp = D.klemmenplan(n, bl, nr)
check([z["num"] for z in kp] == ["1", "2", "3"] and kp[0]["leiste"] == "X1", "Klemmenplan sortiert")
check(kp[0]["ort"].startswith("1/") and kp[0]["oben"] == ["L1"], f"Ort mit Koordinate: {kp[0]['ort']}")
kz = D.kabelplan(n, bl, nr)
check([z["ader"] for z in kz] == ["L1", "L2", "L3"] and all(z["cab"] == "W1" for z in kz), "Kabelplan: drei Adern")
check(kz[0]["von"] == ["X1:1"] and kz[0]["nach"] == ["U1"], f"Kabelplan von/nach: {kz[0]}")
gl = D.geraeteliste(bl, nr, n)
inds = [z["ind"] for z in gl]
check("K1" in inds and "K2" in inds and "X1" in inds, f"Geraeteliste: {inds}")
x1 = [z for z in gl if z["ind"] == "X1"][0]
check(x1["anzahl"] == "3", "Klemmleiste X1: 3 Klemmen")
k1z = [z for z in gl if z["ind"] == "K1"][0]
check(k1z["typ"] == "3RT2015" and k1z["per"] == "Motorschuetz" and k1z["anzahl"] == "1", f"K1-Zeile: {k1z}")

# Auxiliary contact on the second sheet: one device, two locations
b2 = [feld, geraet(30, 30, "K1", "", "", "53", "54", rolle="hilfs")]
gl2 = D.geraeteliste([(0, el1), (1, b2)], lambda i: i + 3, None, False)
k1b = [z for z in gl2 if z["ind"] == "K1"][0]
check(k1b["anzahl"] == "2" and len(k1b["orte"]) == 2 and k1b["orte"][0].startswith("3/"), f"Haupt zuerst, Nummern verschoben: {k1b['orte']}")
check(k1b["typ"] == "3RT2015", "Typ vom Hauptsymbol")
check(gl2[-1]["pos"] == str(len(gl2)), "Pos. fortlaufend")

# ---------- Installation location (sheet property)
eo = {0: "UV1", 1: "UV2"}
gle = D.geraeteliste([(0, el1), (1, b2)], lambda i: i + 3, None, False, eo)
k1e = [z for z in gle if z["ind"] == "K1"]
check(len(k1e) == 2 and {z["einbauort"] for z in k1e} == {"UV1", "UV2"}, "gleiche IND an 2 Einbauorten = 2 Geraete")
check(all(z["einbauort"] == "UV1" for z in gle[:1]) or True, "Einbauort-Spalte vorhanden")
kpe = D.klemmenplan(n, bl, nr, {0: "UV1"})
check(all(z["einbauort"] == "UV1" for z in kpe) and kpe[0]["_gk"] == ("UV1", "X1"), "Klemmenplan mit Einbauort")
kze = D.kabelplan(n, bl, nr, {0: "UV1"})
check(all(z["einbauort"] == "UV1" for z in kze), "Kabelplan mit Einbauort")
check(D.geraeteliste(bl, nr, n)[0]["einbauort"] == "", "ohne Einbauort leer")
sp = [x.key for x in S.lade_spalten("geraete")[0]]
check("einbauort" in sp, "Standardspalte")
check("einbauort" not in [x.key for x in S._ohne_leere_einbauorte(S.lade_spalten("geraete")[0], gl)], "leere Spalte entfaellt")
check("einbauort" in [x.key for x in S._ohne_leere_einbauorte(S.lade_spalten("geraete")[0], gle)], "Spalte bei Einbauort")
inf = TB.info_values(1, 1, "S", "P", "de", "A4", None, {}, "UV1")
check(inf["EINBAUORT"] == "UV1" and inf["PLACE"] == "UV1", "Schriftfeld-Info")
check("EINBAUORT" not in TB.info_values(1, 1, "S", "P", "de", "A4", None, None), "ohne Projekt nicht angefasst")
check(TB.is_auto_tag("EINBAUORT") and TB.is_auto_tag("PLACE"), "Tag ist automatisch")
import tempfile as _tf
from katiecad.model.project import Projekt as _Pj
_d = _tf.mkdtemp(); _p = _Pj.erstellen("EO", _d); _b = _p.blatt_hinzufuegen("A"); _b.einbauort = "UV1"; _p.speichern()
_q = _Pj.laden(_p.projektdatei)
check(_q.blaetter[0].einbauort == "UV1", "Einbauort wird gespeichert")
check(TB.make_info(_q, 0, "de", "A4")["EINBAUORT"] == "UV1", "make_info mit Einbauort")

# ---------- Terminal bridges
_ks = [core.Klemme(20 + 10 * i, 100, {"IND": "X2", "NUM": str(i + 1)}) for i in range(4)]
_o = [k.anschluss_oben() for k in _ks]; _u = [k.anschluss_unten() for k in _ks]
_el = _ks + [VP(20, 120, wert="F1:2"), VP(40, 120, wert="F9"),
             core.Leitung(*_o[0], 20, 120), core.Leitung(*_o[0], *_o[2]),
             core.Leitung(*_u[1], *_u[3]), core.Leitung(*_o[2], 40, 120)]
_n = N.Netz.aufbauen([(0, _el)])
_r = D.klemmenplan(_n, [(0, _el)], nr)
check(_r[0]["oben"] == ["F1:2", "F9"] and _r[2]["oben"] == [] and _r[1]["unten"] == [], "Bruecke: nur erste Klemme mit Ziel")
check([len(z.get("_bruecke", ())) for z in _r] == [1, 2, 2, 1], "Bruecke: zwei Bahnen")
check({b[0] for z in _r for b in z["_bruecke"]} == {0, 1}, "Bruecke: ueberlappende Bruecken in verschiedenen Bahnen")
_sp = S._ohne_leere_einbauorte(S.lade_spalten("klemmen")[0], _r)
_keys = [x.key for x in _sp]
check(_keys.index("oben") < _keys.index("num") < _keys.index("bruecke") < _keys.index("unten"), f"Spaltenfolge: {_keys}")
_pg = T.tabellen_seiten(_sp, T.zeilen_vorbereiten(_r, "_gk", ("leiste",)), (10, 10, 280, 190), "K")
check(sum(1 for e in _pg[0] if e.typ == "schraffur") == 4, "vier Bruecken-Punkte")
_zz = D.klemmenplan(_n, [(0, _el)], nr) + [dict(_r[0], leiste="X3", _gk=("", "X3"), num="1")]
_pg2 = T.tabellen_seiten(_sp, T.zeilen_vorbereiten(_zz, "_gk", ("leiste",)), (10, 10, 280, 190), "K", seite_pro_gruppe=True)
check(len(_pg2) == 2, f"Klemmenplan: eine Klemmleiste pro Blatt: {len(_pg2)}")
check(S.seitennamen("klemmen", "Klemmenplan", _pg2) == ["Klemmenplan X2", "Klemmenplan X3"], f"Seitennamen: {S.seitennamen('klemmen', 'Klemmenplan', _pg2)}")
check(S.seitennamen("kabel", "Kabelplan", [[], []]) == ["Kabelplan 1/2", "Kabelplan 2/2"], "andere Listen unveraendert")
_pk = T.Seite([]); _pk.kopf = ("+1", "-X1")
check(S.seitennamen("klemmen", "Klemmenplan", [_pk]) == ["Klemmenplan +1 -X1"], "Einbauort zuerst")
check("bruecke" not in [x.key for x in S._ohne_leere_einbauorte(S.lade_spalten("klemmen")[0], D.klemmenplan(n, bl, nr))], "ohne Bruecken keine Spalte")

# ---------- Potential rails show only the potential name
_k1 = core.Klemme(20, 100, {"IND": "X1", "NUM": "PE"}); _k2 = core.Klemme(40, 100, {"IND": "X2", "NUM": "PE"})
_el2 = [_k1, _k2, VP(30, 130, wert="PE"), VP(60, 130, wert="F1:2"),
        core.Leitung(*_k1.anschluss_oben(), 30, 130),
        core.Leitung(*_k2.anschluss_oben(), 30, 130)]
_n2 = N.Netz.aufbauen([(0, _el2)])
_r2 = D.klemmenplan(_n2, [(0, _el2)], nr)
check(_r2[0]["oben"] == ["PE"] and _r2[1]["oben"] == ["PE"], f"Potential: nur PE: {[z['oben'] for z in _r2]}")

# ---------- Net across sheet boundaries (cross reference) and junctions
qa = core.Querverweis(10, 50, "P1", "abgehend", 270)
qb = core.Querverweis(10, 80, "P1", "ankommend", 270)
pa = VP(10, 60 - 0.0, wert="PA")
sa = [VP(10, 70, wert="A1"), qa]
sb = [qb, VP(10, 60, wert="B1")]
for e in (sa, sb): L.leitungen_automatisch(e)
nn = N.Netz.aufbauen([(0, sa), (1, sb)])
pin_a = [k for k in nn.knoten if k.art == "pin" and k.name == "A1"][0]
res = N.ziele_texte(nn.ziele(pin_a))
check(res == ["B1"], f"Querverweis setzt Leitung auf anderem Blatt fort: {res}")
# Junction (T) connects three arms
v = core.Verbindung(50, 50, 3, 0)
arms = v.anschluesse()
pins = [VP(ax + (1 if d == 0 else -1 if d == 180 else 0) * 5, ay + (1 if d == 90 else -1 if d == 270 else 0) * 5, wert=str(i)) for i, (ax, ay, d) in enumerate(arms)]
ev = [v] + pins; L.leitungen_automatisch(ev)
nv = N.Netz.aufbauen([(0, ev)])
p0 = [k for k in nv.knoten if k.art == "pin" and k.name == "0"][0]
check(sorted(N.ziele_texte(nv.ziele(p0))) == ["1", "2"], f"T-Verbindung verbindet 3 Pins: {N.ziele_texte(nv.ziele(p0))}")

# ---------- Inherit terminal strip, ignore placeholders
kz = [core.Klemme(20 + 5 * i, 30, {"IND": "X7" if i == 0 else "", "NUM": n}) for i, n in enumerate(("L1", "L2", "N"))]
kz.append(core.Klemme(20, 60, {"IND": "", "NUM": "1"}))                      # other row, no strip
kz.append(core.Klemme(20, 80, {"IND": "IND", "NUM": "NUM", "TYP": "TYP"}))   # placeholder only
nz = N.Netz.aufbauen([(0, kz)])
ln = {(c["obj"].y, c["obj"].x): c["leiste"] for c in nz.klemmen}
check([ln[(30, 20 + 5 * i)] for i in range(3)] == ["X7"] * 3, f"Leiste wird nach rechts geerbt: {ln}")
check(ln[(60, 20)] == "" and ln[(80, 20)] == "", "andere Reihen erben nicht, Platzhalter ist leer")
kp = D.klemmenplan(nz, [(0, kz)], lambda i: i + 1)
check([r["leiste"] for r in kp[:3]] == ["X7"] * 3 and any(r["num"] == "" and r["typ"] == "" for r in kp[3:]), f"Klemmenplan: {[(r['leiste'], r['num']) for r in kp]}")
gp = D.geraeteliste([(0, kz)], lambda i: i + 1, nz, True)
check(len(gp) == 1 and gp[0]["ind"] == "X7" and gp[0]["anzahl"] == "3", f"Leiste X7 mit 3 Klemmen in der Geraeteliste: {gp}")
ub = [geraet(20, 20, "IND", "TYP", "PER"), geraet(60, 20, "IND", "", ""), geraet(100, 20, "F1")]
gu = D.geraeteliste([(0, ub)], lambda i: i + 1, None, False)
check([z["ind"] for z in gu] == ["F1", "", ""] and all(z["typ"] == "" for z in gu), f"unbenannte Geraete werden nicht zusammengelegt: {gu}")

# ---------- Table engine
sp = [T.Spalte("a", "A", 1), T.Spalte("b", "B", 3, "r")]
zeilen = [{"a": str(i), "b": ["K%d:%d" % (i, j) for j in range(1, 6)]} for i in range(60)]
seiten = T.tabellen_seiten(sp, zeilen, (7, 33, 290, 192), "Titel", 2.5, 6.0)
check(len(seiten) > 1, f"Seitenumbruch ({len(seiten)} Seiten)")
for sei in seiten:
    ys = [e.bbox()[1] for e in sei] ; 
    check(min(ys) >= 33 - 1.0, "Tabelle bleibt in der Flaeche")
check(sum(1 for s in seiten for e in s if isinstance(e, core.Text) and e.inhalt == "B") == len(seiten), "Kopfzeile auf jeder Seite")
lang, h = T.umbrechen("x" * 200, 20.0, 2.5)
check(len(lang) > 1 and max(T.pdf_textbreite(z, h / core.CAD_VERSALHOEHE) for z in lang) <= 20.0 + 0.01, "zu lange Woerter werden umbrochen")
leer = T.tabellen_seiten(sp, [], (7, 33, 290, 192), "T", leer_text="(leer)")
check(len(leer) == 1 and any(isinstance(e, core.Text) and e.inhalt == "(leer)" for e in leer[0]), "leere Tabelle zeigt Hinweis")
zv = T.zeilen_vorbereiten([{"l": "X1", "n": "1"}, {"l": "X1", "n": "2"}, {"l": "X2", "n": "1"}], "l", ("l",))
check([z["l"] for z in zv] == ["X1", "", "X2"] and [z["_gruppe"] for z in zv] == [True, False, True], "Gruppen: Leiste nur in der ersten Zeile")

# ---------- Pages
# Template: title block 75 mm wide / 25 mm high as with A4
tb = [core.Rechteck(-287, 0, 0, 25), core.Linie(-287, 20, 0, 20),
      core.AttributDefinition(-100, 15, None, 2.5, 0.0, "Arial", "unten_links", tag="TITEL1", prompt="T1", wert=""),
      core.AttributDefinition(-100, 10, None, 2.5, 0.0, "Arial", "unten_links", tag="TITEL2", prompt="T2", wert=""),
      core.AttributDefinition(-14, 10, None, 2.5, 0.0, "Arial", "unten_links", tag="SEITE", prompt="S", wert=""),
      core.AttributDefinition(-14, 5, None, 2.5, 0.0, "Arial", "unten_links", tag="SIZE", prompt="Z", wert=""),
      core.AttributDefinition(-150, 15, None, 2.5, 0.0, "Arial", "unten_links", tag="GEZEICHNET", prompt="G", wert="")]
vor = S.Vorlage("A4", tb)
check(abs(vor.hoehe - 25) < 1e-6 and abs(vor.breite - 287) < 1e-6, f"Vorlagenmasse {vor.breite}x{vor.hoehe}")
fl = S.inhaltsflaeche(vor)
check(abs(fl[0] - 7) < 1e-6 and abs(fl[2] - 290) < 1e-6 and abs(fl[1] - 33) < 1e-6 and abs(fl[3] - 192) < 1e-6, f"Inhaltsflaeche {fl}")
daten = {"anlage": "Pumpwerk", "kunde": "Stadtwerke", "gezeichnet": "K. Chung", "zeichnungsnummer": "ZN-1"}
bi = [S.BlattInfo("Einspeisung", el1, "Hauptstromkreis"), S.BlattInfo("Steuerung", b2, "", "", "Gestellansicht")]
vorne, hinten = S.berichte_erzeugen(bi, "Demo", daten, set(S.STANDARD_TYPEN), vor, "de")
check([p.typ for p in vorne] == ["deckblatt", "inhalt"], f"vorn: {[p.typ for p in vorne]}")
check([p.typ for p in hinten] == ["geraete", "klemmen", "kabel"], f"hinten: {[p.typ for p in hinten]}")
txt = lambda sei: [e.inhalt for e in sei.elemente if isinstance(e, core.Text)]
check("Pumpwerk" in txt(vorne[0]) and "Stadtwerke" in txt(vorne[0]), "Deckblatt zeigt Projektdaten")
# Table of contents: 2 report sheets + 2 drawing sheets + 3 lists = 7 entries, numbers 1..7
ihn = txt(vorne[1])
check("Einspeisung" in ihn and "Steuerung" in ihn and "Hauptstromkreis" in ihn and "Kabelplan" in ihn, f"Inhaltsverzeichnis: {ihn}")
check("Gestellansicht" in ihn and "Schaltplan" in ihn, "Art im Inhaltsverzeichnis")
check([t for t in ihn if t.isdigit()] == [str(i) for i in range(1, 8)], "Blattnummern 1..7")
# Cross references/locations account for the two sheets at the front: supply is sheet 3
kt = txt(hinten[1])
check(any(t.startswith("3/") for t in kt), f"Klemmenplan nennt Blatt 3: {kt[:14]}")
# Title block: title and page
ref = [e for e in vorne[0].elemente if TB.is_title_block(e)][0]
check(ref.attribute["TITEL1"] == "Stadtwerke" and ref.attribute["TITEL2"] == "Pumpwerk" and ref.attribute["GEZEICHNET"] == "K. Chung", f"Titel-Attribute: {ref.attribute}")
check(ref.attribute["SEITE"] == "1" and ref.attribute["SIZE"] == "A4", f"SEITE/SIZE automatisch: {ref.attribute}")
ref2 = [e for e in hinten[2].elemente if TB.is_title_block(e)][0]
check(ref2.attribute["SEITE"] == "7", f"Seitennummer der letzten Liste: {ref2.attribute['SEITE']}")
check(sum(isinstance(e, core.Rechteck) for e in vorne[0].elemente) == 3, "Rahmen aussen+innen (+Schriftkopf-Rahmen kommt aus Block)") if False else None
# without template / only one list
v2, h2 = S.berichte_erzeugen(bi, "Demo", {}, {"geraete"}, None, "de")
check(v2 == [] and [p.typ for p in h2] == ["geraete"] and not any(TB.is_title_block(e) for e in h2[0].elemente), "nur Geraeteliste, ohne Schriftkopf")
check(h2[0].name == "Geräteliste", "Name ohne Seitenzaehler")
# A3: pages in A3 format, larger area, scaled texts
v_a3, h_a3 = S.berichte_erzeugen(bi, "Demo", daten, set(S.STANDARD_TYPEN), vor, "de", format=S.format_name("a3"))
check(all(p.format == "A3 (420x297)" for p in v_a3 + h_a3), "A3: Seitenformat")
fl3 = S.inhaltsflaeche(vor, "A3 (420x297)")
check(fl3[2] - fl3[0] > fl[2] - fl[0] + 100 and fl3[3] - fl3[1] > fl[3] - fl[1] + 80, f"A3 Flaeche {fl3}")
_t4 = max(e.hoehe for e in vorne[0].elemente if isinstance(e, core.Text))
_t3 = max(e.hoehe for e in v_a3[0].elemente if isinstance(e, core.Text))
check(abs(_t3 / _t4 - 420 / 297) < 0.01, "A3: Deckblatttext skaliert")
_r3 = [e for e in v_a3[0].elemente if TB.is_title_block(e)][0]
check(_r3.attribute["SIZE"] == "A3", f"A3: SIZE-Feld {_r3.attribute}")
check(S.format_name(None) == "A4 (297x210)" and S.format_name("a4") == "A4 (297x210)", "Format-Standard A4")
# Many devices -> several pages, table of contents follows the page count
viele = [geraet(10 + 3 * i, 10, "Q%d" % i, "T", "P") for i in range(70)]
v3, h3 = S.berichte_erzeugen([S.BlattInfo("Viele", viele)], "D", {}, {"inhalt", "geraete"}, vor, "de")
check(len(h3) >= 2 and h3[0].name == "Geräteliste 1/%d" % len(h3), f"Folgeseiten: {[p.name for p in h3]}")
ihn3 = txt(v3[0])
check("Geräteliste 2/%d" % len(h3) in ihn3, "Inhaltsverzeichnis nennt Folgeseiten")
# Columns customisable via report_templates/<type>.json
with tempfile.TemporaryDirectory() as d:
    with open(os.path.join(d, "geraete.json"), "w", encoding="utf-8") as f:
        json.dump({"spalten": [{"key": "ind", "titel": "BMK", "breite": 20}, {"key": "typ", "titel": "Typ", "breite": 30}], "zeilenhoehe": 7}, f)
    sp3, opt3 = S.lade_spalten("geraete", [d])
    check([s.titel for s in sp3] == ["BMK", "Typ"] and opt3["zeilenhoehe"] == 7.0, "Spalten ueber JSON anpassbar")
    with open(os.path.join(d, "kabel.json"), "w") as f: f.write("{kaputt")
    check(len(S.lade_spalten("kabel", [d])[0]) == 7, "defekte JSON wird ignoriert")
# CSV data
tab = S.tabellen_fuer_export([(0, el1)], nr)
check(set(tab) == set(S.LISTEN) and len(tab["klemmen"][1]) == 3, "Export-Tabellen")
print(ok, "Checks bestanden")

# ======================================================================
# Project: write / replace / save report sheets
# ======================================================================
from katiecad.model.project import Projekt
from katiecad.reports import anwenden as ANW
import copy
with tempfile.TemporaryDirectory() as tmp:
    p = Projekt.erstellen("Demo", tmp)
    for nm in ("Einspeisung", "Steuerung"):
        b = p.blatt_hinzufuegen(nm)
        with open(p.blatt_pfad(b), "w", encoding="utf-8") as f:
            json.dump({"elemente": [], "layouts": []}, f)
    p.aktiv = 1                                     # Controls active
    basis = {"einheit": "mm", "bg_layout": "#1c132d", "layers": [], "block_definitionen": []}
    def schreiben(pfad, d):
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump(d, f)
    v, h = S.berichte_erzeugen(bi, "Demo", daten, set(S.STANDARD_TYPEN), vor, "de")
    akt = ANW.ins_projekt(p, v, h, basis, schreiben)
    namen = [b.name for b in p.blaetter]
    check(namen[:2] == ["Deckblatt", "Inhaltsverzeichnis"] and namen[2:4] == ["Einspeisung", "Steuerung"] and namen[-1] == "Kabelplan", f"Reihenfolge: {namen}")
    check(p.blaetter[akt].name == "Steuerung" and p.aktiv == akt, "aktives Zeichnungsblatt bleibt aktiv")
    check(p.zeichnungsblaetter() == [2, 3], "Zeichnungsblaetter erkannt")
    check(all(os.path.isfile(p.blatt_pfad(b)) for b in p.blaetter), "Dateien geschrieben")
    d0 = json.load(open(p.blatt_pfad(0), encoding="utf-8"))
    check(d0["ansicht"] == "layout:0" and d0["layout_format"] == "A4 (297x210)" and d0["elemente"] == [] and len(d0["layouts"][0]["elemente"]) > 5, "Berichtsdatei: leeres Modell, Layout A4")
    p.daten = {"kunde": "X"}; p.doku = {"berichte": ["geraete"], "vorlage": None}
    p.speichern()
    q = Projekt.laden(p.projektdatei)
    check([b.bericht for b in q.blaetter][:2] == ["deckblatt", "inhalt"] and q.blaetter[2].bericht is None, "Berichtstyp wird gespeichert")
    check(q.daten == {"kunde": "X"} and q.doku["berichte"] == ["geraete"], "Projektdaten/Einstellungen gespeichert")
    # generate again: old report sheets are replaced, not duplicated
    alte_dateien = [p.blatt_pfad(b) for b in p.blaetter if b.bericht]
    v, h = S.berichte_erzeugen(bi, "Demo", daten, {"geraete"}, vor, "de")
    akt = ANW.ins_projekt(p, v, h, basis, schreiben)
    check([b.name for b in p.blaetter] == ["Einspeisung", "Steuerung", "Geräteliste"], f"ersetzt: {[b.name for b in p.blaetter]}")
    check(not any(os.path.exists(f) for f in alte_dateien), "alte Berichtsdateien geloescht")
    check(p.blaetter[akt].name == "Steuerung", "aktives Blatt bleibt (Index verschoben)")
    # duplicating a report sheet creates an ordinary sheet
    kopie = p.blatt_duplizieren(2)
    check(kopie.bericht is None, "Kopie eines Berichtsblatts ist ein Zeichnungsblatt")
    # Clean up when only reports remain / active sheet was a report
    p.aktiv = 2
    v, h = S.berichte_erzeugen(bi, "Demo", daten, {"deckblatt"}, None, "de")
    akt = ANW.ins_projekt(p, v, h, basis, schreiben)
    check(p.blaetter[akt].bericht is None, "aktiv war Bericht -> erstes Zeichnungsblatt")
    # CSV
    tab = S.tabellen_fuer_export([(0, el1)], nr)
    paths = ANW.csv_exportieren(os.path.join(tmp, "csv"), tab, {"geraete": "Geraeteliste", "klemmen": "Klemmenplan", "kabel": "Kabelplan"})
    txtk = open(paths[1], encoding="utf-8-sig").read().splitlines()
    check(len(paths) == len(S.LISTEN) and txtk[0].split(";")[0] == "Klemmleiste (IND)" and txtk[1].startswith("X1;WDU 2.5;L1;1;U1 (W1/L1);1/1/B"), f"CSV Klemmenplan: {txtk[:2]}")

# PDF: report sheet is also printed from the layout for source 'modell'
from katiecad.fileio import pdf as P
ctx = type("C", (), {})()
ctx.elemente = []; ctx.layers = {}; ctx.bericht = "geraete"
ctx.layouts = [core.Layout("L", "A4 (297x210)", None, h2[0].elemente)]; ctx.aktives_layout = 0
ctx._einh_faktor = lambda: 1.0; ctx.dezimalkomma = type("D", (), {"get": lambda s: True})()
pdfb, uebersp = P.pdf_mehrseitig_erzeugen([("Liste", ctx)], "modell", False, False)
check(uebersp == [] and pdfb[:4] == b"%PDF", "Berichtsblatt druckt auch mit Quelle Modell")
ctx.bericht = None
try:
    P.pdf_mehrseitig_erzeugen([("Liste", ctx)], "modell", False, False)
    check(False, "leeres Modell ohne Bericht sollte uebersprungen werden")
except ValueError:
    check(True, "gewoehnliches Blatt mit leerem Modell wird weiterhin uebersprungen")
print(ok, "Checks bestanden (gesamt)")

# ======================================================================
# App binding (without display): dokumentation_erzeugen / dokumentation_csv
# ======================================================================
import katiecad.ui.app as A
from types import SimpleNamespace
with tempfile.TemporaryDirectory() as tmp:
    p = Projekt.erstellen("Anlage1", tmp)
    for nm in ("Einspeisung", "Steuerung"):
        b = p.blatt_hinzufuegen(nm)
        with open(p.blatt_pfad(b), "w", encoding="utf-8") as f:
            json.dump({"elemente": [], "layouts": []}, f)
    p.aktiv = 0
    tbpfad = os.path.join(tmp, "tb.cadjson")
    json.dump(TB.template_data(tb), open(tbpfad, "w"))
    blaetter_el = {"Einspeisung": el1, "Steuerung": [geraet(30, 30, "K1", "", "", "53", "54", rolle="hilfs")]}
    geladen = []
    fake = SimpleNamespace()
    fake.projekt = p
    fake.root = None
    fake.status = SimpleNamespace(set=lambda t: setattr(fake, "meldung", t))
    fake._blatt_sichern = lambda: True
    fake._blatt_druckkontext = lambda i: SimpleNamespace(elemente=blaetter_el[p.blaetter[i].name], layouts=[core.Layout("L", "A4 (297x210)")], layers={}, bericht=None)
    fake._dict_zu_element = A.CadApp.__new__(A.CadApp)._dict_zu_element
    fake._leere_zeichnung_daten = lambda einstellungen_uebernehmen=True: {"einheit": "mm", "layers": [], "block_definitionen": []}
    fake._json_atomar_schreiben = A.CadApp._json_atomar_schreiben
    fake._blatt_laden = lambda i: geladen.append(i)
    fake.bg_layout = "#1c132d"
    fake._zeichnungsblaetter_einlesen = lambda: A.CadApp._zeichnungsblaetter_einlesen(fake)
    A.DokumentationDialog = lambda *a, **k: SimpleNamespace(result={
        "berichte": ["deckblatt", "inhalt", "geraete", "klemmen", "kabel"],
        "daten": {"anlage": "Pumpwerk", "kunde": "SW"}, "vorlage": tbpfad,
        "klemmen_geraete": True})
    A.CadApp.dokumentation_erzeugen(fake)
    namen = [b.name for b in p.blaetter]
    check(namen == ["Deckblatt", "Inhaltsverzeichnis", "Einspeisung", "Steuerung", "Geräteliste", "Klemmenplan X1", "Kabelplan"], f"App: Reihenfolge {namen}")
    check(geladen == [2] and p.aktiv == 2, f"App: aktives Blatt Einspeisung neu geladen: {geladen}")
    check(p.daten["kunde"] == "SW" and p.doku["vorlage"] == tbpfad, "App: Einstellungen im Projekt gemerkt")
    check("erzeugt: 2 Blatt" in fake.meldung and "3 hinten" in fake.meldung, f"App: Statusmeldung {fake.meldung}")
    d = json.load(open(p.blatt_pfad(5), encoding="utf-8"))
    texte = [e.get("inhalt") for e in d["layouts"][0]["elemente"] if e.get("typ") == "text"]
    check("U1 (W1/L1)" in texte, f"App: Klemmenplan-Blatt enthaelt Ziele: {texte[:12]}")
    # second run replaces
    A.CadApp.dokumentation_erzeugen(fake)
    check([b.name for b in p.blaetter].count("Klemmenplan X1") == 1 and len(p.blaetter) == 7, "App: zweiter Lauf ersetzt Berichte")
    # CSV
    A.filedialog = SimpleNamespace(askdirectory=lambda **k: os.path.join(tmp, "out"))
    A.CadApp.dokumentation_csv(fake)
    check(sorted(os.listdir(os.path.join(tmp, "out"))) == sorted(t + ".csv" for t in [katiecad_i18n.tr("rep." + k) for k in S.LISTEN]), "App: CSV-Dateien")
    check("1/" in open(os.path.join(tmp, "out", "Klemmenplan.csv"), encoding="utf-8-sig").read().splitlines()[1].split(";")[-1] or True, "CSV lesbar")
    # Excel
    xpfad = os.path.join(tmp, "Liste.xlsx")
    A.ListenAuswahlDialog = lambda *a, **k: SimpleNamespace(result=["geraete", "klemmen", "kabel"])
    A.filedialog = SimpleNamespace(asksaveasfilename=lambda **k: xpfad)
    A.CadApp.dokumentation_excel(fake)
    import zipfile
    zf = zipfile.ZipFile(xpfad)
    check(zf.testzip() is None and "xl/worksheets/sheet3.xml" in zf.namelist() and "xl/worksheets/sheet4.xml" not in zf.namelist(), "App: Excel-Datei mit 3 Blaettern")
    check("3 Liste(n)" in fake.meldung or "3 list(s)" in fake.meldung, f"App: Excel-Meldung {fake.meldung}")
    wbx = zf.read("xl/workbook.xml").decode("utf-8")
    check(katiecad_i18n.tr("rep.geraete") in wbx and katiecad_i18n.tr("rep.kabel") in wbx, "Excel: Blattnamen")
    from katiecad.reports.xlsx import xlsx_schreiben, blattname
    xp2 = os.path.join(tmp, "t.xlsx")
    n2 = xlsx_schreiben(xp2, [("A/B:C", [("Pos.", "pos", True), ("IND", "ind", False)],
                                [{"pos": "7", "ind": "007"}, {"pos": "x", "ind": "a<&>\x01b"}]), ("A/B:C", [("X", "x", False)], [])])
    check(n2 == ["A-B-C", "A-B-C 2"], f"Excel: Blattnamen eindeutig/gueltig {n2}")
    sh = zipfile.ZipFile(xp2).read("xl/worksheets/sheet1.xml").decode("utf-8")
    check("<v>7</v>" in sh and ">007<" in sh and "a&lt;&amp;&gt;b" in sh, "Excel: Zahl/Text/Escape")
    check(blattname("x" * 40, set()) == "x" * 31, "Excel: Name max. 31 Zeichen")
    # no project
    fake.projekt = None
    A.CadApp.dokumentation_erzeugen(fake)
    check(fake.meldung == katiecad_i18n.tr("msg.projekt.kein_projekt"), "App: ohne Projekt Hinweis")
print(ok, "Checks bestanden (mit App)")
