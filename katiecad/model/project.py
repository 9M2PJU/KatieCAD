# -*- coding: utf-8 -*-
"""
katiecad/model/project.py - Project management (NO Tkinter).

A project is a folder containing
    <project name>.katieprj    project file (JSON: name, sheet list)
    Blatt_001.cadjson ...      one drawing file per sheet
    Bloecke/                   block files (*.katieblock) of the project

Each sheet is an ordinary KatieCAD drawing (model + layouts).
The displayed sheet number results from the order in the list
(001, 002, ...); the file names stay unchanged when re-ordering.
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
    """Error with a user-readable message."""


def name_pruefen(name):
    """Returns None if the name is usable as a folder/file name,
    otherwise an error code: 'leer' | 'zeichen' | 'ende' | 'reserviert'."""
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
    def __init__(self, name, datei, bericht=None, einbauort="", art="",
                 beschreibung=""):
        self.name = name
        # Kind of sheet for the table of contents ("" = circuit diagram) and
        # a free description of the sheet.
        self.art = str(art or "").strip()
        self.beschreibung = str(beschreibung or "").strip()
        # Installation location (e.g. "Verteiler UV1"): applies to every object
        # on this sheet; derived when needed (title block, lists), not copied.
        self.einbauort = str(einbauort or "").strip()
        self.datei = datei          # File name relative to the project folder
        # None = drawing sheet; otherwise type of a generated report sheet
        # ("deckblatt", "inhalt", "geraete", "klemmen", "kabel")
        self.bericht = bericht

    def to_dict(self):
        d = {"name": self.name, "datei": self.datei}
        if self.bericht:
            d["bericht"] = self.bericht
        if self.einbauort:
            d["einbauort"] = self.einbauort
        if self.art:
            d["art"] = self.art
        if self.beschreibung:
            d["beschreibung"] = self.beschreibung
        return d


class Projekt:
    def __init__(self, name, ordner, blaetter=None, aktiv=0, naechste_id=1,
                 daten=None, doku=None):
        self.name = name
        self.ordner = ordner
        self.blaetter = list(blaetter) if blaetter else []
        self.aktiv = aktiv
        self.naechste_id = naechste_id
        # Project data for cover sheet / title block (customer, order, ...)
        self.daten = dict(daten) if isinstance(daten, dict) else {}
        # Documentation settings (selected reports, template, ...)
        self.doku = dict(doku) if isinstance(doku, dict) else {}

    # ---- Paths --------------------------------------------------
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

    # ---- Create / load / save ----------------------------------
    @classmethod
    def erstellen(cls, name, basis_ordner):
        """Creates <basis_ordner>/<name>/ and writes the project file
        (with an empty sheet list). The caller creates the first sheet."""
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
                                      bd["datei"], bd.get("bericht") or None,
                                      bd.get("einbauort") or "",
                                      bd.get("art") or "",
                                      bd.get("beschreibung") or ""))
        p = cls(name, ordner, blaetter,
                aktiv=int(d.get("aktiv", 0) or 0),
                naechste_id=int(d.get("naechste_id", len(blaetter) + 1)),
                daten=d.get("daten"), doku=d.get("doku"))
        # The project file may be named differently than in the JSON (copied):
        # the file name takes precedence so that speichern() writes to the same place.
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
            "daten": self.daten,
            "doku": self.doku,
        })

    def umbenennen(self, neuer_name):
        """Renames the project: project file and - if the folder was previously
        named exactly like the project - the project folder too.
        -> True if the folder was renamed as well. Raises ProjektFehler
        ('leer'|'zeichen'|'ende'|'reserviert'|'existiert')."""
        neu = (neuer_name or "").strip()
        fehler = name_pruefen(neu)
        if fehler:
            raise ProjektFehler(fehler)
        alt = self.name
        if neu == alt:
            return False
        alte_datei = self.projektdatei
        ordner_neu = None
        if os.path.basename(os.path.normpath(self.ordner)) == alt:
            ordner_neu = os.path.join(os.path.dirname(os.path.normpath(self.ordner)), neu)
            if os.path.exists(ordner_neu) and neu.lower() != alt.lower():
                raise ProjektFehler("existiert")
        neue_datei = os.path.join(self.ordner, neu + PROJEKT_ENDUNG)
        if os.path.exists(neue_datei) and neu.lower() != alt.lower():
            raise ProjektFehler("existiert")
        try:
            if os.path.exists(alte_datei):
                os.replace(alte_datei, neue_datei)
            self.name = neu
            self.speichern()
            if ordner_neu:
                os.rename(self.ordner, ordner_neu)
                self.ordner = ordner_neu
                return True
        except OSError as e:
            if ordner_neu is None or self.ordner != ordner_neu:
                # Folder stayed unchanged; the project is renamed anyway
                return False
            raise ProjektFehler(str(e))
        return False

    # ---- Sheets ------------------------------------------------
    def neuer_blattname(self):
        i = len(self.blaetter) + 1
        namen = {b.name for b in self.blaetter}
        while f"Blatt {i}" in namen:
            i += 1
        return f"Blatt {i}"

    def blatt_hinzufuegen(self, name=None, nach_index=None):
        """Registers a new sheet (the caller writes the file)."""
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

    # ---- Report sheets (generated lists, cover sheet, ...) -----
    def zeichnungsblaetter(self):
        """Indices of the sheets that are NOT generated report sheets."""
        return [i for i, b in enumerate(self.blaetter) if not b.bericht]

    def berichte_entfernen(self):
        """Removes all report sheets including their files. -> count."""
        weg = [b for b in self.blaetter if b.bericht]
        for b in weg:
            self.blaetter.remove(b)
            try:
                os.remove(os.path.join(self.ordner, b.datei))
            except OSError:
                pass
        if self.aktiv >= len(self.blaetter):
            self.aktiv = max(0, len(self.blaetter) - 1)
        return len(weg)

    def bericht_einfuegen(self, name, typ, position=None):
        """Registers a report sheet at `position` (None = at the end).
        The caller writes the file."""
        b = self.blatt_hinzufuegen(name)
        self.blaetter.remove(b)
        b.bericht = typ
        if position is None or position >= len(self.blaetter):
            self.blaetter.append(b)
        else:
            self.blaetter.insert(max(0, position), b)
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
        b.einbauort = self.blaetter[index].einbauort
        b.art = self.blaetter[index].art
        b.beschreibung = self.blaetter[index].beschreibung
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
        """Returns the new index (or the old one if not possible)."""
        neu = index + delta
        if not (0 <= index < len(self.blaetter)) or \
                not (0 <= neu < len(self.blaetter)):
            return index
        self.blaetter[index], self.blaetter[neu] = \
            self.blaetter[neu], self.blaetter[index]
        return neu

    # ---- Deletion ----------------------------------------------
    def loeschen(self):
        """Deletes the project file, sheet files and block files of the project.
        Foreign files in the folder are left untouched. The folder is only
        removed if it is empty afterwards.
        Returns: (folder_removed: bool, remaining: list[str])"""
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
