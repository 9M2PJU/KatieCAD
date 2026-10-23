# -*- coding: utf-8 -*-
"""
katiecad/reports/seiten.py - Assemble report sheets (NO Tkinter).

Creates cover sheet, table of contents, device list, terminal diagram and
cable plan as lists of layout elements (A4 landscape, sheet frame and
title block from the chosen template). The application writes ordinary
sheets into the project from them.

Order of the sheets:
    cover sheet, table of contents | drawing sheets | device list,
    terminal diagram, cable plan
The sheet numbers of the drawing sheets depend on the number of sheets
before them; the function iterates until the page counts are stable.
"""

import datetime
import json
import os

from katiecad.model.core import (Text, Linie, Rechteck, FARBEN,
                                 ZEICHNUNGSFORMATE)
from katiecad.model import titleblock as TB
from katiecad.common.i18n import tr
from katiecad.reports import daten as D
from katiecad.reports.netz import Netz
from katiecad.reports.tabelle import (Spalte, tabellen_seiten,
                                      zeilen_vorbereiten, TEXT, LINIE)

FORMAT = "A4 (297x210)"
TYPEN = ("deckblatt", "inhalt", "geraete", "klemmen", "kabel")
LISTEN = ("geraete", "klemmen", "kabel")

# Keys of the project data -> tags in the title block (German / English)
TITEL_TAGS = {
    "gezeichnet": ("GEZEICHNET", "DRAWN"),
    "gezeichnet_datum": ("GEZEICHNET_DATUM", "DRAWN_DATE"),
    "geprueft": ("GEPRUEFT", "VERIFIED"),
    "geprueft_datum": ("GEPRUEFT_DATUM", "VERIFIED_DATE"),
    "zeichnungsnummer": ("ZEICHNUNGSNUMMER", "DRAWINGNUMBER"),
    "firma": ("FIRMA", "COMPANY"),
    "kunde": ("KUNDE", "CUSTOMER"),
    "auftrag": ("AUFTRAG", "ORDER"),
    "anlage": ("ANLAGE", "PLANT"),
    "revision": ("REVISION",),
}
DATEN_SCHLUESSEL = ("anlage", "kunde", "auftrag", "zeichnungsnummer", "firma",
                    "gezeichnet", "geprueft", "revision", "datum")


class BlattInfo:
    """A drawing sheet of the project (without report sheets)."""

    def __init__(self, name, elemente, beschreibung=""):
        self.name = name
        self.elemente = elemente
        self.beschreibung = beschreibung


class BerichtSeite:
    def __init__(self, typ, name, elemente):
        self.typ, self.name, self.elemente = typ, name, elemente


class Vorlage:
    """Title block template (elements with origin at the bottom right)."""

    def __init__(self, name, elemente):
        self.name = name
        self.elemente = list(elemente)
        xs, ys = [0.0], [0.0]
        for e in self.elemente:
            b = e.bbox()
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
        self.breite = max(0.0, -min(xs))
        self.hoehe = max(0.0, max(ys))


# ------------------------------------------------------------------
# Column definitions (customisable via report_templates/<type>.json)
# ------------------------------------------------------------------
_STANDARD = {
    "inhalt": [("nr", "rep.col.blatt", 8, "r"), ("name", "rep.col.bezeichnung", 40, "l"),
               ("beschreibung", "rep.col.beschreibung", 70, "l"),
               ("typ", "rep.col.art", 24, "l")],
    "geraete": [("pos", "rep.col.pos", 6, "r"), ("ind", "rep.col.ind", 18, "l"),
                ("typ", "rep.col.typ", 40, "l"), ("per", "rep.col.per", 40, "l"),
                ("anzahl", "rep.col.anzahl", 9, "r"),
                ("ort", "rep.col.fundstellen", 50, "l")],
    "klemmen": [("leiste", "rep.col.leiste", 16, "l"), ("num", "rep.col.num", 10, "l"),
                ("typ", "rep.col.typ", 26, "l"), ("oben", "rep.col.oben", 48, "l"),
                ("unten", "rep.col.unten", 48, "l"), ("ort", "rep.col.ort", 20, "l")],
    "kabel": [("cab", "rep.col.cab", 14, "l"), ("typ", "rep.col.typ", 26, "l"),
              ("ader", "rep.col.ader", 10, "l"), ("von", "rep.col.von", 50, "l"),
              ("nach", "rep.col.nach", 50, "l"), ("ort", "rep.col.ort", 18, "l")],
}
_OPTIONEN = {"textgroesse": 2.5, "zeilenhoehe": 6.0}


def lade_spalten(typ, ordner=()):
    """(columns, options). `ordner`: folders containing <type>.json (later =
    higher priority). Faulty files are ignored."""
    spalten = [Spalte(k, tr(t), g, a) for k, t, g, a in _STANDARD[typ]]
    opt = dict(_OPTIONEN)
    for o in ordner:
        pfad = os.path.join(o, typ + ".json")
        try:
            with open(pfad, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        neue = []
        for s in d.get("spalten", []) if isinstance(d.get("spalten"), list) else []:
            if isinstance(s, dict) and s.get("key"):
                try:
                    neue.append(Spalte(str(s["key"]), str(s.get("titel", s["key"])),
                                       float(s.get("breite", 10)),
                                       str(s.get("ausrichtung", "l"))))
                except (TypeError, ValueError):
                    pass
        if neue:
            spalten = neue
        for k in opt:
            try:
                v = float(d[k])
                if 1.0 <= v <= 20.0:
                    opt[k] = v
            except (KeyError, TypeError, ValueError):
                pass
    return spalten, opt


def spalten_ordner(programm_ordner, projekt_ordner=None):
    out = [os.path.join(programm_ordner, "report_templates")]
    if projekt_ordner:
        out.append(os.path.join(projekt_ordner, "report_templates"))
    return out


# ------------------------------------------------------------------
# Frame, title block, area
# ------------------------------------------------------------------
def _rahmen():
    b, h = ZEICHNUNGSFORMATE[FORMAT]
    aussen, innen = TB.frame_rects(b, h)
    dick = {"layer": "0", "farbe": FARBEN["cyan"], "linientyp": "Volllinie (breit)",
            "eig_farbe": True, "staerke": 0.7}
    duenn = {"layer": "0", "farbe": FARBEN["cyan"], "linientyp": "Volllinie (schmal)",
             "eig_farbe": True, "staerke": 0.35}
    return aussen, innen, [Rechteck(*aussen, **dick), Rechteck(*innen, **duenn)]


def inhaltsflaeche(vorlage):
    """(x1, y1, x2, y2) for tables: sheet frame minus title block."""
    _a, innen, _el = _rahmen()
    tb = vorlage.hoehe if vorlage is not None else 0.0
    return (innen[0] + 2.0, innen[1] + tb + 3.0, innen[2] - 2.0, innen[3] - 3.0)


def kurzes_datum(heute, sprache):
    """Short date for narrow title block fields (15 mm): 23.10.26 / 26-10-23."""
    return heute.strftime("%d.%m.%y") if sprache == "de" else heute.strftime("%y-%m-%d")


def titel_werte(daten, titel1, projektname, heute, sprache):
    """Tag values for the title block from the project data."""
    d = dict(daten)
    if d.get("gezeichnet") or d.get("datum"):
        d["gezeichnet_datum"] = d.get("gezeichnet_datum") or d.get("datum") \
            or kurzes_datum(heute, sprache)
    werte = {}
    for key, tags in TITEL_TAGS.items():
        v = d.get(key, "")
        if v:
            for t in tags:           # fill in all spellings (unknown
                werte[t] = v         # tags are ignored by the block)
    werte["TITEL1"] = titel1
    werte["TITEL2"] = d.get("anlage") or projektname
    werte["TITEL3"] = d.get("kunde", "")
    werte["TITLE"] = titel1
    return werte


def _seite(typ, name, titel1, inhalt, ctx, nr, gesamt):
    """Frame + content + title block of a report page."""
    _a, _i, rahmen = _rahmen()
    el = list(rahmen) + list(inhalt)
    v = ctx["vorlage"]
    if v is not None:
        b, h = ZEICHNUNGSFORMATE[FORMAT]
        ref = TB.make_block(v.name, v.elemente, b, h, layer="0")
        ref.setze_attribute(titel_werte(ctx["daten"], titel1, ctx["projekt"],
                                        ctx["heute"], ctx["sprache"]))
        info = TB.info_values(nr, gesamt, name, ctx["projekt"], ctx["sprache"],
                              FORMAT, ctx["heute"])
        TB.refresh_fields([ref], info, "")
        el.append(ref)
    return BerichtSeite(typ, name, el)


# ------------------------------------------------------------------
# Cover sheet
# ------------------------------------------------------------------
def deckblatt_inhalt(daten, projektname, flaeche, heute, sprache):
    x1, y1, x2, y2 = flaeche
    cx = (x1 + x2) / 2.0
    hoehe = y2 - y1
    el = []
    anlage = daten.get("anlage") or projektname
    el.append(Text(cx, y2 - 0.26 * hoehe, anlage, 10.0, 0.0, "Arial",
                   einfuegepunkt="mitte_zentriert", **TEXT))
    el.append(Text(cx, y2 - 0.38 * hoehe, tr("rep.deck.untertitel"), 5.0, 0.0,
                   "Arial", einfuegepunkt="mitte_zentriert", **TEXT))
    ly = y2 - 0.45 * hoehe
    el.append(Linie(cx - 70, ly, cx + 70, ly, staerke=0.5, **LINIE))
    datum = daten.get("datum") or (heute.strftime("%d.%m.%Y") if sprache == "de"
                                   else heute.strftime("%Y-%m-%d"))
    zeilen = [(tr("rep.deck.kunde"), daten.get("kunde", "")),
              (tr("rep.deck.auftrag"), daten.get("auftrag", "")),
              (tr("rep.deck.zeichnungsnummer"), daten.get("zeichnungsnummer", "")),
              (tr("rep.deck.firma"), daten.get("firma", "")),
              (tr("rep.deck.gezeichnet"), daten.get("gezeichnet", "")),
              (tr("rep.deck.geprueft"), daten.get("geprueft", "")),
              (tr("rep.deck.revision"), daten.get("revision", "")),
              (tr("rep.deck.datum"), datum)]
    zeilen = [(k, v) for k, v in zeilen if v]
    start = ly - 10.0
    schritt = min(8.0, max(4.5, (start - y1 - 2.0) / max(1, len(zeilen))))
    for i, (k, v) in enumerate(zeilen):
        y = start - i * schritt
        el.append(Text(cx - 4.0, y, k, 3.5, 0.0, "Arial",
                       einfuegepunkt="mitte_rechts", **TEXT))
        el.append(Text(cx + 4.0, y, v, 3.5, 0.0, "Arial",
                       einfuegepunkt="mitte_links", **TEXT))
    return el


# ------------------------------------------------------------------
# Rows per report type (also for the CSV export)
# ------------------------------------------------------------------
def listen_zeilen(typ, blaetter, nummer, netz=None, klemmen_in_geraeteliste=True):
    """Rows of a list report. blaetter: [(idx, elements)]."""
    if typ == "geraete":
        return D.geraeteliste(blaetter, nummer, netz, klemmen_in_geraeteliste)
    if typ == "klemmen":
        return D.klemmenplan(netz, blaetter, nummer)
    if typ == "kabel":
        return D.kabelplan(netz, blaetter, nummer)
    raise ValueError(typ)


def netz_aufbauen(blaetter):
    return Netz.aufbauen(blaetter)


def tabellen_fuer_export(blaetter, nummer, ordner=(), klemmen_in_geraeteliste=True):
    """{type: (columns, rows)} for device list, terminal diagram, cable plan."""
    netz = netz_aufbauen(blaetter)
    out = {}
    for typ in LISTEN:
        spalten, _opt = lade_spalten(typ, ordner)
        out[typ] = (spalten, listen_zeilen(typ, blaetter, nummer, netz,
                                           klemmen_in_geraeteliste))
    return out


_GRUPPE = {"klemmen": ("leiste", ("leiste",)), "kabel": ("cab", ("cab", "typ"))}


def _liste_tabelle(typ, zeilen, ordner, flaeche, titel):
    spalten, opt = lade_spalten(typ, ordner)
    gruppe, leer = _GRUPPE.get(typ, (None, ()))
    if gruppe:
        zeilen = zeilen_vorbereiten(zeilen, gruppe, leer)
    return tabellen_seiten(spalten, zeilen, flaeche, titel,
                           opt["textgroesse"], opt["zeilenhoehe"],
                           tr("rep.leer"))


def _name(basis, k, n):
    return basis if n == 1 else f"{basis} {k}/{n}"


# ------------------------------------------------------------------
# Main function
# ------------------------------------------------------------------
def berichte_erzeugen(blaetter, projektname, daten, aktiv, vorlage, sprache,
                      ordner=(), heute=None, klemmen_in_geraeteliste=True):
    """Creates the requested report sheets.

    blaetter: [BlattInfo] of the drawing sheets in project order
    aktiv:    set of requested types from TYPEN
    vorlage:  template or None (without title block)
    -> (vorne, hinten): lists of BerichtSeite"""
    heute = heute or datetime.date.today()
    aktiv = set(aktiv)
    ctx = {"vorlage": vorlage, "daten": dict(daten), "projekt": projektname,
           "heute": heute, "sprache": sprache}
    flaeche = inhaltsflaeche(vorlage)
    basis = [(i, b.elemente) for i, b in enumerate(blaetter)]
    brauchen_netz = bool(aktiv & {"klemmen", "kabel"}) or (
        "geraete" in aktiv and klemmen_in_geraeteliste)
    netz = netz_aufbauen(basis) if brauchen_netz else None
    namen = {t: tr("rep." + t) for t in TYPEN}

    n_deck = 1 if "deckblatt" in aktiv else 0
    n_inh = 1 if "inhalt" in aktiv else 0
    for _ in range(8):
        vorn = n_deck + n_inh

        def nummer(idx, v=vorn):
            return v + idx + 1

        listen = {}
        for typ in LISTEN:
            if typ in aktiv:
                zeilen = listen_zeilen(typ, basis, nummer, netz,
                                       klemmen_in_geraeteliste)
                listen[typ] = _liste_tabelle(typ, zeilen, ordner, flaeche,
                                             namen[typ])
        hinten_n = sum(len(p) for p in listen.values())
        gesamt = vorn + len(blaetter) + hinten_n
        if "inhalt" not in aktiv:
            break
        # Table-of-contents entries in sheet order
        eintraege = []
        if n_deck:
            eintraege.append((namen["deckblatt"], "", namen["deckblatt"]))
        for k in range(n_inh):
            eintraege.append((_name(namen["inhalt"], k + 1, n_inh), "",
                              namen["inhalt"]))
        for b in blaetter:
            eintraege.append((b.name, b.beschreibung, tr("rep.art.zeichnung")))
        for typ in LISTEN:
            seiten = listen.get(typ, [])
            for k in range(len(seiten)):
                eintraege.append((_name(namen[typ], k + 1, len(seiten)), "",
                                  namen[typ]))
        zeilen = D.inhaltsverzeichnis(
            [{"nr": i + 1, "name": n, "beschreibung": b, "typ": t}
             for i, (n, b, t) in enumerate(eintraege)])
        spalten, opt = lade_spalten("inhalt", ordner)
        inh_seiten = tabellen_seiten(spalten, zeilen, flaeche, namen["inhalt"],
                                     opt["textgroesse"], opt["zeilenhoehe"],
                                     tr("rep.leer"))
        if len(inh_seiten) == n_inh:
            break
        n_inh = len(inh_seiten)

    vorne, nr = [], 0
    if n_deck:
        nr += 1
        vorne.append(_seite("deckblatt", namen["deckblatt"], namen["deckblatt"],
                            deckblatt_inhalt(ctx["daten"], projektname, flaeche,
                                             heute, sprache), ctx, nr, gesamt))
    if "inhalt" in aktiv:
        n = len(inh_seiten)
        for k, el in enumerate(inh_seiten):
            nr += 1
            vorne.append(_seite("inhalt", _name(namen["inhalt"], k + 1, n),
                                namen["inhalt"], el, ctx, nr, gesamt))
    hinten = []
    nr = len(vorne) + len(blaetter)
    for typ in LISTEN:
        seiten = listen.get(typ, [])
        for k, el in enumerate(seiten):
            nr += 1
            hinten.append(_seite(typ, _name(namen[typ], k + 1, len(seiten)),
                                 namen[typ], el, ctx, nr, gesamt))
    return vorne, hinten


def beschreibung_aus_layouts(layouts):
    """Title from the title block (TITEL1..3 or TITLE) of the first layout with a
    title block, e.g. 'Main circuit - drive'."""
    for lay in layouts:
        for e in lay.elemente:
            if TB.is_title_block(e):
                teile = [str(e.attribute.get(t, "")).strip()
                         for t in ("TITEL1", "TITEL2", "TITEL3", "TITLE")]
                teile = [t for t in teile if t]
                if teile:
                    return " - ".join(teile[:2])
    return ""
