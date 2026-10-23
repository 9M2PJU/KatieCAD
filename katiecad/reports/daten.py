# -*- coding: utf-8 -*-
"""
katiecad/reports/daten.py - Zeilendaten der Berichte (KEIN Tkinter).

Jede Funktion liefert eine Liste von Dicts (eine Zeile je Dict). Werte sind
Strings oder Listen von Strings (mehrere Ziele in einer Zelle). Blattschluessel
sind 0-basierte Indizes der Zeichnungsblaetter; `nummer(idx)` liefert die
angezeigte Blattnummer (sie haengt davon ab, wie viele Berichtsblaetter
davor stehen).
"""

from collections import defaultdict

from katiecad.model.core import ElektroMaske, ort_text
from katiecad.electrical.logic import (REF_FELD, geraete, felder_aus_elementen, feld_an,
                                       _pos)
from katiecad.reports.netz import (natuerlich, ziele_texte, ende_ziele,
                                   wert_gesetzt)


def _ort(nummer, idx, feld):
    return ort_text((nummer(idx), feld))


def _felder(blaetter):
    return {idx: felder_aus_elementen(el) for idx, el in blaetter}


# ------------------------------------------------------------------
# Geraeteliste
# ------------------------------------------------------------------
def _typ_per(obj):
    if isinstance(obj, ElektroMaske):
        w = obj.werte
        return (wert_gesetzt(w.get("TYP"), "TYP"),
                wert_gesetzt(w.get("PER"), "PER"))
    a = getattr(obj, "attribute", {}) or {}
    return wert_gesetzt(a.get("TYP"), "TYP"), wert_gesetzt(a.get("PER"), "PER")


def geraeteliste(blaetter, nummer, netz=None, klemmenleisten=True):
    """Eine Zeile je Betriebsmittel-Kennzeichen (IND). Hauptsymbol und
    Hilfsbausteine mit gleichem IND zaehlen als ein Geraet.
    Zeilen: pos, ind, typ, per, anzahl, orte (Liste), ort (Text)."""
    gruppen = {}
    reihenfolge = []
    for idx, el in blaetter:
        for g in geraete(el, idx):
            if g["rolle"] == "kabel":
                continue
            ind = wert_gesetzt(g["per"], REF_FELD) if g["rolle"] != "kabel" else g["per"]
            schluessel = ("ind", ind) if ind else ("ohne", id(g["obj"]))
            if schluessel not in gruppen:
                gruppen[schluessel] = {"ind": ind, "typ": "", "per": "",
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
        zeilen.append({"ind": z["ind"], "typ": z["typ"], "per": z["per"],
                       "anzahl": str(z["anzahl"]), "orte": orte,
                       "ort": ", ".join(orte)})
    if klemmenleisten and netz is not None:
        felder = _felder(blaetter)
        leisten = {}
        for kl in netz.klemmen:
            k = kl["obj"]
            kz = kl["leiste"]
            if not kz:
                continue
            z = leisten.setdefault(kz, {"ind": kz, "typ": "", "per": "",
                                        "anzahl": 0, "orte": set()})
            z["anzahl"] += 1
            z["typ"] = z["typ"] or wert_gesetzt(k.werte.get("TYP"), "TYP")
            z["per"] = z["per"] or wert_gesetzt(k.werte.get("PER"), "PER")
            z["orte"].add((kl["blatt"], feld_an(felder.get(kl["blatt"], []),
                                                *_pos(k))))
        for kz, z in leisten.items():
            orte = [_ort(nummer, i, f) for i, f in sorted(z["orte"])]
            zeilen.append({"ind": kz, "typ": z["typ"], "per": z["per"],
                           "anzahl": str(z["anzahl"]), "orte": orte,
                           "ort": ", ".join(orte)})
    # Geraete ohne Kennzeichen ans Ende, sonst natuerlich sortiert
    zeilen.sort(key=lambda r: (r["ind"] == "", natuerlich(r["ind"])))
    for i, z in enumerate(zeilen, 1):
        z["pos"] = str(i)
    return zeilen


# ------------------------------------------------------------------
# Klemmenplan
# ------------------------------------------------------------------
def klemmenplan(netz, blaetter, nummer):
    """Eine Zeile je Klemme, sortiert nach Klemmleiste (IND) und Nummer (NUM).
    Zeilen: leiste, num, typ, per, oben (Liste), unten (Liste), ort."""
    felder = _felder(blaetter)
    zeilen = []
    for kl in netz.klemmen:
        k = kl["obj"]
        w = k.werte
        zeilen.append({
            "leiste": kl["leiste"],
            "num": wert_gesetzt(w.get("NUM"), "NUM"),
            "typ": wert_gesetzt(w.get("TYP"), "TYP"),
            "per": wert_gesetzt(w.get("PER"), "PER"),
            "oben": ziele_texte(netz.ziele(kl["oben"]), kl["oben"].bes),
            "unten": ziele_texte(netz.ziele(kl["unten"]), kl["unten"].bes),
            "ort": _ort(nummer, kl["blatt"],
                        feld_an(felder.get(kl["blatt"], []), *_pos(k))),
            "_blatt": kl["blatt"], "_pos": _pos(k)})
    zeilen.sort(key=lambda r: (r["leiste"] == "", natuerlich(r["leiste"]),
                               natuerlich(r["num"]) if r["num"] else (),
                               r["_blatt"], -r["_pos"][1], r["_pos"][0]))
    return zeilen


# ------------------------------------------------------------------
# Kabelplan
# ------------------------------------------------------------------
def kabelplan(netz, blaetter, nummer):
    """Eine Zeile je Ader (bzw. je Kabel ohne erkannte Adern).
    Von = Ende oberhalb des Kabels (Einspeisung), Nach = Ende darunter.
    Zeilen: cab, typ, ader, von (Liste), nach (Liste), ort."""
    felder = _felder(blaetter)
    nach_cab = defaultdict(list)
    for kb in netz.kabel:
        nach_cab[(kb["obj"].werte.get("CAB", "") or "").strip()].append(kb)
    zeilen = []
    for cab in sorted(nach_cab, key=lambda c: (c == "", natuerlich(c))):
        vorkommen = sorted(nach_cab[cab],
                           key=lambda kb: (kb["blatt"], -kb["obj"].y, kb["obj"].x))
        for kb in vorkommen:
            obj = kb["obj"]
            typ = (obj.werte.get("TYP", "") or "").strip()
            ort = _ort(nummer, kb["blatt"],
                       feld_an(felder.get(kb["blatt"], []), *_pos(obj)))
            adern = [a for a in kb["adern"] if a["kanten"]]
            if not adern:
                zeilen.append({"cab": cab, "typ": typ, "ader": "", "von": [],
                               "nach": [], "ort": ort})
                continue
            for a in adern:
                kante = a["kanten"][0]
                oben, unten = ((kante.a, kante.b) if kante.a.y >= kante.b.y
                               else (kante.b, kante.a))
                zeilen.append({
                    "cab": cab, "typ": typ, "ader": a["name"],
                    "von": ziele_texte(ende_ziele(netz, oben, kante)),
                    "nach": ziele_texte(ende_ziele(netz, unten, kante)),
                    "ort": ort})
    return zeilen


# ------------------------------------------------------------------
# Inhaltsverzeichnis
# ------------------------------------------------------------------
def inhaltsverzeichnis(eintraege):
    """eintraege: [{"nr", "name", "beschreibung", "typ"}] -> Zeilen."""
    return [{"nr": str(e["nr"]), "name": e.get("name", ""),
             "beschreibung": e.get("beschreibung", ""), "typ": e.get("typ", "")}
            for e in eintraege]
