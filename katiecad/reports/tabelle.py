# -*- coding: utf-8 -*-
"""
katiecad/reports/tabelle.py - Tables made of lines and texts with
automatic page breaks (NO Tkinter).

The tables consist of ordinary lines and texts. They are therefore
visible in the layout of the report sheet, printable and included in the PDF.
"""

from katiecad.model.core import (Linie, Text, Rechteck, Schraffur, pdf_textbreite,
                                 CAD_VERSALHOEHE, TEXT_ZEILE)

LINIE = dict(layer="0", eig_farbe=False, linientyp="Volllinie (schmal)")
TEXT = dict(layer="Schrift", eig_farbe=False, linientyp="Volllinie (schmal)")

MIN_TEXT = 1.6          # mm, smallest text height when shrinking
RAND_X = 1.5            # mm distance text <-> column line
RAND_Y = 1.0            # mm distance text <-> row line
TITEL_HOEHE = 4.0       # mm text height of the table heading
TITEL_PLATZ = 9.0       # mm space for the heading
GRAFIK_SPALTE = "bruecke"   # column with the bridge graphic (rows: _bruecke)
PUNKT_R = 0.9           # mm radius of a bridge dot


def _punkt(x, y):
    """Filled dot (hatch over a 16-gon)."""
    import math
    pts = [(x + PUNKT_R * math.cos(2 * math.pi * i / 16),
            y + PUNKT_R * math.sin(2 * math.pi * i / 16)) for i in range(16)]
    return Schraffur(pts, "solid", staerke=0.25, **LINIE)


def _bruecken_zeichnen(el, z, xa, b, y, hoehe, lanes):
    """Bridge graphic of one row in the column [xa, xa + b]."""
    yc = y - hoehe / 2.0
    for lane, punkt, hoch, runter in z.get("_bruecke", ()):
        x = xa + b * (lane + 1) / (lanes + 1.0)
        if hoch and runter:
            el.append(Linie(x, y, x, y - hoehe, staerke=0.35, **LINIE))
        elif hoch:
            el.append(Linie(x, y, x, yc, staerke=0.35, **LINIE))
        elif runter:
            el.append(Linie(x, yc, x, y - hoehe, staerke=0.35, **LINIE))
        if punkt:
            el.append(_punkt(x, yc))


class Spalte:
    def __init__(self, key, titel, gewicht=1.0, ausr="l"):
        self.key = key
        self.titel = titel
        self.gewicht = max(0.1, float(gewicht))
        self.ausr = ausr if ausr in ("l", "r", "c") else "l"


def spaltenbreiten(spalten, gesamt):
    summe = sum(s.gewicht for s in spalten) or 1.0
    return [gesamt * s.gewicht / summe for s in spalten]


def _fs(hoehe):
    return hoehe / CAD_VERSALHOEHE


def _breite(s, hoehe):
    return pdf_textbreite(s, _fs(hoehe))


def _teile(wert):
    if isinstance(wert, (list, tuple)):
        return [str(w) for w in wert if str(w) != ""], True
    return str(wert if wert is not None else "").split(), False


def _zerhacken(s, breite, hoehe):
    """Distribute a word that is too wide over several lines character by character."""
    out, akt = [], ""
    for ch in s:
        if akt and _breite(akt + ch, hoehe) > breite:
            out.append(akt)
            akt = ch
        else:
            akt += ch
    if akt:
        out.append(akt)
    return out


def umbrechen(wert, breite, hoehe):
    """-> (lines: list[str], effective text height). Shrinks the font
    down to MIN_TEXT if an indivisible piece would not fit otherwise."""
    teile, ist_liste = _teile(wert)
    if not teile:
        return [], hoehe
    h = hoehe
    while h > MIN_TEXT and max(_breite(t, h) for t in teile) > breite:
        h = round(h - 0.1, 3)
    zeilen, akt = [], ""
    for i, t in enumerate(teile):
        tt = t + ("," if ist_liste and i < len(teile) - 1 else "")
        if _breite(tt, h) > breite:                    # too wide even when shrunk
            if akt:
                zeilen.append(akt)
                akt = ""
            stuecke = _zerhacken(tt, breite, h)
            zeilen.extend(stuecke[:-1])
            akt = stuecke[-1]
            continue
        kand = (akt + " " + tt) if akt else tt
        if akt and _breite(kand, h) > breite:
            zeilen.append(akt)
            akt = tt
        else:
            akt = kand
    if akt:
        zeilen.append(akt)
    return zeilen, h


def _blockhoehe(n, h):
    return (n - 1) * TEXT_ZEILE * h + 1.4 * h


def _text(x, y, s, h, ausr):
    anker = {"l": "mitte_links", "r": "mitte_rechts", "c": "mitte_zentriert"}[ausr]
    return Text(x, y, s, h, 0.0, "Arial", einfuegepunkt=anker, **TEXT)


def zeilen_vorbereiten(zeilen, gruppe=None, leer_bei_wiederholung=()):
    """Marks group starts (`_gruppe`) and, on repetition, empties the
    columns `leer_bei_wiederholung` (terminal strip only in the first row)."""
    out, vorher = [], object()
    for z in zeilen:
        z = dict(z)
        if gruppe is not None:
            neu = z.get(gruppe) != vorher
            z["_gruppe"] = neu
            if not neu:
                for k in leer_bei_wiederholung:
                    z[k] = ""
            vorher = z.get(gruppe) if neu else vorher
        out.append(z)
    return out


def tabellen_seiten(spalten, zeilen, flaeche, titel="", textgroesse=2.5,
                    zeilenhoehe=6.0, leer_text=""):
    """Draws the table in `flaeche` = (x1, y1, x2, y2) and, if needed, breaks
    it across several pages (header row is repeated).
    -> list of pages; each page is a list of elements."""
    x1, y1, x2, y2 = flaeche
    breiten = spaltenbreiten(spalten, x2 - x1)
    xs = [x1]
    for b in breiten:
        xs.append(xs[-1] + b)

    kopf_h = max(zeilenhoehe, 1.4 * textgroesse + 2 * RAND_Y)
    for sp, b in zip(spalten, breiten):             # Header row may wrap
        lines, h = umbrechen(sp.titel, b - 2 * RAND_X, textgroesse)
        if lines:
            kopf_h = max(kopf_h, _blockhoehe(len(lines), h) + 2 * RAND_Y)
    # Measure rows
    gemessen = []
    for z in zeilen:
        zellen, hoehe = [], zeilenhoehe
        for sp, b in zip(spalten, breiten):
            if sp.key == GRAFIK_SPALTE:             # graphics only, no text
                zellen.append(([], textgroesse))
                continue
            lines, h = umbrechen(z.get(sp.key, ""), b - 2 * RAND_X, textgroesse)
            zellen.append((lines, h))
            if lines:
                hoehe = max(hoehe, _blockhoehe(len(lines), h) + 2 * RAND_Y)
        gemessen.append((z, zellen, hoehe))
    if not gemessen:
        gemessen = [({}, [([leer_text], textgroesse)] +
                     [([], textgroesse)] * (len(spalten) - 1), zeilenhoehe)] \
            if leer_text else []

    oben = y2 - (TITEL_PLATZ if titel else 0.0)
    frei = oben - kopf_h - y1
    seiten, akt, benutzt = [], [], 0.0
    for eintrag in gemessen:
        h = eintrag[2]
        if akt and benutzt + h > frei + 1e-6:
            seiten.append(akt)
            akt, benutzt = [], 0.0
        akt.append(eintrag)
        benutzt += h
    seiten.append(akt)

    ergebnis = []
    for seite in seiten:
        el = []
        if titel:
            el.append(Text(x1, y2, titel, TITEL_HOEHE, 0.0, "Arial",
                           einfuegepunkt="oben_links", **TEXT))
        unten = oben - kopf_h - sum(e[2] for e in seite)
        # Header row
        for sp, xa, b in zip(spalten, xs, breiten):
            lines, h = umbrechen(sp.titel, b - 2 * RAND_X, textgroesse)
            if lines:
                tx = {"l": xa + RAND_X, "r": xa + b - RAND_X,
                      "c": xa + b / 2.0}[sp.ausr]
                el.append(_text(tx, oben - kopf_h / 2.0, "\n".join(lines),
                                h, sp.ausr))
        # Rows
        y = oben - kopf_h
        lanes = 1 + max([l for e in gemessen for l, *_r in e[0].get("_bruecke", ())] or [0])
        for z, zellen, hoehe in seite:
            yc = y - hoehe / 2.0
            for sp, xa, b, (lines, h) in zip(spalten, xs, breiten, zellen):
                if sp.key == GRAFIK_SPALTE:
                    _bruecken_zeichnen(el, z, xa, b, y, hoehe, lanes)
                    continue
                if not lines:
                    continue
                tx = {"l": xa + RAND_X, "r": xa + b - RAND_X,
                      "c": xa + b / 2.0}[sp.ausr]
                el.append(_text(tx, yc, "\n".join(lines), h, sp.ausr))
            y -= hoehe
            if y > unten + 1e-6:
                st = 0.35 if (z.get("_gruppe") is True) else 0.13
                el.append(Linie(x1, y, x2, y, staerke=st, **LINIE))
        # Group line above the first row needs no extra line
        # (header bottom edge). Grid:
        for xa in xs[1:-1]:
            el.append(Linie(xa, oben, xa, unten, staerke=0.25, **LINIE))
        el.append(Linie(x1, oben - kopf_h, x2, oben - kopf_h, staerke=0.5, **LINIE))
        el.append(Rechteck(x1, unten, x2, oben, staerke=0.5, **LINIE))
        ergebnis.append(el)
    return ergebnis


