# -*- coding: utf-8 -*-
"""
katiecad/reports/anwenden.py - Berichtsblaetter ins Projekt schreiben und
Listen exportieren (KEIN Tkinter).
"""

import csv
import os

from katiecad.model.core import Layout
from katiecad.reports.seiten import FORMAT


def blatt_daten(basis, seite, bg_layout=None):
    """Zeichnungsdaten (Dict fuer die .cadjson-Datei) eines Berichtsblatts:
    leeres Modell, ein A4-Layout mit dem Inhalt, Ansicht = Layout."""
    d = dict(basis)
    lay = Layout("Layout1", FORMAT, bg_layout or d.get("bg_layout"),
                 list(seite.elemente))
    d["layout_format"] = FORMAT
    d["elemente"] = []
    d["layouts"] = [lay.to_dict()]
    d["aktives_layout"] = 0
    d["ansicht"] = "layout:0"
    return d


def ins_projekt(projekt, vorne, hinten, basis, schreiben, bg_layout=None):
    """Ersetzt alle Berichtsblaetter des Projekts.

    vorne/hinten: BerichtSeite-Listen (vor bzw. nach den Zeichnungsblaettern)
    basis:        Grunddaten einer leeren Zeichnung (Layer, Einheit, ...)
    schreiben:    Funktion (pfad, daten) -> None, schreibt die Blattdatei
    Der aktive Blatt-Zeiger bleibt auf dem bisherigen Zeichnungsblatt.
    -> Index des aktiven Blatts nach dem Umbau."""
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
    """CSV fuer Excel (Semikolon, UTF-8 mit BOM)."""
    with open(pfad, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([s.titel for s in spalten])
        for z in zeilen:
            w.writerow([zelle(z.get(s.key, "")) for s in spalten])


def csv_exportieren(ordner, tabellen, namen):
    """tabellen: {typ: (spalten, zeilen)}, namen: {typ: Dateiname ohne .csv}.
    -> Liste der geschriebenen Pfade."""
    os.makedirs(ordner, exist_ok=True)
    out = []
    for typ, (spalten, zeilen) in tabellen.items():
        pfad = os.path.join(ordner, namen.get(typ, typ) + ".csv")
        csv_schreiben(pfad, spalten, zeilen)
        out.append(pfad)
    return out
