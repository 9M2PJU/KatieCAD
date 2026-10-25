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
from katiecad.reports.netz import (natuerlich, ziele_texte, ende_ziele, knoten_text,
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
    Rows: leiste, einbauort, num, typ, per, oben (list), unten (list), ort.

    Terminals of the same strip whose top (or bottom) sides are wired
    directly together form a BRIDGE group: only its first terminal lists the
    targets on that side, and the rows carry `_bruecke` = [(lane, dot, up,
    down)] for the bridge graphic."""
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
            "ort": _ort(nummer, kl["blatt"],
                        feld_an(felder.get(kl["blatt"], []), *_pos(k))),
            "_blatt": kl["blatt"], "_pos": _pos(k), "_kl": kl})
    zeilen.sort(key=lambda r: (natuerlich(r["einbauort"]), r["leiste"] == "",
                               natuerlich(r["leiste"]),
                               natuerlich(r["num"]) if r["num"] else (),
                               r["_blatt"], -r["_pos"][1], r["_pos"][0]))
    _bruecken(netz, zeilen)
    for z in zeilen:
        z.pop("_kl", None)
    return zeilen


def _potential(treffer, num):
    """Name of the potential (PE, N, ...) if the net reaches a free pin or a
    cross reference carrying exactly the terminal's name - then only that
    name is shown instead of every terminal/device on the rail."""
    num = (num or "").strip()
    if not num:
        return ""
    for n, _via in treffer:
        if n.art == "klemme":
            continue
        if n.art == "qv":
            name = n.text.strip()
        else:
            name = knoten_text(n).strip()      # 'PE' (symbol or free pin)
        if name.upper() == num.upper():
            return name
    return ""


def _bruecken(netz, zeilen):
    """Fills oben / unten / bruecke / _bruecke of the terminal rows."""
    nach_obj = {id(z["_kl"]["obj"]): i for i, z in enumerate(zeilen)}
    treffer = {}
    gruppen = []                        # [(seite, [row indices])]
    for seite in ("oben", "unten"):
        eltern = list(range(len(zeilen)))

        def wurzel(i):
            while eltern[i] != i:
                eltern[i] = eltern[eltern[i]]
                i = eltern[i]
            return i

        for i, z in enumerate(zeilen):
            node = z["_kl"][seite]
            t = netz.ziele(node)
            treffer[(i, seite)] = (node, t)
            for n, _via in t:
                j = nach_obj.get(id(n.bes)) if n.art == "klemme" else None
                if (j is not None and j != i and n.seite == seite
                        and zeilen[j]["_gk"] == z["_gk"]):
                    eltern[wurzel(i)] = wurzel(j)
        teile = {}
        for i in range(len(zeilen)):
            teile.setdefault(wurzel(i), []).append(i)
        gruppen += [(seite, sorted(m)) for m in teile.values() if len(m) > 1]
    gruppen.sort(key=lambda g: g[1][0])
    # Targets: the first terminal of a group gets them, the others none
    ersatz = {}
    for seite, mitglieder in gruppen:
        ids = {id(zeilen[m]["_kl"]["obj"]) for m in mitglieder}
        alle = [x for m in mitglieder for x in treffer[(m, seite)][1]]
        for pos, i in enumerate(mitglieder):
            ersatz[(i, seite)] = (pos == 0, ids, alle)
    for (i, seite), (node, t) in treffer.items():
        z = zeilen[i]
        if (i, seite) in ersatz:
            erster, ids, alle = ersatz[(i, seite)]
            if not erster:
                z[seite] = []
                continue
            # all targets of the group, without its own members
            t = [(n, v) for n, v in alle if id(n.bes) not in ids]
        pot = _potential(t, z["num"])
        z[seite] = [pot] if pot else ziele_texte(t, node.bes)
    # Lanes: overlapping bridges get different lanes
    belegt = []                         # [(lane, first, last)]
    for seite, mitglieder in gruppen:
        von, bis = mitglieder[0], mitglieder[-1]
        lane = 0
        while any(l == lane and not (bis < v or von > b)
                  for l, v, b in belegt):
            lane += 1
        belegt.append((lane, von, bis))
        for i in range(von, bis + 1):
            z = zeilen[i]
            punkt = i in mitglieder
            z.setdefault("_bruecke", []).append(
                (lane, punkt, i > von, i < bis))
        for i in mitglieder:
            z = zeilen[i]
            andere = [zeilen[m]["num"] or "?" for m in mitglieder if m != i]
            z["bruecke"] = (z.get("bruecke", "") + " " if z.get("bruecke") else "") \
                + seite + ": " + ",".join(andere)


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
