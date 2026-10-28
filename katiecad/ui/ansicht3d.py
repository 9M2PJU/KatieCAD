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
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

from katiecad.common.i18n import tr
from katiecad.model.core import (FARBEN, UI_SCHRIFT, Koerper3D, Gruppe3D, quader, zylinder,
                                 kegel, pyramide, kugel)
from katiecad.model import geom3d as G
from katiecad.model import szene3d as S

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
    raise ValueError(art)


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
        try:
            self.grab_set()
        except tk.TclError:
            pass

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



class LochDialog(tk.Toplevel):
    """Hole (bore). result = (radius_mm, tiefe_mm | None, (x, y), mit_klick)."""

    def __init__(self, parent, faktor, einheit, ort):
        super().__init__(parent)
        self.result = None
        self.f = faktor
        self.title(tr("d3.neu.loch"))
        self.transient(parent)
        self.configure(bg=FARBEN["bg_mittel"])
        self.resizable(False, False)
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        self.vars = {}
        felder = [("durchmesser", tr("d3.dlg.durchmesser") + f" ({einheit})", "10"),
                  ("tiefe", tr("d3.dlg.tiefe_loch") + f" ({einheit})", "0"),
                  ("x", tr("d3.dlg.x") + f" ({einheit})", "%g" % (ort[0] / faktor)),
                  ("y", tr("d3.dlg.y") + f" ({einheit})", "%g" % (ort[1] / faktor))]
        for r, (key, text, wert) in enumerate(felder):
            ttk.Label(f, text=text).grid(row=r, column=0, sticky=tk.W, pady=3)
            v = tk.StringVar(value=wert)
            self.vars[key] = v
            ttk.Entry(f, textvariable=v, width=12).grid(row=r, column=1, padx=8, pady=3)
        self.klick = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text=tr("d3.dlg.klick_loch"), variable=self.klick
                        ).grid(row=len(felder), column=0, columnspan=2, sticky=tk.W, pady=6)
        bt = ttk.Frame(f)
        bt.grid(row=len(felder) + 1, column=0, columnspan=2, pady=(6, 0))
        ttk.Button(bt, text="OK", command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(bt, text=tr("dlg.abbrechen"), command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _zahl(self, key):
        return float(self.vars[key].get().strip().replace(",", "."))

    def _ok(self):
        try:
            d = self._zahl("durchmesser") * self.f
            t = abs(self._zahl("tiefe")) * self.f
            if d <= 0:
                raise ValueError("d")
            pos = (self._zahl("x") * self.f, self._zahl("y") * self.f)
        except ValueError:
            messagebox.showerror(tr("d3.titel"), tr("d3.msg.zahl"), parent=self)
            return
        self.result = (d / 2.0, (t if t > 1e-9 else None), pos, bool(self.klick.get()))
        self.destroy()


class _Info:
    """Writes messages to the status line of the main window."""

    def __init__(self, app):
        self.app = app

    def set(self, text):
        try:
            self.app.status.set(text)
        except Exception:
            pass


class Ansicht3D(tk.Frame):
    def __init__(self, app):
        super().__init__(app.root, bg=FARBEN["bg_mittel"])
        self.app = app
        z = app._3d_zustand()
        self.kamera = z["kamera"]
        self.wuerfel_var, self.persp_var, self.hoehe_var = z["wuerfel"], z["persp"], z["hoehe"]
        self.breite, self.hoehe = 900, 600
        self._drag = None
        self._platz = None
        self._achse = None
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
        a._befehl_knopf(bar, "iso3d", farbe, lambda: self.ansicht("iso_so"))
        a._befehl_knopf(bar, "einpassen3d", farbe, self.einpassen)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        a._umschalt_knopf(bar, "hoehe3d", farbe, self.hoehe_var, lambda: None)
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
        self._drag = {"art": art, "x": e.x, "y": e.y}

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
        if self._drag and self._drag["art"] in ("orbit", "pan"):
            self._drag = None

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

    def zeichne(self, *_):
        self._spaeter_id = None
        c = self.canvas
        c.delete("all")
        try:
            c.configure(bg=self.app.bg_modell)
        except Exception:
            pass
        self._boden(*self._mitte())
        elemente = [e for e in self.app.elemente if self._sichtbar(e)]
        for el in elemente:
            if S.ist_3d(el):
                continue
            farbe, br = self._farbe(el), self._breite(el)
            for zug, geschlossen in S.flache_zuege(el):
                pts = [(x, y, 0.0) for (x, y) in zug]
                if geschlossen and len(pts) > 2:
                    pts.append(pts[0])
                for a, b in zip(pts, pts[1:]):
                    self._linie(a, b, farbe, br)
        for el, nz in S.koerper_netze(elemente):
            farbe, br = self._farbe(el), self._breite(el)
            for (i, j) in nz.kanten:
                self._linie(nz.punkte[i], nz.punkte[j], farbe, br)
        self._auswahl_zeichnen()
        self._vorschau_platz_zeichnen()
        if self.wuerfel_var.get():
            self._wuerfel_zeichnen()
        self._manip_zeichnen()

    def _boden(self, cx, cy):
        k = self.kamera
        try:
            schritt = float(self.app._zahl(self.app.raster_mm, 5.0)) or 5.0
        except Exception:
            schritt = 5.0
        radius = max(self.breite, self.hoehe) / k.skala / 2.0 * 1.3
        while radius / schritt > 40:
            schritt *= 2
        gx, gy = k.ziel[0], k.ziel[1]
        farbe = "#2a2140"
        i0, i1 = int(math.floor((gx - radius) / schritt)), int(math.ceil((gx + radius) / schritt))
        j0, j1 = int(math.floor((gy - radius) / schritt)), int(math.ceil((gy + radius) / schritt))
        for i in range(i0, i1 + 1):
            self._linie((i * schritt, j0 * schritt, 0.0), (i * schritt, j1 * schritt, 0.0), farbe,
                        1, None, "boden")
        for j in range(j0, j1 + 1):
            self._linie((i0 * schritt, j * schritt, 0.0), (i1 * schritt, j * schritt, 0.0), farbe,
                        1, None, "boden")
        L = 60.0 / k.skala
        for name, a in S.ACHSEN.items():
            self._linie((0.0, 0.0, 0.0), (a[0] * L, a[1] * L, a[2] * L), ACHSEN_FARBE[name], 2,
                        None, "boden")

    def _auswahl_zeichnen(self):
        farbe = FARBEN["cyan"]
        for el in self.app.auswahl:
            if S.ist_3d(el):
                for nz in el.netze():
                    for (i, j) in nz.kanten:
                        self._linie(nz.punkte[i], nz.punkte[j], farbe, 3, None, "auswahl")
            else:
                for zug, geschlossen in S.flache_zuege(el):
                    pts = [(x, y, 0.0) for (x, y) in zug]
                    if geschlossen and len(pts) > 2:
                        pts.append(pts[0])
                    for a, b in zip(pts, pts[1:]):
                        self._linie(a, b, farbe, 3, None, "auswahl")

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
        z = S.auswahl_zentrum3(self.app.auswahl)
        if z is None:
            return {}
        return S.achsen_info(self.kamera, z, *self._mitte())

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
            c.create_rectangle(p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5, fill=FARBEN["gelb"],
                               outline=FARBEN["bg_dunkel"], tags="manip")

    # ------------------------------------------------------------------
    # mouse: selection, cube, manipulator
    # ------------------------------------------------------------------
    def _bodenpunkt(self, e, z=0.0):
        p = self.kamera.auf_ebene(e.x, e.y, *self._mitte(), z)
        if p is None:
            return None
        try:
            if self.app.grid_snap.get():
                r = float(self.app._zahl(self.app.fang_mm, 5.0)) or 1.0
                p = (round(p[0] / r) * r, round(p[1] / r) * r, p[2])
        except Exception:
            pass
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
        infos = self._manip_infos()
        achse = S.manip_treffer(infos, e.x, e.y)
        if achse:
            self._drag = {"art": "manip", "achse": achse, "x": e.x, "y": e.y, "info": infos[achse],
                          "mm": 0.0, "bewegt": False}
            self._achse = achse
            return
        el = S.pick([x for x in self.app.elemente if self._sichtbar(x)], self.kamera,
                    *self._mitte(), e.x, e.y)
        if el is None:
            self.app.auswahl = []
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
        elif d["art"] == "manip":
            if abs(e.x - d["x"]) + abs(e.y - d["y"]) < 3 and not d["bewegt"]:
                return
            if not d["bewegt"]:
                d["bewegt"] = True
                self._manip_beginn(d)
            raster = None
            try:
                if self.app.grid_snap.get():
                    raster = float(self.app._zahl(self.app.fang_mm, 5.0)) or None
            except Exception:
                pass
            mm = S.verschiebung_mm(d["info"], e.x - d["x"], e.y - d["y"], raster)
            self._manip_setzen(d, mm)
            self.zeichne()

    def on_los(self, e):
        d, self._drag = self._drag, None
        if not d:
            return
        if d["art"] == "wuerfel":
            if not d["bewegt"]:
                if d["pfeil"]:
                    self._pfeil_ausfuehren(d["pfeil"])
                elif d["name"]:
                    self.ansicht(d["name"])
        elif d["art"] == "manip":
            if d["bewegt"]:
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
        if self._platz is not None:
            self._platz["maus"] = e
            self.zeichne()

    # ---- manipulator actions ---------------------------------------------
    def _extrudierbare(self):
        return [x for x in self.app.auswahl if S.extrudierbar(x)]

    def _hoehen_koerper(self):
        return [x for x in self.app.auswahl
                if isinstance(x, Koerper3D) and x.art in ("prisma", "pyramide")]

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
                k.hoehe_setzen(mm)
        elif modus == "hoehe":
            for k, h0 in zip(d["ziel"], d["h0"]):
                k.hoehe_setzen(h0 + mm)
        else:
            S.verschieben_achse(self.app.auswahl, d["achse"], mm - d["angewandt"])
            d["angewandt"] = mm
        d["mm"] = mm

    def wert_anwenden(self):
        """Typed value: distance along the chosen axis (Z: height of the pulled shape)."""
        text = self.wert_var.get().strip()
        if not text:
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
        self.wert_var.set("")
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.verschoben", achse=achse.upper(),
                             wert=f"{mm / self.app._einh_faktor():.2f}",
                             einheit=self.app.einheit.get()))

    # ------------------------------------------------------------------
    # creating bodies and holes
    # ------------------------------------------------------------------
    def neuer_koerper(self, art):
        k = self.kamera
        dlg = Koerper3DDialog(self.app.root, art, self.app._einh_faktor(), self.app.einheit.get(),
                              (k.ziel[0], k.ziel[1]))
        self.app.root.wait_window(dlg)
        if not dlg.result:
            return
        par, pos, mit_klick = dlg.result
        if mit_klick:
            self._platz = {"art": art, "par": par, "z": pos[2], "maus": None}
            self.info_var.set(tr("d3.msg.platzieren"))
        else:
            self._erzeuge(art, par, pos)

    def _erzeuge(self, art, par, pos):
        kw = {}
        try:
            kw = self.app._layer_daten()
            kw["staerke"] = None
            kw["eig_farbe"] = True
        except Exception:
            kw = {}
        body = koerper_bauen(art, par, pos[0], pos[1], pos[2])
        for key, v in kw.items():
            setattr(body, key, v)
        self.app._snapshot()
        self.app.elemente.append(body)
        self.app.auswahl = [body]
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.erzeugt", art=tr("d3.neu." + art)))

    def loch_dialog(self):
        ziele = S.loch_ziele(self.app.auswahl)
        if not ziele:
            self.info_var.set(tr("d3.msg.kein_loch_ziel"))
            return
        ziel = ziele[0]
        k = self.kamera
        mx, my = ziel.zentrum3()[0], ziel.zentrum3()[1]
        dlg = LochDialog(self.app.root, self.app._einh_faktor(), self.app.einheit.get(), (mx, my))
        self.app.root.wait_window(dlg)
        if not dlg.result:
            return
        r, tiefe, pos, mit_klick = dlg.result
        if mit_klick:
            self._platz = {"art": "loch", "ziel": ziel, "r": r, "tiefe": tiefe,
                           "z": S.loch_oben_z(ziel), "maus": None}
            self.info_var.set(tr("d3.msg.platzieren"))
        else:
            self._loch_erzeugen(ziel, pos[0], pos[1], r, tiefe)

    def _loch_erzeugen(self, ziel, x, y, r, tiefe):
        self.app._snapshot()
        if not S.loch_setzen(ziel, x, y, r, tiefe):
            self.info_var.set(tr("d3.msg.loch_ausserhalb"))
            return
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.loch_erzeugt"))

    def _platz_klick(self, e):
        pl = self._platz
        p = self._bodenpunkt(e, pl["z"])
        if p is None:
            self.info_var.set(tr("d3.msg.keine_ebene"))
            return
        self._platz = None
        if pl["art"] == "loch":
            self._loch_erzeugen(pl["ziel"], p[0], p[1], pl["r"], pl["tiefe"])
        else:
            self._erzeuge(pl["art"], pl["par"], (p[0], p[1], pl["z"]))

    def _vorschau_platz_zeichnen(self):
        pl = self._platz
        if not pl or not pl.get("maus"):
            return
        p = self._bodenpunkt(pl["maus"], pl["z"])
        if p is None:
            return
        if pl["art"] == "loch":
            pts = G.kreis_profil(p[0], p[1], pl["r"], 24)
            pts = [(x, y, pl["z"]) for (x, y) in pts]
            for a, b in zip(pts, pts[1:] + pts[:1]):
                self._linie(a, b, FARBEN["gelb"], 1, (4, 3), "vorschau")
            return
        body = koerper_bauen(pl["art"], pl["par"], p[0], p[1], pl["z"])
        nz = body.netz()
        for (i, j) in nz.kanten:
            self._linie(nz.punkte[i], nz.punkte[j], FARBEN["gelb"], 1, (4, 3), "vorschau")

    def abbrechen(self):
        if self._platz is not None:
            self._platz = None
            self.zeichne()
        elif self.app.auswahl:
            self.app.auswahl = []
            self.app.redraw()
            self.zeichne()

    # ------------------------------------------------------------------
    # extrude, block, delete
    # ------------------------------------------------------------------
    def extrudieren_dialog(self):
        ziele = self._extrudierbare()
        if not ziele:
            self.info_var.set(tr("d3.msg.nichts_extrudierbar"))
            return
        f, u = self.app._einh_faktor(), self.app.einheit.get()
        h = simpledialog.askfloat(tr("d3.extrudieren"), tr("d3.msg.hoehe_frage", einheit=u),
                                  initialvalue=20.0, parent=self.app.root)
        if h is None or abs(h) < 1e-9:
            return
        self.app._snapshot()
        neu = S.extrudieren(self.app.elemente, ziele, h * f)
        self.app.auswahl = [x for x in self.app.auswahl if x not in ziele] + neu
        self.app.redraw()
        self.zeichne()
        self.info_var.set(tr("d3.msg.extrudiert", n=len(neu)))

    def block_bilden(self):
        if len([x for x in self.app.auswahl if S.ist_3d(x)]) < 2:
            self.info_var.set(tr("d3.msg.block_min2"))
            return
        name = simpledialog.askstring(tr("d3.block"), tr("d3.msg.block_name"),
                                      initialvalue="3D-Block", parent=self.app.root) or "3D-Block"
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


class Ansicht3DMixin:
    """Methods of CadApp for the embedded 3D view."""

    _ansicht3d = None
    _3d_state = None

    def _3d_zustand(self):
        """State that survives switching back and forth (camera, toggles)."""
        if self._3d_state is None:
            self._3d_state = {"kamera": G.Kamera(), "wuerfel": tk.BooleanVar(value=True),
                              "persp": tk.BooleanVar(value=False),
                              "hoehe": tk.BooleanVar(value=False)}
        return self._3d_state

    def _3d_var_holen(self):
        if getattr(self, "_3d_var", None) is None:
            self._3d_var = tk.BooleanVar(value=False)
        return self._3d_var

    def ansicht3d_aktiv(self):
        return self._ansicht3d is not None

    def ansicht3d_umschalten(self):
        self.ansicht3d_setzen(not self.ansicht3d_aktiv())

    def ansicht3d_setzen(self, an):
        an = bool(an)
        w = self._ansicht3d
        if an and w is None:
            w = Ansicht3D(self)
            self._ansicht3d = w
            w.pack(fill=tk.BOTH, expand=True, before=self.canvas)
            self.canvas.pack_forget()
            w.after(60, w.einpassen)
        elif not an and w is not None:
            self.canvas.pack(fill=tk.BOTH, expand=True, before=w)
            self._ansicht3d = None
            w.destroy()
            self.redraw()
        self._3d_var_holen().set(an)

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
        """cmd: '3d', 'neu:<art>', 'extrudieren', 'loch', 'block', 'aufloesen'."""
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
