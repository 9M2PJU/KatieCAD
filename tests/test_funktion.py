import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.common.i18n as katiecad_i18n; katiecad_i18n.SPRACHE["aktuell"] = "de"
import katiecad.model.core as core
import katiecad.electrical.funktion as F
import katiecad.electrical.logic as L
from katiecad.model.blocks import block_laden
from katiecad.reports import netz as N, daten as D, seiten as S, daten_sps as DS
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

VP = core.Verbindungspunkt
def geraet(x, y, ind, typ=""):
    sym = [core.Rechteck(-5, -5, 5, 5), VP(0, 5, wert="1", tag="P1"), VP(0, -5, wert="2", tag="P2"),
           core.ElektroMaske(8, 0)]
    b = core.BlockReferenz(x, y, "Sym", sym)
    b.attribute.update({"IND": ind, "TYP": typ, "PER": ""})
    return b

def ft(x, y, text):
    return core.Text(x, y, text, 3.5, 0.0, "Arial", layer=core.FTEXT_LAYER)

nr = lambda i: i + 1
# Funktionstexte: Regel
t1, t2 = ft(0, 100, "Antrieb 1\nLüfter"), ft(100, 100, "Pumpe")
texte = F.funktionstexte([t1, t2, core.Text(5, 5, "normal", 3.5, 0.0, "Arial")])
check(len(texte) == 2 and texte[0][2] == ["Antrieb 1", "Lüfter"], "Funktionstexte erkannt (nur Layer F-Text)")
check(F.funktion_an(texte, 50, 90) == ["Antrieb 1", "Lüfter"], "naechster Text links")
check(F.funktion_an(texte, 150, 90) == ["Pumpe"], "naechster Text rechts davon")
check(F.funktion_an(texte, -20, 90) == [], "links vom ersten Text: keine Funktion")
check(F.funktion_an([], 10, 10) == [], "ohne Texte leer")

# Geraeteliste und Klemmenplan
k1, k2 = geraet(50, 60, "K1", "T"), geraet(150, 60, "K2", "T")
kl = [core.Klemme(50, 20, werte={"IND": "X1", "NUM": "1", "TYP": "", "PER": ""}) for _ in range(1)]
bl = [(0, [t1, t2, k1, k2] + kl)]
n = N.Netz.aufbauen(bl)
gl = D.geraeteliste(bl, nr, n)
fk = {z["ind"]: z["funktion"] for z in gl}
check(fk["K1"] == ["Antrieb 1", "Lüfter"] and fk["K2"] == ["Pumpe"], f"Geraeteliste Funktion: {fk}")
check(fk.get("X1") == ["Antrieb 1", "Lüfter"], f"Klemmenleiste in Geraeteliste: {fk}")
kp = D.klemmenplan(n, bl, nr)
check(kp[0]["funktion"] == ["Antrieb 1", "Lüfter"], "Klemmenplan Funktion")
sp, _o = S.lade_spalten("geraete"); check(sp[-1].key == "funktion", "Spalte Funktion hinten rechts (Geraete)")
sp, _o = S.lade_spalten("klemmen"); check(sp[-1].key == "funktion", "Spalte Funktion hinten rechts (Klemmen)")
check(not any(c.key == "funktion" for c in S._ohne_leere_einbauorte(S.lade_spalten("geraete")[0], [{"funktion": []}])), "leere Funktionsspalte entfaellt")
check(any(c.key == "funktion" for c in S._ohne_leere_einbauorte(S.lade_spalten("geraete")[0], gl)), "Funktionsspalte bleibt mit Inhalt")

# Layer-Konstante
check(core.FTEXT_LAYER == "F-Text" and core.FTEXT_LAYER in core.ELEKTRO_LAYER, "Layer F-Text")
check(core.BEFEHLE["FTEXT"] == "tool:ftext", "Befehl FTEXT")

# SPS-Liste aus der Symbolbibliothek
import katiecad.ui.app as A
a = A.CadApp.__new__(A.CadApp)
def modul(name, x, y, ind):
    pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "symbols", "10 PLC", name + ".katieblock")
    d = block_laden(pfad, a._dict_zu_element)
    b = core.BlockReferenz(x, y, d.name, [e for e in d.elemente])
    for ad in d.attribut_definitionen():
        b.attribute[ad.tag] = ad.wert
    b.attribute["IND"] = ind
    return b
di = modul("PLC DI 8", 100, 100, "-A1")
check(DS.sps_art(di) == "DI", "Symbol traegt SPS=DI")
check(len(DS.kanaele(di)) == 8, "8 Kanaele (ohne Versorgungspin)")
check("VP1_SYM" in di.attribute and "STATION" in di.attribute and "PLATZ" in di.attribute, "Zusatzfelder als Attribute")
cpu = modul("PLC CPU", 20, 100, "-A0")
check(DS.sps_art(cpu) == "CPU" and "VP1_SYM" not in cpu.attribute, "CPU ohne Kanalfelder")
di.attribute.update({"STATION": "SPS1", "PLATZ": "4", "VP1_SYM": "S_Start", "VP1_KOM": "Taster Start"})
taster = geraet(100, 130, "S1", "Taster")
w = core.Leitung(100, 107.5, 100, 125)
bl2 = [(0, [core.Koordinatenfeld(0, 0, 287, 164, 6, 4), di, cpu, taster, w])]
L.leitungen_automatisch(bl2[0][1])
n2 = N.Netz.aufbauen(bl2)
sl = DS.sps_liste(n2, bl2, nr, {0: "Schrank"})
check(len(sl) == 8 and all(r["art"] == "DI" and r["datentyp"] == "BOOL" for r in sl), f"8 Zeilen DI: {len(sl)}")
r0 = [r for r in sl if r["adresse"] == "I0.0"][0]
check(r0["station"] == "SPS1" and r0["platz"] == "4" and r0["baugruppe"] == "-A1" and r0["symbol"] == "S_Start"
      and r0["kommentar"] == "Taster Start" and r0["einbauort"] == "Schrank", f"Zeile I0.0: {r0}")
check(r0["anschluss"] == ["S1:2"], f"Anschluss: {r0['anschluss']}")
check([r["adresse"] for r in sl] == ["I0.%d" % i for i in range(8)], "Adressen sortiert")
check("sps" in S.LISTEN and "sps" in S.TYPEN, "Typ sps registriert")
tab = S.tabellen_fuer_export(bl2, nr)
check("sps" in tab and len(tab["sps"][1]) == 8, "Export enthaelt SPS-Liste")
check(S.lade_spalten("sps")[0][0].key == "station", "Spaltendefinition sps")
de = set(katiecad_i18n.TEXTE["de"]); en = set(katiecad_i18n.TEXTE["en"])
check(de == en, "i18n Paritaet %s" % (de ^ en))
print(ok, "Checks bestanden")
