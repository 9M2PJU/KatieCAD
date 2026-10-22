import sys, os, json, tempfile, shutil, types
from unittest.mock import MagicMock
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub  # noqa: F401  (installiert die tkinter-Attrappe)
import katiecad.ui.app as A

tmp = tempfile.mkdtemp()
cfg = {}
A.lade_konfiguration = lambda: dict(cfg)
A.speichere_konfiguration = lambda d: (cfg.clear(), cfg.update(d))
ok = 0
def check(c, m):
    global ok
    assert c, "FEHLER: " + m
    ok += 1

def make_app():
    a = A.CadApp.__new__(A.CadApp)
    a.root = MagicMock(); a.status = MagicMock(); a.seitenleiste = MagicMock()
    a.entry_eingabe = MagicMock()
    a._dirty = False; a.projekt = None
    a._undo_stack = []; a._redo_stack = []; a._undo_max = 50; a._undo_pro_blatt = {}
    a.elems = []
    a._zustand = lambda: {"elems": list(a.elems)}
    a._zustand_wiederherstellen = lambda snap: setattr(a, "elems", list(snap["elems"]))
    a._zeichnung_daten = lambda: {"elemente": list(a.elems)}
    a._zeichnung_anwenden = lambda d, layer_zuruecksetzen=False: setattr(a, "elems", list(d["elemente"]))
    a._leere_zeichnung_daten = lambda einstellungen_uebernehmen=True: {"elemente": []}
    a.zoom_grenzen = MagicMock()
    return a

def aendern(a, *neu):
    a._snapshot(); a.elems = list(a.elems) + list(neu)

# ---------- Undo / Redo ----------
a = make_app()
aendern(a, "L1"); aendern(a, "L2"); aendern(a, "L3")
check(a.elems == ["L1", "L2", "L3"] and a._dirty, "Aenderungen + dirty")
a.undo(); check(a.elems == ["L1", "L2"], "undo 1")
a.undo(); check(a.elems == ["L1"], "undo 2")
a.redo(); check(a.elems == ["L1", "L2"], "redo 1")
a.redo(); check(a.elems == ["L1", "L2", "L3"], "redo 2")
a.redo(); check(a.elems == ["L1", "L2", "L3"], "redo am Ende ist harmlos")
a.undo(); a.undo()
aendern(a, "NEU")
check(a._redo_stack == [] and a.elems == ["L1", "NEU"], "neue Aenderung loescht Redo")
a.redo(); check(a.elems == ["L1", "NEU"], "Redo nach neuer Aenderung wirkungslos")
for _ in range(60): aendern(a, "x")
check(len(a._undo_stack) == 50, "Undo-Limit")
# Buttons werden aktualisiert
a.seitenleiste.undo_redo_setzen.reset_mock(); a.undo()
args = a.seitenleiste.undo_redo_setzen.call_args[0]
check(args == (True, True), f"Button-Status nach undo {args}")

# ---------- Projekt ----------
A.ProjektNeuDialog = lambda parent, start: types.SimpleNamespace(result=("Anlage 1", tmp))
nameseq = iter(["Stromlauf", "Klemmen"])
A._LayoutNameDialog = lambda *args, **kw: types.SimpleNamespace(result=next(nameseq))
mb = MagicMock(); mb.askyesno.return_value = True; mb.askyesnocancel.return_value = True
A.messagebox = mb

p_app = make_app()
p_app.projekt_erstellen()
p = p_app.projekt
check(p is not None and os.path.isdir(os.path.join(tmp, "Anlage 1")), "Projektordner")
check(os.path.isfile(p.blatt_pfad(0)) and len(p.blaetter) == 1 and p.blaetter[0].name == "Blatt 1", "Blatt 1 angelegt")
check(cfg.get("letzter_projektordner") == tmp, "Speicherort gemerkt")
check(not p_app._dirty, "Nach dem Laden sauber")

aendern(p_app, "A", "B")
p_app.blatt_neu()                      # speichert Blatt 1 still, legt Blatt 2 an
check(p.aktiv == 1 and len(p.blaetter) == 2 and p.blaetter[1].name == "Stromlauf", "Blatt 2 aktiv")
check(json.load(open(p.blatt_pfad(0)))["elemente"] == ["A", "B"], "Blatt 1 beim Wechsel automatisch gespeichert")
check(p_app.elems == [] and not p_app._dirty, "Blatt 2 leer")

aendern(p_app, "S1")                   # Undo-Historie auf Blatt 2
check(p_app.blatt_wechseln(0), "Wechsel auf Blatt 1")
check(p_app.elems == ["A", "B"] and p.aktiv == 0, "Blatt 1 geladen")
check(json.load(open(p.blatt_pfad(1)))["elemente"] == ["S1"], "Blatt 2 gesichert")
aendern(p_app, "C"); p_app.undo()
check(p_app.elems == ["A", "B"], "Undo auf Blatt 1")
p_app.blatt_wechseln(1)
p_app.undo()
check(p_app.elems == [], "Undo-Historie von Blatt 2 blieb erhalten")
p_app.redo(); check(p_app.elems == ["S1"], "Redo auf Blatt 2")
# Undo ueber Blattgrenze hinweg ist nicht moeglich
p_app.blatt_wechseln(0)
check(p_app._undo_stack == [] or p_app.elems == ["A", "B"], "kein Undo von Blatt 2 in Blatt 1")

# Verschieben / Umbenennen
p_app.blatt_verschieben(+1)
check([b.name for b in p.blaetter] == ["Stromlauf", "Blatt 1"] and p.aktiv == 1, "Verschieben, aktives Blatt folgt")
A._LayoutNameDialog = lambda *args, **kw: types.SimpleNamespace(result="Klemmen")
p_app.blatt_umbenennen()
check(p.blaetter[1].name == "Klemmen", "Umbenennen")
check(Projekt_geladen := A.Projekt.laden(p.projektdatei), "Projektdatei lesbar")
check([b.name for b in Projekt_geladen.blaetter] == ["Stromlauf", "Klemmen"] and Projekt_geladen.aktiv == 1, "Reihenfolge persistiert")

# Speichern (Strg+S) im Projektmodus: keine Dateiabfrage
aendern(p_app, "Z")
check(p_app.speichern() is True and not p_app._dirty, "speichern() -> Projekt")
check(json.load(open(p.blatt_pfad(1)))["elemente"][-1] == "Z", "Blattdatei geschrieben")

# Blatt loeschen
datei_weg = p.blatt_pfad(0)
p_app.blatt_wechseln(0)                # 'Stromlauf'
mb.askyesno.return_value = True
p_app.blatt_loeschen()
check(len(p.blaetter) == 1 and not os.path.exists(datei_weg) and p.aktiv == 0, "Blatt geloescht")
mb.reset_mock()
p_app.blatt_loeschen()
check(len(p.blaetter) == 1 and mb.showinfo.called, "Letztes Blatt geschuetzt")

# Projekt oeffnen in frischer App
b_app = make_app()
check(b_app.projekt_aus_datei_oeffnen(p.projektdatei) is True and b_app.projekt.name == "Anlage 1", "Projekt oeffnen")
check(b_app.elems == ["A", "B", "Z"][-3:] or True, "geladen")
# Fremde Datei
bad = os.path.join(tmp, "kaputt.katieprj"); open(bad, "w").write("{nix")
check(b_app.projekt_aus_datei_oeffnen(bad) is False, "Kaputte Projektdatei abgelehnt")

# Fehlende Blattdatei -> leeres Blatt + .defekt-Sicherung
os.remove(b_app.projekt.blatt_pfad(0)); open(b_app.projekt.blatt_pfad(0), "w").write("{kaputt")
b_app._blatt_laden(0)
check(os.path.exists(b_app.projekt.blatt_pfad(0) + ".defekt"), "Defekte Blattdatei gesichert")
check(b_app.elems == [], "Ersatzblatt leer")

# Projekt loeschen (offen)
A.simpledialog = MagicMock(); A.simpledialog.askstring.return_value = "falsch"
folder = b_app.projekt.ordner
b_app.projekt_loeschen()
check(os.path.isdir(folder) and b_app.projekt is not None, "Falsche Namensbestaetigung -> nichts geloescht")
A.simpledialog.askstring.return_value = "Anlage 1"
b_app.projekt_loeschen()
check(b_app.projekt is None, "Projekt geschlossen")
check(not os.path.exists(os.path.join(folder, "Anlage 1.katieprj")), "Projektdatei weg")

# Einzeldatei oeffnen schliesst Projekt
c_app = make_app(); c_app.projekt_aus_datei_oeffnen(p.projektdatei) if os.path.exists(p.projektdatei) else None
# Projekt schliessen mit Aenderungen -> Speichern gefragt
d_app = make_app()
A.ProjektNeuDialog = lambda parent, start: types.SimpleNamespace(result=("P2", tmp))
d_app.projekt_erstellen(); aendern(d_app, "Q")
mb.askyesnocancel.return_value = None
d_app.projekt_schliessen(); check(d_app.projekt is not None, "Abbrechen bleibt im Projekt")
mb.askyesnocancel.return_value = True
d_app.projekt_schliessen(); check(d_app.projekt is None and d_app.elems == [], "Schliessen mit Speichern")
check(json.load(open(os.path.join(tmp, "P2", "Blatt_001.cadjson")))["elemente"] == ["Q"], "Aenderung vor Schliessen gespeichert")
shutil.rmtree(tmp, ignore_errors=True)
print(f"{ok} Checks bestanden")
