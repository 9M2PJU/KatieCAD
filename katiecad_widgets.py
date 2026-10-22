# -*- coding: utf-8 -*-
"""
katiecad_widgets.py - Plattformunabhaengige Bedienelemente (nur Tkinter).

Warum: tk.Button ignoriert unter macOS (Aqua) die Farben bg/fg - Knoepfe mit
eigenem Farbschema erscheinen dort einfach weiss. Ein tk.Label dagegen
respektiert Farben auf Windows, Linux UND macOS. Die Klassen hier bauen
darauf auf.
"""

import tkinter as tk

from katiecad_core import FARBEN


class FlatButton(tk.Label):
    """Knopf auf Label-Basis mit Hover-/Druck-Zustand.

    Unterstuetzt config(text=..., bg=..., fg=..., activebackground=...,
    activeforeground=..., highlightbackground=...) wie tk.Button."""

    def __init__(self, parent, text="", command=None, padx=10, pady=4,
                 font=None, **kw):
        self._bg = kw.pop("bg", FARBEN["bg_hell"])
        self._fg = kw.pop("fg", FARBEN["text"])
        self._abg = kw.pop("activebackground", FARBEN["bg_hover"])
        self._afg = kw.pop("activeforeground", FARBEN["cyan"])
        self._command = command
        self._hover = False
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", FARBEN["rand"])
        super().__init__(parent, text=text, bg=self._bg, fg=self._fg,
                         padx=padx, pady=pady, font=font, cursor="hand2",
                         relief=tk.FLAT, bd=0, **kw)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)

    # -- Optionen wie tk.Button -------------------------------------
    def configure(self, cnf=None, **kw):
        if isinstance(cnf, str) or (cnf is None and not kw):
            return super().configure(cnf)          # Abfrage einer Option
        if cnf:
            kw = {**cnf, **kw}
        if "bg" in kw:
            self._bg = kw["bg"]
        if "background" in kw:
            self._bg = kw["background"]
        if "fg" in kw:
            self._fg = kw["fg"]
        if "foreground" in kw:
            self._fg = kw["foreground"]
        if "activebackground" in kw:
            self._abg = kw.pop("activebackground")
        if "activeforeground" in kw:
            self._afg = kw.pop("activeforeground")
        if "command" in kw:
            self._command = kw.pop("command")
        super().configure(**kw)
        self._anwenden()

    config = configure

    def _anwenden(self):
        if self._hover:
            tk.Label.configure(self, bg=self._abg, fg=self._afg)
        else:
            tk.Label.configure(self, bg=self._bg, fg=self._fg)

    # -- Ereignisse --------------------------------------------------
    def _enter(self, _e=None):
        self._hover = True
        self._anwenden()

    def _leave(self, _e=None):
        self._hover = False
        self._anwenden()
        tk.Label.configure(self, relief=tk.FLAT)

    def _press(self, _e=None):
        tk.Label.configure(self, relief=tk.SUNKEN)

    def _release(self, e=None):
        tk.Label.configure(self, relief=tk.FLAT)
        if e is not None and 0 <= e.x <= self.winfo_width() \
                and 0 <= e.y <= self.winfo_height() and self._command:
            self._command()

    def invoke(self):
        if self._command:
            self._command()


def farb_swatch(parent, farbe, command, width=4):
    """Anklickbares Farbfeld (Label statt tk.Button, siehe Modulkopf)."""
    lbl = tk.Label(parent, bg=farbe, width=width, relief=tk.RIDGE, bd=2,
                   highlightthickness=1, cursor="hand2",
                   highlightbackground=FARBEN["cyan"])
    lbl.bind("<Button-1>", lambda e: command())
    return lbl
