# -*- coding: utf-8 -*-
"""
katiecad/reports/daten_listen.py - Further lists (NO Tkinter, MIT).

connection list, parts list (with parts catalogue), cross reference list,
potential overview, connector overview, label list, revision overview.
Same conventions as katiecad.reports.daten: each function returns a list
of dicts (strings or lists of strings); `nummer(idx)` = displayed sheet
number.
"""

import re

from katiecad.model.core import BlockReferenz, ort_text
from katiecad.electrical.logic import felder_aus_elementen, feld_an, _pos
from katiecad.reports.netz import (natuerlich, ziele_texte, knoten_text,
                                   wert_gesetzt)
from katiecad.reports import daten as D


def _felder(blaetter):
    return {idx: felder_aus_elementen(el) for idx, el in blaetter}


def _knoten_ort(felder, nummer, n):
    return ort_text((nummer(n.blatt), feld_an(felder.get(n.blatt, []), n.x, n.y)))


def _eo(einbauorte, idx):
    return str((einbauorte or {}).get(idx, "") or "").strip()


# ------------------------------------------------------------------
# Connection list
# ------------------------------------------------------------------
def _lauf_ziele(netz, n, kante):
    """Targets reachable from `n` along ONE edge only."""
    andere = [k for k in n.kanten if k is not kante]
    return netz.ziele(n, ohne=andere)


def verbindungsliste(netz, blaetter, nummer, einbauorte=None):
    """One row per point-to-point connection (pin/terminal to pin/terminal/
    potential). Nets with more than two end points are listed as a chain.
    Rows: pos, von, nach, kabel, ort, einbauort."""
    felder = _felder(blaetter)
    gesehen = set()
    paare = []
    for n in netz.knoten:
        if n.art not in ("pin", "klemme"):
            continue
        for kante in n.kanten:
            lauf = _lauf_ziele(netz, n, kante)
            ziele = [(m, v) for m, v in lauf if m.bes is not n.bes]
            if not ziele:
                continue
            ids = frozenset([id(n)] + [id(m) for m, _v in ziele])
            if ids in gesehen:
                continue
            gesehen.add(ids)
            via = {id(m): v for m, v in ziele}
            members = [n] + [m for m, _v in ziele]
            members.sort(key=lambda k: natuerlich(knoten_text(k)))
            for a, b in zip(members, members[1:]):
                v = via.get(id(b)) if a is n else via.get(id(a)) if b is n else ()
                paare.append((a, b, v or ()))
    zeilen = []
    for a, b, v in paare:
        kabel = " ".join(f"{c}/{ad}" if c else ad for c, ad in v)
        zeilen.append({"von": knoten_text(a), "nach": knoten_text(b),
                       "kabel": kabel, "ort": _knoten_ort(felder, nummer, a),
                       "einbauort": _eo(einbauorte, a.blatt)})
    zeilen.sort(key=lambda r: (natuerlich(r["einbauort"]), natuerlich(r["von"]),
                               natuerlich(r["nach"])))
    for i, z in enumerate(zeilen, 1):
        z["pos"] = str(i)
    return zeilen


# ------------------------------------------------------------------
# Parts catalogue and parts list
# ------------------------------------------------------------------
def katalog_dict(katalog):
    """[{typ, hersteller, bestellnr, beschreibung}] -> {TYP.upper(): entry}"""
    out = {}
    for e in katalog or []:
        if isinstance(e, dict) and str(e.get("typ", "")).strip():
            out[str(e["typ"]).strip().upper()] = e
    return out


def stueckliste(blaetter, nummer, netz, katalog=None, einbauorte=None):
    """Parts list: devices, single terminals and cables grouped by TYP.
    Manufacturer / order number / description come from the catalogue.
    Rows: pos, anzahl, typ, hersteller, bestellnr, beschreibung, kennzeichen."""
    kat = katalog_dict(katalog)
    gruppen, reihenfolge = {}, []

    def zaehle(typ, kennz):
        typ = (typ or "").strip()
        schl = typ.upper()
        if schl not in gruppen:
            gruppen[schl] = {"typ": typ, "n": 0, "kz": []}
            reihenfolge.append(schl)
        gruppen[schl]["n"] += 1
        if kennz:
            gruppen[schl]["kz"].append(kennz)

    for z in D.geraeteliste(blaetter, nummer, None, False, einbauorte):
        zaehle(z["typ"], z["ind"])
    if netz is not None:
        for kl in netz.klemmen:
            k = kl["obj"]
            nm = wert_gesetzt(k.werte.get("NUM"), "NUM")
            zaehle(wert_gesetzt(k.werte.get("TYP"), "TYP"),
                   (kl["leiste"] + ":" + nm) if kl["leiste"] and nm
                   else kl["leiste"] or nm)
        for kb in netz.kabel:
            w = kb["obj"].werte
            zaehle((w.get("TYP", "") or "").strip(), (w.get("CAB", "") or "").strip())
    zeilen = []
    for schl in reihenfolge:
        g = gruppen[schl]
        e = kat.get(schl, {})
        zeilen.append({"anzahl": str(g["n"]), "typ": g["typ"],
                       "hersteller": str(e.get("hersteller", "") or ""),
                       "bestellnr": str(e.get("bestellnr", "") or ""),
                       "beschreibung": str(e.get("beschreibung", "") or ""),
                       "kennzeichen": sorted(g["kz"], key=natuerlich)})
    zeilen.sort(key=lambda r: (r["typ"] == "", natuerlich(r["typ"])))
    for i, z in enumerate(zeilen, 1):
        z["pos"] = str(i)
    return zeilen


def typen_der_projekte(blaetter, nummer, netz):
    """All distinct TYP values of the project (for the catalogue dialog)."""
    typen = set()
    for z in D.geraeteliste(blaetter, nummer, None, False, None):
        if z["typ"].strip():
            typen.add(z["typ"].strip())
    if netz is not None:
        for kl in netz.klemmen:
            t = wert_gesetzt(kl["obj"].werte.get("TYP"), "TYP")
            if t:
                typen.add(t)
        for kb in netz.kabel:
            t = (kb["obj"].werte.get("TYP", "") or "").strip()
            if t:
                typen.add(t)
    return sorted(typen, key=natuerlich)


# ------------------------------------------------------------------
# Cross reference list
# ------------------------------------------------------------------
def querverweisliste(netz, blaetter, nummer):
    """One row per cross-reference name: where it leaves and where it arrives.
    Rows: name, abgehend (list), ankommend (list), anzahl."""
    felder = _felder(blaetter)
    gruppen = {}
    for n in netz.knoten:
        if n.art != "qv" or not n.text or n.qv_art == "extern":
            continue
        g = gruppen.setdefault(n.text, {"ab": [], "an": []})
        (g["ab"] if n.qv_art == "abgehend" else g["an"]).append(
            _knoten_ort(felder, nummer, n))
    zeilen = []
    for name in sorted(gruppen, key=natuerlich):
        g = gruppen[name]
        zeilen.append({"name": name, "abgehend": sorted(g["ab"], key=natuerlich),
                       "ankommend": sorted(g["an"], key=natuerlich),
                       "anzahl": str(len(g["ab"]) + len(g["an"]))})
    return zeilen


# ------------------------------------------------------------------
# Potential overview
# ------------------------------------------------------------------
def potenzialuebersicht(netz, blaetter, nummer):
    """Potentials = cross-reference names that are not resolved to a counterpart
    (L1, N, PE, +24V ...) with everything connected to them.
    Rows: potenzial, anzahl, anschluesse (list), orte (list)."""
    felder = _felder(blaetter)
    gruppen = {}
    for n in netz.knoten:
        if n.art == "qv" and n.text and not n.partner:
            gruppen.setdefault(n.text, []).append(n)
    zeilen = []
    for name in sorted(gruppen, key=natuerlich):
        ziele, orte = set(), set()
        for q in gruppen[name]:
            orte.add(_knoten_ort(felder, nummer, q))
            for t in ziele_texte([(m, v) for m, v in netz.ziele(q)
                                  if m.art != "qv"]):
                ziele.add(t)
        zeilen.append({"potenzial": name, "anzahl": str(len(ziele)),
                       "anschluesse": sorted(ziele, key=natuerlich),
                       "orte": sorted(orte, key=natuerlich)})
    return zeilen


# ------------------------------------------------------------------
# Connector overview
# ------------------------------------------------------------------
_STECKER_WORTE = ("stecker", "buchse", "connector", "plug", "socket")


def ist_stecker(kennz, typ=""):
    """Connector by designation (X5, -X5, +A1-X5 but not a terminal strip
    element) or by type text (Stecker, connector ...)."""
    k = re.sub(r"^[=+][^-]*", "", str(kennz or "").strip()).lstrip("-").upper()
    if k.startswith("X"):
        return True
    t = str(typ or "").lower()
    return any(w in t for w in _STECKER_WORTE)


def steckeruebersicht(netz, blaetter, nummer, einbauorte=None):
    """Pin assignment of all connectors (devices with pins whose designation
    starts with X or whose type is a connector).
    Rows: stecker, einbauort, pin, ziele (list), ort; `_gk` = group."""
    felder = _felder(blaetter)
    zeilen = []
    for n in netz.knoten:
        if n.art != "pin" or not n.kennz:
            continue
        a = getattr(n.bes, "attribute", None) or {}
        typ = str(a.get("TYP", "") or "") if isinstance(n.bes, BlockReferenz) else ""
        if not ist_stecker(n.kennz, typ):
            continue
        eo = _eo(einbauorte, n.blatt)
        zeilen.append({"stecker": n.kennz, "einbauort": eo, "_gk": (eo, n.kennz),
                       "pin": n.name or "?",
                       "ziele": ziele_texte(netz.ziele(n), n.bes),
                       "ort": _knoten_ort(felder, nummer, n)})
    zeilen.sort(key=lambda r: (natuerlich(r["einbauort"]), natuerlich(r["stecker"]),
                               natuerlich(r["pin"])))
    return zeilen


# ------------------------------------------------------------------
# Label list
# ------------------------------------------------------------------
def etikettenliste(blaetter, nummer, netz, einbauorte=None, art_namen=None):
    """All labels to be printed: devices, single terminals, cables.
    Rows: etikett, art, einbauort, typ, ort."""
    an = art_namen or {"geraet": "Gerät", "klemme": "Klemme", "kabel": "Kabel"}
    felder = _felder(blaetter)
    zeilen, gesehen = [], set()

    def neu(text, art, eo, typ, ort):
        schl = (text, art, eo)
        if text and schl not in gesehen:
            gesehen.add(schl)
            zeilen.append({"etikett": text, "art": an[art], "einbauort": eo,
                           "typ": typ, "ort": ort})

    for z in D.geraeteliste(blaetter, nummer, None, False, einbauorte):
        neu(z["ind"], "geraet", z["einbauort"], z["typ"], z["ort"])
    if netz is not None:
        for kl in netz.klemmen:
            k = kl["obj"]
            nm = wert_gesetzt(k.werte.get("NUM"), "NUM")
            text = (kl["leiste"] + ":" + nm) if kl["leiste"] and nm else nm
            neu(text, "klemme", _eo(einbauorte, kl["blatt"]),
                wert_gesetzt(k.werte.get("TYP"), "TYP"),
                ort_text((nummer(kl["blatt"]),
                          feld_an(felder.get(kl["blatt"], []), *_pos(k)))))
        for kb in netz.kabel:
            k = kb["obj"]
            neu((k.werte.get("CAB", "") or "").strip(), "kabel",
                _eo(einbauorte, kb["blatt"]), (k.werte.get("TYP", "") or "").strip(),
                ort_text((nummer(kb["blatt"]),
                          feld_an(felder.get(kb["blatt"], []), *_pos(k)))))
    reihenfolge = {an["geraet"]: 0, an["klemme"]: 1, an["kabel"]: 2}
    zeilen.sort(key=lambda r: (natuerlich(r["einbauort"]), reihenfolge[r["art"]],
                               natuerlich(r["etikett"])))
    return zeilen


# ------------------------------------------------------------------
# Revision overview
# ------------------------------------------------------------------
def revisionsuebersicht(projektdaten):
    """Rows of the revision table of the project (title block).
    Rows: stand, aenderung, name, datum. Empty rows are left out."""
    rev = (projektdaten or {}).get("rev")
    rev = rev if isinstance(rev, list) else []
    zeilen = []
    for r in rev:
        if not isinstance(r, dict):
            continue
        z = {k: str(r.get(k, "") or "").strip()
             for k in ("stand", "aenderung", "name", "datum")}
        if any(z.values()):
            zeilen.append(z)
    return zeilen

