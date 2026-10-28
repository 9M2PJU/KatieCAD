# -*- coding: utf-8 -*-
"""
katiecad/ui/dialogs.py - All dialog classes and the licence window.
Used by CadApp; knows CadApp, but CadApp imports this module only
for the dialog classes.

NEW (step 3): _BlockNameDialog, _BlockAuswahlDialog
NEW (electrical base): ProjektNeuDialog, AttributDefinitionDialog,
                     BlockAttributeDialog
"""

import json
import os
import sys
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog

from katiecad.common.i18n import tr, SPRACHE
from katiecad.electrical import suchen as SU
from katiecad.model.core import (
    FARBEN, ZEICHNUNGSFORMATE, LINIENTYPEN, LINIENSTAERKEN,
    SCHRIFTARTEN, MASSSTAEBE, BEM_RICHTUNGEN,
    schrift_fett, schrift_name, schrift_setzen,
    Layer, Text, Linie, Kreis, Bogen, Rechteck, Polylinie,
    Bemassung, Viewport, Verbindung, ElektroMaske,
    parse_massstab, massstab_text,
)
from katiecad.model.project import name_pruefen
from katiecad.ui.widgets import farb_swatch


def _grab_versuchen(dlg, versuche=40):
    """grab_set() fails on Linux (X11/Wayland, GNOME) with
    'window not viewable' as long as the window is not yet displayed.
    The exception used to abort building the dialog -> empty grey
    window. Therefore: first wait until the window is visible."""
    try:
        if not dlg.winfo_exists():
            return
        dlg.wait_visibility()
        dlg.grab_set()
        dlg.focus_force()
    except tk.TclError:
        if versuche > 0:
            try:
                dlg.after(50, lambda: _grab_versuchen(dlg, versuche - 1))
            except tk.TclError:
                pass


_OFFENE_DIALOGE = []


def _schliesse_andere_dialoge(dlg):
    """Only one dialog at a time: opening a new dialog closes every other
    open dialog - except the ones it was opened from (parent chain)."""
    vorfahren = set()
    w = getattr(dlg, "master", None)
    while w is not None:
        vorfahren.add(str(w))
        w = getattr(w, "master", None)
    uebrig = []
    for d in _OFFENE_DIALOGE:
        try:
            lebt = bool(d.winfo_exists())
        except tk.TclError:
            lebt = False
        if not lebt or d is dlg:
            continue
        if str(d) in vorfahren:
            uebrig.append(d)
            continue
        try:
            d.destroy()
        except tk.TclError:
            pass
    _OFFENE_DIALOGE[:] = uebrig + [dlg]


def _modal(dlg):
    """Makes a dialog modal (see _grab_versuchen) and makes sure that only
    one dialog is open at a time."""
    try:
        _schliesse_andere_dialoge(dlg)
    except Exception as ex:
        print(f"[KatieCAD] Dialog: {ex}")
    try:
        dlg.after(10, lambda: _grab_versuchen(dlg))
    except tk.TclError:
        pass



# ============================================================
# MIT licence text (for the separate licence window)
# ============================================================
MIT_LICENSE_TEXT = """MIT License

Copyright (c) 2026 Merecete

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""


def zeige_lizenz_fenster(parent):
    """Shows the MIT licence in a separate, scrollable window."""
    alt = getattr(zeige_lizenz_fenster, "_fenster", None)
    try:
        if alt is not None and alt.winfo_exists():       # only one at a time
            alt.deiconify()
            alt.lift()
            return
    except tk.TclError:
        pass
    win = tk.Toplevel(parent)
    zeige_lizenz_fenster._fenster = win
    win.title("License – KatieCAD")
    win.geometry("620x520")
    win.minsize(400, 300)
    win.transient(parent)
    win.configure(bg=FARBEN["bg_mittel"])

    footer = tk.Frame(win, bg=FARBEN["bg_mittel"], padx=20, pady=14)
    footer.pack(side="bottom", fill="x")

    ttk.Button(footer, text=tr("dlg.schliessen"),
               command=win.destroy).pack(side="right")

    header = tk.Frame(win, bg=FARBEN["bg_mittel"], padx=20, pady=14)
    header.pack(side="top", fill="x")
    tk.Label(header, text="MIT LICENSE",
             font=("Helvetica", 12, "bold"),
             bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"]).pack(anchor="w")

    tk.Frame(win, bg=FARBEN["rand"], height=1).pack(side="top", fill="x", padx=20)

    body = tk.Frame(win, bg=FARBEN["bg_mittel"], padx=20, pady=14)
    body.pack(side="top", fill="both", expand=True)

    text_wrap = tk.Frame(body, bg=FARBEN["bg_dunkel"], bd=0, highlightthickness=0)
    text_wrap.pack(fill="both", expand=True)

    txt = tk.Text(text_wrap, wrap="word",
                  bg=FARBEN["bg_dunkel"], fg=FARBEN["text_dim"],
                  insertbackground=FARBEN["text"],
                  selectbackground=FARBEN["cyan"],
                  selectforeground=FARBEN["bg_dunkel"],
                  relief="flat", bd=0, highlightthickness=0,
                  font=("Courier New", 9), padx=14, pady=12)
    txt.pack(side="left", fill="both", expand=True)

    sb = tk.Scrollbar(text_wrap, command=txt.yview,
                      bg=FARBEN["bg_hell"], troughcolor=FARBEN["bg_dunkel"],
                      activebackground=FARBEN["cyan"],
                      relief="flat", bd=0, highlightthickness=0, width=12)
    sb.pack(side="right", fill="y")
    txt.config(yscrollcommand=sb.set)

    txt.insert("1.0", MIT_LICENSE_TEXT)
    txt.config(state="disabled")

    win.bind("<Escape>", lambda e: win.destroy())

    win.update_idletasks()
    mx = parent.winfo_rootx() + parent.winfo_width() // 2
    my = parent.winfo_rooty() + parent.winfo_height() // 2
    w = win.winfo_width()
    h = win.winfo_height()
    win.geometry(f"+{mx - w // 2}+{my - h // 2}")


# ============================================================
# Layout name dialog
# ============================================================
class _LayoutNameDialog(tk.Toplevel):
    def __init__(self, parent, titel, startname="", label=None):
        super().__init__(parent)
        self.result = None
        self.title(titel)
        self.geometry("360x140")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=label or tr("layout.neu.name")).pack(anchor=tk.W)
        self.name_var = tk.StringVar(value=startname)
        e = ttk.Entry(f, textvariable=self.name_var, width=30)
        e.pack(fill=tk.X, pady=6)
        e.focus_set()
        bf = ttk.Frame(f)
        bf.pack(pady=8)
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_window(self)

    def _ok(self):
        self.result = self.name_var.get().strip()
        self.destroy()


# ============================================================
# Sheet properties (name + installation location)
# ============================================================
class BlattEigenschaftenDialog(tk.Toplevel):
    """Name and installation location of a sheet.
    result = (name, einbauort, art, beschreibung) or None."""

    def __init__(self, parent, titel, name, einbauort="", vorschlaege=(),
                 mit_ort=True, art="", beschreibung="", art_vorschlaege=()):
        super().__init__(parent)
        self.result = None
        self.title(titel)
        self.geometry("440x370")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=tr("dlg.blatt.name")).pack(anchor=tk.W)
        self.name_var = tk.StringVar(value=name)
        e = ttk.Entry(f, textvariable=self.name_var, width=40)
        e.pack(fill=tk.X, pady=(2, 8))
        e.focus_set()
        e.select_range(0, tk.END)
        ttk.Label(f, text=tr("dlg.blatt.einbauort")).pack(anchor=tk.W)
        self.ort_var = tk.StringVar(value=einbauort)
        self.cb = ttk.Combobox(f, textvariable=self.ort_var, width=38,
                               values=list(vorschlaege),
                               state="normal" if mit_ort else "disabled")
        self.cb.pack(fill=tk.X, pady=(2, 2))
        ttk.Label(f, text=tr("dlg.blatt.einbauort_hinweis" if mit_ort
                             else "dlg.blatt.nur_zeichnung"),
                  wraplength=400, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 0))
        ttk.Label(f, text=tr("dlg.blatt.art")).pack(anchor=tk.W, pady=(8, 0))
        self.art_var = tk.StringVar(value=art)
        ttk.Combobox(f, textvariable=self.art_var, width=38,
                     values=list(art_vorschlaege),
                     state="normal" if mit_ort else "disabled").pack(
            fill=tk.X, pady=(2, 2))
        ttk.Label(f, text=tr("dlg.blatt.beschreibung")).pack(anchor=tk.W, pady=(8, 0))
        self.beschr_var = tk.StringVar(value=beschreibung)
        ttk.Entry(f, textvariable=self.beschr_var, width=40,
                  state="normal" if mit_ort else "disabled").pack(
            fill=tk.X, pady=(2, 2))
        bf = ttk.Frame(f)
        bf.pack(pady=10)
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.bind("<Return>", lambda ev: self._ok())
        self.bind("<Escape>", lambda ev: self.destroy())
        self.wait_window(self)

    def _ok(self):
        self.result = (self.name_var.get().strip(), self.ort_var.get().strip(),
                       self.art_var.get().strip(), self.beschr_var.get().strip())
        self.destroy()


# ============================================================
# PropertiesDialog
# ============================================================
class PropertiesDialog(tk.Toplevel):
    def __init__(self, parent, app, element):
        super().__init__(parent)
        self.app = app
        self.el = element
        self.result = False
        self.title(tr("dlg.prop.titel", typ=element.typ.capitalize()))
        self.geometry("480x680")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        row = 0
        ttk.Label(f, text=tr("dlg.prop.typ"), style="Title.TLabel").grid(
            row=row, column=0, sticky=tk.W, pady=4)
        ttk.Label(f, text=element.typ.capitalize(), style="Hint.TLabel").grid(
            row=row, column=1, sticky=tk.W, pady=4)
        row += 1
        ttk.Label(f, text=tr("dlg.prop.layer")).grid(row=row, column=0, sticky=tk.W, pady=4)
        self.layer_var = tk.StringVar(value=element.layer)
        ttk.Combobox(f, textvariable=self.layer_var, values=list(app.layers.keys()),
                     width=20, state="readonly").grid(row=row, column=1, sticky=tk.W, pady=4)
        row += 1
        ttk.Label(f, text=tr("dlg.prop.farbe")).grid(row=row, column=0, sticky=tk.W, pady=4)
        self.farbe_var = tk.StringVar(value=element.farbe)
        ff = ttk.Frame(f)
        ff.grid(row=row, column=1, sticky=tk.W, pady=4)
        self.farbe_btn = farb_swatch(ff, self.farbe_var.get(),
                                     self._farbe_waehlen, width=6)
        self.farbe_btn.pack(side=tk.LEFT)
        ttk.Label(ff, textvariable=self.farbe_var).pack(side=tk.LEFT, padx=6)
        row += 1
        self.eig_farbe_var = tk.BooleanVar(value=getattr(element, "eig_farbe", False))
        ttk.Checkbutton(f, text=tr("dlg.prop.eig_farbe"),
                        variable=self.eig_farbe_var).grid(row=row, column=1,
                                                          sticky=tk.W, pady=4)
        row += 1
        ttk.Label(f, text=tr("dlg.prop.linientyp")).grid(row=row, column=0,
                                                         sticky=tk.W, pady=4)
        self.linientyp_var = tk.StringVar(value=element.linientyp)
        ttk.Combobox(f, textvariable=self.linientyp_var,
                     values=list(LINIENTYPEN.keys()),
                     width=20, state="readonly").grid(row=row, column=1,
                                                       sticky=tk.W, pady=4)
        row += 1
        ttk.Label(f, text=tr("dlg.prop.staerke")).grid(row=row, column=0,
                                                       sticky=tk.W, pady=4)
        staerke_wert = getattr(element, "staerke", None) or 0.35
        self.staerke_var = tk.DoubleVar(value=staerke_wert)
        ttk.Combobox(f, textvariable=self.staerke_var, values=LINIENSTAERKEN,
                     width=10).grid(row=row, column=1, sticky=tk.W, pady=4)
        row += 1
        ttk.Separator(f, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2,
                                                     sticky=tk.EW, pady=8)
        row += 1
        ttk.Label(f, text=tr("dlg.prop.geometrie"), style="Title.TLabel").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=4)
        row += 1
        self.geo_vars = {}

        def add_geo(label, key, value):
            nonlocal row
            ttk.Label(f, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
            v = tk.DoubleVar(value=value)
            self.geo_vars[key] = v
            ttk.Entry(f, textvariable=v, width=15).grid(row=row, column=1,
                                                          sticky=tk.W, pady=3)
            row += 1

        if isinstance(element, Linie):
            for k in ("x1", "y1", "x2", "y2"):
                add_geo(k.upper() + ":", k, getattr(element, k))
        elif isinstance(element, Kreis):
            add_geo("Zentrum X:", "cx", element.cx)
            add_geo("Zentrum Y:", "cy", element.cy)
            add_geo("Radius:", "r", element.r)
        elif isinstance(element, Bogen):
            add_geo("Zentrum X:", "cx", element.cx)
            add_geo("Zentrum Y:", "cy", element.cy)
            add_geo("Radius:", "r", element.r)
            add_geo("Startwinkel:", "start", element.start)
            add_geo("Endwinkel:", "ende", element.ende)
        elif isinstance(element, Rechteck):
            for k in ("x1", "y1", "x2", "y2"):
                add_geo(k.upper() + ":", k, getattr(element, k))
            self._rechteck_groesse(f, row)
            row += 3
        elif isinstance(element, Polylinie):
            ttk.Label(f, text="Punkte:").grid(row=row, column=0, sticky=tk.NW, pady=3)
            self.punkte_text = tk.Text(f, width=25, height=8,
                                       bg=FARBEN["bg_hell"], fg=FARBEN["cyan"])
            self.punkte_text.grid(row=row, column=1, sticky=tk.W, pady=3)
            for (x, y) in element.punkte:
                self.punkte_text.insert(tk.END, f"{x},{y}\n")
            row += 1
        elif isinstance(element, Text):
            ttk.Label(f, text=tr("dlg.text.inhalt")).grid(row=row, column=0,
                                                          sticky=tk.NW, pady=3)
            self.inhalt_text = tk.Text(f, width=25, height=3,
                                       bg=FARBEN["bg_hell"], fg=FARBEN["cyan"])
            self.inhalt_text.grid(row=row, column=1, sticky=tk.W, pady=3)
            self.inhalt_text.insert("1.0", element.inhalt)
            row += 1
            add_geo("X:", "x", element.x)
            add_geo("Y:", "y", element.y)
            add_geo("Höhe:", "hoehe", element.hoehe)
            add_geo("Winkel:", "winkel", element.winkel)
            self.schrift_var = tk.StringVar(value=schrift_name(element.schriftart))
            self.fett_var = tk.BooleanVar(value=schrift_fett(element.schriftart))
            ttk.Label(f, text=tr("dlg.text.schrift")).grid(row=row, column=0,
                                                            sticky=tk.W, pady=3)
            ttk.Combobox(f, textvariable=self.schrift_var, values=SCHRIFTARTEN,
                         width=20).grid(row=row, column=1, sticky=tk.W, pady=3)
            row += 1
            ttk.Checkbutton(f, text=tr("dlg.text.fett"),
                            variable=self.fett_var).grid(row=row, column=1,
                                                         sticky=tk.W, pady=3)
            row += 1
            ttk.Label(f, text=tr("dlg.text.einfuegepunkt")).grid(
                row=row, column=0, sticky=tk.W, pady=3)
            self.einfuegepunkt_anzeige = [
                tr(f"tx.punkt.{k}") for k in Text.EINFUEGEPUNKTE]
            self.einfuegepunkt_werte = list(Text.EINFUEGEPUNKTE)
            self.einfuegepunkt_var = tk.StringVar()
            aktueller = getattr(element, "einfuegepunkt",
                                Text.STANDARD_EINFUEGEPUNKT)
            try:
                idx = self.einfuegepunkt_werte.index(aktueller)
            except ValueError:
                idx = self.einfuegepunkt_werte.index(Text.STANDARD_EINFUEGEPUNKT)
            self.einfuegepunkt_var.set(self.einfuegepunkt_anzeige[idx])
            ttk.Combobox(f, textvariable=self.einfuegepunkt_var,
                         values=self.einfuegepunkt_anzeige,
                         width=20, state="readonly").grid(
                row=row, column=1, sticky=tk.W, pady=3)
            row += 1
        elif isinstance(element, Bemassung):
            for k in (("x1", "y1", "x2", "y2", "mx", "my", "hoehe", "pfeil")
                      + (("x3", "y3") if element.x3 is not None else ())):
                add_geo(k.upper() + ":", k, getattr(element, k))
            add_geo("Nachkommastellen:", "dez", element.dez)
            ttk.Label(f, text="Art:").grid(row=row, column=0, sticky=tk.W, pady=3)
            self.richtung_var = tk.StringVar(value=element.richtung)
            ttk.Combobox(f, textvariable=self.richtung_var,
                         values=list(BEM_RICHTUNGEN), width=18, state="readonly").grid(
                row=row, column=1, sticky=tk.W, pady=3)
            row += 1
            ttk.Label(f, text="Text (<> = Messwert):").grid(row=row, column=0,
                                                             sticky=tk.W, pady=3)
            self.bem_text_var = tk.StringVar(value=element.text_override)
            ttk.Entry(f, textvariable=self.bem_text_var, width=22).grid(
                row=row, column=1, sticky=tk.W, pady=3)
            row += 1
        elif isinstance(element, Viewport):
            add_geo("X:", "x", element.x)
            add_geo("Y:", "y", element.y)
            add_geo("Breite:", "breite", element.breite)
            add_geo("Höhe:", "hoehe", element.hoehe)
            add_geo("Modell-CX:", "mcx", element.modell_zentrum_x)
            add_geo("Modell-CY:", "mcy", element.modell_zentrum_y)
            add_geo("Zoom:", "zoom", element.zoom)
        bf = ttk.Frame(f)
        bf.grid(row=row, column=0, columnspan=2, pady=16)
        ttk.Button(bf, text=tr("dlg.prop.uebernehmen"),
                   command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.wait_window(self)

    def _rechteck_groesse(self, f, row):
        """Width / height of a rectangle (derived from the corners). Editing them resizes the
        rectangle about corner 1 or about the centre (shrinks/grows on both sides)."""
        g = self.geo_vars
        self._b_var = tk.DoubleVar(value=abs(g["x2"].get() - g["x1"].get()))
        self._h_var = tk.DoubleVar(value=abs(g["y2"].get() - g["y1"].get()))
        self._anker_var = tk.StringVar(value=tr("dlg.prop.anker_ecke"))
        for i, (txt, var) in enumerate(((tr("dlg.prop.breite"), self._b_var),
                                        (tr("dlg.prop.hoehe"), self._h_var))):
            ttk.Label(f, text=txt).grid(row=row + i, column=0, sticky=tk.W, pady=3)
            e = ttk.Entry(f, textvariable=var, width=15)
            e.grid(row=row + i, column=1, sticky=tk.W, pady=3)
            e.bind("<Return>", lambda ev: self._groesse_anwenden())
            e.bind("<FocusOut>", lambda ev: self._groesse_anwenden())
        ttk.Label(f, text=tr("dlg.prop.anker")).grid(row=row + 2, column=0, sticky=tk.W, pady=3)
        ttk.Combobox(f, textvariable=self._anker_var, width=20, state="readonly",
                     values=[tr("dlg.prop.anker_ecke"), tr("dlg.prop.anker_mitte")]).grid(
            row=row + 2, column=1, sticky=tk.W, pady=3)
        for k in ("x1", "y1", "x2", "y2"):
            g[k].trace_add("write", lambda *_: self._groesse_anzeigen())

    def _groesse_anzeigen(self):
        if getattr(self, "_sperre", False):
            return
        try:
            g = self.geo_vars
            self._sperre = True
            self._b_var.set(abs(g["x2"].get() - g["x1"].get()))
            self._h_var.set(abs(g["y2"].get() - g["y1"].get()))
        except Exception:
            pass
        finally:
            self._sperre = False

    def _groesse_anwenden(self):
        if getattr(self, "_sperre", False):
            return
        try:
            g = self.geo_vars
            b, h = abs(self._b_var.get()), abs(self._h_var.get())
            mitte = self._anker_var.get() == tr("dlg.prop.anker_mitte")
            self._sperre = True
            for a, c, mass in (("x1", "x2", b), ("y1", "y2", h)):
                v1, v2 = g[a].get(), g[c].get()
                vz = 1.0 if v2 >= v1 else -1.0
                if mitte:
                    m = (v1 + v2) / 2.0
                    g[a].set(round(m - vz * mass / 2.0, 6))
                    g[c].set(round(m + vz * mass / 2.0, 6))
                else:
                    g[c].set(round(v1 + vz * mass, 6))
        except Exception:
            pass
        finally:
            self._sperre = False

    def _farbe_waehlen(self):
        _, hexc = colorchooser.askcolor(color=self.farbe_var.get())
        if hexc:
            self.farbe_var.set(hexc)
            self.farbe_btn.config(bg=hexc)

    def _ok(self):
        el = self.el
        try:
            el.layer = self.layer_var.get()
            el.farbe = self.farbe_var.get()
            el.linientyp = self.linientyp_var.get()
            el.eig_farbe = bool(self.eig_farbe_var.get())
            try:
                el.staerke = float(self.staerke_var.get())
            except Exception:
                pass
            if isinstance(el, Linie):
                for k in ("x1", "y1", "x2", "y2"):
                    setattr(el, k, self.geo_vars[k].get())
            elif isinstance(el, Kreis):
                for k in ("cx", "cy", "r"):
                    setattr(el, k, self.geo_vars[k].get())
            elif isinstance(el, Bogen):
                for k in ("cx", "cy", "r", "start", "ende"):
                    setattr(el, k, self.geo_vars[k].get())
            elif isinstance(el, Rechteck):
                for k in ("x1", "y1", "x2", "y2"):
                    setattr(el, k, self.geo_vars[k].get())
            elif isinstance(el, Polylinie):
                txt = self.punkte_text.get("1.0", "end").strip()
                pts = []
                for zeile in txt.split("\n"):
                    zeile = zeile.strip()
                    if not zeile:
                        continue
                    teile = zeile.replace(";", ",").split(",")
                    if len(teile) == 2:
                        pts.append((float(teile[0]), float(teile[1])))
                el.punkte = pts
            elif isinstance(el, Text):
                el.inhalt = self.inhalt_text.get("1.0", "end").strip()
                el.x = self.geo_vars["x"].get()
                el.y = self.geo_vars["y"].get()
                el.hoehe = self.geo_vars["hoehe"].get()
                el.winkel = self.geo_vars["winkel"].get()
                el.schriftart = schrift_setzen(self.schrift_var.get(), self.fett_var.get())
                try:
                    idx = self.einfuegepunkt_anzeige.index(
                        self.einfuegepunkt_var.get())
                    el.einfuegepunkt = self.einfuegepunkt_werte[idx]
                except (ValueError, AttributeError):
                    el.einfuegepunkt = Text.STANDARD_EINFUEGEPUNKT
            elif isinstance(el, Bemassung):
                for k in ("x1", "y1", "x2", "y2", "mx", "my", "hoehe", "pfeil",
                          "x3", "y3"):
                    if k in self.geo_vars:
                        setattr(el, k, self.geo_vars[k].get())
                el.dez = int(self.geo_vars["dez"].get())
                el.richtung = self.richtung_var.get()
                el.text_override = self.bem_text_var.get()
                el.tx = el.ty = None
            elif isinstance(el, Viewport):
                el.x = self.geo_vars["x"].get()
                el.y = self.geo_vars["y"].get()
                el.breite = self.geo_vars["breite"].get()
                el.hoehe = self.geo_vars["hoehe"].get()
                el.modell_zentrum_x = self.geo_vars["mcx"].get()
                el.modell_zentrum_y = self.geo_vars["mcy"].get()
                el.zoom = self.geo_vars["zoom"].get()
            self.result = True
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ============================================================
# ViewportDialog
# ============================================================
class ViewportDialog(tk.Toplevel):
    def __init__(self, parent, app, vp):
        super().__init__(parent)
        self.app = app
        self.vp = vp
        self.result = False
        self.title(tr("dlg.viewport.titel"))
        self.geometry("440x520")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        row = 0
        ttk.Label(f, text=tr("dlg.viewport.layoutpos"), style="Title.TLabel").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=4)
        row += 1
        self.geo_vars = {}

        def add_geo(label, key, value):
            nonlocal row
            ttk.Label(f, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
            v = tk.DoubleVar(value=value)
            self.geo_vars[key] = v
            ttk.Entry(f, textvariable=v, width=15).grid(row=row, column=1,
                                                          sticky=tk.W, pady=3)
            row += 1

        add_geo(tr("dlg.viewport.x"), "x", vp.x)
        add_geo(tr("dlg.viewport.y"), "y", vp.y)
        add_geo(tr("dlg.viewport.breite"), "breite", vp.breite)
        add_geo(tr("dlg.viewport.hoehe"), "hoehe", vp.hoehe)
        ttk.Separator(f, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2,
                                                     sticky=tk.EW, pady=8)
        row += 1
        ttk.Label(f, text=tr("dlg.viewport.ausschnitt"), style="Title.TLabel").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=4)
        row += 1
        add_geo(tr("dlg.viewport.mcx"), "mcx", vp.modell_zentrum_x)
        add_geo(tr("dlg.viewport.mcy"), "mcy", vp.modell_zentrum_y)
        add_geo(tr("dlg.viewport.zoom"), "zoom", vp.zoom)
        ttk.Label(f, text=tr("dlg.viewport.massstab")).grid(row=row, column=0,
                                                             sticky=tk.W, pady=3)
        self._ms_start = massstab_text(vp.zoom)
        self.ms_var = tk.StringVar(value=self._ms_start)
        ttk.Combobox(f, textvariable=self.ms_var, values=MASSSTAEBE,
                     width=12).grid(row=row, column=1, sticky=tk.W, pady=3)
        row += 1
        self.gesperrt_var = tk.BooleanVar(value=vp.gesperrt)
        ttk.Checkbutton(f, text=tr("dlg.viewport.sperren"),
                        variable=self.gesperrt_var).grid(row=row, column=1,
                                                          sticky=tk.W, pady=3)
        row += 1
        ttk.Button(f, text=tr("dlg.viewport.fit"),
                   command=self._auto_fit).grid(row=row, column=0, columnspan=2,
                                                 pady=8, sticky=tk.EW)
        row += 1
        bf = ttk.Frame(f)
        bf.grid(row=row, column=0, columnspan=2, pady=12)
        ttk.Button(bf, text=tr("dlg.uebernehmen"),
                   command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.wait_window(self)

    def _auto_fit(self):
        if not self.app.elemente:
            return
        xs, ys = [], []
        for el in self.app.elemente:
            b = el.bbox()
            xs.extend([b[0], b[2]])
            ys.extend([b[1], b[3]])
        if not xs:
            return
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        cx = (minx + maxx) / 2
        cy = (miny + maxy) / 2
        bw = maxx - minx
        bh = maxy - miny
        vp = self.vp
        ms = min((vp.breite * 0.9) / bw, (vp.hoehe * 0.9) / bh) \
            if (bw > 1e-6 and bh > 1e-6) else 1.0
        self.geo_vars["mcx"].set(cx)
        self.geo_vars["mcy"].set(cy)
        self.geo_vars["zoom"].set(ms)

    def _ok(self):
        vp = self.vp
        try:
            vp.x = self.geo_vars["x"].get()
            vp.y = self.geo_vars["y"].get()
            vp.breite = self.geo_vars["breite"].get()
            vp.hoehe = self.geo_vars["hoehe"].get()
            vp.modell_zentrum_x = self.geo_vars["mcx"].get()
            vp.modell_zentrum_y = self.geo_vars["mcy"].get()
            vp.zoom = self.geo_vars["zoom"].get()
            ms = self.ms_var.get().strip()
            if ms and ms != self._ms_start:
                vp.zoom = parse_massstab(ms)
            vp.gesperrt = bool(self.gesperrt_var.get())
            self.result = True
            self.destroy()
        except Exception as e:
            messagebox.showerror("Viewport", str(e))


# ============================================================
# Layer dialogs
# ============================================================
class LayerDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title(tr("dlg.layer.titel"))
        self.geometry("650x420")
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        ttk.Label(self, text=tr("dlg.layer.titel"), style="Title.TLabel").pack(pady=6)
        self.tree = ttk.Treeview(self, columns=("name", "farbe", "staerke", "sichtbar"),
                                 show="headings", height=10)
        for c, w, t in [("name", 180, tr("dlg.layer.name").rstrip(":")),
                        ("farbe", 140, tr("dlg.layer.farbe").rstrip(":")),
                        ("staerke", 160, tr("dlg.layer.staerke").rstrip(":")),
                        ("sichtbar", 90, tr("dlg.layer.sichtbar").rstrip(":"))]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8)
        self._aktualisiere()
        bf = ttk.Frame(self)
        bf.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(bf, text=tr("dlg.layer.neu"),
                   command=self.neuer_layer).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text=tr("dlg.layer.bearbeiten"),
                   command=self.bearbeite).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text=tr("dlg.layer.loeschen"),
                   command=self.loeschen).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text=tr("dlg.layer.bereinigen"),
                   command=self.bereinigen).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text=tr("dlg.schliessen"),
                   command=self.destroy).pack(side=tk.RIGHT, padx=2)
        self.wait_window(self)

    def bereinigen(self):
        """Deletes all layers no object uses (layer 0 and the active layer
        stay); with a project this looks at ALL sheets."""
        app = self.app
        projektweit = app.projekt is not None
        bereich = tr("msg.layer.bereich.projekt" if projektweit
                     else "msg.layer.bereich.blatt")
        ungenutzt = app.ungenutzte_layer(projektweit)
        if not ungenutzt:
            messagebox.showinfo("Layer", tr("msg.layer.bereinigt_nichts",
                                            bereich=bereich), parent=self)
            return
        if not messagebox.askyesno(
                "Layer", tr("msg.layer.bereinigt_frage", n=len(ungenutzt),
                            bereich=bereich, namen=", ".join(ungenutzt)),
                parent=self):
            return
        app._snapshot()
        app.layer_bereinigen_anwenden(ungenutzt, projektweit)
        app.layer_cb.config(values=list(app.layers.keys()))
        self._aktualisiere()
        app.redraw()
        app.status.set(tr("msg.layer.bereinigt", n=len(ungenutzt), bereich=bereich))

    def _aktualisiere(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        de = SPRACHE["aktuell"] == "de"
        for name, l in self.app.layers.items():
            self.tree.insert("", "end",
                             values=(name, l.farbe, l.staerke,
                                     ("ja" if l.sichtbar else "nein") if de
                                     else ("yes" if l.sichtbar else "no")))

    def _selektiert(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0], "values")[0]

    def neuer_layer(self):
        dlg = LayerEditDialog(self, None, self.app)
        if dlg.result:
            name, farbe, staerke, sichtbar = dlg.result
            if name in self.app.layers:
                de = SPRACHE["aktuell"] == "de"
                messagebox.showerror("Layer",
                    (f"Layer '{name}' existiert." if de
                     else f"Layer '{name}' already exists."))
                return
            self.app._snapshot()
            self.app.layers[name] = Layer(name, farbe, staerke, sichtbar)
            self.app.layer_cb.config(values=list(self.app.layers.keys()))
            self._aktualisiere()

    def bearbeite(self):
        name = self._selektiert()
        if not name:
            return
        l = self.app.layers[name]
        dlg = LayerEditDialog(self, l, self.app)
        if dlg.result:
            neuer_name, farbe, staerke, sichtbar = dlg.result
            if neuer_name != name and neuer_name in self.app.layers:
                de = SPRACHE["aktuell"] == "de"
                messagebox.showerror("Layer",
                    ("Name existiert." if de else "Name already exists."))
                return
            self.app._snapshot()
            if neuer_name != name:
                del self.app.layers[name]
                for el in self.app.elemente + self.app.layout_elemente:
                    if el.layer == name:
                        el.layer = neuer_name
            self.app.layers[neuer_name] = Layer(neuer_name, farbe, staerke, sichtbar)
            self.app.layer_cb.config(values=list(self.app.layers.keys()))
            self._aktualisiere()
            self.app.redraw()

    def loeschen(self):
        name = self._selektiert()
        if not name or name == "0":
            return
        de = SPRACHE["aktuell"] == "de"
        if messagebox.askyesno("Layer",
                               (f"Layer '{name}' löschen?" if de
                                else f"Delete layer '{name}'?")):
            self.app._snapshot()
            for el in self.app.elemente + self.app.layout_elemente:
                if el.layer == name:
                    el.layer = "0"
            del self.app.layers[name]
            self.app.layer_cb.config(values=list(self.app.layers.keys()))
            self._aktualisiere()
            self.app.redraw()


class LayerEditDialog(tk.Toplevel):
    def __init__(self, parent, layer, app):
        super().__init__(parent)
        self.result = None
        self.title(tr("dlg.layer.titel") if layer else tr("dlg.layer.neu"))
        self.geometry("420x280")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        self.name_var = tk.StringVar(value=layer.name if layer else "NeuerLayer")
        self.farbe_var = tk.StringVar(value=layer.farbe if layer else FARBEN["cyan"])
        self.staerke_var = tk.DoubleVar(value=layer.staerke if layer else 0.35)
        self.sichtbar_var = tk.BooleanVar(value=layer.sichtbar if layer else True)
        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=tr("dlg.layer.name")).grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(f, textvariable=self.name_var, width=25).grid(row=0, column=1)
        ttk.Label(f, text=tr("dlg.layer.farbe")).grid(row=1, column=0, sticky=tk.W, pady=4)
        ff = ttk.Frame(f)
        ff.grid(row=1, column=1, sticky=tk.W)
        self.farbe_btn = farb_swatch(ff, self.farbe_var.get(),
                                     self._farbe_waehlen, width=6)
        self.farbe_btn.pack(side=tk.LEFT)
        ttk.Label(ff, textvariable=self.farbe_var).pack(side=tk.LEFT, padx=6)
        ttk.Label(f, text=tr("dlg.layer.staerke")).grid(row=2, column=0,
                                                         sticky=tk.W, pady=4)
        ttk.Combobox(f, textvariable=self.staerke_var, values=LINIENSTAERKEN,
                     width=10).grid(row=2, column=1, sticky=tk.W)
        ttk.Label(f, text=tr("dlg.layer.sichtbar")).grid(row=3, column=0,
                                                          sticky=tk.W, pady=4)
        ttk.Checkbutton(f, variable=self.sichtbar_var).grid(row=3, column=1,
                                                             sticky=tk.W)
        bf = ttk.Frame(f)
        bf.grid(row=4, column=0, columnspan=2, pady=12)
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.wait_window(self)

    def _farbe_waehlen(self):
        _, hexc = colorchooser.askcolor(color=self.farbe_var.get())
        if hexc:
            self.farbe_var.set(hexc)
            self.farbe_btn.config(bg=hexc)

    def _ok(self):
        self.result = (self.name_var.get().strip(), self.farbe_var.get(),
                       float(self.staerke_var.get()),
                       bool(self.sichtbar_var.get()))
        self.destroy()


# ============================================================
# Text, array and print dialogs
# ============================================================
class TextDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.result = None
        self.title(tr("dlg.text.titel"))
        self.geometry("500x360")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text=tr("dlg.text.inhalt")).grid(row=0, column=0,
                                                       sticky=tk.NW, pady=4)
        self.text_widget = tk.Text(f, width=42, height=5,
                                   bg=FARBEN["bg_hell"], fg=FARBEN["cyan"])
        self.text_widget.grid(row=0, column=1, pady=4)
        self.text_widget.insert("1.0", "Text")

        ttk.Label(f, text=tr("dlg.text.schrift")).grid(row=1, column=0,
                                                        sticky=tk.W, pady=4)
        self.schrift_var = tk.StringVar(value=app.text_schriftart.get())
        self.fett_var = tk.BooleanVar(value=bool(getattr(app, "text_fett", False)))
        sf = ttk.Frame(f)
        sf.grid(row=1, column=1, sticky=tk.W)
        ttk.Combobox(sf, textvariable=self.schrift_var, values=SCHRIFTARTEN,
                     width=22).pack(side=tk.LEFT)
        ttk.Checkbutton(sf, text=tr("dlg.text.fett"),
                        variable=self.fett_var).pack(side=tk.LEFT, padx=8)

        ttk.Label(f, text=tr("dlg.text.hoehe")).grid(row=2, column=0,
                                                      sticky=tk.W, pady=4)
        self.hoehe_var = tk.DoubleVar(value=app.text_hoehe.get())
        ttk.Spinbox(f, textvariable=self.hoehe_var, from_=1, to=200,
                    increment=0.5, width=8).grid(row=2, column=1, sticky=tk.W)

        ttk.Label(f, text=tr("dlg.text.winkel")).grid(row=3, column=0,
                                                       sticky=tk.W, pady=4)
        self.winkel_var = tk.DoubleVar(value=app.text_winkel.get())
        ttk.Spinbox(f, textvariable=self.winkel_var, from_=-180, to=180,
                    increment=15, width=8).grid(row=3, column=1, sticky=tk.W)

        ttk.Label(f, text=tr("dlg.text.einfuegepunkt")).grid(
            row=4, column=0, sticky=tk.W, pady=4)
        self.einfuegepunkt_var = tk.StringVar(value=Text.STANDARD_EINFUEGEPUNKT)
        self._punkt_anzeige = [tr(f"tx.punkt.{k}") for k in Text.EINFUEGEPUNKTE]
        self._punkt_werte = list(Text.EINFUEGEPUNKTE)
        self.punkt_cb = ttk.Combobox(
            f, values=self._punkt_anzeige, state="readonly", width=22)
        aktueller = Text.STANDARD_EINFUEGEPUNKT
        self.punkt_cb.set(tr(f"tx.punkt.{aktueller}"))
        self.punkt_cb.grid(row=4, column=1, sticky=tk.W)

        bf = ttk.Frame(f)
        bf.grid(row=5, column=0, columnspan=2, pady=12)
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.wait_window(self)

    def _aktueller_punkt(self):
        anzeige = self.punkt_cb.get()
        try:
            idx = self._punkt_anzeige.index(anzeige)
            return self._punkt_werte[idx]
        except ValueError:
            return Text.STANDARD_EINFUEGEPUNKT

    def _ok(self):
        inhalt = self.text_widget.get("1.0", "end").strip()
        if not inhalt:
            return
        self.result = (inhalt, float(self.hoehe_var.get()),
                       float(self.winkel_var.get()),
                       schrift_setzen(self.schrift_var.get(), self.fett_var.get()),
                       self._aktueller_punkt())
        self.destroy()


class SchraffurDialog(tk.Toplevel):
    """Hatch type (selection box), spacing and angle in one dialog.
    result = (muster, abstand_mm, winkel_deg) or None."""

    def __init__(self, parent):
        super().__init__(parent)
        de = SPRACHE["aktuell"] == "de"
        self.result = None
        self.title("Schraffur" if de else "Hatch")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        self._arten = [("linien", "Linien" if de else "Lines"),
                       ("solid", "Vollfläche" if de else "Solid fill")]
        ttk.Label(f, text="Art:" if de else "Type:").grid(
            row=0, column=0, sticky=tk.W, pady=4)
        self.art = tk.StringVar(value=self._arten[0][1])
        cb = ttk.Combobox(f, textvariable=self.art, state="readonly", width=16,
                          values=[n for _, n in self._arten])
        cb.grid(row=0, column=1, sticky=tk.W, pady=4, padx=(8, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: self._umschalten())
        self.abstand = tk.StringVar(value="5.0")
        self.winkel = tk.StringVar(value="45")
        ttk.Label(f, text="Abstand (mm):" if de else "Spacing (mm):").grid(
            row=1, column=0, sticky=tk.W, pady=4)
        self.e1 = ttk.Entry(f, textvariable=self.abstand, width=18)
        self.e1.grid(row=1, column=1, sticky=tk.W, pady=4, padx=(8, 0))
        ttk.Label(f, text="Winkel (Grad):" if de else "Angle (deg):").grid(
            row=2, column=0, sticky=tk.W, pady=4)
        self.e2 = ttk.Entry(f, textvariable=self.winkel, width=18)
        self.e2.grid(row=2, column=1, sticky=tk.W, pady=4, padx=(8, 0))
        bf = ttk.Frame(f)
        bf.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_window(self)

    def _muster(self):
        for k, n in self._arten:
            if n == self.art.get():
                return k
        return "linien"

    def _umschalten(self):
        st = "normal" if self._muster() == "linien" else "disabled"
        self.e1.configure(state=st)
        self.e2.configure(state=st)

    def _ok(self):
        muster = self._muster()
        abstand, winkel = 5.0, 45.0
        if muster == "linien":
            try:
                abstand = float(self.abstand.get().replace(",", "."))
                winkel = float(self.winkel.get().replace(",", "."))
            except ValueError:
                messagebox.showerror(self.title(), "Bitte Zahlen eingeben."
                                     if SPRACHE["aktuell"] == "de"
                                     else "Please enter numbers.", parent=self)
                return
            if abstand <= 0:
                messagebox.showerror(self.title(), "Abstand muss größer als 0 sein."
                                     if SPRACHE["aktuell"] == "de"
                                     else "Spacing must be greater than 0.",
                                     parent=self)
                return
        self.result = (muster, abstand, winkel)
        self.destroy()


class ArrayDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.result = None
        self.einh = app._einh_faktor()
        self.title(tr("dlg.reihe.titel"))
        self.geometry("380x260")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        self.v = {}
        zeilen = [(tr("dlg.reihe.spalten"), "nx", 3),
                  (tr("dlg.reihe.zeilen"), "ny", 1),
                  (tr("dlg.reihe.dx", unit=app.einheit.get()), "dx", 10.0),
                  (tr("dlg.reihe.dy", unit=app.einheit.get()), "dy", 10.0)]
        for r, (text, key, wert) in enumerate(zeilen):
            ttk.Label(f, text=text).grid(row=r, column=0, sticky=tk.W, pady=4)
            var = tk.StringVar(value=str(wert))
            self.v[key] = var
            ttk.Entry(f, textvariable=var, width=14).grid(row=r, column=1,
                                                            sticky=tk.W, pady=4)
        ttk.Label(f, text=tr("dlg.reihe.hinweis"), style="Hint.TLabel").grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=6)
        bf = ttk.Frame(f)
        bf.grid(row=5, column=0, columnspan=2, pady=8)
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.wait_window(self)

    def _ok(self):
        de = SPRACHE["aktuell"] == "de"
        try:
            g = lambda k: float(self.v[k].get().replace(",", "."))
            nx, ny = int(g("nx")), int(g("ny"))
            if nx < 1 or ny < 1 or nx * ny > 10000:
                raise ValueError(("Anzahl muss zwischen 1 und 10000 liegen." if de
                                  else "Count must be between 1 and 10000."))
            self.result = (nx, ny, g("dx") * self.einh, g("dy") * self.einh)
            self.destroy()
        except Exception as e:
            messagebox.showerror(tr("dlg.reihe.titel"), str(e))


class DruckDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.result = None
        self.title(tr("dlg.druck.titel"))
        self.geometry("460x470")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        self.quelle = tk.StringVar(
            value="layout" if app._ist_layout() else "modell")
        self.farbig = tk.BooleanVar(value=False)
        self.rahmen = tk.BooleanVar(value=False)
        ttk.Label(f, text=tr("dlg.druck.was"), style="Title.TLabel").pack(anchor=tk.W)
        ttk.Radiobutton(f, text=tr("dlg.druck.layout"),
                        value="layout", variable=self.quelle,
                        command=self._refresh_layout_auswahl).pack(anchor=tk.W, padx=10)
        ttk.Radiobutton(f, text=tr("dlg.druck.modell"),
                        value="modell", variable=self.quelle,
                        command=self._refresh_layout_auswahl).pack(anchor=tk.W, padx=10)

        self.layout_auswahl_frame = ttk.Frame(f)
        self.layout_auswahl_frame.pack(anchor=tk.W, fill=tk.X, pady=(4, 0))
        ttk.Label(self.layout_auswahl_frame,
                  text=tr("dlg.druck.layout_auswahl")).pack(side=tk.LEFT, padx=(10, 4))
        self.layout_names = [l.name for l in app.layouts]
        self.layout_var = tk.StringVar(
            value=self.layout_names[app.aktives_layout]
            if 0 <= app.aktives_layout < len(self.layout_names) else "")
        self.layout_cb = ttk.Combobox(self.layout_auswahl_frame,
                                      textvariable=self.layout_var,
                                      values=self.layout_names,
                                      state="readonly", width=22)
        self.layout_cb.pack(side=tk.LEFT)

        ttk.Label(f, text=tr("dlg.druck.blattformat"),
                  style="Title.TLabel").pack(anchor=tk.W, pady=(10, 0))
        self.format_var = tk.StringVar(value=app.layout_format)
        ttk.Combobox(f, textvariable=self.format_var,
                     values=list(ZEICHNUNGSFORMATE.keys()),
                     width=18, state="readonly").pack(anchor=tk.W, padx=10)
        ttk.Label(f, text=tr("dlg.druck.darstellung"),
                  style="Title.TLabel").pack(anchor=tk.W, pady=(10, 0))
        ttk.Radiobutton(f, text=tr("dlg.druck.sw"), value=False,
                        variable=self.farbig).pack(anchor=tk.W, padx=10)
        ttk.Radiobutton(f, text=tr("dlg.druck.farbig"), value=True,
                        variable=self.farbig).pack(anchor=tk.W, padx=10)
        ttk.Checkbutton(f, text=tr("dlg.druck.rahmen"),
                        variable=self.rahmen).pack(anchor=tk.W, padx=10, pady=(8, 0))
        bf = ttk.Frame(f)
        bf.pack(pady=14)
        ttk.Button(bf, text=tr("dlg.druck.pdf"),
                   command=lambda: self._ok("pdf")).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.druck.vorschau"),
                   command=lambda: self._ok("vorschau")).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.druck.drucken"),
                   command=lambda: self._ok("druck")).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=4)
        self._refresh_layout_auswahl()
        self.wait_window(self)

    def _refresh_layout_auswahl(self):
        if self.quelle.get() == "layout":
            for w in self.layout_auswahl_frame.winfo_children():
                w.pack(side=tk.LEFT, padx=2)
            self.layout_cb.config(state="readonly")
        else:
            for w in self.layout_auswahl_frame.winfo_children():
                w.pack_forget()

    def _ok(self, aktion):
        idx = self.app.aktives_layout
        if self.quelle.get() == "layout":
            try:
                idx = self.layout_names.index(self.layout_var.get())
            except ValueError:
                idx = self.app.aktives_layout
        if self.quelle.get() == "layout" and 0 <= idx < len(self.app.layouts):
            self.app.layouts[idx].format = self.format_var.get()
        self.result = (aktion, self.quelle.get(),
                       bool(self.farbig.get()), bool(self.rahmen.get()), idx)
        self.destroy()


# ============================================================
# NEW (step 3): block dialogs
# ============================================================
class _BlockNameDialog(tk.Toplevel):
    """Asks for the name of a block to be created.

    Attributes:
        result: the entered name (or None on cancel)

    Parameters:
        parent          parent window
        bibliothek      BlockBibliothek (for the existence check)
        startname       suggestion (e.g. "Block1")
    """

    def __init__(self, parent, bibliothek, startname="Block1"):
        super().__init__(parent)
        self.bibliothek = bibliothek
        self.result = None
        self.title(tr("dlg.block.name.titel"))
        self.geometry("420x190")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])

        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text=tr("dlg.block.name")).pack(anchor=tk.W)
        self.name_var = tk.StringVar(value=startname)
        self.entry = ttk.Entry(f, textvariable=self.name_var, width=36)
        self.entry.pack(fill=tk.X, pady=(4, 8))
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)

        self.hinweis = ttk.Label(f, text="", style="Hint.TLabel",
                                 wraplength=380, justify=tk.LEFT)
        self.hinweis.pack(anchor=tk.W, pady=(0, 6))

        bf = ttk.Frame(f)
        bf.pack(pady=(6, 0))
        self.btn_ok = ttk.Button(bf, text=tr("dlg.ok"), command=self._ok)
        self.btn_ok.pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=4)

        self.name_var.trace_add("write", lambda *_: self._pruefen())
        self._pruefen()

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        mx = parent.winfo_rootx() + parent.winfo_width() // 2
        my = parent.winfo_rooty() + parent.winfo_height() // 2
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f"+{mx - w // 2}+{my - h // 2}")
        self.wait_window(self)

    def _pruefen(self):
        name = self.name_var.get().strip()
        if not name:
            self.hinweis.config(
                text=tr("dlg.block.name_leer"),
                foreground=FARBEN["rot"])
            self.btn_ok.state(["disabled"])
            return
        if name in self.bibliothek:
            self.hinweis.config(
                text=tr("dlg.block.name_existiert", name=name),
                foreground=FARBEN["rot"])
            self.btn_ok.state(["disabled"])
            return
        self.hinweis.config(
            text=tr("dlg.block.name_ok", name=name),
            foreground=FARBEN["gruen"])
        self.btn_ok.state(["!disabled"])

    def _ok(self):
        name = self.name_var.get().strip()
        if not name or name in self.bibliothek:
            return
        self.result = name
        self.destroy()


class _BlockAuswahlDialog(tk.Toplevel):
    """Selection of a block from the library for insertion.

    Attributes:
        result: the chosen block name (or None on cancel)
        geloescht: list of names the user removed via the
                   delete button (CadApp persists this).
    """

    def __init__(self, parent, bibliothek, titel=None, knopf=None,
                 hinweis=None):
        super().__init__(parent)
        self.bibliothek = bibliothek
        self.result = None
        self.geloescht = []
        self.title(titel or tr("dlg.block.auswahl.titel"))
        self.geometry("520x460")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])

        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)

        kopf = ttk.Frame(f)
        kopf.pack(fill=tk.X)
        ttk.Label(kopf, text=tr("dlg.block.auswahl.kopf"),
                  style="Title.TLabel").pack(side=tk.LEFT)
        self._anzahl_lbl = ttk.Label(kopf, text="", style="Hint.TLabel")
        self._anzahl_lbl.pack(side=tk.RIGHT)

        ttk.Separator(f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(6, 8))

        listen_frame = ttk.Frame(f)
        listen_frame.pack(fill=tk.BOTH, expand=True)

        spalten = ("name", "anzahl")
        self.tree = ttk.Treeview(listen_frame, columns=spalten,
                                 show="headings", height=12,
                                 selectmode="browse")
        self.tree.heading("name", text=tr("dlg.block.auswahl.name"))
        self.tree.heading("anzahl", text=tr("dlg.block.auswahl.anzahl"))
        self.tree.column("name", width=360, anchor=tk.W)
        self.tree.column("anzahl", width=90, anchor=tk.CENTER)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_buttons())
        self.tree.bind("<Double-Button-1>", lambda e: self._einfuegen())

        sb = ttk.Scrollbar(listen_frame, orient=tk.VERTICAL,
                           command=self.tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=sb.set)

        info = ttk.Label(f, text=hinweis or tr("dlg.block.auswahl.hinweis"),
                         style="Hint.TLabel", wraplength=480, justify=tk.LEFT)
        info.pack(anchor=tk.W, pady=(8, 4))

        bf = ttk.Frame(f)
        bf.pack(fill=tk.X, pady=(6, 0))
        self.btn_einfuegen = ttk.Button(bf, text=knopf or tr("dlg.block.auswahl.einfuegen"),
                                        command=self._einfuegen)
        self.btn_einfuegen.pack(side=tk.LEFT, padx=4)
        self.btn_loeschen = ttk.Button(bf, text=tr("dlg.block.auswahl.loeschen"),
                                       command=self._loeschen)
        self.btn_loeschen.pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.RIGHT, padx=4)

        self._aktualisiere()
        self._update_buttons()

        self.bind("<Return>", lambda e: self._einfuegen())
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        mx = parent.winfo_rootx() + parent.winfo_width() // 2
        my = parent.winfo_rooty() + parent.winfo_height() // 2
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f"+{mx - w // 2}+{my - h // 2}")
        self.wait_window(self)

    def _aktualisiere(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        namen = self.bibliothek.namen()
        for name in namen:
            d = self.bibliothek.get(name)
            if d is None:
                continue
            self.tree.insert("", "end", iid=name,
                             values=(name, len(d.elemente)))
        if namen:
            self.tree.selection_set(namen[0])
            self.tree.focus(namen[0])
        self._anzahl_lbl.config(text=tr("dlg.block.auswahl.anzahl_bloecke",
                                        n=len(namen)))

    def _selektiert(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _update_buttons(self):
        hat = bool(self._selektiert())
        state = ["!disabled"] if hat else ["disabled"]
        self.btn_einfuegen.state(state)
        self.btn_loeschen.state(state)

    def _einfuegen(self):
        name = self._selektiert()
        if not name:
            return
        self.result = name
        self.destroy()

    def _loeschen(self):
        name = self._selektiert()
        if not name:
            return
        if not messagebox.askyesno(
                tr("dlg.block.auswahl.loeschen"),
                tr("dlg.block.auswahl.loeschen_frage", name=name),
                parent=self):
            return
        if self.bibliothek.loesche(name):
            self.geloescht.append(name)
            self._aktualisiere()
            self._update_buttons()


# ============================================================
# NEW: helper function + project and attribute dialogs
# ============================================================
def _zentrieren(dlg, parent):
    dlg.update_idletasks()
    mx = parent.winfo_rootx() + parent.winfo_width() // 2
    my = parent.winfo_rooty() + parent.winfo_height() // 2
    dlg.geometry(f"+{mx - dlg.winfo_width() // 2}+{my - dlg.winfo_height() // 2}")


class ProjektNeuDialog(tk.Toplevel):
    """Project name + freely selectable location.

    result: (name, base_folder) or None. The program then creates
    <base_folder>/<name>/.
    """

    def __init__(self, parent, startordner=""):
        super().__init__(parent)
        self.result = None
        self.title(tr("dlg.projekt.neu.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)

        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text=tr("dlg.projekt.name")).grid(row=0, column=0,
                                                       sticky=tk.W)
        self.name_var = tk.StringVar()
        self.e_name = ttk.Entry(f, textvariable=self.name_var, width=44)
        self.e_name.grid(row=1, column=0, columnspan=2, sticky=tk.EW,
                         pady=(2, 10))

        ttk.Label(f, text=tr("dlg.projekt.ort")).grid(row=2, column=0,
                                                      sticky=tk.W)
        self.ort_var = tk.StringVar(value=startordner or "")
        ttk.Entry(f, textvariable=self.ort_var, width=36).grid(
            row=3, column=0, sticky=tk.EW, pady=(2, 4))
        ttk.Button(f, text=tr("dlg.projekt.durchsuchen"),
                   command=self._durchsuchen).grid(row=3, column=1,
                                                   padx=(6, 0))

        self.lbl_ziel = ttk.Label(f, text="", style="Hint.TLabel",
                                  wraplength=420, justify=tk.LEFT)
        self.lbl_ziel.grid(row=4, column=0, columnspan=2, sticky=tk.W,
                           pady=(4, 8))

        bf = ttk.Frame(f)
        bf.grid(row=5, column=0, columnspan=2, pady=(6, 0))
        self.btn_ok = ttk.Button(bf, text=tr("dlg.ok"), command=self._ok)
        self.btn_ok.pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=4)

        f.columnconfigure(0, weight=1)
        self.name_var.trace_add("write", lambda *_: self._pruefen())
        self.ort_var.trace_add("write", lambda *_: self._pruefen())
        self._pruefen()
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.e_name.focus_set()
        _zentrieren(self, parent)
        self.wait_window(self)

    def _durchsuchen(self):
        pfad = filedialog.askdirectory(
            parent=self, title=tr("dlg.projekt.ort"),
            initialdir=self.ort_var.get() or None)
        if pfad:
            self.ort_var.set(pfad)

    def _pruefen(self):
        import os
        name = self.name_var.get().strip()
        ort = self.ort_var.get().strip()
        fehler = name_pruefen(name)
        msg = None
        if fehler:
            msg = tr("dlg.projekt.fehler." + fehler)
        elif not ort or not os.path.isdir(ort):
            msg = tr("dlg.projekt.fehler.basis_fehlt")
        elif os.path.exists(os.path.join(ort, name)) and \
                os.listdir(os.path.join(ort, name)):
            msg = tr("dlg.projekt.fehler.ordner_existiert")
        if msg:
            self.lbl_ziel.config(text=msg, foreground=FARBEN["rot"])
            self.btn_ok.state(["disabled"])
        else:
            self.lbl_ziel.config(
                text=tr("dlg.projekt.ziel", pfad=os.path.join(ort, name)),
                foreground=FARBEN["gruen"])
            self.btn_ok.state(["!disabled"])

    def _ok(self):
        if "disabled" in self.btn_ok.state():
            return
        self.result = (self.name_var.get().strip(), self.ort_var.get().strip())
        self.destroy()


class AttributDefinitionDialog(tk.Toplevel):
    """Defines a block attribute (tag, prompt, default, height).

    result: dict {tag, prompt, wert, hoehe, sichtbar} or None.
    """

    def __init__(self, parent, hoehe=3.5, vorgabe=None):
        super().__init__(parent)
        self.result = None
        v = vorgabe or {}
        self.title(tr("dlg.attdef.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)

        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)

        self.v_tag = tk.StringVar(value=v.get("tag", ""))
        self.v_prompt = tk.StringVar(value=v.get("prompt", ""))
        self.v_wert = tk.StringVar(value=v.get("wert", ""))
        self.v_hoehe = tk.StringVar(value=str(v.get("hoehe", hoehe)))
        self.v_sicht = tk.BooleanVar(value=v.get("sichtbar", True))
        self._pos_werte = list(Text.EINFUEGEPUNKTE)
        self._pos_anzeige = [tr(f"tx.punkt.{k}") for k in self._pos_werte]
        aktuell = v.get("einfuegepunkt", Text.STANDARD_EINFUEGEPUNKT)
        if aktuell not in self._pos_werte:
            aktuell = Text.STANDARD_EINFUEGEPUNKT
        self.v_pos = tk.StringVar(
            value=self._pos_anzeige[self._pos_werte.index(aktuell)])

        zeilen = (("dlg.attdef.tag", self.v_tag),
                  ("dlg.attdef.prompt", self.v_prompt),
                  ("dlg.attdef.wert", self.v_wert),
                  ("dlg.attdef.hoehe", self.v_hoehe))
        self._entries = []
        for i, (key, var) in enumerate(zeilen):
            ttk.Label(f, text=tr(key)).grid(row=i, column=0, sticky=tk.W,
                                            pady=3, padx=(0, 10))
            e = ttk.Entry(f, textvariable=var, width=30)
            e.grid(row=i, column=1, sticky=tk.EW, pady=3)
            self._entries.append(e)
        ttk.Label(f, text=tr("dlg.attdef.position")).grid(
            row=4, column=0, sticky=tk.W, pady=3, padx=(0, 10))
        ttk.Combobox(f, textvariable=self.v_pos, values=self._pos_anzeige,
                     state="readonly", width=28).grid(
            row=4, column=1, sticky=tk.EW, pady=3)
        ttk.Checkbutton(f, text=tr("dlg.attdef.sichtbar"),
                        variable=self.v_sicht).grid(
            row=5, column=1, sticky=tk.W, pady=(4, 2))
        ttk.Label(f, text=tr("dlg.attdef.hinweis"), style="Hint.TLabel",
                  wraplength=380, justify=tk.LEFT).grid(
            row=6, column=0, columnspan=2, sticky=tk.W, pady=(6, 4))

        bf = ttk.Frame(f)
        bf.grid(row=7, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(
            side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=4)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self._entries[0].focus_set()
        _zentrieren(self, parent)
        self.wait_window(self)

    def _ok(self):
        tag = self.v_tag.get().strip().upper().replace(" ", "_")
        if not tag:
            messagebox.showwarning(tr("dlg.attdef.titel"),
                                   tr("dlg.attdef.tag_leer"), parent=self)
            return
        try:
            hoehe = float(self.v_hoehe.get().strip().replace(",", "."))
            if hoehe <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(tr("dlg.attdef.titel"),
                                   tr("dlg.attdef.hoehe_ungueltig"),
                                   parent=self)
            return
        self.result = {"tag": tag,
                       "prompt": self.v_prompt.get().strip() or tag,
                       "wert": self.v_wert.get(),
                       "hoehe": hoehe,
                       "einfuegepunkt": self._pos_werte[
                           self._pos_anzeige.index(self.v_pos.get())],
                       "sichtbar": bool(self.v_sicht.get())}
        self.destroy()


class BlockAttributeDialog(tk.Toplevel):
    """Prompt for / edit the attributes of a block reference.

    result: dict {TAG: value} or None.
    """

    def __init__(self, parent, ref, titel=None, ausschliessen=()):
        super().__init__(parent)
        self.result = None
        self.ausgeblendet = set()
        self._ausschluss = set(ausschliessen or ())
        self.title(titel or tr("dlg.attedit.titel", name=ref.block_name))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)

        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)
        self._vars = {}
        self._sicht = {}
        self._entries = []
        gesehen = set()
        zeile = 0
        for ad in ref.attribut_definitionen():
            if ad.tag in gesehen or ad.tag in self._ausschluss:
                continue
            gesehen.add(ad.tag)
            text = ad.prompt if ad.prompt and ad.prompt != ad.tag \
                else ad.tag
            if ad.prompt and ad.prompt != ad.tag:
                text = f"{ad.prompt}  [{ad.tag}]"
            ttk.Label(f, text=text).grid(row=zeile, column=0, sticky=tk.W,
                                         pady=3, padx=(0, 10))
            var = tk.StringVar(value=ref.attribute.get(ad.tag, ad.wert))
            e = ttk.Entry(f, textvariable=var, width=32)
            e.grid(row=zeile, column=1, sticky=tk.EW, pady=3)
            sv = tk.BooleanVar(value=ad.tag not in ref.ausgeblendet)
            ttk.Checkbutton(f, text=tr("dlg.attedit.anzeigen"),
                            variable=sv).grid(row=zeile, column=2,
                                              padx=(8, 0), pady=3)
            self._vars[ad.tag] = var
            self._sicht[ad.tag] = sv
            self._entries.append(e)
            zeile += 1
        if not self._vars:
            ttk.Label(f, text=tr("dlg.attedit.keine"),
                      style="Hint.TLabel").grid(row=0, column=0)

        # Device (block with electrical mask): main or auxiliary device
        self.rolle = None
        self.spiegel = None
        self._v_spiegel = None
        self._v_rolle = None
        maske = ref.geraet_maske() if hasattr(ref, "geraet_maske") else None
        if maske is not None:
            self._v_rolle = tk.StringVar(value=maske.rolle)
            ttk.Label(f, text=tr("dlg.maske.rolle")).grid(
                row=zeile, column=0, sticky=tk.W, pady=(8, 2))
            rf = ttk.Frame(f)
            rf.grid(row=zeile, column=1, columnspan=2, sticky=tk.W, pady=(8, 2))
            ttk.Radiobutton(rf, text=tr("dlg.maske.rolle.haupt"), value="haupt",
                            variable=self._v_rolle).pack(side=tk.LEFT, padx=(0, 12))
            ttk.Radiobutton(rf, text=tr("dlg.maske.rolle.hilfs"), value="hilfs",
                            variable=self._v_rolle).pack(side=tk.LEFT)
            zeile += 1
            self._v_spiegel = tk.StringVar(value=getattr(maske, "spiegel", "liste"))
            ttk.Label(f, text=tr("dlg.maske.spiegel")).grid(
                row=zeile, column=0, sticky=tk.NW, pady=(4, 2))
            sf = ttk.Frame(f)
            sf.grid(row=zeile, column=1, columnspan=2, sticky=tk.W, pady=(4, 2))
            for w in ElektroMaske.SPIEGEL:
                ttk.Radiobutton(sf, text=tr("dlg.maske.spiegel." + w), value=w,
                                variable=self._v_spiegel).pack(anchor=tk.W)
            zeile += 1

        bf = ttk.Frame(f)
        bf.grid(row=zeile + 1, column=0, columnspan=3, pady=(10, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(
            side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        if self._entries:
            self._entries[0].focus_set()
            self._entries[0].select_range(0, tk.END)
        _zentrieren(self, parent)
        self.wait_window(self)

    def _ok(self):
        if self._v_rolle is not None:
            self.rolle = self._v_rolle.get()
        if self._v_spiegel is not None:
            self.spiegel = self._v_spiegel.get()
        self.result = {t: v.get() for t, v in self._vars.items()}
        # Tags whose text is to be hidden in this instance
        self.ausgeblendet = {t for t, v in self._sicht.items() if not v.get()}
        self.destroy()


class QuerverweisDialog(tk.Toplevel):
    """Type (outgoing/incoming), direction (N/E/S/W) and text of a
    cross reference. result: dict {art, richtung, text} or None."""

    def __init__(self, parent, vorgabe=None):
        super().__init__(parent)
        self.result = None
        v = vorgabe or {}
        self.title(tr("dlg.qv.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)

        self._arten = ["abgehend", "ankommend"]
        self._rt = [0, 90, 180, 270]
        self.v_art = tk.StringVar(value=tr("dlg.qv.art." + v.get("art", "abgehend")))
        self.v_rt = tk.StringVar(value=tr("dlg.qv.rt.%d" % v.get("richtung", 0)))
        self.v_text = tk.StringVar(value=v.get("text", "L1"))

        ttk.Label(f, text=tr("dlg.qv.art")).grid(row=0, column=0, sticky=tk.W, pady=3, padx=(0, 10))
        ttk.Combobox(f, textvariable=self.v_art, state="readonly", width=22,
                     values=[tr("dlg.qv.art." + a) for a in self._arten]
                     ).grid(row=0, column=1, sticky=tk.EW, pady=3)
        ttk.Label(f, text=tr("dlg.qv.richtung")).grid(row=1, column=0, sticky=tk.W, pady=3, padx=(0, 10))
        ttk.Combobox(f, textvariable=self.v_rt, state="readonly", width=22,
                     values=[tr("dlg.qv.rt.%d" % r) for r in self._rt]
                     ).grid(row=1, column=1, sticky=tk.EW, pady=3)
        ttk.Label(f, text=tr("dlg.qv.text")).grid(row=2, column=0, sticky=tk.W, pady=3, padx=(0, 10))
        self.e_text = ttk.Entry(f, textvariable=self.v_text, width=24)
        self.e_text.grid(row=2, column=1, sticky=tk.EW, pady=3)
        from katiecad.model.core import Querverweis as _QV
        self.v_th = tk.StringVar(value=_zahl_text(v.get("text_hoehe") or _QV.TEXT_HOEHE))
        self.v_zh = tk.StringVar(value=_zahl_text(v.get("ziel_hoehe") or _QV.ZIEL_HOEHE))
        for r, (lbl, var) in enumerate((("dlg.qv.text_hoehe", self.v_th),
                                        ("dlg.qv.ziel_hoehe", self.v_zh)), start=3):
            ttk.Label(f, text=tr(lbl)).grid(row=r, column=0, sticky=tk.W, pady=3, padx=(0, 10))
            ttk.Entry(f, textvariable=var, width=10).grid(row=r, column=1, sticky=tk.W, pady=3)
        self.v_extern = tk.BooleanVar(value=bool(v.get("extern", False)))
        ttk.Checkbutton(f, text=tr("dlg.qv.extern"),
                        variable=self.v_extern).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))
        self.v_reset = tk.BooleanVar(value=False)
        if v.get("bearbeiten"):
            ttk.Checkbutton(f, text=tr("dlg.qv.reset"),
                            variable=self.v_reset).grid(
                row=6, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
        ttk.Label(f, text=tr("dlg.qv.hinweis"), style="Hint.TLabel",
                  wraplength=330, justify=tk.LEFT).grid(
            row=7, column=0, columnspan=2, sticky=tk.W, pady=(6, 4))
        bf = ttk.Frame(f)
        bf.grid(row=8, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.e_text.focus_set()
        self.e_text.select_range(0, tk.END)
        _zentrieren(self, parent)
        self.wait_window(self)

    def _ok(self):
        art = self._arten[[tr("dlg.qv.art." + a) for a in self._arten].index(self.v_art.get())]
        rt = self._rt[[tr("dlg.qv.rt.%d" % r) for r in self._rt].index(self.v_rt.get())]
        try:
            th = float(self.v_th.get().replace(",", "."))
            zh = float(self.v_zh.get().replace(",", "."))
            if th <= 0 or zh <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(tr("dlg.qv.titel"), tr("dlg.qv.fehler_hoehe"), parent=self)
            return
        self.result = {"art": art, "richtung": rt, "text": self.v_text.get().strip(),
                       "extern": bool(self.v_extern.get()),
                       "text_hoehe": th, "ziel_hoehe": zh,
                       "reset": bool(self.v_reset.get())}
        self.destroy()


class PruefungDialog(tk.Toplevel):
    """Non-modal result list of the project check. Double click = jump to
    the location (callback springen(befund))."""

    def __init__(self, parent, befunde, springen, neu_pruefen=None):
        super().__init__(parent)
        self._springen = springen
        self._neu = neu_pruefen
        self._befunde = []
        self.title(tr("dlg.pr.titel"))
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        self.v_info = tk.StringVar()
        ttk.Label(f, textvariable=self.v_info).pack(anchor=tk.W, pady=(0, 6))
        cols = ("stufe", "blatt", "text")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", height=14)
        for c, w in (("stufe", 80), ("blatt", 130), ("text", 460)):
            self.tree.heading(c, text=tr("dlg.pr.sp." + c))
            self.tree.column(c, width=w, anchor=tk.W)
        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.bind("<Double-1>", lambda e: self._los())
        self.tree.bind("<Return>", lambda e: self._los())
        bf = ttk.Frame(self, padding=(10, 0, 10, 10))
        bf.pack(fill=tk.X)
        ttk.Button(bf, text=tr("dlg.pr.neu"), command=self._aktualisieren).pack(side=tk.LEFT)
        ttk.Button(bf, text=tr("dlg.pr.kopieren"), command=self._kopieren).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text=tr("dlg.schliessen"), command=self.destroy).pack(side=tk.RIGHT)
        self.befunde_setzen(befunde)
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 80}")

    def befunde_setzen(self, befunde):
        self._befunde = list(befunde)
        self.tree.delete(*self.tree.get_children())
        for i, b in enumerate(self._befunde):
            self.tree.insert("", tk.END, iid=str(i), values=(
                tr("pr.stufe." + b.stufe), b.blatt_name, b.text))
        n = {s: 0 for s in ("fehler", "warnung", "hinweis")}
        for b in self._befunde:
            n[b.stufe] += 1
        self.v_info.set(tr("dlg.pr.summe", f=n["fehler"], w=n["warnung"],
                           h=n["hinweis"]) if self._befunde else tr("pr.ok"))

    def _los(self):
        sel = self.tree.selection()
        if sel:
            self._springen(self._befunde[int(sel[0])])

    def _aktualisieren(self):
        if self._neu:
            self.befunde_setzen(self._neu())

    def _kopieren(self):
        from katiecad.electrical.pruefung import bericht_text
        self.clipboard_clear()
        self.clipboard_append(bericht_text(self._befunde))


class EigenschaftenPalette(tk.Toplevel):
    """Non-modal properties window (Ctrl+1) for the current selection.
    Works with mixed selections (lines, texts, ...): a field shows
    '*' if the values differ; changes apply to ALL affected elements."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title(tr("dlg.eig.titel"))
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._schliessen)
        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        self.v_info = tk.StringVar()
        ttk.Label(f, textvariable=self.v_info, style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 6))
        self._vars, self._rows = {}, {}

        def zeile(r, feld, widget_fn):
            lb = ttk.Label(f, text=tr("dlg.eig." + feld))
            lb.grid(row=r, column=0, sticky=tk.W, pady=2, padx=(0, 8))
            w = widget_fn()
            w.grid(row=r, column=1, sticky=tk.EW, pady=2)
            self._rows[feld] = (lb, w)

        r = 1
        for feld in ("layer", "linientyp"):
            v = tk.StringVar()
            self._vars[feld] = v
            vals = (lambda: list(app.layers.keys())) if feld == "layer" \
                else (lambda: list(LINIENTYPEN.keys()))
            cb = ttk.Combobox(f, textvariable=v, width=24, values=vals())
            cb.configure(postcommand=lambda c=cb, fn=vals: c.configure(values=fn()))
            cb.bind("<<ComboboxSelected>>", lambda e, k=feld: self._anwenden(k))
            zeile(r, feld, lambda c=cb: c)
            r += 1
        # colour: button + "by layer"
        self._vars["farbe"] = tk.StringVar()
        fr = ttk.Frame(f)
        self.btn_farbe = ttk.Button(fr, textvariable=self._vars["farbe"], width=12,
                                    command=self._farbe_waehlen)
        self.btn_farbe.pack(side=tk.LEFT)
        ttk.Button(fr, text=tr("dlg.eig.vonlayer"), width=10,
                   command=lambda: self._anwenden("farbe", None)).pack(side=tk.LEFT, padx=4)
        zeile(r, "farbe", lambda: fr)
        r += 1
        for feld, br in (("staerke", 10), ("hoehe", 10), ("winkel", 10)):
            v = tk.StringVar()
            self._vars[feld] = v
            e = ttk.Entry(f, textvariable=v, width=br)
            e.bind("<Return>", lambda ev, k=feld: self._anwenden(k))
            e.bind("<FocusOut>", lambda ev, k=feld: self._anwenden(k, nur_wenn_geaendert=True))
            zeile(r, feld, lambda w=e: w)
            r += 1
        v = tk.StringVar()
        self._vars["schriftart"] = v
        cb = ttk.Combobox(f, textvariable=v, width=24,
                          values=list(SCHRIFTARTEN) + [s + " fett" for s in SCHRIFTARTEN])
        cb.bind("<<ComboboxSelected>>", lambda e: self._anwenden("schriftart"))
        zeile(r, "schriftart", lambda: cb)
        r += 1
        ttk.Label(f, text=tr("dlg.eig.hinweis"), style="Hint.TLabel",
                  wraplength=300, justify=tk.LEFT).grid(
            row=r, column=0, columnspan=3, sticky=tk.W, pady=(8, 0))
        self._angezeigt = {}
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 40}+{parent.winfo_rooty() + 80}")
        self.aktualisieren()

    def _schliessen(self):
        self.app._eig_palette = None
        self.destroy()

    def aktualisieren(self):
        from katiecad.model.eigenschaften import gemeinsame, VERSCHIEDEN
        sel = [e for e in self.app.auswahl]
        g = gemeinsame(sel)
        self.v_info.set(tr("dlg.eig.anzahl", n=len(sel)) if g else tr("dlg.eig.keine"))
        self._angezeigt = {}
        for feld, (lb, w) in self._rows.items():
            sicht = feld in g
            state = "normal" if sicht else "disabled"
            try:
                if isinstance(w, ttk.Frame):
                    for c in w.winfo_children():
                        c.state(["!disabled"] if sicht else ["disabled"])
                else:
                    w.state(["!disabled"] if sicht else ["disabled"])
            except tk.TclError:
                pass
            if not sicht:
                self._vars[feld].set("")
                continue
            val = g[feld]
            if val == VERSCHIEDEN:
                txt = tr("dlg.eig.verschieden")
            elif val is None:
                txt = tr("dlg.eig.vonlayer") if feld == "farbe" else ""
            elif isinstance(val, float):
                txt = ("%g" % val)
            else:
                txt = str(val)
            self._vars[feld].set(txt)
            self._angezeigt[feld] = txt

    def _farbe_waehlen(self):
        akt = self._vars["farbe"].get()
        _, hexc = colorchooser.askcolor(color=akt if akt.startswith("#") else None,
                                        parent=self)
        if hexc:
            self._anwenden("farbe", hexc)

    def _anwenden(self, feld, wert="__lesen__", nur_wenn_geaendert=False):
        if wert == "__lesen__":
            wert = self._vars[feld].get().strip()
            if nur_wenn_geaendert and wert == self._angezeigt.get(feld):
                return
            if wert == tr("dlg.eig.verschieden"):
                return
            if feld in ("hoehe", "winkel", "staerke"):
                if wert == "" and feld == "staerke":
                    wert = None
                else:
                    try:
                        wert = float(wert.replace(",", "."))
                    except ValueError:
                        self.aktualisieren()
                        return
                    if feld in ("hoehe", "staerke") and wert <= 0:
                        self.aktualisieren()
                        return
        self.app.eigenschaft_anwenden(feld, wert)


class VerbindungspunkteDialog(tk.Toplevel):
    """Non-modal window 'Select connection points' for the wire tool.
    Shows the selected points; closing = cancel."""

    def __init__(self, parent, on_close):
        super().__init__(parent)
        self._on_close = on_close
        self.title(tr("dlg.leitung.titel"))
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=tr("dlg.leitung.info"), wraplength=320,
                  justify=tk.LEFT).grid(row=0, column=0, columnspan=2,
                                        sticky=tk.W, pady=(0, 8))
        self.v1 = tk.StringVar(value=tr("dlg.leitung.leer"))
        self.v2 = tk.StringVar(value=tr("dlg.leitung.leer"))
        ttk.Label(f, text=tr("dlg.leitung.punkt1"), style="Title.TLabel").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(f, textvariable=self.v1).grid(row=1, column=1, sticky=tk.W, padx=8)
        ttk.Label(f, text=tr("dlg.leitung.punkt2"), style="Title.TLabel").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(f, textvariable=self.v2).grid(row=2, column=1, sticky=tk.W, padx=8)
        ttk.Button(f, text=tr("dlg.leitung.fertig"),
                   command=self._schliessen).grid(row=3, column=0, columnspan=2, pady=(10, 0))
        self.protocol("WM_DELETE_WINDOW", self._schliessen)
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 260}+{parent.winfo_rooty() + 120}")

    def setze(self, p1=None, p2=None):
        leer = tr("dlg.leitung.leer")
        self.v1.set(p1 or leer)
        self.v2.set(p2 or leer)

    def _schliessen(self):
        cb, self._on_close = self._on_close, None
        try:
            self.destroy()
        finally:
            if cb:
                cb()

    def schliessen_still(self):
        self._on_close = None
        self.destroy()


class ProjektDruckDialog(tk.Toplevel):
    """Select several sheets of a project for PDF/print.

    result: (action, indices, source, colour, frame) or None.
    action: 'pdf' | 'vorschau' | 'druck'
    """

    def __init__(self, parent, projekt):
        super().__init__(parent)
        self.result = None
        self.title(tr("dlg.druckp.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        self.geometry("470x540")
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text=tr("dlg.druckp.blaetter"), style="Title.TLabel").pack(anchor=tk.W)
        lf = ttk.Frame(f)
        lf.pack(fill=tk.BOTH, expand=True, pady=4)
        self.lb = tk.Listbox(lf, selectmode=tk.EXTENDED, exportselection=False,
                             height=10, bg=FARBEN["bg_dunkel"], fg=FARBEN["cyan"],
                             selectbackground=FARBEN["cyan"],
                             selectforeground=FARBEN["bg_dunkel"],
                             highlightthickness=0, relief=tk.FLAT)
        sb = ttk.Scrollbar(lf, orient=tk.VERTICAL, command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        for i, b in enumerate(projekt.blaetter):
            self.lb.insert(tk.END, f"{projekt.nummer(i)}   {b.name}")
        self.lb.select_set(0, tk.END)
        kz = ttk.Frame(f)
        kz.pack(anchor=tk.W)
        ttk.Button(kz, text=tr("dlg.druckp.alle"),
                   command=lambda: self.lb.select_set(0, tk.END)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(kz, text=tr("dlg.druckp.keine"),
                   command=lambda: self.lb.select_clear(0, tk.END)).pack(side=tk.LEFT)

        self.quelle = tk.StringVar(value="layout")
        self.farbig = tk.BooleanVar(value=False)
        self.rahmen = tk.BooleanVar(value=False)
        ttk.Label(f, text=tr("dlg.druck.was"), style="Title.TLabel").pack(anchor=tk.W, pady=(10, 0))
        ttk.Radiobutton(f, text=tr("dlg.druckp.layout"), value="layout",
                        variable=self.quelle).pack(anchor=tk.W, padx=10)
        ttk.Radiobutton(f, text=tr("dlg.druckp.modell"), value="modell",
                        variable=self.quelle).pack(anchor=tk.W, padx=10)
        ttk.Label(f, text=tr("dlg.druck.darstellung"), style="Title.TLabel").pack(anchor=tk.W, pady=(10, 0))
        ttk.Radiobutton(f, text=tr("dlg.druck.sw"), value=False,
                        variable=self.farbig).pack(anchor=tk.W, padx=10)
        ttk.Radiobutton(f, text=tr("dlg.druck.farbig"), value=True,
                        variable=self.farbig).pack(anchor=tk.W, padx=10)
        ttk.Checkbutton(f, text=tr("dlg.druck.rahmen"),
                        variable=self.rahmen).pack(anchor=tk.W, padx=10, pady=(8, 0))
        bf = ttk.Frame(f)
        bf.pack(pady=12)
        ttk.Button(bf, text=tr("dlg.druck.pdf"), command=lambda: self._ok("pdf")).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.druck.vorschau"), command=lambda: self._ok("vorschau")).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.druck.drucken"), command=lambda: self._ok("druck")).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=4)
        _zentrieren(self, parent)
        self.wait_window(self)

    def _ok(self, aktion):
        idx = list(self.lb.curselection())
        if not idx:
            messagebox.showinfo(tr("dlg.druckp.titel"), tr("dlg.druckp.keine_auswahl"), parent=self)
            return
        self.result = (aktion, idx, self.quelle.get(),
                       bool(self.farbig.get()), bool(self.rahmen.get()))
        self.destroy()


class DokumentationDialog(tk.Toplevel):
    """Choose report sheets (cover sheet, table of contents, device list,
    terminal diagram, cable plan) and project data.

    vorlagen: [(display_name, path|None)] - None = without title block
    einst:    saved settings {"berichte", "vorlage", "klemmen_geraete"}
    daten:    project data {"anlage", "kunde", ...}
    result:   {"berichte": [...], "daten": {...}, "vorlage": path|None,
               "klemmen_geraete": bool} or None"""

    FELDER = ("anlage", "kunde", "auftrag", "zeichnungsnummer", "firma",
              "gezeichnet", "geprueft", "revision", "datum")
    STANDARD = ("deckblatt", "inhalt", "geraete", "klemmen", "kabel")
    TYPEN = STANDARD + ("verbindungen", "stueckliste", "querverweise",
                        "potenziale", "stecker", "etiketten", "revisionen", "sps")

    def __init__(self, parent, vorlagen, einst, daten, projektname,
                 vorlage_vorgabe=None):
        super().__init__(parent)
        self.result = None
        self._pfade = [pf for _n, pf in vorlagen]
        self.title(tr("dlg.doku.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text=tr("dlg.doku.berichte"), style="Title.TLabel").pack(anchor=tk.W)
        aktiv = einst.get("berichte")
        if not isinstance(aktiv, list):
            aktiv = list(self.STANDARD)
        self.v_typ = {}
        raster = ttk.Frame(f)
        raster.pack(anchor=tk.W, padx=10)
        haelfte = (len(self.TYPEN) + 1) // 2
        for i, t in enumerate(self.TYPEN):
            self.v_typ[t] = tk.BooleanVar(value=t in aktiv)
            ttk.Checkbutton(raster, text=tr("rep." + t),
                            variable=self.v_typ[t]).grid(
                row=i % haelfte, column=i // haelfte, sticky=tk.W, padx=(0, 24))
        self.v_klg = tk.BooleanVar(value=bool(einst.get("klemmen_geraete", True)))
        ttk.Checkbutton(f, text=tr("dlg.doku.klemmen_geraete"),
                        variable=self.v_klg).pack(anchor=tk.W, padx=10, pady=(4, 0))

        ttk.Label(f, text=tr("dlg.doku.daten"), style="Title.TLabel").pack(
            anchor=tk.W, pady=(12, 2))
        g = ttk.Frame(f)
        g.pack(fill=tk.X)
        g.columnconfigure(1, weight=1)
        self.v_f = {}
        for i, k in enumerate(self.FELDER):
            ttk.Label(g, text=tr("dlg.doku.f." + k)).grid(
                row=i, column=0, sticky=tk.W, padx=(10, 8), pady=1)
            wert = daten.get(k, "")
            if k == "anlage" and not wert:
                wert = projektname
            self.v_f[k] = tk.StringVar(value=wert)
            ttk.Entry(g, textvariable=self.v_f[k], width=34).grid(
                row=i, column=1, sticky=tk.EW, pady=1)

        ttk.Label(f, text=tr("dlg.doku.vorlage"), style="Title.TLabel").pack(
            anchor=tk.W, pady=(12, 2))
        self.v_vorlage = tk.StringVar()
        namen = [n for n, _p in vorlagen]
        self.cb = ttk.Combobox(f, textvariable=self.v_vorlage, values=namen,
                               state="readonly", width=40)
        self.cb.pack(anchor=tk.W, padx=10)
        wunsch = einst.get("vorlage", vorlage_vorgabe)
        idx = 0
        if wunsch in self._pfade:
            idx = self._pfade.index(wunsch)
        elif len(vorlagen) > 1:
            idx = 1
        if namen:
            self.cb.current(idx)

        ttk.Label(f, text=tr("dlg.doku.format"), style="Title.TLabel").pack(
            anchor=tk.W, pady=(12, 2))
        ff = ttk.Frame(f)
        ff.pack(anchor=tk.W, padx=10)
        self.v_format = tk.StringVar(
            value=einst.get("format") if einst.get("format") in ("a4", "a3") else "a4")
        for key, text in (("a4", "DIN A4"), ("a3", "DIN A3")):
            ttk.Radiobutton(ff, text=text, value=key,
                            variable=self.v_format).pack(side=tk.LEFT, padx=(0, 14))

        ttk.Label(f, text=tr("dlg.doku.hinweis"), style="Hint.TLabel",
                  wraplength=430, justify=tk.LEFT).pack(anchor=tk.W, pady=(12, 4))
        bf = ttk.Frame(f)
        bf.pack(pady=(8, 0))
        ttk.Button(bf, text=tr("dlg.doku.erzeugen"), command=self._ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.bind("<Escape>", lambda e: self.destroy())
        _zentrieren(self, parent)
        self.wait_window(self)

    def _ok(self):
        typen = [t for t in self.TYPEN if self.v_typ[t].get()]
        i = self.cb.current()
        pfad = self._pfade[i] if 0 <= i < len(self._pfade) else None
        self.result = {
            "berichte": typen,
            "daten": {k: v.get().strip() for k, v in self.v_f.items()},
            "vorlage": pfad,
            "klemmen_geraete": bool(self.v_klg.get()),
            "format": self.v_format.get(),
        }
        self.destroy()


class ProjektEigenschaftenDialog(tk.Toplevel):
    """Project properties: data for cover sheet and title blocks (filled in
    automatically on every sheet) and the revision table (4 rows).

    daten:  project data (dict); projektname: default for 'anlage'
    result: the new project data dict (all other keys are kept) or None"""

    FELDER = ("anlage", "kunde", "auftrag", "zeichnungsnummer", "firma",
              "gezeichnet", "datum", "geprueft", "geprueft_datum", "revision")
    REV_SPALTEN = ("stand", "aenderung", "name", "datum")
    REV_ZEILEN = 4

    def __init__(self, parent, daten, projektname):
        super().__init__(parent)
        self.result = None
        self._daten = dict(daten or {})
        self.title(tr("dlg.pe.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text=tr("dlg.pe.daten"), style="Title.TLabel").pack(anchor=tk.W)
        g = ttk.Frame(f)
        g.pack(fill=tk.X)
        g.columnconfigure(1, weight=1)
        self.v_f = {}
        for i, k in enumerate(self.FELDER):
            ttk.Label(g, text=tr("dlg.pe.f." + k)).grid(
                row=i, column=0, sticky=tk.W, padx=(10, 8), pady=1)
            wert = self._daten.get(k, "")
            if k == "anlage" and not wert:
                wert = projektname
            self.v_f[k] = tk.StringVar(value=wert)
            ttk.Entry(g, textvariable=self.v_f[k], width=40).grid(
                row=i, column=1, sticky=tk.EW, pady=1)

        ttk.Label(f, text=tr("dlg.pe.rev"), style="Title.TLabel").pack(
            anchor=tk.W, pady=(12, 2))
        r = ttk.Frame(f)
        r.pack(fill=tk.X, padx=(10, 0))
        breiten = {"stand": 8, "aenderung": 30, "name": 10, "datum": 12}
        for c, k in enumerate(self.REV_SPALTEN):
            ttk.Label(r, text=tr("dlg.pe.rev." + k)).grid(row=0, column=c, sticky=tk.W, padx=2)
        rev = self._daten.get("rev")
        rev = rev if isinstance(rev, list) else []
        self.v_rev = []
        for i in range(self.REV_ZEILEN):
            alt = rev[i] if i < len(rev) and isinstance(rev[i], dict) else {}
            zeile = {}
            for c, k in enumerate(self.REV_SPALTEN):
                zeile[k] = tk.StringVar(value=str(alt.get(k, "") or ""))
                ttk.Entry(r, textvariable=zeile[k], width=breiten[k]).grid(
                    row=i + 1, column=c, sticky=tk.EW, padx=2, pady=1)
            self.v_rev.append(zeile)

        ttk.Label(f, text=tr("dlg.pe.hinweis"), style="Hint.TLabel",
                  wraplength=520, justify=tk.LEFT).pack(anchor=tk.W, pady=(12, 4))
        bf = ttk.Frame(f)
        bf.pack(pady=(8, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.bind("<Escape>", lambda e: self.destroy())
        _zentrieren(self, parent)
        self.wait_window(self)

    def _ok(self):
        d = dict(self._daten)
        d.update({k: v.get().strip() for k, v in self.v_f.items()})
        d["rev"] = [{k: v.get().strip() for k, v in zeile.items()}
                    for zeile in self.v_rev]
        self.result = d
        self.destroy()


class VerbindungspunktDialog(tk.Toplevel):
    """Designation of a connection point + switch 'Show text'.
    result: {'wert': str, 'sichtbar': bool, 'richtungen': [0|90|180|270]}
    or None."""

    def __init__(self, parent, wert="", sichtbar=True, titel=None,
                 richtungen=(0, 90, 180, 270)):
        super().__init__(parent)
        self.result = None
        self.title(titel or tr("dlg.vp.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=tr("dlg.vp.text")).pack(anchor=tk.W)
        self.v_wert = tk.StringVar(value=wert)
        self.e = ttk.Entry(f, textvariable=self.v_wert, width=30)
        self.e.pack(fill=tk.X, pady=(2, 8))
        self.v_sicht = tk.BooleanVar(value=sichtbar)
        ttk.Checkbutton(f, text=tr("dlg.vp.anzeigen"),
                        variable=self.v_sicht).pack(anchor=tk.W)
        ttk.Label(f, text=tr("dlg.vp.richtungen")).pack(anchor=tk.W, pady=(10, 2))
        rf = ttk.Frame(f)
        rf.pack(anchor=tk.W)
        self.v_r = {r: tk.BooleanVar(value=r in richtungen)
                    for r in (90, 0, 270, 180)}
        for zeile, spalte, r, key in ((0, 1, 90, "nord"), (1, 2, 0, "ost"),
                                      (2, 1, 270, "sued"), (1, 0, 180, "west")):
            ttk.Checkbutton(rf, text=tr("dlg.vp." + key),
                            variable=self.v_r[r]).grid(
                row=zeile, column=spalte, sticky=tk.W, padx=6, pady=1)
        bf = ttk.Frame(f)
        bf.pack(pady=(10, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.e.focus_set()
        self.e.select_range(0, tk.END)
        _zentrieren(self, parent)
        self.wait_window(self)

    def _ok(self):
        self.result = {"wert": self.v_wert.get().strip(),
                       "sichtbar": bool(self.v_sicht.get()),
                       "richtungen": sorted(r for r, v in self.v_r.items()
                                            if v.get())}
        self.destroy()


# ============================================================
# Block browser (block files directly in the file system) + preview
# ============================================================
def zeichne_block_vorschau(canvas, geom, breite=320, hoehe=300):
    """Draws a preview geometry (blocks.vorschau_geometrie) centred
    and to scale on a canvas."""
    canvas.delete("all")
    canvas.configure(bg=FARBEN["bg_dunkel"] if "bg_dunkel" in FARBEN
                     else "#1c132d")
    bb = geom["bbox"] if geom else None
    if not bb:
        return
    x1, y1, x2, y2 = bb
    bw, bh = max(x2 - x1, 1e-6), max(y2 - y1, 1e-6)
    rand = 16
    sk = min((breite - 2 * rand) / bw, (hoehe - 2 * rand) / bh)
    ox = (breite - bw * sk) / 2 - x1 * sk
    oy = (hoehe + bh * sk) / 2 + y1 * sk

    def px(x, y):
        return ox + x * sk, oy - y * sk

    for pts, farbe in geom["flaechen"]:
        flach = [c for p in pts for c in px(*p)]
        if len(flach) >= 6:
            canvas.create_polygon(*flach, fill=farbe, outline=farbe)
    for pts, geschlossen, farbe in geom["linien"]:
        q = [px(*p) for p in pts]
        if geschlossen and len(q) > 2:
            q.append(q[0])
        if len(q) >= 2:
            canvas.create_line(*[c for p in q for c in p], fill=farbe, width=1)
    for (x, y, text, h, farbe) in geom["texte"]:
        gr = int(h * sk * 1.0)
        if gr >= 4:
            canvas.create_text(*px(x, y), text=text, fill=farbe,
                               font=("Arial", min(gr, 40)))


def oeffne_im_dateimanager(pfad):
    import subprocess
    try:
        if sys.platform.startswith("win"):
            os.startfile(pfad)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", pfad])
        else:
            subprocess.Popen(["xdg-open", pfad])
    except Exception as e:
        print(f"[KatieCAD] Dateimanager: {e}")


class BlockBrowserDialog(tk.Toplevel):
    """Browses folders with block files (*.katieblock), shows a
    preview and inserts the chosen block.

    wurzeln: [(display_name, folder_path)]
    lader:   function path -> BlockDefinition (raises on errors)
    result:  path of the chosen file or None
    wurzeln: after closing also contains the added folders"""

    def __init__(self, parent, wurzeln, lader, start=None):
        super().__init__(parent)
        self.result = None
        self.wurzeln = list(wurzeln)
        self._lader = lader
        self._dateien = {}
        self.title(tr("dlg.bb.titel"))
        self.geometry("980x560")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])

        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        f.columnconfigure(1, weight=1)
        f.rowconfigure(1, weight=1)

        ttk.Label(f, text=tr("dlg.bb.ordner"), style="Title.TLabel").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(f, text=tr("dlg.bb.dateien"), style="Title.TLabel").grid(row=0, column=1, sticky=tk.W, padx=8)
        ttk.Label(f, text=tr("dlg.bb.vorschau"), style="Title.TLabel").grid(row=0, column=2, sticky=tk.W)

        self.baum = ttk.Treeview(f, show="tree", selectmode="browse", height=18)
        self.baum.grid(row=1, column=0, sticky="ns")
        self.baum.column("#0", width=230)
        self.baum.bind("<<TreeviewSelect>>", lambda e: self._ordner_gewaehlt())

        self.liste = ttk.Treeview(f, columns=("name", "datum"), show="headings",
                                  selectmode="browse", height=18)
        self.liste.heading("name", text=tr("dlg.block.auswahl.name"))
        self.liste.heading("datum", text="")
        self.liste.column("name", width=240, anchor=tk.W)
        self.liste.column("datum", width=110, anchor=tk.CENTER)
        self.liste.grid(row=1, column=1, sticky="nsew", padx=8)
        self.liste.bind("<<TreeviewSelect>>", lambda e: self._datei_gewaehlt())
        self.liste.bind("<Double-Button-1>", lambda e: self._einfuegen())

        rf = ttk.Frame(f)
        rf.grid(row=1, column=2, sticky="n")
        self.vorschau = tk.Canvas(rf, width=320, height=300, highlightthickness=1)
        self.vorschau.pack()
        self.info = ttk.Label(rf, text="", style="Hint.TLabel", wraplength=320,
                              justify=tk.LEFT)
        self.info.pack(anchor=tk.W, pady=(6, 0))

        ttk.Label(f, text=tr("dlg.bb.hinweis"), style="Hint.TLabel",
                  wraplength=900, justify=tk.LEFT).grid(
            row=2, column=0, columnspan=3, sticky=tk.W, pady=(8, 4))

        bf = ttk.Frame(f)
        bf.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=(4, 0))
        self.btn_ein = ttk.Button(bf, text=tr("dlg.bb.einfuegen"), command=self._einfuegen)
        self.btn_ein.pack(side=tk.LEFT, padx=3)
        ttk.Button(bf, text=tr("dlg.bb.neuer_ordner"), command=self._neuer_ordner).pack(side=tk.LEFT, padx=3)
        ttk.Button(bf, text=tr("dlg.bb.ordner_hinzu"), command=self._ordner_hinzu).pack(side=tk.LEFT, padx=3)
        ttk.Button(bf, text=tr("dlg.bb.dateimanager"), command=self._dateimanager).pack(side=tk.LEFT, padx=3)
        self.btn_del = ttk.Button(bf, text=tr("dlg.bb.loeschen"), command=self._loeschen)
        self.btn_del.pack(side=tk.LEFT, padx=3)
        ttk.Button(bf, text=tr("dlg.bb.schliessen"), command=self.destroy).pack(side=tk.RIGHT, padx=3)

        self._baum_aufbauen(start)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self._einfuegen())
        self._knoepfe()
        _zentrieren(self, parent)
        self.wait_window(self)

    # Folder tree
    def _baum_aufbauen(self, auswahl=None):
        from katiecad.model.blocks import unterordner
        for i in self.baum.get_children():
            self.baum.delete(i)

        def fuelle(eltern, pfad, tiefe):
            if tiefe > 5:
                return
            for n in unterordner(pfad):
                p = os.path.join(pfad, n)
                if not self.baum.exists(p):
                    self.baum.insert(eltern, "end", iid=p, text=n, open=False)
                    fuelle(p, p, tiefe + 1)

        for name, pfad in self.wurzeln:
            if not os.path.isdir(pfad) or self.baum.exists(pfad):
                continue
            self.baum.insert("", "end", iid=pfad, text=name, open=True)
            fuelle(pfad, pfad, 0)
        ziel = auswahl if auswahl and self.baum.exists(auswahl) else None
        if ziel is None and self.baum.get_children():
            ziel = self.baum.get_children()[0]
        if ziel:
            self.baum.selection_set(ziel)
            self.baum.see(ziel)

    def _ordner(self):
        sel = self.baum.selection()
        return sel[0] if sel else None

    def _ordner_gewaehlt(self):
        from katiecad.model.blocks import blockdateien
        import time
        for i in self.liste.get_children():
            self.liste.delete(i)
        self._dateien = {}
        o = self._ordner()
        if o:
            for n, pf in blockdateien(o):
                self._dateien[n] = pf
                try:
                    d = time.strftime("%d.%m.%Y", time.localtime(os.path.getmtime(pf)))
                except OSError:
                    d = ""
                self.liste.insert("", "end", iid=n, values=(n[:-len(".katieblock")], d))
        kids = self.liste.get_children()
        if kids:
            self.liste.selection_set(kids[0])
        else:
            zeichne_block_vorschau(self.vorschau, None)
            self.info.config(text=tr("dlg.bb.keine"))
        self._knoepfe()

    def _datei(self):
        sel = self.liste.selection()
        return self._dateien.get(sel[0]) if sel else None

    def _datei_gewaehlt(self):
        from katiecad.model.blocks import vorschau_geometrie
        pf = self._datei()
        self._knoepfe()
        if not pf:
            return
        try:
            d = self._lader(pf)
            geom = vorschau_geometrie(d)
        except Exception as e:
            zeichne_block_vorschau(self.vorschau, None)
            self.info.config(text=tr("dlg.bb.fehler", fehler=e))
            return
        zeichne_block_vorschau(self.vorschau, geom)
        bb = geom["bbox"] or (0, 0, 0, 0)
        text = tr("dlg.bb.info", n=len(d.elemente), b=round(bb[2] - bb[0], 1),
                  h=round(bb[3] - bb[1], 1))
        try:
            tags = [a.tag for a in d.attribut_definitionen()]
        except Exception:
            tags = []
        if tags:
            text += "\n" + tr("dlg.bb.attribute", liste=", ".join(tags))
        self.info.config(text=text)

    def _knoepfe(self):
        st = ["!disabled"] if self._datei() else ["disabled"]
        self.btn_ein.state(st)
        self.btn_del.state(st)

    # Actions
    def _einfuegen(self):
        pf = self._datei()
        if not pf:
            return
        self.result = pf
        self.destroy()

    def _neuer_ordner(self):
        o = self._ordner()
        if not o:
            return
        from tkinter import simpledialog
        name = simpledialog.askstring(tr("dlg.bb.neuer_ordner"),
                                      tr("dlg.bb.ordnername"), parent=self)
        if not name or not name.strip():
            return
        neu = os.path.join(o, name_sicher(name.strip()))
        try:
            os.makedirs(neu, exist_ok=True)
        except OSError as e:
            messagebox.showerror(tr("dlg.bb.titel"),
                                 tr("dlg.bb.ordner_fehler", fehler=e), parent=self)
            return
        self._baum_aufbauen(neu)

    def _ordner_hinzu(self):
        pf = filedialog.askdirectory(parent=self, title=tr("dlg.bb.ordner_hinzu"))
        if not pf:
            return
        pf = os.path.normpath(pf)
        if all(os.path.normpath(p) != pf for _n, p in self.wurzeln):
            self.wurzeln.append((os.path.basename(pf) or pf, pf))
        self._baum_aufbauen(pf)

    def _dateimanager(self):
        o = self._ordner()
        if o:
            oeffne_im_dateimanager(o)

    def _loeschen(self):
        pf = self._datei()
        if not pf:
            return
        if not messagebox.askyesno(
                tr("dlg.bb.loeschen"),
                tr("dlg.bb.loeschen_frage", name=os.path.basename(pf)), parent=self):
            return
        try:
            os.remove(pf)
        except OSError as e:
            messagebox.showerror(tr("dlg.bb.titel"), str(e), parent=self)
            return
        self._ordner_gewaehlt()


def name_sicher(name):
    import re
    n = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(". ")
    return n or "Ordner"


class BlockSpeichernDialog(tk.Toplevel):
    """Name and target folder of a new block, with preview.
    result: {'name': str, 'ordner': str|None} (ordner None = only in the
    drawing) or None on cancel."""

    def __init__(self, parent, geom, name, ordner, dateiname_fn):
        super().__init__(parent)
        self.result = None
        self._fn = dateiname_fn
        self.title(tr("dlg.bs.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)
        links = ttk.Frame(f)
        links.grid(row=0, column=0, sticky="nw", padx=(0, 12))
        ttk.Label(links, text=tr("dlg.bs.name")).pack(anchor=tk.W)
        self.v_name = tk.StringVar(value=name)
        ttk.Entry(links, textvariable=self.v_name, width=40).pack(fill=tk.X, pady=(2, 8))
        self.v_datei = tk.BooleanVar(value=True)
        ttk.Checkbutton(links, text=tr("dlg.bs.datei"), variable=self.v_datei,
                        command=self._pruefen).pack(anchor=tk.W)
        ttk.Label(links, text=tr("dlg.bs.ordner")).pack(anchor=tk.W, pady=(8, 0))
        zeile = ttk.Frame(links)
        zeile.pack(fill=tk.X)
        self.v_ordner = tk.StringVar(value=ordner or "")
        ttk.Entry(zeile, textvariable=self.v_ordner, width=34).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(zeile, text=tr("dlg.bs.durchsuchen"), command=self._suchen).pack(side=tk.LEFT, padx=(4, 0))
        self.hinweis = ttk.Label(links, text="", style="Hint.TLabel", wraplength=340, justify=tk.LEFT)
        self.hinweis.pack(anchor=tk.W, pady=8)
        bf = ttk.Frame(links)
        bf.pack(pady=(4, 0))
        self.btn_ok = ttk.Button(bf, text=tr("dlg.ok"), command=self._ok)
        self.btn_ok.pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.vorschau = tk.Canvas(f, width=260, height=240, highlightthickness=1)
        self.vorschau.grid(row=0, column=1)
        zeichne_block_vorschau(self.vorschau, geom, 260, 240)
        self.v_name.trace_add("write", lambda *_: self._pruefen())
        self.v_ordner.trace_add("write", lambda *_: self._pruefen())
        self._pruefen()
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        _zentrieren(self, parent)
        self.wait_window(self)

    def _suchen(self):
        pf = filedialog.askdirectory(parent=self, title=tr("dlg.bs.ordner"),
                                     initialdir=self.v_ordner.get() or None)
        if pf:
            self.v_ordner.set(os.path.normpath(pf))

    def _pruefen(self):
        name = self.v_name.get().strip()
        if not name:
            self.hinweis.config(text=tr("dlg.bs.name_leer"), foreground=FARBEN["rot"])
            self.btn_ok.state(["disabled"])
            return
        if not self.v_datei.get() or not self.v_ordner.get().strip():
            self.hinweis.config(text=tr("dlg.bs.nur_zeichnung"), foreground=FARBEN["gelb"] if "gelb" in FARBEN else FARBEN["cyan"])
            self.btn_ok.state(["!disabled"])
            return
        datei = self._fn(name)
        pfad = os.path.join(self.v_ordner.get().strip(), datei)
        if os.path.exists(pfad):
            self.hinweis.config(text=tr("dlg.bs.existiert", datei=datei), foreground=FARBEN["rot"])
            self.btn_ok.state(["disabled"])
        else:
            self.hinweis.config(text=tr("dlg.bs.ok", pfad=pfad), foreground=FARBEN["gruen"])
            self.btn_ok.state(["!disabled"])

    def _ok(self):
        if "disabled" in self.btn_ok.state():
            return
        name = self.v_name.get().strip()
        if not name:
            return
        ordner = (self.v_ordner.get().strip()
                  if self.v_datei.get() and self.v_ordner.get().strip() else None)
        self.result = {"name": name, "ordner": ordner}
        self.destroy()



def _zahl_text(x):
    """Number for an entry field without needless decimals (287.0 -> 287)."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    return ("%.2f" % x).rstrip("0").rstrip(".")


class KoordinatenfeldDialog(tk.Toplevel):
    """Columns, rows, size and grid lines of the coordinate field.
    result: {'spalten', 'zeilen', 'breite', 'hoehe', 'raster'} or None."""

    def __init__(self, parent, vorgabe=None):
        super().__init__(parent)
        self.result = None
        v = vorgabe or {}
        self.title(tr("dlg.kf.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)
        self._vars = {}
        # Presets: DIN A4 (default) and DIN A3, each without title block
        self._voreinst = {"a4": {"spalten": 6, "zeilen": 4, "breite": 287, "hoehe": 164},
                          "a3": {"spalten": 8, "zeilen": 5, "breite": 395, "hoehe": 252.59}}
        felder = (("spalten", "dlg.kf.spalten", 6), ("zeilen", "dlg.kf.zeilen", 4),
                  ("breite", "dlg.kf.breite", 287), ("hoehe", "dlg.kf.hoehe", 164))
        self.v_preset = tk.StringVar(value="own")
        pf = ttk.Frame(f)
        pf.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))
        for key, text in (("a4", "DIN A4"), ("a3", "DIN A3"),
                          ("own", "Eigene" if SPRACHE["aktuell"] == "de" else "Custom")):
            ttk.Radiobutton(pf, text=text, value=key, variable=self.v_preset,
                            command=self._preset_gewaehlt).pack(side=tk.LEFT, padx=(0, 14))
        for i, (key, label, std) in enumerate(felder):
            self._vars[key] = tk.StringVar(value=_zahl_text(v.get(key, std)))
            ttk.Label(f, text=tr(label)).grid(row=i + 1, column=0, sticky=tk.W,
                                              pady=3, padx=(0, 10))
            ttk.Entry(f, textvariable=self._vars[key], width=10).grid(
                row=i + 1, column=1, sticky=tk.W, pady=3)
        self.v_raster = tk.BooleanVar(value=bool(v.get("raster", False)))
        ttk.Checkbutton(f, text=tr("dlg.kf.raster"), variable=self.v_raster).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=3)
        ttk.Label(f, text=tr("dlg.kf.hinweis"), style="Hint.TLabel",
                  wraplength=380, justify=tk.LEFT).grid(
            row=6, column=0, columnspan=2, sticky=tk.W, pady=(6, 4))
        self._preset_erkennen()
        for var in self._vars.values():
            var.trace_add("write", lambda *_: self._preset_erkennen())
        bf = ttk.Frame(f)
        bf.grid(row=7, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        _zentrieren(self, parent)
        self.wait_window(self)

    def _werte(self):
        try:
            return {k: float(self._vars[k].get().replace(",", "."))
                    for k in ("spalten", "zeilen", "breite", "hoehe")}
        except ValueError:
            return None

    def _preset_erkennen(self):
        """Selects A4/A3 if the values match, otherwise 'Custom'."""
        w = self._werte()
        wahl = "own"
        if w is not None:
            for k, vorg in self._voreinst.items():
                if all(abs(w[n] - vorg[n]) < 0.005 for n in vorg):
                    wahl = k
        self.v_preset.set(wahl)

    def _preset_gewaehlt(self):
        vorg = self._voreinst.get(self.v_preset.get())
        if vorg:
            for k, val in vorg.items():
                self._vars[k].set(_zahl_text(val))

    def _ok(self):
        try:
            sp = int(float(self._vars["spalten"].get().replace(",", ".")))
            ze = int(float(self._vars["zeilen"].get().replace(",", ".")))
            br = float(self._vars["breite"].get().replace(",", "."))
            ho = float(self._vars["hoehe"].get().replace(",", "."))
            if not (1 <= sp <= 99 and 1 <= ze <= 26 and br > 20 and ho > 20):
                raise ValueError
        except ValueError:
            messagebox.showerror(tr("dlg.kf.titel"), tr("dlg.kf.fehler"), parent=self)
            return
        self.result = {"spalten": sp, "zeilen": ze, "breite": br, "hoehe": ho,
                       "raster": bool(self.v_raster.get())}
        self.destroy()


class VerbindungDialog(tk.Toplevel):
    """Arms and dot of a junction (same layout as the pin dialog).
    result: {'arme': [0|90|180|270, ...], 'punkt': bool} or None."""

    def __init__(self, parent, vorgabe=None):
        super().__init__(parent)
        self.result = None
        v = vorgabe or {}
        arme = v.get("arme", (0, 90, 180))
        self.title(tr("dlg.verb.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=tr("dlg.verb.arme")).pack(anchor=tk.W, pady=(0, 2))
        rf = ttk.Frame(f)
        rf.pack(anchor=tk.W)
        self.v_r = {r: tk.BooleanVar(value=r in arme) for r in (90, 0, 270, 180)}
        for zeile, spalte, r, key in ((0, 1, 90, "nord"), (1, 2, 0, "ost"),
                                      (2, 1, 270, "sued"), (1, 0, 180, "west")):
            ttk.Checkbutton(rf, text=tr("dlg.vp." + key),
                            variable=self.v_r[r]).grid(
                row=zeile, column=spalte, sticky=tk.W, padx=6, pady=1)
        self.v_punkt = tk.BooleanVar(value=bool(v.get("punkt", True)))
        ttk.Checkbutton(f, text=tr("dlg.verb.punkt"),
                        variable=self.v_punkt).pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(f, text=tr("dlg.verb.schraeg")).pack(anchor=tk.W, pady=(10, 2))
        sf = ttk.Frame(f)
        sf.pack(anchor=tk.W)
        self.v_schraeg = tk.IntVar(value=(int(v.get("ausrichtung", 0)) * 90 + 180) % 360)
        for zeile, spalte, r, key in ((0, 1, 90, "nord"), (1, 2, 0, "ost"),
                                      (2, 1, 270, "sued"), (1, 0, 180, "west")):
            ttk.Radiobutton(sf, text=tr("dlg.vp." + key), value=r,
                            variable=self.v_schraeg).grid(
                row=zeile, column=spalte, sticky=tk.W, padx=6, pady=1)
        ttk.Label(f, text=tr("dlg.verb.hinweis"), style="Hint.TLabel",
                  wraplength=320, justify=tk.LEFT).pack(anchor=tk.W, pady=(6, 0))
        self.l_fehler = ttk.Label(f, text="", foreground="#ff6b6b")
        self.l_fehler.pack(anchor=tk.W)
        bf = ttk.Frame(f)
        bf.pack(pady=(8, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        _zentrieren(self, parent)
        self.wait_window(self)

    def _ok(self):
        arme = sorted(r for r, v in self.v_r.items() if v.get())
        if len(arme) < 2:
            self.l_fehler.config(text=tr("dlg.verb.min2"))
            return
        self.result = {"arme": arme, "punkt": bool(self.v_punkt.get()),
                       "ausrichtung": ((int(self.v_schraeg.get()) - 180) // 90) % 4}
        self.destroy()


class FestMaskeDialog(tk.Toplevel):
    """Filling in the fixed fields of an electrical mask / terminal.

    felder: list of tags (e.g. ['IND','TYP','PER']); werte: {tag: text}
    rolle:  None or 'haupt'/'hilfs' (electrical mask only)
    result: {'werte': {...}, 'rolle': ...} or None."""

    def __init__(self, parent, titel, felder, werte=None, rolle=None, hinweis="",
                 zusatz=(), spiegel=None):
        super().__init__(parent)
        self.result = None
        werte = werte or {}
        self.title(titel)
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)
        self._vars, self._entries = {}, []
        for i, tag in enumerate(felder):
            ttk.Label(f, text=tag + ":").grid(row=i, column=0, sticky=tk.W, pady=3, padx=(0, 10))
            var = tk.StringVar(value=werte.get(tag, ""))
            e = ttk.Entry(f, textvariable=var, width=30)
            e.grid(row=i, column=1, sticky=tk.EW, pady=3)
            self._vars[tag] = var
            self._entries.append(e)
        row = len(felder)
        self.v_rolle = tk.StringVar(value=rolle or "haupt")
        self._rolle = rolle is not None
        if self._rolle:
            ttk.Label(f, text=tr("dlg.maske.rolle")).grid(row=row, column=0, sticky=tk.W, pady=(8, 2))
            rf = ttk.Frame(f)
            rf.grid(row=row, column=1, sticky=tk.W, pady=(8, 2))
            ttk.Radiobutton(rf, text=tr("dlg.maske.rolle.haupt"), value="haupt",
                            variable=self.v_rolle).pack(anchor=tk.W)
            ttk.Radiobutton(rf, text=tr("dlg.maske.rolle.hilfs"), value="hilfs",
                            variable=self.v_rolle).pack(anchor=tk.W)
            row += 1
        self.v_spiegel = tk.StringVar(value=spiegel or "liste")
        self._spiegel = spiegel is not None and self._rolle
        if self._spiegel:
            ttk.Label(f, text=tr("dlg.maske.spiegel")).grid(row=row, column=0, sticky=tk.NW, pady=(4, 2))
            sf = ttk.Frame(f)
            sf.grid(row=row, column=1, sticky=tk.W, pady=(4, 2))
            for w in ElektroMaske.SPIEGEL:
                ttk.Radiobutton(sf, text=tr("dlg.maske.spiegel." + w), value=w,
                                variable=self.v_spiegel).pack(anchor=tk.W)
            row += 1
        self._zvars = {}
        for key, label, wert in zusatz:       # further input fields (e.g. cores)
            ttk.Label(f, text=label).grid(row=row, column=0, sticky=tk.W, pady=2, padx=(0, 10))
            var = tk.StringVar(value=wert)
            ttk.Entry(f, textvariable=var, width=30).grid(row=row, column=1, sticky=tk.EW, pady=2)
            self._zvars[key] = var
            row += 1
        if hinweis:
            ttk.Label(f, text=hinweis, style="Hint.TLabel", wraplength=360,
                      justify=tk.LEFT).grid(row=row, column=0, columnspan=2,
                                            sticky=tk.W, pady=(8, 4))
            row += 1
        bf = ttk.Frame(f)
        bf.grid(row=row, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        if self._entries:
            self._entries[0].focus_set()
            self._entries[0].select_range(0, tk.END)
        _zentrieren(self, parent)
        self.wait_window(self)

    def _ok(self):
        self.result = {"werte": {t: v.get().strip() for t, v in self._vars.items()},
                       "rolle": self.v_rolle.get() if self._rolle else None,
                       "spiegel": self.v_spiegel.get() if self._spiegel else None,
                       "zusatz": {k: v.get().strip() for k, v in self._zvars.items()}}
        self.destroy()


class TitleBlockDialog(tk.Toplevel):
    """Choose a title block template.

    entries: list of (label, key) - key is None (frame only), "builtin" or a
    file path. result: the chosen key, "" for 'frame only', or None (cancel)."""

    def __init__(self, parent, entries, preselect=None, on_open_folder=None,
                 folders_text=""):
        super().__init__(parent)
        self.result = None
        self._keys = [k for _l, k in entries]
        self.title(tr("dlg.tb.titel"))
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=14)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=tr("dlg.tb.auswahl")).pack(anchor=tk.W, pady=(0, 4))
        self.lb = tk.Listbox(f, height=min(12, max(5, len(entries))), width=44,
                             exportselection=False, activestyle="dotbox",
                             bg=FARBEN["bg_hell"], fg=FARBEN["cyan"],
                             selectbackground=FARBEN["select_bg"],
                             selectforeground=FARBEN["select_fg"],
                             highlightthickness=0, relief=tk.FLAT)
        for label, _k in entries:
            self.lb.insert(tk.END, label)
        self.lb.pack(fill=tk.BOTH, expand=True)
        idx = 1 if len(entries) > 1 else 0
        if preselect in self._keys:
            idx = self._keys.index(preselect)
        self.lb.selection_set(idx)
        self.lb.see(idx)
        self.lb.bind("<Double-Button-1>", lambda e: self._ok())
        ttk.Label(f, text=tr("dlg.tb.hinweis") + ("\n" + folders_text if folders_text else ""),
                  style="Hint.TLabel", wraplength=380, justify=tk.LEFT).pack(
            anchor=tk.W, pady=(8, 4))
        bf = ttk.Frame(f)
        bf.pack(pady=(8, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=4)
        if on_open_folder is not None:
            ttk.Button(bf, text=tr("dlg.tb.ordner"), command=on_open_folder).pack(
                side=tk.LEFT, padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        _zentrieren(self, parent)
        self.wait_window(self)

    def _ok(self):
        sel = self.lb.curselection()
        if not sel:
            return
        key = self._keys[sel[0]]
        self.result = "" if key is None else key
        self.destroy()


class SuchenErsetzenDialog(tk.Toplevel):
    """Find and replace texts in the open sheet or the whole project."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._treffer = []
        self._daten = {}
        self.title(tr("dlg.sr.titel"))
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        self._stand = None
        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        self.v_such = tk.StringVar()
        self.v_neu = tk.StringVar()
        self.v_gross = tk.BooleanVar(value=False)
        self.v_wort = tk.BooleanVar(value=False)
        hat_projekt = app.projekt is not None
        self.v_bereich = tk.StringVar(value="projekt" if hat_projekt else "blatt")
        ttk.Label(f, text=tr("dlg.sr.suchen")).grid(row=0, column=0, sticky=tk.W, pady=3)
        e1 = ttk.Entry(f, textvariable=self.v_such, width=40)
        e1.grid(row=0, column=1, columnspan=3, sticky=tk.EW)
        ttk.Label(f, text=tr("dlg.sr.ersetzen")).grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Entry(f, textvariable=self.v_neu, width=40).grid(
            row=1, column=1, columnspan=3, sticky=tk.EW)
        ttk.Checkbutton(f, text=tr("dlg.sr.gross"), variable=self.v_gross).grid(
            row=2, column=1, sticky=tk.W)
        ttk.Checkbutton(f, text=tr("dlg.sr.wort"), variable=self.v_wort).grid(
            row=2, column=2, columnspan=2, sticky=tk.W)
        ttk.Label(f, text=tr("dlg.sr.bereich")).grid(row=3, column=0, sticky=tk.W, pady=3)
        ttk.Radiobutton(f, text=tr("dlg.sr.blatt"), value="blatt",
                        variable=self.v_bereich).grid(row=3, column=1, sticky=tk.W)
        rb = ttk.Radiobutton(f, text=tr("dlg.sr.projekt"), value="projekt",
                             variable=self.v_bereich)
        rb.grid(row=3, column=2, sticky=tk.W)
        if not hat_projekt:
            rb.state(["disabled"])
        spalten = ("blatt", "objekt", "feld", "text", "neu")
        self.tree = ttk.Treeview(f, columns=spalten, show="headings",
                                 height=12, selectmode="extended")
        for c, w in (("blatt", 120), ("objekt", 110), ("feld", 70),
                     ("text", 170), ("neu", 170)):
            self.tree.heading(c, text=tr("dlg.sr.col." + c))
            self.tree.column(c, width=w)
        self.tree.grid(row=4, column=0, columnspan=4, sticky=tk.NSEW, pady=(8, 4))
        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.tree.yview)
        sb.grid(row=4, column=4, sticky=tk.NS, pady=(8, 4))
        self.tree.configure(yscrollcommand=sb.set)
        self.v_status = tk.StringVar(value=tr("dlg.sr.hinweis"))
        ttk.Label(f, textvariable=self.v_status, style="Hint.TLabel",
                  wraplength=560, justify=tk.LEFT).grid(
            row=5, column=0, columnspan=4, sticky=tk.W, pady=4)
        bf = ttk.Frame(f)
        bf.grid(row=6, column=0, columnspan=4, sticky=tk.EW, pady=(6, 0))
        ttk.Button(bf, text=tr("dlg.sr.btn_suchen"), command=self.suchen).pack(
            side=tk.LEFT, padx=2)
        ttk.Button(bf, text=tr("dlg.sr.btn_auswahl"),
                   command=lambda: self.ersetzen(nur_auswahl=True)).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text=tr("dlg.sr.btn_alle"),
                   command=lambda: self.ersetzen(nur_auswahl=False)).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text=tr("dlg.schliessen"), command=self.destroy).pack(
            side=tk.RIGHT, padx=2)
        f.columnconfigure(1, weight=1)
        f.rowconfigure(4, weight=1)
        self.bind("<Return>", lambda e: self.suchen())
        self.bind("<Escape>", lambda e: self.destroy())
        self.tree.bind("<Double-Button-1>", self.springen)
        e1.focus_set()
        self.wait_window(self)

    def springen(self, event=None):
        """Double click on a hit: show the object (switches the sheet if
        necessary), select it and move the dialog out of the way."""
        iid = self.tree.identify_row(event.y) if event is not None else ""
        if not iid:
            sel = self.tree.selection()
            iid = sel[0] if sel else ""
        if not iid or int(iid) >= len(self._treffer):
            return
        t = self._treffer[int(iid)]
        app = self.app
        aktiv = app.projekt.aktiv if app.projekt is not None else 0
        el = t.element
        neu_suchen = False
        if t.blatt != aktiv:
            liste = self._daten.get(t.blatt, {}).get("elemente", [])
            idx = next((k for k, d in enumerate(liste) if d is t.element), None)
            if idx is None or not app.blatt_wechseln(t.blatt):
                return
            if app._ist_layout():
                app.ansicht.set("modell")
                app.ansicht_wechseln()
            if idx >= len(app.elemente):
                return
            el = app.elemente[idx]
            neu_suchen = True          # open / stored sheets swapped roles
        app.zu_element_springen(el)
        if neu_suchen:
            self.suchen()
        self._wegruecken(el)

    def _wegruecken(self, el):
        """Moves the dialog to the side so that it does not cover `el`."""
        try:
            app = self.app
            b = el.bbox()
            px, py = app.mm_to_px((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            sx = app.canvas.winfo_rootx() + px
            sy = app.canvas.winfo_rooty() + py
            self.update_idletasks()
            x0, y0 = self.winfo_rootx(), self.winfo_rooty()
            w, h = self.winfo_width(), self.winfo_height()
            if x0 - 60 <= sx <= x0 + w + 60 and y0 - 60 <= sy <= y0 + h + 60:
                sw = self.winfo_screenwidth()
                x = 10 if sx > sw / 2 else max(10, sw - w - 10)
                self.geometry("+%d+%d" % (x, y0))
        except tk.TclError:
            pass

    def _lade(self, pfad):
        try:
            with open(pfad, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def _blatt_name(self, i):
        p = self.app.projekt
        if p is None:
            return "-"
        return "%s %s" % (p.nummer(i), p.blaetter[i].name)

    def suchen(self):
        such = self.v_such.get()
        for it in self.tree.get_children():
            self.tree.delete(it)
        self._treffer, self._daten = [], {}
        if not such:
            return
        app = self.app
        app._blatt_sichern()
        self._stand = app.projekt.aktiv if app.projekt is not None else 0
        self._treffer, self._daten = SU.suche_projekt(
            app.projekt, app.elemente, such, self.v_gross.get(),
            self.v_wort.get(), self.v_bereich.get() == "projekt", self._lade)
        neu = self.v_neu.get()
        for i, t in enumerate(self._treffer):
            self.tree.insert("", "end", iid=str(i), values=(
                self._blatt_name(t.blatt), tr("dlg.sr.art." + t.art), t.feld,
                t.text, SU.ersetzt(t.text, such, neu, self.v_gross.get(),
                                   self.v_wort.get())))
        if self._treffer:
            blaetter = len({t.blatt for t in self._treffer})
            self.v_status.set(tr("dlg.sr.n_treffer", n=len(self._treffer), b=blaetter))
        else:
            self.v_status.set(tr("dlg.sr.keine"))

    def ersetzen(self, nur_auswahl):
        such = self.v_such.get()
        if not such:
            return
        if not self._treffer:
            self.suchen()
        if nur_auswahl:
            ids = [int(i) for i in self.tree.selection()]
            hits = [self._treffer[i] for i in ids]
            if not hits:
                self.v_status.set(tr("dlg.sr.nichts_gewaehlt"))
                return
        else:
            hits = list(self._treffer)
        if not hits:
            return
        app = self.app
        aktiv = app.projekt.aktiv if app.projekt is not None else 0
        if aktiv != self._stand:            # another sheet was opened meanwhile
            self.suchen()
            self.v_status.set(tr("dlg.sr.aktualisiert"))
            return
        fremd = [t for t in hits if t.blatt != aktiv]
        if fremd and not messagebox.askyesno(
                tr("dlg.sr.titel"), tr("dlg.sr.frage_anderes", n=len(hits),
                                       m=len(fremd)), parent=self):
            return
        neu = self.v_neu.get()
        gross, wort = self.v_gross.get(), self.v_wort.get()
        eigene = [t for t in hits if t.blatt == aktiv]
        n = 0
        if eigene:
            app._snapshot()
            n += SU.ersetze(eigene, such, neu, gross, wort)
        geaendert = set()
        for t in fremd:
            if SU.ersetze([t], such, neu, gross, wort):
                n += 1
                geaendert.add(t.blatt)
        for i in geaendert:
            try:
                app._json_atomar_schreiben(app.projekt.blatt_pfad(i), self._daten[i])
            except OSError as ex:
                messagebox.showerror(tr("dlg.sr.titel"), str(ex), parent=self)
        app._qv_cache.clear()
        app.redraw()
        self.suchen()
        self.v_status.set(tr("dlg.sr.fertig", n=n))


class SchnellauswahlDialog(tk.Toplevel):
    """Quick select: choose type / layer / colour / line type.
    result = dict(kriterien, negiert, hinzufuegen) or None."""

    def __init__(self, parent, werte):
        """werte: {"typ": [...], "layer": [...], "farbe": [...], "linientyp": [...]}"""
        super().__init__(parent)
        de = SPRACHE["aktuell"] == "de"
        self.result = None
        self.title("Schnellauswahl" if de else "Quick select")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        alle = "(alle)" if de else "(all)"
        self._alle = alle
        self.vars = {}
        felder = (("typ", "Objektart:" if de else "Object type:"),
                  ("layer", "Layer:"),
                  ("farbe", "Farbe:" if de else "Colour:"),
                  ("linientyp", "Linientyp:" if de else "Line type:"))
        for row, (key, text) in enumerate(felder):
            ttk.Label(f, text=text).grid(row=row, column=0, sticky=tk.W, pady=4)
            v = tk.StringVar(value=alle)
            self.vars[key] = v
            ttk.Combobox(f, textvariable=v, state="readonly", width=26,
                         values=[alle] + list(werte.get(key, []))).grid(
                row=row, column=1, sticky=tk.W, pady=4, padx=(8, 0))
        self.negiert = tk.BooleanVar(value=False)
        self.hinzu = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Alles AUSSER diesen Treffern auswählen" if de
                        else "Select everything EXCEPT these matches",
                        variable=self.negiert).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        ttk.Checkbutton(f, text="Zur bestehenden Auswahl hinzufügen" if de
                        else "Add to the current selection",
                        variable=self.hinzu).grid(
            row=5, column=0, columnspan=2, sticky=tk.W)
        bf = ttk.Frame(f)
        bf.grid(row=6, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_window(self)

    def _ok(self):
        krit = {k: (None if v.get() == self._alle else v.get())
                for k, v in self.vars.items()}
        self.result = {"kriterien": krit, "negiert": self.negiert.get(),
                       "hinzufuegen": self.hinzu.get()}
        self.destroy()



class BauteilkatalogDialog(tk.Toplevel):
    """Parts catalogue of the project: manufacturer, order number and
    description per TYP (used by the parts list).

    katalog:     [{"typ", "hersteller", "bestellnr", "beschreibung"}]
    vorschlaege: TYP values found in the drawing (button 'Take over types')
    result:      the new catalogue list or None"""

    SPALTEN = ("typ", "hersteller", "bestellnr", "beschreibung")

    def __init__(self, parent, katalog, vorschlaege=()):
        super().__init__(parent)
        de = SPRACHE["aktuell"] == "de"
        self.result = None
        self._vorschlaege = list(vorschlaege)
        self.title("Bauteilkatalog" if de else "Parts catalogue")
        self.transient(parent)
        _modal(self)
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=("Hersteller, Bestellnummer und Beschreibung je Typ (TYP). "
                           "Die Stückliste übernimmt die Angaben automatisch."
                           if de else
                           "Manufacturer, order number and description per type (TYP). "
                           "The parts list uses them automatically."),
                  style="Hint.TLabel", wraplength=620, justify=tk.LEFT).pack(anchor=tk.W)
        titel = {"typ": "TYP", "hersteller": "Hersteller" if de else "Manufacturer",
                 "bestellnr": "Bestellnummer" if de else "Order number",
                 "beschreibung": "Beschreibung" if de else "Description"}
        breiten = {"typ": 150, "hersteller": 150, "bestellnr": 170, "beschreibung": 260}
        self.tree = ttk.Treeview(f, columns=self.SPALTEN, show="headings",
                                 height=12, selectmode="extended")
        for c in self.SPALTEN:
            self.tree.heading(c, text=titel[c])
            self.tree.column(c, width=breiten[c], anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=8)
        self.tree.bind("<Double-1>", lambda e: self._bearbeiten())
        for e in katalog or []:
            if isinstance(e, dict):
                self._zeile_einfuegen(e)
        bf = ttk.Frame(f)
        bf.pack(fill=tk.X)
        ttk.Button(bf, text="Hinzufügen" if de else "Add",
                   command=self._hinzufuegen).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text="Bearbeiten" if de else "Edit",
                   command=self._bearbeiten).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text="Löschen" if de else "Delete",
                   command=self._loeschen).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text="Typen aus Zeichnung übernehmen" if de
                   else "Take over types from drawing",
                   command=self._uebernehmen).pack(side=tk.LEFT, padx=12)
        ok = ttk.Frame(f)
        ok.pack(pady=(10, 0))
        ttk.Button(ok, text=tr("dlg.ok"), command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(ok, text=tr("dlg.abbrechen"),
                   command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.bind("<Escape>", lambda e: self.destroy())
        _zentrieren(self, parent)
        self.wait_window(self)

    def _zeile_einfuegen(self, e):
        self.tree.insert("", tk.END,
                         values=[str(e.get(c, "") or "") for c in self.SPALTEN])

    def _alle_typen(self):
        return {str(self.tree.item(i, "values")[0]).strip().upper()
                for i in self.tree.get_children()}

    def _uebernehmen(self):
        vorhanden = self._alle_typen()
        for t in self._vorschlaege:
            if t.strip().upper() not in vorhanden:
                self._zeile_einfuegen({"typ": t})

    def _formular(self, werte):
        de = SPRACHE["aktuell"] == "de"
        dlg = tk.Toplevel(self)
        dlg.title("Bauteil" if de else "Part")
        dlg.transient(self)
        _modal(dlg)
        dlg.configure(bg=FARBEN["bg_mittel"])
        g = ttk.Frame(dlg, padding=12)
        g.pack()
        namen = {"typ": "TYP", "hersteller": "Hersteller:" if de else "Manufacturer:",
                 "bestellnr": "Bestellnummer:" if de else "Order number:",
                 "beschreibung": "Beschreibung:" if de else "Description:"}
        vars_ = {}
        for i, c in enumerate(self.SPALTEN):
            ttk.Label(g, text=namen[c]).grid(row=i, column=0, sticky=tk.W, pady=3)
            vars_[c] = tk.StringVar(value=werte.get(c, ""))
            ttk.Entry(g, textvariable=vars_[c], width=40).grid(
                row=i, column=1, pady=3, padx=(8, 0))
        erg = {}

        def ok():
            if vars_["typ"].get().strip():
                erg.update({c: v.get().strip() for c, v in vars_.items()})
                dlg.destroy()
        bf = ttk.Frame(g)
        bf.grid(row=len(self.SPALTEN), column=0, columnspan=2, pady=(10, 0))
        ttk.Button(bf, text=tr("dlg.ok"), command=ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text=tr("dlg.abbrechen"),
                   command=dlg.destroy).pack(side=tk.LEFT, padx=6)
        dlg.bind("<Return>", lambda e: ok())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.wait_window(dlg)
        return erg or None

    def _hinzufuegen(self):
        e = self._formular({})
        if e:
            self._zeile_einfuegen(e)

    def _bearbeiten(self):
        sel = self.tree.selection()
        if not sel:
            return
        v = self.tree.item(sel[0], "values")
        e = self._formular(dict(zip(self.SPALTEN, v)))
        if e:
            self.tree.item(sel[0], values=[e[c] for c in self.SPALTEN])

    def _loeschen(self):
        for i in self.tree.selection():
            self.tree.delete(i)

    def _ok(self):
        out = []
        for i in self.tree.get_children():
            v = self.tree.item(i, "values")
            e = dict(zip(self.SPALTEN, [str(x).strip() for x in v]))
            if e["typ"]:
                out.append(e)
        self.result = out
        self.destroy()
