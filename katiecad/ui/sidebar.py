# -*- coding: utf-8 -*-
"""
katiecad/ui/sidebar.py - Linke Seitenleiste von KatieCAD.

Oben:   Undo / Redo
Mitte:  Blattliste des geoeffneten Projekts (mit Nummerierung)
        bzw. Hinweis + Knoepfe, wenn kein Projekt offen ist.
Rand:   Ziehgriff zum Veraendern der Breite.

Die Leiste enthaelt keine Fachlogik; sie ruft nur Methoden der CadApp:
    undo, redo, blatt_wechseln(i), blatt_neu, blatt_loeschen,
    blatt_umbenennen(index=None), blatt_verschieben(delta),
    projekt_erstellen, projekt_oeffnen, projekt_drucken,
    sidebar_breite_merken(px)
und liest app.projekt (katiecad.model.project.Projekt oder None).
"""

import sys
import tkinter as tk
from tkinter import ttk

from katiecad.common.i18n import tr
from katiecad.model.core import FARBEN

BREITE_STANDARD = 230
BREITE_MIN = 170
BREITE_MAX = 620


class Seitenleiste(ttk.Frame):
    def __init__(self, parent, app, breite=None):
        super().__init__(parent, padding=(6, 6))
        self.app = app
        self._sync = False          # unterdrueckt Auswahl-Ereignisse
        self._undo_ok = False
        self._redo_ok = False
        self._wrap_labels = []
        self.breite = self._begrenzen(breite or BREITE_STANDARD)
        self.configure(width=self.breite)
        self.pack_propagate(False)

        # Ziehgriff (Geschwister im Hauptfenster)
        self.griff = tk.Frame(parent, width=5, cursor="sb_h_double_arrow",
                              bg=FARBEN["bg_mittel"])
        self.griff.bind("<Enter>", lambda e: self.griff.config(bg=FARBEN["cyan"]))
        self.griff.bind("<Leave>", lambda e: self.griff.config(bg=FARBEN["bg_mittel"]))
        self.griff.bind("<B1-Motion>", self._ziehen)
        self.griff.bind("<ButtonRelease-1>", self._ziehen_ende)
        self.bind("<Configure>", self._umbruch_anpassen)
        self._bauen()

    def einbauen(self):
        """Packt Leiste und Griff links ins Hauptfenster."""
        self.pack(side=tk.LEFT, fill=tk.Y)
        self.griff.pack(side=tk.LEFT, fill=tk.Y)

    # ---------------------------------------------------------
    # Groesse
    # ---------------------------------------------------------
    def _begrenzen(self, px):
        try:
            maximum = max(BREITE_MIN, min(BREITE_MAX,
                          int(self.winfo_toplevel().winfo_width() * 0.6)))
        except Exception:
            maximum = BREITE_MAX
        return max(BREITE_MIN, min(maximum, int(px)))

    def _ziehen(self, event):
        neu = self._begrenzen(event.x_root - self.winfo_rootx())
        if neu != self.breite:
            self.breite = neu
            self.configure(width=neu)

    def _ziehen_ende(self, event=None):
        try:
            self.app.sidebar_breite_merken(self.breite)
        except Exception:
            pass

    def _umbruch_anpassen(self, event=None):
        wl = max(80, self.winfo_width() - 24)
        for lbl in self._wrap_labels:
            try:
                lbl.configure(wraplength=wl)
            except tk.TclError:
                pass

    def _wrap_label(self, parent, **kw):
        lbl = ttk.Label(parent, wraplength=max(80, self.breite - 24),
                        justify=tk.LEFT, **kw)
        self._wrap_labels.append(lbl)
        return lbl

    # ---------------------------------------------------------
    # Aufbau
    # ---------------------------------------------------------
    def _bauen(self):
        for w in self.winfo_children():
            w.destroy()
        self._wrap_labels = []
        app = self.app

        # --- Undo / Redo ---
        zeile = ttk.Frame(self)
        zeile.pack(fill=tk.X)
        self.btn_undo = ttk.Button(zeile, text=tr("sb.undo"), command=app.undo)
        self.btn_undo.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.btn_redo = ttk.Button(zeile, text=tr("sb.redo"), command=app.redo)
        self.btn_redo.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        # --- Projektkopf ---
        ttk.Label(self, text=tr("sb.projekt"),
                  style="Title.TLabel").pack(anchor=tk.W)
        self.lbl_projekt = self._wrap_label(self, text="", style="Hint.TLabel")
        self.lbl_projekt.pack(anchor=tk.W, pady=(0, 6))

        # --- Ohne Projekt ---
        self.f_leer = ttk.Frame(self)
        self._wrap_label(self.f_leer, text=tr("sb.kein_projekt")).pack(
            anchor=tk.W, pady=(0, 8))
        ttk.Button(self.f_leer, text=tr("sb.projekt_erstellen"),
                   command=app.projekt_erstellen).pack(fill=tk.X, pady=2)
        ttk.Button(self.f_leer, text=tr("sb.projekt_oeffnen"),
                   command=app.projekt_oeffnen).pack(fill=tk.X, pady=2)

        # --- Mit Projekt: Blattliste ---
        self.f_blaetter = ttk.Frame(self)
        ttk.Label(self.f_blaetter, text=tr("sb.blaetter"),
                  style="Title.TLabel").pack(anchor=tk.W, pady=(0, 3))

        tf = ttk.Frame(self.f_blaetter)
        tf.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tf, columns=("nr", "name"),
                                 show="headings", selectmode="browse")
        self.tree.heading("nr", text=tr("sb.spalte_nr"))
        self.tree.heading("name", text=tr("sb.spalte_name"))
        self.tree.column("nr", width=46, anchor=tk.CENTER, stretch=False)
        self.tree.column("name", width=140, anchor=tk.W)
        sb = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._gewaehlt)
        self.tree.bind("<Double-Button-1>", self._doppelklick)
        self.tree.bind("<Button-3>", self._kontextmenue)
        if sys.platform == "darwin":     # Mac: Rechtsklick = Button-2 / Ctrl+Klick
            self.tree.bind("<Button-2>", self._kontextmenue)
            self.tree.bind("<Control-Button-1>", self._kontextmenue)
        self.tree.bind("<F2>", lambda e: app.blatt_umbenennen())

        bz = ttk.Frame(self.f_blaetter)
        bz.pack(fill=tk.X, pady=(6, 0))
        for text, cmd in (("+", app.blatt_neu),
                          ("\u2212", app.blatt_loeschen),
                          ("\u25B2", lambda: app.blatt_verschieben(-1)),
                          ("\u25BC", lambda: app.blatt_verschieben(+1)),
                          ("Abc", app.blatt_umbenennen)):
            ttk.Button(bz, text=text, width=3, padding=(2, 3),
                       command=cmd).pack(side=tk.LEFT, expand=True,
                                         fill=tk.X, padx=1)
        ttk.Button(self.f_blaetter, text=tr("sb.drucken"),
                   command=app.projekt_drucken).pack(fill=tk.X, pady=(6, 0))
        self._wrap_label(self.f_blaetter, text=tr("sb.hinweis"),
                         style="Hint.TLabel").pack(anchor=tk.W, pady=(6, 0))

        self.aktualisieren()
        self.undo_redo_setzen(self._undo_ok, self._redo_ok)

    def neu_beschriften(self):
        """Nach Sprachwechsel: alles neu aufbauen."""
        self._bauen()

    # ---------------------------------------------------------
    # Zustand
    # ---------------------------------------------------------
    def undo_redo_setzen(self, undo_ok, redo_ok):
        self._undo_ok, self._redo_ok = bool(undo_ok), bool(redo_ok)
        self.btn_undo.state(["!disabled"] if undo_ok else ["disabled"])
        self.btn_redo.state(["!disabled"] if redo_ok else ["disabled"])

    def aktualisieren(self):
        """Blattliste aus app.projekt aktualisieren.

        Gleichbleibende Zeilenzahl: Zeilen werden NUR umbeschriftet (nicht
        neu aufgebaut) - sonst gehen Doppelklicks verloren, weil bereits der
        erste Klick einen Blattwechsel ausloest."""
        p = self.app.projekt
        self._sync = True
        try:
            if p is None:
                for item in self.tree.get_children():
                    self.tree.delete(item)
                self.lbl_projekt.config(text="")
                self.f_blaetter.pack_forget()
                if not self.f_leer.winfo_ismapped():
                    self.f_leer.pack(fill=tk.X)
                return
            self.f_leer.pack_forget()
            if not self.f_blaetter.winfo_ismapped():
                self.f_blaetter.pack(fill=tk.BOTH, expand=True)
            self.lbl_projekt.config(text=p.name)
            vorhanden = self.tree.get_children()
            if len(vorhanden) != len(p.blaetter):
                for item in vorhanden:
                    self.tree.delete(item)
                for i, b in enumerate(p.blaetter):
                    self.tree.insert("", "end", iid=str(i),
                                     values=(p.nummer(i), b.name))
            else:
                for i, b in enumerate(p.blaetter):
                    self.tree.item(str(i), values=(p.nummer(i), b.name))
            if p.blaetter and 0 <= p.aktiv < len(p.blaetter):
                if self.tree.selection() != (str(p.aktiv),):
                    self.tree.selection_set(str(p.aktiv))
                self.tree.focus(str(p.aktiv))
                self.tree.see(str(p.aktiv))
        finally:
            self._sync = False

    # ---------------------------------------------------------
    # Ereignisse
    # ---------------------------------------------------------
    def _gewaehlt(self, event=None):
        if self._sync:
            return
        sel = self.tree.selection()
        if not sel:
            return
        index = int(sel[0])
        p = self.app.projekt
        if p is None or index == p.aktiv:
            return
        if not self.app.blatt_wechseln(index):
            self.aktualisieren()        # Auswahl zuruecksetzen

    def _zeile_unter(self, event):
        iid = self.tree.identify_row(event.y)
        return int(iid) if iid else None

    def _doppelklick(self, event):
        idx = self._zeile_unter(event)
        if idx is not None:
            self.app.blatt_umbenennen(idx)

    def _kontextmenue(self, event):
        idx = self._zeile_unter(event)
        p = self.app.projekt
        if idx is None or p is None:
            return
        if idx != p.aktiv and not self.app.blatt_wechseln(idx):
            return
        m = tk.Menu(self, tearoff=0, bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                    activebackground=FARBEN["cyan"],
                    activeforeground=FARBEN["bg_dunkel"])
        m.add_command(label=tr("sb.kontext.umbenennen"),
                      command=lambda: self.app.blatt_umbenennen())
        m.add_command(label=tr("sb.kontext.neu"), command=self.app.blatt_neu)
        m.add_separator()
        m.add_command(label=tr("sb.kontext.hoch"),
                      command=lambda: self.app.blatt_verschieben(-1))
        m.add_command(label=tr("sb.kontext.runter"),
                      command=lambda: self.app.blatt_verschieben(+1))
        m.add_separator()
        m.add_command(label=tr("sb.kontext.loeschen"),
                      command=self.app.blatt_loeschen)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()
