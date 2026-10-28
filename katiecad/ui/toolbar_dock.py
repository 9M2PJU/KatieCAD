# -*- coding: utf-8 -*-
"""
katiecad/ui/toolbar_dock.py - Dockable symbol toolbar (mixin of CadApp, MIT).

There is one symbol toolbar per department (tools, electrical, 3D). Each can
sit on top, at the bottom or at the right edge of the window, independently
of the others. Drag the grip at the start of a bar towards an edge and
release - it snaps there - or choose View > Toolbars. At the right edge the
symbols wrap into several columns. The choices are stored in the configuration.
"""

import tkinter as tk
from tkinter import ttk

from katiecad.common.config import lade_konfiguration, speichere_konfiguration

POSITIONEN = ("oben", "unten", "rechts")
ZELLE_PX = 36                 # height of one symbol row at the right edge


def ziel_position(relx, rely, aktuell="oben"):
    """Docking edge for a pointer position inside the window (0..1)."""
    if relx > 0.85:
        return "rechts"
    if rely > 0.78:
        return "unten"
    if rely < 0.22:
        return "oben"
    return aktuell


def spalten_zeilen(anzahl, hoehe_px):
    """Rows per column for the right-hand toolbar."""
    return max(6, min(anzahl, int(hoehe_px // ZELLE_PX)))


LEISTEN = ("werkzeug", "elektro", "3d")            # order inside a docking area
LEISTEN_ATTR = {"werkzeug": "tb1", "elektro": "tbE", "3d": "tbD"}
CONFIG_KEY = {"werkzeug": "toolbar_pos", "elektro": "toolbar_pos_elektro",
              "3d": "toolbar_pos_3d"}


class ToolbarDockMixin:
    _tb_pos_werte = None
    _tb_info = None
    _tb_resize_id = None
    _tb_zonen = None

    # ---- positions ----------------------------------------------------
    def toolbar_position(self, name="werkzeug"):
        if self._tb_pos_werte is None:
            self._tb_pos_werte = {}
        if name not in self._tb_pos_werte:
            try:
                pos = lade_konfiguration().get(CONFIG_KEY[name], "oben")
            except Exception:
                pos = "oben"
            self._tb_pos_werte[name] = pos if pos in POSITIONEN else "oben"
        return self._tb_pos_werte[name]

    def toolbar_position_setzen(self, pos, name="werkzeug", speichern=True):
        if pos not in POSITIONEN or name not in CONFIG_KEY:
            return
        self.toolbar_position(name)
        self._tb_pos_werte[name] = pos
        if speichern:
            try:
                cfg = lade_konfiguration()
                cfg[CONFIG_KEY[name]] = pos
                speichere_konfiguration(cfg)
            except Exception:
                pass
        self._toolbar_anordnen()

    def _leiste(self, name):
        return getattr(self, LEISTEN_ATTR[name], None)

    def _zone(self, pos):
        """Frame that holds all bars docked at `pos` (created on demand)."""
        if self._tb_zonen is None:
            self._tb_zonen = {}
        z = self._tb_zonen.get(pos)
        if z is None:
            z = ttk.Frame(self.root)
            self._tb_zonen[pos] = z
        return z

    # ---- layout -------------------------------------------------------
    def _toolbar_anordnen(self):
        """(Re)places the three symbol toolbars according to their stored positions."""
        if self._tb_info is None:
            self._tb_info = {}
        koord = getattr(self, "_koord_bar", None)
        belegt = {p: [] for p in POSITIONEN}
        for name in LEISTEN:
            tb = self._leiste(name)
            if tb is None:
                continue
            pos = self.toolbar_position(name)
            if pos != "oben" and koord is None:
                pos = "oben"
            belegt[pos].append(name)
            for ch in tb.winfo_children():
                if ch.winfo_manager() == "pack":
                    self._tb_info[ch] = ch.pack_info()
            for ch in tb.winfo_children():
                ch.pack_forget()
                ch.grid_forget()
            tb.pack_forget()
        for pos in POSITIONEN:
            self._zone(pos).pack_forget()
        # docking areas
        if belegt["oben"]:
            self._zone("oben").pack(side=tk.TOP, fill=tk.X, before=self.tb2)
        if belegt["unten"] and koord is not None:
            self._zone("unten").pack(side=tk.BOTTOM, fill=tk.X, after=koord)
        if belegt["rechts"] and koord is not None:
            self._zone("rechts").pack(side=tk.RIGHT, fill=tk.Y, after=koord)
        for pos, namen in belegt.items():
            zone = self._zone(pos)
            for name in namen:
                tb = self._leiste(name)
                if pos == "rechts":
                    tb.pack(in_=zone, side=tk.TOP, fill=tk.X, anchor="n")
                if pos == "rechts":
                    self._leiste_gitter(name, len(namen))
                else:
                    for ch in tb.winfo_children():
                        info = self._tb_info.get(ch)
                        if info:
                            info = {k: v for k, v in info.items() if k != "in"}
                            ch.pack(**info)
                        else:
                            ch.pack(side=tk.LEFT)
        for pos in ("oben", "unten"):
            self._zone_reihen(pos, belegt[pos])
        if not getattr(self, "_tb_binding", False):
            self._tb_binding = True
            self.root.bind("<Configure>", self._toolbar_groesse, add="+")

    def _zone_reihen(self, pos, namen):
        """Bars on top/bottom sit side by side and wrap into a new row when too wide."""
        if not namen:
            return
        zone = self._zone(pos)
        try:
            self.root.update_idletasks()
        except Exception:
            return
        frei = self.root.winfo_width()
        frei = frei if frei > 300 else 1200
        reihe, x, spalte = 0, 0, 0
        for name in namen:
            tb = self._leiste(name)
            w = tb.winfo_reqwidth()
            if x and x + w > frei:
                reihe, x, spalte = reihe + 1, 0, 0
            tb.grid(in_=zone, row=reihe, column=spalte, sticky="nw")
            x += w
            spalte += 1

    def _leiste_gitter(self, name, anzahl_rechts):
        tb = self._leiste(name)
        sichtbar = [c for c in tb.winfo_children() if not isinstance(c, ttk.Separator)]
        hoehe = (self.root.winfo_height() - 230) // max(1, anzahl_rechts)
        n = spalten_zeilen(len(sichtbar), hoehe)
        for i, ch in enumerate(sichtbar):
            ch.grid(row=i % n, column=i // n, padx=1, pady=1, sticky="w")
        return n

    def _toolbar_groesse(self, event=None):
        if self._tb_resize_id is not None:
            try:
                self.root.after_cancel(self._tb_resize_id)
            except Exception:
                pass
        self._tb_resize_id = self.root.after(250, self._toolbar_neu_gitter)

    def _toolbar_neu_gitter(self):
        self._tb_resize_id = None
        rechts = [n for n in LEISTEN if self._leiste(n) is not None
                  and self.toolbar_position(n) == "rechts"]
        key = (self.root.winfo_height() // ZELLE_PX, self.root.winfo_width() // 40, len(rechts))
        if getattr(self, "_tb_zeilen", None) == key:
            return
        self._tb_zeilen = key
        for n in rechts:
            self._leiste_gitter(n, len(rechts))
        for pos in ("oben", "unten"):
            self._zone_reihen(pos, [n for n in LEISTEN if self._leiste(n) is not None
                                    and self.toolbar_position(n) == pos])

    def _toolbar_griff_binden(self, griff, name="werkzeug"):
        """Drag the grip to an edge of the window and release."""
        def los(e):
            try:
                w = max(1, self.root.winfo_width())
                h = max(1, self.root.winfo_height())
                px, py = self.root.winfo_pointerxy()
                relx = (px - self.root.winfo_rootx()) / w
                rely = (py - self.root.winfo_rooty()) / h
            except Exception:
                return
            neu = ziel_position(relx, rely, self.toolbar_position(name))
            if neu != self.toolbar_position(name):
                self.toolbar_position_setzen(neu, name)
        griff.bind("<ButtonRelease-1>", los)
