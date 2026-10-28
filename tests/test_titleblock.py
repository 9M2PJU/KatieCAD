import os, sys, json, tempfile, types, shutil
from unittest.mock import MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401
import katiecad.common.i18n as i18n; i18n.SPRACHE["aktuell"] = "en"
import katiecad.model.core as core
import katiecad.model.titleblock as TB
import katiecad.ui.app as A
from katiecad.model.project import Projekt, ProjektFehler
NS = types.SimpleNamespace
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

A.lade_konfiguration = lambda: {}
A.speichere_konfiguration = lambda d: None
A.messagebox = MagicMock()

# ---- Geometry
aussen, innen = TB.frame_rects(420, 297)
check(innen == (20.0, 5.0, 415.0, 292.0), "Rand links 20 mm, sonst 5 mm")
check(TB.block_origin(420, 297) == (415.0, 5.0), "Nullpunkt = untere rechte Ecke des Blattrands")
a4_aussen, a4_innen = TB.frame_rects(297, 210)
check(a4_innen == (5.0, 5.0, 292.0, 195.0), "A4: links 5 mm, oben 15 mm, rechts/unten 5 mm: %s" % (a4_innen,))
check(TB.block_origin(297, 210) == (292.0, 5.0), "A4: Nullpunkt unten rechts")
check(TB.margins(594, 420) == (20.0, 5.0, 5.0, 5.0) and TB.margins(297, 210)[1] == 15.0, "nur A4 hat 15 mm oben")

# ---- Templates in the folder
tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, "prog")); os.makedirs(os.path.join(tmp, "proj", "title_blocks"))
els = TB.default_elements("en")
for ordner, n in (("prog", "A"), (os.path.join("proj", "title_blocks"), "B")):
    with open(os.path.join(tmp, ordner, n + ".cadjson"), "w", encoding="utf-8") as f:
        json.dump(TB.template_data(els), f)
with open(os.path.join(tmp, "prog", "kaputt.cadjson"), "w") as f:
    f.write("{nicht json")
lst = TB.list_templates([os.path.join(tmp, "prog"), os.path.join(tmp, "proj", "title_blocks")])
check([n for n, _ in lst] == ["A", "B", "kaputt"], "Vorlagen werden gelistet: %s" % [n for n, _ in lst])
check(TB.program_folder().endswith("title_blocks"), "Programmordner title_blocks")

class T(A.CadApp):
    view = {"zoom": 2.0, "ox": 0, "oy": 0}
def make():
    a = T.__new__(T)
    a.root = MagicMock(); a.status = MagicMock(); a.seitenleiste = MagicMock()
    a._dirty = False; a.projekt = None
    a._undo_stack = []; a._redo_stack = []; a._undo_max = 50; a._undo_pro_blatt = {}
    a.elemente = []; a.layers = a._standard_layers()
    a.layouts = [core.Layout("Layout1", "A3 (420x297)", "#1c132d")]; a.aktives_layout = 0
    a._ist_layout = lambda: True; a._zustand = lambda: {"n": 0}
    a.redraw = MagicMock(); a.auswahl = []
    a.massstab = NS(get=lambda: "1:50")
    return a
D = lambda *x, **k: None
la = TB.load_template(lst[0][1], lambda d: make()._dict_zu_element(d))
check(len(la) == len(els), "Vorlage laden: %d Elemente" % len(la))
for bad in (lst[2][1], os.path.join(tmp, "gibts_nicht.cadjson")):
    try:
        TB.load_template(bad, lambda d: None); check(False, "Fehler erwartet")
    except (OSError, ValueError):
        check(True, "Defekte/fehlende Vorlage -> Fehler")

# ---- Insert frame + title block
a = make()
alt = core.Rechteck(10, 5, 415, 292)       # old frame with 10 mm on the left
a.layouts[0].elemente.append(alt)
asked = []
a._attribute_abfragen = lambda r: asked.append(r)
A.TitleBlockDialog = lambda *x, **k: NS(result=lst[0][1])
A.TB.template_folders = lambda f=None: [os.path.join(tmp, "prog")]
a.rahmen_einfuegen()
le = a.layouts[0].elemente
blocks = [e for e in le if TB.is_title_block(e)]
check(len(blocks) == 1 and (blocks[0].x, blocks[0].y) == (415.0, 5.0), "Schriftkopf unten rechts am Blattrand")
check(alt not in le, "alter 10-mm-Rahmen entfernt")
check(any(isinstance(e, core.Rechteck) and abs(e.x1 - 20) < 1e-6 for e in le), "neuer Rahmen mit 20 mm links")
check(blocks[0].attribute["PAGE"] == "1" and blocks[0].attribute["PAGES"] == "1" and blocks[0].attribute["DATE"], "automatische Felder gefuellt")
check(asked == [blocks[0]], "uebrige Felder werden abgefragt")
check(a._attr_ausschluss(blocks[0]) == {ad.tag for ad in blocks[0].attribut_definitionen() if ad.tag in TB.RESERVED} and a._attr_ausschluss(core.BlockReferenz(0, 0, "X", [])) == (), "reservierte Tags nicht abgefragt")
n_rect = sum(isinstance(e, core.Rechteck) for e in le)
A.TitleBlockDialog = lambda *x, **k: NS(result=os.path.join(tmp, "prog", "A.cadjson"))
a.rahmen_einfuegen()
le = a.layouts[0].elemente
check(len([e for e in le if TB.is_title_block(e)]) == 1, "erneutes Einfuegen ersetzt den Schriftkopf")
check(sum(isinstance(e, core.Rechteck) for e in le) == n_rect, "Rahmen wird nicht doppelt gezeichnet")
A.TitleBlockDialog = lambda *x, **k: NS(result="")
a.rahmen_einfuegen()
check(not any(TB.is_title_block(e) for e in a.layouts[0].elemente), "nur Rahmen: Schriftkopf entfernt")
A.TitleBlockDialog = lambda *x, **k: NS(result=os.path.join(tmp, "prog", "kaputt.cadjson"))
a.rahmen_einfuegen(); check(A.messagebox.showerror.called, "defekte Vorlage meldet Fehler")
a._ist_layout = lambda: False; a.status.reset_mock(); a.rahmen_einfuegen()
check(a.status.set.called, "im Modell: nur Hinweis")

# ---- A4: different margin, old frames are replaced
a = make(); a.layouts[0].format = "A4 (297x210)"
a.layouts[0].elemente += [core.Rechteck(20, 5, 292, 205), core.Rechteck(10, 5, 292, 205)]
A.TitleBlockDialog = lambda *x, **k: NS(result=os.path.join(tmp, "prog", "A.cadjson"))
a._attribute_abfragen = lambda r: None
a.rahmen_einfuegen()
le = a.layouts[0].elemente
rs = sorted((round(e.x1), round(e.y1), round(e.x2), round(e.y2)) for e in le if isinstance(e, core.Rechteck))
check(rs == [(0, 0, 297, 210), (5, 5, 292, 195)], "A4: alte Rahmen ersetzt, neuer Rahmen 5/15/5/5: %s" % rs)
tbk = [e for e in le if TB.is_title_block(e)][0]
check((tbk.x, tbk.y) == (292.0, 5.0), "A4: Schriftkopf unten rechts")
a.rahmen_einfuegen()
check(sum(isinstance(e, core.Rechteck) for e in a.layouts[0].elemente) == 2, "A4: kein doppelter Rahmen")

# ---- Automatic fields across the project
pd = os.path.join(tmp, "pr"); os.makedirs(pd)
p = Projekt.erstellen("Anlage", pd)
p.blatt_hinzufuegen("Erstes")
b2 = p.blatt_hinzufuegen("Zweites")
vp = core.Viewport(10, 10, 100, 100, zoom=0.5) if "zoom" in core.Viewport.__init__.__code__.co_varnames else None
blk = TB.make_block("t", TB.default_elements("en"), 420, 297, layer="0")
info = TB.make_info(p, 1, "de", "A3 (420x297)")
check(info["PAGE"] == "2" and info["PAGES"] == "2" and info["SHEET"] == "Zweites" and info["PROJECT"] == "Anlage" and info["FORMAT"] == "A3", "make_info: %s" % info)
check(len(info["DATE"].split(".")) == 3, "Datum deutsch")
lay = [blk] + ([vp] if vp else [])
n = TB.refresh_fields(lay, info, "1:1")
check(n > 0 and blk.attribute["PAGE"] == "2", "refresh_fields setzt Werte")
if vp: check(blk.attribute["SCALE"] == "1:2", "Massstab vom Viewport: %s" % blk.attribute["SCALE"])
check(TB.refresh_fields(lay, info, "1:1") == 0, "zweiter Lauf: nichts mehr zu aendern")
# User field stays untouched
blk.attribute["TEXT"] = "Hauptverteiler"; TB.refresh_fields(lay, info, "")
check(blk.attribute["TEXT"] == "Hauptverteiler", "Anwenderfelder bleiben")
# via round trip
d = blk.to_dict(); b3 = make()._dict_zu_element(json.loads(json.dumps(d)))
check(TB.is_title_block(b3) and b3.attribute["TEXT"] == "Hauptverteiler", "Schriftkopf-Block Roundtrip")

# ---- Duplicate sheet (project)
pd2 = os.path.join(tmp, "pr2"); os.makedirs(pd2)
p = Projekt.erstellen("P", pd2)
p.blatt_hinzufuegen("Erstes")
p.blatt_hinzufuegen("Zweites")
with open(p.blatt_pfad(0), "w", encoding="utf-8") as f: json.dump({"elemente": [1, 2, 3]}, f)
nb = p.blatt_duplizieren(0)
check([x.name for x in p.blaetter][:2] == [p.blaetter[0].name, p.blaetter[0].name + " (Kopie)"] and p.blaetter.index(nb) == 1, "Kopie direkt hinter dem Original")
check(json.load(open(p.blatt_pfad(nb))) == {"elemente": [1, 2, 3]} and nb.datei != p.blaetter[0].datei, "Dateiinhalt kopiert, eigene Datei")
nb2 = p.blatt_duplizieren(0)
check(nb2.name.endswith("(Kopie 2)"), "Namen eindeutig: %s" % nb2.name)
try:
    p.blatt_duplizieren(99); check(False, "Fehler erwartet")
except ProjektFehler:
    check(True, "ungueltiger Index -> ProjektFehler")
os.remove(p.blatt_pfad(2))
try:
    p.blatt_duplizieren(2); check(False, "Fehler erwartet")
except ProjektFehler:
    check(True, "fehlende Quelldatei -> ProjektFehler")
n_vorher = len(p.blaetter)
check(n_vorher == 4, "kein Blatt zu viel registriert")

# ---- Duplicate sheet (app)
a = make(); a.projekt = p; p.aktiv = 0
A._LayoutNameDialog = lambda *x, **k: NS(result="Kopie XY")
a._blatt_sichern = lambda: True; a._stacks_merken = MagicMock(); a._blatt_laden = MagicMock()
n0 = len(p.blaetter); a.blatt_duplizieren()
check(len(p.blaetter) == n0 + 1 and p.blaetter[1].name == "Kopie XY", "App: Blatt dupliziert und eingefuegt")
a._blatt_laden.assert_called_with(1)
check(True, "App: neues Blatt wird geladen")
a.projekt = None; a.blatt_duplizieren()
check(a.status.set.called, "ohne Projekt: Hinweis")

# ---- Sidebar
a = make(); a.canvas = object(); sl = MagicMock(); sl.ist_sichtbar.return_value = True; a.seitenleiste = sl
a.seitenleiste_umschalten(); check(sl.ausblenden.called, "Seitenleiste ausblenden")
sl.ist_sichtbar.return_value = False; a.seitenleiste_umschalten(); check(sl.einblenden.called, "Seitenleiste einblenden")

# ---- Project data in the title block of every sheet
class _B:
    def __init__(self, n): self.name = n
class _P:
    name = "Pumpwerk"
    blaetter = [_B("Einspeisung"), _B("Antriebe")]
    daten = {"kunde": "Stadtwerke", "gezeichnet": "K. Chung", "zeichnungsnummer": "Z-7",
             "rev": [{"stand": "A", "aenderung": "Erstausgabe", "name": "KC", "datum": "01.10.2026"},
                     {"stand": "B", "aenderung": "", "name": "", "datum": ""}]}
inf = TB.make_info(_P(), 1, "de", "A0 (1189x841)")
check(inf["TITEL1"] == "Stadtwerke" and inf["TITEL2"] == "Pumpwerk" and inf["TITEL3"] == "Antriebe", "Titel-Teile: Kunde, Projekt, Blatt")
check(inf["TITLE"] == "Stadtwerke - Pumpwerk - Antriebe" and inf["TITEL"] == inf["TITLE"], "Titel kombiniert")
check(inf["FORMAT"] == "A0" and inf["BLATTFORMAT"] == "A0" and inf["SIZE"] == "A0", "Blattformat")
check(inf["GEZEICHNET"] == "K. Chung" and inf["DRAWN"] == "K. Chung" and inf["ZEICHNUNGSNUMMER"] == "Z-7", "Projektdaten")
check(inf["REV1_STAND"] == "A" and inf["REV1_INDEX"] == "A" and inf["REV1_AENDERUNG"] == "Erstausgabe" and inf["REV1_CHANGE"] == "Erstausgabe" and inf["REV1_NAME"] == "KC" and inf["REV1_DATUM"] == "01.10.2026" and inf["REV2_STAND"] == "B", "Aenderungsindex")
check(inf["REV3_STAND"] == "" and inf["REV2_AENDERUNG"] == "", "leere Zeilen werden geleert")
check(all(t in TB.RESERVED for t in ("REV4_DATE", "TITEL3", "KUNDE", "GEZEICHNET_DATUM", "PAPIERFORMAT")), "Tags reserviert")
blk.attribute["GEZEICHNET"] = "von Hand"
class _AD: tag = "GEZEICHNET"
blk.attribut_definitionen = lambda: [_AD()]
TB.refresh_fields([blk], {"GEZEICHNET": ""}, "")
check(blk.attribute["GEZEICHNET"] == "", "leere Projektdaten leeren das Feld wieder")
check(TB.info_values(1, 1, "", "", "de", "A4", None, None).get("KUNDE") is None, "ohne Projekt wird nichts angefasst")

# ---- Tolerant tag spellings, checked-by date
check(TB.norm_tag("Geprüft_Datum") == "GEPRUEFTDATUM" and TB.is_auto_tag("Rev-1 Stand") and TB.is_auto_tag("STAND1") and TB.is_auto_tag("Aenderung_2") and TB.is_auto_tag("Datum3") and not TB.is_auto_tag("TEXT"), "tolerante Tag-Schreibweisen")
class _AD2:
    def __init__(self, t): self.tag = t
blk.attribut_definitionen = lambda: [_AD2(t) for t in ("Stand1", "Änderung1", "Name1", "Datum1", "GEPRUEFT_DATUM", "Geprüft")]
blk.attribute.clear()
class _P2(_P):
    daten = dict(_P.daten, geprueft="M. Muster", datum="02.10.2026")
TB.refresh_fields([blk], TB.make_info(_P2(), 0, "de", "A4"), "")
check(blk.attribute.get("Stand1") == "A" and blk.attribute.get("Änderung1") == "Erstausgabe" and blk.attribute.get("Name1") == "KC" and blk.attribute.get("Datum1") == "01.10.2026", "Aenderungsindex mit eigenen Tag-Namen: %s" % blk.attribute)
check(blk.attribute.get("GEPRUEFT_DATUM") == "02.10.2026" and blk.attribute.get("Geprüft") == "M. Muster", "Pruefdatum gesetzt: %s" % blk.attribute)

for t, erw in (("AENDERUNG_NAME1", (1, "name")), ("AendDatum2", (2, "datum")), ("Name_Aend3", (3, "name")),
               ("DATUM_AEND4", (4, "datum")), ("Stand_Index1", (1, "stand")), ("Bearb2", (2, "name"))):
    check(TB.parse_rev_tag(t) == erw, "Tag %s -> %s" % (t, TB.parse_rev_tag(t)))
check(TB.parse_rev_tag("NAME") is None and TB.parse_rev_tag("TEXT3") is None, "keine falschen Treffer")
print(ok, "Checks bestanden")
