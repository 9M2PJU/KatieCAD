# -*- coding: utf-8 -*-
"""
katiecad/ui/toolbar_dock.py - Dockable symbol toolbar (mixin of CadApp, MIT).

The symbol toolbar (tb1) can sit on top, at the bottom or at the right edge
of the window. Drag the grip at its start towards an edge and release - it
snaps there - or choose View > Toolbar. At the right edge the symbols wrap
into several columns. The choice is stored in the configuration.
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


class ToolbarDockMixin:
    _tb_pos_wert = None
    _tb_info = None
    _tb_resize_id = None

    def toolbar_position(self):
        if self._tb_pos_wert is None:
            try:
                pos = lade_konfiguration().get("toolbar_pos", "oben")
            except Exception:
                pos = "oben"
            self._tb_pos_wert = pos if pos in POSITIONEN else "oben"
        return self._tb_pos_wert

    def toolbar_position_setzen(self, pos, speichern=True):
        if pos not in POSITIONEN:
            return
        self._tb_pos_wert = pos
        if speichern:
            try:
                cfg = lade_konfiguration()
                cfg["toolbar_pos"] = pos
                speichere_konfiguration(cfg)
            except Exception:
                pass
        self._toolbar_anordnen()

    def _toolbar_anordnen(self):
        """(Re)places tb1 according to the stored position."""
        tb = self.tb1
        pos = self.toolbar_position()
        kinder = list(tb.winfo_children())
        if self._tb_info is None:
            self._tb_info = {}
        for ch in kinder:                       # remember the original pack options
            if ch.winfo_manager() == "pack":
                self._tb_info[ch] = ch.pack_info()
        for ch in kinder:
            ch.pack_forget()
            ch.grid_forget()
        tb.pack_forget()
        koord = getattr(self, "_koord_bar", None)
        if pos == "unten" and koord is not None:
            tb.pack(side=tk.BOTTOM, fill=tk.X, after=koord)
        elif pos == "rechts" and koord is not None:
            tb.pack(side=tk.RIGHT, fill=tk.Y, after=koord)
        else:
            pos = "oben"
            tb.pack(side=tk.TOP, fill=tk.X, before=self.tb2)
        if pos == "rechts":
            sichtbar = [c for c in kinder if not isinstance(c, ttk.Separator)]
            n = spalten_zeilen(len(sichtbar), self.root.winfo_height() - 230)
            for i, ch in enumerate(sichtbar):
                ch.grid(row=i % n, column=i // n, padx=1, pady=1, sticky="w")
        else:
            for ch in kinder:
                info = self._tb_info.get(ch)
                if info:
                    ch.pack(**info)
                else:
                    ch.pack(side=tk.LEFT)
        if not getattr(self, "_tb_binding", False):
            self._tb_binding = True
            self.root.bind("<Configure>", self._toolbar_groesse, add="+")

    def _toolbar_groesse(self, event=None):
        if self.toolbar_position() != "rechts":
            return
        if self._tb_resize_id is not None:
            try:
                self.root.after_cancel(self._tb_resize_id)
            except Exception:
                pass
        self._tb_resize_id = self.root.after(250, self._toolbar_neu_gitter)

    def _toolbar_neu_gitter(self):
        self._tb_resize_id = None
        if self.toolbar_position() != "rechts":
            return
        kinder = [c for c in self.tb1.winfo_children() if not isinstance(c, ttk.Separator)]
        n = spalten_zeilen(len(kinder), self.root.winfo_height() - 230)
        letzte = getattr(self, "_tb_zeilen", None)
        if letzte == n:
            return
        self._tb_zeilen = n
        for i, ch in enumerate(kinder):
            ch.grid(row=i % n, column=i // n, padx=1, pady=1, sticky="w")

    def _toolbar_griff_binden(self, griff):
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
            neu = ziel_position(relx, rely, self.toolbar_position())
            if neu != self.toolbar_position():
                self.toolbar_position_setzen(neu)
        griff.bind("<ButtonRelease-1>", los)
