# -*- coding: utf-8 -*-
"""
katiecad/electrical/logic.py - Logik fuer Elektro-Plaene (KEIN Tkinter).

Querverweise: Zwei oder mehr Querverweis-Pfeile mit gleichem Text gehoeren
zusammen. Jeder zeigt als Ziel die Blattnummer(n) der anderen.
"""

from collections import Counter, defaultdict

import math
from copy import deepcopy

from katiecad.model.core import (Querverweis, Verbindungspunkt, BlockReferenz,
                           Verbindung, Klemme, ElektroMaske, Leitung,
                           Koordinatenfeld)
from katiecad.common.i18n import tr


def felder_aus_elementen(elemente):
    """Alle Koordinatenfelder (Zonenraster) einer Elementliste."""
    return [e for e in elemente if isinstance(e, Koordinatenfeld)]


def felder_aus_blattdaten(daten):
    """Koordinatenfelder aus den JSON-Daten eines (nicht geladenen) Blattes."""
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
    """"Spalte/Zeile" der Stelle (x, y) im ersten passenden Feld, sonst ""."""
    for f in felder:
        z = f.zone(x, y)
        if z:
            return z
    return ""


def _pos(obj):
    return float(getattr(obj, "x", 0.0)), float(getattr(obj, "y", 0.0))


def qv_texte_aus_blattdaten(daten):
    """Querverweise aus den JSON-Daten eines Blattes (ohne Objekte):
    Liste von (text, "Spalte/Zeile")."""
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
                texte.append((t, feld))
    return texte


def qv_texte_aus_elementen(elemente):
    """Querverweise einer Elementliste: Liste von (text, "Spalte/Zeile")."""
    felder = felder_aus_elementen(elemente)
    return [(e.text.strip(), feld_an(felder, *_pos(e))) for e in elemente
            if isinstance(e, Querverweis) and e.text.strip()]


def _text_feld(eintrag):
    """Akzeptiert "text" oder (text, feld)."""
    if isinstance(eintrag, (tuple, list)):
        return str(eintrag[0]), (eintrag[1] if len(eintrag) > 1 else "")
    return str(eintrag), ""


def querverweis_ziele(elemente, blatt_nr, andere_blaetter):
    """Setzt `ziel` an allen Querverweisen von `elemente`.

    ziel = sortierte Liste von (blatt_nr, "Spalte/Zeile") der Gegenstuecke;
    "Spalte/Zeile" ist leer, wenn das Blatt kein Koordinatenfeld an dieser
    Stelle hat.
    elemente:        Elemente des Blattes mit der Nummer `blatt_nr`
    andere_blaetter: {blatt_nr: [text oder (text, feld), ...]} fuer alle
                     uebrigen Blaetter
    """
    qvs = [e for e in elemente if isinstance(e, Querverweis)]
    if not qvs:
        return
    felder = felder_aus_elementen(elemente)
    eigene = []                                  # (qv, text, feld)
    for qv in qvs:
        t = qv.text.strip()
        if t:
            eigene.append((qv, t, feld_an(felder, *_pos(qv))))
    vorkommen = defaultdict(list)                # text -> [(blatt, feld, qv|None)]
    for qv, t, feld in eigene:
        vorkommen[t].append((blatt_nr, feld, qv))
    for nr, eintraege in andere_blaetter.items():
        for e in eintraege:
            t, feld = _text_feld(e)
            vorkommen[t].append((nr, feld, None))
    for qv in qvs:
        t = qv.text.strip()
        if not t:
            qv.ziel = []
            continue
        qv.ziel = sorted({(nr, feld) for nr, feld, anderer in vorkommen[t]
                          if anderer is not qv})


def ziele_fuer_alle_blaetter(blaetter):
    """blaetter: {blatt_nr: [elemente]} -> setzt `ziel` in allen Blaettern."""
    texte = {nr: qv_texte_aus_elementen(el) for nr, el in blaetter.items()}
    for nr, el in blaetter.items():
        andere = {n: t for n, t in texte.items() if n != nr}
        querverweis_ziele(el, nr, andere)


def verbindungspunkte(elemente, sichtbar=lambda el: True):
    """Alle Verbindungspunkte (auch aus Bloecken) als aufgeloeste Elemente."""
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
    """Ein Punkt, an dem eine Leitung enden darf."""
    __slots__ = ("x", "y", "name")

    def __init__(self, x, y, name):
        self.x, self.y, self.name = x, y, name


def _anschluesse_von(el):
    """Anschlusspunkte eines einzelnen (aufgeloesten) Elements."""
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
    """Alle Leitungs-Anschlusspunkte:
       - Pins (auch aus Bloecken)
       - Querverweise: NUR Basis und Spitze des Pfeils
       - Verbindungen: die Armenden
       - Klemmen: oben und unten"""
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
    """Naechster Anschlusspunkt innerhalb `tol` (mm) oder None."""
    best, bd = None, None
    for a in anschlusspunkte(elemente, sichtbar):
        d = ((a.x - x) ** 2 + (a.y - y) ** 2) ** 0.5
        if d <= tol and (bd is None or d < bd):
            best, bd = a, d
    return best


def naechster_vp(elemente, x, y, tol, sichtbar=lambda el: True):
    """Naechster Verbindungspunkt innerhalb `tol` (mm) oder None."""
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
# Geraete (Elektro-Maske): automatische Verweise ueber PER
# ============================================================
# Feld, ueber das Geraete einander zugeordnet werden (gleicher Wert = gleiches
# Geraet, z. B. Hauptschuetz K1 und seine Hilfskontakte K1).
REF_FELD = "IND"


def geraete(elemente, blatt_nr):
    """Alle Geraete eines Blattes: freie Elektro-Masken und Bloecke mit
    Elektro-Maske. -> Liste von Dicts {obj, per, ind, rolle, blatt}."""
    out = []
    felder = felder_aus_elementen(elemente)
    for el in elemente:
        if isinstance(el, ElektroMaske):
            w = el.werte
            out.append({"obj": el, "per": w.get(REF_FELD, "").strip(),
                        "ind": w.get("IND", ""), "rolle": el.rolle,
                        "blatt": blatt_nr, "feld": feld_an(felder, *_pos(el))})
        elif isinstance(el, BlockReferenz):
            m = el.geraet_maske()
            if m is not None:
                out.append({"obj": el,
                            "per": str(el.attribute.get(REF_FELD, "")).strip(),
                            "ind": str(el.attribute.get("IND", "")),
                            "rolle": m.rolle, "blatt": blatt_nr,
                            "feld": feld_an(felder, *_pos(el))})
    return out


def geraete_aus_blattdaten(daten):
    """Geraete eines (nicht geladenen) Blattes aus den JSON-Daten:
    Liste von (per, rolle, ind, "Spalte/Zeile")."""
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
        elif d.get("typ") == "block":
            for k in d.get("elemente", []) or []:
                if isinstance(k, dict) and k.get("typ") == "maske":
                    a = d.get("attribute", {}) or {}
                    res.append((str(a.get(REF_FELD, "")).strip(),
                                k.get("rolle", "haupt"), str(a.get("IND", "")),
                                feld_von(d)))
                    break
    return res


def geraete_referenzen(eigene, blatt_nr, andere_blaetter):
    """Setzt `refs` (sortierte, eindeutige (Blatt, "Spalte/Zeile")) an allen
    Geraeten.

    Hauptsymbol  -> verweist auf alle Hilfsbausteine mit gleichem PER
    Hilfsbaustein-> verweist nur auf das Hauptsymbol mit gleichem PER
    eigene:          Ergebnis von geraete()
    andere_blaetter: {blatt_nr: [(per, rolle, ind[, feld]), ...]}"""
    kandidaten = []                       # (per, rolle, (blatt, feld), id)
    for g in eigene:
        kandidaten.append((g["per"], g["rolle"],
                           (g["blatt"], g.get("feld", "")), id(g["obj"])))
    for nr, liste in andere_blaetter.items():
        for e in liste:
            per, rolle = e[0], e[1]
            feld = e[3] if len(e) > 3 else ""
            kandidaten.append((str(per).strip(), rolle, (nr, feld), None))
    for g in eigene:
        if not g["per"]:
            g["obj"].refs = []
            continue
        gesucht = "hilfs" if g["rolle"] == "haupt" else "haupt"
        g["obj"].refs = sorted({blatt for per, rolle, blatt, oid in kandidaten
                                if per == g["per"] and rolle == gesucht
                                and oid != id(g["obj"])})


# ============================================================
# Leitungen: teilen und Verbindungen bereinigen
# ============================================================
TOL = 0.05


def naechster_leitungspunkt(elemente, x, y, tol):
    """Liegt (x, y) innerhalb `tol` auf dem INNEREN einer Leitung?
    -> (leitung, px, py) mit dem Lotfusspunkt, sonst None."""
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
        # Endpunkte sind keine Teilungspunkte
        if d <= tol and TOL / laenge < t < 1 - TOL / laenge:
            if bd is None or d < bd:
                best, bd = (el, px, py), d
    return best


def leitung_teilen(elemente, x, y, tol=TOL):
    """Teilt eine Leitung, auf deren Inneren (x, y) liegt, in zwei Leitungen.
    Rueckgabe: True, wenn geteilt wurde."""
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
    """Alle Punkte, an denen eine Leitung enden darf (inkl. Verbindungsmitte)."""
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
    """Leitungen, die an `v` enden UND am anderen Ende einen Gegenpart
    (Pin, Verbindung, Klemme, Querverweis) haben."""
    anker = _ankerpunkte(elemente, ausser=v)
    mein = _verb_punkte(v)
    res = []
    for l in elemente:
        if not isinstance(l, Leitung):
            continue
        e1, e2 = (l.x1, l.y1), (l.x2, l.y2)
        an1 = any(_nahe(e1, p) for p in mein)
        an2 = any(_nahe(e2, p) for p in mein)
        if an1 == an2:                       # beide oder keins -> irrelevant
            continue
        fern = e2 if an1 else e1
        if any(_nahe(fern, p) for p in anker):
            res.append(l)
    return res


def vollstaendige_verbindungen(elemente):
    """ids der Verbindungen, die aktuell mindestens zwei Leitungen mit
    Gegenpart haben (= 'verbunden')."""
    return {id(v) for v in elemente
            if isinstance(v, Verbindung)
            and len(_gueltige_leitungen(v, elemente)) >= 2}


def _anker_enden(l, anker):
    return (any(_nahe((l.x1, l.y1), p) for p in anker)
            and any(_nahe((l.x2, l.y2), p) for p in anker))


def vollstaendige_leitungen(elemente):
    """ids der Leitungen, die an BEIDEN Enden einen Gegenpart haben
    (Pin, Verbindung, Klemme oder Querverweis)."""
    anker = _ankerpunkte(elemente)
    return {id(l) for l in elemente
            if isinstance(l, Leitung) and _anker_enden(l, anker)}


def verbindungen_bereinigen(elemente, vorher, vorher_leitungen=()):
    """Raeumt nach dem Loeschen auf (in place, kaskadierend):
      - Leitungen, die vorher an beiden Enden angeschlossen waren
        (`vorher_leitungen` = Ergebnis von vollstaendige_leitungen) und
        jetzt an einem Ende keinen Gegenpart mehr haben, verschwinden;
      - Verbindungen, die vorher verbunden waren (`vorher` = Ergebnis von
        vollstaendige_verbindungen) und weniger als zwei gueltige Leitungen
        haben, verschwinden samt der daran haengenden Leitungen.
    Rueckgabe: (anzahl_verbindungen, anzahl_leitungen)."""
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
# Automatisches Unterbrechen von Leitungen durch aufgesetzte Geraete
# ============================================================
def einrast_punkte(el):
    """Punkte eines Objekts, an denen eine darunterliegende Leitung
    unterbrochen und angeschlossen wird: Pin, Verbindung (Mitte), Klemme
    (oben/unten) und alle diese Punkte in Bloecken (Geraeten)."""
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
    """Setzt man ein Objekt (Pin, Verbindung, Klemme, Geraet) auf eine
    Leitung, wird diese unterbrochen:
      - ein Punkt auf der Leitung  -> Leitung in zwei Teile, beide am Punkt
      - mehrere Punkte (z. B. oben/unten am Geraet) -> die Leitung endet am
        ersten Punkt und beginnt am letzten wieder; dazwischen (im Geraet)
        entfaellt sie.
    Jedes neue Objekt wird einzeln behandelt. Rueckgabe: Anzahl der
    unterbrochenen Leitungen."""
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

