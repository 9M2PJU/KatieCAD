# -*- coding: utf-8 -*-
"""
katiecad_app.py - GUI von KatieCAD (CadApp, main()).
Enthaelt die Tkinter-UI, Events, Werkzeuge und den App-State.
Dialoge liegen in katiecad_dialogs.py, PDF-Ausgabe in katiecad_pdf.py.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import math, json, re
import os, sys, tempfile, subprocess
import tkinter.font as tkfont

try:
    import ezdxf
    EZDXF_VERFUEGBAR = True
except ImportError:
    EZDXF_VERFUEGBAR = False

try:
    import ezdwg
    EZDWG_VERFUEGBAR = True
except ImportError:
    EZDWG_VERFUEGBAR = False

try:
    from PIL import Image, ImageTk
    PILLOW_VERFUEGBAR = True
except ImportError:
    PILLOW_VERFUEGBAR = False

from katiecad_i18n import tr, SPRACHE, setze_sprache, TEXTE
from katiecad_config import lade_konfiguration, speichere_sprache
from katiecad_core import (
    FARBEN, EINHEITEN, ZEICHNUNGSFORMATE, MASSSTAEBE, LINIENTYPEN,
    RASTER_GROESSEN, BG_PRESETS, SCHRIFTARTEN, LINIENSTAERKEN,
    GRIFF_RADIUS, MIN_VP_GROESSE, PASTE_OFFSET_MM,
    TEXT_BREITE, TEXT_ZEILE, CAD_VERSALHOEHE, LW_PX_FAKTOR, BEM_RICHTUNGEN,
    BEFEHLE, PdfSeite, ist_dunkel,
    Layer, Layout, Element, Linie, Kreis, Bogen, Rechteck, Polylinie, Text,
    Bemassung, Viewport,
    bogen_sweep, bogen_punkte, winkel_im_bogen, bogen_aus_3_punkten,
    bogen_mitte_start_ende, abstand_punkt_segment, naechster_punkt_segment,
    clip_polyline, gedrehtes_rechteck, punkt_in_gedrehtem_rechteck,
    bem_zahl, parse_massstab, massstab_text, normmassstab_unter,
    lot_fuss, linien_schnitt, bbox_enthalten, bbox_ueberlappt,
    punkte_drehen,
)
from katiecad_dialogs import (
    MIT_LICENSE_TEXT, zeige_lizenz_fenster,
    _LayoutNameDialog, PropertiesDialog, ViewportDialog,
    LayerDialog, LayerEditDialog, TextDialog, ArrayDialog, DruckDialog,
)
from katiecad_pdf import pdf_erzeugen, pdf_senden


# ============================================================
# Style-Setup (tkinter-abhängig, daher hier)
# ============================================================
def _style_setup(root):
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except Exception:
        pass

    st.configure("TFrame", background=FARBEN["bg_mittel"])
    st.configure("TLabel", background=FARBEN["bg_mittel"],
                 foreground=FARBEN["text"], font=("Segoe UI", 9))
    st.configure("Title.TLabel", background=FARBEN["bg_mittel"],
                 foreground=FARBEN["cyan"], font=("Segoe UI", 9, "bold"))
    st.configure("Hint.TLabel", background=FARBEN["bg_mittel"],
                 foreground=FARBEN["cyan"], font=("Segoe UI", 9, "italic"))

    st.configure("TButton",
                 background=FARBEN["bg_hell"],
                 foreground=FARBEN["cyan"],
                 borderwidth=1, focusthickness=0,
                 font=("Segoe UI", 9, "bold"),
                 padding=(8, 4))
    st.map("TButton",
           background=[("active", FARBEN["bg_hover"]),
                       ("pressed", FARBEN["cyan_dunkel"])],
           foreground=[("active", FARBEN["text_hell"])])

    st.configure("TRadiobutton",
                 background=FARBEN["bg_mittel"],
                 foreground=FARBEN["text"],
                 font=("Segoe UI", 9))
    st.map("TRadiobutton",
           background=[("active", FARBEN["bg_mittel"])],
           foreground=[("active", FARBEN["cyan"]),
                       ("selected", FARBEN["cyan"])])

    st.configure("TCheckbutton",
                 background=FARBEN["bg_mittel"],
                 foreground=FARBEN["text"],
                 font=("Segoe UI", 9))
    st.map("TCheckbutton",
           background=[("active", FARBEN["bg_mittel"])],
           foreground=[("active", FARBEN["cyan"]),
                       ("selected", FARBEN["cyan"])])

    st.configure("TEntry",
                 fieldbackground=FARBEN["bg_hell"],
                 foreground=FARBEN["cyan"],
                 insertcolor=FARBEN["cyan"],
                 bordercolor=FARBEN["rand"])
    st.map("TEntry",
           fieldbackground=[("focus", FARBEN["bg_hover"])])

    st.configure("TCombobox",
                 fieldbackground=FARBEN["bg_hell"],
                 background=FARBEN["bg_hell"],
                 foreground=FARBEN["cyan"],
                 arrowcolor=FARBEN["cyan"],
                 bordercolor=FARBEN["rand"])
    st.map("TCombobox",
           fieldbackground=[("readonly", FARBEN["bg_hell"])],
           foreground=[("readonly", FARBEN["cyan"])])

    st.configure("TSpinbox",
                 fieldbackground=FARBEN["bg_hell"],
                 background=FARBEN["bg_hell"],
                 foreground=FARBEN["cyan"],
                 arrowcolor=FARBEN["cyan"],
                 bordercolor=FARBEN["rand"])

    st.configure("TSeparator", background=FARBEN["rand"])
    st.configure("Treeview",
                 background=FARBEN["bg_hell"],
                 fieldbackground=FARBEN["bg_hell"],
                 foreground=FARBEN["text"],
                 bordercolor=FARBEN["rand"],
                 rowheight=22)
    st.configure("Treeview.Heading",
                 background=FARBEN["bg_mittel"],
                 foreground=FARBEN["cyan"],
                 font=("Segoe UI", 9, "bold"))
    st.map("Treeview",
           background=[("selected", FARBEN["select_bg"])],
           foreground=[("selected", FARBEN["select_fg"])])


# ============================================================
# Hauptanwendung
# ============================================================
class CadApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KatieCAD")
        self.root.geometry("1500x950")
        self.root.configure(bg=FARBEN["bg_dunkel"])

        # --- Sprache aus persistenter Konfiguration laden (vor UI-Aufbau!) ---
        _cfg = lade_konfiguration()
        setze_sprache(_cfg.get("sprache", "en"))

        # Selbstcheck: sind alle im Manifest gelisteten Module da?
        try:
            from katiecad_manifest import fehlende_module, VERSION
            fehlend = fehlende_module()
            if fehlend:
                print(f"[KatieCAD] ACHTUNG – fehlende Module: {fehlend}")
            else:
                print(f"[KatieCAD] Version {VERSION} – alle Module vorhanden.")
        except Exception as e:
            print(f"[KatieCAD] Manifest-Check übersprungen: {e}")

        _style_setup(root)

        self.layers = {
            "0": Layer("0", "#c29bff", 0.35),
            "Konstruktion": Layer("Konstruktion", "#b886fb", 0.25),
            "Bemaßung": Layer("Bemaßung", "#ff2d95", 0.25),
            "Schrift": Layer("Schrift", "#d8d0e8", 0.35),
            "Verdeckt": Layer("Verdeckt", "#8b7ea8", 0.25),
        }
        self.aktiver_layer = tk.StringVar(value="0")

        self.elemente = []

        self.layouts = [Layout("Layout1", Layout.STANDARD_FORMAT,
                               "#1c132d")]
        self.aktives_layout = 0
        self.ansicht = tk.StringVar(value="modell")

        self.aktives_werkzeug = tk.StringVar(value="auswahl")
        self.einheit = tk.StringVar(value="mm")
        self.massstab = tk.StringVar(value="1:1")
        self.linientyp = tk.StringVar(value="Volllinie (schmal)")
        self.linienstaerke = tk.DoubleVar(value=0.35)
        self.zeichenfarbe = FARBEN["cyan"]
        self.eigene_farbe = tk.BooleanVar(value=True)

        self.kreis_modus = tk.StringVar(value="radius")

        self.text_hoehe = tk.DoubleVar(value=3.5)
        self.text_winkel = tk.DoubleVar(value=0.0)
        self.text_schriftart = tk.StringVar(value="Arial")

        self.bg_modell = "#120a1f"

        self.view_modell = {"zoom": 1.5, "ox": 100, "oy": 700}

        self.osnap = tk.BooleanVar(value=True)
        self.grid_snap = tk.BooleanVar(value=True)
        self.ortho = tk.BooleanVar(value=False)
        self.raster_sichtbar = tk.BooleanVar(value=True)
        self.raster_punktiert = tk.BooleanVar(value=True)
        self.raster_mm = tk.DoubleVar(value=5.0)
        self.fang_mm = tk.DoubleVar(value=5.0)
        self.osnap_modi = {
            "endpunkt":  tk.BooleanVar(value=True),
            "mittelpunkt": tk.BooleanVar(value=True),
            "zentrum":   tk.BooleanVar(value=True),
            "schnittpunkt": tk.BooleanVar(value=True),
            "quadrant":  tk.BooleanVar(value=True),
            "lot":       tk.BooleanVar(value=True),
            "naechster": tk.BooleanVar(value=False),
        }

        self.pan_start = None
        self.letzter_punkt = None
        self.temp_ids = []
        self.aktuelle_polylinie = []
        self._viewport_modus = False

        self._snap_punkt_aktuell = None
        self._maus_px = (0, 0)

        self.eingabe_var = tk.StringVar()
        self.status = tk.StringVar()

        self._layout_buttons = {}

        self.auswahl = []
        self._auswahl_rechteck_start = None
        self._auswahl_rechteck_id = None
        self._auswahl_richtung = None
        self._drag_modus = None

        self._text_drag_el = None
        self._text_drag_start = None
        self._masslinie_drag_el = None
        self._masslinie_drag_start = None

        self._vp_pan_start = None
        self._aktiver_viewport = None

        self._vp_aktion = "none"
        self._vp_el = None
        self._vp_ecke = None
        self._vp_start_mm = None
        self._vp_start_rect = None

        self._undo_stack = []
        self._undo_max = 50

        self._clipboard = []
        self._clipboard_basispunkt = None
        self._clipboard_mit_basis = False

        self._paste_aktiv = False
        self._paste_vorlagen = []
        self._paste_bezug = (0.0, 0.0)
        self._paste_vorschau_ids = []
        self._paste_maus_mm = (0.0, 0.0)

        self._bem_status = "none"
        self._bem_p1 = None
        self._bem_p2 = None

        self._bogen_status = "none"
        self._bogen_start = None
        self._bogen_ende = None

        self._griff_drag_el = None
        self._griff_drag_id = None
        self._griff_drag_original = None

        self._dirty = False

        self.lw_anzeigen = tk.BooleanVar(value=True)
        self.bogen_modus = tk.StringVar(value="mitte")
        self.bogen_richtung = tk.StringVar(value="auto")
        self.bem_art = tk.StringVar(value="auto")
        self.bem_hoehe = tk.DoubleVar(value=2.5)
        self.bem_pfeil = tk.DoubleVar(value=2.5)
        self.bem_dez = tk.IntVar(value=2)
        # Dezimalkomma passend zur geladenen Sprache initialisieren
        self.dezimalkomma = tk.BooleanVar(value=(SPRACHE["aktuell"] == "de"))
        self._pts = []
        self._bem_kreis = None
        self._snap_ausschluss = None
        self._font_cache = {}
        self._vp_fenster = None
        self._vp_fenster_norm = False
        self._vp_letzter_pt = None
        self._op = None
        self._cmd_pending = None
        self._rc_start = None
        self._rc_bewegt = False

        self._stretch_rechteck_start = None
        self._stretch_rechteck_id = None

        self._warte_auf_basispunkt = False

        self.sprache_var = tk.StringVar(value=SPRACHE["aktuell"])

        self._info_logo = None

        # --- Viewport-Leiste: Statusvariablen ---
        self._vp_modus_var = tk.StringVar(value="layout")
        self._vp_massstab_var = tk.StringVar(value="1:1")
        self._vp_sperre_var = tk.BooleanVar(value=False)
        self._vp_status_var = tk.StringVar(value="")

        self._build_ui()
        self._bind_events()
        self._zeichne_raster()

        self._build_koord_bar()

        self.root.protocol("WM_DELETE_WINDOW", self.beenden)

    # --------------------------------------------------------
    # Properties
    # --------------------------------------------------------
    @property
    def layout(self):
        return self.layouts[self.aktives_layout]

    @property
    def layout_elemente(self):
        return self.layouts[self.aktives_layout].elemente

    @layout_elemente.setter
    def layout_elemente(self, wert):
        self.layouts[self.aktives_layout].elemente = wert

    @property
    def layout_format(self):
        return self.layouts[self.aktives_layout].format

    @layout_format.setter
    def layout_format(self, wert):
        self.layouts[self.aktives_layout].format = wert

    @property
    def bg_layout(self):
        return self.layouts[self.aktives_layout].bg

    @bg_layout.setter
    def bg_layout(self, wert):
        self.layouts[self.aktives_layout].bg = wert

    @property
    def view(self):
        if not self._ist_layout():
            return self.view_modell
        return self.layouts[self.aktives_layout].view

    def _ist_layout(self):
        return self.ansicht.get().startswith("layout")

    def _layout_index(self):
        s = self.ansicht.get()
        if s.startswith("layout:"):
            try:
                return int(s.split(":", 1)[1])
            except (ValueError, IndexError):
                return 0
        return 0

    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True
            self._update_titel()

    def _mark_clean(self):
        self._dirty = False
        self._update_titel()

    def _update_titel(self):
        basis = "KatieCAD"
        if self._dirty:
            self.root.title(f"{basis} *")
        else:
            self.root.title(basis)

    def beenden(self):
        if self._dirty:
            antwort = messagebox.askyesnocancel(
                tr("msg.beenden_titel"), tr("msg.beenden_frage"))
            if antwort is None:
                return
            if antwort:
                if not self.speichern():
                    return
        self.root.destroy()

    # --------------------------------------------------------
    # Sprachumschaltung
    # --------------------------------------------------------
    def sprache_wechseln(self, code):
        if code not in TEXTE or code == SPRACHE["aktuell"]:
            return
        setze_sprache(code)
        speichere_sprache(code)
        self.sprache_var.set(code)
        if code == "en":
            self.dezimalkomma.set(False)
        else:
            self.dezimalkomma.set(True)
        self._retranslate_ui()

    def _retranslate_ui(self):
        self._build_menu()
        self._build_toolbars()
        self._retranslate_eingabeleiste()
        self._retranslate_statusbar()
        self._aktualisiere_osnap_anzeige()
        self._update_kontext_widgets()
        self._update_eingabe_hinweis()
        self._layout_switcher_neu_aufbauen()
        self._retranslate_viewport_leiste()
        self._viewport_modus_anzeige_aktualisieren()
        self.redraw()

    # --------------------------------------------------------
    # Undo
    # --------------------------------------------------------
    def _snapshot(self):
        try:
            self._undo_stack.append(self._zustand())
            if len(self._undo_stack) > self._undo_max:
                self._undo_stack.pop(0)
            self._mark_dirty()
        except Exception as e:
            print(f"Snapshot-Fehler: {e}")

    def undo(self):
        if not self._undo_stack:
            self.status.set("Nichts rueckgaengig zu machen.")
            return
        snap = self._undo_stack.pop()
        try:
            self.elemente = []
            for d in snap.get("elemente", []):
                el = self._dict_zu_element(d)
                if el:
                    self.elemente.append(el)
            layouts_daten = snap.get("layouts")
            if layouts_daten is not None:
                neue = []
                for ld in layouts_daten:
                    lay = Layout.from_dict(ld, self._dict_zu_element)
                    neue.append(lay)
                if neue:
                    self.layouts = neue
                else:
                    self.layouts = [Layout("Layout1", Layout.STANDARD_FORMAT,
                                           "#1c132d")]
                if self.aktives_layout >= len(self.layouts):
                    self.aktives_layout = len(self.layouts) - 1
                if self._ist_layout():
                    idx = self._layout_index()
                    if idx >= len(self.layouts):
                        idx = len(self.layouts) - 1
                        self.aktives_layout = idx
                        self.ansicht.set(f"layout:{idx}")
            else:
                self.layouts = [Layout("Layout1", Layout.STANDARD_FORMAT,
                                       "#1c132d")]
                self.aktives_layout = 0
                for d in snap.get("layout_elemente", []):
                    el = self._dict_zu_element(d)
                    if el:
                        self.layouts[0].elemente.append(el)
            for ld in snap.get("layers", []):
                self.layers[ld["name"]] = Layer(ld["name"],
                                                ld.get("farbe", "#c29bff"),
                                                ld.get("staerke", 0.35),
                                                ld.get("sichtbar", True))
            self.layer_cb.config(values=list(self.layers.keys()))
            self.auswahl = []
            self._aktiver_viewport = None
            self._vp_aktion = "none"
            self._vp_el = None
            self._paste_abbrechen()
            self._bem_abbrechen()
            self._bogen_abbrechen()
            self._layout_switcher_neu_aufbauen()
            self._viewport_modus_anzeige_aktualisieren()
            self._mark_dirty()
            self.redraw()
            self.status.set("Rueckgaengig gemacht.")
        except Exception as e:
            print(f"Undo-Fehler: {e}")

    # --------------------------------------------------------
    # Copy / Paste
    # --------------------------------------------------------
    def kopieren(self, event=None):
        if not self.auswahl:
            self.status.set(tr("msg.nichts_kopieren"))
            return "break"
        self._clipboard = [el.to_dict() for el in self.auswahl]
        self._clipboard_basispunkt = None
        self._clipboard_mit_basis = False
        de = SPRACHE["aktuell"] == "de"
        self.status.set(f"{len(self._clipboard)} " +
                        ("Element(e) kopiert. Strg+V zum Einfügen (Basispunkt = "
                         "linke untere Ecke)." if de else
                         "element(s) copied. Ctrl+V to paste (base point = "
                         "lower-left corner)."))
        return "break"

    def kopieren_mit_basispunkt(self, event=None):
        self._op_start("copybase")
        return "break"

    def _basispunkt_setzen(self, x_mm, y_mm):
        self._clipboard_basispunkt = (x_mm, y_mm)
        self._warte_auf_basispunkt = False
        de = SPRACHE["aktuell"] == "de"
        self.status.set(
            (f"Basispunkt gesetzt auf ({x_mm:.2f}, {y_mm:.2f}) mm. "
             "Strg+V zum Einfügen." if de else
             f"Base point set to ({x_mm:.2f}, {y_mm:.2f}) mm. "
             "Ctrl+V to paste."))

    def ausschneiden(self, event=None):
        if not self.auswahl:
            self.status.set(tr("msg.nichts_loeschen"))
            return "break"
        self._clipboard = [el.to_dict() for el in self.auswahl]
        self._clipboard_basispunkt = None
        self._clipboard_mit_basis = False
        self.auswahl_loeschen()
        de = SPRACHE["aktuell"] == "de"
        self.status.set(f"{len(self._clipboard)} " +
                        ("Element(e) ausgeschnitten. Strg+V zum Einfügen." if de
                         else "element(s) cut. Ctrl+V to paste."))
        return "break"

    def einfuegen(self, event=None):
        if self._paste_aktiv:
            self._paste_abbrechen()
        if not self._clipboard:
            self.status.set(tr("msg.zwischenablage_leer"))
            return "break"
        self._paste_vorlagen = []
        for d in self._clipboard:
            el = self._dict_zu_element(dict(d))
            if el is not None:
                self._paste_vorlagen.append(el)
        if not self._paste_vorlagen:
            self.status.set(tr("msg.zwischenablage_leer"))
            return "break"
        if self._clipboard_mit_basis and self._clipboard_basispunkt is not None:
            self._paste_bezug = self._clipboard_basispunkt
        else:
            xs, ys = [], []
            for el in self._paste_vorlagen:
                b = el.bbox()
                xs.extend([b[0], b[2]])
                ys.extend([b[1], b[3]])
            self._paste_bezug = (min(xs), min(ys)) if xs else (0.0, 0.0)
        self._paste_aktiv = True
        self.auswahl = []
        de = SPRACHE["aktuell"] == "de"
        self.status.set("Einfügen: Maus bewegen, Klick = platzieren, ESC = abbrechen."
                        if de else
                        "Paste: move mouse, click = place, ESC = cancel.")
        self._paste_vorschau_aktualisieren(self._maus_px[0], self._maus_px[1])
        return "break"

    def duplizieren(self, event=None):
        if not self.auswahl:
            self.status.set(tr("msg.nichts_kopieren"))
            return "break"
        self._snapshot()
        ziel_liste = self._aktuelle_elemente_liste()
        neue_el = []
        for el in self.auswahl:
            klon = self._dict_zu_element(el.to_dict())
            if klon is None:
                continue
            klon.verschieben(PASTE_OFFSET_MM, -PASTE_OFFSET_MM)
            ziel_liste.append(klon)
            neue_el.append(klon)
        self.auswahl = neue_el
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        self.status.set(f"{len(neue_el)} " +
                        (f"Element(e) dupliziert (Versatz {PASTE_OFFSET_MM} mm)."
                         if de else
                         f"element(s) duplicated (offset {PASTE_OFFSET_MM} mm)."))
        return "break"

    def _paste_abbrechen(self):
        self._paste_aktiv = False
        self._paste_vorlagen = []
        self._paste_bezug = (0.0, 0.0)
        for i in self._paste_vorschau_ids:
            self.canvas.delete(i)
        self._paste_vorschau_ids = []
        self.canvas.delete("paste_vorschau")

    def _paste_platzieren(self):
        if not self._paste_aktiv or not self._paste_vorlagen:
            return
        ziel_mm = self._paste_maus_mm or (0.0, 0.0)
        dx = ziel_mm[0] - self._paste_bezug[0]
        dy = ziel_mm[1] - self._paste_bezug[1]
        self._snapshot()
        ziel_liste = self._aktuelle_elemente_liste()
        neue_el = []
        for vorlage in self._paste_vorlagen:
            klon = self._dict_zu_element(vorlage.to_dict())
            if klon is None:
                continue
            klon.verschieben(dx, dy)
            ziel_liste.append(klon)
            neue_el.append(klon)
        self.auswahl = neue_el
        n = len(neue_el)
        self._paste_abbrechen()
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        self.status.set(f"{n} " +
                        (f"Element(e) platziert an ({ziel_mm[0]:.2f}, "
                         f"{ziel_mm[1]:.2f}) mm." if de else
                         f"element(s) placed at ({ziel_mm[0]:.2f}, "
                         f"{ziel_mm[1]:.2f}) mm."))

    def _paste_vorschau_aktualisieren(self, maus_px_x, maus_px_y):
        if not self._paste_aktiv or not self._paste_vorlagen:
            return
        x, y = self._eingabepunkt_px(maus_px_x, maus_px_y, None)
        self._paste_maus_mm = (x, y)
        dx = x - self._paste_bezug[0]
        dy = y - self._paste_bezug[1]
        self.canvas.delete("paste_vorschau")
        stil = {"farbe": FARBEN["gruen"], "w": 2, "dash": (5, 3)}
        for vorlage in self._paste_vorlagen:
            klon = self._dict_zu_element(vorlage.to_dict())
            if klon is None:
                continue
            klon.verschieben(dx, dy)
            if isinstance(klon, Viewport):
                x1, y1 = self.mm_to_px(klon.x, klon.y + klon.hoehe)
                x2, y2 = self.mm_to_px(klon.x + klon.breite, klon.y)
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=FARBEN["gruen"],
                                             width=2, dash=(5, 3), tags="paste_vorschau")
            else:
                self._zeichne_element(klon, tags=("paste_vorschau",),
                                      tf=self._ctx_zu_px, skala=self._ctx_skala(),
                                      stil=stil)
        px, py = self._ctx_zu_px(x, y)
        c = self.canvas
        c.create_oval(px - 5, py - 5, px + 5, py + 5, outline=FARBEN["orange"],
                      width=2, tags="paste_vorschau")
        c.create_line(px - 10, py, px + 10, py, fill=FARBEN["orange"], tags="paste_vorschau")
        c.create_line(px, py - 10, px, py + 10, fill=FARBEN["orange"], tags="paste_vorschau")

    # --------------------------------------------------------
    def _bem_abbrechen(self):
        self._op = None
        self._cmd_pending = None
        self._pts = []
        self._bem_kreis = None
        self._clear_temp()

    def _bogen_abbrechen(self):
        self._pts = []
        self._clear_temp()

    # --------------------------------------------------------
    # UI-Aufbau
    # --------------------------------------------------------
    def _build_ui(self):
        self._build_menu()
        self.tb1 = ttk.Frame(self.root, padding=4)
        self.tb1.pack(side=tk.TOP, fill=tk.X)
        self.tb2 = ttk.Frame(self.root, padding=4)
        self.tb2.pack(side=tk.TOP, fill=tk.X)
        self.tb3 = ttk.Frame(self.root, padding=4)
        self.tb3.pack(side=tk.TOP, fill=tk.X)
        self._build_toolbars()
        self._build_eingabeleiste()
        self._build_layout_switcher()
        self._build_statusbar()

        self.canvas = tk.Canvas(self.root, bg=self.bg_modell,
                                highlightthickness=1,
                                highlightbackground=FARBEN["rand"],
                                cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Viewport-Leiste bauen (nach dem Canvas, damit before=self.canvas klappt)
        self._build_viewport_leiste()

        self._update_kontext_widgets()
        self._viewport_modus_anzeige_aktualisieren()

    def _build_koord_bar(self):
        koord_bar = tk.Label(self.root, textvariable=self.status,
                             relief=tk.SUNKEN, anchor=tk.W,
                             padx=6, pady=4,
                             bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                             font=("Consolas", 9))
        koord_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_menu(self):
        menubar = tk.Menu(self.root,
                          bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                          activebackground=FARBEN["cyan"],
                          activeforeground=FARBEN["bg_dunkel"], bd=0)

        # Datei
        m_datei = tk.Menu(menubar, tearoff=0,
                          bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                          activebackground=FARBEN["cyan"],
                          activeforeground=FARBEN["bg_dunkel"])
        m_datei.add_command(label=tr("menu.datei.neu"), command=self.neu)
        m_datei.add_command(label=tr("menu.datei.oeffnen"), command=self.oeffnen)
        m_datei.add_command(label=tr("menu.datei.speichern"), command=self.speichern,
                            accelerator="Strg+S" if SPRACHE["aktuell"] == "de" else "Ctrl+S")
        m_datei.add_separator()
        m_datei.add_command(label=tr("menu.datei.import_dxf"), command=self.import_dxf)
        m_datei.add_command(label=tr("menu.datei.import_dwg"), command=self.import_dwg)
        m_datei.add_command(label=tr("menu.datei.export_dxf"), command=self.export_dxf)
        m_datei.add_separator()
        m_datei.add_command(label=tr("menu.datei.drucken"), command=self.drucken)
        m_datei.add_separator()
        m_datei.add_command(label=tr("menu.datei.beenden"), command=self.beenden)
        menubar.add_cascade(label=tr("menu.datei"), menu=m_datei)

        # Bearbeiten
        m_bearb = tk.Menu(menubar, tearoff=0,
                          bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                          activebackground=FARBEN["cyan"],
                          activeforeground=FARBEN["bg_dunkel"])
        m_bearb.add_command(label=tr("menu.bearbeiten.undo"), command=self.undo)
        m_bearb.add_separator()
        m_bearb.add_command(label=tr("menu.bearbeiten.kopieren"), command=self.kopieren)
        m_bearb.add_command(label=tr("menu.bearbeiten.kopieren_basis"),
                            command=self.kopieren_mit_basispunkt)
        m_bearb.add_command(label=tr("menu.bearbeiten.ausschneiden"), command=self.ausschneiden)
        m_bearb.add_command(label=tr("menu.bearbeiten.einfuegen"), command=self.einfuegen)
        m_bearb.add_command(label=tr("menu.bearbeiten.duplizieren"), command=self.duplizieren)
        m_bearb.add_separator()
        m_bearb.add_command(label=tr("menu.bearbeiten.verschieben"),
                            command=lambda: self._op_start("move"))
        m_bearb.add_command(label=tr("menu.bearbeiten.kopieren_praezise"),
                            command=lambda: self._op_start("copy"))
        m_bearb.add_command(label=tr("menu.bearbeiten.reihe"),
                            command=lambda: self._op_start("array"))
        m_bearb.add_command(label=tr("menu.bearbeiten.drehen"),
                            command=lambda: self._op_start("rotate"))
        m_bearb.add_command(label=tr("menu.bearbeiten.strecken"),
                            command=lambda: self._op_start("stretch"))
        m_bearb.add_separator()
        m_bearb.add_command(label=tr("menu.bearbeiten.alles_loeschen"), command=self.neu)
        m_bearb.add_separator()
        m_bearb.add_command(label=tr("menu.bearbeiten.auswahl_loeschen"),
                            command=self.auswahl_loeschen)
        m_bearb.add_command(label=tr("menu.bearbeiten.alles_markieren"),
                            command=self.alle_markieren)
        menubar.add_cascade(label=tr("menu.bearbeiten"), menu=m_bearb)

        # Einfügen
        m_einf = tk.Menu(menubar, tearoff=0,
                         bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                         activebackground=FARBEN["cyan"],
                         activeforeground=FARBEN["bg_dunkel"])
        m_einf.add_command(label=tr("menu.einfuegen.auswahl"),
                           command=lambda: self._werkzeug_aus_menue("auswahl"))
        m_einf.add_separator()
        m_einf.add_command(label=tr("menu.einfuegen.linie"),
                           command=lambda: self._werkzeug_aus_menue("linie"))
        m_einf.add_command(label=tr("menu.einfuegen.polylinie"),
                           command=lambda: self._werkzeug_aus_menue("polylinie"))
        m_einf.add_command(label=tr("menu.einfuegen.kreis"),
                           command=lambda: self._werkzeug_aus_menue("kreis"))
        m_einf.add_command(label=tr("menu.einfuegen.bogen"),
                           command=lambda: self._werkzeug_aus_menue("bogen"))
        m_einf.add_command(label=tr("menu.einfuegen.rechteck"),
                           command=lambda: self._werkzeug_aus_menue("rechteck"))
        m_einf.add_separator()
        m_einf.add_command(label=tr("menu.einfuegen.text"),
                           command=lambda: self._werkzeug_aus_menue("text"))
        m_einf.add_command(label=tr("menu.einfuegen.bemassung"),
                           command=lambda: self._werkzeug_aus_menue("bemassung"))
        m_einf.add_separator()
        m_einf.add_command(label=tr("menu.einfuegen.viewport"),
                           command=self.viewport_modus_starten)
        m_einf.add_command(label=tr("menu.einfuegen.rahmen"),
                           command=self.rahmen_einfuegen)
        menubar.add_cascade(label=tr("menu.einfuegen"), menu=m_einf)

        # Ansicht
        m_ansicht = tk.Menu(menubar, tearoff=0,
                            bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                            activebackground=FARBEN["cyan"],
                            activeforeground=FARBEN["bg_dunkel"])
        m_ansicht.add_command(label=tr("menu.ansicht.modell"),
                              command=lambda: self.setze_ansicht("modell"))
        m_ansicht.add_command(label=tr("menu.ansicht.layout"),
                              command=self._ansicht_aktuelles_layout)
        m_ansicht.add_separator()
        m_ansicht.add_command(label=tr("vp.leiste.viewport"),
                              command=self._menue_viewport_ansicht)
        m_ansicht.add_command(label=tr("vp.leiste.layout"),
                              command=self._menue_layout_ansicht)
        m_ansicht.add_separator()
        m_ansicht.add_command(label=tr("menu.ansicht.zoom_grenzen"),
                              command=self.zoom_grenzen)
        m_ansicht.add_separator()
        m_ansicht.add_command(label=tr("menu.ansicht.bg_modell"),
                              command=lambda: self.bg_waehlen("modell"))
        m_ansicht.add_command(label=tr("menu.ansicht.bg_layout"),
                              command=lambda: self.bg_waehlen("layout"))
        m_ansicht.add_separator()
        m_ansicht.add_command(label=tr("menu.ansicht.reset"),
                              command=self._reset_view)
        menubar.add_cascade(label=tr("menu.ansicht"), menu=m_ansicht)

        # Sprache
        m_sprache = tk.Menu(menubar, tearoff=0,
                            bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                            activebackground=FARBEN["cyan"],
                            activeforeground=FARBEN["bg_dunkel"])
        m_sprache.add_radiobutton(label=tr("menu.sprache.de"), value="de",
                                  variable=self.sprache_var,
                                  command=lambda: self.sprache_wechseln("de"))
        m_sprache.add_radiobutton(label=tr("menu.sprache.en"), value="en",
                                  variable=self.sprache_var,
                                  command=lambda: self.sprache_wechseln("en"))
        menubar.add_cascade(label=tr("menu.sprache"), menu=m_sprache)

        # Hilfe
        m_hilfe = tk.Menu(menubar, tearoff=0,
                          bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                          activebackground=FARBEN["cyan"],
                          activeforeground=FARBEN["bg_dunkel"])
        m_hilfe.add_command(label=tr("menu.hilfe.info"), command=self.zeige_info_fenster)
        menubar.add_cascade(label=tr("menu.hilfe"), menu=m_hilfe)

        self.root.config(menu=menubar)
        self._menubar = menubar

    def _build_toolbars(self):
        for attr in ("tb1", "tb2", "tb3"):
            if not hasattr(self, attr):
                frm = ttk.Frame(self.root, padding=4)
                frm.pack(side=tk.TOP, fill=tk.X)
                setattr(self, attr, frm)
            else:
                frm = getattr(self, attr)
                if not frm.winfo_ismapped():
                    frm.pack(side=tk.TOP, fill=tk.X)
            for child in list(frm.winfo_children()):
                child.destroy()

        # --- Toolbar 1 ---
        tb = self.tb1
        ttk.Label(tb, text=tr("tb.werkzeug"), style="Title.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        for key in ("auswahl", "linie", "polylinie", "kreis", "bogen",
                    "rechteck", "text", "bemassung"):
            ttk.Radiobutton(tb, text=tr(f"tb.wz.{key}"), value=key,
                            variable=self.aktives_werkzeug,
                            command=self._werkzeug_gewechselt
                            ).pack(side=tk.LEFT)

        # --- Toolbar 2 ---
        tb2 = self.tb2
        ttk.Label(tb2, text=tr("tb.layer"), style="Title.TLabel").pack(side=tk.LEFT)
        self.layer_cb = ttk.Combobox(tb2, textvariable=self.aktiver_layer,
                                     values=list(self.layers.keys()),
                                     width=16, state="readonly")
        self.layer_cb.pack(side=tk.LEFT, padx=4)
        self.layer_cb.bind("<<ComboboxSelected>>", self._layer_gewechselt)
        ttk.Button(tb2, text=tr("tb.layer_btn"),
                   command=self.layer_verwalten).pack(side=tk.LEFT, padx=2)
        self.lbl_layer_info = ttk.Label(tb2, text="", style="Hint.TLabel")
        self.lbl_layer_info.pack(side=tk.LEFT, padx=8)
        self._layer_info_aktualisieren()
        ttk.Separator(tb2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Label(tb2, text=tr("tb.linientyp"), style="Title.TLabel").pack(side=tk.LEFT)
        cb_lt = ttk.Combobox(tb2, textvariable=self.linientyp,
                             values=list(LINIENTYPEN.keys()),
                             width=18, state="readonly")
        cb_lt.pack(side=tk.LEFT, padx=4)
        cb_lt.bind("<<ComboboxSelected>>", self._stil_auf_auswahl)
        ttk.Label(tb2, text="  " + tr("tb.staerke"), style="Title.TLabel").pack(side=tk.LEFT)
        cb_ls = ttk.Combobox(tb2, textvariable=self.linienstaerke,
                             values=LINIENSTAERKEN, width=6, state="readonly")
        cb_ls.pack(side=tk.LEFT, padx=4)
        cb_ls.bind("<<ComboboxSelected>>", self._stil_auf_auswahl)
        ttk.Label(tb2, text="mm").pack(side=tk.LEFT)
        ttk.Label(tb2, text="  " + tr("tb.farbe"), style="Title.TLabel").pack(side=tk.LEFT, padx=(8, 0))
        self.farbe_btn = tk.Button(tb2, bg=self.zeichenfarbe, width=3,
                                   command=self.farbe_waehlen,
                                   relief=tk.FLAT, bd=0,
                                   highlightthickness=1,
                                   highlightbackground=FARBEN["cyan"])
        self.farbe_btn.pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(tb2, text=tr("tb.eig_farbe"),
                        variable=self.eigene_farbe).pack(side=tk.LEFT, padx=(0, 6))

        # --- Toolbar 3 ---
        tb3 = self.tb3
        self.lbl_einheit = ttk.Label(tb3, text=tr("tb.einheit"), style="Title.TLabel")
        self.cb_einheit = ttk.Combobox(tb3, textvariable=self.einheit,
                                       values=list(EINHEITEN.keys()),
                                       width=5, state="readonly")
        self.lbl_massstab = ttk.Label(tb3, text="  " + tr("tb.massstab"), style="Title.TLabel")
        self.cb_massstab = ttk.Combobox(tb3, textvariable=self.massstab,
                                        values=MASSSTAEBE, width=8, state="readonly")
        self.basis_widgets = [self.lbl_einheit, self.cb_einheit,
                              self.lbl_massstab, self.cb_massstab]

        self.lbl_kreis = ttk.Label(tb3, text="  " + tr("tb.kreis"), style="Title.TLabel")
        self.rb_radius = ttk.Radiobutton(tb3, text=tr("tb.radius"), value="radius",
                                         variable=self.kreis_modus)
        self.rb_durch = ttk.Radiobutton(tb3, text=tr("tb.durchmesser"),
                                        value="durchmesser", variable=self.kreis_modus)
        self.kreis_widgets = [self.lbl_kreis, self.rb_radius, self.rb_durch]

        self.lbl_schrift = ttk.Label(tb3, text="  " + tr("tb.schrift"), style="Title.TLabel")
        self.cb_schrift = ttk.Combobox(tb3, textvariable=self.text_schriftart,
                                       values=SCHRIFTARTEN, width=14, state="readonly")
        self.lbl_hoehe = ttk.Label(tb3, text=tr("tb.hoehe"), style="Title.TLabel")
        self.sp_hoehe = ttk.Spinbox(tb3, textvariable=self.text_hoehe,
                                    from_=1.0, to=100.0, increment=0.5, width=5)
        self.lbl_winkel = ttk.Label(tb3, text=tr("tb.winkel"), style="Title.TLabel")
        self.sp_winkel = ttk.Spinbox(tb3, textvariable=self.text_winkel,
                                     from_=-180, to=180, increment=15, width=5)
        self.text_widgets = [self.lbl_schrift, self.cb_schrift,
                             self.lbl_hoehe, self.sp_hoehe,
                             self.lbl_winkel, self.sp_winkel]

        self.lbl_fmt = ttk.Label(tb3, text=tr("tb.blattformat"), style="Title.TLabel")
        self._fmt_var = tk.StringVar(value=self.layout_format)
        self.cb_fmt = ttk.Combobox(tb3, textvariable=self._fmt_var,
                                   values=list(ZEICHNUNGSFORMATE.keys()),
                                   width=14, state="readonly")
        self.cb_fmt.bind("<<ComboboxSelected>>", self._layout_format_gewaehlt)
        self.btn_rahmen = ttk.Button(tb3, text=tr("tb.rahmen"),
                                     command=self.rahmen_einfuegen)
        self.btn_viewport = ttk.Button(tb3, text=tr("tb.viewport"),
                                       command=self.viewport_modus_starten)
        self.btn_blatt_clear = ttk.Button(tb3, text=tr("tb.blatt_leeren"),
                                          command=self.blatt_leeren)
        self.layout_widgets = [self.lbl_fmt, self.cb_fmt, self.btn_rahmen,
                               self.btn_viewport, self.btn_blatt_clear]

        self.lbl_bogen = ttk.Label(tb3, text="  " + tr("tb.bogen"), style="Title.TLabel")
        self.rb_b_mitte = ttk.Radiobutton(tb3, text=tr("tb.bogen.mitte"),
                                          value="mitte", variable=self.bogen_modus,
                                          command=self._bem_abbrechen)
        self.rb_b_3p = ttk.Radiobutton(tb3, text=tr("tb.bogen.3p"), value="3punkt",
                                       variable=self.bogen_modus,
                                       command=self._bem_abbrechen)
        self.lbl_b_r = ttk.Label(tb3, text=" " + tr("tb.bogen.richtung"), style="Title.TLabel")
        self.rb_b_auto = ttk.Radiobutton(tb3, text=tr("tb.bogen.auto"), value="auto",
                                         variable=self.bogen_richtung)
        self.rb_b_ccw = ttk.Radiobutton(tb3, text=tr("tb.bogen.ccw"), value="ccw",
                                        variable=self.bogen_richtung)
        self.rb_b_cw = ttk.Radiobutton(tb3, text=tr("tb.bogen.cw"), value="cw",
                                       variable=self.bogen_richtung)
        self.bogen_widgets = [self.lbl_bogen, self.rb_b_mitte, self.rb_b_3p,
                              self.lbl_b_r, self.rb_b_auto, self.rb_b_ccw, self.rb_b_cw]

        self.lbl_bem = ttk.Label(tb3, text="  " + tr("tb.mass"), style="Title.TLabel")
        self.cb_bem_art = ttk.Combobox(tb3, textvariable=self.bem_art,
                                       values=["auto", "horizontal", "vertikal",
                                               "ausgerichtet", "radius", "durchmesser"],
                                       width=12, state="readonly")
        self.cb_bem_art.bind("<<ComboboxSelected>>",
                             lambda e: (self._bem_abbrechen(), self._update_eingabe_hinweis()))
        self.lbl_bem_h = ttk.Label(tb3, text=" " + tr("tb.mass.text"), style="Title.TLabel")
        self.sp_bem_h = ttk.Spinbox(tb3, textvariable=self.bem_hoehe,
                                    from_=0.5, to=100.0, increment=0.5, width=5)
        self.lbl_bem_p = ttk.Label(tb3, text=" " + tr("tb.mass.pfeil"), style="Title.TLabel")
        self.sp_bem_p = ttk.Spinbox(tb3, textvariable=self.bem_pfeil,
                                    from_=0.5, to=100.0, increment=0.5, width=5)
        self.lbl_bem_d = ttk.Label(tb3, text=" " + tr("tb.mass.nachkomma"), style="Title.TLabel")
        self.sp_bem_d = ttk.Spinbox(tb3, textvariable=self.bem_dez,
                                    from_=0, to=6, increment=1, width=3)
        self.cb_bem_komma = ttk.Checkbutton(tb3, text=tr("tb.mass.komma"),
                                            variable=self.dezimalkomma,
                                            command=self.redraw)
        self.bem_widgets = [self.lbl_bem, self.cb_bem_art, self.lbl_bem_h, self.sp_bem_h,
                            self.lbl_bem_p, self.sp_bem_p, self.lbl_bem_d, self.sp_bem_d,
                            self.cb_bem_komma]

        self._tb3_anker = ttk.Frame(tb3, width=1)
        self._tb3_anker.pack(side=tk.LEFT)
        ttk.Separator(tb3, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(tb3, text=tr("tb.zoom_plus"), width=8,
                   command=lambda: self._zoom(1.25)).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb3, text=tr("tb.zoom_minus"), width=8,
                   command=lambda: self._zoom(0.8)).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb3, text=tr("tb.reset"), width=8,
                   command=self._reset_view).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb3, text=tr("tb.zoom_grenzen"), width=14,
                   command=self.zoom_grenzen).pack(side=tk.LEFT, padx=2)

        ttk.Separator(tb3, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Label(tb3, text=tr("tb.hintergrund"), style="Title.TLabel").pack(side=tk.LEFT)
        bg_aktuell = self.bg_layout if self._ist_layout() else self.bg_modell
        self.bg_btn = tk.Button(tb3, bg=bg_aktuell, width=3,
                                command=lambda: self.bg_waehlen(
                                    "layout" if self._ist_layout() else "modell"),
                                relief=tk.FLAT, bd=0,
                                highlightthickness=1,
                                highlightbackground=FARBEN["cyan"])
        self.bg_btn.pack(side=tk.LEFT, padx=4)
        self.bg_preset_cb = ttk.Combobox(tb3, values=list(BG_PRESETS.keys()),
                                         width=18, state="readonly")
        self.bg_preset_cb.pack(side=tk.LEFT, padx=2)
        self.bg_preset_cb.bind("<<ComboboxSelected>>",
                               self._bg_preset_angewendet)

    def _build_eingabeleiste(self):
        self.frame_eingabe = ttk.Frame(self.root, padding=(6, 4))
        self.frame_eingabe.pack(side=tk.BOTTOM, fill=tk.X)
        self.lbl_eingabe = ttk.Label(self.frame_eingabe, text=tr("eingabe.label"),
                                     style="Title.TLabel")
        self.lbl_eingabe.pack(side=tk.LEFT, padx=(0, 6))
        self.entry_eingabe = ttk.Entry(self.frame_eingabe,
                                       textvariable=self.eingabe_var,
                                       width=28, font=("Consolas", 11))
        self.entry_eingabe.pack(side=tk.LEFT, padx=4)
        self.entry_eingabe.bind("<Return>", self._eingabe_enter)
        self.lbl_hinweis = ttk.Label(self.frame_eingabe, text="",
                                     style="Hint.TLabel")
        self.lbl_hinweis.pack(side=tk.LEFT, padx=8)

    def _retranslate_eingabeleiste(self):
        if hasattr(self, "lbl_eingabe"):
            self.lbl_eingabe.config(text=tr("eingabe.label"))

    # --------------------------------------------------------
    # Layout-Switcher (unten)
    # --------------------------------------------------------
    def _build_layout_switcher(self):
        self.layout_switcher_frame = ttk.Frame(self.root, padding=(6, 3))
        self.layout_switcher_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Label(self.layout_switcher_frame, text=tr("tb.ansicht"),
                  style="Title.TLabel").pack(side=tk.LEFT, padx=(0, 4))

        ttk.Radiobutton(self.layout_switcher_frame,
                        text=tr("layout.switcher.modell"), value="modell",
                        variable=self.ansicht,
                        command=self.ansicht_wechseln).pack(side=tk.LEFT)

        ttk.Separator(self.layout_switcher_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=6)

        self._layout_buttons_frame = ttk.Frame(self.layout_switcher_frame)
        self._layout_buttons_frame.pack(side=tk.LEFT)

        ttk.Button(self.layout_switcher_frame, text=tr("layout.switcher.neu"),
                   width=3, command=self.neues_layout).pack(side=tk.LEFT, padx=(4, 1))
        ttk.Button(self.layout_switcher_frame, text=tr("layout.switcher.loeschen"),
                   width=3, command=self.layout_loeschen).pack(side=tk.LEFT, padx=1)
        ttk.Button(self.layout_switcher_frame, text=tr("layout.switcher.umbenennen"),
                   width=3, command=self.layout_umbenennen).pack(side=tk.LEFT, padx=1)

        self._layout_switcher_neu_aufbauen()

    def _layout_switcher_neu_aufbauen(self):
        if not hasattr(self, "_layout_buttons_frame"):
            return
        for w in self._layout_buttons_frame.winfo_children():
            w.destroy()
        for i, lay in enumerate(self.layouts):
            ttk.Radiobutton(self._layout_buttons_frame, text=lay.name,
                            value=f"layout:{i}",
                            variable=self.ansicht,
                            command=self.ansicht_wechseln
                            ).pack(side=tk.LEFT, padx=(0, 2))

    def _ansicht_aktuelles_layout(self):
        self.setze_ansicht(f"layout:{self.aktives_layout}")

    def _layout_format_gewaehlt(self, event=None):
        neues = self._fmt_var.get()
        if neues in ZEICHNUNGSFORMATE:
            self._snapshot()
            self.layout.format = neues
            self.redraw()
            self._mark_dirty()

    def neues_layout(self):
        name = f"Layout{len(self.layouts) + 1}"
        basis = len(self.layouts)
        while any(l.name == name for l in self.layouts):
            basis += 1
            name = f"Layout{basis}"
        self._snapshot()
        self.layouts.append(Layout(name, self.layout_format, self.bg_layout))
        self._layout_switcher_neu_aufbauen()
        self.aktives_layout = len(self.layouts) - 1
        self.ansicht.set(f"layout:{self.aktives_layout}")
        self.ansicht_wechseln()
        self.status.set(tr("layout.angelegt"))

    def layout_loeschen(self):
        if len(self.layouts) <= 1:
            messagebox.showinfo(tr("layout.loeschen.titel"),
                                tr("layout.letztes_schuetzen"))
            return
        idx = self._layout_index() if self._ist_layout() else self.aktives_layout
        lay = self.layouts[idx]
        if not messagebox.askyesno(tr("layout.loeschen.titel"),
                                   tr("layout.loeschen.frage", name=lay.name)):
            return
        self._snapshot()
        del self.layouts[idx]
        if self.aktives_layout >= len(self.layouts):
            self.aktives_layout = len(self.layouts) - 1
        self._layout_switcher_neu_aufbauen()
        if self._ist_layout():
            self.ansicht.set(f"layout:{self.aktives_layout}")
            self.ansicht_wechseln()
        else:
            self.redraw()
        self.status.set(tr("layout.geloescht"))

    def layout_umbenennen(self):
        idx = self._layout_index() if self._ist_layout() else self.aktives_layout
        lay = self.layouts[idx]
        neu = _LayoutNameDialog(self.root, tr("layout.umbenennen.titel"),
                                lay.name).result
        if not neu:
            return
        neu = neu.strip()
        if not neu:
            messagebox.showwarning(tr("layout.umbenennen.titel"),
                                   tr("layout.name_leer"))
            return
        if any(l is not lay and l.name == neu for l in self.layouts):
            messagebox.showwarning(tr("layout.umbenennen.titel"),
                                   tr("layout.name_existiert"))
            return
        self._snapshot()
        lay.name = neu
        self._layout_switcher_neu_aufbauen()
        self.status.set(tr("layout.umbenannt"))

    def _build_statusbar(self):
        bar = ttk.Frame(self.root, padding=(6, 4))
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        self._statusbar_frame = bar
        self._status_buttons = {}

        def toggle_btn(key, text, var, command=None, key_hint=""):
            def cmd():
                var.set(not var.get())
                if command:
                    command()
            b = tk.Button(bar, text=text + (f" [{key_hint}]" if key_hint else ""),
                          relief=tk.FLAT, bd=0, padx=10, pady=4, command=cmd,
                          font=("Segoe UI", 9, "bold"),
                          highlightthickness=1)
            b.pack(side=tk.LEFT, padx=2)
            def update_style(*_):
                if var.get():
                    b.config(bg=FARBEN["cyan"], fg=FARBEN["bg_dunkel"],
                             activebackground=FARBEN["cyan"],
                             activeforeground=FARBEN["bg_dunkel"],
                             highlightbackground=FARBEN["cyan"])
                else:
                    b.config(bg=FARBEN["bg_hell"], fg=FARBEN["text_dim"],
                             activebackground=FARBEN["bg_hover"],
                             activeforeground=FARBEN["cyan"],
                             highlightbackground=FARBEN["rand"])
            var.trace_add("write", update_style)
            update_style()
            self._status_buttons[key] = (b, key_hint)
            return b

        self.fang_btn = toggle_btn("osnap",
                                    "OFANG" if SPRACHE["aktuell"] == "de" else "OSNAP",
                                    self.osnap, key_hint="F3")
        self.fang_pfeil = tk.Button(
            bar, text="▾", relief=tk.FLAT, bd=0, padx=4, pady=4,
            font=("Segoe UI", 8, "bold"),
            bg=FARBEN["bg_hell"], fg=FARBEN["cyan"],
            activebackground=FARBEN["bg_hover"],
            activeforeground=FARBEN["text_hell"],
            highlightthickness=1,
            highlightbackground=FARBEN["rand"],
            command=self._zeige_osnap_menue)
        self.fang_pfeil.pack(side=tk.LEFT, padx=(0, 2))
        self.snap_btn = toggle_btn("snap", tr("sb.fang"), self.grid_snap, key_hint="F9")
        self.ortho_btn = toggle_btn("ortho", tr("sb.ortho"), self.ortho, key_hint="F8")
        self.raster_btn = toggle_btn("raster", tr("sb.raster"), self.raster_sichtbar,
                                     command=self._zeichne_raster, key_hint="F7")
        self.punkt_btn = toggle_btn("punkt", tr("sb.punktiert"), self.raster_punktiert,
                                    command=self._zeichne_raster)
        self.lst_btn = toggle_btn("lst", tr("sb.lst"), self.lw_anzeigen, command=self.redraw)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        self._lbl_raster = ttk.Label(bar, text=tr("sb.raster_mm"), style="Title.TLabel")
        self._lbl_raster.pack(side=tk.LEFT)
        cb = ttk.Combobox(bar, textvariable=self.raster_mm,
                          values=RASTER_GROESSEN, width=6)
        cb.pack(side=tk.LEFT, padx=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.redraw())
        cb.bind("<Return>", lambda e: self.redraw())
        self._lbl_fang = ttk.Label(bar, text=tr("sb.fang_mm"), style="Title.TLabel")
        self._lbl_fang.pack(side=tk.LEFT, padx=(4, 0))
        cb2 = ttk.Combobox(bar, textvariable=self.fang_mm,
                           values=RASTER_GROESSEN, width=6)
        cb2.pack(side=tk.LEFT, padx=2)
        cb2.bind("<Return>", lambda e: self.status.set(
            (f"Fang: {self._zahl(self.fang_mm, 5):g} mm" if SPRACHE["aktuell"] == "de"
             else f"Snap: {self._zahl(self.fang_mm, 5):g} mm")))
        ttk.Label(bar, text="mm").pack(side=tk.LEFT, padx=(0, 8))

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        self._lbl_objektfang = ttk.Label(bar, text=tr("sb.objektfang"),
                                         style="Title.TLabel")
        self._lbl_objektfang.pack(side=tk.LEFT, padx=(0, 4))
        self.lbl_osnap_modi = ttk.Label(bar, text="", style="Hint.TLabel")
        self.lbl_osnap_modi.pack(side=tk.LEFT, padx=4)
        self._aktualisiere_osnap_anzeige()
        for key, var in self.osnap_modi.items():
            var.trace_add("write", lambda *_: self._aktualisiere_osnap_anzeige())

    def _retranslate_statusbar(self):
        if hasattr(self, "fang_btn") and "osnap" in self._status_buttons:
            b, hint = self._status_buttons["osnap"]
            b.config(text=("OFANG" if SPRACHE["aktuell"] == "de" else "OSNAP")
                     + (f" [{hint}]" if hint else ""))
        mapping = {
            "snap": "sb.fang", "ortho": "sb.ortho", "raster": "sb.raster",
            "punkt": "sb.punktiert", "lst": "sb.lst",
        }
        for key, schluessel in mapping.items():
            if key in self._status_buttons:
                b, hint = self._status_buttons[key]
                b.config(text=tr(schluessel) + (f" [{hint}]" if hint else ""))
        if hasattr(self, "_lbl_raster"):
            self._lbl_raster.config(text=tr("sb.raster_mm"))
        if hasattr(self, "_lbl_fang"):
            self._lbl_fang.config(text=tr("sb.fang_mm"))
        if hasattr(self, "_lbl_objektfang"):
            self._lbl_objektfang.config(text=tr("sb.objektfang"))
        self._aktualisiere_osnap_anzeige()

    def _werkzeug_aus_menue(self, key):
        self.aktives_werkzeug.set(key)
        self._werkzeug_gewechselt()

    def _aktualisiere_osnap_anzeige(self):
        aktive = [k for k, v in self.osnap_modi.items() if v.get()]
        text = tr("sb.keine") if not aktive else ", ".join(
            tr(f"sb.osnap.{k}") for k in aktive)
        if hasattr(self, "lbl_osnap_modi"):
            self.lbl_osnap_modi.config(text=text)

    def _zeige_osnap_menue(self):
        menu = tk.Menu(self.root, tearoff=0,
                       bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                       activebackground=FARBEN["cyan"],
                       activeforeground=FARBEN["bg_dunkel"])
        menu.add_command(label=tr("osnap.aktiv"),
                         command=lambda: self.osnap.set(not self.osnap.get()))
        menu.add_separator()
        for key in ("endpunkt", "mittelpunkt", "zentrum", "schnittpunkt",
                    "quadrant", "lot", "naechster"):
            menu.add_checkbutton(label=tr(f"osnap.{key}"),
                                 variable=self.osnap_modi[key])
        menu.add_separator()
        menu.add_command(label=tr("osnap.alle_an"), command=self._alle_osnap_an)
        menu.add_command(label=tr("osnap.alle_aus"), command=self._alle_osnap_aus)
        x = self.fang_pfeil.winfo_rootx()
        y = self.fang_pfeil.winfo_rooty() + self.fang_pfeil.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _alle_osnap_an(self):
        for v in self.osnap_modi.values():
            v.set(True)

    def _alle_osnap_aus(self):
        for v in self.osnap_modi.values():
            v.set(False)

    def _update_kontext_widgets(self):
        alle = (self.basis_widgets + self.kreis_widgets + self.text_widgets +
                self.layout_widgets + self.bogen_widgets + self.bem_widgets)
        for w in alle:
            w.pack_forget()
        def zeige(widgets):
            for w in widgets:
                w.pack(side=tk.LEFT, padx=2, before=self._tb3_anker)
        zeige(self.layout_widgets if self._ist_layout() else self.basis_widgets)
        if hasattr(self, "_fmt_var"):
            self._fmt_var.set(self.layout_format)
        werkzeug = self.aktives_werkzeug.get()
        if werkzeug == "kreis":
            zeige(self.kreis_widgets)
        elif werkzeug == "text":
            zeige(self.text_widgets)
        elif werkzeug == "bogen":
            zeige(self.bogen_widgets)
        elif werkzeug == "bemassung":
            zeige(self.bem_widgets)

    # --------------------------------------------------------
    # Viewport-Leiste (nur im Layout sichtbar)
    # --------------------------------------------------------
    def _build_viewport_leiste(self):
        self.viewport_leiste = ttk.Frame(self.root, padding=(6, 3))
        # Wird NICHT sofort gepackt – die Sichtbarkeit steuert
        # _viewport_modus_anzeige_aktualisieren() abhängig vom Modus.

        ttk.Label(self.viewport_leiste, text=tr("tb.ansicht"),
                  style="Title.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Radiobutton(self.viewport_leiste, text=tr("vp.leiste.layout"),
                        value="layout", variable=self._vp_modus_var,
                        command=self._vp_modus_gewaehlt
                        ).pack(side=tk.LEFT)
        ttk.Radiobutton(self.viewport_leiste, text=tr("vp.leiste.viewport"),
                        value="viewport", variable=self._vp_modus_var,
                        command=self._vp_modus_gewaehlt
                        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Separator(self.viewport_leiste, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Label(self.viewport_leiste, text=tr("vp.leiste.zoom") + ":",
                  style="Title.TLabel").pack(side=tk.LEFT)
        self._vp_btn_plus = ttk.Button(self.viewport_leiste, text="+", width=3,
                                       command=lambda: self._vp_zoom_faktor(1.25))
        self._vp_btn_plus.pack(side=tk.LEFT, padx=1)
        self._vp_btn_minus = ttk.Button(self.viewport_leiste, text="−", width=3,
                                        command=lambda: self._vp_zoom_faktor(0.8))
        self._vp_btn_minus.pack(side=tk.LEFT, padx=1)
        self._vp_btn_fit = ttk.Button(self.viewport_leiste,
                                      text=tr("vp.leiste.fit"),
                                      command=self._vp_fit_aktueller)
        self._vp_btn_fit.pack(side=tk.LEFT, padx=1)

        self._vp_lbl_massstab = ttk.Label(self.viewport_leiste,
                                          text="  " + tr("vp.leiste.massstab"),
                                          style="Title.TLabel")
        self._vp_lbl_massstab.pack(side=tk.LEFT, padx=(8, 0))
        self._vp_cb_massstab = ttk.Combobox(self.viewport_leiste,
                                            textvariable=self._vp_massstab_var,
                                            values=MASSSTAEBE, width=8,
                                            state="readonly")
        self._vp_cb_massstab.pack(side=tk.LEFT, padx=2)
        self._vp_cb_massstab.bind("<<ComboboxSelected>>",
                                  self._vp_massstab_gewaehlt)

        ttk.Separator(self.viewport_leiste, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=6)

        self._vp_chk_sperre = ttk.Checkbutton(self.viewport_leiste,
                                              text=tr("vp.leiste.sperren"),
                                              variable=self._vp_sperre_var,
                                              command=self._vp_sperre_toggle)
        self._vp_chk_sperre.pack(side=tk.LEFT)

        self._vp_status_lbl = ttk.Label(self.viewport_leiste,
                                        textvariable=self._vp_status_var,
                                        style="Hint.TLabel")
        self._vp_status_lbl.pack(side=tk.LEFT, padx=8)

    def _retranslate_viewport_leiste(self):
        if not hasattr(self, "viewport_leiste"):
            return
        # Kinder neu beschriften geht am einfachsten über komplettes Neubauen:
        self.viewport_leiste.destroy()
        self._build_viewport_leiste()
        self._viewport_modus_anzeige_aktualisieren()

    def _viewport_leiste_sichtbar(self, sichtbar):
        if not hasattr(self, "viewport_leiste"):
            return
        if sichtbar:
            if not self.viewport_leiste.winfo_ismapped():
                self.viewport_leiste.pack(side=tk.TOP, fill=tk.X,
                                          before=self.canvas)
        else:
            # pack_forget() ist idempotent und sicher, auch wenn die Leiste
            # gerade nicht gemappt ist. So ist sie garantiert weg, egal wie
            # die Pack-Reihenfolge beim Start aussieht.
            self.viewport_leiste.pack_forget()

    def _viewport_modus_anzeige_aktualisieren(self):
        if not hasattr(self, "viewport_leiste"):
            return
        self._viewport_leiste_sichtbar(self._ist_layout())
        vp = self._aktiver_viewport
        if self._ist_layout() and vp is not None:
            self._vp_modus_var.set("viewport")
        else:
            self._vp_modus_var.set("layout")
        if vp is None:
            self._vp_status_var.set(tr("vp.leiste.kein_vp"))
            self._vp_massstab_var.set("1:1")
            self._vp_sperre_var.set(False)
            state = "disabled"
        else:
            name = self._viewport_name(vp)
            zustand = (tr("vp.leiste.status_gesperrt") if vp.gesperrt
                       else tr("vp.leiste.status_frei"))
            self._vp_status_var.set(
                tr("vp.leiste.aktiv", name=name) + "  –  " + zustand)
            self._vp_massstab_var.set(massstab_text(vp.zoom))
            self._vp_sperre_var.set(vp.gesperrt)
            state = "normal"
        for w in (getattr(self, "_vp_btn_plus", None),
                  getattr(self, "_vp_btn_minus", None),
                  getattr(self, "_vp_btn_fit", None),
                  getattr(self, "_vp_cb_massstab", None),
                  getattr(self, "_vp_chk_sperre", None)):
            if w is not None:
                try:
                    w.configure(state=state)
                except Exception:
                    pass

    def _viewport_name(self, vp):
        try:
            idx = self.layout_elemente.index(vp)
        except ValueError:
            return "Viewport"
        n = sum(1 for i in range(idx + 1)
                if isinstance(self.layout_elemente[i], Viewport))
        return f"Viewport {n}"

    def _vp_modus_gewaehlt(self):
        if not self._ist_layout():
            self._vp_modus_var.set("layout")
            messagebox.showinfo(tr("vp.leiste.viewport"),
                                tr("vp.leiste.kein_layout_hinweis"))
            return
        if self._vp_modus_var.get() == "viewport":
            vp = self._aktiver_viewport
            if vp is None:
                vp = self._erster_viewport()
            if vp is None:
                self._vp_modus_var.set("layout")
                messagebox.showinfo(tr("vp.leiste.viewport"),
                                    tr("vp.leiste.viewport_waehlen"))
                return
            self._vp_aktivieren(vp)
        else:
            self._vp_deaktivieren()

    def _menue_viewport_ansicht(self):
        if not self._ist_layout():
            self._ansicht_aktuelles_layout()
        self._vp_modus_var.set("viewport")
        self._vp_modus_gewaehlt()

    def _menue_layout_ansicht(self):
        if self._ist_layout():
            self._vp_modus_var.set("layout")
            self._vp_modus_gewaehlt()

    def _erster_viewport(self):
        for el in self.layout_elemente:
            if isinstance(el, Viewport):
                return el
        return None

    def _vp_deaktivieren(self):
        if self._aktiver_viewport is not None:
            self._aktiver_viewport.aktiv = False
            self._aktiver_viewport = None
        self._vp_modus_var.set("layout")
        self.redraw()
        self._viewport_modus_anzeige_aktualisieren()
        de = SPRACHE["aktuell"] == "de"
        self.status.set("Layout-Ansicht." if de else "Layout view.")

    def _vp_zoom_faktor(self, faktor):
        vp = self._aktiver_viewport
        if vp is None:
            return
        if vp.gesperrt:
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Viewport-Maßstab ist gesperrt." if de
                            else "Viewport scale is locked.")
            return
        self._vp_zoom_um_punkt(vp, faktor, self._vp_mittelpunkt_mm(vp))
        self._viewport_modus_anzeige_aktualisieren()

    def _vp_mittelpunkt_mm(self, vp):
        return (vp.x + vp.breite / 2, vp.y + vp.hoehe / 2)

    def _vp_zoom_um_punkt(self, vp, faktor, punkt_mm):
        mx_mm, my_mm = punkt_mm
        mod_x, mod_y = self._papier_zu_modell(vp, mx_mm, my_mm)
        self._snapshot()
        vp.zoom *= faktor
        vcx = vp.x + vp.breite / 2
        vcy = vp.y + vp.hoehe / 2
        vp.modell_zentrum_x = mod_x - (mx_mm - vcx) / vp.zoom
        vp.modell_zentrum_y = mod_y - (my_mm - vcy) / vp.zoom
        self.redraw()

    def _vp_massstab_gewaehlt(self, event=None):
        vp = self._aktiver_viewport
        if vp is None:
            return
        if vp.gesperrt:
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Viewport-Maßstab ist gesperrt." if de
                            else "Viewport scale is locked.")
            self._viewport_modus_anzeige_aktualisieren()
            return
        text = self._vp_massstab_var.get()
        try:
            neuer_zoom = parse_massstab(text)
        except Exception:
            return
        cx_mm, cy_mm = self._vp_mittelpunkt_mm(vp)
        mod_x, mod_y = self._papier_zu_modell(vp, cx_mm, cy_mm)
        self._snapshot()
        vp.zoom = neuer_zoom
        vcx = vp.x + vp.breite / 2
        vcy = vp.y + vp.hoehe / 2
        vp.modell_zentrum_x = mod_x - (cx_mm - vcx) / vp.zoom
        vp.modell_zentrum_y = mod_y - (cy_mm - vcy) / vp.zoom
        self.redraw()
        self._viewport_modus_anzeige_aktualisieren()
        de = SPRACHE["aktuell"] == "de"
        self.status.set((f"Viewport-Maßstab {text}" if de
                         else f"Viewport scale {text}"))

    def _vp_fit_aktueller(self):
        vp = self._aktiver_viewport
        if vp is None:
            return
        if vp.gesperrt:
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Viewport-Maßstab ist gesperrt." if de
                            else "Viewport scale is locked.")
            return
        self._vp_auto_fit(vp)
        self._viewport_modus_anzeige_aktualisieren()

    def _vp_sperre_toggle(self):
        vp = self._aktiver_viewport
        if vp is None:
            return
        vp.gesperrt = bool(self._vp_sperre_var.get())
        self._viewport_modus_anzeige_aktualisieren()
        de = SPRACHE["aktuell"] == "de"
        self.status.set(("Viewport-Maßstab " + (
            "gesperrt." if vp.gesperrt else "entsperrt.") if de else
            "Viewport scale " + (
            "locked." if vp.gesperrt else "unlocked.")))

    # --------------------------------------------------------
    def ansicht_wechseln(self):
        if self._ist_layout():
            idx = self._layout_index()
            if 0 <= idx < len(self.layouts):
                self.aktives_layout = idx
        if self._aktiver_viewport is not None:
            self._aktiver_viewport.aktiv = False
            self._aktiver_viewport = None
        self.letzter_punkt = None
        self._clear_temp()
        self.aktuelle_polylinie = []
        self.auswahl = []
        self._vp_aktion = "none"
        self._vp_el = None
        self._paste_abbrechen()
        self._bem_abbrechen()
        self._bogen_abbrechen()
        self._update_kontext_widgets()
        bg = self.bg_modell if not self._ist_layout() else self.bg_layout
        self.canvas.config(bg=bg)
        self.bg_btn.config(bg=bg)
        self._zeichne_raster()
        self.redraw()
        self._viewport_modus_anzeige_aktualisieren()
        de = SPRACHE["aktuell"] == "de"
        if self._ist_layout():
            self.status.set(("Ansicht: Layout '" if de else "View: layout '")
                            + self.layout.name + "'")
        else:
            self.status.set(("Ansicht: Modell" if de else "View: model"))

    def setze_ansicht(self, name):
        self.ansicht.set(name)
        self.ansicht_wechseln()

    def bg_waehlen(self, bereich):
        aktuell = self.bg_modell if bereich == "modell" else self.bg_layout
        _, hexc = colorchooser.askcolor(color=aktuell,
                                        title=tr("tb.hintergrund"))
        if not hexc:
            return
        self._bg_setzen(bereich, hexc)

    def _bg_setzen(self, bereich, hexc):
        if bereich == "modell":
            self.bg_modell = hexc
        else:
            self.bg_layout = hexc
        aktuell_layout = self._ist_layout()
        if (bereich == "modell" and not aktuell_layout) or \
           (bereich == "layout" and aktuell_layout):
            self.canvas.config(bg=hexc)
            self.bg_btn.config(bg=hexc)
            self.redraw()
            self._zeichne_raster()
        self._mark_dirty()

    def _bg_preset_angewendet(self, event=None):
        auswahl = self.bg_preset_cb.get()
        if auswahl in BG_PRESETS:
            self._bg_setzen("layout" if self._ist_layout() else "modell",
                            BG_PRESETS[auswahl])

    def _layer_gewechselt(self, event=None):
        self._layer_info_aktualisieren()

    def _layer_info_aktualisieren(self):
        l = self.layers.get(self.aktiver_layer.get())
        if l:
            de = SPRACHE["aktuell"] == "de"
            self.lbl_layer_info.config(
                text=(f"Farbe: {l.farbe}   Stärke: {l.staerke} mm" if de
                      else f"Color: {l.farbe}   Weight: {l.staerke} mm"))

    def layer_verwalten(self):
        LayerDialog(self.root, self)

    def zoom_grenzen(self, event=None):
        liste = self.elemente if not self._ist_layout() else self.layout_elemente
        cw = self.canvas.winfo_width() or 1200
        ch = self.canvas.winfo_height() or 700
        if not liste:
            self.view["zoom"] = 1.5
            self.view["ox"] = cw / 2
            self.view["oy"] = ch / 2
            self.redraw()
            self._zeichne_raster()
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Zoom Grenzen (leer)." if de else "Zoom extents (empty).")
            return
        xs, ys = [], []
        for el in liste:
            b = el.bbox()
            xs.extend([b[0], b[2]])
            ys.extend([b[1], b[3]])
        if not xs or not ys:
            return
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        bw = maxx - minx
        bh = maxy - miny
        if bw < 1e-6: bw = 10.0
        if bh < 1e-6: bh = 10.0
        zoom_x = (cw * 0.85) / bw
        zoom_y = (ch * 0.85) / bh
        neuer_zoom = min(zoom_x, zoom_y)
        cx = (minx + maxx) / 2
        cy = (miny + maxy) / 2
        self.view["zoom"] = max(0.001, neuer_zoom)
        self.view["ox"] = cw / 2 - cx * self.view["zoom"]
        self.view["oy"] = ch / 2 + cy * self.view["zoom"]
        self.redraw()
        self._zeichne_raster()
        de = SPRACHE["aktuell"] == "de"
        self.status.set("Zoom Grenzen ausgeführt." if de else "Zoom extents applied.")
        return "break"

    # --------------------------------------------------------
    def _bind_events(self):
        c = self.canvas
        c.bind("<Button-1>", self.on_click)
        c.bind("<B1-Motion>", self.on_drag_b1)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Double-Button-1>", self.on_doppelklick)
        c.bind("<Double-Button-2>", self.zoom_grenzen)
        c.bind("<Double-Button-3>", self.zoom_grenzen)
        c.bind("<Button-2>", self.on_pan_start)
        c.bind("<B2-Motion>", self.on_pan)
        c.bind("<ButtonRelease-2>", self.on_pan_end)
        c.bind("<Button-3>", self.on_rechtsklick_start)
        c.bind("<B3-Motion>", self.on_pan)
        c.bind("<ButtonRelease-3>", self.on_rechtsklick_end)
        c.bind("<Motion>", self.on_move)
        c.bind("<MouseWheel>", self.on_wheel)
        c.bind("<Button-4>", lambda e: self._zoom_auf_maus(e, 1.1))
        c.bind("<Button-5>", lambda e: self._zoom_auf_maus(e, 0.9))
        c.bind("<Configure>", lambda e: self._zeichne_raster())
        c.bind("<Leave>", lambda e: self._snap_marker_loeschen())
        self.root.bind("<F3>", lambda e: self.osnap.set(not self.osnap.get()))
        self.root.bind("<F7>", lambda e: (self.raster_sichtbar.set(
            not self.raster_sichtbar.get()), self._zeichne_raster()))
        self.root.bind("<F8>", lambda e: self.ortho.set(not self.ortho.get()))
        self.root.bind("<F9>", lambda e: self.grid_snap.set(not self.grid_snap.get()))
        self.root.bind("<Escape>", self._escape)
        self.root.bind("<Delete>", lambda e: self.auswahl_loeschen())
        self.root.bind("<Control-a>", lambda e: self.alle_markieren())
        self.root.bind("<Control-A>", lambda e: self.alle_markieren())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-Z>", lambda e: self.undo())
        self.root.bind("<Control-c>", self.kopieren)
        self.root.bind("<Control-C>", self.kopieren)
        self.root.bind("<Control-Shift-C>", self.kopieren_mit_basispunkt)
        self.root.bind("<Control-Shift-c>", self.kopieren_mit_basispunkt)
        self.root.bind("<Control-x>", self.ausschneiden)
        self.root.bind("<Control-X>", self.ausschneiden)
        self.root.bind("<Control-v>", self.einfuegen)
        self.root.bind("<Control-V>", self.einfuegen)
        self.root.bind("<Control-d>", self.duplizieren)
        self.root.bind("<Control-D>", self.duplizieren)
        self.root.bind("<Control-p>", lambda e: self.drucken())
        self.root.bind("<Control-P>", lambda e: self.drucken())
        self.root.bind("<Control-s>", lambda e: self.speichern())
        self.root.bind("<Control-S>", lambda e: self.speichern())
        self.root.bind("<g>", self.zoom_grenzen)
        self.root.bind("<G>", self.zoom_grenzen)
        self.entry_eingabe.bind("<Tab>", self._on_tab)

    def _on_tab(self, event):
        self.entry_eingabe.insert(tk.INSERT, "  ")
        return "break"

    def _escape(self, event=None):
        if self._paste_aktiv:
            self._paste_abbrechen()
        if self._griff_drag_el is not None:
            self._griff_drag_el = None
            self._griff_drag_id = None
        self._bem_abbrechen()
        self._bogen_abbrechen()
        self._warte_auf_basispunkt = False
        self._clipboard_mit_basis = False
        if self._vp_aktion != "none":
            self._vp_reset_drag()
        self._vp_fenster = None
        if self._aktiver_viewport is not None:
            self._aktiver_viewport.aktiv = False
            self._aktiver_viewport = None
        if self.aktuelle_polylinie:
            self._polylinie_abschliessen(geschlossen=False)
        self.letzter_punkt = None
        self._pts = []
        self._viewport_modus = False
        self._snap_ausschluss = None
        self._snap_marker_loeschen()
        self._clear_temp()
        self._eingabe_zuruecksetzen()
        if self.aktives_werkzeug.get() != "auswahl":
            self.aktives_werkzeug.set("auswahl")
        self._update_kontext_widgets()
        self._update_eingabe_hinweis()
        self._viewport_modus_anzeige_aktualisieren()
        self.auswahl = []
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        self.status.set("Zurück zur Auswahl." if de else "Back to selection.")

    def _werkzeug_gewechselt(self):
        self.letzter_punkt = None
        self.aktuelle_polylinie = []
        self._pts = []
        self._op = None
        self._cmd_pending = None
        self._vp_fenster = None
        self._viewport_modus = False
        self._clear_temp()
        self._eingabe_zuruecksetzen()
        self._update_eingabe_hinweis()
        self._update_kontext_widgets()
        if self.aktives_werkzeug.get() != "auswahl":
            self.auswahl_leeren()
        de = SPRACHE["aktuell"] == "de"
        self.status.set(("Werkzeug: " if de else "Tool: ")
                        + self.aktives_werkzeug.get())

    def _clear_temp(self):
        self.temp_ids = []
        self.canvas.delete("vorschau")

    def farbe_waehlen(self):
        _, hexc = colorchooser.askcolor(color=self.zeichenfarbe)
        if hexc:
            self.zeichenfarbe = hexc
            self.farbe_btn.config(bg=hexc)
            self.eigene_farbe.set(True)

    def mm_to_px(self, x_mm, y_mm):
        v = self.view
        return (v["ox"] + x_mm * v["zoom"], v["oy"] - y_mm * v["zoom"])

    def px_to_mm(self, x_px, y_px):
        v = self.view
        return (x_px - v["ox"]) / v["zoom"], (v["oy"] - y_px) / v["zoom"]

    def _zeichne_raster(self):
        c = self.canvas
        c.delete("raster")
        if self._ist_layout():
            self._zeichne_blatt()
            return
        if not self.raster_sichtbar.get():
            return
        w = c.winfo_width() or 1200
        h = c.winfo_height() or 700
        v = self.view
        dunkel = ist_dunkel(self.bg_modell)
        if dunkel:
            farbe_punkt = "#322352"
            farbe_linie_klein = "#1c132d"
            farbe_linie_gross = "#2c1c47"
            farbe_achse = FARBEN["cyan"]
            rand_farbe = "#4a396b"
        else:
            farbe_punkt = "#555555"
            farbe_linie_klein = "#c8c8c8"
            farbe_linie_gross = "#909090"
            farbe_achse = FARBEN["cyan_dunkel"]
            rand_farbe = "#888888"
        step_px = max(0.01, self._zahl(self.raster_mm, 5.0)) * v["zoom"]
        while step_px < 12:
            step_px *= 5
        haupt_step = step_px * 5
        ox = v["ox"]
        oy = v["oy"]
        if self.raster_punktiert.get():
            x = ox - int(ox / step_px + 1) * step_px
            while x < w:
                y = oy - int(oy / step_px + 1) * step_px
                while y < h:
                    c.create_oval(x - 1.5, y - 1.5, x + 1.5, y + 1.5,
                                  fill=farbe_punkt, outline=rand_farbe,
                                  width=1, tags="raster")
                    y += step_px
                x += step_px
        else:
            x = ox - int(ox / step_px + 1) * step_px
            while x < w:
                ist_haupt = abs((x - ox) % haupt_step) < 2
                farbe = farbe_linie_gross if ist_haupt else farbe_linie_klein
                breite = 2 if ist_haupt else 1
                c.create_line(x, 0, x, h, fill=farbe, width=breite, tags="raster")
                x += step_px
            y = oy - int(oy / step_px + 1) * step_px
            while y < h:
                ist_haupt = abs((oy - y) % haupt_step) < 2
                farbe = farbe_linie_gross if ist_haupt else farbe_linie_klein
                breite = 2 if ist_haupt else 1
                c.create_line(0, y, w, y, fill=farbe, width=breite, tags="raster")
                y += step_px
        c.create_line(0, oy, w, oy, fill=farbe_achse, width=2, tags="raster")
        c.create_line(ox, 0, ox, h, fill=farbe_achse, width=2, tags="raster")
        c.tag_lower("raster")

    def _zeichne_blatt(self):
        c = self.canvas
        c.delete("blatt")
        b, h = ZEICHNUNGSFORMATE[self.layout_format]
        x1, y1 = self.mm_to_px(0, h)
        x2, y2 = self.mm_to_px(b, 0)
        c.create_rectangle(x1, y1, x2, y2, fill=self.bg_layout,
                           outline=FARBEN["cyan"],
                           width=2, tags="blatt")
        c.tag_lower("blatt")

    def _zoom_auf_maus(self, event, faktor):
        if self._ist_layout() and self._aktiver_viewport is not None:
            vp = self._aktiver_viewport
            if vp.gesperrt:
                de = SPRACHE["aktuell"] == "de"
                self.status.set("Viewport-Maßstab ist gesperrt." if de
                                else "Viewport scale is locked.")
                return
            mx_mm, my_mm = self.px_to_mm(event.x, event.y)
            if not (vp.x <= mx_mm <= vp.x + vp.breite and
                    vp.y <= my_mm <= vp.y + vp.hoehe):
                return
            self._vp_zoom_um_punkt(vp, faktor, (mx_mm, my_mm))
            self._viewport_modus_anzeige_aktualisieren()
            return
        v = self.view
        mx, my = event.x, event.y
        x_mm_vor = (mx - v["ox"]) / v["zoom"]
        y_mm_vor = (v["oy"] - my) / v["zoom"]
        v["zoom"] *= faktor
        v["ox"] = mx - x_mm_vor * v["zoom"]
        v["oy"] = my + y_mm_vor * v["zoom"]
        self.redraw()
        self._zeichne_raster()

    def _zoom(self, faktor):
        v = self.view
        cw = self.canvas.winfo_width() or 1000
        ch = self.canvas.winfo_height() or 700
        mx, my = cw / 2, ch / 2
        x_mm_vor = (mx - v["ox"]) / v["zoom"]
        y_mm_vor = (v["oy"] - my) / v["zoom"]
        v["zoom"] *= faktor
        v["ox"] = mx - x_mm_vor * v["zoom"]
        v["oy"] = my + y_mm_vor * v["zoom"]
        self.redraw()
        self._zeichne_raster()

    def _reset_view(self):
        cw = self.canvas.winfo_width() or 1000
        ch = self.canvas.winfo_height() or 700
        if not self._ist_layout():
            self.view_modell = {"zoom": 1.5, "ox": 100, "oy": ch - 50}
        else:
            self.layouts[self.aktives_layout].view = {"zoom": 1.5, "ox": 150,
                                                      "oy": ch - 50}
        self.redraw()
        self._zeichne_raster()

    def on_wheel(self, event):
        faktor = 1.1 if event.delta > 0 else 0.9
        self._zoom_auf_maus(event, faktor)

    def on_pan_start(self, event):
        v = self.view
        self.pan_start = (event.x, event.y, v["ox"], v["oy"])
        if self._ist_layout() and self._aktiver_viewport is not None:
            vp = self._aktiver_viewport
            self._vp_pan_start = (event.x, event.y,
                                  vp.modell_zentrum_x, vp.modell_zentrum_y)

    def on_pan(self, event):
        if self._rc_start and (abs(event.x - self._rc_start[0]) > 3 or abs(event.y - self._rc_start[1]) > 3):
            self._rc_bewegt = True
        if self._ist_layout() and self._aktiver_viewport is not None:
            vp = self._aktiver_viewport
            if vp.gesperrt:
                return
            if self._vp_pan_start is None:
                self._vp_pan_start = (event.x, event.y,
                                      vp.modell_zentrum_x, vp.modell_zentrum_y)
                return
            x0, y0, cx0, cy0 = self._vp_pan_start
            dx_px = event.x - x0
            dy_px = event.y - y0
            v = self.view
            dx_lay = dx_px / v["zoom"]
            dy_lay = -dy_px / v["zoom"]
            vp.modell_zentrum_x = cx0 - dx_lay / vp.zoom
            vp.modell_zentrum_y = cy0 - dy_lay / vp.zoom
            self.redraw()
            return
        if not self.pan_start:
            return
        x0, y0, ox, oy = self.pan_start
        v = self.view
        v["ox"] = ox + (event.x - x0)
        v["oy"] = oy + (event.y - y0)
        self.redraw()
        self._zeichne_raster()

    def on_pan_end(self, event):
        self.pan_start = None
        self._vp_pan_start = None

    def on_rechtsklick_start(self, event):
        self._rc_start = (event.x, event.y)
        self._rc_bewegt = False
        if self._paste_aktiv:
            self._paste_abbrechen()
            self.redraw()
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Einfügen abgebrochen." if de else "Paste cancelled.")
            return
        if self._cmd_pending is not None:
            self._cmd_pending = None
            self._update_eingabe_hinweis()
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Abgebrochen." if de else "Cancelled.")
            return
        if self._op is not None:
            self._op_rechtsklick()
            return
        if self._pts:
            self._pts = []
            self.letzter_punkt = None
            self.redraw()
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Abgebrochen." if de else "Cancelled.")
            return
        if self._vp_aktion != "none":
            return
        if self._ist_layout() and self._aktiver_viewport is not None:
            self.on_pan_start(event)
            return
        if self._ist_layout() and self._aktiver_viewport is None:
            vp = self._viewport_unter_maus(event)
            if vp is not None and self.aktives_werkzeug.get() == "auswahl":
                self._viewport_kontextmenu(event, vp)
                return
        if self.letzter_punkt is None and not self.aktuelle_polylinie:
            self.on_pan_start(event)

    def on_rechtsklick_end(self, event):
        if self.pan_start:
            self.pan_start = None
            self._vp_pan_start = None
            if (not self._rc_bewegt and self.aktives_werkzeug.get() == "auswahl"
                    and self._op is None and not self._pts
                    and self._ctx()[0] != "vp"
                    and not (self._ist_layout()
                             and self._aktiver_viewport is not None)):
                self._kontextmenue(event)
        else:
            if self.aktuelle_polylinie:
                self._polylinie_abschliessen(geschlossen=False)
            self.letzter_punkt = None
            self._pts = []
            self._clear_temp()
            self._eingabe_zuruecksetzen()
            self._update_eingabe_hinweis()

    def _viewport_kontextmenu(self, event, vp):
        stil = dict(tearoff=0, bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                    activebackground=FARBEN["cyan"],
                    activeforeground=FARBEN["bg_dunkel"])
        menu = tk.Menu(self.root, **stil)
        de = SPRACHE["aktuell"] == "de"
        menu.add_command(label=("Aktivieren (Modell bearbeiten)" if de
                                else "Activate (edit model)"),
                         command=lambda: self._vp_aktivieren(vp))
        menu.add_separator()
        ms = tk.Menu(menu, **stil)
        for m in MASSSTAEBE:
            ms.add_command(label=m, command=lambda m=m: self._vp_massstab_setzen(vp, m))
        menu.add_cascade(label=(f"Maßstab setzen (aktuell {massstab_text(vp.zoom)})" if de
                                else f"Set scale (current {massstab_text(vp.zoom)})"), menu=ms)
        menu.add_command(label=(("Maßstab " + ("entsperren" if vp.gesperrt else "sperren"))
                                if de else
                                ("Scale " + ("unlock" if vp.gesperrt else "lock"))),
                         command=lambda: self._vp_sperre_umschalten(vp))
        menu.add_command(label=("Ausschnitt per Fenster (exakt, Objektfang)" if de
                                else "View by window (exact, object snap)"),
                         command=lambda: self._vp_fenster_start(vp, False))
        menu.add_command(label=("Ausschnitt per Fenster + Normmaßstab" if de
                                else "View by window + standard scale"),
                         command=lambda: self._vp_fenster_start(vp, True))
        menu.add_command(label=("Ansicht an Modell anpassen (Auto-Fit)" if de
                                else "Fit view to model (auto-fit)"),
                         command=lambda: self._vp_auto_fit(vp))
        menu.add_command(label=("An Auswahl ausrichten" if de
                                else "Align to selection"),
                         command=lambda: self._vp_an_objekt(vp))
        menu.add_separator()
        menu.add_command(label=("Eigenschaften..." if de else "Properties..."),
                         command=lambda: self._vp_eigenschaften(vp))
        menu.add_command(label=("Löschen" if de else "Delete"),
                         command=lambda: self._vp_loeschen(vp))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _vp_aktivieren(self, vp):
        if self._aktiver_viewport is not None:
            self._aktiver_viewport.aktiv = False
        vp.aktiv = True
        self._aktiver_viewport = vp
        self._vp_modus_var.set("viewport")
        self.redraw()
        self._viewport_modus_anzeige_aktualisieren()
        de = SPRACHE["aktuell"] == "de"
        self.status.set(("Viewport aktiviert. ESC oder Layout-Ansicht zum "
                         "Verlassen." if de else
                         "Viewport activated. ESC or Layout view to leave."))

    def _vp_eigenschaften(self, vp):
        vorher = self._zustand()
        dlg = ViewportDialog(self.root, self, vp)
        if dlg.result:
            self._undo_stack.append(vorher)
            self._mark_dirty()
            self.redraw()
            self._viewport_modus_anzeige_aktualisieren()

    def _vp_loeschen(self, vp):
        de = SPRACHE["aktuell"] == "de"
        if messagebox.askyesno(
                ("Viewport löschen" if de else "Delete viewport"),
                ("Diesen Viewport entfernen?" if de else "Remove this viewport?")):
            self._snapshot()
            if vp in self.layout_elemente:
                self.layout_elemente.remove(vp)
            if self._aktiver_viewport is vp:
                self._aktiver_viewport = None
            self.redraw()
            self._viewport_modus_anzeige_aktualisieren()

    def _vp_auto_fit(self, vp):
        de = SPRACHE["aktuell"] == "de"
        if not self.elemente:
            messagebox.showinfo(
                ("Auto-Fit" if de else "Auto-fit"),
                ("Keine Modellelemente vorhanden." if de else "No model elements found."))
            return
        self._snapshot()
        xs, ys = [], []
        for el in self.elemente:
            b = el.bbox()
            xs.extend([b[0], b[2]])
            ys.extend([b[1], b[3]])
        if not xs:
            return
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        vp.modell_zentrum_x = (minx + maxx) / 2
        vp.modell_zentrum_y = (miny + maxy) / 2
        bw = maxx - minx
        bh = maxy - miny
        if bw > 1e-6 and bh > 1e-6:
            vp.zoom = min((vp.breite * 0.9) / bw, (vp.hoehe * 0.9) / bh)
        self.redraw()
        self.status.set(("Auto-Fit angewandt." if de else "Auto-fit applied."))

    def _vp_an_objekt(self, vp):
        de = SPRACHE["aktuell"] == "de"
        if not self.elemente:
            return
        objekte = ([el for el in self.auswahl if el in self.elemente]
                   if self.auswahl else self.elemente)
        if not objekte:
            messagebox.showinfo(
                ("An Objekt ausrichten" if de else "Align to object"),
                ("Bitte Element(e) im Modell auswählen." if de
                 else "Please select element(s) in the model."))
            return
        self._snapshot()
        xs, ys = [], []
        for el in objekte:
            b = el.bbox()
            xs.extend([b[0], b[2]])
            ys.extend([b[1], b[3]])
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        vp.modell_zentrum_x = (minx + maxx) / 2
        vp.modell_zentrum_y = (miny + maxy) / 2
        bw = maxx - minx
        bh = maxy - miny
        if bw > 1e-6 and bh > 1e-6:
            vp.zoom = min((vp.breite * 0.95) / bw, (vp.hoehe * 0.95) / bh)
        self.redraw()
        self.status.set(("Viewport an Auswahl ausgerichtet." if de
                         else "Viewport aligned to selection."))

    # --------------------------------------------------------
    # Objektfang
    # --------------------------------------------------------
    def _finde_snap_in_liste(self, liste, mx, my, tol, ref=None):
        modi = self.osnap_modi
        kand = []
        segs = []

        def sammle(x, y, typ, prio):
            d = math.hypot(x - mx, y - my)
            if d <= tol:
                kand.append((prio, d, x, y, typ))

        def ende(x, y):
            if modi["endpunkt"].get():
                sammle(x, y, "endpunkt", 0)

        def seg(x1, y1, x2, y2):
            segs.append((x1, y1, x2, y2))
            if modi["mittelpunkt"].get():
                sammle((x1 + x2) / 2, (y1 + y2) / 2, "mittelpunkt", 1)

        def zentrum(x, y):
            if modi["zentrum"].get():
                sammle(x, y, "zentrum", 2)

        def quadrant(x, y):
            if modi["quadrant"].get():
                sammle(x, y, "quadrant", 2)

        for el in liste:
            if el is self._snap_ausschluss:
                continue
            l = self.layers.get(el.layer)
            if l and not l.sichtbar:
                continue
            if isinstance(el, Linie):
                ende(el.x1, el.y1); ende(el.x2, el.y2)
                seg(el.x1, el.y1, el.x2, el.y2)
            elif isinstance(el, (Rechteck, Viewport)):
                if isinstance(el, Rechteck):
                    x1, y1, x2, y2 = el.x1, el.y1, el.x2, el.y2
                else:
                    x1, y1, x2, y2 = el.x, el.y, el.x + el.breite, el.y + el.hoehe
                ecken = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
                for (x, y) in ecken:
                    ende(x, y)
                for i in range(4):
                    seg(ecken[i][0], ecken[i][1],
                        ecken[(i + 1) % 4][0], ecken[(i + 1) % 4][1])
                if isinstance(el, Viewport):
                    zentrum((x1 + x2) / 2, (y1 + y2) / 2)
            elif isinstance(el, Polylinie):
                for (x, y) in el.punkte:
                    ende(x, y)
                pts = el.punkte + ([el.punkte[0]] if el.geschlossen else [])
                for i in range(len(pts) - 1):
                    seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
            elif isinstance(el, Kreis):
                zentrum(el.cx, el.cy)
                for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    quadrant(el.cx + dx * el.r, el.cy + dy * el.r)
                if modi["naechster"].get():
                    d = math.hypot(mx - el.cx, my - el.cy)
                    if d > 1e-9 and abs(d - el.r) <= tol:
                        sammle(el.cx + (mx - el.cx) / d * el.r,
                               el.cy + (my - el.cy) / d * el.r, "naechster", 5)
            elif isinstance(el, Bogen):
                zentrum(el.cx, el.cy)
                for a in (el.start, el.ende):
                    ende(el.cx + el.r * math.cos(math.radians(a)),
                         el.cy + el.r * math.sin(math.radians(a)))
                sw = bogen_sweep(el.start, el.ende)
                am = math.radians(el.start + sw / 2)
                if modi["mittelpunkt"].get():
                    sammle(el.cx + el.r * math.cos(am),
                           el.cy + el.r * math.sin(am), "mittelpunkt", 1)
                for q in (0, 90, 180, 270):
                    if winkel_im_bogen(q, el.start, el.ende):
                        quadrant(el.cx + el.r * math.cos(math.radians(q)),
                                 el.cy + el.r * math.sin(math.radians(q)))
                if modi["naechster"].get():
                    d = math.hypot(mx - el.cx, my - el.cy)
                    if d > 1e-9 and abs(d - el.r) <= tol:
                        w = math.degrees(math.atan2(my - el.cy, mx - el.cx))
                        if winkel_im_bogen(w, el.start, el.ende):
                            sammle(el.cx + (mx - el.cx) / d * el.r,
                                   el.cy + (my - el.cy) / d * el.r, "naechster", 5)
            elif isinstance(el, Text):
                ende(el.x, el.y)
            elif isinstance(el, Bemassung):
                ende(el.x1, el.y1); ende(el.x2, el.y2)

        if modi["naechster"].get() or (modi["lot"].get() and ref is not None):
            for (x1, y1, x2, y2) in segs:
                if modi["lot"].get() and ref is not None:
                    dx, dy = x2 - x1, y2 - y1
                    L2 = dx * dx + dy * dy
                    if L2 > 1e-18:
                        t = ((ref[0] - x1) * dx + (ref[1] - y1) * dy) / L2
                        if 0.0 <= t <= 1.0:
                            sammle(x1 + t * dx, y1 + t * dy, "lot", 4)
                if modi["naechster"].get():
                    nx, ny = naechster_punkt_segment(mx, my, x1, y1, x2, y2)
                    sammle(nx, ny, "naechster", 5)

        if modi["schnittpunkt"].get():
            nah = [s for s in segs
                   if abstand_punkt_segment(mx, my, *s) <= tol][:60]
            for i in range(len(nah)):
                for j in range(i + 1, len(nah)):
                    sp = linien_schnitt(*nah[i], *nah[j])
                    if sp:
                        sammle(sp[0], sp[1], "schnittpunkt", 3)

        if not kand:
            return None
        kand.sort(key=lambda k: (k[0], k[1]))
        _, _, x, y, typ = kand[0]
        return (x, y, typ)

    def _snap_ctx(self, x, y, ref=None):
        if not self.osnap.get():
            return None
        tol = 12.0 / self._ctx_skala()
        liste = self._ctx_liste()
        if self.aktuelle_polylinie and self.aktives_werkzeug.get() == "polylinie":
            liste = list(liste) + [Polylinie(list(self.aktuelle_polylinie))]
        return self._finde_snap_in_liste(liste, x, y, tol, ref)

    def _zeichne_snap_marker(self, x, y, typ):
        c = self.canvas
        self._snap_marker_loeschen()
        px, py = self._ctx_zu_px(x, y)
        s = 8
        g = FARBEN["gruen"]
        if typ == "endpunkt":
            c.create_rectangle(px - s, py - s, px + s, py + s,
                               outline=g, width=3, tags="snapmarker")
        elif typ == "mittelpunkt":
            c.create_polygon(px, py - s, px + s, py + s, px - s, py + s,
                             outline=g, width=3, fill="", tags="snapmarker")
        elif typ == "zentrum":
            c.create_oval(px - s, py - s, px + s, py + s,
                          outline=g, width=3, tags="snapmarker")
        elif typ == "quadrant":
            c.create_polygon(px, py - s, px + s, py, px, py + s, px - s, py,
                             outline=g, width=3, fill="", tags="snapmarker")
        elif typ == "schnittpunkt":
            c.create_line(px - s, py - s, px + s, py + s,
                          fill=g, width=3, tags="snapmarker")
            c.create_line(px - s, py + s, px + s, py - s,
                          fill=g, width=3, tags="snapmarker")
        elif typ == "lot":
            c.create_line(px - s, py + s, px - s, py - s, px + s, py - s,
                          fill=g, width=3, tags="snapmarker")
            c.create_line(px - s, py, px, py, px, py - s,
                          fill=g, width=2, tags="snapmarker")
        else:
            c.create_line(px - s, py - s, px + s, py - s, px - s, py + s,
                          px + s, py + s, px - s, py - s,
                          fill=g, width=3, tags="snapmarker")
        label = tr(f"osnap.{typ}")
        c.create_text(px + 16, py - 16, text=label, anchor=tk.SW,
                      fill=FARBEN["bg_dunkel"], font=("Segoe UI", 9, "bold"),
                      tags="snapmarker")
        c.create_text(px + 15, py - 17, text=label, anchor=tk.SW,
                      fill=FARBEN["gelb"], font=("Segoe UI", 9, "bold"),
                      tags="snapmarker")

    def _snap_marker_loeschen(self):
        self.canvas.delete("snapmarker")
        self._snap_punkt_aktuell = None

    def _fadenkreuz(self, x_px, y_px):
        c = self.canvas
        c.delete("fadenkreuz")
        w = c.winfo_width() or 1200
        h = c.winfo_height() or 700
        c.create_line(0, y_px, w, y_px, fill=FARBEN["cyan"], dash=(3, 5),
                      tags="fadenkreuz")
        c.create_line(x_px, 0, x_px, h, fill=FARBEN["cyan"], dash=(3, 5),
                      tags="fadenkreuz")

    def on_move(self, event):
        self._maus_px = (event.x, event.y)
        einh = self._einh_faktor()
        unit = self.einheit.get()
        if self._griff_drag_el is not None and self._griff_drag_id is not None:
            self._griff_bewegen_zu(event)
            return
        if self._paste_aktiv:
            self._paste_vorschau_aktualisieren(event.x, event.y)
            ziel = self._paste_maus_mm
            de = SPRACHE["aktuell"] == "de"
            self.status.set(
                (f"[EINFÜGEN]  X = {ziel[0] / einh:8.2f} {unit}   "
                 f"Y = {ziel[1] / einh:8.2f} {unit}   |   "
                 f"Klick = platzieren, ESC = abbrechen" if de else
                 f"[PASTE]  X = {ziel[0] / einh:8.2f} {unit}   "
                 f"Y = {ziel[1] / einh:8.2f} {unit}   |   "
                 f"Click = place, ESC = cancel"))
            return
        if self._warte_auf_basispunkt:
            x, y = self._eingabepunkt(event)
            de = SPRACHE["aktuell"] == "de"
            self.status.set(
                (f"Basispunkt setzen: X = {x / einh:.2f}  Y = {y / einh:.2f}  |  "
                 "Klick = bestätigen, ESC = abbrechen" if de else
                 f"Set base point: X = {x / einh:.2f}  Y = {y / einh:.2f}  |  "
                 "Click = confirm, ESC = cancel"))
            self._fadenkreuz(event.x, event.y)
            return
        if self._drag_modus == "auswahl_rechteck" and self._auswahl_rechteck_start:
            self._zeichne_auswahl_rechteck(event)
            return
        if self._vp_aktion != "none" and self._vp_el is not None:
            self._vp_drag_vorschau(event)
            return
        pt = self._eingabepunkt(event, self.letzter_punkt)
        self._fadenkreuz(event.x, event.y)
        werkzeug_aktiv = (self.aktives_werkzeug.get() != "auswahl"
                          or self._viewport_modus or self._vp_fenster is not None
                          or self._op is not None)
        if werkzeug_aktiv and (self.letzter_punkt is not None or self._pts
                               or self.aktuelle_polylinie):
            self._werkzeug_vorschau(pt)
        kind, vp = self._ctx()
        de = SPRACHE["aktuell"] == "de"
        modus_info = ""
        if kind == "vp":
            modus_info = (
                (f"   |   [VIEWPORT AKTIV  {massstab_text(vp.zoom)}"
                 f"{' gesperrt' if vp.gesperrt else ''}]" if de else
                 f"   |   [VIEWPORT ACTIVE  {massstab_text(vp.zoom)}"
                 f"{' locked' if vp.gesperrt else ''}]"))
        elif kind == "layout" and self._viewport_unter_maus(event) is not None:
            modus_info = (
                ("   |   [Viewport: Rechtsklick für Menü, Doppelklick = aktivieren]"
                 if de else
                 "   |   [Viewport: right-click for menu, double-click = activate]"))
        ansicht_name = (self.layout.name if self._ist_layout() else
                        ("Modell" if de else "Model"))
        self.status.set(
            f"[{ansicht_name}]  "
            f"X = {pt[0] / einh:8.2f} {unit}   Y = {pt[1] / einh:8.2f} {unit}   |   "
            f"Zoom {self.view['zoom']:.2f}   |   "
            f"{'Layer' if de else 'Layer'}: {self.aktiver_layer.get()}   |   "
            f"{'Auswahl' if de else 'Selected'}: {len(self.auswahl)}   |   "
            f"OFang: {'AN' if self.osnap.get() else 'AUS'}   "
            f"{'Fang' if de else 'Snap'}: {'AN' if self.grid_snap.get() else 'AUS'} "
            f"({self._zahl(self.fang_mm, 5):g})   "
            f"Ortho: {'AN' if self.ortho.get() else 'AUS'}" + modus_info)

    def _vp_drag_bestaetigen(self):
        vp = self._vp_el
        if vp is None or self._vp_start_rect is None or self._vp_letzter_pt is None:
            self._vp_reset_drag()
            return
        x, y, bw, bh = self._vp_neues_rect(self._vp_letzter_pt)
        self._snapshot()
        vp.x, vp.y, vp.breite, vp.hoehe = x, y, bw, bh
        self._vp_reset_drag()
        self._snap_marker_loeschen()
        self.redraw()

    def _vp_reset_drag(self):
        self._vp_aktion = "none"
        self._vp_el = None
        self._vp_ecke = None
        self._vp_start_mm = None
        self._vp_start_rect = None
        self._vp_letzter_pt = None
        self._snap_ausschluss = None
        self.canvas.delete("vp_vorschau")

    def _vp_griff_unter_maus(self, event):
        if not self._ist_layout():
            return None, None
        x_mm, y_mm = self.px_to_mm(event.x, event.y)
        tol = 9.0 / self.view["zoom"]
        for el in reversed(self.layout_elemente):
            if not isinstance(el, Viewport):
                continue
            ecken = {"nw": (el.x, el.y + el.hoehe),
                     "ne": (el.x + el.breite, el.y + el.hoehe),
                     "sw": (el.x, el.y), "se": (el.x + el.breite, el.y)}
            for name, (ex, ey) in ecken.items():
                if abs(x_mm - ex) <= tol and abs(y_mm - ey) <= tol:
                    return el, name
        return None, None

    def _vp_vorschau_zeichnen(self, x, y, breite, hoehe):
        self.canvas.delete("vp_vorschau")
        px1, py1 = self.mm_to_px(x, y + hoehe)
        px2, py2 = self.mm_to_px(x + breite, y)
        self.canvas.create_rectangle(px1, py1, px2, py2,
                                     outline=FARBEN["orange"], width=3,
                                     dash=(5, 3), tags="vp_vorschau")
        mx = (px1 + px2) / 2
        my = (py1 + py2) / 2
        self.canvas.create_text(mx, my,
                                text=f"{breite:.1f} x {hoehe:.1f} mm",
                                fill=FARBEN["gelb"], font=("Segoe UI", 9, "bold"),
                                tags="vp_vorschau")

    def _aktuelle_elemente_liste(self):
        return self._ctx_liste()

    def _element_unter_maus(self, x_mm, y_mm, toleranz_mm):
        liste = self._aktuelle_elemente_liste()
        for el in reversed(liste):
            l = self.layers.get(el.layer)
            if l and not l.sichtbar:
                continue
            if self._punkt_auf_element(el, x_mm, y_mm, toleranz_mm):
                return el
        return None

    def _punkt_auf_element(self, el, x_mm, y_mm, tol):
        if isinstance(el, Viewport):
            return (el.x <= x_mm <= el.x + el.breite and
                    el.y <= y_mm <= el.y + el.hoehe)
        if isinstance(el, Text):
            return el.punkt_im_rahmen(x_mm, y_mm, tol)
        if isinstance(el, Kreis):
            return abs(math.hypot(x_mm - el.cx, y_mm - el.cy) - el.r) <= tol
        if isinstance(el, Bogen):
            if abs(math.hypot(x_mm - el.cx, y_mm - el.cy) - el.r) > tol:
                return False
            w = math.degrees(math.atan2(y_mm - el.cy, x_mm - el.cx))
            if winkel_im_bogen(w, el.start, el.ende):
                return True
            for a in (el.start, el.ende):
                ex = el.cx + el.r * math.cos(math.radians(a))
                ey = el.cy + el.r * math.sin(math.radians(a))
                if math.hypot(ex - x_mm, ey - y_mm) <= tol:
                    return True
            return False
        for pts, geschlossen in self._el_polylinien(el, self.view["zoom"]):
            if isinstance(el, (Text,)):
                continue
            p = pts + ([pts[0]] if geschlossen and len(pts) > 2 else [])
            for i in range(len(p) - 1):
                if abstand_punkt_segment(x_mm, y_mm, p[i][0], p[i][1],
                                         p[i + 1][0], p[i + 1][1]) <= tol:
                    return True
        if isinstance(el, Bemassung):
            g = el.geometrie(self._einh_faktor(), self.dezimalkomma.get())
            if g["text"]:
                _, cx, cy, ang, w, h = g["text"]
                return punkt_in_gedrehtem_rechteck(x_mm, y_mm, cx, cy, w, h, ang, tol)
        return False

    def auswahl_leeren(self):
        self.auswahl = []
        self.redraw()

    def auswahl_loeschen(self):
        if not self.auswahl:
            return
        self._snapshot()
        liste = self._aktuelle_elemente_liste()
        for el in self.auswahl:
            if el in liste:
                liste.remove(el)
        n = len(self.auswahl)
        self.auswahl = []
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        self.status.set((f"{n} Element(e) gelöscht." if de
                         else f"{n} element(s) deleted."))

    def alle_markieren(self):
        liste = self._aktuelle_elemente_liste()
        self.auswahl = [el for el in liste
                        if self.layers.get(el.layer) is None or
                        self.layers.get(el.layer).sichtbar]
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        self.status.set((f"{len(self.auswahl)} Element(e) markiert." if de
                         else f"{len(self.auswahl)} element(s) selected."))

    def _zeichne_auswahl_rechteck(self, event):
        if not self._auswahl_rechteck_start:
            return
        x0_px, y0_px, x0_mm, y0_mm = self._auswahl_rechteck_start
        x1_px, y1_px = event.x, event.y
        x1_mm, y1_mm = self.px_to_mm(x1_px, y1_px)
        if x1_px < x0_px:
            farbe = FARBEN["cyan"]
            self._auswahl_richtung = "links"
        else:
            farbe = FARBEN["gruen"]
            self._auswahl_richtung = "rechts"
        if self._auswahl_rechteck_id:
            self.canvas.delete(self._auswahl_rechteck_id)
        self._auswahl_rechteck_id = self.canvas.create_rectangle(
            x0_px, y0_px, x1_px, y1_px,
            outline=farbe, width=2, dash=(5, 3), tags="auswahlrechteck")
        bbox = (min(x0_mm, x1_mm), min(y0_mm, y1_mm),
                max(x0_mm, x1_mm), max(y0_mm, y1_mm))
        vorschau = self._elemente_im_auswahlrechteck(bbox, self._auswahl_richtung)
        self.canvas.delete("auswahlvorschau")
        for el in vorschau:
            self._zeichne_auswahl_highlight(el, farbe=FARBEN["magenta"],
                                            tags="auswahlvorschau")

    def _elemente_im_auswahlrechteck(self, bbox, richtung):
        treffer = []
        liste = self._aktuelle_elemente_liste()
        for el in liste:
            l = self.layers.get(el.layer)
            if l and not l.sichtbar:
                continue
            el_bbox = el.bbox()
            if richtung == "links":
                if bbox_enthalten(bbox, el_bbox):
                    treffer.append(el)
            else:
                if bbox_ueberlappt(bbox, el_bbox):
                    treffer.append(el)
        return treffer

    def _zeichne_auswahl_highlight(self, el, farbe=None, tags=("element",)):
        if farbe is None:
            farbe = FARBEN["magenta"]
        c = self.canvas
        if isinstance(el, Viewport):
            x1, y1 = self.mm_to_px(el.x, el.y + el.hoehe)
            x2, y2 = self.mm_to_px(el.x + el.breite, el.y)
            c.create_rectangle(x1 - 2, y1 - 2, x2 + 2, y2 + 2,
                               outline=farbe, width=3, dash=(3, 3), tags=tags)
            return
        papier = self.view["zoom"] if self._ist_layout() else None
        w = self._lw_px(self._effektive_staerke_mm(el), papier) + 5
        for pts, geschlossen in self._el_polylinien(el, self.view["zoom"]):
            px = [self.mm_to_px(x, y) for (x, y) in pts]
            if geschlossen and len(px) > 2:
                px.append(px[0])
            for teil in clip_polyline(px, self._sicht_rect()):
                flat = [v for q in teil for v in q]
                c.create_line(*flat, fill=FARBEN["magenta"], width=w, tags=tags,
                              capstyle=tk.ROUND, joinstyle=tk.ROUND)
                c.create_line(*flat, fill=farbe, width=1, dash=(4, 3), tags=tags)

    def _zeichne_auswahl_highlights(self):
        self.canvas.delete("auswahl_highlight")
        self.canvas.delete("griffe")
        for el in self.auswahl:
            self._zeichne_auswahl_highlight(el, farbe=FARBEN["cyan"],
                                            tags=("element", "auswahl_highlight"))
        self.canvas.tag_lower("auswahl_highlight")
        for el in self.auswahl:
            self._zeichne_griffe(el)

    def _zeichne_griffe(self, el):
        c = self.canvas
        try:
            griffe = el.griffe()
        except Exception:
            griffe = []
        for (gid, x, y) in griffe:
            px, py = self.mm_to_px(x, y)
            r = GRIFF_RADIUS
            c.create_rectangle(px - r, py - r, px + r, py + r,
                               fill=FARBEN["gelb"],
                               outline=FARBEN["bg_dunkel"], width=1,
                               tags="griffe")

    def _griff_unter_maus(self, event):
        x_mm, y_mm = self.px_to_mm(event.x, event.y)
        tol_mm = max(0.01, 8 / self.view["zoom"])
        for el in reversed(self.auswahl):
            if isinstance(el, Viewport):
                continue
            try:
                griffe = el.griffe()
            except Exception:
                continue
            for (gid, gx, gy) in griffe:
                if abs(x_mm - gx) <= tol_mm and abs(y_mm - gy) <= tol_mm:
                    return el, gid
        return None, None

    def on_click(self, event):
        if self._vp_aktion != "none":
            return
        if self._warte_auf_basispunkt:
            x, y = self._eingabepunkt(event)
            self._basispunkt_setzen(x, y)
            return
        if self._paste_aktiv:
            self._paste_vorschau_aktualisieren(event.x, event.y)
            self._paste_platzieren()
            return
        if (self._op is not None and self._op["typ"] == "stretch"
                and self._op["stufe"] == "fenster"):
            self.auswahl_rechteck_start(event)
            return
        if self._op is not None and self._op["stufe"] in ("basis", "ziel"):
            pt = self._eingabepunkt(event, self.letzter_punkt)
            self._op_klick(pt)
            self.entry_eingabe.focus_set()
            return
        werkzeug = self.aktives_werkzeug.get()
        kind, vp = self._ctx()
        if self._viewport_modus and kind == "layout":
            x, y = self._eingabepunkt(event, self.letzter_punkt)
            self._click_viewport_aufziehen(x, y)
            return
        if self._vp_fenster is not None and kind == "vp":
            x, y = self._eingabepunkt(event, self.letzter_punkt)
            self._vp_fenster_klick(x, y)
            return
        if werkzeug != "auswahl":
            if (werkzeug == "bemassung" and not self._pts
                    and self.bem_art.get() in ("radius", "durchmesser")):
                pt = self._px_zu_ctx(event.x, event.y)
            else:
                pt = self._eingabepunkt(event, self.letzter_punkt)
            self._zeichnen_werkzeug_anwenden(*pt)
            self._update_eingabe_hinweis()
            self.entry_eingabe.focus_set()
            return
        if kind == "vp":
            return
        el_griff, gid = self._griff_unter_maus(event)
        if el_griff is not None:
            self._snapshot()
            self._griff_drag_el = el_griff
            self._griff_drag_id = gid
            self._snap_ausschluss = el_griff
            return
        x_mm, y_mm = self.px_to_mm(event.x, event.y)
        tol_mm = 8 / self.view["zoom"]
        if kind == "layout":
            vpg, ecke = self._vp_griff_unter_maus(event)
            if vpg is not None:
                self._vp_aktion = "resize"
                self._vp_el = vpg
                self._vp_ecke = ecke
                self._vp_start_mm = (x_mm, y_mm)
                self._vp_start_rect = (vpg.x, vpg.y, vpg.breite, vpg.hoehe)
                self._vp_letzter_pt = None
                self._snap_ausschluss = vpg
                return
        el = self._element_unter_maus(x_mm, y_mm, tol_mm)
        if isinstance(el, Viewport):
            if el in self.auswahl:
                self._vp_start_move(el, x_mm, y_mm)
            else:
                self.auswahl = [el]
                self.redraw()
            return
        if el:
            if el in self.auswahl:
                self.auswahl.remove(el)
            else:
                self.auswahl.append(el)
            self.redraw()
            de = SPRACHE["aktuell"] == "de"
            self.status.set((f"{len(self.auswahl)} Element(e) markiert." if de
                             else f"{len(self.auswahl)} element(s) selected."))
            return
        self.auswahl_rechteck_start(event)

    def _zeichnen_werkzeug_anwenden(self, x_mm, y_mm):
        werkzeug = self.aktives_werkzeug.get()
        pt = (x_mm, y_mm)
        lp = self.letzter_punkt
        if werkzeug == "linie":
            if lp is None:
                self.letzter_punkt = pt
            elif math.hypot(x_mm - lp[0], y_mm - lp[1]) > 1e-9:
                self._snapshot()
                self._ziel_liste().append(self._neue_linie(lp[0], lp[1], x_mm, y_mm))
                self.letzter_punkt = None
                self.redraw()
        elif werkzeug == "polylinie":
            if lp is None or not self.aktuelle_polylinie:
                self.aktuelle_polylinie = [pt]
            else:
                p0 = self.aktuelle_polylinie[0]
                if (len(self.aktuelle_polylinie) >= 3
                        and math.hypot(pt[0] - p0[0], pt[1] - p0[1]) < 1e-9):
                    self._polylinie_abschliessen(geschlossen=True)
                    return
                if math.hypot(pt[0] - lp[0], pt[1] - lp[1]) < 1e-9:
                    return
                self.aktuelle_polylinie.append(pt)
            self.letzter_punkt = pt
        elif werkzeug == "kreis":
            if lp is None:
                self.letzter_punkt = pt
            else:
                r = math.hypot(x_mm - lp[0], y_mm - lp[1])
                if r > 1e-9:
                    self._snapshot()
                    self._ziel_liste().append(self._neuer_kreis(lp[0], lp[1], r))
                    self.letzter_punkt = None
                    self.redraw()
        elif werkzeug == "rechteck":
            if lp is None:
                self.letzter_punkt = pt
            elif abs(x_mm - lp[0]) > 1e-9 and abs(y_mm - lp[1]) > 1e-9:
                self._snapshot()
                self._ziel_liste().append(self._neues_rechteck(lp[0], lp[1], x_mm, y_mm))
                self.letzter_punkt = None
                self.redraw()
        elif werkzeug == "bogen":
            self._bogen_klick(pt)
        elif werkzeug == "bemassung":
            self._bem_klick(pt)
        elif werkzeug == "text":
            self._text_einfuegen(x_mm, y_mm)

    def _click_viewport_aufziehen(self, x_mm, y_mm):
        if self.letzter_punkt is None:
            self.letzter_punkt = (x_mm, y_mm)
            de = SPRACHE["aktuell"] == "de"
            self.status.set(("Viewport: Gegenüberliegende Ecke setzen "
                             "(Objektfang aktiv)." if de else
                             "Viewport: set opposite corner (object snap active)."))
            return
        x1, y1 = self.letzter_punkt
        bw, bh = abs(x_mm - x1), abs(y_mm - y1)
        if bw < 5 or bh < 5:
            self.letzter_punkt = None
            self._clear_temp()
            return
        self._snapshot()
        cx_m, cy_m = self._modell_zentrum()
        zoom = normmassstab_unter(self._berechne_fit_zoom(bw, bh), MASSSTAEBE)
        vp = Viewport(min(x1, x_mm), min(y1, y_mm), bw, bh,
                      modell_zentrum_x=cx_m, modell_zentrum_y=cy_m, zoom=zoom,
                      layer="0", farbe=FARBEN["cyan"], linientyp="Volllinie (schmal)")
        self.layout_elemente.append(vp)
        self.letzter_punkt = None
        self._viewport_modus = False
        self._clear_temp()
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        self.status.set(
            (f"Viewport platziert (Maßstab {massstab_text(zoom)}). Rechtsklick "
             "auf den Viewport für Maßstab/Ausschnitt." if de else
             f"Viewport placed (scale {massstab_text(zoom)}). Right-click the "
             "viewport for scale/view."))

    def _berechne_fit_zoom(self, vp_bw, vp_bh):
        if not self.elemente:
            return 1.0
        xs, ys = [], []
        for el in self.elemente:
            b = el.bbox()
            xs.extend([b[0], b[2]])
            ys.extend([b[1], b[3]])
        if not xs:
            return 1.0
        modell_bw = max(xs) - min(xs)
        modell_bh = max(ys) - min(ys)
        if modell_bw < 1e-6 or modell_bh < 1e-6:
            return 1.0
        return min((vp_bw * 0.9) / modell_bw, (vp_bh * 0.9) / modell_bh)

    def auswahl_rechteck_start(self, event):
        x0_mm, y0_mm = self.px_to_mm(event.x, event.y)
        self._auswahl_rechteck_start = (event.x, event.y, x0_mm, y0_mm)
        self._drag_modus = "auswahl_rechteck"
        self._auswahl_richtung = None

    def on_doppelklick(self, event):
        if self._paste_aktiv:
            self._paste_abbrechen()
            self.redraw()
            return
        if (self._pts or self._viewport_modus or self._vp_fenster is not None
                or self.aktives_werkzeug.get() != "auswahl"):
            return
        kind, vp = self._ctx()
        if kind == "vp":
            return
        x_mm, y_mm = self.px_to_mm(event.x, event.y)
        el = self._element_unter_maus(x_mm, y_mm, 8 / self.view["zoom"])
        if isinstance(el, Viewport):
            self._vp_aktivieren(el)
            return
        if not el:
            return
        vorher = self._zustand()
        dlg = PropertiesDialog(self.root, self, el)
        if dlg.result:
            self._undo_stack.append(vorher)
            self._mark_dirty()
            self.redraw()

    def _viewport_unter_maus(self, event):
        x_mm, y_mm = self.px_to_mm(event.x, event.y)
        for el in reversed(self.layout_elemente):
            if isinstance(el, Viewport):
                if el.x <= x_mm <= el.x + el.breite and \
                        el.y <= y_mm <= el.y + el.hoehe:
                    return el
        return None

    def _text_einfuegen(self, x_mm, y_mm):
        dlg = TextDialog(self.root, self)
        if not dlg.result:
            return
        inhalt, hoehe, winkel, schriftart, einfuegepunkt = dlg.result
        self.text_hoehe.set(hoehe)
        self.text_winkel.set(winkel)
        self.text_schriftart.set(schriftart)
        self._snapshot()
        daten = self._layer_daten()
        if "Schrift" in self.layers:
            daten["layer"] = "Schrift"
            daten["farbe"] = self.layers["Schrift"].farbe
        daten["eig_farbe"] = True
        daten["staerke"] = None
        self._ziel_liste().append(
            Text(x_mm, y_mm, inhalt, hoehe, winkel, schriftart,
                 einfuegepunkt=einfuegepunkt, **daten))
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        self.status.set((f"Text eingefügt: '{inhalt[:30]}'" if de
                         else f"Text inserted: '{inhalt[:30]}'"))

    def _modell_zentrum(self):
        if not self.elemente:
            return (0.0, 0.0)
        xs, ys = [], []
        for el in self.elemente:
            b = el.bbox()
            xs.extend([b[0], b[2]])
            ys.extend([b[1], b[3]])
        if not xs:
            return (0.0, 0.0)
        return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)

    def on_drag_b1(self, event):
        self._maus_px = (event.x, event.y)
        if self._griff_drag_el is not None:
            self._griff_bewegen_zu(event)
            return
        if self._paste_aktiv:
            self._paste_vorschau_aktualisieren(event.x, event.y)
            return
        if self._drag_modus == "auswahl_rechteck":
            self._zeichne_auswahl_rechteck(event)
            return
        if self._vp_aktion != "none" and self._vp_el is not None:
            self._vp_drag_vorschau(event)
            return

    def on_release(self, event):
        if self._griff_drag_el is not None:
            self._griff_drag_el = None
            self._griff_drag_id = None
            self._snap_ausschluss = None
            self._snap_marker_loeschen()
            self.redraw()
            return
        if self._paste_aktiv:
            return
        if self._drag_modus == "auswahl_rechteck":
            self._finalisiere_auswahl_rechteck(event)
        if self._vp_aktion != "none":
            self._maus_px = (event.x, event.y)
            self._vp_drag_bestaetigen()

    def _finalisiere_auswahl_rechteck(self, event):
        if not self._auswahl_rechteck_start:
            return
        x0_px, y0_px, x0_mm, y0_mm = self._auswahl_rechteck_start
        x1_px, y1_px = event.x, event.y
        x1_mm, y1_mm = self.px_to_mm(x1_px, y1_px)
        if (self._op is not None and self._op["typ"] == "stretch"
                and self._op["stufe"] == "fenster"):
            if abs(x1_px - x0_px) < 4 and abs(y1_px - y0_px) < 4:
                self._auswahl_rechteck_start = None
                self._drag_modus = None
                if self._auswahl_rechteck_id:
                    self.canvas.delete(self._auswahl_rechteck_id)
                    self._auswahl_rechteck_id = None
                self.canvas.delete("auswahlvorschau")
                return
            bbox = (min(x0_mm, x1_mm), min(y0_mm, y1_mm),
                    max(x0_mm, x1_mm), max(y0_mm, y1_mm))
            self._op["fenster"] = bbox
            self._op["stufe"] = "basis"
            self._auswahl_rechteck_start = None
            self._drag_modus = None
            if self._auswahl_rechteck_id:
                self.canvas.delete(self._auswahl_rechteck_id)
                self._auswahl_rechteck_id = None
            self.canvas.delete("auswahlvorschau")
            self.auswahl = self._elemente_im_auswahlrechteck(bbox, "rechts")
            self.redraw()
            self._op_hinweis()
            return
        if abs(x1_px - x0_px) < 4 and abs(y1_px - y0_px) < 4:
            self.auswahl_leeren()
        else:
            bbox = (min(x0_mm, x1_mm), min(y0_mm, y1_mm),
                    max(x0_mm, x1_mm), max(y0_mm, y1_mm))
            richtung = "links" if x1_px < x0_px else "rechts"
            treffer = self._elemente_im_auswahlrechteck(bbox, richtung)
            self.auswahl = treffer
            de = SPRACHE["aktuell"] == "de"
            self.status.set(
                (f"{len(self.auswahl)} Element(e) markiert "
                 f"({'komplett' if richtung == 'links' else 'berührt'})." if de
                 else f"{len(self.auswahl)} element(s) selected "
                 f"({'fully' if richtung == 'links' else 'crossing'})."))
        self._auswahl_rechteck_start = None
        self._drag_modus = None
        self._auswahl_richtung = None
        if self._auswahl_rechteck_id:
            self.canvas.delete(self._auswahl_rechteck_id)
            self._auswahl_rechteck_id = None
        self.canvas.delete("auswahlvorschau")
        self.redraw()

    def _polylinie_abschliessen(self, geschlossen=False):
        if len(self.aktuelle_polylinie) >= 2:
            self._snapshot()
            self._ziel_liste().append(Polylinie(self.aktuelle_polylinie,
                                                geschlossen=geschlossen,
                                                **self._layer_daten()))
        self.aktuelle_polylinie = []
        self.letzter_punkt = None
        self.redraw()

    def redraw(self):
        c = self.canvas
        for tag in ("element", "blatt", "layout", "auswahl_highlight",
                    "vp_griffe", "griffe"):
            c.delete(tag)
        self._clear_temp()
        if not self._ist_layout():
            for el in self.elemente:
                l = self.layers.get(el.layer)
                if l and not l.sichtbar:
                    continue
                self._zeichne_element(el)
            self._zeichne_auswahl_highlights()
            self._zeichne_raster()
        else:
            self._zeichne_blatt()
            for el in self.layout_elemente:
                self._zeichne_layout_element(el)
            self._zeichne_auswahl_highlights()
            for el in self.auswahl:
                if isinstance(el, Viewport):
                    self._zeichne_viewport_griffe(el)
            c.tag_lower("blatt")
        self._vorschau_neu()
        c.tag_raise("snapmarker")

    def _zeichne_viewport_griffe(self, vp):
        c = self.canvas
        ecken = [(vp.x, vp.y), (vp.x + vp.breite, vp.y),
                 (vp.x, vp.y + vp.hoehe), (vp.x + vp.breite, vp.y + vp.hoehe)]
        for (ex, ey) in ecken:
            px, py = self.mm_to_px(ex, ey)
            r = GRIFF_RADIUS
            c.create_rectangle(px - r, py - r, px + r, py + r,
                               fill=FARBEN["orange"],
                               outline=FARBEN["bg_dunkel"], width=1,
                               tags="vp_griffe")

    def _effektive_zeichenfarbe(self, el):
        l = self.layers.get(el.layer)
        farbe = el.farbe if (el.eig_farbe or l is None) else l.farbe
        bg = self.bg_modell if not self._ist_layout() else self.bg_layout
        if ist_dunkel(bg) and farbe.lower() in ("#000000", "#000", "black"):
            return "#ffffff"
        return farbe

    def _effektive_staerke_mm(self, el):
        if getattr(el, "staerke", None) is not None:
            return el.staerke
        l = self.layers.get(el.layer)
        basis = l.staerke if l else 0.35
        if "breit" in (el.linientyp or ""):
            return max(basis * 2, 0.7)
        return basis

    def _zeichne_element(self, el, tags=("element",), tf=None, skala=None,
                         clip=None, stil=None):
        tf = tf or self.mm_to_px
        sk = skala if skala is not None else self.view["zoom"]
        clip = clip or self._sicht_rect()
        if stil:
            farbe, w, dash = stil["farbe"], stil["w"], stil.get("dash")
        else:
            farbe = self._effektive_zeichenfarbe(el)
            lt = LINIENTYPEN.get(el.linientyp, LINIENTYPEN["Volllinie (schmal)"])
            dash = None if isinstance(el, (Bemassung, Text)) else lt["dash"]
            papier = self.view["zoom"] if self._ist_layout() else None
            w = self._lw_px(self._effektive_staerke_mm(el), papier)
            if isinstance(el, Bemassung):
                w = max(1, min(w, 2))
        self._zeichne_prims(self._prims(el, sk), farbe, w, dash, tf, sk, tags, clip)

    def _zeichne_layout_element(self, el):
        c = self.canvas
        l = self.layers.get(el.layer)
        if l and not l.sichtbar:
            return
        if isinstance(el, Viewport):
            x1, y1 = self.mm_to_px(el.x, el.y + el.hoehe)
            x2, y2 = self.mm_to_px(el.x + el.breite, el.y)
            rahmen_farbe = FARBEN["magenta"] if el.aktiv else FARBEN["cyan"]
            rahmen_breite = 3 if el.aktiv else 2
            c.create_rectangle(x1, y1, x2, y2, outline=rahmen_farbe,
                               width=rahmen_breite, tags="layout")
            self._zeichne_viewport_inhalt(el, (x1, y1, x2, y2))
        else:
            self._zeichne_element(el, tags=("layout",))

    def _zeichne_viewport_inhalt(self, vp, bbox_px):
        x1_px, y1_px, x2_px, y2_px = bbox_px
        clip = (min(x1_px, x2_px), min(y1_px, y2_px),
                max(x1_px, x2_px), max(y1_px, y2_px))
        skala = self.view["zoom"] * vp.zoom
        vcx, vcy = self.mm_to_px(vp.x + vp.breite / 2, vp.y + vp.hoehe / 2)

        def tf(mx, my):
            return (vcx + (mx - vp.modell_zentrum_x) * skala,
                    vcy - (my - vp.modell_zentrum_y) * skala)

        for me in self.elemente:
            l = self.layers.get(me.layer)
            if l and not l.sichtbar:
                continue
            b = me.bbox()
            ax, ay = tf(b[0], b[1])
            bx, by = tf(b[2], b[3])
            if (max(ax, bx) < clip[0] or min(ax, bx) > clip[2] or
                    max(ay, by) < clip[1] or min(ay, by) > clip[3]):
                continue
            self._zeichne_element(me, tags=("layout",), tf=tf, skala=skala, clip=clip)

    def rahmen_einfuegen(self):
        if not self._ist_layout():
            self.status.set("Rahmen nur im Layout möglich.")
            return
        self._snapshot()
        b, h = ZEICHNUNGSFORMATE[self.layout_format]
        basis = {"layer": "0", "farbe": FARBEN["cyan"],
                 "linientyp": "Volllinie (breit)", "eig_farbe": True, "staerke": 0.7}
        basis2 = {"layer": "0", "farbe": FARBEN["cyan"],
                  "linientyp": "Volllinie (schmal)", "eig_farbe": True, "staerke": 0.35}
        self.layout_elemente.append(Rechteck(0, 0, b, h, **basis))
        self.layout_elemente.append(Rechteck(10, 5, b - 5, h - 5, **basis2))
        sw, sh = 180, 60
        fx, fy = b - 5 - sw, 5
        self.layout_elemente.append(Rechteck(fx, fy, fx + sw, fy + sh, **basis))
        self.layout_elemente.append(Linie(fx, fy + sh - 20, fx + sw, fy + sh - 20, **basis2))
        self.layout_elemente.append(Linie(fx + 90, fy, fx + 90, fy + sh - 20, **basis2))
        de = SPRACHE["aktuell"] == "de"
        self.layout_elemente.append(Text(fx + 3, fy + sh - 6,
            (f"Zeichnung: {self.layout_format}" if de
             else f"Drawing: {self.layout_format}"), 5.0, 0.0, "Arial", **basis2))
        self.layout_elemente.append(Text(fx + 3, fy + sh - 16,
            (f"Maßstab: {self.massstab.get()}" if de
             else f"Scale: {self.massstab.get()}"), 3.5, 0.0, "Arial", **basis2))
        self.layout_elemente.append(Text(fx + 3, fy + 6,
            ("Einheit: mm" if de else "Unit: mm"), 3.5, 0.0, "Arial", **basis2))
        self.layout_elemente.append(Text(fx + 93, fy + sh - 6,
            ("Werkstoff:" if de else "Material:"), 3.5, 0.0, "Arial", **basis2))
        self.layout_elemente.append(Text(fx + 93, fy + sh - 16,
            ("Datum / Name:" if de else "Date / Name:"), 3.5, 0.0, "Arial", **basis2))
        self.layout_elemente.append(Text(fx + 93, fy + 6,
            "DIN EN ISO 5457 / DIN 6771", 2.5, 0.0, "Arial", **basis2))
        self.redraw()

    def viewport_modus_starten(self):
        if not self._ist_layout():
            self.status.set("Bitte zuerst ein Layout öffnen.")
            return
        self._viewport_modus = True
        self.letzter_punkt = None
        de = SPRACHE["aktuell"] == "de"
        self.status.set(("Viewport-Modus: Rechteck im Layout aufziehen." if de
                         else "Viewport mode: drag a rectangle in the layout."))

    def blatt_leeren(self):
        de = SPRACHE["aktuell"] == "de"
        if messagebox.askyesno(
                ("Blatt leeren" if de else "Clear sheet"),
                ("Alle Layout-Elemente entfernen?" if de
                 else "Remove all layout elements?")):
            self._snapshot()
            self.layouts[self.aktives_layout].elemente = []
            self._aktiver_viewport = None
            self.redraw()
            self._viewport_modus_anzeige_aktualisieren()

    # --------------------------------------------------------
    # Info-Fenster
    # --------------------------------------------------------
    def zeige_info_fenster(self):
        info_win = tk.Toplevel(self.root)
        info_win.title(tr("info.titel"))
        info_win.geometry("450x420")
        info_win.transient(self.root)
        info_win.configure(bg=FARBEN["bg_mittel"])
        info_win.resizable(False, False)

        frame = tk.Frame(info_win, bg=FARBEN["bg_mittel"], padx=26, pady=22)
        frame.pack(fill=tk.BOTH, expand=True)

        title_row = tk.Frame(frame, bg=FARBEN["bg_mittel"])
        title_row.pack(anchor="w", fill="x")

        logo_path = None
        kandidaten = [
            "KatieCAD.png",
            os.path.join(os.getcwd(), "KatieCAD.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "KatieCAD.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "KatieCAD.png"),
        ]
        for k in kandidaten:
            k_abs = os.path.abspath(k)
            if os.path.isfile(k_abs):
                logo_path = k_abs
                break

        if logo_path is None:
            print("[KatieCAD] Logo nicht gefunden. Gesucht in:")
            for k in kandidaten:
                print(f"    {os.path.abspath(k)}")
        elif not PILLOW_VERFUEGBAR:
            print("[KatieCAD] Pillow nicht installiert – Logo wird nicht angezeigt.")
        else:
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
                logo_img = logo_img.resize((64, 64), Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_img)
                logo_lbl = tk.Label(title_row, image=logo_photo,
                                    bg=FARBEN["bg_mittel"], bd=0,
                                    highlightthickness=0)
                logo_lbl.image = logo_photo
                logo_lbl.pack(side="left", padx=(0, 14))
                print(f"[KatieCAD] Logo geladen: {logo_path}")
            except Exception as e:
                print(f"[KatieCAD] Logo konnte nicht geladen werden: {e}")

        tk.Label(title_row, text="KatieCAD",
                 font=("Helvetica", 15, "bold"),
                 bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"]).pack(side="left", anchor="w")

        tk.Frame(frame, bg=FARBEN["rand"], height=1).pack(fill="x", pady=(8, 14))

        tk.Label(frame, text=tr("info.version"),
                 font=("Helvetica", 9),
                 bg=FARBEN["bg_mittel"], fg=FARBEN["text"]).pack(anchor="w", pady=(0, 6))

        tk.Label(frame, text=tr("info.copyright"),
                 font=("Helvetica", 9, "italic"),
                 bg=FARBEN["bg_mittel"], fg=FARBEN["text_dim"]).pack(anchor="w", pady=(0, 6))

        tk.Label(frame, text="Released under the MIT License.",
                 font=("Helvetica", 9),
                 bg=FARBEN["bg_mittel"], fg=FARBEN["text_dim"]).pack(anchor="w", pady=(0, 16))

        tk.Frame(frame, bg=FARBEN["rand"], height=1).pack(fill="x", pady=(0, 14))

        btn_row = tk.Frame(frame, bg=FARBEN["bg_mittel"])
        btn_row.pack(fill="x", side="bottom")

        def make_btn(text, cmd):
            b = tk.Button(btn_row, text=text, command=cmd,
                          bg=FARBEN["bg_hell"], fg=FARBEN["text"],
                          activebackground=FARBEN["bg_hover"],
                          activeforeground=FARBEN["cyan"],
                          relief="raised", bd=1, font=("Helvetica", 9, "bold"),
                          padx=14, pady=4, cursor="hand2")
            return b

        make_btn("License", lambda: zeige_lizenz_fenster(info_win)).pack(side="left")
        make_btn(tr("dlg.schliessen"), info_win.destroy).pack(side="right")

        info_win.update_idletasks()
        mx = self.root.winfo_rootx() + self.root.winfo_width() // 2
        my = self.root.winfo_rooty() + self.root.winfo_height() // 2
        w = info_win.winfo_width()
        h = info_win.winfo_height()
        info_win.geometry(f"+{mx - w // 2}+{my - h // 2}")

    def neu(self):
        de = SPRACHE["aktuell"] == "de"
        if self._dirty:
            antwort = messagebox.askyesnocancel(
                ("Neu" if de else "New"),
                ("Die Zeichnung wurde geändert.\n\nMöchten Sie vor dem Löschen "
                 "speichern?" if de else
                 "The drawing has been modified.\n\nSave before deleting?"))
            if antwort is None:
                return
            if antwort:
                if not self.speichern():
                    return
        elif not messagebox.askyesno(
                ("Neu" if de else "New"),
                ("Alle Elemente löschen?" if de else "Delete all elements?")):
            return
        self.elemente = []
        self.layouts = [Layout("Layout1", Layout.STANDARD_FORMAT, "#1c132d")]
        self.aktives_layout = 0
        self.ansicht.set("modell")
        self.auswahl = []
        self._aktiver_viewport = None
        self._paste_abbrechen()
        self._bem_abbrechen()
        self._bogen_abbrechen()
        self._undo_stack = []
        self._layout_switcher_neu_aufbauen()
        self._update_kontext_widgets()
        bg = self.bg_modell
        self.canvas.config(bg=bg)
        self.bg_btn.config(bg=bg)
        self._mark_clean()
        self.redraw()
        self._zeichne_raster()
        self._viewport_modus_anzeige_aktualisieren()

    def speichern(self):
        de = SPRACHE["aktuell"] == "de"
        pfad = filedialog.asksaveasfilename(
            defaultextension=".cadjson",
            filetypes=[("CAD-Datei" if de else "CAD file", "*.cadjson"),
                       ("Alle Dateien" if de else "All files", "*.*")])
        if not pfad:
            return False
        daten = {
            "einheit": self.einheit.get(),
            "massstab": self.massstab.get(),
            "bg_modell": self.bg_modell,
            "layout_format": self.layout_format,
            "bg_layout": self.layouts[0].bg,
            "raster_mm": self._zahl(self.raster_mm, 5.0),
            "fang_mm": self._zahl(self.fang_mm, 5.0),
            "layers": [l.to_dict() for l in self.layers.values()],
            "elemente": [e.to_dict() for e in self.elemente],
            "layouts": [l.to_dict() for l in self.layouts],
            "aktives_layout": self.aktives_layout,
            "ansicht": self.ansicht.get(),
            "sprache": SPRACHE["aktuell"],
        }
        try:
            with open(pfad, "w", encoding="utf-8") as f:
                json.dump(daten, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror(tr("msg.speichern_fehlgeschlagen"), str(e))
            return False
        self._mark_clean()
        self.status.set((f"Gespeichert: {pfad}" if de else f"Saved: {pfad}"))
        return True

    def oeffnen(self):
        de = SPRACHE["aktuell"] == "de"
        if self._dirty:
            antwort = messagebox.askyesnocancel(
                ("Öffnen" if de else "Open"),
                ("Die aktuelle Zeichnung wurde geändert.\n\nMöchten Sie vor dem "
                 "Öffnen speichern?" if de else
                 "The current drawing has been modified.\n\nSave before opening?"))
            if antwort is None:
                return
            if antwort:
                if not self.speichern():
                    return
        pfad = filedialog.askopenfilename(
            filetypes=[("CAD-Datei" if de else "CAD file", "*.cadjson"),
                       ("Alle Dateien" if de else "All files", "*.*")])
        if not pfad:
            return
        try:
            with open(pfad, "r", encoding="utf-8") as f:
                daten = json.load(f)
        except Exception as e:
            messagebox.showerror(tr("msg.oeffnen_fehlgeschlagen"), str(e))
            return
        self.einheit.set(daten.get("einheit", "mm"))
        self.massstab.set(daten.get("massstab", "1:1"))
        self.bg_modell = daten.get("bg_modell", "#120a1f")
        self.raster_mm.set(daten.get("raster_mm", 5.0))
        self.fang_mm.set(daten.get("fang_mm", 5.0))
        for ld in daten.get("layers", []):
            self.layers[ld["name"]] = Layer(ld["name"], ld.get("farbe", "#c29bff"),
                                            ld.get("staerke", 0.35),
                                            ld.get("sichtbar", True))
        self.layer_cb.config(values=list(self.layers.keys()))
        self.elemente = []
        for d in daten.get("elemente", []):
            el = self._dict_zu_element(d)
            if el:
                self.elemente.append(el)

        if "layouts" in daten and daten["layouts"]:
            self.layouts = []
            for ld in daten["layouts"]:
                self.layouts.append(Layout.from_dict(ld, self._dict_zu_element))
            if not self.layouts:
                self.layouts = [Layout("Layout1", Layout.STANDARD_FORMAT, "#1c132d")]
        else:
            alt = Layout(daten.get("layout_format", Layout.STANDARD_FORMAT),
                         daten.get("layout_format", Layout.STANDARD_FORMAT),
                         daten.get("bg_layout", "#1c132d"))
            alt.name = "Layout1"
            for d in daten.get("layout_elemente", []):
                el = self._dict_zu_element(d)
                if el:
                    if isinstance(el, Viewport):
                        el.aktiv = False
                    alt.elemente.append(el)
            self.layouts = [alt]

        self.aktives_layout = int(daten.get("aktives_layout", 0))
        if self.aktives_layout >= len(self.layouts):
            self.aktives_layout = len(self.layouts) - 1
        gespeicherte_ansicht = daten.get("ansicht", "modell")
        if gespeicherte_ansicht.startswith("layout"):
            idx = 0
            if ":" in gespeicherte_ansicht:
                try:
                    idx = int(gespeicherte_ansicht.split(":", 1)[1])
                except ValueError:
                    idx = 0
            if idx >= len(self.layouts):
                idx = len(self.layouts) - 1
            self.aktives_layout = idx
            self.ansicht.set(f"layout:{idx}")
        else:
            self.ansicht.set("modell")

        self.auswahl = []
        self._aktiver_viewport = None
        self._paste_abbrechen()
        self._bem_abbrechen()
        self._bogen_abbrechen()
        bg = self.bg_modell if not self._ist_layout() else self.bg_layout
        self.canvas.config(bg=bg)
        self.bg_btn.config(bg=bg)
        self._undo_stack = []
        self._layout_switcher_neu_aufbauen()
        self._update_kontext_widgets()
        self._mark_clean()
        self.redraw()
        self._zeichne_raster()
        self._viewport_modus_anzeige_aktualisieren()
        self.status.set((f"Geöffnet: {pfad}" if de else f"Opened: {pfad}"))

    def _dict_zu_element(self, d):
        d = dict(d)
        typ = d.pop("typ")
        if typ == "viewport":
            if "zoom" not in d and "massstab" in d:
                d["zoom"] = d.pop("massstab")
            d.pop("aktiv", None)
        if "staerke" not in d:
            d["staerke"] = None
        try:
            if typ == "linie":      return Linie(**d)
            if typ == "kreis":      return Kreis(**d)
            if typ == "bogen":      return Bogen(**d)
            if typ == "rechteck":   return Rechteck(**d)
            if typ == "polylinie":  return Polylinie(**d)
            if typ == "text":       return Text(**d)
            if typ == "bemassung":  return Bemassung(**d)
            if typ == "viewport":   return Viewport(**d)
        except Exception as e:
            print(f"Fehler beim Laden: {e} - {d}")
        return None

    def export_dxf(self):
        de = SPRACHE["aktuell"] == "de"
        if not EZDXF_VERFUEGBAR:
            messagebox.showwarning("DXF",
                ("ezdxf nicht installiert." if de else "ezdxf is not installed."))
            return
        pfad = filedialog.asksaveasfilename(
            defaultextension=".dxf",
            filetypes=[("DXF-Datei" if de else "DXF file", "*.dxf"),
                       ("Alle Dateien" if de else "All files", "*.*")])
        if not pfad:
            return
        try:
            doc = ezdxf.new(dxfversion="R2010")
            for name, l in self.layers.items():
                if name not in doc.layers:
                    doc.layers.add(name, color=self._hex_zu_aci(l.farbe))
            msp = doc.modelspace()
            for el in self.elemente:
                self._element_zu_dxf(msp, el)
            doc.saveas(pfad)
            self.status.set((f"DXF exportiert: {pfad}" if de
                             else f"DXF exported: {pfad}"))
        except Exception as e:
            messagebox.showerror("DXF",
                (f"Fehler:\n{e}" if de else f"Error:\n{e}"))

    def _hex_zu_aci(self, hexfarbe):
        mapping = {"#000000": 7, "#ffffff": 7, "#ff0000": 1, "#ffff00": 2,
                   "#00ff00": 3, "#00ffff": 4, "#0000ff": 5, "#ff00ff": 6,
                   "#0066cc": 5, "#666666": 8, "#cc0000": 1, "#888888": 8,
                   "#c29bff": 4, "#ff2d95": 6, "#39ff14": 3}
        return mapping.get(hexfarbe.lower(), 7)

    def _element_zu_dxf(self, msp, el):
        attribs = {"layer": el.layer}
        try:
            if isinstance(el, Linie):
                msp.add_line((el.x1, el.y1), (el.x2, el.y2), dxfattribs=attribs)
            elif isinstance(el, Kreis):
                msp.add_circle((el.cx, el.cy), el.r, dxfattribs=attribs)
            elif isinstance(el, Bogen):
                msp.add_arc((el.cx, el.cy), el.r, el.start, el.ende, dxfattribs=attribs)
            elif isinstance(el, Rechteck):
                pts = [(el.x1, el.y1), (el.x2, el.y1), (el.x2, el.y2), (el.x1, el.y2)]
                msp.add_lwpolyline(pts, close=True, dxfattribs=attribs)
            elif isinstance(el, Polylinie):
                msp.add_lwpolyline(el.punkte, close=el.geschlossen, dxfattribs=attribs)
            elif isinstance(el, Text):
                self._dxf_text(msp, el.inhalt, el.x, el.y, el.hoehe, el.winkel,
                               el.layer, einfuegepunkt=el.einfuegepunkt)
            elif isinstance(el, Bemassung):
                g = el.geometrie(self._einh_faktor(), self.dezimalkomma.get())
                for (x1, y1, x2, y2) in g["linien"]:
                    msp.add_line((x1, y1), (x2, y2), dxfattribs=attribs)
                for (x, y, ang, L) in g["pfeile"]:
                    ux, uy = math.cos(ang), math.sin(ang)
                    bx, by = x - ux * L, y - uy * L
                    hw = L / 6.0
                    a = (bx - uy * hw, by + ux * hw)
                    b = (bx + uy * hw, by - ux * hw)
                    msp.add_solid([(x, y), a, b, b], dxfattribs=attribs)
                if g["text"]:
                    s, cx, cy, ang, w, h = g["text"]
                    self._dxf_text(msp, s, cx, cy, h, ang, el.layer, mitte=True)
        except Exception as e:
            print(f"Element konnte nicht exportiert werden: {e}")

    def _dxf_text(self, msp, inhalt, x, y, hoehe, winkel, layer,
                  mitte=False, einfuegepunkt=None):
        try:
            from ezdxf.enums import TextEntityAlignment as A
        except Exception:
            A = None

        if A is not None:
            zuordnung = {
                "oben_links":      A.TOP_LEFT,
                "oben_zentriert":  A.TOP_CENTER,
                "oben_rechts":     A.TOP_RIGHT,
                "mitte_links":     A.MIDDLE_LEFT,
                "mitte_zentriert": A.MIDDLE_CENTER,
                "mitte_rechts":    A.MIDDLE_RIGHT,
                "unten_links":     A.BOTTOM_LEFT,
                "unten_zentriert": A.BOTTOM_CENTER,
                "unten_rechts":    A.BOTTOM_RIGHT,
            }
        else:
            zuordnung = {}

        if einfuegepunkt is None:
            einfuegepunkt = "mitte_zentriert" if mitte else "unten_links"
        align = zuordnung.get(einfuegepunkt)

        if "\n" in inhalt:
            attach = {
                "oben_links": 1, "oben_zentriert": 2, "oben_rechts": 3,
                "mitte_links": 4, "mitte_zentriert": 5, "mitte_rechts": 6,
                "unten_links": 7, "unten_zentriert": 8, "unten_rechts": 9,
            }.get(einfuegepunkt, 7)
            m = msp.add_mtext(
                inhalt.replace("\n", "\\P"),
                dxfattribs={"layer": layer, "char_height": hoehe,
                            "rotation": winkel, "attachment_point": attach})
            m.set_location((x, y))
            return

        t = msp.add_text(inhalt,
                         dxfattribs={"layer": layer, "height": hoehe,
                                     "rotation": winkel})
        if align is not None:
            try:
                t.set_placement((x, y), align=align)
                return
            except Exception:
                pass
        t.set_placement((x, y))

    def import_dxf(self):
        de = SPRACHE["aktuell"] == "de"
        if not EZDXF_VERFUEGBAR:
            messagebox.showwarning("DXF",
                ("ezdxf nicht installiert." if de else "ezdxf is not installed."))
            return
        pfad = filedialog.askopenfilename(
            filetypes=[("DXF-Datei" if de else "DXF file", "*.dxf"),
                       ("Alle Dateien" if de else "All files", "*.*")])
        if not pfad:
            return
        try:
            self._snapshot()
            doc = ezdxf.readfile(pfad)
            msp = doc.modelspace()
            importiert = 0
            for e in msp:
                if self._dxf_zu_element(e):
                    importiert += 1
            self.redraw()
            self.status.set(
                (f"DXF importiert ({importiert} Elemente): {pfad}" if de
                 else f"DXF imported ({importiert} elements): {pfad}"))
        except Exception as e:
            messagebox.showerror("DXF",
                (f"Fehler:\n{e}" if de else f"Error:\n{e}"))

    def _dxf_zu_element(self, e):
        typ = e.dxftype()
        layer = e.dxf.get("layer", "0")
        if layer not in self.layers:
            self.layers[layer] = Layer(layer, FARBEN["cyan"], 0.35)
            self.layer_cb.config(values=list(self.layers.keys()))
        try:
            if typ == "LINE":
                s = e.dxf.start; en = e.dxf.end
                self.elemente.append(Linie(s.x, s.y, en.x, en.y, layer=layer,
                                           farbe=FARBEN["cyan"],
                                           linientyp="Volllinie (schmal)"))
                return True
            if typ == "CIRCLE":
                c = e.dxf.center; r = e.dxf.radius
                self.elemente.append(Kreis(c.x, c.y, r, layer=layer,
                                           farbe=FARBEN["cyan"],
                                           linientyp="Volllinie (schmal)"))
                return True
            if typ == "ARC":
                c = e.dxf.center; r = e.dxf.radius
                s = e.dxf.start_angle; en = e.dxf.end_angle
                self.elemente.append(Bogen(c.x, c.y, r, s, en, layer=layer,
                                           farbe=FARBEN["cyan"],
                                           linientyp="Volllinie (schmal)"))
                return True
            if typ == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in e.get_points()]
                self.elemente.append(Polylinie(pts, geschlossen=bool(e.closed),
                                               layer=layer, farbe=FARBEN["cyan"],
                                               linientyp="Volllinie (schmal)"))
                return True
            if typ in ("TEXT", "MTEXT"):
                inhalt = e.dxf.text if typ == "TEXT" else e.text
                pos = e.dxf.insert
                hoehe = e.dxf.get("height", 3.5)
                self.elemente.append(Text(pos.x, pos.y, inhalt, hoehe, 0.0,
                                           "Arial", layer=layer,
                                           farbe=FARBEN["cyan"],
                                           linientyp="Volllinie (schmal)"))
                return True
        except Exception as ex:
            print(f"DXF-Element nicht importiert: {ex}")
        return False

    def import_dwg(self):
        de = SPRACHE["aktuell"] == "de"
        if not EZDWG_VERFUEGBAR:
            messagebox.showwarning("DWG",
                ("ezdwg nicht installiert." if de else "ezdwg is not installed."))
            return
        pfad = filedialog.askopenfilename(
            filetypes=[("DWG-Datei" if de else "DWG file", "*.dwg"),
                       ("Alle Dateien" if de else "All files", "*.*")])
        if not pfad:
            return
        try:
            self._snapshot()
            doc = ezdwg.read(pfad)
            msp = doc.modelspace()
            importiert = 0
            for e in msp.query("LINE LWPOLYLINE CIRCLE ARC TEXT MTEXT"):
                if self._dwg_zu_element(e):
                    importiert += 1
            self.redraw()
            self.status.set(
                (f"DWG importiert ({importiert} Elemente): {pfad}" if de
                 else f"DWG imported ({importiert} elements): {pfad}"))
        except Exception as e:
            messagebox.showerror("DWG",
                (f"Fehler:\n{e}" if de else f"Error:\n{e}"))

    def _dwg_zu_element(self, e):
        try:
            typ = e.dxftype()
            layer = e.dxf.get("layer", "0")
            if layer not in self.layers:
                self.layers[layer] = Layer(layer, FARBEN["cyan"], 0.35)
                self.layer_cb.config(values=list(self.layers.keys()))
            if typ == "LINE":
                s = e.dxf.start; en = e.dxf.end
                self.elemente.append(Linie(s.x, s.y, en.x, en.y, layer=layer,
                                           farbe=FARBEN["cyan"],
                                           linientyp="Volllinie (schmal)"))
                return True
            if typ == "CIRCLE":
                c = e.dxf.center; r = e.dxf.radius
                self.elemente.append(Kreis(c.x, c.y, r, layer=layer,
                                           farbe=FARBEN["cyan"],
                                           linientyp="Volllinie (schmal)"))
                return True
            if typ == "ARC":
                c = e.dxf.center; r = e.dxf.radius
                s = e.dxf.start_angle; en = e.dxf.end_angle
                self.elemente.append(Bogen(c.x, c.y, r, s, en, layer=layer,
                                           farbe=FARBEN["cyan"],
                                           linientyp="Volllinie (schmal)"))
                return True
            if typ == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in e.get_points()]
                self.elemente.append(Polylinie(pts, geschlossen=bool(e.closed),
                                               layer=layer, farbe=FARBEN["cyan"],
                                               linientyp="Volllinie (schmal)"))
                return True
        except Exception as ex:
            print(f"DWG-Element nicht importiert: {ex}")
        return False

    def _update_eingabe_hinweis(self):
        h = self.lbl_hinweis.config
        if self._cmd_pending is not None:
            return
        if self._op is not None:
            self._op_hinweis()
            return
        de = SPRACHE["aktuell"] == "de"
        w = self.aktives_werkzeug.get()
        n = len(self._pts)
        if w == "auswahl":
            if self._ist_layout():
                h(text=("Viewport: Klick markiert | Ecke ziehen = skalieren | "
                        "Mitte ziehen = verschieben | Rechtsklick = Menü" if de else
                        "Viewport: click = select | drag corner = resize | "
                        "drag middle = move | right-click = menu"))
            else:
                h(text=("Element anklicken | Griffe ziehen = ändern | Links-/"
                        "Rechtsziehen = Fenster-/Kreuzauswahl" if de else
                        "Click element | drag grips = edit | drag left/right = "
                        "window/crossing selection"))
        elif w == "linie":
            h(text=(("Ersten Punkt 'x,y' ODER klicken" if self.letzter_punkt is None
                     else "Länge / 'L<Winkel' / '@dx,dy' / 'x,y'") if de else
                    ("First point 'x,y' OR click" if self.letzter_punkt is None
                     else "Length / 'L<angle' / '@dx,dy' / 'x,y'")))
        elif w == "kreis":
            h(text=(("Mittelpunkt 'x,y' ODER klicken" if self.letzter_punkt is None
                     else ("Radius eingeben" if self.kreis_modus.get() == "radius"
                           else "Durchmesser eingeben")) if de else
                    ("Center 'x,y' OR click" if self.letzter_punkt is None
                     else ("Enter radius" if self.kreis_modus.get() == "radius"
                           else "Enter diameter"))))
        elif w == "rechteck":
            h(text=(("Ersten Eckpunkt 'x,y' ODER klicken" if self.letzter_punkt is None
                     else "'Breite,Höhe' ODER klicken") if de else
                    ("First corner 'x,y' OR click" if self.letzter_punkt is None
                     else "'Width,Height' OR click")))
        elif w == "bogen":
            if self.bogen_modus.get() == "mitte":
                txt = (["Mittelpunkt setzen", "Startpunkt setzen",
                        "Endpunkt setzen (Richtung folgt der Maus)"] if de else
                       ["Set center", "Set start point",
                        "Set end point (direction follows mouse)"])
            else:
                txt = (["Startpunkt setzen", "Punkt auf dem Bogen setzen",
                        "Endpunkt setzen"] if de else
                       ["Set start point", "Set point on arc", "Set end point"])
            h(text=txt[min(n, 2)])
        elif w == "bemassung":
            if self.bem_art.get() in ("radius", "durchmesser"):
                h(text=(("Kreis/Bogen anklicken" if n == 0
                         else "Position der Maßangabe setzen") if de else
                        ("Click circle/arc" if n == 0
                         else "Set dimension text position")))
            else:
                h(text=(["1. Messpunkt setzen", "2. Messpunkt setzen",
                         "Maßlinie positionieren, Klick = fertig"] if de else
                        ["Set 1st measurement point", "Set 2nd measurement point",
                         "Position dimension line, click = done"])[min(n, 2)])
        elif w == "text":
            h(text=("Einfügepunkt klicken, dann Text eingeben" if de
                    else "Click insertion point, then enter text"))
        else:
            h(text="")

    def _eingabe_zuruecksetzen(self):
        self.eingabe_var.set("")

    def _eingabe_enter(self, event=None):
        text = self.eingabe_var.get().strip()
        if self._cmd_pending is not None:
            cb = self._cmd_pending
            self._cmd_pending = None
            self.eingabe_var.set("")
            try:
                cb(text)
            except Exception as ex:
                messagebox.showerror(tr("eingabe.label"), str(ex))
            self._update_eingabe_hinweis()
            return
        if not text:
            self._eingabe_leer()
            return
        w = self.aktives_werkzeug.get()
        einh = self._einh_faktor()
        try:
            wort = text.upper()
            if w == "polylinie" and self.aktuelle_polylinie and wort in (
                    "S", "SCHLIESSEN", "C", "CLOSE"):
                self._polylinie_abschliessen(geschlossen=True)
                self.letzter_punkt = None
                self.eingabe_var.set("")
                self._update_eingabe_hinweis()
                return
            tok = text.split(None, 1)
            cmd = BEFEHLE.get(tok[0].upper())
            if cmd:
                self.eingabe_var.set("")
                self._befehl(cmd, tok[1] if len(tok) > 1 else "")
                return
            if self._op is not None and self._op["stufe"] in ("basis", "ziel"):
                self._eingabe_op(text, einh)
            elif w == "linie":
                self._eingabe_linie(text, einh)
            elif w == "kreis":
                self._eingabe_kreis(text, einh)
            elif w == "rechteck":
                self._eingabe_rechteck(text, einh)
            elif w == "polylinie":
                self._eingabe_polylinie(text, einh)
            elif w in ("bogen", "bemassung"):
                self._eingabe_punkt_werkzeug(text, einh)
            self.eingabe_var.set("")
            self._update_eingabe_hinweis()
        except Exception as ex:
            messagebox.showerror(tr("eingabe.label"), str(ex))
            self.eingabe_var.set("")

    def _parse_xy(self, text, einh):
        teile = text.replace(";", ",").split(",")
        if len(teile) != 2:
            raise ValueError(("Bitte 'x,y' eingeben" if SPRACHE["aktuell"] == "de"
                              else "Please enter 'x,y'"))
        return float(teile[0].strip()) * einh, float(teile[1].strip()) * einh

    def _parse_einzelwert(self, text, einh):
        text = text.strip().replace(",", ".")
        m = re.match(r"^([0-9.+\-eE]+)\s*([a-zA-Z]*)$", text)
        if not m:
            raise ValueError((f"Ungültiger Wert: {text!r}"
                              if SPRACHE["aktuell"] == "de"
                              else f"Invalid value: {text!r}"))
        wert = float(m.group(1))
        suffix = m.group(2).lower()
        if suffix in EINHEITEN:
            return wert * EINHEITEN[suffix]
        return wert * einh

    def _eingabe_linie(self, text, einh):
        if self.letzter_punkt is None:
            x, y = self._parse_xy(text, einh)
            self.letzter_punkt = (x, y)
            self.redraw()
            return
        lx, ly = self.letzter_punkt
        x2, y2 = self._parse_punkt_eingabe(text, lx, ly, einh)
        self._snapshot()
        self._ziel_liste().append(self._neue_linie(lx, ly, x2, y2))
        self.letzter_punkt = None
        self._clear_temp()
        self.redraw()

    def _eingabe_kreis(self, text, einh):
        if self.letzter_punkt is None:
            x, y = self._parse_xy(text, einh)
            self.letzter_punkt = (x, y)
            self.redraw()
            return
        val = self._parse_einzelwert(text, einh)
        r = val if self.kreis_modus.get() == "radius" else val / 2.0
        cx, cy = self.letzter_punkt
        self._snapshot()
        self._ziel_liste().append(self._neuer_kreis(cx, cy, r))
        self.letzter_punkt = None
        self._clear_temp()
        self.redraw()

    def _eingabe_rechteck(self, text, einh):
        if self.letzter_punkt is None:
            x, y = self._parse_xy(text, einh)
            self.letzter_punkt = (x, y)
            self.redraw()
            return
        teile = [t for t in re.split(r"[,;\t]+|\s{2,}", text.strip()) if t.strip()]
        if len(teile) != 2:
            raise ValueError(("Bitte 'Breite,Höhe' eingeben"
                              if SPRACHE["aktuell"] == "de"
                              else "Please enter 'Width,Height'"))
        bw = self._parse_einzelwert(teile[0], einh)
        bh = self._parse_einzelwert(teile[1], einh)
        x1, y1 = self.letzter_punkt
        self._snapshot()
        self._ziel_liste().append(self._neues_rechteck(x1, y1, x1 + bw, y1 + bh))
        self.letzter_punkt = None
        self._clear_temp()
        self.redraw()

    def _parse_punkt_eingabe(self, text, lx, ly, einh):
        text = text.strip()
        if text.startswith("@"):
            teile = text[1:].replace(";", ",").split(",")
            if len(teile) == 2:
                dx = self._parse_einzelwert(teile[0], einh)
                dy = self._parse_einzelwert(teile[1], einh)
                return lx + dx, ly + dy
        if "<" in text:
            teile = text.split("<")
            L = self._parse_einzelwert(teile[0], einh)
            winkel = float(teile[1].replace(",", ".").strip())
            rad = math.radians(winkel)
            return lx + L * math.cos(rad), ly + L * math.sin(rad)
        try:
            L = self._parse_einzelwert(text, einh)
            mx, my = self._maus_px
            x_maus, y_maus = self.px_to_mm(mx, my)
            dx = x_maus - lx
            dy = y_maus - ly
            if self.ortho.get():
                if abs(dx) >= abs(dy):
                    return (lx + L, ly) if dx >= 0 else (lx - L, ly)
                return (lx, ly + L) if dy >= 0 else (lx, ly - L)
            dist = math.hypot(dx, dy)
            if dist < 1e-9:
                return lx + L, ly
            return lx + L * dx / dist, ly + L * dy / dist
        except ValueError:
            pass
        teile = text.replace(";", ",").split(",")
        if len(teile) == 2:
            return (self._parse_einzelwert(teile[0], einh),
                    self._parse_einzelwert(teile[1], einh))
        raise ValueError(("Format nicht erkannt" if SPRACHE["aktuell"] == "de"
                          else "Format not recognized"))

    def _eingabe_abbrechen(self):
        self.eingabe_var.set("")
        self.letzter_punkt = None
        self._clear_temp()
        self._update_eingabe_hinweis()

    def _layer_daten(self):
        l = self.layers.get(self.aktiver_layer.get())
        farbe = self.zeichenfarbe if self.eigene_farbe.get() else (
            l.farbe if l else FARBEN["cyan"])
        lt = self.linientyp.get()
        st = self._zahl(self.linienstaerke, 0.35)
        if "breit" in lt:
            st = max(st, 0.7)
        return {"layer": self.aktiver_layer.get(), "farbe": farbe,
                "linientyp": lt, "eig_farbe": bool(self.eigene_farbe.get()),
                "staerke": st}

    def _neue_linie(self, x1, y1, x2, y2):
        return Linie(x1, y1, x2, y2, **self._layer_daten())

    def _neuer_kreis(self, cx, cy, r):
        return Kreis(cx, cy, r, **self._layer_daten())

    def _neues_rechteck(self, x1, y1, x2, y2):
        return Rechteck(x1, y1, x2, y2, **self._layer_daten())

    def _neuer_bogen(self, cx, cy, r, s, e):
        return Bogen(cx, cy, r, s, e, **self._layer_daten())

    def _ctx(self):
        if self._ist_layout():
            if self._aktiver_viewport is not None:
                return "vp", self._aktiver_viewport
            return "layout", None
        return "modell", None

    def _ctx_liste(self):
        return self.layout_elemente if self._ctx()[0] == "layout" else self.elemente

    def _ziel_liste(self):
        return self._ctx_liste()

    def _papier_zu_modell(self, vp, x, y):
        return (vp.modell_zentrum_x + (x - (vp.x + vp.breite / 2)) / vp.zoom,
                vp.modell_zentrum_y + (y - (vp.y + vp.hoehe / 2)) / vp.zoom)

    def _modell_zu_papier(self, vp, x, y):
        return (vp.x + vp.breite / 2 + (x - vp.modell_zentrum_x) * vp.zoom,
                vp.y + vp.hoehe / 2 + (y - vp.modell_zentrum_y) * vp.zoom)

    def _ctx_zu_px(self, x, y):
        kind, vp = self._ctx()
        if kind == "vp":
            x, y = self._modell_zu_papier(vp, x, y)
        return self.mm_to_px(x, y)

    def _px_zu_ctx(self, px, py):
        x, y = self.px_to_mm(px, py)
        kind, vp = self._ctx()
        if kind == "vp":
            return self._papier_zu_modell(vp, x, y)
        return x, y

    def _ctx_skala(self):
        kind, vp = self._ctx()
        return self.view["zoom"] * (vp.zoom if kind == "vp" else 1.0)

    def _einh_faktor(self):
        return EINHEITEN.get(self.einheit.get(), 1.0)

    def _zahl(self, var, default, ganz=False):
        try:
            v = var.get()
            return int(v) if ganz else float(v)
        except Exception:
            return default

    def _sicht_rect(self):
        cw = self.canvas.winfo_width() or 1200
        ch = self.canvas.winfo_height() or 700
        m = 1500
        return (-m, -m, cw + m, ch + m)

    def _eingabepunkt_px(self, px, py, ref=None, marker=True):
        x, y = self._px_zu_ctx(px, py)
        snap = self._snap_ctx(x, y, ref)
        if snap:
            if marker:
                self._zeichne_snap_marker(snap[0], snap[1], snap[2])
            return (snap[0], snap[1])
        if marker:
            self._snap_marker_loeschen()
        r = self._zahl(self.fang_mm, 5.0) or 1.0
        if self.ortho.get() and ref is not None:
            if abs(x - ref[0]) >= abs(y - ref[1]):
                y = ref[1]
                if self.grid_snap.get():
                    x = round(x / r) * r
            else:
                x = ref[0]
                if self.grid_snap.get():
                    y = round(y / r) * r
        elif self.grid_snap.get():
            x = round(x / r) * r
            y = round(y / r) * r
        return (x, y)

    def _eingabepunkt(self, event, ref=None, marker=True):
        return self._eingabepunkt_px(event.x, event.y, ref, marker)

    def _lw_px(self, staerke_mm, papier_skala=None):
        if not self.lw_anzeigen.get():
            return 1
        w = 1 + int(staerke_mm * LW_PX_FAKTOR)
        if papier_skala:
            w = max(w, int(staerke_mm * papier_skala + 0.5))
        return max(1, w)

    def _prims(self, el, skala):
        if isinstance(el, Linie):
            return [("l", [(el.x1, el.y1), (el.x2, el.y2)], False)]
        if isinstance(el, Rechteck):
            return [("l", [(el.x1, el.y1), (el.x2, el.y1),
                           (el.x2, el.y2), (el.x1, el.y2)], True)]
        if isinstance(el, Polylinie):
            return [("l", list(el.punkte), el.geschlossen)] if len(el.punkte) >= 2 else []
        if isinstance(el, Kreis):
            n = int(max(24, min(720, el.r * skala * 1.2)))
            pts = [(el.cx + el.r * math.cos(2 * math.pi * i / n),
                    el.cy + el.r * math.sin(2 * math.pi * i / n)) for i in range(n)]
            return [("l", pts, True)]
        if isinstance(el, Bogen):
            sw = bogen_sweep(el.start, el.ende)
            n = int(max(6, min(720, el.r * skala * 1.2 * sw / 360.0)))
            return [("l", bogen_punkte(el.cx, el.cy, el.r, el.start, el.ende, n), False)]
        if isinstance(el, Text):
            return [("t", el.x, el.y, el.inhalt, el.hoehe, el.winkel,
                     el.schriftart, el.einfuegepunkt)]
        if isinstance(el, Bemassung):
            g = el.geometrie(self._einh_faktor(), self.dezimalkomma.get())
            out = [("l", [(l[0], l[1]), (l[2], l[3])], False) for l in g["linien"]]
            out += [("p", p[0], p[1], p[2], p[3]) for p in g["pfeile"]]
            if g["text"]:
                s, cx, cy, ang, w, h = g["text"]
                out.append(("tc", cx, cy, s, h, ang, "Arial"))
            return out
        return []

    def _el_polylinien(self, el, skala):
        if isinstance(el, Text):
            return [(el.rahmen(), True)]
        out = [(p[1], p[2]) for p in self._prims(el, skala) if p[0] == "l"]
        if isinstance(el, Bemassung):
            g = el.geometrie(self._einh_faktor(), self.dezimalkomma.get())
            if g["text"]:
                _, cx, cy, ang, w, h = g["text"]
                out.append((gedrehtes_rechteck(cx, cy, w, h, ang), True))
        return out

    def _font(self, fam, px):
        key = (fam, px)
        f = self._font_cache.get(key)
        if f is None:
            f = tkfont.Font(family=fam, size=-int(px))
            self._font_cache[key] = f
        return f

    def _zeichne_prims(self, prims, farbe, w, dash, tf, skala, tags, clip):
        c = self.canvas
        xmin, ymin, xmax, ymax = clip
        for p in prims:
            k = p[0]
            if k == "l":
                pts = [tf(x, y) for (x, y) in p[1]]
                if p[2] and len(pts) > 2:
                    pts.append(pts[0])
                for teil in clip_polyline(pts, clip):
                    flat = [v for q in teil for v in q]
                    kw = {"fill": farbe, "width": w, "tags": tags,
                          "capstyle": tk.ROUND, "joinstyle": tk.ROUND}
                    if dash:
                        kw["dash"] = dash
                    c.create_line(*flat, **kw)
            elif k == "p":
                _, x, y, ang, L = p
                ux, uy = math.cos(ang), math.sin(ang)
                bx, by = x - ux * L, y - uy * L
                hw = L / 6.0
                pp = [tf(x, y), tf(bx - uy * hw, by + ux * hw),
                      tf(bx + uy * hw, by - ux * hw)]
                tip = pp[0]
                if not (xmin <= tip[0] <= xmax and ymin <= tip[1] <= ymax):
                    continue
                flat = [v for q in pp for v in q]
                c.create_polygon(*flat, fill=farbe, outline=farbe, tags=tags)
            else:
                self._zeichne_text_prim(p, farbe, tf, skala, tags, clip)

    def _zeichne_text_prim(self, p, farbe, tf, skala, tags, clip):
        if len(p) == 8:
            art, x, y, inhalt, hoehe, winkel, fam, einfuegepunkt = p
        else:
            art, x, y, inhalt, hoehe, winkel, fam = p
            einfuegepunkt = "unten_links"
        c = self.canvas
        xmin, ymin, xmax, ymax = clip

        tmp = Text(x, y, inhalt, hoehe, winkel, fam, einfuegepunkt=einfuegepunkt)
        w_mm, h_mm = tmp.masse()
        dx_lokal, dy_lokal = tmp._versatz_lokal(w_mm, h_mm)

        h_px = hoehe * skala
        zeilen = inhalt.split("\n") or [""]
        n = len(zeilen)

        ex = (math.cos(math.radians(winkel)), -math.sin(math.radians(winkel)))
        ey = (-math.sin(math.radians(winkel)), -math.cos(math.radians(winkel)))
        bx, by = tf(x, y)
        ux_px = bx + dx_lokal * skala * ex[0] + dy_lokal * skala * ey[0]
        uy_px = by + dx_lokal * skala * ex[1] + dy_lokal * skala * ey[1]

        if h_px < 3.0:
            w_px = w_mm * skala
            c.create_line(ux_px, uy_px,
                          ux_px + ex[0] * w_px, uy_px + ex[1] * w_px,
                          fill=farbe, tags=tags)
            return

        em = max(4, int(round(h_px / CAD_VERSALHOEHE)))
        f = self._font(fam, em)
        asc = f.metrics("ascent")
        desc = f.metrics("descent")
        ls = f.metrics("linespace")
        w_px = max(f.measure(z) for z in zeilen)

        top = (n - 1) * ls + asc
        cl = (top - desc) / 2.0
        mx = ux_px + ex[0] * w_px / 2 + ey[0] * cl
        my = uy_px + ex[1] * w_px / 2 + ey[1] * cl

        for (lx, ly) in ((0, -desc), (w_px, -desc), (w_px, top), (0, top)):
            qx = ux_px + ex[0] * lx + ey[0] * ly
            qy = uy_px + ex[1] * lx + ey[1] * ly
            if not (xmin <= qx <= xmax and ymin <= qy <= ymax):
                return

        kw = {"text": inhalt, "anchor": tk.CENTER, "fill": farbe, "font": f,
              "justify": tk.LEFT, "tags": tags}
        try:
            c.create_text(mx, my, angle=winkel, **kw)
        except tk.TclError:
            c.create_text(mx, my, **kw)

    def _bogen_aus_punkten(self, p):
        if self.bogen_modus.get() == "mitte":
            erg = bogen_mitte_start_ende(p[0], p[1], p[2], self.bogen_richtung.get())
            if erg is None:
                return None
            r, s, e = erg
            return (p[0][0], p[0][1], r, s, e)
        return bogen_aus_3_punkten(p[0], p[1], p[2])

    def _bogen_klick(self, pt):
        modus = self.bogen_modus.get()
        self._pts.append(pt)
        self.letzter_punkt = pt
        n = len(self._pts)
        de = SPRACHE["aktuell"] == "de"
        if n < 3:
            if modus == "mitte":
                hinweise = (["Startpunkt (bestimmt Radius) setzen",
                             "Endpunkt setzen - Richtung folgt der Maus"] if de else
                            ["Set start point (determines radius)",
                             "Set end point - direction follows mouse"])
            else:
                hinweise = (["Zweiten Punkt (liegt auf dem Bogen) setzen",
                             "Endpunkt setzen"] if de else
                            ["Set second point (on the arc)", "Set end point"])
            self.status.set(("Bogen: " if de else "Arc: ") + hinweise[n - 1])
            return
        erg = self._bogen_aus_punkten(self._pts)
        self._pts = []
        self.letzter_punkt = None
        self._clear_temp()
        if erg is None:
            self.status.set(("Bogen nicht möglich (Punkte kollinear oder Winkel "
                             "identisch)." if de else
                             "Arc not possible (collinear points or identical "
                             "angle)."))
            return
        cx, cy, r, s, e = erg
        self._snapshot()
        self._ziel_liste().append(self._neuer_bogen(cx, cy, r, s, e))
        self.redraw()
        self.status.set((f"Bogen platziert: R {r / self._einh_faktor():.2f}, "
                         f"{bogen_sweep(s, e):.1f}°" if de else
                         f"Arc placed: R {r / self._einh_faktor():.2f}, "
                         f"{bogen_sweep(s, e):.1f}°"))

    def _kreis_unter_punkt(self, pt):
        tol = 10.0 / self._ctx_skala()
        for el in reversed(self._ctx_liste()):
            l = self.layers.get(el.layer)
            if l and not l.sichtbar:
                continue
            if isinstance(el, (Kreis, Bogen)):
                d = math.hypot(pt[0] - el.cx, pt[1] - el.cy)
                if abs(d - el.r) <= tol:
                    if isinstance(el, Bogen):
                        w = math.degrees(math.atan2(pt[1] - el.cy, pt[0] - el.cx))
                        if not winkel_im_bogen(w, el.start, el.ende, 2.0):
                            continue
                    return (el.cx, el.cy, el.r)
        return None

    def _bem_element(self, pts, m):
        art = self.bem_art.get()
        daten = self._layer_daten()
        if "Bemaßung" in self.layers:
            daten["layer"] = "Bemaßung"
            daten["farbe"] = self.layers["Bemaßung"].farbe
        daten["eig_farbe"] = True
        daten["staerke"] = None
        daten["linientyp"] = "Volllinie (schmal)"
        if art in ("radius", "durchmesser"):
            richt = art
        elif art == "auto":
            richt = Bemassung.linear_richtung(pts[0], pts[1], m)
        else:
            richt = art
        return Bemassung(pts[0][0], pts[0][1], pts[1][0], pts[1][1],
                         mx=m[0], my=m[1], richtung=richt,
                         hoehe=self._zahl(self.bem_hoehe, 2.5),
                         pfeil=self._zahl(self.bem_pfeil, 2.5),
                         dez=self._zahl(self.bem_dez, 2, ganz=True), **daten)

    def _bem_klick(self, pt):
        art = self.bem_art.get()
        n = len(self._pts)
        de = SPRACHE["aktuell"] == "de"
        if art in ("radius", "durchmesser"):
            if n == 0:
                k = self._kreis_unter_punkt(pt)
                if k is None:
                    self.status.set(("Bemaßung: Bitte einen Kreis oder Bogen "
                                     "anklicken." if de else
                                     "Dimension: please click a circle or arc."))
                    return
                cx, cy, r = k
                dx, dy = pt[0] - cx, pt[1] - cy
                d = math.hypot(dx, dy) or 1.0
                P = (cx + dx / d * r, cy + dy / d * r)
                self._pts = [(cx, cy), P]
                self.letzter_punkt = P
                self.status.set(("Bemaßung: Position der Maßangabe setzen." if de
                                 else "Dimension: set text position."))
                return
            self._bem_fertig(pt)
            return
        if n == 0:
            self._pts = [pt]
            self.letzter_punkt = pt
            self.status.set(("Bemaßung: 2. Messpunkt setzen." if de
                             else "Dimension: set 2nd measurement point."))
        elif n == 1:
            if math.hypot(pt[0] - self._pts[0][0], pt[1] - self._pts[0][1]) < 1e-9:
                self.status.set(("Bemaßung: 2. Punkt = 1. Punkt." if de
                                 else "Dimension: 2nd point = 1st point."))
                return
            self._pts.append(pt)
            self.letzter_punkt = pt
            self.status.set(("Bemaßung: Maus bewegen = Maßlinie positionieren, "
                             "Klick = fertig." if de else
                             "Dimension: move mouse to position line, click = done."))
        else:
            self._bem_fertig(pt)

    def _bem_fertig(self, m):
        el = self._bem_element(self._pts[:2], m)
        self._snapshot()
        self._ziel_liste().append(el)
        self._pts = []
        self.letzter_punkt = None
        self._clear_temp()
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        self.status.set((f"Bemaßung ({el.richtung}) platziert: "
                         f"{el.text(self._einh_faktor(), self.dezimalkomma.get())}"
                         if de else
                         f"Dimension ({el.richtung}) placed: "
                         f"{el.text(self._einh_faktor(), self.dezimalkomma.get())}"))

    def _vorschau_neu(self):
        self._clear_temp()
        if self._paste_aktiv:
            self._paste_vorschau_ids = []
            self._paste_vorschau_aktualisieren(self._maus_px[0], self._maus_px[1])
            return
        werkzeug_aktiv = (self.aktives_werkzeug.get() != "auswahl"
                          or self._viewport_modus or self._vp_fenster is not None
                          or self._op is not None)
        if not werkzeug_aktiv:
            return
        if self.letzter_punkt is None and not self._pts and not self.aktuelle_polylinie:
            return
        pt = self._eingabepunkt_px(self._maus_px[0], self._maus_px[1],
                                   self.letzter_punkt, marker=False)
        self._werkzeug_vorschau(pt)

    def _werkzeug_vorschau(self, pt):
        self._clear_temp()
        c = self.canvas
        w = self.aktives_werkzeug.get()
        lp = self.letzter_punkt
        einh = self._einh_faktor()
        unit = self.einheit.get()
        std = {"farbe": FARBEN["cyan"], "w": 2, "dash": (5, 3)}
        tf, sk = self._ctx_zu_px, self._ctx_skala()
        if self._op is not None:
            self._op_vorschau(pt)
            return

        def zeige(el, stil=std):
            self._zeichne_element(el, tags=("vorschau",), tf=tf, skala=sk, stil=stil)

        def label(x, y, s, dy=-12):
            px, py = tf(x, y)
            c.create_text(px, py + dy, text=s, fill=FARBEN["gelb"],
                          font=("Segoe UI", 9, "bold"), tags="vorschau")

        def hilfslinie(a, b):
            zeige(Linie(a[0], a[1], b[0], b[1]),
                  {"farbe": FARBEN["cyan_dunkel"], "w": 1, "dash": (2, 4)})

        if self._viewport_modus or self._vp_fenster is not None:
            if lp is not None:
                zeige(Rechteck(lp[0], lp[1], pt[0], pt[1]),
                      {"farbe": FARBEN["orange"], "w": 2, "dash": (5, 3)})
                label((lp[0] + pt[0]) / 2, (lp[1] + pt[1]) / 2,
                      f"{abs(pt[0] - lp[0]):.1f} x {abs(pt[1] - lp[1]):.1f} mm", 0)
            return
        if w == "linie" and lp is not None:
            zeige(Linie(lp[0], lp[1], pt[0], pt[1]))
            L = math.hypot(pt[0] - lp[0], pt[1] - lp[1])
            ang = math.degrees(math.atan2(pt[1] - lp[1], pt[0] - lp[0]))
            label((lp[0] + pt[0]) / 2, (lp[1] + pt[1]) / 2,
                  f"{L / einh:.2f} {unit}  |  {ang:.1f}°")
        elif w == "kreis" and lp is not None:
            r = math.hypot(pt[0] - lp[0], pt[1] - lp[1])
            if r > 1e-9:
                zeige(Kreis(lp[0], lp[1], r))
                hilfslinie(lp, pt)
                txt = (f"R {r / einh:.2f}" if self.kreis_modus.get() == "radius"
                       else f"D {2 * r / einh:.2f}")
                label(lp[0] + r, lp[1], txt)
        elif w == "rechteck" and lp is not None:
            zeige(Rechteck(lp[0], lp[1], pt[0], pt[1]))
            label((lp[0] + pt[0]) / 2, (lp[1] + pt[1]) / 2,
                  f"{abs(pt[0] - lp[0]) / einh:.1f} x {abs(pt[1] - lp[1]) / einh:.1f}", 0)
        elif w == "polylinie" and self.aktuelle_polylinie:
            pts = list(self.aktuelle_polylinie) + [pt]
            if len(pts) >= 2:
                zeige(Polylinie(pts))
                a = self.aktuelle_polylinie[-1]
                label((a[0] + pt[0]) / 2, (a[1] + pt[1]) / 2,
                      f"{math.hypot(pt[0] - a[0], pt[1] - a[1]) / einh:.2f} {unit}")
        elif w == "bogen" and self._pts:
            p = self._pts
            mitte = self.bogen_modus.get() == "mitte"
            if len(p) == 1:
                hilfslinie(p[0], pt)
                if mitte:
                    r = math.hypot(pt[0] - p[0][0], pt[1] - p[0][1])
                    if r > 1e-9:
                        zeige(Kreis(p[0][0], p[0][1], r),
                              {"farbe": FARBEN["cyan_dunkel"], "w": 1, "dash": (2, 4)})
                        label(p[0][0] + r, p[0][1], f"R {r / einh:.2f}")
            elif len(p) == 2:
                erg = self._bogen_aus_punkten([p[0], p[1], pt])
                if mitte:
                    hilfslinie(p[0], p[1])
                    hilfslinie(p[0], pt)
                if erg:
                    cx, cy, r, s, e = erg
                    zeige(Bogen(cx, cy, r, s, e))
                    a = math.radians(s + bogen_sweep(s, e) / 2)
                    label(cx + r * math.cos(a), cy + r * math.sin(a),
                          f"R {r / einh:.2f}  {bogen_sweep(s, e):.1f}°")
        elif w == "bemassung" and self._pts:
            radial = self.bem_art.get() in ("radius", "durchmesser")
            if len(self._pts) == 1 and not radial:
                hilfslinie(self._pts[0], pt)
                label((self._pts[0][0] + pt[0]) / 2, (self._pts[0][1] + pt[1]) / 2,
                      f"{math.hypot(pt[0] - self._pts[0][0], pt[1] - self._pts[0][1]) / einh:.2f} {unit}")
            elif len(self._pts) >= 2:
                zeige(self._bem_element(self._pts[:2], pt),
                      {"farbe": FARBEN["gelb"], "w": 1, "dash": None})

    def _griff_bewegen_zu(self, event):
        pt = self._eingabepunkt(event)
        self._griff_drag_el.griff_bewegen(self._griff_drag_id, pt[0], pt[1])
        self.redraw()

    def _vp_start_move(self, vp, x_mm, y_mm):
        base = (x_mm, y_mm)
        tol = 12.0 / self.view["zoom"]
        punkte = [(vp.x, vp.y), (vp.x + vp.breite, vp.y),
                  (vp.x, vp.y + vp.hoehe), (vp.x + vp.breite, vp.y + vp.hoehe),
                  (vp.x + vp.breite / 2, vp.y + vp.hoehe / 2)]
        best = min(punkte, key=lambda p: math.hypot(p[0] - x_mm, p[1] - y_mm))
        if math.hypot(best[0] - x_mm, best[1] - y_mm) <= tol:
            base = best
        self._vp_aktion = "move"
        self._vp_el = vp
        self._vp_start_mm = base
        self._vp_start_rect = (vp.x, vp.y, vp.breite, vp.hoehe)
        self._vp_letzter_pt = None
        self._snap_ausschluss = vp

    def _vp_neues_rect(self, pt):
        sx, sy, sbw, sbh = self._vp_start_rect
        if self._vp_aktion == "move":
            bx, by = self._vp_start_mm
            return (sx + pt[0] - bx, sy + pt[1] - by, sbw, sbh)
        l, r, b, t = sx, sx + sbw, sy, sy + sbh
        mx, my = pt
        e = self._vp_ecke
        if e in ("se", "ne"):
            r = max(l + MIN_VP_GROESSE, mx)
        else:
            l = min(r - MIN_VP_GROESSE, mx)
        if e in ("ne", "nw"):
            t = max(b + MIN_VP_GROESSE, my)
        else:
            b = min(t - MIN_VP_GROESSE, my)
        return (l, b, r - l, t - b)

    def _vp_drag_vorschau(self, event):
        if self._vp_el is None or self._vp_start_rect is None:
            return
        if self._vp_aktion == "move":
            rx, ry = self._px_zu_ctx(event.x, event.y)
            bx, by = self._vp_start_mm
            sx, sy, bw, bh = self._vp_start_rect
            x, y = sx + rx - bx, sy + ry - by
            refs = [(x, y), (x + bw, y), (x, y + bh), (x + bw, y + bh),
                    (x + bw / 2, y + bh / 2)]
            best = None
            for (qx, qy) in refs:
                snap = self._snap_ctx(qx, qy)
                if snap:
                    d = math.hypot(snap[0] - qx, snap[1] - qy)
                    if best is None or d < best[0]:
                        best = (d, snap[0] - qx, snap[1] - qy, snap)
            self._snap_marker_loeschen()
            if best:
                rx += best[1]
                ry += best[2]
                self._zeichne_snap_marker(*best[3])
            pt = (rx, ry)
        else:
            pt = self._eingabepunkt(event)
        self._vp_letzter_pt = pt
        self._vp_vorschau_zeichnen(*self._vp_neues_rect(pt))

    def _vp_fenster_start(self, vp, norm=False):
        self._vp_aktivieren(vp)
        self._vp_fenster = vp
        self._vp_fenster_norm = norm
        self.letzter_punkt = None
        de = SPRACHE["aktuell"] == "de"
        self.status.set(("Ausschnitt: 1. Eckpunkt des Modellfensters setzen "
                         "(Objektfang aktiv, ESC = abbrechen)." if de else
                         "View: set 1st corner of model window "
                         "(object snap active, ESC = cancel)."))

    def _vp_fenster_klick(self, x, y):
        vp = self._vp_fenster
        de = SPRACHE["aktuell"] == "de"
        if self.letzter_punkt is None:
            self.letzter_punkt = (x, y)
            self.status.set(("Ausschnitt: Gegenüberliegende Ecke setzen." if de
                             else "View: set opposite corner."))
            return
        x1, y1 = self.letzter_punkt
        bw, bh = abs(x - x1), abs(y - y1)
        if bw < 1e-9 or bh < 1e-9:
            return
        self._snapshot()
        vp.modell_zentrum_x = (x + x1) / 2
        vp.modell_zentrum_y = (y + y1) / 2
        z = min(vp.breite / bw, vp.hoehe / bh)
        if getattr(self, "_vp_fenster_norm", False):
            z = normmassstab_unter(z, MASSSTAEBE)
        vp.zoom = z
        self._vp_fenster = None
        self.letzter_punkt = None
        self._clear_temp()
        self.redraw()
        self._viewport_modus_anzeige_aktualisieren()
        self.status.set((f"Ausschnitt gesetzt, Maßstab {massstab_text(vp.zoom)}."
                         if de else
                         f"View set, scale {massstab_text(vp.zoom)}."))

    def _vp_massstab_setzen(self, vp, text):
        self._snapshot()
        vp.zoom = parse_massstab(text)
        self.redraw()
        if self._aktiver_viewport is vp:
            self._viewport_modus_anzeige_aktualisieren()
        de = SPRACHE["aktuell"] == "de"
        self.status.set((f"Viewport-Maßstab {text}" if de
                         else f"Viewport scale {text}"))

    def _vp_sperre_umschalten(self, vp):
        vp.gesperrt = not vp.gesperrt
        if self._aktiver_viewport is vp:
            self._viewport_modus_anzeige_aktualisieren()
        de = SPRACHE["aktuell"] == "de"
        self.status.set(("Viewport-Maßstab " + (
            "gesperrt." if vp.gesperrt else "entsperrt.") if de else
            "Viewport scale " + (
            "locked." if vp.gesperrt else "unlocked.")))

    def _zustand(self):
        return {"elemente": [e.to_dict() for e in self.elemente],
                "layouts": [l.to_dict() for l in self.layouts],
                "aktives_layout": self.aktives_layout,
                "layers": [l.to_dict() for l in self.layers.values()]}

    def _eingabe_punkt_werkzeug(self, text, einh):
        if self.letzter_punkt is None:
            pt = self._parse_xy(text, einh)
        else:
            pt = self._parse_punkt_eingabe(text, self.letzter_punkt[0],
                                           self.letzter_punkt[1], einh)
        self._zeichnen_werkzeug_anwenden(*pt)
        self.redraw()

    def _stil_auf_auswahl(self, event=None):
        ziele = [e for e in self.auswahl
                 if not isinstance(e, (Viewport, Text, Bemassung))]
        if not ziele:
            return
        self._snapshot()
        st = self._zahl(self.linienstaerke, 0.35)
        for el in ziele:
            el.staerke = st
            el.linientyp = self.linientyp.get()
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        self.status.set((f"Stärke {st} mm / {self.linientyp.get()} auf "
                         f"{len(ziele)} Element(e) angewendet." if de else
                         f"Weight {st} mm / {self.linientyp.get()} applied to "
                         f"{len(ziele)} element(s)."))

    def _op_start(self, typ):
        kind, vp = self._ctx()
        de = SPRACHE["aktuell"] == "de"
        if kind == "vp":
            self.status.set(("Bitte zuerst den Viewport verlassen (ESC)." if de
                             else "Please leave the viewport first (ESC)."))
            return
        if typ == "stretch":
            self.aktives_werkzeug.set("auswahl")
            self._pts = []
            self.letzter_punkt = None
            self._clear_temp()
            self.auswahl = []
            self._op = {"typ": "stretch", "stufe": "fenster", "basis": None,
                        "objekte": [], "fenster": None}
            self._drag_modus = None
            self.redraw()
            self._op_hinweis()
            self.status.set(("STRECKEN: Fenster überkreuzend aufziehen." if de
                             else "STRETCH: drag a crossing window."))
            return
        sel = list(self.auswahl)
        if self.aktives_werkzeug.get() != "auswahl":
            self.aktives_werkzeug.set("auswahl")
            self._werkzeug_gewechselt()
        self._pts = []
        self.letzter_punkt = None
        self._clear_temp()
        self.auswahl = sel
        self._op = {"typ": typ, "stufe": "wahl", "basis": None, "objekte": []}
        if sel:
            self._op_bestaetigen()
        else:
            self.redraw()
            self._op_hinweis()

    def _op_name(self):
        de = SPRACHE["aktuell"] == "de"
        return {"move": "VERSCHIEBEN" if de else "MOVE",
                "copy": "KOPIEREN" if de else "COPY",
                "copybase": "KOPIEREN MIT BASISPUNKT" if de else "COPY WITH BASE POINT",
                "array": "REIHE" if de else "ARRAY",
                "rotate": "DREHEN" if de else "ROTATE",
                "stretch": "STRECKEN" if de else "STRETCH"}.get(self._op["typ"], "")

    def _op_hinweis(self):
        op = self._op
        if op is None:
            return
        de = SPRACHE["aktuell"] == "de"
        if op.get("stufe") == "fenster":
            t = ("Fenster überkreuzend aufziehen (umfasst zu streckende Punkte)"
                 if de else
                 "Drag a crossing window (contains points to stretch)")
        elif op["stufe"] == "wahl":
            t = ("Objekte wählen, dann Enter oder Rechtsklick" if de
                 else "Select objects, then Enter or right-click")
        elif op["stufe"] == "basis":
            t = ("Basispunkt angeben (klicken oder x,y)" if de
                 else "Specify base point (click or x,y)")
        else:
            if op["typ"] == "copy":
                t = (("Zielpunkt: klicken, 'x,y', '@dx,dy', 'L<Winkel' - "
                      "Enter/Rechtsklick = fertig") if de else
                     ("Target point: click, 'x,y', '@dx,dy', 'L<angle' - "
                      "Enter/right-click = done"))
            elif op["typ"] == "rotate":
                t = (("Drehwinkel in Grad eingeben (gegen Uhrzeigersinn) "
                      "oder Maus bewegen + Klick") if de else
                     ("Enter rotation angle in degrees (CCW) "
                      "or move mouse + click"))
            elif op["typ"] == "stretch":
                t = ("Zielpunkt: klicken oder 'x,y' / '@dx,dy' / 'L<Winkel'"
                     if de else
                     "Target point: click or 'x,y' / '@dx,dy' / 'L<angle'")
            else:
                t = (("Zielpunkt: klicken, 'x,y', '@dx,dy' oder 'L<Winkel' "
                      "(Abstand)") if de else
                     ("Target point: click, 'x,y', '@dx,dy' or 'L<angle' "
                      "(distance)"))
        self.status.set(f"{self._op_name()}: {t}")
        self.lbl_hinweis.config(text=f"{self._op_name()}: {t}")

    def _op_bestaetigen(self):
        op = self._op
        de = SPRACHE["aktuell"] == "de"
        if not self.auswahl:
            self.status.set(("Keine Objekte gewählt - ESC bricht ab." if de
                             else "No objects selected - ESC cancels."))
            return
        op["objekte"] = list(self.auswahl)
        if op["typ"] == "array":
            self._op = None
            self._op_array()
            return
        op["stufe"] = "basis"
        self.redraw()
        self._op_hinweis()

    def _op_array(self):
        dlg = ArrayDialog(self.root, self)
        if not dlg.result:
            self.redraw()
            return
        nx, ny, dx, dy = dlg.result
        quellen = list(self.auswahl)
        self._snapshot()
        ziel = self._ziel_liste()
        neu = 0
        for i in range(ny):
            for j in range(nx):
                if i == 0 and j == 0:
                    continue
                for el in quellen:
                    k = self._dict_zu_element(el.to_dict())
                    if k is not None:
                        k.verschieben(j * dx, i * dy)
                        ziel.append(k)
                        neu += 1
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        self.status.set((f"Reihe: {neu} Kopie(n) erzeugt ({nx} x {ny})." if de
                         else f"Array: {neu} copy(ies) created ({nx} x {ny})."))

    def _op_klick(self, pt):
        op = self._op
        if op is None:
            return
        de = SPRACHE["aktuell"] == "de"
        if op["typ"] == "stretch":
            if op["stufe"] == "basis":
                op["basis"] = pt
                self.letzter_punkt = pt
                op["stufe"] = "ziel"
                self._op_hinweis()
                return
            if op["stufe"] == "ziel":
                dx, dy = pt[0] - op["basis"][0], pt[1] - op["basis"][1]
                if abs(dx) < 1e-12 and abs(dy) < 1e-12:
                    return
                self._snapshot()
                self._stretch_anwenden(op["fenster"], dx, dy)
                self._op_beenden(
                    (f"Gestrekt um dx={dx / self._einh_faktor():.3f}, "
                     f"dy={dy / self._einh_faktor():.3f} {self.einheit.get()}"
                     if de else
                     f"Stretched by dx={dx / self._einh_faktor():.3f}, "
                     f"dy={dy / self._einh_faktor():.3f} {self.einheit.get()}"))
                return
        if op["stufe"] == "basis":
            op["basis"] = pt
            self.letzter_punkt = pt
            if op["typ"] == "copybase":
                self._op_copybase_fertig()
                return
            op["stufe"] = "ziel"
            self._op_hinweis()
            return
        if op["stufe"] == "ziel":
            if op["typ"] == "rotate":
                bx, by = op["basis"]
                dx, dy = pt[0] - bx, pt[1] - by
                if math.hypot(dx, dy) < 1e-9:
                    return
                winkel = -math.degrees(math.atan2(dy, dx))
                self._snapshot()
                for el in op["objekte"]:
                    el.drehen(bx, by, winkel)
                self._op_beenden(
                    (f"Gedreht um {winkel:.2f}° um ({bx:.2f}, {by:.2f})"
                     if de else
                     f"Rotated by {winkel:.2f}° around ({bx:.2f}, {by:.2f})"))
                return
            dx, dy = pt[0] - op["basis"][0], pt[1] - op["basis"][1]
            if abs(dx) < 1e-12 and abs(dy) < 1e-12:
                return
            self._snapshot()
            ziel = self._ziel_liste()
            if op["typ"] == "move":
                for el in op["objekte"]:
                    el.verschieben(dx, dy)
                self._op_beenden(
                    (f"Verschoben um dx={dx / self._einh_faktor():.3f}, "
                     f"dy={dy / self._einh_faktor():.3f} {self.einheit.get()}"
                     if de else
                     f"Moved by dx={dx / self._einh_faktor():.3f}, "
                     f"dy={dy / self._einh_faktor():.3f} {self.einheit.get()}"))
            else:
                for el in op["objekte"]:
                    k = self._dict_zu_element(el.to_dict())
                    if k is not None:
                        k.verschieben(dx, dy)
                        ziel.append(k)
                self.redraw()
                self.status.set(
                    (f"Kopiert (dx={dx / self._einh_faktor():.3f}, "
                     f"dy={dy / self._einh_faktor():.3f}). Weiteren Zielpunkt "
                     "angeben oder Enter/Rechtsklick = fertig." if de else
                     f"Copied (dx={dx / self._einh_faktor():.3f}, "
                     f"dy={dy / self._einh_faktor():.3f}). Specify another "
                     "target point or Enter/right-click = done."))

    def _stretch_anwenden(self, fenster, dx, dy):
        xmin, ymin, xmax, ymax = fenster

        def innen(x, y):
            return xmin <= x <= xmax and ymin <= y <= ymax

        for el in self._aktuelle_elemente_liste():
            l = self.layers.get(el.layer)
            if l and not l.sichtbar:
                continue
            self._stretch_element(el, innen, dx, dy)

    def _stretch_element(self, el, innen, dx, dy):
        if isinstance(el, Linie):
            if innen(el.x1, el.y1):
                el.x1 += dx; el.y1 += dy
            if innen(el.x2, el.y2):
                el.x2 += dx; el.y2 += dy
        elif isinstance(el, Kreis):
            if innen(el.cx, el.cy):
                el.cx += dx; el.cy += dy
        elif isinstance(el, Bogen):
            if innen(el.cx, el.cy):
                el.cx += dx; el.cy += dy
        elif isinstance(el, Rechteck):
            if innen(el.x1, el.y1) or innen(el.x1, el.y2):
                el.x1 += dx
            if innen(el.x2, el.y1) or innen(el.x2, el.y2):
                el.x2 += dx
            if innen(el.x1, el.y1) or innen(el.x2, el.y1):
                el.y1 += dy
            if innen(el.x1, el.y2) or innen(el.x2, el.y2):
                el.y2 += dy
        elif isinstance(el, Polylinie):
            el.punkte = [((x + dx, y + dy) if innen(x, y) else (x, y))
                         for (x, y) in el.punkte]
        elif isinstance(el, Text):
            if innen(el.x, el.y):
                el.x += dx; el.y += dy
        elif isinstance(el, Bemassung):
            if innen(el.x1, el.y1):
                el.x1 += dx; el.y1 += dy
            if innen(el.x2, el.y2):
                el.x2 += dx; el.y2 += dy
            if innen(el.x1, el.y1) and innen(el.x2, el.y2):
                el.mx += dx; el.my += dy
                if el.tx is not None and el.ty is not None:
                    el.tx += dx; el.ty += dy
        elif isinstance(el, Viewport):
            x1, y1 = el.x, el.y
            x2, y2 = el.x + el.breite, el.y + el.hoehe
            ecken = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
            if all(innen(cx, cy) for cx, cy in ecken):
                el.x += dx; el.y += dy
            else:
                if innen(x1, y1) or innen(x1, y2):
                    x1 += dx
                if innen(x2, y1) or innen(x2, y2):
                    x2 += dx
                if innen(x1, y1) or innen(x2, y1):
                    y1 += dy
                if innen(x1, y2) or innen(x2, y2):
                    y2 += dy
                el.x = min(x1, x2); el.y = min(y1, y2)
                el.breite = abs(x2 - x1); el.hoehe = abs(y2 - y1)

    def _op_copybase_fertig(self):
        op = self._op
        self._clipboard = [e.to_dict() for e in op["objekte"]]
        self._clipboard_basispunkt = op["basis"]
        self._clipboard_mit_basis = True
        n = len(self._clipboard)
        de = SPRACHE["aktuell"] == "de"
        self._op_beenden(
            (f"{n} Objekt(e) mit Basispunkt kopiert - mit Strg+V einfügen "
             "(Basispunkt hängt am Mauszeiger)." if de else
             f"{n} object(s) copied with base point - paste with Ctrl+V "
             "(base point attached to cursor)."))

    def _op_beenden(self, meldung=""):
        self._op = None
        self.letzter_punkt = None
        self._clear_temp()
        self._snap_marker_loeschen()
        self.redraw()
        self._update_eingabe_hinweis()
        if meldung:
            self.status.set(meldung)

    def _op_rechtsklick(self):
        op = self._op
        if op is None:
            return False
        de = SPRACHE["aktuell"] == "de"
        if op["stufe"] == "wahl":
            if self.auswahl:
                self._op_bestaetigen()
            else:
                self._op_beenden("Abgebrochen." if de else "Cancelled.")
        elif op["stufe"] == "ziel" and op["typ"] == "copy":
            self._op_beenden("Kopieren beendet." if de else "Copy finished.")
        else:
            self._op_beenden("Abgebrochen." if de else "Cancelled.")
        return True

    def _op_vorschau(self, pt):
        op = self._op
        if op is None or op["stufe"] != "ziel":
            return
        tf, sk = self._ctx_zu_px, self._ctx_skala()
        stil = {"farbe": FARBEN["gruen"], "w": 1, "dash": (4, 3)}
        einh = self._einh_faktor()

        if op["typ"] == "stretch":
            dx, dy = pt[0] - op["basis"][0], pt[1] - op["basis"][1]
            xmin, ymin, xmax, ymax = op["fenster"]

            def innen(x, y):
                return xmin <= x <= xmax and ymin <= y <= ymax

            for el in self._aktuelle_elemente_liste():
                l = self.layers.get(el.layer)
                if l and not l.sichtbar:
                    continue
                klon = self._dict_zu_element(el.to_dict())
                if klon is None:
                    continue
                self._stretch_element(klon, innen, dx, dy)
                if isinstance(klon, Viewport):
                    x1_, y1_ = self.mm_to_px(klon.x, klon.y + klon.hoehe)
                    x2_, y2_ = self.mm_to_px(klon.x + klon.breite, klon.y)
                    self.canvas.create_rectangle(x1_, y1_, x2_, y2_,
                                                 outline=FARBEN["gruen"],
                                                 dash=(5, 3), tags="vorschau")
                else:
                    self._zeichne_element(klon, tags=("vorschau",), tf=tf,
                                          skala=sk, stil=stil)
            bx, by = tf(*op["basis"])
            px_, py_ = tf(*pt)
            self.canvas.create_line(bx, by, px_, py_, fill=FARBEN["gelb"],
                                    dash=(2, 3), tags="vorschau")
            self.canvas.create_text(
                px_ + 10, py_ - 14, anchor=tk.W, fill=FARBEN["gelb"],
                font=("Segoe UI", 9, "bold"), tags="vorschau",
                text=f"dx {dx / einh:.2f}  dy {dy / einh:.2f}")
            return

        if op["typ"] == "rotate":
            bx, by = op["basis"]
            dx, dy = pt[0] - bx, pt[1] - by
            winkel = (-math.degrees(math.atan2(dy, dx))
                      if math.hypot(dx, dy) > 1e-9 else 0.0)
            for el in op["objekte"]:
                k = self._dict_zu_element(el.to_dict())
                if k is None:
                    continue
                k.drehen(bx, by, winkel)
                if isinstance(k, Viewport):
                    x1, y1 = self.mm_to_px(k.x, k.y + k.hoehe)
                    x2, y2 = self.mm_to_px(k.x + k.breite, k.y)
                    self.canvas.create_rectangle(x1, y1, x2, y2,
                                                 outline=FARBEN["gruen"],
                                                 dash=(4, 3), tags="vorschau")
                else:
                    self._zeichne_element(k, tags=("vorschau",), tf=tf, skala=sk,
                                          stil=stil)
            bx_px, by_px = tf(bx, by)
            px_, py_ = tf(*pt)
            self.canvas.create_line(bx_px, by_px, px_, py_,
                                    fill=FARBEN["gelb"], dash=(2, 3),
                                    tags="vorschau")
            self.canvas.create_text(px_ + 10, py_ - 14, anchor=tk.W,
                                    fill=FARBEN["gelb"],
                                    font=("Segoe UI", 9, "bold"),
                                    tags="vorschau",
                                    text=f"{winkel:.2f}°")
            return

        dx, dy = pt[0] - op["basis"][0], pt[1] - op["basis"][1]
        for el in op["objekte"]:
            k = self._dict_zu_element(el.to_dict())
            if k is None:
                continue
            k.verschieben(dx, dy)
            if isinstance(k, Viewport):
                x1, y1 = self.mm_to_px(k.x, k.y + k.hoehe)
                x2, y2 = self.mm_to_px(k.x + k.breite, k.y)
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=FARBEN["gruen"],
                                             dash=(4, 3), tags="vorschau")
            else:
                self._zeichne_element(k, tags=("vorschau",), tf=tf, skala=sk, stil=stil)
        bx, by = tf(*op["basis"])
        px_, py_ = tf(*pt)
        self.canvas.create_line(bx, by, px_, py_, fill=FARBEN["gelb"],
                                dash=(2, 3), tags="vorschau")
        self.canvas.create_text(px_ + 10, py_ - 14, anchor=tk.W, fill=FARBEN["gelb"],
                                font=("Segoe UI", 9, "bold"), tags="vorschau",
                                text=f"dx {dx / einh:.2f}  dy {dy / einh:.2f}  |  "
                                     f"{math.hypot(dx, dy) / einh:.2f} {self.einheit.get()}")

    def _eingabe_op(self, text, einh):
        op = self._op
        if op is None:
            return
        if op["typ"] == "stretch":
            if op["stufe"] == "basis":
                self._op_klick(self._parse_xy(text, einh))
                return
            if op["stufe"] == "ziel":
                self._op_klick(self._parse_punkt_eingabe(
                    text, op["basis"][0], op["basis"][1], einh))
                return
        if op["stufe"] == "basis":
            pt = self._parse_xy(text, einh)
            self._op_klick(pt)
            return
        if op["typ"] == "rotate":
            t = text.strip().replace(",", ".")
            try:
                winkel = -float(t)
                bx, by = op["basis"]
                self._snapshot()
                for el in op["objekte"]:
                    el.drehen(bx, by, winkel)
                de = SPRACHE["aktuell"] == "de"
                self._op_beenden(
                    (f"Gedreht um {-winkel:.2f}° um ({bx:.2f}, {by:.2f})"
                     if de else
                     f"Rotated by {-winkel:.2f}° around ({bx:.2f}, {by:.2f})"))
                return
            except ValueError:
                pass
            pt = self._parse_punkt_eingabe(text, op["basis"][0],
                                           op["basis"][1], einh)
            self._op_klick(pt)
            return
        pt = self._parse_punkt_eingabe(text, op["basis"][0], op["basis"][1], einh)
        self._op_klick(pt)

    def _eingabe_leer(self):
        if self._op is not None:
            self._op_rechtsklick()
        elif self.aktives_werkzeug.get() == "polylinie" and self.aktuelle_polylinie:
            self._polylinie_abschliessen(geschlossen=False)
            self.letzter_punkt = None

    def _eingabe_polylinie(self, text, einh):
        if self.letzter_punkt is None:
            pt = self._parse_xy(text, einh)
        else:
            pt = self._parse_punkt_eingabe(text, self.letzter_punkt[0],
                                           self.letzter_punkt[1], einh)
        self._zeichnen_werkzeug_anwenden(*pt)
        self.redraw()

    def _befehl(self, cmd, arg=""):
        arg = arg.strip()
        if cmd in ("raster", "fang"):
            self._cmd_wert(cmd, arg)
        elif cmd in ("ofang", "ortho"):
            var = self.osnap if cmd == "ofang" else self.ortho
            a = arg.upper()
            if a in ("EIN", "ON", "AN"):
                var.set(True)
            elif a in ("AUS", "OFF"):
                var.set(False)
            else:
                var.set(not var.get())
            de = SPRACHE["aktuell"] == "de"
            name = (("Objektfang" if cmd == "ofang" else "Ortho") if de
                    else ("Object snap" if cmd == "ofang" else "Ortho"))
            self.status.set(f"{name}: {'EIN' if var.get() else 'AUS'}")
        elif cmd in ("move", "copy", "copybase", "array", "rotate", "stretch"):
            self._op_start(cmd)
        elif cmd == "paste":
            self.einfuegen()
        elif cmd == "druck":
            self.drucken()
        elif cmd == "undo":
            self.undo()
        elif cmd == "delete":
            self.auswahl_loeschen()
        elif cmd == "zg":
            self.zoom_grenzen()
        elif cmd.startswith("tool:"):
            self.aktives_werkzeug.set(cmd[5:])
            self._werkzeug_gewechselt()

    def _cmd_wert(self, cmd, arg):
        var = self.raster_mm if cmd == "raster" else self.fang_mm
        de = SPRACHE["aktuell"] == "de"
        name = ("Raster" if cmd == "raster" else "Fang") if de else \
               ("Grid" if cmd == "raster" else "Snap")

        def setze(text):
            t = text.strip().upper()
            if t in ("EIN", "ON", "AN"):
                (self.raster_sichtbar if cmd == "raster" else self.grid_snap).set(True)
            elif t in ("AUS", "OFF"):
                (self.raster_sichtbar if cmd == "raster" else self.grid_snap).set(False)
            elif t:
                wert = self._parse_einzelwert(text, self._einh_faktor())
                if wert <= 0:
                    raise ValueError(("Der Wert muss größer als 0 sein." if de
                                      else "Value must be greater than 0."))
                var.set(round(wert, 6))
                if cmd == "fang":
                    self.grid_snap.set(True)
            self._zeichne_raster()
            self.redraw()
            an = (self.raster_sichtbar if cmd == "raster" else self.grid_snap).get()
            self.status.set(f"{name}: {var.get():g} mm, {'EIN' if an else 'AUS'}")

        if arg:
            try:
                setze(arg)
            except Exception as ex:
                messagebox.showerror(name, str(ex))
        else:
            self._cmd_pending = setze
            txt = ((f"{name}weite eingeben [aktuell {var.get():g} mm] oder "
                    "EIN/AUS") if de else
                   (f"Enter {name.lower()} spacing [current {var.get():g} mm] "
                    "or ON/OFF"))
            self.lbl_hinweis.config(text=txt)
            self.status.set(txt)
            self.entry_eingabe.focus_set()

    def _kontextmenue(self, event):
        de = SPRACHE["aktuell"] == "de"
        stil = dict(tearoff=0, bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                    activebackground=FARBEN["cyan"],
                    activeforeground=FARBEN["bg_dunkel"])
        m = tk.Menu(self.root, **stil)
        if self.auswahl:
            m.add_command(label=("Verschieben (Basispunkt)" if de
                                 else "Move (base point)"),
                          command=lambda: self._op_start("move"))
            m.add_command(label=("Kopieren (Basispunkt, mehrfach)" if de
                                 else "Copy (base point, multiple)"),
                          command=lambda: self._op_start("copy"))
            m.add_command(label=("Kopieren mit Basispunkt (COPYBASE)" if de
                                 else "Copy with base point (COPYBASE)"),
                          command=lambda: self._op_start("copybase"))
            m.add_command(label=("Reihe (Anordnung)..." if de else "Array..."),
                          command=lambda: self._op_start("array"))
            m.add_command(label=tr("menu.bearbeiten.drehen_basis"),
                          command=lambda: self._op_start("rotate"))
            m.add_separator()
            m.add_command(label=("Löschen" if de else "Delete"),
                          command=self.auswahl_loeschen)
            m.add_separator()
        m.add_command(label=("Einfügen" if de else "Paste"), command=self.einfuegen)
        m.add_command(label=("Alles markieren" if de else "Select all"),
                      command=self.alle_markieren)
        m.add_command(label=("Zoom Grenzen" if de else "Zoom extents"),
                      command=self.zoom_grenzen)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def drucken(self):
        dlg = DruckDialog(self.root, self)
        if not dlg.result:
            return
        aktion, quelle, farbig, rahmen, layout_index = dlg.result
        try:
            daten = pdf_erzeugen(self, quelle, farbig, rahmen, layout_index)
        except Exception as ex:
            messagebox.showerror("PDF", str(ex))
            return
        de = SPRACHE["aktuell"] == "de"
        if aktion == "pdf":
            pfad = filedialog.asksaveasfilename(
                defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if not pfad:
                return
            with open(pfad, "wb") as f:
                f.write(daten)
            self.status.set((f"PDF gespeichert: {pfad}" if de
                             else f"PDF saved: {pfad}"))
        else:
            fd, pfad = tempfile.mkstemp(suffix=".pdf", prefix="katiecad_")
            with os.fdopen(fd, "wb") as f:
                f.write(daten)
            pdf_senden(pfad, aktion == "druck")
            self.status.set(("An den Drucker gesendet." if de
                             else "Sent to printer.") if aktion == "druck" else
                            ("Vorschau geöffnet." if de else "Preview opened."))


# ============================================================
def main():
    root = tk.Tk()
    app = CadApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
