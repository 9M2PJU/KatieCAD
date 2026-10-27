# -*- coding: utf-8 -*-
"""
katiecad/electrical/logic.py - Logic for electrical diagrams (NO Tkinter).

Cross references: two or more cross-reference arrows with the same text
belong together. Each shows the sheet number(s) of the others as its target.
"""

from collections import Counter, defaultdict

import math
from copy import deepcopy

from katiecad.model.core import (Querverweis, Verbindungspunkt, BlockReferenz,
                           Verbindung, Klemme, ElektroMaske, Leitung,
                           Koordinatenfeld, Text, Kabel, E_LINES)
from katiecad.common.i18n import tr


def felder_aus_elementen(elemente):
    """All coordinate fields (zone grids) of an element list."""
    return [e for e in elemente if isinstance(e, Koordinatenfeld)]


def felder_aus_blattdaten(daten):
    """Coordinate fields from the JSON data of a (not loaded) sheet."""
    out = []
    if not isinstance(daten, dict):
        return out
    for d in daten.get("elemente", []):
        if isinstance(d, dict) and d.get("typ") == "koordinatenfeld":
            try:
                kw = {k: v for k, v in d.items() if k != "typ"}
                out.append(Koordinatenfeld(**kw))
            except (TypeError, ValueError):
                pass
    return out


def feld_an(felder, x, y):
    """"Column/row" of the location (x, y) in the first matching field, otherwise ""."""
    for f in felder:
        z = f.zone(x, y)
        if z:
            return z
    return ""


def _pos(obj):
    return float(getattr(obj, "x", 0.0)), float(getattr(obj, "y", 0.0))


def qv_texte_aus_blattdaten(daten):
    """Cross references from the JSON data of a sheet (without objects):
    list of (text, "column/row")."""
    texte = []
    if not isinstance(daten, dict):
        return texte
    felder = felder_aus_blattdaten(daten)
    for d in daten.get("elemente", []):
        if isinstance(d, dict) and d.get("typ") == "querverweis":
            t = str(d.get("text", "")).strip()
            if t:
                try:
                    feld = feld_an(felder, float(d.get("x", 0)), float(d.get("y", 0)))
                except (TypeError, ValueError):
                    feld = ""
                texte.append((t, feld, d.get("art", "abgehend")))
    return texte


def qv_texte_aus_elementen(elemente):
    """Cross references of an element list: list of (text, "column/row")."""
    felder = felder_aus_elementen(elemente)
    return [(e.text.strip(), feld_an(felder, *_pos(e)), e.art) for e in elemente
            if isinstance(e, Querverweis) and e.text.strip()]


def _text_feld(eintrag):
    """Accepts "text", (text, field) or (text, field, art) -> (text, field, art)."""
    if isinstance(eintrag, (tuple, list)):
        return (str(eintrag[0]), (eintrag[1] if len(eintrag) > 1 else ""),
                (eintrag[2] if len(eintrag) > 2 else None))
    return str(eintrag), "", None


def _kette_ziele(qv, blatt_nr, andere):
    """Chain logic: with the same name over several sheets an outgoing
    reference points to the incoming one on the NEXT sheet, an incoming one
    to the outgoing one on the PREVIOUS sheet (left to right), so L1 does
    not need to be numbered L1.1, L1.2 ... Without a clear partner in that
    direction all other occurrences are used (old behaviour).
    andere: [(sheet, field, other_qv, art)] without qv itself."""
    gegen = "ankommend" if qv.art == "abgehend" else "abgehend"
    kand = [o for o in andere if o[3] == gegen]
    if qv.art == "abgehend":
        kand = [o for o in kand if o[0] > blatt_nr]
        ziel_nr = min((o[0] for o in kand), default=None)
    else:
        kand = [o for o in kand if o[0] < blatt_nr]
        ziel_nr = max((o[0] for o in kand), default=None)
    if ziel_nr is None:
        return andere
    return [o for o in kand if o[0] == ziel_nr]


def querverweis_ziele(elemente, blatt_nr, andere_blaetter):
    """Sets `ziel` on all cross references of `elemente`.

    ziel = sorted list of (sheet_no, "column/row") of the counterparts;
    "column/row" is empty if the sheet has no coordinate field at this
    location.
    elemente:        elements of the sheet with number `blatt_nr`
    andere_blaetter: {sheet_no: [text or (text, field), ...]} for all
                     other sheets
    """
    qvs = [e for e in elemente if isinstance(e, Querverweis)]
    if not qvs:
        return
    felder = felder_aus_elementen(elemente)
    eigene = []                                  # (qv, text, field)
    for qv in qvs:
        t = qv.text.strip()
        if t:
            eigene.append((qv, t, feld_an(felder, *_pos(qv))))
    vorkommen = defaultdict(list)                # text -> [(sheet, field, qv|None)]
    for qv, t, feld in eigene:
        vorkommen[t].append((blatt_nr, feld, qv, qv.art))
    for nr, eintraege in andere_blaetter.items():
        for e in eintraege:
            t, feld, art = _text_feld(e)
            vorkommen[t].append((nr, feld, None, art))
    for qv in qvs:
        t = qv.text.strip()
        if not t:
            qv.ziel = []
            continue
        andere = [o for o in vorkommen[t] if o[2] is not qv]
        # (the chain applies only if the name appears on at least 3 places)
        if len(andere) >= 2:
            andere = _kette_ziele(qv, blatt_nr, andere)
        qv.ziel = sorted({(o[0], o[1]) for o in andere})


def ziele_fuer_alle_blaetter(blaetter):
    """blaetter: {sheet_no: [elements]} -> sets `ziel` in all sheets."""
    texte = {nr: qv_texte_aus_elementen(el) for nr, el in blaetter.items()}
    for nr, el in blaetter.items():
        andere = {n: t for n, t in texte.items() if n != nr}
        querverweis_ziele(el, nr, andere)


def verbindungspunkte(elemente, sichtbar=lambda el: True):
    """All connection points (including those in blocks) as resolved elements."""
    out = []
    for el in elemente:
        if not sichtbar(el):
            continue
        if isinstance(el, Verbindungspunkt):
            out.append(el)
        elif isinstance(el, BlockReferenz):
            out.extend(k for k in el.aufgeloest()
                       if isinstance(k, Verbindungspunkt))
    return out


class Anschluss:
    """A point where a wire may end."""
    __slots__ = ("x", "y", "name")

    def __init__(self, x, y, name):
        self.x, self.y, self.name = x, y, name


def _anschluesse_von(el):
    """Connection points of a single (resolved) element."""
    out = []
    if isinstance(el, Querverweis):
        t = el.text or "-"
        bx, by = el.basis_punkt()
        sx, sy = el.spitze_punkt()
        out.append(Anschluss(bx, by, tr("an.qv_basis", text=t)))
        out.append(Anschluss(sx, sy, tr("an.qv_spitze", text=t)))
    elif isinstance(el, Verbindungspunkt):
        out.append(Anschluss(el.x, el.y, tr("an.vp", text=el.wert or "-")))
    elif isinstance(el, Verbindung):
        for (ax, ay, d) in el.anschluesse():
            out.append(Anschluss(ax, ay, tr("an.verbindung", art=el.art,
                                            richtung=tr("dlg.richtung.%d" % d))))
    elif isinstance(el, Klemme):
        t = el.werte.get("NUM") or el.werte.get("IND") or "-"
        ox, oy = el.anschluss_oben()
        ux, uy = el.anschluss_unten()
        out.append(Anschluss(ox, oy, tr("an.klemme_oben", text=t)))
        out.append(Anschluss(ux, uy, tr("an.klemme_unten", text=t)))
    return out


def anschlusspunkte(elemente, sichtbar=lambda el: True):
    """All wire connection points:
       - pins (also from blocks)
       - cross references: ONLY base and tip of the arrow
       - junctions: the arm ends
       - terminals: top and bottom"""
    out = []
    for el in elemente:
        if not sichtbar(el):
            continue
        if isinstance(el, BlockReferenz):
            for k in el.aufgeloest():
                out.extend(_anschluesse_von(k))
        else:
            out.extend(_anschluesse_von(el))
    return out


def naechster_anschluss(elemente, x, y, tol, sichtbar=lambda el: True):
    """Nearest connection point within `tol` (mm) or None."""
    best, bd = None, None
    for a in anschlusspunkte(elemente, sichtbar):
        d = ((a.x - x) ** 2 + (a.y - y) ** 2) ** 0.5
        if d <= tol and (bd is None or d < bd):
            best, bd = a, d
    return best


def naechster_vp(elemente, x, y, tol, sichtbar=lambda el: True):
    """Nearest connection point (pin) within `tol` (mm) or None."""
    best, bd = None, None
    for vp in verbindungspunkte(elemente, sichtbar):
        d = ((vp.x - x) ** 2 + (vp.y - y) ** 2) ** 0.5
        if d <= tol and (bd is None or d < bd):
            best, bd = vp, d
    return best


def naechste_bezeichnung(zuletzt):
    """'13' -> '14', 'A1' -> 'A2', 'PE' -> 'PE'."""
    z = (zuletzt or "").strip()
    i = len(z)
    while i > 0 and z[i - 1].isdigit():
        i -= 1
    if i == len(z):
        return z
    return z[:i] + str(int(z[i:]) + 1).zfill(len(z) - i)


# ============================================================
# Devices (electrical mask): automatic references via PER
# ============================================================
# Field used to match devices with each other (same value = same
# device, e.g. main contactor K1 and its auxiliary contacts K1).
REF_FELD = "IND"


def kontakt_art(pins):
    """Contact type from the pin labels of an auxiliary part (function
    digits per IEC: 1-2 break, 3-4 make, 5-6 break, 7-8 make).
    -> 'schliesser' | 'oeffner' | 'wechsler' | 'spule' | 'unbekannt'"""
    ps = [str(p).strip() for p in pins if str(p).strip()]
    if not ps:
        return "unbekannt"
    if any(p[:1].upper() == "A" for p in ps):
        return "spule"
    ziffern = {p[-1] for p in ps if p[-1:].isdigit()}
    if {"1", "2", "4"} <= ziffern:
        return "wechsler"
    for a, b, art in (("3", "4", "schliesser"), ("7", "8", "schliesser"),
                      ("1", "2", "oeffner"), ("5", "6", "oeffner")):
        if a in ziffern and b in ziffern:
            return art
    return "unbekannt"


def _pins_von(block):
    return [str(v.wert) for v in verbindungspunkte([block])]


def geraete(elemente, blatt_nr):
    """All devices of a sheet: free electrical masks and blocks with an
    electrical mask. -> list of dicts {obj, per, ind, rolle, blatt}."""
    out = []
    felder = felder_aus_elementen(elemente)
    for el in elemente:
        if isinstance(el, ElektroMaske):
            w = el.werte
            out.append({"obj": el, "per": w.get(REF_FELD, "").strip(),
                        "ind": w.get("IND", ""), "rolle": el.rolle,
                        "blatt": blatt_nr, "feld": feld_an(felder, *_pos(el))})
        elif isinstance(el, Kabel):
            out.append({"obj": el, "per": el.werte.get("CAB", "").strip(),
                        "ind": "", "rolle": "kabel", "blatt": blatt_nr,
                        "feld": feld_an(felder, *_pos(el))})
        elif isinstance(el, BlockReferenz):
            m = el.geraet_maske()
            if m is not None:
                out.append({"obj": el,
                            "per": str(el.attribute.get(REF_FELD, "")).strip(),
                            "ind": str(el.attribute.get("IND", "")),
                            "rolle": m.rolle, "blatt": blatt_nr,
                            "pins": _pins_von(el),
                            "feld": feld_an(felder, *_pos(el))})
    return out


def geraete_aus_blattdaten(daten):
    """Devices of a (not loaded) sheet from the JSON data:
    list of (per, role, ind, "column/row")."""
    res = []
    if not isinstance(daten, dict):
        return res
    felder = felder_aus_blattdaten(daten)

    def feld_von(d):
        try:
            return feld_an(felder, float(d.get("x", 0)), float(d.get("y", 0)))
        except (TypeError, ValueError):
            return ""

    for d in daten.get("elemente", []):
        if not isinstance(d, dict):
            continue
        if d.get("typ") == "maske":
            w = d.get("werte", {}) or {}
            res.append((str(w.get(REF_FELD, "")).strip(), d.get("rolle", "haupt"),
                        str(w.get("IND", "")), feld_von(d)))
        elif d.get("typ") == "kabel":
            w = d.get("werte", {}) or {}
            res.append((str(w.get("CAB", "")).strip(), "kabel", "", feld_von(d)))
        elif d.get("typ") == "block":
            for k in d.get("elemente", []) or []:
                if isinstance(k, dict) and k.get("typ") == "maske":
                    a = d.get("attribute", {}) or {}
                    pins = [str(a.get(v.get("tag"), v.get("wert", "")))
                            for v in d.get("elemente", []) or []
                            if isinstance(v, dict) and v.get("typ") == "vpunkt"]
                    res.append((str(a.get(REF_FELD, "")).strip(),
                                k.get("rolle", "haupt"), str(a.get("IND", "")),
                                feld_von(d), pins))
                    break
    return res


def geraete_referenzen(eigene, blatt_nr, andere_blaetter):
    """Sets `refs` (sorted, unique (sheet, "column/row")) on all
    devices.

    main symbol      -> refers to all auxiliary parts with the same PER
    auxiliary part   -> refers only to the main symbol with the same PER
    eigene:          result of geraete()
    andere_blaetter: {sheet_no: [(per, role, ind[, field]), ...]}"""
    kandidaten = []          # (per, role, (sheet, field), id, pins)
    for g in eigene:
        kandidaten.append((g["per"], g["rolle"],
                           (g["blatt"], g.get("feld", "")), id(g["obj"]),
                           g.get("pins", [])))
    for nr, liste in andere_blaetter.items():
        for e in liste:
            per, rolle = e[0], e[1]
            feld = e[3] if len(e) > 3 else ""
            pins = e[4] if len(e) > 4 else []
            kandidaten.append((str(per).strip(), rolle, (nr, feld), None, pins))
    for g in eigene:
        if not g["per"]:
            g["obj"].refs = []
            g["obj"].kontakte = []
            continue
        kont = []
        if g["rolle"] == "haupt":
            for per, rolle, blatt, oid, pins in kandidaten:
                if per == g["per"] and rolle == "hilfs" and oid != id(g["obj"]):
                    art = kontakt_art(pins)
                    if art != "spule":
                        pt = tuple(str(p).strip() for p in pins if str(p).strip())
                        kont.append((art, pt, blatt))
            kont.sort(key=lambda k: (k[1], str(k[2])))
        g["obj"].kontakte = kont
        gesucht = ("kabel" if g["rolle"] == "kabel"
                   else "hilfs" if g["rolle"] == "haupt" else "haupt")
        g["obj"].refs = sorted({blatt for per, rolle, blatt, oid, _p in kandidaten
                                if per == g["per"] and rolle == gesucht
                                and oid != id(g["obj"])})


# ============================================================
# Wires: split and clean up connections
# ============================================================
TOL = 0.05


def naechster_leitungspunkt(elemente, x, y, tol):
    """Does (x, y) lie within `tol` on the INTERIOR of a wire?
    -> (wire, px, py) with the foot of the perpendicular, otherwise None."""
    best, bd = None, None
    for el in elemente:
        if not isinstance(el, Leitung):
            continue
        dx, dy = el.x2 - el.x1, el.y2 - el.y1
        l2 = dx * dx + dy * dy
        if l2 < 1e-12:
            continue
        t = ((x - el.x1) * dx + (y - el.y1) * dy) / l2
        px, py = el.x1 + t * dx, el.y1 + t * dy
        d = math.hypot(x - px, y - py)
        laenge = math.sqrt(l2)
        # End points are not split points
        if d <= tol and TOL / laenge < t < 1 - TOL / laenge:
            if bd is None or d < bd:
                best, bd = (el, px, py), d
    return best


def leitung_teilen(elemente, x, y, tol=TOL):
    """Splits a wire, on whose interior (x, y) lies, into two wires.
    Returns True if it was split."""
    hit = naechster_leitungspunkt(elemente, x, y, tol)
    if hit is None:
        return False
    el, px, py = hit
    a = deepcopy(el)
    b = deepcopy(el)
    a.x2, a.y2 = x, y
    b.x1, b.y1 = x, y
    i = elemente.index(el)
    elemente[i:i + 1] = [a, b]
    return True


def _ankerpunkte(elemente, ausser=None):
    """All points where a wire may end (incl. junction centres)."""
    pts = []
    for el in elemente:
        if el is ausser:
            continue
        if isinstance(el, Verbindung):
            pts.append((el.x, el.y))
        if isinstance(el, BlockReferenz):
            for k in el.aufgeloest():
                pts.extend((a.x, a.y) for a in _anschluesse_von(k))
        else:
            pts.extend((a.x, a.y) for a in _anschluesse_von(el))
    return pts


def _nahe(p, q):
    return abs(p[0] - q[0]) <= TOL and abs(p[1] - q[1]) <= TOL


def _verb_punkte(v):
    return [(v.x, v.y)] + [(ax, ay) for (ax, ay, _d) in v.anschluesse()]


def _gueltige_leitungen(v, elemente):
    """Wires that end at `v` AND have a counterpart (pin, junction, terminal,
    cross reference) at the other end."""
    anker = _ankerpunkte(elemente, ausser=v)
    mein = _verb_punkte(v)
    res = []
    for l in elemente:
        if not isinstance(l, Leitung):
            continue
        e1, e2 = (l.x1, l.y1), (l.x2, l.y2)
        an1 = any(_nahe(e1, p) for p in mein)
        an2 = any(_nahe(e2, p) for p in mein)
        if an1 == an2:                       # both or none -> irrelevant
            continue
        fern = e2 if an1 else e1
        if any(_nahe(fern, p) for p in anker):
            res.append(l)
    return res


def vollstaendige_verbindungen(elemente):
    """ids of the junctions that currently have at least two wires with a
    counterpart (= 'connected')."""
    return {id(v) for v in elemente
            if isinstance(v, Verbindung)
            and len(_gueltige_leitungen(v, elemente)) >= 2}


def _anker_enden(l, anker):
    return (any(_nahe((l.x1, l.y1), p) for p in anker)
            and any(_nahe((l.x2, l.y2), p) for p in anker))


def vollstaendige_leitungen(elemente):
    """ids of the wires that have a counterpart at BOTH ends
    (pin, junction, terminal or cross reference)."""
    anker = _ankerpunkte(elemente)
    return {id(l) for l in elemente
            if isinstance(l, Leitung) and _anker_enden(l, anker)}


def verbindungen_bereinigen(elemente, vorher, vorher_leitungen=()):
    """Cleans up after deleting (in place, cascading):
      - wires that were connected at both ends before
        (`vorher_leitungen` = result of vollstaendige_leitungen) and now
        have no counterpart at one end disappear;
      - junctions that were connected before (`vorher` = result of
        vollstaendige_verbindungen) and now have fewer than two valid wires
        disappear together with the wires attached to them.
    Returns: (number_of_junctions, number_of_wires)."""
    n_v = n_l = 0
    while True:
        geaendert = False
        anker = _ankerpunkte(elemente)
        for l in [l for l in elemente
                  if isinstance(l, Leitung) and id(l) in vorher_leitungen
                  and not _anker_enden(l, anker)]:
            elemente.remove(l)
            n_l += 1
            geaendert = True
        weg = [v for v in elemente
               if isinstance(v, Verbindung) and id(v) in vorher
               and len(_gueltige_leitungen(v, elemente)) < 2]
        for v in weg:
            punkte = _verb_punkte(v)
            for l in [l for l in elemente if isinstance(l, Leitung)
                      and (any(_nahe((l.x1, l.y1), p) for p in punkte)
                           or any(_nahe((l.x2, l.y2), p) for p in punkte))]:
                elemente.remove(l)
                n_l += 1
            elemente.remove(v)
            n_v += 1
            geaendert = True
        if not geaendert:
            return n_v, n_l


# ============================================================
# Wires are automatically interrupted by devices placed on top of them
# ============================================================
def einrast_punkte(el):
    """Points of an object where an underlying wire is interrupted and
    connected: pin, junction (centre), terminal (top/bottom) and all such
    points in blocks (devices)."""
    if isinstance(el, Verbindungspunkt):
        return [(el.x, el.y)]
    if isinstance(el, Verbindung):
        return [(el.x, el.y)]
    if isinstance(el, Klemme):
        return [el.anschluss_oben(), el.anschluss_unten()]
    if isinstance(el, BlockReferenz):
        out = []
        for k in el.aufgeloest():
            out.extend(einrast_punkte(k))
        return out
    return []


def leitungen_einrasten(elemente, neue, tol=0.5):
    """If an object (pin, junction, terminal, device) is placed on a wire,
    the wire is interrupted:
      - one point on the wire    -> wire in two parts, both at the point
      - several points (e.g. top/bottom of a device) -> the wire ends at the
        first point and starts again at the last; in between (inside the
        device) it is omitted.
    Each new object is handled individually. Returns the number of
    interrupted wires."""
    n = 0
    for obj in neue:
        pts = einrast_punkte(obj)
        if not pts:
            continue
        for l in [l for l in elemente if isinstance(l, Leitung) and l not in neue]:
            dx, dy = l.x2 - l.x1, l.y2 - l.y1
            laenge = math.hypot(dx, dy)
            if laenge < 1e-9:
                continue
            auf = []
            for (px, py) in pts:
                t = ((px - l.x1) * dx + (py - l.y1) * dy) / (laenge * laenge)
                fx, fy = l.x1 + t * dx, l.y1 + t * dy
                if (math.hypot(px - fx, py - fy) <= tol
                        and t * laenge > TOL and (1 - t) * laenge > TOL):
                    auf.append((t, px, py))
            if not auf:
                continue
            auf.sort()
            erst, letzt = auf[0], auf[-1]
            a = deepcopy(l)
            b = deepcopy(l)
            a.x2, a.y2 = erst[1], erst[2]
            b.x1, b.y1 = letzt[1], letzt[2]
            i = elemente.index(l)
            elemente[i:i + 1] = [a, b]
            n += 1
    return n


# ============================================================
# Automatic wires (like Eplan P8)
# ============================================================
def _block_kanten(kinder):
    xs, ys = [], []
    for k in kinder:
        if isinstance(k, (Text, Verbindungspunkt)):
            if not isinstance(k, Verbindungspunkt):
                continue
        b = k.bbox()
        xs += [b[0], b[2]]
        ys += [b[1], b[3]]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _pin_richtung(pin, kanten):
    """Allowed direction of a pin in a device: the nearest outer edge of the
    symbol (on a tie, vertical before horizontal).
    Without edges (free pin): all directions. Explicitly set directions of
    the pin (`richtungen`) always take precedence."""
    if getattr(pin, "richtungen", None) is not None:
        return set(pin.richtungen)
    x, y = pin.x, pin.y
    if kanten is None:
        return None
    x1, y1, x2, y2 = kanten
    d = [(y2 - y, 0, 90), (y - y1, 0, 270), (x2 - x, 1, 0), (x - x1, 1, 180)]
    d.sort()
    return {d[0][2]}


def _auto_anker(elemente):
    """[(x, y, allowed_directions|None, owner_id, owner, binds_in)]"""
    out = []

    def sammle(k, besitzer, kanten):
        bid = id(besitzer)
        if isinstance(k, Verbindungspunkt):
            out.append((k.x, k.y, _pin_richtung(k, kanten), bid, besitzer))
        elif isinstance(k, Verbindung):
            for (ax, ay, d) in k.anschluesse():
                out.append((ax, ay, {d}, bid, besitzer))
        elif isinstance(k, Klemme):
            ox, oy = k.anschluss_oben()
            ux, uy = k.anschluss_unten()
            out.append((ox, oy, {90}, bid, besitzer))
            out.append((ux, uy, {270}, bid, besitzer))
        elif isinstance(k, Querverweis):
            # Connection lies on the side facing away from the text
            if k.art == "abgehend":
                bx, by = k.basis_punkt()
                out.append((bx, by, {(k.richtung + 180) % 360}, bid, besitzer))
            else:
                sx, sy = k.spitze_punkt()
                out.append((sx, sy, {k.richtung}, bid, besitzer))

    for el in elemente:
        if isinstance(el, BlockReferenz):
            kinder = el.aufgeloest()
            kanten = _block_kanten(kinder)
            for k in kinder:
                sammle(k, el, kanten)
        else:
            sammle(el, el, None)
    return out


def _cluster(werte, key):
    """Groups entries with (almost) the same key(entry)."""
    werte = sorted(werte, key=key)
    gruppen, akt = [], []
    for w in werte:
        if akt and abs(key(w) - key(akt[-1])) > TOL:
            gruppen.append(akt)
            akt = []
        akt.append(w)
    if akt:
        gruppen.append(akt)
    return gruppen


def gewuenschte_leitungen(elemente):
    """All wire pieces that must exist automatically:
    [(x1, y1, x2, y2, owner)]. Two neighbouring connection points on a
    horizontal/vertical line are connected if they belong to
    different objects and their directions match.
    A connection point in between (also of a device) interrupts it."""
    anker = _auto_anker(elemente)
    soll = []
    for gr in _cluster(anker, key=lambda a: a[0]):          # vertical
        gr.sort(key=lambda a: a[1])
        for lo, hi in zip(gr, gr[1:]):
            if lo[3] == hi[3] or hi[1] - lo[1] < TOL:
                continue
            if (lo[2] is None or 90 in lo[2]) and (hi[2] is None or 270 in hi[2]):
                soll.append((lo[0], lo[1], lo[0], hi[1], lo[4]))
    for gr in _cluster(anker, key=lambda a: a[1]):          # horizontal
        gr.sort(key=lambda a: a[0])
        for lo, hi in zip(gr, gr[1:]):
            if lo[3] == hi[3] or hi[0] - lo[0] < TOL:
                continue
            if (lo[2] is None or 0 in lo[2]) and (hi[2] is None or 180 in hi[2]):
                soll.append((lo[0], lo[1], hi[0], lo[1], lo[4]))
    return soll


def _seg_key(x1, y1, x2, y2):
    a, b = (round(x1, 2), round(y1, 2)), (round(x2, 2), round(y2, 2))
    return (a, b) if a <= b else (b, a)


def leitungen_automatisch(elemente):
    """Reconciles the automatic wires with the connection points (in
    place): missing ones are created, no longer possible ones removed.
    Hand-drawn wires (older files) that exactly match a desired piece
    become automatic wires. Existing wires are kept (same objects) as long
    as they still apply.
    Returns: (created, removed, removed_objects)."""
    soll = {}
    for (x1, y1, x2, y2, bes) in gewuenschte_leitungen(elemente):
        soll.setdefault(_seg_key(x1, y1, x2, y2), (x1, y1, x2, y2, bes))
    vorhanden = {}
    weg = []
    uebrig = []                                  # do not match exactly
    for l in elemente:
        if not isinstance(l, Leitung):
            continue
        k = _seg_key(l.x1, l.y1, l.x2, l.y2)
        if k in soll:
            if k in vorhanden:                   # duplicate
                weg.append(l)
                continue
            l.auto = True
            vorhanden[k] = l
        else:
            uebrig.append(l)
    # Wires that are off by a fraction of a mm (e.g. drawn by hand)
    # count as the same piece or as a duplicate
    for l in uebrig:
        treffer = None
        for k, (x1, y1, x2, y2, _b) in soll.items():
            if ((abs(l.x1 - x1) <= 0.3 and abs(l.y1 - y1) <= 0.3
                 and abs(l.x2 - x2) <= 0.3 and abs(l.y2 - y2) <= 0.3)
                    or (abs(l.x1 - x2) <= 0.3 and abs(l.y1 - y2) <= 0.3
                        and abs(l.x2 - x1) <= 0.3 and abs(l.y2 - y1) <= 0.3)):
                treffer = k
                break
        if treffer is not None:
            if treffer in vorhanden:
                weg.append(l)                    # duplication
            else:
                l.x1, l.y1, l.x2, l.y2 = soll[treffer][:4]
                l.auto = True
                vorhanden[treffer] = l
        elif l.auto:
            weg.append(l)                        # no longer possible
    for l in weg:
        elemente.remove(l)
    neu = 0
    for k, (x1, y1, x2, y2, bes) in soll.items():
        if k in vorhanden:
            continue
        elemente.append(Leitung(x1, y1, x2, y2, auto=True, layer=E_LINES))
        neu += 1
    return neu, len(weg), weg


def kabel_kreuzungen(elemente):
    """Sets `kreuzungen` on all cables: x positions where a vertical wire
    truly crosses the cable line (wires ending on the line do not count)."""
    kabel = [k for k in elemente if isinstance(k, Kabel)]
    if not kabel:
        return
    senkrecht = [l for l in elemente
                 if isinstance(l, Leitung) and abs(l.x1 - l.x2) <= TOL]
    for k in kabel:
        xs = set()
        for l in senkrecht:
            lo, hi = sorted((l.y1, l.y2))
            if lo + TOL < k.y < hi - TOL and k.x + TOL < l.x1 <= k.x + k.laenge + TOL:
                xs.add(round(l.x1, 2))
        # Wires lying (almost) on the same vertical line are one core
        gruppen = []
        for x in sorted(xs):
            if gruppen and x - gruppen[-1][-1] <= 0.5:
                gruppen[-1].append(x)
            else:
                gruppen.append([x])
        k.kreuzungen = [g[0] for g in gruppen]
