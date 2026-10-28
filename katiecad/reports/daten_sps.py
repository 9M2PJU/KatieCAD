# -*- coding: utf-8 -*-
"""
katiecad/reports/daten_sps.py - PLC (SPS) I/O list (NO Tkinter, MIT).

A device is a PLC module if its block carries the attribute `SPS` with one
of CPU / DI / DO / AI / AO (the symbols of the category "10 PLC" do).
Further module attributes: STATION (controller), PLATZ (slot).
Per channel (pin with tag VPn) the attributes VPn_SYM (symbol name) and
VPn_KOM (comment) can be filled in; the pin text is the channel address.
"""

from katiecad.model.core import BlockReferenz, Verbindungspunkt, ort_text
from katiecad.electrical.logic import felder_aus_elementen, feld_an, _pos
from katiecad.reports.netz import natuerlich, ziele_texte, wert_gesetzt

ARTEN = ("DI", "DO", "AI", "AO")
DATENTYP = {"DI": "BOOL", "DO": "BOOL", "AI": "INT", "AO": "INT"}
SPS_TAG, STATION_TAG, PLATZ_TAG = "SPS", "STATION", "PLATZ"


def sps_art(block):
    """'CPU' / 'DI' / 'DO' / 'AI' / 'AO' or '' (not a PLC module)."""
    a = str((getattr(block, "attribute", None) or {}).get(SPS_TAG, "")).strip().upper()
    return a if a in ARTEN + ("CPU",) else ""


def kanaele(block):
    """Channel pins of a module: pins with VPn_SYM / VPn_KOM definitions,
    otherwise all pins."""
    pins = [e for e in block.elemente if isinstance(e, Verbindungspunkt)]
    tags = {getattr(e, "tag", "") for e in block.elemente}
    mit = [p for p in pins if p.tag + "_SYM" in tags or p.tag + "_KOM" in tags]
    return mit or pins


def sps_liste(netz, blaetter, nummer, einbauorte=None):
    """One row per channel of all I/O modules.
    Rows: station, baugruppe, platz, art, adresse, datentyp, symbol,
    kommentar, anschluss (list), ort, einbauort; `_gk` = group."""
    zeilen = []
    for idx, el in blaetter:
        felder = felder_aus_elementen(el)
        eo = str((einbauorte or {}).get(idx, "") or "").strip()
        for b in el:
            if not isinstance(b, BlockReferenz):
                continue
            art = sps_art(b)
            if art not in ARTEN:
                continue
            a = b.attribute
            ind = wert_gesetzt(a.get("IND"), "IND")
            station = str(a.get(STATION_TAG, "") or "").strip()
            platz = str(a.get(PLATZ_TAG, "") or "").strip()
            knoten = {}
            if netz is not None:
                for n in netz.knoten:
                    if n.art == "pin" and n.bes is b:
                        knoten.setdefault(n.name, n)
            for p in kanaele(b):
                adr = str(a.get(p.tag, p.wert) or "").strip()
                n = knoten.get(adr)
                ziele = ziele_texte(netz.ziele(n), b) if (n is not None and netz) else []
                zeilen.append({
                    "station": station, "baugruppe": ind, "platz": platz,
                    "art": art, "adresse": adr, "datentyp": DATENTYP[art],
                    "symbol": str(a.get(p.tag + "_SYM", "") or "").strip(),
                    "kommentar": str(a.get(p.tag + "_KOM", "") or "").strip(),
                    "anschluss": ziele, "einbauort": eo,
                    "ort": ort_text((nummer(idx), feld_an(felder, *_pos(b)))),
                    "_gk": (eo, station, ind), "_x": _pos(b)[0]})
    zeilen.sort(key=lambda r: (natuerlich(r["einbauort"]), natuerlich(r["station"]),
                               natuerlich(r["platz"]), natuerlich(r["baugruppe"]),
                               natuerlich(r["adresse"])))
    for z in zeilen:
        z.pop("_x", None)
    return zeilen
