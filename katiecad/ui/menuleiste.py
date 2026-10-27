# -*- coding: utf-8 -*-
"""
katiecad/ui/menuleiste.py - Own menu bar for Linux/X11 (MIT).

Why: the native Tk menu bar grabs mouse and keyboard. On X11/XWayland
(GNOME) this grab is not honoured: after switching to another application
the open menu stays on screen on top of the foreign window. This menu bar
has no grab; it simply closes when the window loses the focus or when the
user clicks elsewhere.

The menus are still ordinary (never posted) tk.Menu objects used as data
model: this class only reads their entries (label, accelerator, state,
check marks) and calls `menu.invoke(index)`.
"""

import tkinter as tk
import tkinter.font as tkfont


class MenuLeiste(tk.Frame):
    def __init__(self, parent, bg, fg, aktiv_bg, aktiv_fg, sperr_fg="#6b5c8a"):
        super().__init__(parent, bg=bg, bd=0, highlightthickness=0)
        self._bg, self._fg = bg, fg
        self._abg, self._afg = aktiv_bg, aktiv_fg
        self._sperr = sperr_fg
        self._eintraege = []           # [(label_widget, tk.Menu)]
        self._offen = None             # index of the open menu
        self._popup = None
        self._cache = {}               # index -> (popup, zeilen): built once
        self._zeilen = []              # [(row_frame, menu_index, state, widgets)]
        self._aktiv = None             # highlighted row (index into _zeilen)
        try:
            self._font = tkfont.nametofont("TkMenuFont")
        except tk.TclError:
            self._font = tkfont.nametofont("TkDefaultFont")
        top = self.winfo_toplevel()
        top.bind("<FocusOut>", self._fokus_aus, add="+")
        top.bind("<Unmap>", lambda e: self.schliessen(), add="+")
        top.bind("<Configure>", self._fenster_bewegt, add="+")
        top.bind("<F10>", self._f10, add="+")
        top.bind_all("<ButtonPress>", self._klick, add="+")
        top.bind_all("<Key>", self._taste, add="+")

    # ------------------------------------------------------------
    def setze(self, eintraege):
        """eintraege: [(label, tk.Menu)] - rebuilds the bar."""
        self.schliessen()
        for w, _m in self._eintraege:
            w.destroy()
        for pop, _z in self._cache.values():
            try:
                pop.destroy()
            except tk.TclError:
                pass
        self._cache = {}
        self._eintraege = []
        for i, (label, menu) in enumerate(eintraege):
            w = tk.Label(self, text=label, bg=self._bg, fg=self._fg,
                         font=self._font, padx=8, pady=3, bd=0)
            w.pack(side=tk.LEFT)
            w.bind("<Button-1>", lambda e, i=i: self._umschalten(i))
            w.bind("<Enter>", lambda e, i=i: self._ueber(i))
            self._eintraege.append((w, menu))
        self.after(200, self._vorbauen)

    def _vorbauen(self):
        """Builds all drop-downs once in the background (opening is then
        instant); they are only refreshed when opened."""
        for i in range(len(self._eintraege)):
            if i not in self._cache:
                try:
                    self._bauen(i)
                except tk.TclError:
                    return

    def _faerben(self):
        for i, (w, _m) in enumerate(self._eintraege):
            if i == self._offen:
                w.config(bg=self._abg, fg=self._afg)
            else:
                w.config(bg=self._bg, fg=self._fg)

    # ------------------------------------------------------------
    def _umschalten(self, i):
        if self._offen == i:
            self.schliessen()
        else:
            self.oeffnen(i)

    def _ueber(self, i):
        if self._offen is not None and self._offen != i:
            self.oeffnen(i)

    def oeffnen(self, i, tastatur=False):
        self._popup_zerstoeren()
        self._offen = i
        self._faerben()
        w, menu = self._eintraege[i]
        if i not in self._cache:
            self._bauen(i)
        pop, zeilen = self._cache[i]
        self._zeilen = zeilen
        self._aktiv = None
        self._auffrischen(zeilen)
        x = w.winfo_rootx()
        y = w.winfo_rooty() + w.winfo_height()
        br, ho = pop.winfo_reqwidth(), pop.winfo_reqheight()
        sb, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = max(0, min(x, sb - br))
        y = max(0, min(y, sh - ho))
        pop.geometry("+%d+%d" % (x, y))
        pop.deiconify()
        pop.lift()
        self._popup = pop
        if tastatur:
            self._weiter(+1)

    def _bauen(self, i):
        w, menu = self._eintraege[i]
        pop = tk.Toplevel(self)
        pop.withdraw()
        pop.overrideredirect(True)
        try:
            pop.attributes("-topmost", True)
        except tk.TclError:
            pass
        rahmen = tk.Frame(pop, bg=self._fg, bd=0)
        rahmen.pack(fill=tk.BOTH, expand=True)
        innen = tk.Frame(rahmen, bg=self._bg, bd=0)
        innen.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self._zeilen = []
        try:
            ende = menu.index("end")
        except tk.TclError:
            ende = None
        if ende is not None:
            for idx in range(ende + 1):
                self._zeile(innen, menu, idx)
        pop.update_idletasks()
        self._cache[i] = (pop, self._zeilen)
        self._zeilen = []

    def _auffrischen(self, zeilen):
        """Takes over state and check marks of the menu entries."""
        for nr, z in enumerate(zeilen):
            zeile, idx, _alt, (l1, l2, l3), menu = z
            typ = menu.type(idx)
            try:
                state = menu.entrycget(idx, "state")
            except tk.TclError:
                state = "normal"
            marke = ""
            if typ in ("checkbutton", "radiobutton"):
                try:
                    var = menu.entrycget(idx, "variable")
                    wert = menu.tk.globalgetvar(str(var))
                    soll = menu.entrycget(idx, "onvalue" if typ == "checkbutton"
                                          else "value")
                    if str(wert) == str(soll):
                        marke = "\u2713"
                except tk.TclError:
                    pass
            fg = self._fg if state != "disabled" else self._sperr
            for wdg in (zeile, l1, l2, l3):
                wdg.config(bg=self._bg)
            l1.config(text=marke, fg=fg)
            l2.config(fg=fg)
            l3.config(fg=fg)
            zeilen[nr] = (zeile, idx, state, (l1, l2, l3), menu)

    def _zeile(self, innen, menu, idx):
        typ = menu.type(idx)
        if typ == "tearoff":
            return
        if typ == "separator":
            tk.Frame(innen, bg=self._fg, height=1).pack(
                fill=tk.X, padx=2, pady=3)
            return
        try:
            text = menu.entrycget(idx, "label")
        except tk.TclError:
            text = ""
        try:
            accel = menu.entrycget(idx, "accelerator")
        except tk.TclError:
            accel = ""
        try:
            state = menu.entrycget(idx, "state")
        except tk.TclError:
            state = "normal"
        marke = ""
        if typ in ("checkbutton", "radiobutton"):
            try:
                var = menu.entrycget(idx, "variable")
                wert = menu.tk.globalgetvar(str(var))
                soll = menu.entrycget(idx, "onvalue" if typ == "checkbutton"
                                      else "value")
                if str(wert) == str(soll):
                    marke = "✓"
            except tk.TclError:
                pass
        zeile = tk.Frame(innen, bg=self._bg, bd=0)
        zeile.pack(fill=tk.X)
        fg = self._fg if state != "disabled" else self._sperr
        l1 = tk.Label(zeile, text=marke, bg=self._bg, fg=fg, font=self._font,
                      width=2, anchor="w")
        l2 = tk.Label(zeile, text=text, bg=self._bg, fg=fg, font=self._font,
                      anchor="w", padx=2, pady=3)
        l3 = tk.Label(zeile, text=accel + ("  ▸" if typ == "cascade" else ""),
                      bg=self._bg, fg=fg, font=self._font, anchor="e", padx=10)
        l1.pack(side=tk.LEFT)
        l3.pack(side=tk.RIGHT)
        l2.pack(side=tk.LEFT, fill=tk.X, expand=True)
        nr = len(self._zeilen)
        self._zeilen.append((zeile, idx, state, (l1, l2, l3), menu))
        for wdg in (zeile, l1, l2, l3):
            wdg.bind("<Enter>", lambda e, nr=nr: self._markieren(nr))
            wdg.bind("<ButtonRelease-1>", lambda e, nr=nr: self._ausloesen(nr))

    def _markieren(self, nr):
        if self._aktiv is not None and self._aktiv < len(self._zeilen):
            z = self._zeilen[self._aktiv]
            for w in (z[0],) + z[3]:
                w.config(bg=self._bg)
            z[3][0].config(fg=self._fg if z[2] != "disabled" else self._sperr)
            z[3][1].config(fg=self._fg if z[2] != "disabled" else self._sperr)
            z[3][2].config(fg=self._fg if z[2] != "disabled" else self._sperr)
        self._aktiv = nr
        if nr is None:
            return
        z = self._zeilen[nr]
        if z[2] == "disabled":
            return
        for w in (z[0],) + z[3]:
            w.config(bg=self._abg)
        for w in z[3]:
            w.config(fg=self._afg)

    def _ausloesen(self, nr):
        if nr is None or nr >= len(self._zeilen):
            return
        _z, idx, state, _w, menu = self._zeilen[nr]
        if state == "disabled":
            return
        self.schliessen()
        # after closing, so that dialogs are not blocked by the pop-up
        self.after(10, lambda: self._aufrufen(menu, idx))

    @staticmethod
    def _aufrufen(menu, idx):
        try:
            menu.invoke(idx)
        except tk.TclError:
            pass

    # ------------------------------------------------------------
    def _popup_zerstoeren(self):
        if self._popup is not None:
            try:
                self._popup.withdraw()
            except tk.TclError:
                pass
        self._popup = None
        self._zeilen = []
        self._aktiv = None

    def schliessen(self):
        self._popup_zerstoeren()
        if self._offen is not None:
            self._offen = None
            self._faerben()

    def ist_offen(self):
        return self._offen is not None

    # ------------------------------------------------------------
    def _fokus_aus(self, event):
        if self._offen is None or event.widget is not self.winfo_toplevel():
            return
        # focus moves within the application? Then it is not "away".
        self.after(80, self._fokus_pruefen)

    def _fokus_pruefen(self):
        try:
            if self.winfo_toplevel().focus_displayof() is None:
                self.schliessen()
        except tk.TclError:
            pass

    def _fenster_bewegt(self, event):
        if self._offen is None or event.widget is not self.winfo_toplevel():
            return
        self.schliessen()

    def _klick(self, event):
        if self._offen is None:
            return
        w = event.widget
        try:
            while w is not None:
                if w is self._popup or w is self:
                    return
                w = w.master
        except Exception:
            return
        self.schliessen()

    def _f10(self, event=None):
        if self._eintraege and self._offen is None:
            self.oeffnen(0, tastatur=True)
            return "break"

    def _weiter(self, richtung):
        n = len(self._zeilen)
        if not n:
            return
        nr = self._aktiv
        for _ in range(n):
            if nr is None:
                nr = 0 if richtung > 0 else n - 1
            else:
                nr = (nr + richtung) % n
            if self._zeilen[nr][2] != "disabled":
                self._markieren(nr)
                return

    def _taste(self, event):
        if self._offen is None:
            return
        k = event.keysym
        if k == "Escape":
            self.schliessen()
        elif k == "Down":
            self._weiter(+1)
        elif k == "Up":
            self._weiter(-1)
        elif k == "Right":
            self.oeffnen((self._offen + 1) % len(self._eintraege), tastatur=True)
        elif k == "Left":
            self.oeffnen((self._offen - 1) % len(self._eintraege), tastatur=True)
        elif k in ("Return", "KP_Enter"):
            self._ausloesen(self._aktiv)
        else:
            return
        return "break"
