# -*- coding: utf-8 -*-
"""
katiecad/ui/widgets.py - Platform-independent controls (Tkinter only).

Why: tk.Button ignores the bg/fg colours on macOS (Aqua) - buttons with a
custom colour scheme simply appear white there. A tk.Label, however,
respects colours on Windows, Linux AND macOS. The classes here are built
on it.
"""

import tkinter as tk

from katiecad.model.core import FARBEN


class FlatButton(tk.Label):
    """Label-based button with hover/pressed state.

    Supports config(text=..., bg=..., fg=..., activebackground=...,
    activeforeground=..., highlightbackground=...) like tk.Button."""

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

    # -- Options like tk.Button -------------------------------------
    def configure(self, cnf=None, **kw):
        if isinstance(cnf, str) or (cnf is None and not kw):
            return super().configure(cnf)          # Query an option
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

    # -- Events --------------------------------------------------
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
    """Clickable colour field (label instead of tk.Button, see module header)."""
    lbl = tk.Label(parent, bg=farbe, width=width, relief=tk.RIDGE, bd=2,
                   highlightthickness=1, cursor="hand2",
                   highlightbackground=FARBEN["cyan"])
    lbl.bind("<Button-1>", lambda e: command())
    return lbl


class Tooltip:
    """Small help text below a widget after the mouse rested on it."""

    def __init__(self, widget, text, verzoegerung=500):
        self.widget, self.text, self.verz = widget, text, verzoegerung
        self._id = None
        self._fenster = None
        widget.bind("<Enter>", self._planen, add="+")
        widget.bind("<Leave>", self._weg, add="+")
        widget.bind("<ButtonPress>", self._weg, add="+")

    def _planen(self, _e=None):
        self._weg()
        self._id = self.widget.after(self.verz, self._zeigen)

    def _zeigen(self):
        self._id = None
        if self._fenster is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 4
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            w = tk.Toplevel(self.widget)
            w.wm_overrideredirect(True)
            w.wm_geometry("+%d+%d" % (x, y))
            tk.Label(w, text=self.text, bg=FARBEN["bg_hell"], fg=FARBEN["text_hell"],
                     bd=0, padx=7, pady=3, highlightthickness=1,
                     highlightbackground=FARBEN["cyan_dunkel"]).pack()
            self._fenster = w
        except tk.TclError:
            self._fenster = None

    def _weg(self, _e=None):
        if self._id is not None:
            try:
                self.widget.after_cancel(self._id)
            except tk.TclError:
                pass
            self._id = None
        if self._fenster is not None:
            try:
                self._fenster.destroy()
            except tk.TclError:
                pass
            self._fenster = None
