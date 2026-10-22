# -*- coding: utf-8 -*-
"""
katiecad/model/project.py - Projektverwaltung (KEIN Tkinter).

Ein Projekt ist ein Ordner mit
    <Projektname>.katieprj     Projektdatei (JSON: Name, Blattliste)
    Blatt_001.cadjson ...      je Blatt eine Zeichnungsdatei
    Bloecke/                   Blockdateien (*.katieblock) des Projekts

Jedes Blatt ist eine normale KatieCAD-Zeichnung (Modell + Layouts).
Die angezeigte Blattnummer ergibt sich aus der Reihenfolge in der Liste
(001, 002, ...); die Dateinamen bleiben beim Umsortieren unveraendert.
"""

import json
import os
import re

PROJEKT_ENDUNG = ".katieprj"
BLATT_ENDUNG = ".cadjson"
BLOCK_ENDUNG = ".katieblock"
BLOCK_ORDNER = "Bloecke"
FORMAT_KENNUNG = "katiecad-projekt"
FORMAT_VERSION = 1

_UNGUELTIG = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVIERT = {"CON", "PRN", "AUX", "NUL",
               *{f"COM{i}" for i in range(1, 10)},
               *{f"LPT{i}" for i in range(1, 10)}}


class ProjektFehler(Exception):
    """Fehler mit anwenderlesbarer Meldung."""


def name_pruefen(name):
    """Gibt None zurueck, wenn der Name als Ordner-/Dateiname taugt,
    sonst einen Fehlercode: 'leer' | 'zeichen' | 'ende' | 'reserviert'."""
    n = (name or "").strip()
    if not n:
        return "leer"
    if _UNGUELTIG.search(n):
        return "zeichen"
    if n.endswith(".") or n.endswith(" "):
        return "ende"
    if n.split(".")[0].upper() in _RESERVIERT:
        return "reserviert"
    return None


def _json_schreiben(pfad, daten):
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)
    os.replace(tmp, pfad)


class Blatt:
    def __init__(self, name, datei):
        self.name = name
        self.datei = datei          # Dateiname relativ zum Projektordner

    def to_dict(self):
        return {"name": self.name, "datei": self.datei}


class Projekt:
    def __init__(self, name, ordner, blaetter=None, aktiv=0, naechste_id=1):
        self.name = name
        self.ordner = ordner
        self.blaetter = list(blaetter) if blaetter else []
        self.aktiv = aktiv
        self.naechste_id = naechste_id

    # ---- Pfade --------------------------------------------------
    @property
    def projektdatei(self):
        return os.path.join(self.ordner, self.name + PROJEKT_ENDUNG)

    @property
    def bloecke_ordner(self):
        return os.path.join(self.ordner, BLOCK_ORDNER)

    def blatt_pfad(self, blatt_oder_index):
        b = (self.blaetter[blatt_oder_index]
             if isinstance(blatt_oder_index, int) else blatt_oder_index)
        return os.path.join(self.ordner, b.datei)

    @staticmethod
    def nummer(index):
        return f"{index + 1:03d}"

    # ---- Anlegen / Laden / Speichern ---------------------------
    @classmethod
    def erstellen(cls, name, basis_ordner):
        """Legt <basis_ordner>/<name>/ an und schreibt die Projektdatei
        (mit leerer Blattliste). Das erste Blatt legt der Aufrufer an."""
        name = (name or "").strip()
        fehler = name_pruefen(name)
        if fehler:
            raise ProjektFehler(fehler)
        if not basis_ordner or not os.path.isdir(basis_ordner):
            raise ProjektFehler("basis_fehlt")
        ordner = os.path.join(basis_ordner, name)
        if os.path.exists(ordner) and (not os.path.isdir(ordner)
                                       or os.listdir(ordner)):
            raise ProjektFehler("ordner_existiert")
        try:
            os.makedirs(ordner, exist_ok=True)
        except OSError as e:
            raise ProjektFehler(str(e))
        p = cls(name, ordner)
        p.speichern()
        return p

    @classmethod
    def laden(cls, pfad):
        try:
            with open(pfad, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            raise ProjektFehler(str(e))
        if not isinstance(d, dict) or d.get("format") != FORMAT_KENNUNG:
            raise ProjektFehler("kein_projekt")
        ordner = os.path.dirname(os.path.abspath(pfad))
        name = d.get("name") or os.path.splitext(os.path.basename(pfad))[0]
        blaetter = []
        for bd in d.get("blaetter", []):
            if isinstance(bd, dict) and bd.get("datei"):
                blaetter.append(Blatt(bd.get("name") or bd["datei"],
                                      bd["datei"]))
        p = cls(name, ordner, blaetter,
                aktiv=int(d.get("aktiv", 0) or 0),
                naechste_id=int(d.get("naechste_id", len(blaetter) + 1)))
        # Die Projektdatei heisst evtl. anders als im JSON (umkopiert):
        # der Dateiname hat Vorrang, damit speichern() am selben Ort schreibt.
        p.name = os.path.splitext(os.path.basename(pfad))[0]
        if not (0 <= p.aktiv < len(p.blaetter)):
            p.aktiv = 0
        return p

    def speichern(self):
        os.makedirs(self.ordner, exist_ok=True)
        _json_schreiben(self.projektdatei, {
            "format": FORMAT_KENNUNG,
            "version": FORMAT_VERSION,
            "name": self.name,
            "aktiv": self.aktiv,
            "naechste_id": self.naechste_id,
            "blaetter": [b.to_dict() for b in self.blaetter],
        })

    # ---- Blaetter ----------------------------------------------
    def neuer_blattname(self):
        i = len(self.blaetter) + 1
        namen = {b.name for b in self.blaetter}
        while f"Blatt {i}" in namen:
            i += 1
        return f"Blatt {i}"

    def blatt_hinzufuegen(self, name=None, nach_index=None):
        """Registriert ein neues Blatt (Datei schreibt der Aufrufer)."""
        name = (name or "").strip() or self.neuer_blattname()
        while True:
            datei = f"Blatt_{self.naechste_id:03d}{BLATT_ENDUNG}"
            self.naechste_id += 1
            if not os.path.exists(os.path.join(self.ordner, datei)):
                break
        b = Blatt(name, datei)
        if nach_index is None or nach_index >= len(self.blaetter) - 1:
            self.blaetter.append(b)
        else:
            self.blaetter.insert(nach_index + 1, b)
        return b

    def kopie_name(self, name):
        """Free name for a copy: 'X (Kopie)', 'X (Kopie 2)', ..."""
        namen = {b.name for b in self.blaetter}
        kandidat = f"{name} (Kopie)"
        i = 2
        while kandidat in namen:
            kandidat = f"{name} (Kopie {i})"
            i += 1
        return kandidat

    def blatt_duplizieren(self, index, name=None):
        """Copies sheet `index` completely (the file is copied; the caller
        must have saved the sheet before). The copy is inserted directly
        after the original. Returns the new Blatt."""
        import shutil
        if not (0 <= index < len(self.blaetter)):
            raise ProjektFehler("invalid sheet")
        quelle = self.blatt_pfad(index)
        if not os.path.isfile(quelle):
            raise ProjektFehler(f"sheet file missing: {quelle}")
        name = (name or "").strip() or self.kopie_name(self.blaetter[index].name)
        b = self.blatt_hinzufuegen(name, nach_index=index)
        try:
            shutil.copy2(quelle, self.blatt_pfad(b))
        except OSError:
            self.blaetter.remove(b)
            raise
        return b

    def blatt_entfernen(self, index, datei_loeschen=True):
        b = self.blaetter.pop(index)
        if datei_loeschen:
            try:
                os.remove(os.path.join(self.ordner, b.datei))
            except OSError:
                pass
        if self.aktiv >= len(self.blaetter):
            self.aktiv = max(0, len(self.blaetter) - 1)
        return b

    def blatt_verschieben(self, index, delta):
        """Gibt den neuen Index zurueck (oder den alten, wenn nicht moeglich)."""
        neu = index + delta
        if not (0 <= index < len(self.blaetter)) or \
                not (0 <= neu < len(self.blaetter)):
            return index
        self.blaetter[index], self.blaetter[neu] = \
            self.blaetter[neu], self.blaetter[index]
        return neu

    # ---- Loeschen ----------------------------------------------
    def loeschen(self):
        """Loescht Projektdatei, Blattdateien und Blockdateien des Projekts.
        Fremde Dateien im Ordner bleiben unangetastet. Der Ordner wird nur
        entfernt, wenn er danach leer ist.
        Rueckgabe: (ordner_entfernt: bool, uebrig: list[str])"""
        ziele = [self.projektdatei, self.projektdatei + ".tmp"]
        ziele += [self.blatt_pfad(b) for b in self.blaetter]
        for z in ziele:
            try:
                os.remove(z)
            except OSError:
                pass
        bo = self.bloecke_ordner
        if os.path.isdir(bo):
            for fn in os.listdir(bo):
                if fn.lower().endswith(BLOCK_ENDUNG):
                    try:
                        os.remove(os.path.join(bo, fn))
                    except OSError:
                        pass
            try:
                os.rmdir(bo)
            except OSError:
                pass
        try:
            os.rmdir(self.ordner)
            return True, []
        except OSError:
            try:
                return False, sorted(os.listdir(self.ordner))
            except OSError:
                return False, []

