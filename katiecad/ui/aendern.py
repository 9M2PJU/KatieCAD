# -*- coding: utf-8 -*-
"""
katiecad/ui/aendern.py - Change length, align, manipulator (mixin of CadApp).

* LAENGE / LENGTHEN: click a line near one end, then click the new end
  position (projected onto the line) or type the change in mm
  (+5 lengthens, -5 shortens, =50 sets the length to 50).
* AUSRICHTEN / ALIGN: aligns the selected objects to the left/right/top/
  bottom edge or to the centre of the selection.
* MANIP / MANIPULATOR: shows an axis cross on the selection. A drag on the
  X or Y arm moves the objects ONLY along that axis, whatever point the
  object snap picks (only its component along the axis counts). The centre
  square moves freely. Distances can be typed.
"""

import math
import tkinter as tk

from katiecad.common.i18n import tr, SPRACHE
from katiecad.model.core import FARBEN, Linie, UI_SCHRIFT

ARM_PX = 46            # length of a manipulator arm (pixels)
TREFFER_PX = 7         # hit tolerance
MITTE_PX = 6           # half size of the centre square
PIVOT_DX = PIVOT_DY = 18   # pivot handle: offset from the manipulator origin (pixels)


def _de():
    return SPRACHE["aktuell"] == "de"


class AendernMixin:
    # ------------------------------------------------------------
    # Change length
    # ------------------------------------------------------------
    def laenge_start(self):
        if self.aktives_werkzeug.get() != "auswahl":
            self.aktives_werkzeug.set("auswahl")
            self._werkzeug_gewechselt()
        self._laenge = {"el": None}
        self.status.set(tr("msg.laenge.start"))

    def _laenge_ende(self, leise=False):
        if getattr(self, "_laenge", None) is not None:
            self._laenge = None
            self._cmd_pending = None
            self._clear_temp()
            if not leise:
                self.status.set(tr("msg.laenge.ende"))

    def _laenge_klick(self, event):
        L = self._laenge
        if L["el"] is None:
            x, y = self.px_to_mm(event.x, event.y)
            el = self._element_unter_maus(x, y, 8 / self.view["zoom"])
            if not isinstance(el, Linie):
                self.status.set(tr("msg.laenge.nur_linie"))
                return
            d1 = math.hypot(x - el.x1, y - el.y1)
            d2 = math.hypot(x - el.x2, y - el.y2)
            fest, frei = ((el.x2, el.y2), (el.x1, el.y1)) if d1 <= d2 \
                else ((el.x1, el.y1), (el.x2, el.y2))
            laenge = math.hypot(frei[0] - fest[0], frei[1] - fest[1])
            if laenge < 1e-9:
                self.status.set(tr("msg.laenge.nur_linie"))
                return
            L.update(el=el, ende=1 if d1 <= d2 else 2, fest=fest,
                     u=((frei[0] - fest[0]) / laenge, (frei[1] - fest[1]) / laenge),
                     laenge=laenge)
            self.auswahl = [el]
            self._cmd_pending = self._laenge_eingabe
            self.redraw()
            self.status.set(self._laenge_hinweis())
            return
        pt = self._eingabepunkt(event, L["fest"])
        self._laenge_anwenden(self._laenge_aus_punkt(pt))

    def _laenge_hinweis(self):
        f, u = self._einh_faktor(), self.einheit.get()
        return tr("msg.laenge.wert", laenge=f"{self._laenge['laenge'] / f:.3f}", einheit=u)

    def _laenge_aus_punkt(self, pt):
        L = self._laenge
        fx, fy = L["fest"]
        return (pt[0] - fx) * L["u"][0] + (pt[1] - fy) * L["u"][1]

    def _laenge_eingabe(self, text):
        """Typed value: +5 / -5 = change, =50 = new length (in drawing units)."""
        L = getattr(self, "_laenge", None)
        if L is None or L["el"] is None:
            return
        text = text.strip()
        if not text:
            self._cmd_pending = self._laenge_eingabe
            return
        einh = self._einh_faktor()
        try:
            if text.startswith("="):
                neu = self._parse_einzelwert(text[1:], einh)
            else:
                neu = L["laenge"] + self._parse_einzelwert(text, einh)
        except ValueError as e:
            self.status.set(str(e))
            self._cmd_pending = self._laenge_eingabe
            return
        self._laenge_anwenden(neu)

    def _laenge_anwenden(self, neue_laenge):
        L = self._laenge
        if neue_laenge < 1e-6:
            self.status.set(tr("msg.laenge.zu_kurz"))
            self._cmd_pending = self._laenge_eingabe
            return
        el = L["el"]
        fx, fy = L["fest"]
        ex, ey = fx + L["u"][0] * neue_laenge, fy + L["u"][1] * neue_laenge
        self._snapshot()
        if L["ende"] == 1:
            el.x1, el.y1 = ex, ey
        else:
            el.x2, el.y2 = ex, ey
        f, u = self._einh_faktor(), self.einheit.get()
        alt = L["laenge"]
        self._laenge = {"el": None}
        self._cmd_pending = None
        self._clear_temp()
        self.redraw()
        self.status.set(tr("msg.laenge.fertig", alt=f"{alt / f:.3f}",
                           neu=f"{neue_laenge / f:.3f}", einheit=u))

    def _laenge_bewegt(self, event):
        L = self._laenge
        if L["el"] is not None:
            pt = self._eingabepunkt(event, L["fest"])
            neu = self._laenge_aus_punkt(pt)
            self._clear_temp()
            if neu > 1e-6:
                fx, fy = L["fest"]
                ex, ey = fx + L["u"][0] * neu, fy + L["u"][1] * neu
                x1, y1 = self.mm_to_px(fx, fy)
                x2, y2 = self.mm_to_px(ex, ey)
                self.canvas.create_line(x1, y1, x2, y2, fill=FARBEN["gruen"], width=2,
                                        dash=(5, 3), tags="vorschau")
                f, u = self._einh_faktor(), self.einheit.get()
                self.canvas.create_text(
                    x2 + 8, y2 - 10, anchor="w", fill=FARBEN["gelb"],
                    font=(UI_SCHRIFT, 10, "bold"), tags="vorschau",
                    text=f"{neu / f:.3f} {u}  ({(neu - L['laenge']) / f:+.3f})")
        self._fadenkreuz(event.x, event.y)

    # ------------------------------------------------------------
    # Align
    # ------------------------------------------------------------
    @staticmethod
    def ausrichten_delta(boxen, modus):
        """Shifts (dx, dy) per bounding box (xmin, ymin, xmax, ymax) so that
        all boxes align to the edge/centre of the whole selection.
        modus: links | rechts | oben | unten | mitte_h | mitte_v"""
        xmin = min(b[0] for b in boxen); ymin = min(b[1] for b in boxen)
        xmax = max(b[2] for b in boxen); ymax = max(b[3] for b in boxen)
        out = []
        for b in boxen:
            dx = dy = 0.0
            if modus == "links":
                dx = xmin - b[0]
            elif modus == "rechts":
                dx = xmax - b[2]
            elif modus == "mitte_h":
                dx = (xmin + xmax) / 2 - (b[0] + b[2]) / 2
            elif modus == "unten":
                dy = ymin - b[1]
            elif modus == "oben":
                dy = ymax - b[3]
            elif modus == "mitte_v":
                dy = (ymin + ymax) / 2 - (b[1] + b[3]) / 2
            out.append((dx, dy))
        return out

    def ausrichten(self, modus):
        ziele = [e for e in self.auswahl if hasattr(e, "bbox") and hasattr(e, "verschieben")]
        if len(ziele) < 2:
            self.status.set(tr("msg.ausrichten.min2"))
            return
        deltas = self.ausrichten_delta([e.bbox() for e in ziele], modus)
        if not any(abs(dx) > 1e-9 or abs(dy) > 1e-9 for dx, dy in deltas):
            self.status.set(tr("msg.ausrichten.schon"))
            return
        self._snapshot()
        for e, (dx, dy) in zip(ziele, deltas):
            if abs(dx) > 1e-9 or abs(dy) > 1e-9:
                e.verschieben(dx, dy)
        self._einrasten(ziele)
        self.redraw()
        self.status.set(tr("msg.ausrichten.fertig", n=len(ziele)))

    # ------------------------------------------------------------
    # Manipulator
    # ------------------------------------------------------------
    def manipulator_umschalten(self):
        self.manipulator_setzen(not getattr(self, "_manip_an", False))

    def manipulator_setzen(self, an):
        self._manip_an = bool(an)
        try:
            self._manip_var.set(self._manip_an)
        except Exception:
            pass
        self.redraw()
        self.status.set(tr("msg.manip.an" if self._manip_an else "msg.manip.aus"))

    def _manip_zentrum(self):
        boxen = [e.bbox() for e in self.auswahl
                 if hasattr(e, "bbox") and hasattr(e, "verschieben")]
        if not boxen:
            return None
        zx = (min(b[0] for b in boxen) + max(b[2] for b in boxen)) / 2
        zy = (min(b[1] for b in boxen) + max(b[3] for b in boxen)) / 2
        key = tuple(id(e) for e in self.auswahl)
        if key != getattr(self, "_manip_key", None):          # new selection: back to the middle
            self._manip_key = key
            self._manip_off = (0.0, 0.0)
        off = getattr(self, "_manip_off", (0.0, 0.0))
        return (zx + off[0], zy + off[1])

    def manipulator_versetzen(self):
        """Next click sets the manipulator origin anywhere (object snap works)."""
        if not self.auswahl:
            self.status.set(tr("msg.manip.aus"))
            return
        self.manipulator_setzen(True)
        self._manip_pivot_warten = True
        self.status.set(tr("msg.manip.pivot"))

    def manipulator_zentrieren(self):
        self._manip_off = (0.0, 0.0)
        self._manip_pivot_warten = False
        self.redraw()
        self.status.set(tr("msg.manip.pivot_zentriert"))

    def _manip_pivot_klick(self, event):
        """True if the click defined the new manipulator origin."""
        if not getattr(self, "_manip_pivot_warten", False):
            return False
        self._manip_pivot_warten = False
        pt = self._eingabepunkt(event, None)
        z0 = self._manip_zentrum()
        if pt is not None and z0 is not None:
            off = getattr(self, "_manip_off", (0.0, 0.0))
            self._manip_off = (off[0] + pt[0] - z0[0], off[1] + pt[1] - z0[1])
            self.status.set(tr("msg.manip.pivot_ok"))
        self.redraw()
        return True

    def _manip_sichtbar(self):
        return (getattr(self, "_manip_an", False) and self.auswahl
                and self._op is None and self.aktives_werkzeug.get() == "auswahl"
                and not self._ist_layout())

    def _manip_zeichnen(self):
        self.canvas.delete("manip")
        if not self._manip_sichtbar():
            return
        z = self._manip_zentrum()
        if z is None:
            return
        px, py = self.mm_to_px(*z)
        c = self.canvas
        rot, gruen, gelb = "#ff4d4d", "#3ddc84", FARBEN["gelb"]
        c.create_line(px - ARM_PX, py, px + ARM_PX, py, fill=rot, width=2, tags="manip")
        c.create_polygon(px + ARM_PX, py, px + ARM_PX - 9, py - 5, px + ARM_PX - 9, py + 5,
                         fill=rot, outline=rot, tags="manip")
        c.create_line(px, py - ARM_PX, px, py + ARM_PX, fill=gruen, width=2, tags="manip")
        c.create_polygon(px, py - ARM_PX, px - 5, py - ARM_PX + 9, px + 5, py - ARM_PX + 9,
                         fill=gruen, outline=gruen, tags="manip")
        c.create_rectangle(px - MITTE_PX, py - MITTE_PX, px + MITTE_PX, py + MITTE_PX,
                           fill=gelb, outline=FARBEN["bg_dunkel"], tags="manip")
        # pivot handle: click it, then click the new origin
        hx, hy = px + PIVOT_DX, py + PIVOT_DY
        c.create_oval(hx - 6, hy - 6, hx + 6, hy + 6, outline=FARBEN["orange"], width=2, tags="manip")
        c.create_line(hx - 3, hy, hx + 3, hy, fill=FARBEN["orange"], tags="manip")
        c.create_line(hx, hy - 3, hx, hy + 3, fill=FARBEN["orange"], tags="manip")

    def _manip_treffer(self, event):
        """'frei' (centre), 'x', 'y' or None for a click at event."""
        if not self._manip_sichtbar():
            return None
        z = self._manip_zentrum()
        if z is None:
            return None
        px, py = self.mm_to_px(*z)
        dx, dy = event.x - px, event.y - py
        if abs(dx - PIVOT_DX) <= 8 and abs(dy - PIVOT_DY) <= 8:
            return "pivot"
        if abs(dx) <= MITTE_PX and abs(dy) <= MITTE_PX:
            return "frei"
        if abs(dy) <= TREFFER_PX and abs(dx) <= ARM_PX:
            return "x"
        if abs(dx) <= TREFFER_PX and abs(dy) <= ARM_PX:
            return "y"
        return None

    def _manip_klick(self, event):
        """True if the click was taken by the manipulator."""
        art = self._manip_treffer(event)
        if art is None:
            return False
        if art == "pivot":
            self.manipulator_versetzen()
            return True
        z = self._manip_zentrum()
        self._op = {"typ": "move", "stufe": "ziel", "basis": z,
                    "objekte": list(self.auswahl),
                    "achse": art if art in ("x", "y") else None}
        self.letzter_punkt = z
        self._snap_ausschluss = list(self.auswahl)   # no snapping to the moving objects
        self.canvas.delete("manip")
        self._op_hinweis()
        if self._op["achse"]:
            self.status.set(tr("msg.manip.achse_" + art))
        return True

    @staticmethod
    def achse_projektion(basis, pt, achse):
        """Keeps only the component of pt along the axis through basis."""
        if achse == "x":
            return (pt[0], basis[1])
        if achse == "y":
            return (basis[0], pt[1])
        return pt

    def _op_achse(self, pt):
        op = self._op
        if op is not None and op.get("achse") and op.get("basis"):
            return self.achse_projektion(op["basis"], pt, op["achse"])
        return pt

    def _manip_eingabe(self, text, einh):
        """Typed distance along the axis (e.g. 25 or -10). True if handled."""
        op = self._op
        if op is None or not op.get("achse") or op["stufe"] != "ziel":
            return False
        try:
            d = self._parse_einzelwert(text, einh)
        except ValueError:
            return False
        bx, by = op["basis"]
        self._op_klick((bx + d, by) if op["achse"] == "x" else (bx, by + d))
        return True
