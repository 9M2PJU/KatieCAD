# -*- coding: utf-8 -*-
"""
katiecad_elektro.py - Logik fuer Elektro-Plaene (KEIN Tkinter).

Querverweise: Zwei oder mehr Querverweis-Pfeile mit gleichem Text gehoeren
zusammen. Jeder zeigt als Ziel die Blattnummer(n) der anderen.
"""

from collections import Counter, defaultdict

from katiecad_core import Querverweis, Verbindungspunkt, BlockReferenz
from katiecad_i18n import tr


def qv_texte_aus_blattdaten(daten):
    """Querverweis-Texte aus den JSON-Daten eines Blattes (ohne Objekte)."""
    texte = []
    if not isinstance(daten, dict):
        return texte
    for d in daten.get("elemente", []):
        if isinstance(d, dict) and d.get("typ") == "querverweis":
            t = str(d.get("text", "")).strip()
            if t:
                texte.append(t)
    return texte


def qv_texte_aus_elementen(elemente):
    return [e.text.strip() for e in elemente
            if isinstance(e, Querverweis) and e.text.strip()]


def querverweis_ziele(elemente, blatt_nr, andere_blaetter):
    """Setzt `ziel` an allen Querverweisen von `elemente`.

    elemente:        Elemente des Blattes mit der Nummer `blatt_nr`
    andere_blaetter: {blatt_nr: [texte, ...]} fuer alle uebrigen Blaetter
    """
    qvs = [e for e in elemente if isinstance(e, Querverweis)]
    if not qvs:
        return
    vorkommen = defaultdict(Counter)            # text -> Counter(blatt_nr)
    for t in qv_texte_aus_elementen(qvs):
        vorkommen[t][blatt_nr] += 1
    for nr, texte in andere_blaetter.items():
        for t in texte:
            vorkommen[t][nr] += 1
    for qv in qvs:
        t = qv.text.strip()
        if not t:
            qv.ziel = []
            continue
        # eigenes Blatt zaehlt nur, wenn dort ein weiterer Verweis liegt
        qv.ziel = sorted(nr for nr, n in vorkommen[t].items()
                         if nr != blatt_nr or n >= 2)


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


def anschlusspunkte(elemente, sichtbar=lambda el: True):
    """Alle Leitungs-Anschlusspunkte:
       - Verbindungspunkte (auch aus Bloecken)
       - Querverweise: NUR Basis und Spitze des Pfeils"""
    out = []
    for el in elemente:
        if not sichtbar(el):
            continue
        if isinstance(el, Querverweis):
            t = el.text or "-"
            bx, by = el.basis_punkt()
            sx, sy = el.spitze_punkt()
            out.append(Anschluss(bx, by, tr("an.qv_basis", text=t)))
            out.append(Anschluss(sx, sy, tr("an.qv_spitze", text=t)))
        elif isinstance(el, Verbindungspunkt):
            out.append(Anschluss(el.x, el.y, tr("an.vp", text=el.wert or "-")))
        elif isinstance(el, BlockReferenz):
            for k in el.aufgeloest():
                if isinstance(k, Verbindungspunkt):
                    out.append(Anschluss(k.x, k.y,
                                         tr("an.vp", text=k.wert or "-")))
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
