# -*- coding: utf-8 -*-
"""
katiecad/reports/daten.py - Row data of the reports (NO Tkinter).

Each function returns a list of dicts (one dict per row). Values are
strings or lists of strings (several targets in one cell). Sheet keys
are 0-based indices of the drawing sheets; `nummer(idx)` returns the
displayed sheet number (it depends on how many report sheets precede it).
"""

from collections import defaultdict

from katiecad.model.core import ElektroMaske, ort_text
from katiecad.electrical.logic import (REF_FELD, geraete, felder_aus_elementen, feld_an,
                                       _pos)
from katiecad.reports.netz import (natuerlich, ziele_texte, ende_ziele,
                                   wert_gesetzt)


def _ort(nummer, idx, feld):
    return ort_text((nummer(idx), feld))


def _eo(einbauorte, idx):
    """Installation location of a sheet ('' if none)."""
    return str((einbauorte or {}).get(idx, "") or "").strip()


def _felder(blaetter):
    return {idx: felder_aus_elementen(el) for idx, el in blaetter}


# ------------------------------------------------------------------
# Device list
# ------------------------------------------------------------------
def _typ_per(obj):
    if isinstance(obj, ElektroMaske):
        w = obj.werte
        return (wert_gesetzt(w.get("TYP"), "TYP"),
                wert_gesetzt(w.get("PER"), "PER"))
    a = getattr(obj, "attribute", {}) or {}
    return wert_gesetzt(a.get("TYP"), "TYP"), wert_gesetzt(a.get("PER"), "PER")


def geraeteliste(blaetter, nummer, netz=None, klemmenleisten=True,
                 einbauorte=None):
    """One row per equipment identifier (IND). Main symbol and auxiliary
    parts with the same IND count as one device.
    Same IND at different installation locations (sheet property) = different
    devices.
    Rows: pos, ind, einbauort, typ, per, anzahl, orte (list), ort (text)."""
    gruppen = {}
    reihenfolge = []
    for idx, el in blaetter:
        for g in geraete(el, idx):
            if g["rolle"] == "kabel":
                continue
            ind = wert_gesetzt(g["per"], REF_FELD) if g["rolle"] != "kabel" else g["per"]
            eo = _eo(einbauorte, idx)
            schluessel = ("ind", eo, ind) if ind else ("ohne", id(g["obj"]))
            if schluessel not in gruppen:
                gruppen[schluessel] = {"ind": ind, "eo": eo, "typ": "", "per": "",
                                       "anzahl": 0, "orte": [], "haupt": None}
                reihenfolge.append(schluessel)
            z = gruppen[schluessel]
            typ, per = _typ_per(g["obj"])
            z["anzahl"] += 1
            z["orte"].append((g["rolle"] != "haupt", idx, g["feld"]))
            if g["rolle"] == "haupt" or z["haupt"] is None:
                z["haupt"] = g["rolle"]
                if typ or not z["typ"]:
                    z["typ"] = typ or z["typ"]
                if per or not z["per"]:
                    z["per"] = per or z["per"]
            else:
                z["typ"] = z["typ"] or typ
                z["per"] = z["per"] or per
    zeilen = []
    for s in reihenfolge:
        z = gruppen[s]
        orte = [_ort(nummer, i, f) for _h, i, f in sorted(z["orte"])]
        zeilen.append({"ind": z["ind"], "einbauort": z["eo"], "typ": z["typ"],
                       "per": z["per"], "anzahl": str(z["anzahl"]),
                       "orte": orte, "ort": ", ".join(orte)})
    if klemmenleisten and netz is not None:
        felder = _felder(blaetter)
        leisten = {}
        for kl in netz.klemmen:
            k = kl["obj"]
            kz = kl["leiste"]
            if not kz:
                continue
            eo = _eo(einbauorte, kl["blatt"])
            z = leisten.setdefault((eo, kz), {"ind": kz, "eo": eo, "typ": "",
                                              "per": "", "anzahl": 0,
                                              "orte": set()})
            z["anzahl"] += 1
            z["typ"] = z["typ"] or wert_gesetzt(k.werte.get("TYP"), "TYP")
            z["per"] = z["per"] or wert_gesetzt(k.werte.get("PER"), "PER")
            z["orte"].add((kl["blatt"], feld_an(felder.get(kl["blatt"], []),
                                                *_pos(k))))
        for (_eo_, kz), z in leisten.items():
            orte = [_ort(nummer, i, f) for i, f in sorted(z["orte"])]
            zeilen.append({"ind": kz, "einbauort": z["eo"], "typ": z["typ"],
                           "per": z["per"], "anzahl": str(z["anzahl"]),
                           "orte": orte, "ort": ", ".join(orte)})
    # Devices without identifier at the end, otherwise naturally sorted
    zeilen.sort(key=lambda r: (natuerlich(r["einbauort"]), r["ind"] == "",
                               natuerlich(r["ind"])))
    for i, z in enumerate(zeilen, 1):
        z["pos"] = str(i)
    return zeilen


# ------------------------------------------------------------------
# Terminal diagram
# ------------------------------------------------------------------
def klemmenplan(netz, blaetter, nummer, einbauorte=None):
    """One row per terminal, sorted by terminal strip (IND) and number (NUM).
    Rows: leiste, einbauort, num, typ, per, oben (list), unten (list), ort."""
    felder = _felder(blaetter)
    zeilen = []
    for kl in netz.klemmen:
        k = kl["obj"]
        w = k.werte
        eo = _eo(einbauorte, kl["blatt"])
        zeilen.append({
            "leiste": kl["leiste"], "einbauort": eo, "_gk": (eo, kl["leiste"]),
            "num": wert_gesetzt(w.get("NUM"), "NUM"),
            "typ": wert_gesetzt(w.get("TYP"), "TYP"),
            "per": wert_gesetzt(w.get("PER"), "PER"),
            "oben": ziele_texte(netz.ziele(kl["oben"]), kl["oben"].bes),
            "unten": ziele_texte(netz.ziele(kl["unten"]), kl["unten"].bes),
            "ort": _ort(nummer, kl["blatt"],
                        feld_an(felder.get(kl["blatt"], []), *_pos(k))),
            "_blatt": kl["blatt"], "_pos": _pos(k)})
    zeilen.sort(key=lambda r: (natuerlich(r["einbauort"]), r["leiste"] == "",
                               natuerlich(r["leiste"]),
                               natuerlich(r["num"]) if r["num"] else (),
                               r["_blatt"], -r["_pos"][1], r["_pos"][0]))
    return zeilen


# ------------------------------------------------------------------
# Cable plan
# ------------------------------------------------------------------
def kabelplan(netz, blaetter, nummer, einbauorte=None):
    """One row per core (or per cable without detected cores).
    Von = end above the cable (supply), Nach = end below.
    Rows: cab, einbauort, typ, ader, von (list), nach (list), ort."""
    felder = _felder(blaetter)
    nach_cab = defaultdict(list)
    for kb in netz.kabel:
        nach_cab[(kb["obj"].werte.get("CAB", "") or "").strip()].append(kb)
    zeilen = []
    for cab in sorted(nach_cab, key=lambda c: (c == "", natuerlich(c))):
        vorkommen = sorted(nach_cab[cab],
                           key=lambda kb: (natuerlich(_eo(einbauorte, kb["blatt"])),
                                           kb["blatt"], -kb["obj"].y, kb["obj"].x))
        for kb in vorkommen:
            obj = kb["obj"]
            eo = _eo(einbauorte, kb["blatt"])
            typ = (obj.werte.get("TYP", "") or "").strip()
            ort = _ort(nummer, kb["blatt"],
                       feld_an(felder.get(kb["blatt"], []), *_pos(obj)))
            adern = [a for a in kb["adern"] if a["kanten"]]
            if not adern:
                zeilen.append({"cab": cab, "einbauort": eo, "_gk": (cab, eo),
                               "typ": typ, "ader": "", "von": [],
                               "nach": [], "ort": ort})
                continue
            for a in adern:
                kante = a["kanten"][0]
                oben, unten = ((kante.a, kante.b) if kante.a.y >= kante.b.y
                               else (kante.b, kante.a))
                zeilen.append({
                    "cab": cab, "einbauort": eo, "_gk": (cab, eo),
                    "typ": typ, "ader": a["name"],
                    "von": ziele_texte(ende_ziele(netz, oben, kante)),
                    "nach": ziele_texte(ende_ziele(netz, unten, kante)),
                    "ort": ort})
    return zeilen


# ------------------------------------------------------------------
# Table of contents
# ------------------------------------------------------------------
def inhaltsverzeichnis(eintraege):
    """eintraege: [{"nr", "name", "beschreibung", "typ"}] -> rows."""
    return [{"nr": str(e["nr"]), "name": e.get("name", ""),
             "beschreibung": e.get("beschreibung", ""), "typ": e.get("typ", "")}
            for e in eintraege]
