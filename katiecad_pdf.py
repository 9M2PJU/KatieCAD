# -*- coding: utf-8 -*-
"""
katiecad_pdf.py - PDF-Erzeugung fuer Modell- und Layout-Ansicht.
Enthaelt KEIN Tkinter. Wird von CadApp aufgerufen.

NEU (Schritt 2): BlockReferenz wird aufgeloest ausgegeben.
NEU (Schritt 8): Schraffuren (Solid und Linien) werden unterstuetzt.
NEU (Elektro): Querverweise, Verbindungspunkt-Beschriftung, mehrseitige PDFs.
"""

import math, os, sys, tempfile, subprocess
from tkinter import messagebox

from katiecad_core import (
    ZEICHNUNGSFORMATE, MASSSTAEBE, LINIENTYPEN, PdfSeite,
    Text, Bemassung, Viewport,
    Linie, Rechteck, Polylinie, Kreis, Bogen,
    BlockReferenz, Schraffur, Querverweis, Verbindungspunkt,
    pdf_mehrseitig,
    bogen_sweep, bogen_punkte,
    normmassstab_unter, massstab_text,
)
from katiecad_i18n import tr, SPRACHE


def _pdf_farbe(el, layers, farbig):
    if not farbig:
        return "#000000"
    f = (el.farbe if getattr(el, "eig_farbe", False)
         else (layers[el.layer].farbe if el.layer in layers
               else el.farbe))
    try:
        h = f.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        if 0.299 * r + 0.587 * g + 0.114 * b > 200:
            return "#000000"
    except Exception:
        return "#000000"
    return f


def _effektive_staerke_mm(el, layers):
    if getattr(el, "staerke", None) is not None:
        return el.staerke
    l = layers.get(el.layer)
    basis = l.staerke if l else 0.35
    if "breit" in (el.linientyp or ""):
        return max(basis * 2, 0.7)
    return basis


def _prims(el, skala, einh_faktor, dezimalkomma):
    """Liefert die Primitiven eines Elements (wie CadApp._prims)."""
    if isinstance(el, Linie):
        return [("l", [(el.x1, el.y1), (el.x2, el.y2)], False)]
    if isinstance(el, Rechteck):
        return [("l", [(el.x1, el.y1), (el.x2, el.y1),
                       (el.x2, el.y2), (el.x1, el.y2)], True)]
    if isinstance(el, Polylinie):
        return [("l", list(el.punkte), el.geschlossen)] if len(el.punkte) >= 2 else []
    if isinstance(el, Kreis):
        n = int(max(24, min(720, el.r * skala * 1.2)))
        pts = [(el.cx + el.r * math.cos(2 * math.pi * i / n),
                el.cy + el.r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        return [("l", pts, True)]
    if isinstance(el, Bogen):
        sw = bogen_sweep(el.start, el.ende)
        n = int(max(6, min(720, el.r * skala * 1.2 * sw / 360.0)))
        return [("l", bogen_punkte(el.cx, el.cy, el.r, el.start, el.ende, n), False)]
    if isinstance(el, Text):
        return [("t", el.x, el.y, el.inhalt, el.hoehe, el.winkel,
                 el.schriftart, el.einfuegepunkt)]
    if isinstance(el, Bemassung):
        g = el.geometrie(einh_faktor, dezimalkomma)
        out = [("l", [(l[0], l[1]), (l[2], l[3])], False) for l in g["linien"]]
        out += [("p", p[0], p[1], p[2], p[3]) for p in g["pfeile"]]
        if g["text"]:
            s, cx, cy, ang, w, h = g["text"]
            out.append(("tc", cx, cy, s, h, ang, "Arial"))
        return out
    return []


def _pdf_element(seite, el, tf, zs, farbig, layers, einh_faktor, dezimalkomma):
    # NEU: Block / Querverweis aufgeloest ausgeben
    if isinstance(el, (BlockReferenz, Querverweis)):
        for kind in el.aufgeloest():
            _pdf_element(seite, kind, tf, zs, farbig, layers,
                         einh_faktor, dezimalkomma)
        return

    # NEU: Verbindungspunkt - der Kreis erscheint nur im Modell, im PDF
    # nur die Beschriftung.
    if isinstance(el, Verbindungspunkt):
        t = el.text_element()
        if t is not None:
            _pdf_element(seite, t, tf, zs, farbig, layers,
                         einh_faktor, dezimalkomma)
        return

    # NEU: Schraffur ausgeben
    if isinstance(el, Schraffur):
        farbe = _pdf_farbe(el, layers, farbig)
        if el.muster == "solid":
            pts = [tf(x, y) for (x, y) in el.punkte]
            seite.flaeche(pts, farbe)
        else:
            # Grenzlinie (optional, hier zeichnen wir sie mit, um saubere Kanten zu haben)
            pts = [tf(x, y) for (x, y) in el.punkte]
            seite.linie(pts, 0.25, farbe, None, True)
            
            # Schraffurlinien
            for (p1, p2) in el.geometrie_linien():
                seite.linie([tf(p1[0], p1[1]), tf(p2[0], p2[1])], 0.18, farbe)
        return

    farbe = _pdf_farbe(el, layers, farbig)
    w = _effektive_staerke_mm(el, layers)
    dash = None
    if not isinstance(el, (Bemassung, Text)):
        lt = LINIENTYPEN.get(el.linientyp, LINIENTYPEN["Volllinie (schmal)"])
        if lt["dash"]:
            dash = tuple(max(0.3, d * 0.45) for d in lt["dash"])
    if isinstance(el, Bemassung):
        w = min(w, 0.25)
    for p in _prims(el, max(zs, 0.05) * 10, einh_faktor, dezimalkomma):
        k = p[0]
        if k == "l":
            seite.linie([tf(x, y) for (x, y) in p[1]], w, farbe, dash, p[2])
        elif k == "p":
            _, x, y, ang, L = p
            ux, uy = math.cos(ang), math.sin(ang)
            bx, by = x - ux * L, y - uy * L
            hw = L / 6.0
            seite.flaeche([tf(x, y), tf(bx - uy * hw, by + ux * hw),
                           tf(bx + uy * hw, by - ux * hw)], farbe)
        else:
            if len(p) == 8:
                art, x, y, inhalt, hoehe, winkel, fam, einfuegepunkt = p
            else:
                art, x, y, inhalt, hoehe, winkel, fam = p
                einfuegepunkt = "unten_links"
            tmp = Text(x, y, inhalt, hoehe, winkel, fam,
                       einfuegepunkt=einfuegepunkt)
            w_mm, h_mm = tmp.masse()
            dxl, dyl = tmp._versatz_lokal(w_mm, h_mm)
            a = math.radians(winkel)
            ex = (math.cos(a), math.sin(a))
            ey = (-math.sin(a), math.cos(a))
            ux_mm = x + dxl * ex[0] + dyl * ey[0]
            uy_mm = y + dxl * ex[1] + dyl * ey[1]
            baseline_x = ux_mm + 0.3 * hoehe * ey[0]
            baseline_y = uy_mm + 0.3 * hoehe * ey[1]
            ox, oy = tf(baseline_x, baseline_y)
            seite.text(ox, oy, inhalt, hoehe * zs, winkel, farbe, mitte=False)


def _pdf_viewport(seite, vp, elemente, layers, farbig, rahmen,
                  einh_faktor, dezimalkomma):
    z = vp.zoom
    cxp, cyp = vp.x + vp.breite / 2, vp.y + vp.hoehe / 2

    def tf(mx, my):
        return (cxp + (mx - vp.modell_zentrum_x) * z,
                cyp + (my - vp.modell_zentrum_y) * z)

    seite.clip_start(vp.x, vp.y, vp.x + vp.breite, vp.y + vp.hoehe)
    for me in elemente:
        l = layers.get(me.layer)
        if l and not l.sichtbar:
            continue
        b = me.bbox()
        ax, ay = tf(b[0], b[1])
        bx, by = tf(b[2], b[3])
        if (max(ax, bx) < vp.x or min(ax, bx) > vp.x + vp.breite or
                max(ay, by) < vp.y or min(ay, by) > vp.y + vp.hoehe):
            continue
        _pdf_element(seite, me, tf, z, farbig, layers, einh_faktor, dezimalkomma)
    seite.clip_ende()
    if rahmen:
        seite.linie([(vp.x, vp.y), (vp.x + vp.breite, vp.y),
                     (vp.x + vp.breite, vp.y + vp.hoehe),
                     (vp.x, vp.y + vp.hoehe)],
                    0.25, "#000000", None, True)


def pdf_seite_erzeugen(app, quelle, farbig, vp_rahmen, layout_index=None):
    """Erzeugt eine PdfSeite fuer Modell oder Layout.
    app muss bieten: elemente, layers, layouts, aktives_layout,
                     layout_format, _einh_faktor(), dezimalkomma.get()."""
    de = SPRACHE["aktuell"] == "de"
    einh = app._einh_faktor()
    komma = app.dezimalkomma.get()

    if quelle == "layout":
        if layout_index is None:
            layout_index = app.aktives_layout
        lay = app.layouts[layout_index]
        b, h = ZEICHNUNGSFORMATE[lay.format]
        seite = PdfSeite(b, h)
        for el in lay.elemente:
            l = app.layers.get(el.layer)
            if l and not l.sichtbar:
                continue
            if isinstance(el, Viewport):
                _pdf_viewport(seite, el, app.elemente, app.layers, farbig,
                              vp_rahmen, einh, komma)
            else:
                _pdf_element(seite, el, lambda x, y: (x, y), 1.0, farbig,
                             app.layers, einh, komma)
        return seite

    b, h = ZEICHNUNGSFORMATE[app.layouts[app.aktives_layout].format]
    sichtbar = [e for e in app.elemente
                if not (app.layers.get(e.layer) and not app.layers[e.layer].sichtbar)]
    if not sichtbar:
        raise ValueError(("Das Modell ist leer." if de
                          else "The model is empty."))
    bbs = [e.bbox() for e in sichtbar]
    x1, y1 = min(b_[0] for b_ in bbs), min(b_[1] for b_ in bbs)
    x2, y2 = max(b_[2] for b_ in bbs), max(b_[3] for b_ in bbs)
    bw, bh = max(x2 - x1, 1e-6), max(y2 - y1, 1e-6)
    if bh > bw and b > h:
        b, h = h, b
    rand = 10.0
    fit = min((b - 2 * rand) / bw, (h - 2 * rand) / bh)
    z = normmassstab_unter(fit, MASSSTAEBE)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

    def tf(x, y):
        return (b / 2 + (x - cx) * z, h / 2 + (y - cy) * z)

    seite = PdfSeite(b, h)
    for el in sichtbar:
        _pdf_element(seite, el, tf, z, farbig, app.layers, einh, komma)
    seite.text(rand, 4.0,
               ("Maßstab " if de else "Scale ") + massstab_text(z),
               3.0, 0.0, "#000000")
    return seite


def pdf_erzeugen(app, quelle, farbig, vp_rahmen, layout_index=None):
    """Erzeugt PDF-Bytes (eine Seite) fuer Modell oder Layout."""
    return pdf_seite_erzeugen(app, quelle, farbig, vp_rahmen,
                              layout_index).to_bytes()


def pdf_mehrseitig_erzeugen(kontexte, quelle, farbig, vp_rahmen):
    """Mehrere Blaetter in EINE PDF-Datei (eine Seite pro Blatt/Layout).

    kontexte: Liste von (anzeigename, ctx); ctx bietet dieselben Attribute
              wie `app` in pdf_erzeugen.
    Rueckgabe: (pdf_bytes, uebersprungene_namen)
    """
    seiten, uebersprungen = [], []
    for name, ctx in kontexte:
        try:
            seiten.append(pdf_seite_erzeugen(ctx, quelle, farbig, vp_rahmen))
        except Exception:
            uebersprungen.append(name)
    if not seiten:
        raise ValueError(tr("msg.druckp.keine_seiten"))
    return pdf_mehrseitig(seiten), uebersprungen


def pdf_senden(pfad, drucken):
    de = SPRACHE["aktuell"] == "de"
    try:
        if sys.platform.startswith("win"):
            os.startfile(pfad, "print" if drucken else "open")
        elif sys.platform == "darwin":
            subprocess.run(["lpr", pfad] if drucken else ["open", pfad],
                           check=True)
        else:
            subprocess.run(["lpr", pfad] if drucken else ["xdg-open", pfad],
                           check=True)
    except Exception as ex:
        messagebox.showwarning(
            ("Drucken" if de else "Print"),
            (f"Die Datei konnte nicht automatisch geöffnet/gedruckt werden "
             f"({ex}).\nDie PDF liegt hier:\n{pfad}" if de else
             f"The file could not be opened/printed automatically ({ex}).\n"
             f"The PDF is here:\n{pfad}"))
