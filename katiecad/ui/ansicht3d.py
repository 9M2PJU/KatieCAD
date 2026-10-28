# -*- coding: utf-8 -*-
"""
katiecad/ui/ansicht3d.py - 3D wireframe view inside the main window (MIT).

The 3D view replaces the 2D canvas (same window, same undo, same layer /
colour / weight toolbar). The flat 2D drawing lies on the ground plane
(z = 0), 3D bodies are drawn as wireframe. Orbit with the middle mouse
button, pan with Ctrl + middle mouse button (or the right button), zoom
with the wheel. An optional view cube sets standard views. The 3D
manipulator (X/Y/Z arrows) moves the selection along one axis; the Z arrow
also pulls closed 2D shapes up or down into solids ("push/pull").
"""

import math
import re
import tkinter as tk
from tkinter import ttk, messagebox

from katiecad.common.i18n import tr
from katiecad.model.core import (FARBEN, UI_SCHRIFT, Koerper3D, Gruppe3D, Skizze3D, Bemassung3D, Text3D, Viewport,
                                 quader, zylinder, kegel, pyramide, kugel)
from katiecad.model import geom3d as G
from katiecad.model import szene3d as S
from katiecad.model import schrank as SCHR
from katiecad.ui.dialogs import _modal, _LayoutNameDialog

# basic 2D tools of the toolbar -> their 3D counterparts (drawing on the work plane / 3D dimension)
WERKZEUG_3D = {"linie": "linie", "polylinie": "poly", "kreis": "kreis", "rechteck": "rechteck",
               "bemassung": "bem", "text": "text"}

BTN_MITTE, BTN_RECHTS = ("3", "2") if __import__("sys").platform == "darwin" else ("2", "3")

ACHSEN_FARBE = {"x": "#ff4d4d", "y": "#3ddc84", "z": "#4da6ff"}
WUERFEL_MITTE = (84, 96)         # distance from the upper right corner
WUERFEL_GROESSE = 46
PARAMETER = {                    # field keys per body type
    "quader": ("breite", "tiefe", "hoehe"),
    "zylinder": ("radius", "hoehe"),
    "kegel": ("radius", "hoehe"),
    "pyramide": ("ecken", "breite", "tiefe", "hoehe"),
    "kugel": ("radius",),
}
VORGABE = {"breite": 40.0, "tiefe": 30.0, "hoehe": 20.0, "radius": 15.0, "ecken": 4}


def koerper_bauen(art, par, x, y, z):
    """Body of type `art` at the base point (x, y, z); par = values in mm."""
    if art == "quader":
        return quader(x, y, x + par["breite"], y + par["tiefe"], z, par["hoehe"])
    if art == "zylinder":
        return zylinder(x, y, par["radius"], z, par["hoehe"])
    if art == "kegel":
        return kegel(x, y, par["radius"], z, par["hoehe"])
    if art == "pyramide":
        return pyramide(x, y, z, par["hoehe"], int(par["ecken"]), par["breite"], par["tiefe"])
    if art == "kugel":
        return kugel(x, y, z + par["radius"], par["radius"])
    if art == "schrank":
        platte = (par["pb"], par["ph"]) if par.get("platte") else None
        return SCHR.schrank_bauen(par["breite"], par["hoehe"], par["tiefe"], x, y, z,
                                  platte, par.get("sockel", 0.0), bool(par.get("tuer")),
                                  bool(par.get("seite_l")), bool(par.get("seite_r")),
                                  bool(par.get("griff_links")))
    raise ValueError(art)


class SchrankDialog(tk.Toplevel):
    """Standard control cabinet: pick a size or enter free dimensions. result as in
    Koerper3DDialog = (par, (x, y, z), mit_klick) in mm."""

    def __init__(self, parent, faktor, einheit, ort):
        super().__init__(parent)
        self.result = None
        self.f = faktor
        self.title(tr("d3.neu.schrank"))
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        self.vars = {}
        r = 0
        ttk.Label(f, text=tr("d3.schrank.auswahl")).grid(row=r, column=0, sticky=tk.W, pady=3)
        frei = tr("d3.schrank.frei")
        self._namen = [frei] + [SCHR.vorgabe_name(s) for s in SCHR.SCHRAENKE]
        self.auswahl = tk.StringVar(value=self._namen[1])
        cb = ttk.Combobox(f, textvariable=self.auswahl, values=self._namen, width=26,
                          state="readonly")
        cb.grid(row=r, column=1, padx=8, pady=3)
        cb.bind("<<ComboboxSelected>>", lambda e: self._gewaehlt())
        r += 1
        felder = [("breite", tr("d3.dlg.breite"), 600), ("hoehe", tr("d3.dlg.hoehe"), 1800),
                  ("tiefe", tr("d3.dlg.tiefe"), 300), ("pb", tr("d3.schrank.pb"), 499),
                  ("ph", tr("d3.schrank.ph"), 1696),
                  ("x", tr("d3.dlg.x"), ort[0] / faktor), ("y", tr("d3.dlg.y"), ort[1] / faktor),
                  ("z", tr("d3.dlg.z"), 0.0)]
        for key, text, wert in felder:
            ttk.Label(f, text=text + f" ({einheit})").grid(row=r, column=0, sticky=tk.W, pady=3)
            v = tk.StringVar(value="%g" % wert)
            self.vars[key] = v
            ttk.Entry(f, textvariable=v, width=12).grid(row=r, column=1, sticky=tk.W, padx=8, pady=3)
            r += 1
        self.platte = tk.BooleanVar(value=True)
        self.tuer = tk.BooleanVar(value=False)
        self.seite_l = tk.BooleanVar(value=False)
        self.seite_r = tk.BooleanVar(value=False)
        for var, key in ((self.platte, "platte"), (self.tuer, "tuer"),
                         (self.seite_l, "seite_l"), (self.seite_r, "seite_r")):
            ttk.Checkbutton(f, text=tr("d3.schrank." + key), variable=var
                            ).grid(row=r, column=0, columnspan=2, sticky=tk.W, pady=2)
            r += 1
        ttk.Label(f, text=tr("d3.schrank.griff")).grid(row=r, column=0, sticky=tk.W, pady=3)
        self.griff = tk.StringVar(value=tr("d3.schrank.rechts"))
        ttk.Combobox(f, textvariable=self.griff, width=12, state="readonly",
                     values=[tr("d3.schrank.rechts"), tr("d3.schrank.links")]
                     ).grid(row=r, column=1, sticky=tk.W, padx=8, pady=3)
        r += 1
        ttk.Label(f, text=tr("d3.schrank.sockel")).grid(row=r, column=0, sticky=tk.W, pady=3)
        self.sockel = tk.StringVar(value=tr("d3.schrank.ohne"))
        ttk.Combobox(f, textvariable=self.sockel, width=12, state="readonly",
                     values=[tr("d3.schrank.ohne")] + [f"{h} mm" for h in SCHR.SOCKEL_HOEHEN[1:]]
                     ).grid(row=r, column=1, sticky=tk.W, padx=8, pady=3)
        r += 1
        self.klick = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text=tr("d3.dlg.klick"), variable=self.klick
                        ).grid(row=r, column=0, columnspan=2, sticky=tk.W, pady=6)
        r += 1
        bt = ttk.Frame(f)
        bt.grid(row=r, column=0, columnspan=2, pady=(6, 0))
        ttk.Button(bt, text="OK", command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bt, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self._gewaehlt()
        _modal(self)

    def _setze(self, key, mm):
        self.vars[key].set("%g" % round(mm / self.f, 3))

    def _gewaehlt(self):
        i = self._namen.index(self.auswahl.get())
        if i == 0:
            return                                    # free dimensions: keep the values
        h, b, t, pb, ph = SCHR.SCHRAENKE[i - 1]
        for key, v in (("breite", b), ("hoehe", h), ("tiefe", t), ("pb", pb), ("ph", ph)):
            self._setze(key, v)

    def _zahl(self, key):
        return float(self.vars[key].get().strip().replace(",", "."))

    def _ok(self):
        try:
            par = {k: self._zahl(k) * self.f for k in ("breite", "hoehe", "tiefe", "pb", "ph")}
            if min(par.values()) <= 0:
                raise ValueError
            par["platte"] = 1 if self.platte.get() else 0
            par["tuer"] = 1 if self.tuer.get() else 0
            par["griff_links"] = 1 if self.griff.get() == tr("d3.schrank.links") else 0
            par["seite_l"] = 1 if self.seite_l.get() else 0
            par["seite_r"] = 1 if self.seite_r.get() else 0
            if par["platte"] and (par["pb"] >= par["breite"] or par["ph"] >= par["hoehe"]):
                raise ValueError
            sk = self.sockel.get()
            par["sockel"] = float(sk.split()[0]) if sk[:1].isdigit() else 0.0
            pos = (self._zahl("x") * self.f, self._zahl("y") * self.f, self._zahl("z") * self.f)
        except ValueError:
            messagebox.showerror(tr("d3.titel"), tr("d3.msg.zahl"), parent=self)
            return
        self.result = (par, pos, bool(self.klick.get()))
        self.destroy()


class Koerper3DDialog(tk.Toplevel):
    """Parameters of a new 3D body. result = (par, (x, y, z), mit_klick) in mm."""

    def __init__(self, parent, art, faktor, einheit, ort):
        super().__init__(parent)
        self.result = None
        self.art, self.f = art, faktor
        self.title(tr("d3.neu." + art))
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        self.vars = {}
        zeilen = list(PARAMETER[art])
        felder = [(k, tr("d3.dlg." + k), VORGABE[k]) for k in zeilen]
        felder += [("x", tr("d3.dlg.x"), ort[0] / faktor), ("y", tr("d3.dlg.y"), ort[1] / faktor),
                   ("z", tr("d3.dlg.z"), 0.0)]
        for r, (key, text, wert) in enumerate(felder):
            ttk.Label(f, text=text + (f" ({einheit})" if key != "ecken" else "")
                      ).grid(row=r, column=0, sticky=tk.W, pady=3)
            v = tk.StringVar(value=("%g" % wert))
            self.vars[key] = v
            ttk.Entry(f, textvariable=v, width=12).grid(row=r, column=1, padx=8, pady=3)
        self.klick = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text=tr("d3.dlg.klick"), variable=self.klick
                        ).grid(row=len(felder), column=0, columnspan=2, sticky=tk.W, pady=6)
        bt = ttk.Frame(f)
        bt.grid(row=len(felder) + 1, column=0, columnspan=2, pady=(6, 0))
        ttk.Button(bt, text="OK", command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bt, text=tr("dlg.abbrechen"),
            command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        _modal(self)

    def _zahl(self, key):
        return float(self.vars[key].get().strip().replace(",", "."))

    def _ok(self):
        try:
            par = {}
            for k in PARAMETER[self.art]:
                par[k] = self._zahl(k) if k == "ecken" else self._zahl(k) * self.f
            if "ecken" in par:
                par["ecken"] = max(3, min(12, int(par["ecken"])))
            for k in ("breite", "tiefe", "hoehe", "radius"):
                if k in par and (par[k] == 0 or (k != "hoehe" and par[k] < 0)):
                    raise ValueError(k)
            pos = (self._zahl("x") * self.f, self._zahl("y") * self.f, self._zahl("z") * self.f)
        except ValueError:
            messagebox.showerror(tr("d3.titel"), tr("d3.msg.zahl"), parent=self)
            return
        self.result = (par, pos, bool(self.klick.get()))
        self.destroy()



class DrehDialog(tk.Toplevel):
    """Axis (X/Y/Z) and angle for rotating 3D objects. result = (axis, degrees)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.title(tr("d3.drehen.titel"))
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=tr("d3.drehen.achse")).grid(row=0, column=0, columnspan=3, sticky=tk.W)
        self.achse = tk.StringVar(value="z")
        for i, a in enumerate(("x", "y", "z")):
            ttk.Radiobutton(f, text=a.upper(), value=a, variable=self.achse
                            ).grid(row=1, column=i, padx=8, pady=4)
        ttk.Label(f, text=tr("d3.drehen.winkel"), wraplength=320).grid(
            row=2, column=0, columnspan=3, sticky=tk.W, pady=(8, 2))
        self.winkel = tk.StringVar(value="90")
        e = ttk.Entry(f, textvariable=self.winkel, width=12)
        e.grid(row=3, column=0, columnspan=3, sticky=tk.W)
        bt = ttk.Frame(f)
        bt.grid(row=4, column=0, columnspan=3, pady=(10, 0))
        ttk.Button(bt, text="OK", command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bt, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.bind("<Return>", lambda ev: self._ok())
        self.bind("<Escape>", lambda ev: self.destroy())
        e.focus_set()
        _modal(self)

    def _ok(self):
        try:
            w = float(self.winkel.get().strip().replace(",", "."))
        except ValueError:
            messagebox.showerror(tr("d3.titel"), tr("d3.msg.zahl"), parent=self)
            return
        self.result = (self.achse.get(), w)
        self.destroy()


class AbrundDialog(tk.Toplevel):
    """Radius + which edges to round. result = (radius, vertical, top, bottom)."""

    def __init__(self, parent, einheit):
        super().__init__(parent)
        self.result = None
        self.title(tr("d3.abrunden.titel"))
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=tr("d3.abrunden.radius") + f" ({einheit})").grid(row=0, column=0, sticky=tk.W)
        self.radius = tk.StringVar(value="5")
        e = ttk.Entry(f, textvariable=self.radius, width=10)
        e.grid(row=0, column=1, padx=8, pady=3)
        self.senkrecht = tk.BooleanVar(value=False)
        self.oben = tk.BooleanVar(value=True)
        self.unten = tk.BooleanVar(value=False)
        for r, (var, key) in enumerate(((self.oben, "oben"), (self.unten, "unten"),
                                        (self.senkrecht, "senkrecht")), start=1):
            ttk.Checkbutton(f, text=tr("d3.abrunden." + key), variable=var
                            ).grid(row=r, column=0, columnspan=2, sticky=tk.W, pady=2)
        bt = ttk.Frame(f)
        bt.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(bt, text="OK", command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bt, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.bind("<Return>", lambda ev: self._ok())
        self.bind("<Escape>", lambda ev: self.destroy())
        e.focus_set()
        _modal(self)

    def _ok(self):
        try:
            r = float(self.radius.get().strip().replace(",", "."))
            if r <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(tr("d3.titel"), tr("d3.msg.zahl"), parent=self)
            return
        if not (self.senkrecht.get() or self.oben.get() or self.unten.get()):
            return
        self.result = (r, bool(self.senkrecht.get()), bool(self.oben.get()), bool(self.unten.get()))
        self.destroy()


class MassDialog(tk.Toplevel):
    """Edit the dimensions of a body / sketch. result = {key: value} in display units."""

    def __init__(self, parent, titel, felder):
        super().__init__(parent)
        self.result = None
        self.title(titel)
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        self.vars = {}
        for r, (key, text, wert) in enumerate(felder):
            ttk.Label(f, text=text).grid(row=r, column=0, sticky=tk.W, pady=3)
            v = tk.StringVar(value="%g" % round(wert, 6))
            self.vars[key] = v
            ttk.Entry(f, textvariable=v, width=12).grid(row=r, column=1, padx=8, pady=3)
        bt = ttk.Frame(f)
        bt.grid(row=len(felder), column=0, columnspan=2, pady=(10, 0))
        ttk.Button(bt, text="OK", command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bt, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        _modal(self)

    def _ok(self):
        try:
            res = {k: float(v.get().strip().replace(",", ".")) for k, v in self.vars.items()}
            if any(x <= 0 for x in res.values()):
                raise ValueError
        except ValueError:
            messagebox.showerror(tr("d3.titel"), tr("d3.msg.zahl"), parent=self)
            return
        self.result = res
        self.destroy()


def frage_zahl(parent, titel, text, vorgabe):
    """Number prompt in the program's own dialog style; None if cancelled."""
    dlg = _LayoutNameDialog(parent, titel, vorgabe, text)
    if dlg.result is None:
        return None
    try:
        return float(dlg.result.strip().replace(",", "."))
    except ValueError:
        return None


class _Info:
    """Writes messages to the status line of the main window."""

    def __init__(self, app):
        self.app = app

    def set(self, text):
        try:
            self.app.status.set(text)
        except Exception:
            pass


def _vorzeichen(k):
    """+1 / -1 for bodies whose pull direction is world Z (or on the ground), else 0."""
    if not getattr(k, "ebene", None):
        return 1.0
    wz = G.ebene_basis(k.ebene)[2][2]
    return (1.0 if wz > 0 else -1.0) if abs(wz) > 0.9 else 0.0


class Ansicht3D(tk.Frame):
    MODI = ("flaeche", "linie", "kreis", "rechteck", "poly", "bem", "pivot", "text", "messen")
    SKIZZEN = ("linie", "kreis", "rechteck", "poly")

    def __init__(self, app):
        super().__init__(app.root, bg=FARBEN["bg_mittel"])
        self.app = app
        z = app._3d_zustand()
        self.zustand = z
        self.kamera = z["kamera"]
        self.wuerfel_var, self.persp_var, self.hoehe_var = z["wuerfel"], z["persp"], z["hoehe"]
        self.raster_var = z["raster"]
        self.breite, self.hoehe = 900, 600
        self._drag = None
        self._platz = None
        self._achse = None
        self._modus = None
        self._skiz = None             # sketch / dimension in progress
        self._messungen = []          # finished 3D distance measurements (mode "messen")
        self._maus = None
        self._hover = None
        self._manip_off = (0.0, 0.0, 0.0)          # manipulator origin relative to the centre
        self._manip_key = None
        self._spaeter_id = None
        self.wert_var = tk.StringVar()
        self.info_var = _Info(app)
        self._baue_leiste()
        self.canvas = tk.Canvas(self, bg=app.bg_modell, highlightthickness=1,
                                highlightbackground=FARBEN["rand"], cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self._binden()

    # ------------------------------------------------------------------
    # furniture
    # ------------------------------------------------------------------
    def _baue_leiste(self):
        bar = ttk.Frame(self, padding=(6, 2))
        bar.pack(side=tk.TOP, fill=tk.X)
        a, farbe = self.app, FARBEN["cyan"]
        ttk.Label(bar, text=tr("d3.titel"), style="Title.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        a._umschalt_knopf(bar, "wuerfel", farbe, self.wuerfel_var, self.zeichne)
        a._umschalt_knopf(bar, "persp", farbe, self.persp_var, self._persp)
        a._umschalt_knopf(bar, "raster3d", farbe, self.raster_var, self.zeichne)
        a._befehl_knopf(bar, "iso3d", farbe, lambda: self.ansicht("iso_so"))
        a._befehl_knopf(bar, "einpassen3d", farbe, self.einpassen)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        a._umschalt_knopf(bar, "hoehe3d", farbe, self.hoehe_var, lambda: None)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        a._befehl_knopf(bar, "flaeche3d", farbe, lambda: self.modus_setzen("flaeche"))
        a._befehl_knopf(bar, "ebene0", farbe, self.ebene_zuruecksetzen)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        a._befehl_knopf(bar, "mass3d", farbe, self.massdialog)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        a._befehl_knopf(bar, "manip_pivot", farbe, lambda: self.modus_setzen("pivot"))
        a._befehl_knopf(bar, "drehen3d", farbe, self.drehen_dialog)
        a._befehl_knopf(bar, "abrunden3d", farbe, self.abrunden_dialog)
        ttk.Label(bar, text=tr("d3.wert"), style="Title.TLabel").pack(side=tk.LEFT, padx=(10, 4))
        e = ttk.Entry(bar, textvariable=self.wert_var, width=10)
        e.pack(side=tk.LEFT)
        e.bind("<Return>", lambda ev: self.wert_anwenden())
        ttk.Label(bar, text=tr("d3.wert.hinweis"), style="Hint.TLabel").pack(side=tk.LEFT, padx=8)

    def _binden(self):
        c = self.canvas
        c.bind("<Button-1>", self.on_klick)
        c.bind("<B1-Motion>", self.on_zug)
        c.bind("<ButtonRelease-1>", self.on_los)
        c.bind("<Double-Button-1>", self.on_doppel)
        c.bind(f"<Button-{BTN_MITTE}>", lambda e: self._start_navigation(e, "mitte"))
        c.bind(f"<B{BTN_MITTE}-Motion>", self.on_navigation)
        c.bind(f"<ButtonRelease-{BTN_MITTE}>", self.on_navigation_ende)
        c.bind(f"<Double-Button-{BTN_MITTE}>", lambda e: self.einpassen())
        c.bind(f"<Button-{BTN_RECHTS}>", lambda e: self._start_navigation(e, "rechts"))
        c.bind(f"<B{BTN_RECHTS}-Motion>", self.on_navigation)
        c.bind(f"<ButtonRelease-{BTN_RECHTS}>", self.on_navigation_ende)
        c.bind("<MouseWheel>", self.on_rad)
        c.bind("<Button-4>", lambda e: self._zoom(1.12))
        c.bind("<Button-5>", lambda e: self._zoom(1 / 1.12))
        c.bind("<Motion>", self.on_bewegt)
        c.bind("<Configure>", self.on_groesse)
        c.bind("<Escape>", lambda e: self.abbrechen())
        c.bind("<Return>", lambda e: self._skizze_abschliessen())

    # ------------------------------------------------------------------
    # camera
    # ------------------------------------------------------------------
    def _mitte(self):
        return self.breite / 2.0, self.hoehe / 2.0

    def on_groesse(self, e):
        self.breite, self.hoehe = max(100, e.width), max(100, e.height)
        self.zeichne_spaeter()

    def einpassen(self, *_):
        pts = S.szene_punkte(self.app.elemente)
        if not pts:
            self.kamera.ziel = (0.0, 0.0, 0.0)
            self.kamera.skala = 2.0
        else:
            self.kamera.anpassen(pts, self.breite, self.hoehe)
        self.zeichne()

    def ansicht(self, name):
        self.kamera.ansicht_setzen(name)
        self.zeichne()

    def _persp(self):
        self.kamera.perspektive = bool(self.persp_var.get())
        self.zeichne()

    def _zoom(self, f):
        self.kamera.zoom(f)
        self.zeichne()

    def on_rad(self, e):
        self._zoom(1.12 if e.delta > 0 else 1 / 1.12)

    def _start_navigation(self, e, taste):
        ctrl = bool(e.state & 0x4)
        art = "pan" if (taste == "rechts" or ctrl) else "orbit"
        self._drag = {"art": art, "x": e.x, "y": e.y, "x0": e.x, "y0": e.y,
                      "rechts": taste == "rechts"}

    def on_navigation(self, e):
        d = self._drag
        if not d or d["art"] not in ("orbit", "pan"):
            return
        dx, dy = e.x - d["x"], e.y - d["y"]
        d["x"], d["y"] = e.x, e.y
        if d["art"] == "orbit":
            self.kamera.orbit(dx, dy)
        else:
            self.kamera.pan(dx, dy)
        self.zeichne()

    def on_navigation_ende(self, e):
        d = self._drag
        if d and d["art"] in ("orbit", "pan"):
            self._drag = None
            if d.get("rechts") and abs(e.x - d["x0"]) + abs(e.y - d["y0"]) < 4:
                self.kontextmenue(e)

    # ------------------------------------------------------------------
    # drawing (wireframe only)
    # ------------------------------------------------------------------
    def zeichne_spaeter(self):
        if self._spaeter_id is not None:
            try:
                self.after_cancel(self._spaeter_id)
            except Exception:
                pass
        self._spaeter_id = self.after(40, self.zeichne)

    def aktualisieren(self):
        """Called by the main window after changes (colour, layer, undo, ...)."""
        self.zeichne_spaeter()

    def _linie(self, p, q, farbe, breite=1, dash=None, tag="szene"):
        seg = self.kamera.proj_segment(p, q, *self._mitte())
        if seg is None:
            return
        kw = {"fill": farbe, "width": breite, "tags": tag}
        if dash:
            kw["dash"] = dash
        self.canvas.create_line(seg[0][0], seg[0][1], seg[1][0], seg[1][1], **kw)

    def _punktiert(self):
        try:
            return bool(self.app.raster_punktiert.get())
        except Exception:
            return False

    def _punkt(self, p, farbe, tag="szene"):
        q = self.kamera.proj(p, *self._mitte())
        if q is not None:
            self.canvas.create_rectangle(q[0] - 1, q[1] - 1, q[0] + 1, q[1] + 1, fill=farbe,
                                         outline=farbe, tags=tag)

    def _polylinie(self, pts, farbe, breite=1, dash=None, tag="szene", geschlossen=False):
        pts = list(pts) + ([pts[0]] if geschlossen and len(pts) > 2 else [])
        for a, b in zip(pts, pts[1:]):
            self._linie(a, b, farbe, breite, dash, tag)

    def _farbe(self, el):
        try:
            return self.app._effektive_zeichenfarbe(el)
        except Exception:
            return el.farbe

    @staticmethod
    def _breite(el):
        st = getattr(el, "staerke", None)
        if not st:
            return 1
        return max(1, min(4, int(round(st * 3))))

    def _sichtbar(self, el):
        l = self.app.layers.get(getattr(el, "layer", None))
        return not (l and not l.sichtbar)

    def _text3(self, p, text, farbe, tag="szene"):
        q = self.kamera.proj(p, *self._mitte())
        if q is not None:
            self.canvas.create_text(q[0], q[1] - 8, text=text, fill=farbe,
                                    font=(UI_SCHRIFT, 9), tags=tag)

    def zeichne(self, *_):
        self._spaeter_id = None
        c = self.canvas
        c.delete("all")
        try:
            c.configure(bg=self.app.bg_modell)
        except Exception:
            pass
        if self.raster_var.get():
            self._boden(*self._mitte())
        else:
            self._achsenkreuz()
        elemente = [e for e in self.app.elemente if self._sichtbar(e)]
        for el in elemente:
            if S.ist_3d(el):
                continue
            farbe, br = self._farbe(el), self._breite(el)
            for zug, geschlossen in S.zuege3(el):
                self._polylinie(zug, farbe, br, geschlossen=geschlossen)
            if isinstance(el, Bemassung3D):
                self._text3(el.text_pos3(), el.wert_text(), farbe)
            elif isinstance(el, Text3D):
                q = self.kamera.proj(el.p, *self._mitte())
                if q is not None:
                    px = max(6, int(round(el.hoehe * self.kamera.skala * 0.9)))
                    self.canvas.create_text(q[0], q[1], text=el.inhalt, fill=farbe, anchor="sw",
                                            font=(UI_SCHRIFT, px), tags="szene")
        if self._modus == "messen" or self._messungen:
            for (a, b, t) in self._messungen:
                self._linie(a, b, FARBEN["gelb"], 1, (4, 3), "szene")
                self._text3(G.v_mul(G.v_add(a, b), 0.5), t, FARBEN["gelb"])
        for el, nz in S.koerper_netze(elemente):
            farbe, br = self._farbe(el), self._breite(el)
            for (i, j) in nz.kanten:
                self._linie(nz.punkte[i], nz.punkte[j], farbe, br)
        self._ebene_zeichnen()
        self._auswahl_zeichnen()
        self._vorschau_zeichnen()
        if self.wuerfel_var.get():
            self._wuerfel_zeichnen()
        self._manip_zeichnen()
        self._hover_zeichnen()

    def _achsenkreuz(self):
        L = 60.0 / self.kamera.skala
        for name, a in S.ACHSEN.items():
            self._linie((0.0, 0.0, 0.0), (a[0] * L, a[1] * L, a[2] * L), ACHSEN_FARBE[name], 2,
                        None, "boden")

    def _raster_mm(self):
        try:
            return float(self.app._zahl(self.app.raster_mm, 5.0)) or 5.0
        except Exception:
            return 5.0

    def _boden(self, cx, cy):
        k = self.kamera
        schritt = self._raster_mm()
        radius = max(self.breite, self.hoehe) / k.skala / 2.0 * 1.3
        while radius / schritt > 40:
            schritt *= 2
        gx, gy = k.ziel[0], k.ziel[1]
        farbe = "#2a2140"
        i0, i1 = int(math.floor((gx - radius) / schritt)), int(math.ceil((gx + radius) / schritt))
        j0, j1 = int(math.floor((gy - radius) / schritt)), int(math.ceil((gy + radius) / schritt))
        if self._punktiert():
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self._punkt((i * schritt, j * schritt, 0.0), "#5b4a8a", "boden")
        else:
            for i in range(i0, i1 + 1):
                self._linie((i * schritt, j0 * schritt, 0.0), (i * schritt, j1 * schritt, 0.0),
                            farbe, 1, None, "boden")
            for j in range(j0, j1 + 1):
                self._linie((i0 * schritt, j * schritt, 0.0), (i1 * schritt, j * schritt, 0.0),
                            farbe, 1, None, "boden")
        self._achsenkreuz()

    def _ebene_zeichnen(self):
        """Active work plane (a picked face): outline, local axes and grid."""
        pl = self.zustand.get("plane")
        if not pl:
            return
        e, pts = pl["ebene"], pl["pts"]
        gelb = FARBEN["gelb"]
        self._polylinie(pts, gelb, 2, None, "ebene", True)
        lok = [G.ebene_lokal(e, p) for p in pts]
        xs = [p[0] for p in lok]; ys = [p[1] for p in lok]
        if self.raster_var.get():
            r = self._raster_mm()
            while (max(xs) - min(xs)) / r > 40 or (max(ys) - min(ys)) / r > 40:
                r *= 2
            i0, i1 = int(math.floor(min(xs) / r)), int(math.ceil(max(xs) / r))
            j0, j1 = int(math.floor(min(ys) / r)), int(math.ceil(max(ys) / r))
            if self._punktiert():
                for i in range(i0, i1 + 1):
                    for j in range(j0, j1 + 1):
                        self._punkt(G.ebene_punkt(e, i * r, j * r), "#a8923a", "ebene")
            else:
                for i in range(i0, i1 + 1):
                    self._linie(G.ebene_punkt(e, i * r, j0 * r), G.ebene_punkt(e, i * r, j1 * r),
                                "#6b5a1f", 1, (2, 3), "ebene")
                for j in range(j0, j1 + 1):
                    self._linie(G.ebene_punkt(e, i0 * r, j * r), G.ebene_punkt(e, i1 * r, j * r),
                                "#6b5a1f", 1, (2, 3), "ebene")
        L = 14.0 / self.kamera.skala
        o = tuple(e[:3])
        self._linie(o, G.ebene_punkt(e, L, 0), ACHSEN_FARBE["x"], 2, None, "ebene")
        self._linie(o, G.ebene_punkt(e, 0, L), ACHSEN_FARBE["y"], 2, None, "ebene")

    def _auswahl_zeichnen(self):
        farbe = FARBEN["cyan"]
        for el in self.app.auswahl:
            if S.ist_3d(el):
                for nz in el.netze():
                    for (i, j) in nz.kanten:
                        self._linie(nz.punkte[i], nz.punkte[j], farbe, 3, None, "auswahl")
            else:
                for zug, geschlossen in S.zuege3(el):
                    self._polylinie(zug, farbe, 3, None, "auswahl", geschlossen)

    # ---- view cube ------------------------------------------------------
    def _wuerfel_mitte(self):
        return self.breite - WUERFEL_MITTE[0], WUERFEL_MITTE[1]

    def _pfeile(self):
        """Rotation arrows around the cube: key -> triangle points."""
        mx, my = self._wuerfel_mitte()
        R, a = WUERFEL_GROESSE * 1.0 + 20, 8
        return {
            "rechts": [(mx + R + a, my), (mx + R - a, my - a), (mx + R - a, my + a)],
            "links": [(mx - R - a, my), (mx - R + a, my - a), (mx - R + a, my + a)],
            "oben": [(mx, my - R - a), (mx - a, my - R + a), (mx + a, my - R + a)],
            "unten": [(mx, my + R + a), (mx - a, my + R - a), (mx + a, my + R - a)],
        }

    def _wuerfel_zeichnen(self):
        mx, my = self._wuerfel_mitte()
        c = self.canvas
        for name, pts, mitte, q in G.wuerfel_zeichnung(self.kamera, mx, my, WUERFEL_GROESSE):
            flat = [v for p in pts for v in p]
            c.create_polygon(*flat, fill=FARBEN["bg_hell"], outline=FARBEN["cyan"], width=1,
                             tags="wuerfel")
            if q > 0.35:
                c.create_text(mitte[0], mitte[1], text=tr("d3.ansicht." + name),
                              fill=FARBEN["cyan"], font=(UI_SCHRIFT, 8, "bold"), tags="wuerfel")
        for key, pts in self._pfeile().items():
            flat = [v for p in pts for v in p]
            c.create_polygon(*flat, fill=FARBEN["cyan"], outline=FARBEN["cyan"], tags="wuerfel")

    def _pfeil_treffer(self, x, y):
        for key, pts in self._pfeile().items():
            if G.punkt_in_polygon(x, y, pts) or math.hypot(
                    x - sum(p[0] for p in pts) / 3, y - sum(p[1] for p in pts) / 3) < 11:
                return key
        return None

    def _pfeil_ausfuehren(self, key):
        k = self.kamera
        if key == "rechts":
            k.yaw = (round(k.yaw / 90.0) * 90.0 + 90.0) % 360.0
        elif key == "links":
            k.yaw = (round(k.yaw / 90.0) * 90.0 - 90.0) % 360.0
        elif key == "oben":
            k.pitch = min(90.0, k.pitch + 45.0)
        elif key == "unten":
            k.pitch = max(-90.0, k.pitch - 45.0)
        self.zeichne()

    # ---- manipulator ------------------------------------------------------
    def _manip_infos(self):
        if not self.app.auswahl:
            return {}
        z = self._manip_zentrum3()
        if z is None:
            return {}
        return S.achsen_info(self.kamera, z, *self._mitte())

    def _manip_zentrum3(self):
        """Manipulator origin: centre of the selection plus the user's offset (if any)."""
        z = S.auswahl_zentrum3(self.app.auswahl)
        if z is None:
            return None
        key = tuple(id(x) for x in self.app.auswahl)
        if key != self._manip_key:
            self._manip_key = key
            self._manip_off = (0.0, 0.0, 0.0)
        o = self._manip_off
        return (z[0] + o[0], z[1] + o[1], z[2] + o[2])

    def pivot_zuruecksetzen(self):
        self._manip_off = (0.0, 0.0, 0.0)
        self.info_var.set(tr("d3.msg.pivot_zentriert"))
        self.zeichne()

    def _manip_zeichnen(self):
        c = self.canvas
        infos = self._manip_infos()
        for name, i in infos.items():
            farbe = ACHSEN_FARBE[name]
            breit = 4 if name == self._achse else 2
            c.create_line(i["von"][0], i["von"][1], i["bis"][0], i["bis"][1], fill=farbe,
                          width=breit, tags="manip")
            ux, uy = i["dir"]
            bx, by = i["bis"]
            c.create_polygon(bx, by, bx - ux * 12 - uy * 5, by - uy * 12 + ux * 5,
                             bx - ux * 12 + uy * 5, by - uy * 12 - ux * 5, fill=farbe,
                             outline=farbe, tags="manip")
            c.create_text(bx + ux * 12, by + uy * 12, text=name.upper(), fill=farbe,
                          font=(UI_SCHRIFT, 9, "bold"), tags="manip")
        if infos:
            p = next(iter(infos.values()))["von"]
            hx, hy = p[0] + 18, p[1] + 18                  # pivot handle: click, then click the new origin
            c.create_oval(hx - 6, hy - 6, hx + 6, hy + 6, outline=FARBEN["orange"], width=2, tags="manip")
            c.create_line(hx - 3, hy, hx + 3, hy, fill=FARBEN["orange"], tags="manip")
            c.create_line(hx, hy - 3, hx, hy + 3, fill=FARBEN["orange"], tags="manip")
            c.create_rectangle(p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5, fill=FARBEN["gelb"],
                               outline=FARBEN["bg_dunkel"], tags="manip")

    # ------------------------------------------------------------------
    # modes: face, sketch, dimension
    # ------------------------------------------------------------------
    def _ebene(self):
        pl = self.zustand.get("plane")
        return pl["ebene"] if pl else G.BODEN_EBENE

    def modus_setzen(self, modus):
        if modus != "messen":
            self._messungen = []
        self._skiz = None
        self._platz = None
        self._modus = modus
        self.canvas.configure(cursor="tcross")
        self.info_var.set(tr("d3.modus." + modus))
        self.zeichne()

    def ebene_zuruecksetzen(self):
        self.zustand["plane"] = None
        self.zustand["auto"] = False
        self.info_var.set(tr("d3.msg.ebene_boden"))
        self.zeichne()

    def _modus_ende(self):
        self._messungen = []
        self._modus = None
        self._skiz = None
        self.canvas.configure(cursor="crosshair")
        try:                                  # the basic tool of the toolbar falls back to "Selection"
            if self.app.aktives_werkzeug.get() in WERKZEUG_3D:
                self.app.aktives_werkzeug.set("auswahl")
        except Exception:
            pass

    def _raster_fang(self):
        try:
            if self.app.grid_snap.get():
                return float(self.app._zahl(self.app.fang_mm, 5.0)) or None
        except Exception:
            pass
        return None

    def _sichtbare(self):
        return [x for x in self.app.elemente if self._sichtbar(x)]

    def _flaeche_unter(self, e):
        """Face of a body under the mouse -> (ebene, pts) or None."""
        r = S.flaeche_pick(self._sichtbare(), self.kamera, *self._mitte(), e.x, e.y)
        return (r[1], r[2]) if r else None

    def _fang_ebene(self, e, ebene):
        """Snap in the plane `ebene` -> ((x, y), kind, 3D point) or None."""
        mx, my = self._mitte()

        def in_ebene(p):
            return abs(G.ebene_lokal(ebene, p)[2]) < 1e-3

        fp = (S.fang_suche(self._sichtbare(), self.kamera, mx, my, e.x, e.y, 12.0, in_ebene)
              if self.app.osnap.get() else None)             # F3 / "OFANG" also applies in 3D
        if fp is not None:
            l = G.ebene_lokal(ebene, fp[0])
            return (l[0], l[1]), fp[1], fp[0]
        p = S.punkt_auf_ebene(self.kamera, mx, my, e.x, e.y, ebene, self._raster_fang())
        if p is None:
            return None
        return p, "raster", G.ebene_punkt(ebene, p[0], p[1])

    def _fang_raum(self, e):
        """(3D point, kind) for dimensions: object snap anywhere, else the face under the
        mouse, else the work plane."""
        mx, my = self._mitte()
        fp = S.fang_suche(self._sichtbare(), self.kamera, mx, my, e.x, e.y) \
            if self.app.osnap.get() else None
        if fp is not None:
            return fp
        fl = self._flaeche_unter(e) if self.zustand.get("auto", True) else None
        ebene = fl[0] if fl else self._ebene()
        r = self._fang_ebene(e, ebene)
        return (r[2], r[1]) if r else None

    def _lokal_punkt(self, e, ebene=None):
        """Local point on the work plane under the mouse (object snap, then grid).
        With ORTHO (F8) lines/polylines are restricted to the local X or Y direction."""
        r = self._fang_ebene(e, ebene or self._ebene())
        p = r[0] if r else None
        sk = self._skiz
        if (p is not None and sk and self.app.ortho.get() and sk.get("pts")
                and sk["form"] in ("linie", "poly")):
            q = sk["pts"][-1]
            if abs(p[0] - q[0]) >= abs(p[1] - q[1]):
                p = (p[0], q[1])
            else:
                p = (q[0], p[1])
        return p

    def _raum_punkt(self, e):
        r = self._fang_raum(e)
        p = r[0] if r else None
        sk = self._skiz
        if (p is not None and sk and self.app.ortho.get() and len(sk.get("pts", ())) == 1
                and sk["form"] in ("bem", "messen")):
            # ORTHO: only along the dominant coordinate axis from the first point
            q = sk["pts"][0]
            d = G.v_sub(p, q)
            i = max(range(3), key=lambda k: abs(d[k]))
            p = tuple(q[k] + (d[k] if k == i else 0.0) for k in range(3))
        return p

    def _hover_berechnen(self):
        """Face highlight + snap marker under the mouse (drawing modes only)."""
        e, m = self._maus, self._modus
        self._hover = None
        if e is None or m not in self.MODI:
            return
        h = {"fang": None, "flaeche": None}
        erste = self._skiz is None
        if m in ("bem", "pivot", "text", "messen"):
            h["fang"] = self._fang_raum(e)
            fl = self._flaeche_unter(e) if self.zustand.get("auto", True) else None
            h["flaeche"] = fl[1] if fl else None
        elif m == "flaeche":
            fl = self._flaeche_unter(e)
            h["flaeche"] = fl[1] if fl else None
        else:
            ebene = self._ebene()
            if erste and self.zustand.get("auto", True):
                fl = self._flaeche_unter(e)
                if fl:
                    ebene = fl[0]
                    h["flaeche"] = fl[1]
            r = self._fang_ebene(e, ebene)
            if r:
                h["fang"] = (r[2], r[1])
        self._hover = h

    @staticmethod
    def _ecken_von(elemente):
        """The 8 corners of the bounding box of each object (fixture points of a block)."""
        out = []
        for el in elemente:
            b = None
            if isinstance(el, Gruppe3D):          # block: ignore thin parts (door, handle, plate)
                bs = [t.bbox3() for t in el.teile if t.bbox3()]
                dick = [q for q in bs if min(q[3] - q[0], q[4] - q[1], q[5] - q[2]) >= 20.0]
                bs = dick or bs
                if bs:
                    b = (min(q[0] for q in bs), min(q[1] for q in bs), min(q[2] for q in bs),
                         max(q[3] for q in bs), max(q[4] for q in bs), max(q[5] for q in bs))
            elif hasattr(el, "bbox3"):
                b = el.bbox3()
            if not b:
                continue
            for x in (b[0], b[3]):
                for y in (b[1], b[4]):
                    for z in (b[2], b[5]):
                        out.append((x, y, z))
        return out

    def _fang_marke(self, punkte):
        """Yellow snap marker(s) [(3D point, kind)] on the preview layer."""
        c = self.canvas
        for p, art in punkte:
            q = self.kamera.proj(p, *self._mitte())
            if q is None:
                continue
            x, y = q[0], q[1]
            f = FARBEN["gelb"]
            c.create_rectangle(x - 6, y - 6, x + 6, y + 6, outline=f, width=2, tags="vorschau")
            c.create_text(x + 10, y - 12, text=tr("d3.fang." + art), fill=f, anchor="w",
                          font=(UI_SCHRIFT, 8), tags="vorschau")

    def _achse_fang(self, d, mm):
        """OSNAP while moving along an axis: a corner/edge/centre of the selection snaps to the
        coordinate of a snap point of another object. -> (mm, [(point, kind)])"""
        if not self.app.osnap.get():
            return mm, []
        i = "xyz".index(d["achse"])
        auswahl = [x for x in self.app.auswahl if S.ist_raum(x)]
        if not auswahl:
            return mm, []
        rest = [x for x in self._sichtbare() if x not in self.app.auswahl]
        eigene = [(c, "end") for c in self._ecken_von([x for x in auswahl if S.ist_3d(x)])]
        andere = S.fang_kandidaten(rest)
        tol = 12.0 / max(self.kamera.skala, 1e-6)
        best, bd = None, tol
        for q, _a in eigene:
            q0 = q[i] - d.get("angewandt", 0.0)
            for pt, art in andere:
                cand = pt[i] - q0
                dd = abs(cand - mm)
                if dd < bd - 1e-9:
                    best, bd = (cand, pt, art), dd
        if best is None:
            return mm, []
        return best[0], [(best[1], best[2])]

    def _hover_zeichnen(self):
        c = self.canvas
        c.delete("hover")
        self._hover_berechnen()
        h = self._hover
        if not h:
            return
        if h["flaeche"]:
            self._polylinie(h["flaeche"], FARBEN["cyan"], 3, None, "hover", True)
        if h["fang"]:
            p, art = h["fang"]
            q = self.kamera.proj(p, *self._mitte())
            if q is None:
                return
            x, y = q[0], q[1]
            f = FARBEN["gelb"]
            if art == "end":
                c.create_rectangle(x - 5, y - 5, x + 5, y + 5, outline=f, width=2, tags="hover")
            elif art == "mitte":
                c.create_polygon(x, y - 6, x - 6, y + 5, x + 6, y + 5, outline=f, fill="",
                                 width=2, tags="hover")
            elif art == "zentrum":
                c.create_oval(x - 6, y - 6, x + 6, y + 6, outline=f, width=2, tags="hover")
                c.create_line(x - 9, y, x + 9, y, fill=f, tags="hover")
                c.create_line(x, y - 9, x, y + 9, fill=f, tags="hover")
            else:
                f = FARBEN["cyan"]
                c.create_line(x - 5, y, x + 5, y, fill=f, width=2, tags="hover")
                c.create_line(x, y - 5, x, y + 5, fill=f, width=2, tags="hover")
            c.create_text(x + 10, y - 12, text=tr("d3.fang." + art), fill=f, anchor="w",
                          font=(UI_SCHRIFT, 8), tags="hover")

    def _stil(self):
        try:
            kw = self.app._layer_daten()
            kw["staerke"] = None
            kw["eig_farbe"] = True
            return kw
        except Exception:
            return {}

    def _modus_klick(self, e):
        m = self._modus
        if m == "flaeche":
            r = S.flaeche_pick([x for x in self.app.elemente if self._sichtbar(x)], self.kamera,
                               *self._mitte(), e.x, e.y)
            if r is None:
                self.info_var.set(tr("d3.msg.keine_flaeche"))
                return
            _k, ebene, pts = r
            self.zustand["plane"] = {"ebene": ebene, "pts": pts}
            self.zustand["auto"] = True
            self._modus_ende()
            self.info_var.set(tr("d3.msg.ebene_gesetzt"))
            self.zeichne()
        elif m in self.SKIZZEN:
            sk = self._skiz
            if sk is None and self.zustand.get("auto", True):
                fl = self._flaeche_unter(e)           # draw directly on the face under the mouse
                if fl:
                    self.zustand["plane"] = {"ebene": fl[0], "pts": fl[1]}
            p = self._lokal_punkt(e)
            if p is None:
                self.info_var.set(tr("d3.msg.keine_ebene"))
                return
            if sk is None:
                self._skiz = {"form": m, "pts": [p], "maus": p}
                self.info_var.set(tr("d3.msg.skizze_" + m))
            elif m == "kreis":
                r = math.hypot(p[0] - sk["pts"][0][0], p[1] - sk["pts"][0][1])
                if r > 1e-6:
                    self._skizze_fertig("kreis", [sk["pts"][0][0], sk["pts"][0][1], r])
            elif m in ("rechteck", "linie"):
                q = sk["pts"][0]
                if m == "linie" and math.hypot(p[0] - q[0], p[1] - q[1]) > 1e-6:
                    self._skizze_fertig("linie", [q[0], q[1], p[0], p[1]])
                elif m == "rechteck" and abs(p[0] - q[0]) > 1e-6 and abs(p[1] - q[1]) > 1e-6:
                    self._skizze_fertig("rechteck", [q[0], q[1], p[0], p[1]])
            else:
                sk["pts"].append(p)
            self.zeichne()
        elif m == "pivot":
            p = self._raum_punkt(e)
            z = S.auswahl_zentrum3(self.app.auswahl)
            if p is None or z is None:
                self.info_var.set(tr("d3.msg.nichts_drehbar") if z is None else tr("d3.msg.keine_ebene"))
                return
            self._manip_key = tuple(id(x) for x in self.app.auswahl)
            self._manip_off = (p[0] - z[0], p[1] - z[1], p[2] - z[2])
            self._modus_ende()
            self.info_var.set(tr("d3.msg.pivot_ok"))
            self.zeichne()
        elif m == "text":
            p = self._raum_punkt(e)
            if p is None:
                self.info_var.set(tr("d3.msg.keine_ebene"))
                return
            self._text_setzen(p)
        elif m == "messen":
            p = self._raum_punkt(e)
            if p is None:
                self.info_var.set(tr("d3.msg.keine_ebene"))
                return
            sk = self._skiz
            if sk is None:
                self._skiz = {"form": "messen", "pts": [p]}
                self.info_var.set(tr("d3.msg.mess_p2"))
            elif G.v_len(G.v_sub(p, sk["pts"][0])) > 1e-9:
                self._mess_fertig(sk["pts"][0], p)
        elif m == "bem":
            p = self._raum_punkt(e)
            if p is None:
                self.info_var.set(tr("d3.msg.keine_ebene"))
                return
            sk = self._skiz
            if sk is None:
                self._skiz = {"form": "bem", "pts": [p]}
                self.info_var.set(tr("d3.msg.bem_p2"))
            elif len(sk["pts"]) == 1:
                if G.v_len(G.v_sub(p, sk["pts"][0])) > 1e-6:
                    sk["pts"].append(p)
                    self.info_var.set(tr("d3.msg.bem_pos"))
            else:
                self._bem_fertig(self._bem_versatz(e, sk["pts"]))
            self.zeichne()

    def _text_setzen(self, p):
        from tkinter import simpledialog
        t = simpledialog.askstring(tr("d3.text.titel"), tr("d3.text.frage"), parent=self.app.root)
        if not t or not t.strip():
            return
        self.app._snapshot()
        try:
            h = float(self.app._zahl(getattr(self.app, "text_hoehe", None), 3.5)) or 3.5
        except Exception:
            h = 3.5
        el = Text3D(p, t, h, **self._stil())
        self.app.elemente.append(el)
        self.app.auswahl = [el]
        self.app.redraw()
        self.info_var.set(tr("d3.msg.text_fertig"))

    def text_bearbeiten(self, el):
        from tkinter import simpledialog
        t = simpledialog.askstring(tr("d3.text.titel"), tr("d3.text.frage"), parent=self.app.root,
                                   initialvalue=el.inhalt)
        if t is not None and t.strip():
            self.app._snapshot()
            el.inhalt = t
            self.app.redraw()

    def _mess_text3(self, p1, p2):
        f = self.app._einh_faktor()
        d = G.v_sub(p2, p1)
        def z(v):
            t = f"{abs(v) / f:.3f}"
            return t.replace(".", ",") if self.app.dezimalkomma.get() else t
        return (z(G.v_len(d)), z(d[0]), z(d[1]), z(d[2]))

    def _mess_fertig(self, p1, p2):
        a, dx, dy, dz = self._mess_text3(p1, p2)
        self._messungen.append((p1, p2, a))
        self._skiz = None
        self.info_var.set(tr("d3.msg.mess_ok", a=a, dx=dx, dy=dy, dz=dz,
                             einheit=self.app.einheit.get()))
        try:
            self.app.status.set(self.info_var.get())
        except Exception:
            pass
        self.zeichne()

    def _bem_versatz(self, e, pts):
        """Offset vector of a dimension: mouse point in the plane through p1 that faces the camera."""
        p1, p2 = pts[0], pts[1]
        o, d = self.kamera.strahl(e.x, e.y, *self._mitte())
        f = self.kamera.basis()[2]
        nenner = G.v_dot(d, f)
        if abs(nenner) < 1e-9:
            return (0.0, 0.0, 0.0)
        t = G.v_dot(G.v_sub(p1, o), f) / nenner
        q = G.v_add(o, G.v_mul(d, t))
        off = G.v_sub(q, p1)
        ax = G.v_norm(G.v_sub(p2, p1))
        off = G.v_sub(off, G.v_mul(ax, G.v_dot(off, ax)))
        return off

    def _bem_fertig(self, versatz):
        p1, p2 = self._skiz["pts"][0], self._skiz["pts"][1]
        self.app._snapshot()
        b = Bemassung3D(p1, p2, versatz, faktor=self.app._einh_faktor(), **self._stil())
        self.app.elemente.append(b)
        self.app.auswahl = [b]
        self._skiz = None
        self.app.redraw()
        self.info_var.set(tr("d3.msg.bem_fertig", wert=b.wert_text(), einheit=self.app.einheit.get()))

    def _skizze_fertig(self, form, daten):
        self.app._snapshot()
        sk = Skizze3D({"poly": "polylinie"}.get(form, form), self._ebene(), daten, **self._stil())
        self.app.elemente.append(sk)
        self.app.auswahl = [sk]
        self._skiz = None
        self.app.redraw()
        self.info_var.set(tr("d3.msg.skizze_fertig"))

    def _skizze_abschliessen(self):
        """Enter: closes a polyline sketch."""
        sk = self._skiz
        if sk and sk["form"] == "poly" and len(sk["pts"]) >= 3:
            self._skizze_fertig("poly", [list(p) for p in sk["pts"]])
            self.zeichne()
        elif sk is None and self.wert_var.get().strip():
            self.wert_anwenden()

    def _vorschau_zeichnen(self):
        sk, m = self._skiz, self._modus
        gelb = FARBEN["gelb"]
        if self._platz is not None and self._platz.get("maus"):
            pl = self._platz
            p, fang = self._platz_pos(pl["maus"], pl)
            if p is not None:
                self._fang_marke(fang)
                body = koerper_bauen(pl["art"], pl["par"], p[0], p[1], p[2])
                for nz in (body.netze() if hasattr(body, "netze") else [body.netz()]):
                    for (i, j) in nz.kanten:
                        self._linie(nz.punkte[i], nz.punkte[j], gelb, 1, (4, 3), "vorschau")
        if not sk or not self._maus:
            return
        if sk["form"] == "messen":
            q = self._raum_punkt(self._maus)
            if q:
                self._linie(sk["pts"][0], q, gelb, 1, (4, 3), "vorschau")
                self._text3(G.v_mul(G.v_add(sk["pts"][0], q), 0.5),
                            self._mess_text3(sk["pts"][0], q)[0], gelb, "vorschau")
            return
        if sk["form"] == "bem":
            pts = sk["pts"]
            if len(pts) == 1:
                q = self._raum_punkt(self._maus)
                if q:
                    self._linie(pts[0], q, gelb, 1, (4, 3), "vorschau")
            elif len(pts) == 2:
                v = self._bem_versatz(self._maus, pts)
                b = Bemassung3D(pts[0], pts[1], v, faktor=self.app._einh_faktor())
                for zug in b.zuege3():
                    self._polylinie(zug, gelb, 1, (4, 3), "vorschau")
                self._text3(b.text_pos3(), b.wert_text(), gelb, "vorschau")
            return
        p = self._lokal_punkt(self._maus)
        if p is None:
            return
        e = self._ebene()
        q0 = sk["pts"][0]
        if sk["form"] == "kreis":
            r = math.hypot(p[0] - q0[0], p[1] - q0[1])
            prof = G.kreis_profil(q0[0], q0[1], r, 32)
            self._polylinie([G.ebene_punkt(e, x, y) for x, y in prof], gelb, 1, (4, 3), "vorschau", True)
        elif sk["form"] == "linie":
            self._linie(G.ebene_punkt(e, q0[0], q0[1]), G.ebene_punkt(e, p[0], p[1]), gelb, 1,
                        (4, 3), "vorschau")
        elif sk["form"] == "rechteck":
            prof = G.rechteck_profil(q0[0], q0[1], p[0], p[1])
            self._polylinie([G.ebene_punkt(e, x, y) for x, y in prof], gelb, 1, (4, 3), "vorschau", True)
        else:
            pts = [G.ebene_punkt(e, x, y) for x, y in sk["pts"] + [p]]
            self._polylinie(pts, gelb, 1, (4, 3), "vorschau")

    # ------------------------------------------------------------------
    # mouse: selection, cube, manipulator
    # ------------------------------------------------------------------
    def _bodenpunkt(self, e, z=0.0):
        p = self.kamera.auf_ebene(e.x, e.y, *self._mitte(), z)
        if p is None:
            return None
        r = self._raster_fang()
        if r:
            p = (round(p[0] / r) * r, round(p[1] / r) * r, p[2])
        return p

    def on_klick(self, e):
        self.canvas.focus_set()
        if self._platz is not None:
            self._platz_klick(e)
            return
        if self.wuerfel_var.get():
            mx, my = self._wuerfel_mitte()
            pf = self._pfeil_treffer(e.x, e.y)
            name = G.wuerfel_treffer(self.kamera, mx, my, WUERFEL_GROESSE, e.x, e.y)
            if pf or name or math.hypot(e.x - mx, e.y - my) <= WUERFEL_GROESSE * 1.3:
                self._drag = {"art": "wuerfel", "x": e.x, "y": e.y, "bewegt": False,
                              "name": name, "pfeil": pf}
                return
        if self._modus:
            self._modus_klick(e)
            return
        infos = self._manip_infos()
        if infos:
            o = next(iter(infos.values()))["von"]
            if abs(e.x - (o[0] + 18)) <= 8 and abs(e.y - (o[1] + 18)) <= 8:
                self.modus_setzen("pivot")
                return
        achse = S.manip_treffer(infos, e.x, e.y)
        if achse:
            self._drag = {"art": "manip", "achse": achse, "x": e.x, "y": e.y, "info": infos[achse],
                          "mm": 0.0, "bewegt": False}
            self._achse = achse
            return
        el = S.pick([x for x in self.app.elemente if self._sichtbar(x)], self.kamera,
                    *self._mitte(), e.x, e.y)
        if el is None:
            # empty space: drag = selection window (like 2D), plain click = deselect
            self._drag = {"art": "rahmen", "x": e.x, "y": e.y, "bewegt": False,
                          "add": bool(e.state & 0x5)}
            return
        elif bool(e.state & 0x5):                 # Shift / Ctrl: toggle
            if el in self.app.auswahl:
                self.app.auswahl.remove(el)
            else:
                self.app.auswahl.append(el)
        else:
            self.app.auswahl = [el]
        self._achse = None
        self.app.redraw()
        self.zeichne()

    def on_doppel(self, e):
        if self._modus or self._platz is not None:
            # Tk reports a fast second click as <Double-Button-1> and would not call
            # on_klick: in drawing modes it must still count as an ordinary click.
            self.on_klick(e)
            return
        el = S.pick([x for x in self.app.elemente if self._sichtbar(x)], self.kamera,
                    *self._mitte(), e.x, e.y)
        if el is None:
            return
        self.app.auswahl = [el]
        if isinstance(el, Text3D):
            self.text_bearbeiten(el)
            return
        if S.parameter(el):
            self.massdialog()
        else:
            self.app._element_bearbeiten(el)
            self.app.redraw()
            self.zeichne()

    def on_zug(self, e):
        d = self._drag
        if not d:
            return
        if d["art"] == "wuerfel":
            if not d["bewegt"] and abs(e.x - d["x"]) + abs(e.y - d["y"]) < 4:
                return
            d["bewegt"] = True
            self.kamera.orbit(e.x - d["x"], e.y - d["y"])
            d["x"], d["y"] = e.x, e.y
            self.zeichne()
        elif d["art"] == "rahmen":
            if abs(e.x - d["x"]) + abs(e.y - d["y"]) < 4 and not d["bewegt"]:
                return
            d["bewegt"] = True
            self._rahmen_zeichnen(d, e)
        elif d["art"] == "manip":
            if abs(e.x - d["x"]) + abs(e.y - d["y"]) < 3 and not d["bewegt"]:
                return
            if not d["bewegt"]:
                d["bewegt"] = True
                self._manip_beginn(d)
            mm = S.verschiebung_mm(d["info"], e.x - d["x"], e.y - d["y"], self._raster_fang())
            self._achsfang = []
            if d.get("modus") == "verschieben":
                mm, self._achsfang = self._achse_fang(d, mm)
            self._manip_setzen(d, mm)
            self.zeichne()
            self._fang_marke(self._achsfang)

    def _rahmen_zeichnen(self, d, e):
        """Selection window: cyan (left to right) = fully inside, green = touching."""
        c = self.canvas
        c.delete("rahmen")
        kreuz = e.x < d["x"]
        farbe = FARBEN["gruen"] if kreuz else FARBEN["cyan"]
        c.create_rectangle(d["x"], d["y"], e.x, e.y, outline=farbe, width=2, dash=(5, 3),
                           tags="rahmen")
        r = (min(d["x"], e.x), min(d["y"], e.y), max(d["x"], e.x), max(d["y"], e.y))
        for el in S.auswahl_im_rahmen([x for x in self.app.elemente if self._sichtbar(x)],
                                      self.kamera, *self._mitte(), r, kreuz):
            for nz in (el.netze() if S.ist_3d(el) else []):
                for (i, j) in nz.kanten:
                    self._linie(nz.punkte[i], nz.punkte[j], FARBEN["magenta"], 2, None, "rahmen")
            for zug, geschl in ([] if S.ist_3d(el) else S.zuege3(el)):
                self._polylinie(zug, FARBEN["magenta"], 2, None, "rahmen", geschl)

    def on_los(self, e):
        d, self._drag = self._drag, None
        self._achsfang = []
        if not d:
            return
        if d["art"] == "rahmen":
            self.canvas.delete("rahmen")
            if not d["bewegt"]:
                if not d["add"]:
                    self.app.auswahl = []
            else:
                r = (min(d["x"], e.x), min(d["y"], e.y), max(d["x"], e.x), max(d["y"], e.y))
                treffer = S.auswahl_im_rahmen([x for x in self.app.elemente if self._sichtbar(x)],
                                              self.kamera, *self._mitte(), r, e.x < d["x"])
                neu = list(self.app.auswahl) if d["add"] else []
                for t in treffer:
                    if t not in neu:
                        neu.append(t)
                self.app.auswahl = neu
                self.info_var.set(tr("d3.msg.markiert", n=len(neu)))
            self._achse = None
            self.app.redraw()
            self.zeichne()
            return
        if d["art"] == "wuerfel":
            if not d["bewegt"]:
                if d["pfeil"]:
                    self._pfeil_ausfuehren(d["pfeil"])
                elif d["name"]:
                    self.ansicht(d["name"])
        elif d["art"] == "manip":
            if d["bewegt"]:
                if d.get("modus") == "extrudieren":
                    self._extrusion_abschliessen(d["ziel"])
                self.app.redraw()
                self.zeichne()
                self.info_var.set(tr("d3.msg.verschoben", achse=d["achse"].upper(),
                                     wert=f"{d['mm'] / self.app._einh_faktor():.2f}",
                                     einheit=self.app.einheit.get()))
            else:
                self.zeichne()
                self.info_var.set(tr("d3.msg.achse", achse=d["achse"].upper()))
                self.wert_var.set("")

    def on_bewegt(self, e):
        self._maus = e
        if self._platz is not None:
            self._platz["maus"] = e
            self.zeichne()
        elif self._skiz is not None:
            self.zeichne()
        elif self._modus in self.MODI:
            self._hover_zeichnen()

    def _extrusion_abschliessen(self, koerper):
        """Bodies pulled downwards into the body below become pockets."""
        gefallen = [k for k in koerper if S.extrusion_abschliessen(self.app.elemente, k)]
        if gefallen:
            self.app.auswahl = [x for x in self.app.auswahl if x not in gefallen]
            self.info_var.set(tr("d3.msg.tasche"))

    # ---- manipulator actions ---------------------------------------------
    def _extrudierbare(self):
        out = []
        for x in self.app.auswahl:
            if not S.extrudierbar(x):
                continue
            if isinstance(x, Skizze3D) and abs(G.ebene_basis(x.ebene)[2][2]) < 0.9:
                continue
            out.append(x)
        return out

    def _hoehen_koerper(self):
        return [x for x in self.app.auswahl
                if isinstance(x, Koerper3D) and x.art in ("prisma", "pyramide") and _vorzeichen(x)]

    def _manip_beginn(self, d):
        """First movement of a drag: prepares extrusion / height change."""
        self.app._snapshot()
        d["modus"] = "verschieben"
        if d["achse"] == "z":
            ext = self._extrudierbare()
            if ext:
                neu = S.extrudieren(self.app.elemente, ext, 0.0)
                self.app.auswahl = [x for x in self.app.auswahl if x not in ext] + neu
                d["modus"] = "extrudieren"
                d["ziel"] = neu
            elif self.hoehe_var.get() and self._hoehen_koerper():
                d["modus"] = "hoehe"
                d["ziel"] = self._hoehen_koerper()
                d["h0"] = [x.hoehe for x in d["ziel"]]
        d["angewandt"] = 0.0

    def _manip_setzen(self, d, mm):
        modus = d.get("modus", "verschieben")
        if modus == "extrudieren":
            for k in d["ziel"]:
                k.hoehe_setzen(mm * (_vorzeichen(k) or 1.0))
        elif modus == "hoehe":
            for k, h0 in zip(d["ziel"], d["h0"]):
                k.hoehe_setzen(h0 + mm * _vorzeichen(k))
        else:
            S.verschieben_achse(self.app.auswahl, d["achse"], mm - d["angewandt"])
            d["angewandt"] = mm
        d["mm"] = mm

    def wert_anwenden(self):
        """Typed value: sketch size while drawing, else distance along the chosen axis."""
        text = self.wert_var.get().strip()
        if not text:
            return
        sk = self._skiz
        if sk and sk["form"] in ("kreis", "rechteck", "linie"):
            self._skizze_wert(text, sk)
            return
        try:
            mm = float(text.replace(",", ".")) * self.app._einh_faktor()
        except ValueError:
            self.info_var.set(tr("d3.msg.zahl"))
            return
        if not self.app.auswahl:
            self.info_var.set(tr("d3.msg.keine_auswahl"))
            return
        achse = self._achse or "z"
        d = {"achse": achse, "mm": 0.0}
        self._manip_beginn(d)
        self._manip_setzen(d, mm)
        if d.get("modus") == "extrudieren":
            self._extrusion_abschliessen(d["ziel"])
        self.wert_var.set("")
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.verschoben", achse=achse.upper(),
                             wert=f"{mm / self.app._einh_faktor():.2f}",
                             einheit=self.app.einheit.get()))

    def eingabe_3d(self, text):
        """Input line of the main window while drawing in 3D (like in 2D). First point as
        'x,y' on the work plane; then circle: radius, rectangle: 'width,height' (or 'width x
        height'), line: 'length' or 'length<angle', polyline: 'x,y' or '@dx,dy'. -> True if used."""
        m = self._modus
        if m not in self.SKIZZEN:
            return False
        f = self.app._einh_faktor()
        sk = self._skiz

        def zahl(t):
            return float(t.strip().replace(",", ".")) * f
        try:
            t = text.strip().lower()
            if sk is None:
                a = [v for v in re.split(r"[,;]\s*|\s+", t) if v]
                if len(a) != 2:
                    raise ValueError
                p = (float(a[0].replace(",", ".")) * f, float(a[1].replace(",", ".")) * f)
                self._skiz = {"form": m, "pts": [p], "maus": p}
                self.info_var.set(tr("d3.msg.skizze_" + m))
            elif m == "poly":
                rel = t.startswith("@")
                a = [v for v in re.split(r"[,;]\s*|\s+", t.lstrip("@")) if v]
                if len(a) != 2:
                    raise ValueError
                x, y = float(a[0].replace(",", ".")) * f, float(a[1].replace(",", ".")) * f
                if rel:
                    x, y = sk["pts"][-1][0] + x, sk["pts"][-1][1] + y
                sk["pts"].append((x, y))
            elif m == "linie" and "<" in t:
                l, w = t.split("<", 1)
                L, W = zahl(l), math.radians(float(w.strip().replace(",", ".")))
                q = sk["pts"][0]
                self._skizze_fertig("linie", [q[0], q[1], q[0] + L * math.cos(W), q[1] + L * math.sin(W)])
            else:
                self._skizze_wert(t, sk)
                return True
        except ValueError:
            self.info_var.set(tr("d3.msg.zahl"))
            return True
        self.zeichne()
        return True

    def _skizze_wert(self, text, sk):
        """Typed size while drawing: circle = radius, rectangle = width [x height]."""
        f = self.app._einh_faktor()
        try:
            trenner = r"[x;, ]+" if sk["form"] == "rechteck" else r"[x; ]+"   # "500,1000" like in 2D
            teile = [t for t in re.split(trenner, text.strip().lower()) if t]
            zahlen = [float(t.replace(",", ".")) * f for t in teile]
        except ValueError:
            zahlen = []
        if not zahlen or any(z <= 0 for z in zahlen):
            self.info_var.set(tr("d3.msg.zahl"))
            return
        q = sk["pts"][0]
        self.wert_var.set("")
        if sk["form"] == "kreis":
            self._skizze_fertig("kreis", [q[0], q[1], zahlen[0]])
        elif sk["form"] == "linie":
            m = (self._lokal_punkt(self._maus) if self._maus is not None else None) or (q[0] + 1, q[1])
            dx, dy = m[0] - q[0], m[1] - q[1]
            n = math.hypot(dx, dy) or 1.0
            if n < 1e-9:
                dx, dy, n = 1.0, 0.0, 1.0
            self._skizze_fertig("linie", [q[0], q[1], q[0] + dx / n * zahlen[0], q[1] + dy / n * zahlen[0]])
        else:
            w = zahlen[0]
            h = zahlen[1] if len(zahlen) > 1 else zahlen[0]
            self._skizze_fertig("rechteck", [q[0], q[1], q[0] + w, q[1] + h])
        self.zeichne()

    # ------------------------------------------------------------------
    # creating bodies
    # ------------------------------------------------------------------
    def neuer_koerper(self, art):
        k = self.kamera
        if art == "schrank":
            dlg = SchrankDialog(self.app.root, self.app._einh_faktor(), self.app.einheit.get(),
                                (k.ziel[0], k.ziel[1]))
        else:
            dlg = Koerper3DDialog(self.app.root, art, self.app._einh_faktor(),
                                  self.app.einheit.get(), (k.ziel[0], k.ziel[1]))
        self.app.root.wait_window(dlg)
        if not dlg.result:
            return
        par, pos, mit_klick = dlg.result
        self._modus_ende()
        if mit_klick:
            self._platz = {"art": art, "par": par, "z": pos[2], "maus": None}
            self.info_var.set(tr("d3.msg.platzieren"))
        else:
            self._erzeuge(art, par, pos)

    def _erzeuge(self, art, par, pos):
        body = koerper_bauen(art, par, pos[0], pos[1], pos[2])
        for key, v in self._stil().items():
            setattr(body, key, v)
            for t in getattr(body, "teile", ()):                 # cabinet = block of several bodies
                setattr(t, key, v)
        self.app._snapshot()
        self.app.elemente.append(body)
        self.app.auswahl = [body]
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.erzeugt", art=tr("d3.neu." + art)))

    def _platz_pos(self, e, pl):
        """Base point of a body being placed: grid, then OSNAP: a corner/centre of the new body
        snaps onto a snap point of an existing object (to line bodies up or join them).
        -> (position or None, [(snap point, kind)])"""
        p = self._bodenpunkt(e, pl["z"])
        if p is None:
            return None, []
        if not self.app.osnap.get():
            return p, []
        mx, my = self._mitte()
        body = koerper_bauen(pl["art"], pl["par"], p[0], p[1], p[2])
        eigene = self._ecken_von([body])
        andere = S.fang_kandidaten(self._sichtbare())
        best, bd = None, 16.0
        for c in eigene:
            qc = self.kamera.proj(c, mx, my)
            if qc is None:
                continue
            for pt, art in andere:
                qe = self.kamera.proj(pt, mx, my)
                if qe is None:
                    continue
                d = math.hypot(qe[0] - qc[0], qe[1] - qc[1])
                if d < bd:
                    best, bd = (G.v_sub(pt, c), pt, art), d
        if best is None:
            return p, []
        dv, pt, art = best
        return (p[0] + dv[0], p[1] + dv[1], p[2] + dv[2]), [(pt, art)]

    def _platz_klick(self, e):
        pl = self._platz
        pos, _f = self._platz_pos(e, pl)
        if pos is None:
            self.info_var.set(tr("d3.msg.keine_ebene"))
            return
        self._platz = None
        self._erzeuge(pl["art"], pl["par"], pos)

    def abbrechen(self):
        if self._skiz is not None:
            self._skiz = None
            self.zeichne()
        elif self._modus is not None:
            self._modus_ende()
            self.zeichne()
        elif self._platz is not None:
            self._platz = None
            self.zeichne()
        elif self.app.auswahl:
            self.app.auswahl = []
            self.app.redraw()
            self.zeichne()

    # ------------------------------------------------------------------
    # bore, extrude, size, block
    # ------------------------------------------------------------------
    def loch_dialog(self):
        """Bore / pocket from the selected sketches into the body they lie on."""
        sk = [x for x in self.app.auswahl if isinstance(x, Skizze3D)]
        if not sk:
            self.info_var.set(tr("d3.msg.kein_loch_ziel"))
            return
        u = self.app.einheit.get()
        t = frage_zahl(self.app.root, tr("d3.neu.loch"), tr("d3.dlg.tiefe_loch") + f" ({u})", "0")
        if t is None:
            return
        tiefe = abs(t) * self.app._einh_faktor()
        self.app._snapshot()
        n = 0
        for x in sk:
            if S.skizze_in_ausschnitt(self.app.elemente, x, tiefe if tiefe > 1e-9 else None):
                n += 1
        self.app.auswahl = [x for x in self.app.auswahl if x in self.app.elemente]
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.loch_erzeugt") if n else tr("d3.msg.loch_ausserhalb"))

    def drehen_dialog(self):
        """Rotate the selection about X, Y or Z through the manipulator origin."""
        if not self.app.auswahl:
            self.info_var.set(tr("d3.msg.nichts_drehbar"))
            return
        dlg = DrehDialog(self.app.root)
        self.app.root.wait_window(dlg)
        if not dlg.result:
            return
        achse, winkel = dlg.result
        richt = S.ACHSEN[achse]
        p0 = self._manip_zentrum3()
        self.app._snapshot()
        n = S.drehen3d(self.app.auswahl, p0, richt, winkel)
        if not n:
            self.info_var.set(tr("d3.msg.nichts_drehbar"))
        else:
            self.info_var.set(tr("d3.msg.gedreht", n=n, achse=achse.upper(), winkel="%g" % winkel))
        self.app.redraw()
        self.zeichne()

    def abrunden_dialog(self):
        """Round vertical edges and / or the top / bottom perimeter edges of the selected bodies."""
        ziele = [k for x in self.app.auswahl if S.ist_3d(x) for k in x.koerper() if k.art == "prisma"]
        if not ziele:
            self.info_var.set(tr("d3.msg.nichts_abrundbar"))
            return
        dlg = AbrundDialog(self.app.root, self.app.einheit.get())
        self.app.root.wait_window(dlg)
        if not dlg.result:
            return
        r, senkrecht, oben, unten = dlg.result
        r *= self.app._einh_faktor()
        self.app._snapshot()
        n = 0
        for k in ziele:
            ok = False
            if senkrecht and not k.rund:
                ok = k.kanten_abrunden(r) or ok
            if oben or unten:
                ok = k.kanten_oben_unten(r, oben, unten) or ok
            n += 1 if ok else 0
        self.info_var.set(tr("d3.msg.abgerundet", n=n) if n else tr("d3.msg.nichts_abrundbar"))
        self.app.redraw()
        self.zeichne()

    def extrudieren_dialog(self):
        ziele = [x for x in self.app.auswahl if S.extrudierbar(x)]
        if not ziele:
            self.info_var.set(tr("d3.msg.nichts_extrudierbar"))
            return
        u = self.app.einheit.get()
        h = frage_zahl(self.app.root, tr("d3.extrudieren"), tr("d3.msg.hoehe_frage", einheit=u),
                       "20")
        if h is None or abs(h) < 1e-9:
            return
        self.app._snapshot()
        neu = S.extrudieren(self.app.elemente, ziele, h * self.app._einh_faktor())
        self.app.auswahl = [x for x in self.app.auswahl if x not in ziele] + neu
        self._extrusion_abschliessen(neu)
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.extrudiert", n=len(neu)))

    def massdialog(self):
        """Change size (radius, width, depth, height ...) of the selected body / sketch."""
        ziele = [x for x in self.app.auswahl if S.parameter(x)]
        if len(ziele) != 1:
            self.info_var.set(tr("d3.msg.kein_mass"))
            return
        el = ziele[0]
        f, u = self.app._einh_faktor(), self.app.einheit.get()
        felder = []
        for key, wert in S.parameter(el):
            if key == "faktor":
                felder.append((key, tr("d3.dlg.faktor"), 100.0))
            else:
                felder.append((key, tr("d3.dlg." + key) + f" ({u})", wert / f))
        dlg = MassDialog(self.app.root, tr("d3.mass"), felder)
        self.app.root.wait_window(dlg)
        if not dlg.result:
            return
        par = {k: (v if k == "faktor" else v * f) for k, v in dlg.result.items()}
        self.app._snapshot()
        if S.parameter_setzen(el, par):
            self.app.redraw()
            self.zeichne()
            self.info_var.set(tr("d3.msg.mass_geaendert"))

    def block_bilden(self):
        if len([x for x in self.app.auswahl if S.ist_3d(x)]) < 2:
            self.info_var.set(tr("d3.msg.block_min2"))
            return
        name = frage_text(self.app.root, tr("d3.block"), tr("d3.msg.block_name"), "3D-Block") \
            or "3D-Block"
        self.app._snapshot()
        g = S.gruppe_bilden(self.app.elemente, self.app.auswahl, name)
        self.app.auswahl = [g] if g else []
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.block_gebildet", name=name))

    def block_aufloesen(self):
        gr = [x for x in self.app.auswahl if isinstance(x, Gruppe3D)]
        if not gr:
            self.info_var.set(tr("d3.msg.kein_block"))
            return
        self.app._snapshot()
        frei = S.gruppe_aufloesen(self.app.elemente, gr)
        self.app.auswahl = frei
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.block_aufgeloest"))

    # ------------------------------------------------------------------
    # context menu
    # ------------------------------------------------------------------
    def kontextmenue(self, e):
        el = S.pick([x for x in self.app.elemente if self._sichtbar(x)], self.kamera,
                    *self._mitte(), e.x, e.y)
        if el is not None and el not in self.app.auswahl:
            self.app.auswahl = [el]
            self.app.redraw()
            self.zeichne()
        stil = dict(tearoff=0, bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                    activebackground=FARBEN["cyan"], activeforeground=FARBEN["bg_dunkel"])
        m = tk.Menu(self, **stil)
        if self.app.auswahl:
            m.add_command(label=tr("d3.ctx.eigenschaften"), command=self._ctx_eigenschaften)
            if len([x for x in self.app.auswahl if S.parameter(x)]) == 1:
                m.add_command(label=tr("d3.ctx.mass"), command=self.massdialog)
            m.add_command(label=tr("d3.ctx.layer_aus"), command=self._ctx_layer_aus)
            m.add_command(label=tr("d3.ctx.loeschen"), command=self._ctx_loeschen)
            m.add_separator()
        m.add_command(label=tr("d3.ctx.layer_ein"), command=self._ctx_layer_ein)
        m.add_command(label=tr("d3.ctx.layer_dialog"), command=self.app.layer_verwalten)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _ctx_eigenschaften(self):
        if len(self.app.auswahl) == 1:
            self.app._element_bearbeiten(self.app.auswahl[0])
        else:
            self.app.eigenschaften_fenster()
        self.app.redraw()
        self.zeichne()

    def _ctx_layer_aus(self):
        names = {getattr(x, "layer", None) for x in self.app.auswahl}
        self.app._snapshot()
        for n in names:
            l = self.app.layers.get(n)
            if l:
                l.sichtbar = False
        self.app.auswahl = []
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.layer_aus", layer=", ".join(sorted(str(n) for n in names))))

    def _ctx_layer_ein(self):
        self.app._snapshot()
        for l in self.app.layers.values():
            l.sichtbar = True
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.layer_ein"))

    def _ctx_loeschen(self):
        self.app.auswahl_loeschen()
        self.zeichne()


def frage_text(parent, titel, text, vorgabe):
    dlg = _LayoutNameDialog(parent, titel, vorgabe, text)
    return dlg.result or None


class Ansicht3DMixin:
    """Methods of CadApp for the embedded 3D view."""

    _ansicht3d = None
    _3d_state = None

    def _3d_zustand(self):
        """State that survives switching back and forth (camera, toggles, work plane)."""
        if self._3d_state is None:
            self._3d_state = {"kamera": G.Kamera(), "wuerfel": tk.BooleanVar(value=True),
                              "persp": tk.BooleanVar(value=False),
                              "hoehe": tk.BooleanVar(value=False),
                              "raster": self.raster_sichtbar, "plane": None, "auto": True}
        return self._3d_state

    def _3d_var_holen(self):
        if getattr(self, "_3d_var", None) is None:
            self._3d_var = tk.BooleanVar(value=False)
        return self._3d_var

    def ansicht3d_aktiv(self):
        return self._ansicht3d is not None

    def ansicht3d_umschalten(self):
        self.ansicht3d_setzen(not self.ansicht3d_aktiv())

    def _vp_fuer_3d(self):
        """Viewport that the 3D switch affects in a layout: active, selected, or the only one."""
        if self._aktiver_viewport is not None:
            return self._aktiver_viewport
        vps = [x for x in self.layout_elemente if isinstance(x, Viewport)]
        sel = [x for x in vps if x in self.auswahl]
        if sel:
            return sel[0]
        return vps[0] if len(vps) == 1 else None

    def _ansicht3d_im_layout(self, an):
        """In a layout the 3D switch turns the chosen viewport 3D (iso view) or back to 2D."""
        vp = self._vp_fuer_3d()
        if vp is None:
            self.status.set(tr("d3.vp.waehlen"))
            self._3d_var_holen().set(bool(getattr(self._vp_fuer_3d(), "ansicht3d", None)))
            return
        self._snapshot()
        if an and not vp.ansicht3d:
            S.vp_ansicht_setzen(vp, self.elemente, -45.0, 35.264, False)
            self.status.set(tr("d3.vp.an"))
        elif not an:
            vp.ansicht3d = None
        self._3d_var_holen().set(bool(vp.ansicht3d))
        self.redraw()

    def ansicht3d_setzen(self, an):
        an = bool(an)
        if self._ist_layout():
            if self._ansicht3d is not None:
                self._ansicht3d_aus_fenster()
            self._ansicht3d_im_layout(an)
            self.werkzeuge_fuer_3d()
            return
        w = self._ansicht3d
        if an and w is None:
            w = Ansicht3D(self)
            self._ansicht3d = w
            w.pack(fill=tk.BOTH, expand=True, before=self.canvas)
            self.canvas.pack_forget()
            w.after(60, w.einpassen)
            self.ansicht3d_werkzeug(beim_oeffnen=True)
        elif not an and w is not None:
            self.canvas.pack(fill=tk.BOTH, expand=True, before=w)
            self._ansicht3d = None
            w.destroy()
            self.redraw()
        self._3d_var_holen().set(an)
        self.werkzeuge_fuer_3d()

    def _ansicht3d_aus_fenster(self):
        w = self._ansicht3d
        if w is not None:
            self.canvas.pack(fill=tk.BOTH, expand=True, before=w)
            self._ansicht3d = None
            w.destroy()

    def ansicht3d_werkzeug(self, beim_oeffnen=False):
        """Called when the tool changes (and when 3D opens): in 3D the basic tools Line,
        Polyline, Circle, Rectangle and Dimension work on the work plane / as 3D
        dimension; other 2D tools switch back to the 2D view."""
        w = self._ansicht3d
        if w is None or self._ist_layout():
            return
        wz = self.aktives_werkzeug.get()
        if wz in WERKZEUG_3D:
            w.modus_setzen(WERKZEUG_3D[wz])
        elif wz == "auswahl":
            if w._modus in WERKZEUG_3D.values():
                w._modus_ende()
                w.zeichne()
        else:                                      # 2D-only tool: stays in 3D, just not available
            self.aktives_werkzeug.set("auswahl")
            self._werkzeug_gewechselt_2d()
            if not beim_oeffnen:
                self.status.set(tr("d3.msg.nur_2d"))

    def werkzeuge_fuer_3d(self):
        """Greys out the toolbar buttons that only work in 2D while the 3D view is shown."""
        an = self.ansicht3d_aktiv() and not self._ist_layout()
        for key, b in getattr(self, "_wz_knoepfe", {}).items():
            if key in WERKZEUG_3D or key == "auswahl":
                continue
            if key.startswith("cmd:") and key != "cmd:laenge":
                continue
            try:
                b.state(["disabled"] if an else ["!disabled"])
            except Exception:
                pass

    def ansicht3d_oeffnen(self):
        self.ansicht3d_setzen(True)
        return self._ansicht3d

    def ansicht3d_aktualisieren(self):
        w = self._ansicht3d
        if w is None:
            return
        try:
            w.aktualisieren()
        except Exception:
            pass

    def ansicht3d_befehl(self, cmd):
        """cmd: 'neu:<art>', 'extrudieren', 'loch', 'block', 'aufloesen', 'mass'."""
        if cmd in ("pivot", "pivot_zentrum") and not self.ansicht3d_aktiv():
            # in the 2D view the same commands move / centre the 2D manipulator
            (self.manipulator_versetzen if cmd == "pivot" else self.manipulator_zentrieren)()
            return
        w = self.ansicht3d_oeffnen()
        if cmd.startswith("neu:"):
            w.neuer_koerper(cmd.split(":", 1)[1])
        elif cmd == "extrudieren":
            w.extrudieren_dialog()
        elif cmd == "loch":
            w.loch_dialog()
        elif cmd == "block":
            w.block_bilden()
        elif cmd == "aufloesen":
            w.block_aufloesen()
        elif cmd == "mass":
            w.massdialog()
        elif cmd == "drehen":
            w.drehen_dialog()
        elif cmd == "abrunden":
            w.abrunden_dialog()
        elif cmd == "pivot":
            w.modus_setzen("pivot")
        elif cmd == "pivot_zentrum":
            w.pivot_zuruecksetzen()
