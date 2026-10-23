# -*- coding: utf-8 -*-
"""
katiecad/reports/netz.py - Netzverfolgung ueber alle Blaetter (KEIN Tkinter).

Aus den Anschlusspunkten (Pins, Klemmen, Verbindungen, Querverweise) und den
Leitungen aller Blaetter entsteht ein Graph. Von einer Klemmenseite oder
einem Kabelende aus laesst sich so feststellen, WOHIN eine Leitung fuehrt
(Geraet:Pin, Klemme, Potentialverweis) - auch ueber Verbindungen, Kabel und
Blattgrenzen hinweg.

Regeln
  * Pins und Klemmen sind Endpunkte: die Suche geht nicht durch sie hindurch.
  * Eine Verbindung verbindet alle ihre Arme; eine Kreuzung (4 Arme) ohne
    Punkt verbindet nur gegenueberliegende Arme.
  * Zwei Anschlusspunkte verschiedener Objekte, die genau aufeinander liegen
    (< 0,1 mm), gelten als verbunden.
  * Querverweise mit gleichem Text setzen die Leitung auf einem anderen Blatt
    fort, wenn es genau EINEN abgehenden und mindestens einen ankommenden
    (oder umgekehrt) gibt. Sonst bleibt der Querverweis ein Endpunkt
    (z. B. ein Potential wie L1, das an vielen Stellen vorkommt).
"""

import math
from collections import defaultdict

from katiecad.model.core import (BlockReferenz, Verbindungspunkt, Verbindung,
                                 Klemme, Querverweis, Leitung, Kabel)

SUCH_TOL = 0.4          # mm: Leitungsende -> Anschlusspunkt
BERUEHRUNG = 0.1        # mm: aufeinanderliegende Anschlusspunkte
ZELLE = 1.0             # mm: Rastergroesse fuer die Nachbarschaftssuche
ADER_TOL = 1.0          # mm: Leitung -> naechste Aderkreuzung des Kabels


class Knoten:
    __slots__ = ("blatt", "x", "y", "art", "bes", "kennz", "name", "seite",
                 "kanten", "text", "qv_art", "partner")

    def __init__(self, blatt, x, y, art, bes=None, kennz="", name="",
                 seite="", text="", qv_art=""):
        self.blatt, self.x, self.y, self.art = blatt, x, y, art
        self.bes = bes                  # Besitzer (Element), zum Vergleich
        self.kennz = kennz              # Geraet / Klemmleiste
        self.name = name                # Pin- bzw. Klemmennummer
        self.seite = seite              # Klemme: "oben" | "unten"
        self.kanten = []
        self.text = text                # Querverweis-Text
        self.qv_art = qv_art
        self.partner = []               # Querverweis-Gegenstuecke


class Kante:
    __slots__ = ("a", "b", "kabel")

    def __init__(self, a, b, kabel=None):
        self.a, self.b, self.kabel = a, b, kabel   # kabel: (CAB, Ader) | None


def _verbinden(a, b, kabel=None):
    if a is b:
        return None
    k = Kante(a, b, kabel)
    a.kanten.append(k)
    b.kanten.append(k)
    return k


def wert_gesetzt(wert, tag):
    """Feldwert ohne Platzhalter: leer oder gleich dem Feldnamen ('IND' im
    Feld IND, wie ihn die Vorlage eines Symbols anzeigt) gilt als nicht
    ausgefuellt."""
    w = ("" if wert is None else str(wert)).strip()
    return "" if w.upper() == str(tag).upper() else w


class Netz:
    def __init__(self):
        self.knoten = []
        self._raster = defaultdict(list)
        self.klemmen = []        # {"obj", "blatt", "oben", "unten"}
        self.kabel = []          # {"obj", "blatt", "adern": [{"name","kanten"}]}
        self._leitung = {}       # id(Leitung) -> Kante

    # ---- Aufbau ---------------------------------------------------
    def _neu(self, blatt, x, y, art, **kw):
        n = Knoten(blatt, x, y, art, **kw)
        self.knoten.append(n)
        self._raster[(blatt, int(math.floor(x / ZELLE)),
                      int(math.floor(y / ZELLE)))].append(n)
        return n

    def _naehe(self, blatt, x, y, tol):
        gx, gy = int(math.floor(x / ZELLE)), int(math.floor(y / ZELLE))
        r = int(math.ceil(tol / ZELLE))
        for ix in range(gx - r, gx + r + 1):
            for iy in range(gy - r, gy + r + 1):
                for k in self._raster.get((blatt, ix, iy), ()):
                    d = math.hypot(k.x - x, k.y - y)
                    if d <= tol:
                        yield d, k

    def _finde(self, blatt, x, y):
        best = min(self._naehe(blatt, x, y, SUCH_TOL), default=None,
                   key=lambda t: t[0])
        return best[1] if best else None

    def _anker(self, blatt, k, bes, kennz):
        if isinstance(k, Verbindungspunkt):
            self._neu(blatt, k.x, k.y, "pin", bes=bes, kennz=kennz,
                      name=(k.wert or "").strip())
        elif isinstance(k, Verbindung):
            arme = [(self._neu(blatt, ax, ay, "verb", bes=bes), d)
                    for (ax, ay, d) in k.anschluesse()]
            kreuzung = k.art == 4 and not k.punkt
            for i, (a, da) in enumerate(arme):
                for b, db in arme[i + 1:]:
                    if not kreuzung or (da - db) % 360 == 180:
                        _verbinden(a, b)
        elif isinstance(k, Klemme):
            ox, oy = k.anschluss_oben()
            ux, uy = k.anschluss_unten()
            kz = wert_gesetzt(k.werte.get("IND"), "IND")
            nm = wert_gesetzt(k.werte.get("NUM"), "NUM")
            oben = self._neu(blatt, ox, oy, "klemme", bes=bes, kennz=kz,
                             name=nm, seite="oben")
            unten = self._neu(blatt, ux, uy, "klemme", bes=bes, kennz=kz,
                              name=nm, seite="unten")
            self.klemmen.append({"obj": k, "blatt": blatt, "leiste": kz,
                                 "oben": oben, "unten": unten})
        elif isinstance(k, Querverweis):
            if k.art == "abgehend":
                x, y = k.basis_punkt()
            else:
                x, y = k.spitze_punkt()
            self._neu(blatt, x, y, "qv", bes=bes, text=k.text.strip(),
                      qv_art=k.art)

    def _leisten_erben(self, klemmen):
        """Klemmen ohne Klemmleiste uebernehmen die der naechsten Klemme links
        davon in derselben Reihe (die Leiste wird meist nur an der ersten
        Klemme eingetragen)."""
        reihen = []
        for kl in sorted(klemmen, key=lambda c: (c["obj"].y, c["obj"].x)):
            if reihen and abs(reihen[-1][0] - kl["obj"].y) <= 0.5:
                reihen[-1][1].append(kl)
            else:
                reihen.append([kl["obj"].y, [kl]])
        for _y, reihe in reihen:
            aktuell = ""
            for kl in sorted(reihe, key=lambda c: c["obj"].x):
                if kl["leiste"]:
                    aktuell = kl["leiste"]
                elif aktuell:
                    kl["leiste"] = aktuell
                    kl["geerbt"] = True
                    kl["oben"].kennz = kl["unten"].kennz = aktuell

    def blatt_hinzufuegen(self, blatt, elemente):
        """`blatt`: beliebiger Schluessel (z. B. 0-basierter Index)."""
        start = len(self.knoten)
        start_kl = len(self.klemmen)
        for el in elemente:
            if isinstance(el, BlockReferenz):
                kz = (wert_gesetzt(el.attribute.get("IND"), "IND")
                      or str(el.block_name))
                for k in el.aufgeloest():
                    self._anker(blatt, k, el, kz)
            else:
                self._anker(blatt, el, el, "")
        self._leisten_erben(self.klemmen[start_kl:])
        neue = self.knoten[start:]
        # aufeinanderliegende Anschluesse verschiedener Objekte
        for n in neue:
            for _d, m in self._naehe(blatt, n.x, n.y, BERUEHRUNG):
                if m is not n and m.bes is not n.bes and id(m) > id(n):
                    _verbinden(n, m)
        # Leitungen
        for l in elemente:
            if not isinstance(l, Leitung):
                continue
            a = (self._finde(blatt, l.x1, l.y1)
                 or self._neu(blatt, l.x1, l.y1, "frei"))
            b = (self._finde(blatt, l.x2, l.y2)
                 or self._neu(blatt, l.x2, l.y2, "frei"))
            k = _verbinden(a, b)
            if k is not None:
                self._leitung[id(l)] = k
        self._kabel_adern(blatt, elemente)

    def _kabel_adern(self, blatt, elemente):
        kabel = [k for k in elemente if isinstance(k, Kabel)]
        if not kabel:
            return
        senkrecht = [l for l in elemente if isinstance(l, Leitung)
                     and abs(l.x1 - l.x2) <= 0.05 and id(l) in self._leitung]
        for kb in kabel:
            xs = sorted(kb.kreuzungen)
            adern = [{"name": kb.ader_name(i, cx - kb.x), "x": cx, "kanten": []}
                     for i, cx in enumerate(xs)]
            for l in senkrecht:
                lo, hi = sorted((l.y1, l.y2))
                if not (lo + 0.05 < kb.y < hi - 0.05):
                    continue
                if not (kb.x + 0.05 < l.x1 <= kb.x + kb.laenge + 0.05):
                    continue
                if not adern:
                    continue
                best = min(adern, key=lambda a: abs(a["x"] - l.x1))
                if abs(best["x"] - l.x1) <= ADER_TOL:
                    kante = self._leitung[id(l)]
                    kante.kabel = (kb.werte.get("CAB", "").strip(), best["name"])
                    best["kanten"].append(kante)
            self.kabel.append({"obj": kb, "blatt": blatt, "adern": adern})

    def abschliessen(self):
        """Querverweis-Gegenstuecke bestimmen (nach dem letzten Blatt)."""
        gruppen = defaultdict(list)
        for n in self.knoten:
            if n.art == "qv" and n.text:
                gruppen[n.text].append(n)
        for g in gruppen.values():
            ab = [n for n in g if n.qv_art == "abgehend"]
            an = [n for n in g if n.qv_art == "ankommend"]
            if len(ab) == 1 and an:
                ab[0].partner = list(an)
                for n in an:
                    n.partner = list(ab)
            elif len(an) == 1 and ab:
                an[0].partner = list(ab)
                for n in ab:
                    n.partner = list(an)

    @classmethod
    def aufbauen(cls, blaetter):
        """blaetter: [(schluessel, elemente), ...]"""
        netz = cls()
        for schluessel, elemente in blaetter:
            netz.blatt_hinzufuegen(schluessel, elemente)
        netz.abschliessen()
        return netz

    # ---- Abfragen ---------------------------------------------------
    def ziele(self, start, ohne=()):
        """Alle Endpunkte, die von `start` aus erreichbar sind.
        -> [(knoten, kabel_infos)], kabel_infos = ((CAB, Ader), ...)
        `ohne`: Kanten, die nicht benutzt werden duerfen."""
        verboten = {id(k) for k in ohne}
        out = []
        gesehen = {id(start)}
        stapel = [(start, ())]
        while stapel:
            n, via = stapel.pop()
            for k in n.kanten:
                if id(k) in verboten:
                    continue
                m = k.b if k.a is n else k.a
                if id(m) in gesehen:
                    continue
                gesehen.add(id(m))
                v = via + ((k.kabel,) if k.kabel else ())
                if m.art in ("pin", "klemme"):
                    out.append((m, v))
                elif m.art == "qv":
                    if m.partner:
                        for p in m.partner:
                            if id(p) not in gesehen:
                                gesehen.add(id(p))
                                stapel.append((p, v))
                    else:
                        out.append((m, v))
                else:
                    stapel.append((m, v))
        return out


def ende_ziele(netz, knoten, kante):
    """Ziele am Ende einer Ader/Leitung `kante` bei `knoten`: der Endpunkt
    selbst (Pin, Klemme, Querverweis) oder, wenn dort eine Verbindung sitzt,
    alles, was dahinter hängt."""
    if knoten.art in ("pin", "klemme") or (knoten.art == "qv" and not knoten.partner):
        return [(knoten, ())]
    if knoten.art == "qv":
        out = []
        for p in knoten.partner:
            out.extend(netz.ziele(p))
        return out
    return netz.ziele(knoten, ohne=[kante])


def knoten_text(n):
    """Lesbarer Name eines Endpunkts: 'K1:13', 'X1:3', '→ L1'."""
    if n.art == "qv":
        return "→ " + n.text
    if n.kennz and n.name:
        return f"{n.kennz}:{n.name}"
    return n.kennz or n.name or "?"


def ziele_texte(treffer, eigener_besitzer=None):
    """Sortierte, eindeutige Texte; Kabel, die der Weg durchquert, stehen
    in Klammern: 'K1:13 (W1/L1)'."""
    gesehen = {}
    for n, via in treffer:
        if eigener_besitzer is not None and n.bes is eigener_besitzer:
            continue
        t = knoten_text(n)
        if via:
            t += " (" + " ".join(f"{c}/{a}" if c else a for c, a in via) + ")"
        gesehen.setdefault(t, True)
    return sorted(gesehen, key=natuerlich)


def natuerlich(s):
    """Sortierschluessel: 'X10' hinter 'X2'."""
    import re
    return tuple((0, int(t)) if t.isdigit() else (1, t.lower())
                 for t in re.split(r"(\d+)", str(s)) if t != "")
