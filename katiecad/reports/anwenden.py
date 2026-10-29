# -*- coding: utf-8 -*-
"""
katiecad/reports/anwenden.py - Write report sheets into the project and
export lists (NO Tkinter).
"""

import csv
import os

from katiecad.model.core import Layout
from katiecad.reports.seiten import FORMAT


def blatt_daten(basis, seite, bg_layout=None):
    """Drawing data (dict for the .cadjson file) of a report sheet:
    empty model, one A4 layout with the content, view = layout."""
    d = dict(basis)
    fmt = getattr(seite, "format", FORMAT)
    lay = Layout("Layout1", fmt, bg_layout or d.get("bg_layout"),
                 list(seite.elemente))
    d["layout_format"] = fmt
    d["elemente"] = []
    d["layouts"] = [lay.to_dict()]
    d["aktives_layout"] = 0
    d["ansicht"] = "layout:0"
    return d


def ins_projekt(projekt, vorne, hinten, basis, schreiben, bg_layout=None):
    """Replaces all report sheets of the project.

    vorne/hinten: BerichtSeite lists (before / after the drawing sheets)
    basis:        base data of an empty drawing (layers, unit, ...)
    schreiben:    function (path, data) -> None, writes the sheet file
    The active-sheet pointer stays on the previous drawing sheet.
    -> index of the active sheet after the rebuild."""
    aktiv = (projekt.blaetter[projekt.aktiv]
             if 0 <= projekt.aktiv < len(projekt.blaetter) else None)
    if aktiv is not None and aktiv.bericht:
        aktiv = None
    projekt.berichte_entfernen()
    pos = 0
    for seite in vorne:
        b = projekt.bericht_einfuegen(seite.name, seite.typ, pos)
        schreiben(projekt.blatt_pfad(b), blatt_daten(basis, seite, bg_layout))
        pos += 1
    for seite in hinten:
        b = projekt.bericht_einfuegen(seite.name, seite.typ, None)
        schreiben(projekt.blatt_pfad(b), blatt_daten(basis, seite, bg_layout))
    if aktiv is not None and aktiv in projekt.blaetter:
        projekt.aktiv = projekt.blaetter.index(aktiv)
    else:
        z = projekt.zeichnungsblaetter()
        projekt.aktiv = z[0] if z else 0
    return projekt.aktiv


def zelle(wert):
    if isinstance(wert, (list, tuple)):
        return ", ".join(str(w) for w in wert)
    return "" if wert is None else str(wert)


def csv_schreiben(pfad, spalten, zeilen):
    """CSV for Excel (semicolon, UTF-8 with BOM)."""
    with open(pfad, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([s.titel for s in spalten])
        for z in zeilen:
            w.writerow([zelle(z.get(s.key, "")) for s in spalten])


def csv_exportieren(ordner, tabellen, namen):
    """tabellen: {type: (columns, rows)}, namen: {type: file name without .csv}.
    -> list of the paths written."""
    os.makedirs(ordner, exist_ok=True)
    out = []
    for typ, (spalten, zeilen) in tabellen.items():
        pfad = os.path.join(ordner, namen.get(typ, typ) + ".csv")
        csv_schreiben(pfad, spalten, zeilen)
        out.append(pfad)
    return out


def xlsx_exportieren(pfad, tabellen, namen, auswahl=None):
    """All (or the chosen) lists into ONE Excel workbook, one sheet per list.
    tabellen: {type: (columns, rows)}, namen: {type: sheet name}, auswahl: list of types.
    -> list of the sheet names written."""
    from katiecad.reports.xlsx import xlsx_schreiben
    blaetter = []
    for typ, (spalten, zeilen) in tabellen.items():
        if auswahl is not None and typ not in auswahl:
            continue
        sp = [(s.titel, s.key, s.ausr == "r") for s in spalten]
        blaetter.append((namen.get(typ, typ), sp, zeilen))
    return xlsx_schreiben(pfad, blaetter)
