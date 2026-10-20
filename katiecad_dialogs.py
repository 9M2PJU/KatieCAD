# -*- coding: utf-8 -*-
"""
katiecad_dialogs.py - Alle Dialog-Klassen und das Lizenz-Fenster.
Wird von CadApp genutzt; kennt CadApp, aber CadApp importiert dieses
Modul nur fuer die Dialog-Klassen.

NEU (Schritt 3): _BlockNameDialog, _BlockAuswahlDialog
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox

from katiecad_i18n import tr, SPRACHE
from katiecad_core import (
    FARBEN, ZEICHNUNGSFORMATE, LINIENTYPEN, LINIENSTAERKEN,
    SCHRIFTARTEN, MASSSTAEBE, BEM_RICHTUNGEN,
    Layer, Text, Linie, Kreis, Bogen, Rechteck, Polylinie,
    Bemassung, Viewport,
    parse_massstab, massstab_text,
)


# ============================================================
# MIT-Lizenztext (fuer das separate Lizenz-Fenster)
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
    """Zeigt die MIT-Lizenz in einem eigenen, scrollbaren Fenster."""
    win = tk.Toplevel(parent)
    win.title("License – KatieCAD")
    win.geometry("620x520")
    win.minsize(400, 300)
    win.transient(parent)
    win.configure(bg=FARBEN["bg_mittel"])

    footer = tk.Frame(win, bg=FARBEN["bg_mittel"], padx=20, pady=14)
    footer.pack(side="bottom", fill="x")

    tk.Button(footer, text=tr("dlg.schliessen"), command=win.destroy,
              bg=FARBEN["bg_hell"], fg=FARBEN["text"],
              activebackground=FARBEN["bg_hover"],
              activeforeground=FARBEN["cyan"],
              relief="raised", bd=1, font=("Helvetica", 9, "bold"),
              padx=14, pady=4, cursor="hand2").pack(side="right")

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
# Layout-Name-Dialog
# ============================================================
class _LayoutNameDialog(tk.Toplevel):
    def __init__(self, parent, titel, startname=""):
        super().__init__(parent)
        self.result = None
        self.title(titel)
        self.geometry("360x140")
        self.transient(parent)
        self.grab_set()
        self.configure(bg=FARBEN["bg_mittel"])
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=tr("layout.neu.name")).pack(anchor=tk.W)
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
        self.grab_set()
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
        self.farbe_btn = tk.Button(ff, bg=self.farbe_var.get(), width=5,
                                   command=self._farbe_waehlen, relief=tk.FLAT, bd=0)
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
            self.schrift_var = tk.StringVar(value=element.schriftart)
            ttk.Label(f, text=tr("dlg.text.schrift")).grid(row=row, column=0,
                                                            sticky=tk.W, pady=3)
            ttk.Combobox(f, textvariable=self.schrift_var, values=SCHRIFTARTEN,
                         width=20).grid(row=row, column=1, sticky=tk.W, pady=3)
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
            for k in ("x1", "y1", "x2", "y2", "mx", "my", "hoehe", "pfeil"):
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
                el.schriftart = self.schrift_var.get()
                try:
                    idx = self.einfuegepunkt_anzeige.index(
                        self.einfuegepunkt_var.get())
                    el.einfuegepunkt = self.einfuegepunkt_werte[idx]
                except (ValueError, AttributeError):
                    el.einfuegepunkt = Text.STANDARD_EINFUEGEPUNKT
            elif isinstance(el, Bemassung):
                for k in ("x1", "y1", "x2", "y2", "mx", "my", "hoehe", "pfeil"):
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
        self.grab_set()
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
# Layer-Dialoge
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
        ttk.Button(bf, text=tr("dlg.schliessen"),
                   command=self.destroy).pack(side=tk.RIGHT, padx=2)
        self.wait_window(self)

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
        self.grab_set()
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
        self.farbe_btn = tk.Button(ff, bg=self.farbe_var.get(), width=5,
                                   command=self._farbe_waehlen, relief=tk.FLAT, bd=0)
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
# Text-, Array- und Druck-Dialog
# ============================================================
class TextDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.result = None
        self.title(tr("dlg.text.titel"))
        self.geometry("500x360")
        self.transient(parent)
        self.grab_set()
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
        ttk.Combobox(f, textvariable=self.schrift_var, values=SCHRIFTARTEN,
                     width=22).grid(row=1, column=1, sticky=tk.W)

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
                       float(self.winkel_var.get()), self.schrift_var.get(),
                       self._aktueller_punkt())
        self.destroy()


class ArrayDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.result = None
        self.einh = app._einh_faktor()
        self.title(tr("dlg.reihe.titel"))
        self.geometry("380x260")
        self.transient(parent)
        self.grab_set()
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
        self.grab_set()
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
# NEU (Schritt 3): Block-Dialoge
# ============================================================
class _BlockNameDialog(tk.Toplevel):
    """Fragt nach dem Namen fuer einen neu zu erzeugenden Block.

    Attribute:
        result: der eingegebene Name (oder None bei Abbruch)

    Parameter:
        parent          Elternfenster
        bibliothek      BlockBibliothek (fuer Existenz-Pruefung)
        startname       Vorschlag (z.B. "Block1")
    """

    def __init__(self, parent, bibliothek, startname="Block1"):
        super().__init__(parent)
        self.bibliothek = bibliothek
        self.result = None
        self.title(tr("dlg.block.name.titel"))
        self.geometry("420x190")
        self.transient(parent)
        self.grab_set()
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
    """Auswahl eines Blocks aus der Bibliothek zum Einfuegen.

    Attribute:
        result: der gewaehlte Blockname (oder None bei Abbruch)
        geloescht: Liste der Namen, die der Nutzer ueber den
                   Loeschen-Button entfernt hat (CadApp persistiert das).
    """

    def __init__(self, parent, bibliothek):
        super().__init__(parent)
        self.bibliothek = bibliothek
        self.result = None
        self.geloescht = []
        self.title(tr("dlg.block.auswahl.titel"))
        self.geometry("520x460")
        self.transient(parent)
        self.grab_set()
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

        info = ttk.Label(f, text=tr("dlg.block.auswahl.hinweis"),
                         style="Hint.TLabel", wraplength=480, justify=tk.LEFT)
        info.pack(anchor=tk.W, pady=(8, 4))

        bf = ttk.Frame(f)
        bf.pack(fill=tk.X, pady=(6, 0))
        self.btn_einfuegen = ttk.Button(bf, text=tr("dlg.block.auswahl.einfuegen"),
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
