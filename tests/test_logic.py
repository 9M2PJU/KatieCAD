import sys, os, json, tempfile, shutil, types
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401  (installs the tkinter stand-in)   # Tk stub
import katiecad.model.core as core
import katiecad.ui.app as appmod
from katiecad.model.project import Projekt, ProjektFehler, name_pruefen
from katiecad.model.blocks import block_speichern, block_laden, vorschlag_dateiname

holder = types.SimpleNamespace()
holder._dict_zu_element = lambda d: appmod.CadApp._dict_zu_element(holder, d)
fac = holder._dict_zu_element

ok = 0
def check(cond, msg):
    global ok
    assert cond, "FEHLER: " + msg
    ok += 1

# ---------- 1) Attributes in the block ----------
sym = core.Rechteck(-5, -5, 5, 5)
a1 = core.AttributDefinition(0, 8, None, 3.5, 0.0, "Arial", tag="name", prompt="Betriebsmittel", wert="-Q1")
a2 = core.AttributDefinition(0, -8, None, 2.5, 0.0, "Arial", tag="Leistung", wert="", sichtbar=True)
a3 = core.AttributDefinition(0, -12, None, 2.5, 0.0, "Arial", tag="intern", wert="geheim", sichtbar=False)
check(a1.tag == "NAME" and a1.typ == "attdef" and a1.inhalt == "<NAME>", "AttDef Normalisierung")
d = core.BlockDefinition("Schuetz", (0, 0), [sym, a1, a2, a3])
check(len(d.attribut_definitionen()) == 3, "attribut_definitionen")
ref = core.BlockReferenz(100, 50, "Schuetz", d.elemente, layer="0")
check(ref.attribute == {"NAME": "-Q1", "LEISTUNG": "", "INTERN": "geheim"}, "Defaults uebernommen")
kinder = ref.aufgeloest()
texte = [k for k in kinder if isinstance(k, core.Text)]
check(len(texte) == 1 and texte[0].inhalt == "-Q1" and not isinstance(texte[0], core.AttributDefinition),
      "nur sichtbare, nichtleere Attribute als Text")
check(abs(texte[0].x - 100) < 1e-9 and abs(texte[0].y - 58) < 1e-9, "Position transformiert")
ref.setze_attribute({"NAME": "-K12", "LEISTUNG": "5,5 kW", "UNBEKANNT": "x"})
check("UNBEKANNT" not in ref.attribute, "unbekannte Tags ignoriert")
inh = sorted(k.inhalt for k in ref.aufgeloest() if isinstance(k, core.Text))
check(inh == ["-K12", "5,5 kW"], f"Werte sichtbar: {inh}")
# Rotation + scaling
ref2 = core.BlockReferenz(0, 0, "Schuetz", d.elemente, skalierung=2.0, winkel=90.0)
t = [k for k in ref2.aufgeloest() if isinstance(k, core.Text)][0]
check(abs(t.hoehe - 7.0) < 1e-9 and abs(t.winkel - 90.0) < 1e-9, "Skalierung/Drehung Text")
b = ref.bbox()
check(b[3] >= 8, "bbox enthaelt sichtbare Attribute")
# The instance must be decoupled from the definition
ref.elemente[1].wert = "X"
check(d.elemente[1].wert == "-Q1", "Deep copy")

# ---------- 2) Serialisation ----------
ref.setze_attribute({"NAME": "-K12"})
js = json.loads(json.dumps(ref.to_dict()))
r2 = fac(js)
check(isinstance(r2, core.BlockReferenz) and r2.attribute["NAME"] == "-K12" and r2.attribute["LEISTUNG"] == "5,5 kW",
      "Roundtrip BlockReferenz.attribute")
check(len(r2.attribut_definitionen()) == 3, "Roundtrip AttDefs in Referenz")
dd = core.BlockDefinition.from_dict(json.loads(json.dumps(d.to_dict())), fac)
check([type(e).__name__ for e in dd.elemente] == ["Rechteck", "AttributDefinition", "AttributDefinition", "AttributDefinition"], "Roundtrip Definition")
# Legacy file without 'attribute'
alt = ref.to_dict(); alt.pop("attribute")
r3 = fac(json.loads(json.dumps(alt)))
check(r3.attribute["NAME"] == "X", "Altformat ohne attribute -> Defaults der Instanz")
# Exploding: children from aufgeloest are text with value
check(all(not isinstance(k, core.AttributDefinition) for k in ref.aufgeloest()), "Explode ohne AttDefs")
# Serialise a free AttDef in the model
fa = fac(json.loads(json.dumps(a1.to_dict())))
check(isinstance(fa, core.AttributDefinition) and fa.prompt == "Betriebsmittel", "freie AttDef")

# ---------- 3) Block file ----------
tmp = tempfile.mkdtemp()
try:
    pf = os.path.join(tmp, vorschlag_dateiname('Sch:ütz/1'))
    check(pf.endswith(".katieblock") and ":" not in os.path.basename(pf), "Dateiname bereinigt")
    block_speichern(pf, d)
    dl = block_laden(pf, fac)
    check(dl.name == "Schuetz" and len(dl.attribut_definitionen()) == 3, "Blockdatei Roundtrip")
    open(os.path.join(tmp, "x.katieblock"), "w").write("{kaputt")
    try: block_laden(os.path.join(tmp, "x.katieblock"), fac); check(False, "kaputt")
    except Exception as e: check(True, "kaputte Blockdatei -> Fehler")
    open(os.path.join(tmp, "y.katieblock"), "w").write('{"foo": 1}')
    try: block_laden(os.path.join(tmp, "y.katieblock"), fac); check(False, "fremd")
    except Exception as e: check(True, "fremdes JSON -> Fehler")

    # ---------- 4) Project ----------
    check(name_pruefen("") == "leer" and name_pruefen("a/b") == "zeichen" and name_pruefen("x.") == "ende"
          and name_pruefen("con") == "reserviert" and name_pruefen("Hauptverteilung 1") is None, "name_pruefen")
    p = Projekt.erstellen("Verteilung Nord", tmp)
    check(os.path.isfile(os.path.join(tmp, "Verteilung Nord", "Verteilung Nord.katieprj")), "Projektdatei angelegt")
    try: Projekt.erstellen("Verteilung Nord", tmp); check(False, "doppelt")
    except ProjektFehler as e: check(str(e) == "ordner_existiert", "Doppeltes Projekt abgelehnt")
    b1 = p.blatt_hinzufuegen("Deckblatt"); b2 = p.blatt_hinzufuegen(); b3 = p.blatt_hinzufuegen("Stromlauf")
    check([b.datei for b in p.blaetter] == ["Blatt_001.cadjson", "Blatt_002.cadjson", "Blatt_003.cadjson"], "Dateinamen")
    check(b2.name == "Blatt 2" and p.nummer(2) == "003", "Name/Nummer")
    for b in p.blaetter: open(p.blatt_pfad(b), "w").write("{}")
    p.blatt_verschieben(2, -1)
    check([b.name for b in p.blaetter] == ["Deckblatt", "Stromlauf", "Blatt 2"], "verschieben")
    check(p.blatt_verschieben(0, -1) == 0, "verschieben am Rand")
    p.aktiv = 1; p.speichern()
    q = Projekt.laden(p.projektdatei)
    check([b.name for b in q.blaetter] == ["Deckblatt", "Stromlauf", "Blatt 2"] and q.aktiv == 1 and q.naechste_id == 4, "laden")
    q.blatt_entfernen(1)
    check(len(q.blaetter) == 2 and not os.path.exists(os.path.join(q.ordner, "Blatt_003.cadjson")), "entfernen loescht Datei")
    b4 = q.blatt_hinzufuegen("Neu")
    check(b4.datei == "Blatt_004.cadjson", "IDs werden nicht wiederverwendet")
    # Foreign file in the folder + block folder
    os.makedirs(q.bloecke_ordner); block_speichern(os.path.join(q.bloecke_ordner, "a.katieblock"), d)
    open(os.path.join(q.ordner, "notizen.txt"), "w").write("fremd")
    q.speichern()
    weg, rest = q.loeschen()
    check(not weg and rest == ["notizen.txt"], f"Loeschen schont fremde Dateien: {rest}")
    check(not os.path.exists(q.projektdatei) and not os.path.exists(q.bloecke_ordner), "Projektdateien weg")
    os.remove(os.path.join(q.ordner, "notizen.txt"))
    p2 = Projekt.erstellen("Leer", tmp); weg, rest = p2.loeschen()
    check(weg and not os.path.exists(p2.ordner), "leerer Ordner wird entfernt")
    open(os.path.join(tmp, "fremd.katieprj"), "w").write('{"format":"anderes"}')
    try: Projekt.laden(os.path.join(tmp, "fremd.katieprj")); check(False, "fremd")
    except ProjektFehler as e: check(str(e) == "kein_projekt", "Fremdes Format abgelehnt")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print(f"{ok} Checks bestanden")
