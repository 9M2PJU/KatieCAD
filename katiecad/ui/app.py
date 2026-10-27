# -*- coding: utf-8 -*-
"""
katiecad/ui/app.py - GUI of KatieCAD (CadApp, main()).
Contains the Tkinter UI, events, tools and the app state.
Dialogs are in katiecad/ui/dialogs.py, PDF output in katiecad/fileio/pdf.py.

NEW (step 7 - EXPLODE):
  - The EXPLODE/X/AUFLOESEN command explodes selected blocks into their
    child elements.
  - The context menu offers "Explode block" when a block is selected.
NEW (electrical base): redo + sidebar, projects with sheets,
  block attributes (ATTDEF/ATTEDIT) and block files (*.katieblock).
NEW (step 8 - HATCHING):
  - New element hatching (solid and lines).
  - Menu item "Hatch selection" under Insert.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
import math, json, re, zlib
from copy import deepcopy
import os, sys, tempfile, subprocess, datetime, time
_PROJEKT_WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter.font as tkfont

try:
    import ezdxf
    EZDXF_VERFUEGBAR = True
except ImportError:
    EZDXF_VERFUEGBAR = False

try:
    from katiecad.fileio import cad_import as cadimport
    CADIMPORT_VERFUEGBAR = True
except ImportError:
    CADIMPORT_VERFUEGBAR = False

try:
    from PIL import Image, ImageTk
    PILLOW_VERFUEGBAR = True
except ImportError:
    PILLOW_VERFUEGBAR = False

from katiecad.common.i18n import tr, SPRACHE, setze_sprache, TEXTE
from katiecad.common.config import (lade_konfiguration, speichere_sprache,
                             speichere_konfiguration)
from katiecad.model import titleblock as TB
from katiecad.model.project import (Projekt, ProjektFehler, PROJEKT_ENDUNG,
                              BLOCK_ENDUNG)
from katiecad.model.blocks import (block_speichern, block_laden,
                              vorschlag_dateiname, BlockDateiFehler,
                              vorschau_geometrie, standard_ordner, symbol_ordner)
from katiecad.ui.menuleiste import MenuLeiste
from katiecad.ui.sidebar import Seitenleiste
from katiecad.ui.widgets import FlatButton, farb_swatch
from katiecad.model.core import (
    FARBEN, EINHEITEN, ZEICHNUNGSFORMATE, MASSSTAEBE, LINIENTYPEN,
    RASTER_GROESSEN, BG_PRESETS, SCHRIFTARTEN, LINIENSTAERKEN,
    GRIFF_RADIUS, MIN_VP_GROESSE, PASTE_OFFSET_MM,
    TEXT_BREITE, TEXT_ZEILE, CAD_VERSALHOEHE, LW_PX_FAKTOR, BEM_RICHTUNGEN,
    BEFEHLE, PdfSeite, ist_dunkel,
    E_DEVICES, E_LINES, E_CABLE, E_CLAMPS, E_PIN, ELEKTRO_LAYER,
    Layer, Layout, Element, Linie, Kreis, Bogen, Rechteck, Polylinie, Text,
    Bemassung, Viewport, Schraffur, Bild, konturen_aus_elementen, bereich_an_punkt,
    AttributDefinition, Leitung, Verbindungspunkt, Querverweis,
    Verbindung, ElektroMaske, Klemme, Kabel, Koordinatenfeld, ZUSAMMENGESETZT,
    vp_tags_eindeutig, LEITUNG_FARBE, UI_SCHRIFT,
    BlockDefinition, BlockReferenz, BlockBibliothek,
    bogen_sweep, bogen_punkte, winkel_im_bogen, bogen_aus_3_punkten,
    bogen_mitte_start_ende, abstand_punkt_segment, naechster_punkt_segment,
    clip_polyline, gedrehtes_rechteck, punkt_in_gedrehtem_rechteck,
    bem_zahl, parse_massstab, massstab_text, normmassstab_unter,
    lot_fuss, linien_schnitt, bbox_enthalten, bbox_ueberlappt,
    punkte_drehen, norm360,
    trim_linie, trim_polylinie, trim_bogen, kreis_zu_bogen,
    teile_bogen_durch_winkel,
)
from katiecad.ui.dialogs import (
    MIT_LICENSE_TEXT, zeige_lizenz_fenster,
    _LayoutNameDialog, BlattEigenschaftenDialog, PropertiesDialog, ViewportDialog,
    LayerDialog, LayerEditDialog, TextDialog, ArrayDialog, SchraffurDialog, DruckDialog,
    _BlockNameDialog, _BlockAuswahlDialog, BlockBrowserDialog,
    BlockSpeichernDialog,
    ProjektNeuDialog, AttributDefinitionDialog, BlockAttributeDialog,
    SuchenErsetzenDialog, QuerverweisDialog, PruefungDialog, EigenschaftenPalette, VerbindungspunkteDialog, ProjektDruckDialog,
    VerbindungspunktDialog, VerbindungDialog, FestMaskeDialog,
    KoordinatenfeldDialog,
    TitleBlockDialog, DokumentationDialog, ProjektEigenschaftenDialog,
)
from katiecad.reports import seiten as SEI, anwenden as ANW
from katiecad.fileio.pdf import pdf_erzeugen, pdf_senden, pdf_mehrseitig_erzeugen
from katiecad.electrical.logic import (leitungen_automatisch, kabel_kreuzungen, querverweis_ziele, qv_texte_aus_blattdaten,
                              qv_texte_aus_elementen, naechster_vp,
                              naechster_anschluss, anschlusspunkte,
                              naechste_bezeichnung, geraete,
                              geraete_aus_blattdaten, geraete_referenzen,
                              naechster_leitungspunkt, leitung_teilen,
                              vollstaendige_verbindungen, vollstaendige_leitungen,
                              leitungen_einrasten,
                              verbindungen_bereinigen)
from types import SimpleNamespace

ELEKTRO_WERKZEUGE = ("vpunkt", "verbindung", "leitung", "querverweis",
                     "maske", "klemme", "koordinatenfeld", "kabel")


# ============================================================
# Style setup (tkinter-dependent, therefore here)
# ============================================================
# macOS: right mouse button = Button-2, middle = Button-3 (reversed on X11/Windows)
_MAC = sys.platform == "darwin"
BTN_MITTE, BTN_RECHTS = ("3", "2") if _MAC else ("2", "3")


def _style_setup(root):
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except Exception:
        pass

    st.configure("TFrame", background=FARBEN["bg_mittel"])
    st.configure("TLabel", background=FARBEN["bg_mittel"],
                 foreground=FARBEN["text"], font=(UI_SCHRIFT, 9))
    st.configure("Title.TLabel", background=FARBEN["bg_mittel"],
                 foreground=FARBEN["cyan"], font=(UI_SCHRIFT, 9, "bold"))
    st.configure("Hint.TLabel", background=FARBEN["bg_mittel"],
                 foreground=FARBEN["cyan"], font=(UI_SCHRIFT, 9, "italic"))

    st.configure("TButton",
                 background=FARBEN["bg_hell"],
                 foreground=FARBEN["cyan"],
                 borderwidth=1, focusthickness=0,
                 font=(UI_SCHRIFT, 9, "bold"),
                 padding=(8, 4))
    st.map("TButton",
           background=[("active", FARBEN["bg_hover"]),
                       ("pressed", FARBEN["cyan_dunkel"])],
           foreground=[("active", FARBEN["text_hell"])])

    st.configure("TRadiobutton",
                 background=FARBEN["bg_mittel"],
                 foreground=FARBEN["text"],
                 font=(UI_SCHRIFT, 9))
    st.map("TRadiobutton",
           background=[("active", FARBEN["bg_mittel"])],
           foreground=[("active", FARBEN["cyan"]),
                       ("selected", FARBEN["cyan"])])

    st.configure("TCheckbutton",
                 background=FARBEN["bg_mittel"],
                 foreground=FARBEN["text"],
                 font=(UI_SCHRIFT, 9))
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
                 font=(UI_SCHRIFT, 9, "bold"))
    st.map("Treeview",
           background=[("selected", FARBEN["select_bg"])],
           foreground=[("selected", FARBEN["select_fg"])])


# ============================================================
# Main application
# ============================================================
def geraete_aus_blattdaten_liste(app, j):
    """Devices (per, role, ind) of sheet j - the active sheet from memory,
    the others from the file (with cache)."""
    p = app.projekt
    if j == p.aktiv:
        return [(g["per"], g["rolle"], g["ind"], g.get("feld", ""),
                 g.get("pins", []))
                for g in geraete(app.elemente, j + 1)]
    return app._geraete_blatt(p.blatt_pfad(j))


class CadApp:
    def __init__(self, root):
        self.root = root
        if _MAC:
            # Every <Control-...> shortcut also applies with Cmd on the Mac
            _orig_bind = self.root.bind

            def _bind_mac(seq=None, func=None, add=None):
                res = _orig_bind(seq, func, add)
                if func is not None and seq and seq.startswith("<Control-"):
                    _orig_bind("<Command-" + seq[len("<Control-"):], func, add)
                return res
            self.root.bind = _bind_mac
        self.root.title("KatieCAD")
        self.root.geometry("1500x950")
        self.root.configure(bg=FARBEN["bg_dunkel"])

        _cfg = lade_konfiguration()
        setze_sprache(_cfg.get("sprache", "en"))

        try:
            from katiecad.manifest import fehlende_module, VERSION
            fehlend = fehlende_module()
            if fehlend:
                print(f"[KatieCAD] ACHTUNG – fehlende Module: {fehlend}")
            else:
                print(f"[KatieCAD] Version {VERSION} – alle Module vorhanden.")
        except Exception as e:
            print(f"[KatieCAD] Manifest-Check übersprungen: {e}")

        _style_setup(root)

        self.layers = self._standard_layers()
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
        self._redo_stack = []
        self._undo_max = 50
        self._undo_pro_blatt = {}
        self.projekt = None             # current project (or None)
        self._attdef_wartend = None     # Attribute definition waiting to be placed
        self._leitung_p1 = None         # Wire tool: first point
        self._leitung_dialog = None
        self._qv_vorgabe = None         # Cross-reference settings
        self._vp_letzte_bez = ""
        self._vp_text_anzeigen = True
        self._qv_cache = {}
        self._ge_cache = {}
        self._vb_vorgabe = None
        self._vp_vorgabe = None
        self._mk_werte = {}
        self._mk_rolle = "haupt"
        self._mk_spiegel = "liste"
        self._kl_werte = {}
        self._vp_richtungen = (0, 90, 180, 270)
        self._kabel_p1 = None
        self._kb_werte = {}
        self._kf_werte = {"spalten": 6, "zeilen": 4, "breite": 287.0,
                          "hoehe": 164.0, "raster": False}
        self._geraet_modus = False

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
        self._hatch_pick = None
        self._prop_pick = None
        self._letztes_fenster = None
        self._menuleiste = None
        self._menubar = None

        self._trim_status = "none"
        self._trim_grenzen = []
        self._trim_anzahl = 0
        self._break_status = "none"
        self._break_el = None
        self._break_p1 = None

        self.sprache_var = tk.StringVar(value=SPRACHE["aktuell"])

        self._info_logo = None

        self.block_bibliothek = BlockBibliothek(self._dict_zu_element)
        self._block_einfuege_name = None
        self._warte_auf_blockpunkt = False
        self._block_erzeuge_auswahl = None

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
        p = getattr(self, "projekt", None)
        if p is not None and p.blaetter:
            b = p.blaetter[p.aktiv]
            basis = f"KatieCAD \u2013 {p.name} \u2013 {p.nummer(p.aktiv)} {b.name}"
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
    # Language switching
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
        self.seitenleiste.neu_beschriften()
        self._update_titel()
        self.redraw()

    # --------------------------------------------------------
    # Undo / Redo
    # --------------------------------------------------------
    def _aktualisiere_undo_redo(self):
        sl = getattr(self, "seitenleiste", None)
        if sl is not None:
            sl.undo_redo_setzen(bool(self._undo_stack), bool(self._redo_stack))

    @staticmethod
    def _snap_groesse(st):
        try:
            n = len(st.get("elemente", ()))
            n += sum(len(l.get("elemente", ())) for l in st.get("layouts", ()))
            return n
        except Exception:
            return 0

    def _snap_pack(self, st):
        """Large drawings: store the state compressed (factor ~10-20).
        Without it every one of the up to 50 undo steps occupies a full copy
        of all elements (quickly several GB with DXF imports)."""
        if self._snap_groesse(st) < 1500:
            return st
        raw = json.dumps(st, separators=(",", ":")).encode("utf-8")
        return ("z", zlib.compress(raw, 1))

    @staticmethod
    def _snap_unpack(snap):
        if isinstance(snap, tuple) and len(snap) == 2 and snap[0] == "z":
            return json.loads(zlib.decompress(snap[1]).decode("utf-8"))
        return snap

    def _historie_limit(self, n_elemente):
        """Max. steps per stack; fewer for large drawings."""
        if n_elemente < 3000:
            return self._undo_max
        return max(8, min(self._undo_max, 150000 // max(1, n_elemente)))

    def _stapel_begrenzen(self, stapel, n_elemente):
        grenze = self._historie_limit(n_elemente)
        while len(stapel) > grenze:
            stapel.pop(0)

    def _stacks_merken(self, pfad):
        """Remember the undo/redo of a sheet for later return - but only
        for the most recently visited sheets (memory)."""
        self._undo_pro_blatt.pop(pfad, None)
        self._undo_pro_blatt[pfad] = (self._undo_stack, self._redo_stack)
        while len(self._undo_pro_blatt) > 4:
            self._undo_pro_blatt.pop(next(iter(self._undo_pro_blatt)))

    def _push_undo(self, vorher):
        """Puts a state onto the undo stack BEFORE a change.
        Every new change invalidates the redo history."""
        n = self._snap_groesse(vorher)
        self._undo_stack.append(self._snap_pack(vorher))
        self._stapel_begrenzen(self._undo_stack, n)
        self._redo_stack.clear()
        self._mark_dirty()
        self._aktualisiere_undo_redo()

    def _undo_reset(self):
        self._undo_stack = []
        self._redo_stack = []
        self._aktualisiere_undo_redo()

    def _snapshot(self):
        try:
            self._push_undo(self._zustand())
        except Exception as e:
            print(f"Snapshot-Fehler: {e}")

    def undo(self):
        self._historie_schritt(self._undo_stack, self._redo_stack,
                               "msg.undo.leer", "msg.undo.fertig")

    def redo(self):
        self._historie_schritt(self._redo_stack, self._undo_stack,
                               "msg.redo.leer", "msg.redo.fertig")

    def _historie_schritt(self, quelle, ziel, leer_key, fertig_key):
        if not quelle:
            self.status.set(tr(leer_key))
            return
        aktuell_roh = self._zustand()
        aktuell = self._snap_pack(aktuell_roh)
        snap_roh = quelle.pop()
        ziel.append(aktuell)
        self._stapel_begrenzen(ziel, self._snap_groesse(aktuell_roh))
        try:
            snap = self._snap_unpack(snap_roh)
            self._zustand_wiederherstellen(snap)
        except Exception as e:
            print(f"Undo/Redo-Fehler: {e}")
            if ziel and ziel[-1] is aktuell:
                ziel.pop()
            quelle.append(snap_roh)
            self._aktualisiere_undo_redo()
            return
        self._mark_dirty()
        self._aktualisiere_undo_redo()
        self.status.set(tr(fertig_key))

    def _zustand_wiederherstellen(self, snap):
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
        self._trim_abbrechen()
        self._break_abbrechen()
        self._layout_switcher_neu_aufbauen()
        self._viewport_modus_anzeige_aktualisieren()
        self.redraw()

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
        self._einrasten(neue_el)
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
        self._einrasten(neue_el)
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

    def _trim_abbrechen(self):
        self._trim_status = "none"
        self._trim_grenzen = []
        self._trim_anzahl = 0
        self._clear_temp()

    def _break_abbrechen(self):
        self._break_status = "none"
        self._break_el = None
        self._break_p1 = None
        self._clear_temp()

    # --------------------------------------------------------
    # UI construction
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

        self.seitenleiste = Seitenleiste(
            self.root, self,
            breite=lade_konfiguration().get("sidebar_breite"))
        self.seitenleiste.einbauen()
        if lade_konfiguration().get("sidebar_sichtbar") is False:
            self.seitenleiste.ausblenden()

        self.canvas = tk.Canvas(self.root, bg=self.bg_modell,
                                highlightthickness=1,
                                highlightbackground=FARBEN["rand"],
                                cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._build_viewport_leiste()

        self._update_kontext_widgets()
        self._viewport_modus_anzeige_aktualisieren()

    def _build_koord_bar(self):
        koord_bar = tk.Label(self.root, textvariable=self.status,
                             relief=tk.SUNKEN, anchor=tk.W,
                             padx=6, pady=4,
                             bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                             font=("Consolas", 9))
        # Must come before the side bar in the packing order; if the side
        # bar is hidden (saved setting) it is not packed, so use the canvas.
        vor = (self.seitenleiste if self.seitenleiste.ist_sichtbar()
               else self.canvas)
        koord_bar.pack(side=tk.BOTTOM, fill=tk.X, before=vor)

    def _build_menu(self):
        # Forces the dark colour for the menu
        self.root.option_add('*Menu.background', FARBEN["bg_mittel"])
        self.root.option_add('*Menu.foreground', FARBEN["cyan"])
        self.root.option_add('*Menu.activeBackground', FARBEN["cyan"])
        self.root.option_add('*Menu.activeForeground', FARBEN["bg_dunkel"])
        # Drop-down lists of the comboboxes (otherwise light/inconsistent on Linux/Mac)
        self.root.option_add('*TCombobox*Listbox.background', FARBEN["bg_hell"])
        self.root.option_add('*TCombobox*Listbox.foreground', FARBEN["cyan"])
        self.root.option_add('*TCombobox*Listbox.selectBackground', FARBEN["select_bg"])
        self.root.option_add('*TCombobox*Listbox.selectForeground', FARBEN["select_fg"])

        menubar = tk.Menu(self.root,
                          bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                          activebackground=FARBEN["cyan"],
                          activeforeground=FARBEN["bg_dunkel"], bd=0)

        # File
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
        m_datei.add_command(label=tr("menu.datei.import_pdf"), command=self.import_pdf)
        m_datei.add_command(label=tr("menu.datei.import_bild"), command=self.import_bild)
        m_datei.add_command(label=tr("menu.datei.export_dxf"), command=self.export_dxf)
        m_datei.add_command(label=tr("menu.datei.export_dwg"), command=self.export_dwg)
        m_datei.add_separator()
        m_datei.add_command(label=tr("menu.datei.drucken"), command=self.drucken)
        m_datei.add_separator()
        m_datei.add_command(label=tr("menu.datei.beenden"), command=self.beenden)
        menubar.add_cascade(label=tr("menu.datei"), menu=m_datei)

        # Project
        m_projekt = tk.Menu(menubar, tearoff=0,
                            bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                            activebackground=FARBEN["cyan"],
                            activeforeground=FARBEN["bg_dunkel"])
        m_projekt.add_command(label=tr("menu.projekt.erstellen"),
                              command=self.projekt_erstellen)
        m_projekt.add_command(label=tr("menu.projekt.oeffnen"),
                              command=self.projekt_oeffnen)
        m_projekt.add_command(label=tr("menu.projekt.speichern"),
                              command=self.projekt_speichern)
        m_projekt.add_command(label=tr("menu.projekt.schliessen"),
                              command=self.projekt_schliessen)
        m_projekt.add_command(label=tr("menu.projekt.umbenennen"),
                              command=self.projekt_umbenennen)
        m_projekt.add_command(label=tr("menu.projekt.eigenschaften"),
                              command=self.projekt_eigenschaften)
        m_projekt.add_command(label=tr("menu.projekt.tbfelder"),
                              command=self.schriftkopf_felder_pruefen)
        m_projekt.add_command(label=tr("menu.projekt.pruefen"),
                              command=self.projekt_pruefen)
        m_projekt.add_separator()
        m_projekt.add_command(label=tr("menu.projekt.blatt_neu"),
                              command=self.blatt_neu)
        m_projekt.add_command(label=tr("menu.projekt.blatt_duplizieren"),
                              command=self.blatt_duplizieren)
        m_projekt.add_command(label=tr("menu.projekt.blatt_umbenennen_f2"),
                              command=self.blatt_umbenennen)
        m_projekt.add_command(label=tr("menu.projekt.blatt_loeschen"),
                              command=self.blatt_loeschen)
        m_projekt.add_separator()
        m_projekt.add_command(label=tr("menu.projekt.drucken"),
                              command=self.projekt_drucken)
        m_projekt.add_command(label=tr("menu.datei.export_projekt_dxf"),
                              command=self.projekt_dxf_exportieren)
        m_projekt.add_separator()
        m_projekt.add_command(label=tr("menu.projekt.doku"),
                              command=self.dokumentation_erzeugen)
        m_projekt.add_command(label=tr("menu.projekt.doku_csv"),
                              command=self.dokumentation_csv)
        m_projekt.add_separator()
        m_projekt.add_command(label=tr("menu.projekt.loeschen"),
                              command=self.projekt_loeschen)
        menubar.add_cascade(label=tr("menu.projekt"), menu=m_projekt)

        # Edit
        m_bearb = tk.Menu(menubar, tearoff=0,
                          bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                          activebackground=FARBEN["cyan"],
                          activeforeground=FARBEN["bg_dunkel"])
        m_bearb.add_command(label=tr("menu.bearbeiten.undo"), command=self.undo)
        m_bearb.add_command(label=tr("menu.bearbeiten.redo"), command=self.redo)
        m_bearb.add_separator()
        m_bearb.add_command(label=tr("menu.bearbeiten.kopieren"), command=self.kopieren)
        m_bearb.add_command(label=tr("menu.bearbeiten.kopieren_basis"),
                            command=self.kopieren_mit_basispunkt)
        m_bearb.add_command(label=tr("menu.bearbeiten.ausschneiden"), command=self.ausschneiden)
        m_bearb.add_command(label=tr("menu.bearbeiten.einfuegen"), command=self.einfuegen)
        m_bearb.add_command(label=tr("menu.bearbeiten.duplizieren"), command=self.duplizieren)
        m_bearb.add_command(label=tr("menu.bearbeiten.eigenschaften"),
                            command=self.eigenschaften_fenster)
        m_bearb.add_command(label=tr("menu.bearbeiten.suchen"),
                            command=self.suchen_ersetzen)
        m_bearb.add_command(label=tr("menu.bearbeiten.eig_uebertragen"),
                            command=self.eigenschaften_uebertragen_start)
        m_bearb.add_separator()
        m_bearb.add_command(label=tr("menu.bearbeiten.verschieben"),
                            command=lambda: self._op_start("move"))
        m_bearb.add_command(label=tr("menu.bearbeiten.kopieren_praezise"),
                            command=lambda: self._op_start("copy"))
        m_bearb.add_command(label=tr("menu.bearbeiten.reihe"),
                            command=lambda: self._op_start("array"))
        m_bearb.add_command(label=tr("menu.bearbeiten.drehen"),
                            command=lambda: self._op_start("rotate"))
        m_bearb.add_command(label=tr("menu.bearbeiten.skalieren"),
                            command=lambda: self._op_start("scale"))
        m_bearb.add_command(label=tr("menu.bearbeiten.spiegeln"),
                            command=lambda: self._op_start("mirror"))
        m_bearb.add_command(label=tr("menu.bearbeiten.strecken"),
                            command=lambda: self._op_start("stretch"))
        m_bearb.add_command(label=tr("tb.wz.stutzen"),
                            command=lambda: self._werkzeug_aus_menue("stutzen"))
        m_bearb.add_command(label=tr("tb.wz.brechen"),
                            command=lambda: self._werkzeug_aus_menue("brechen"))
        m_bearb.add_separator()
        m_bearb.add_command(label=tr("menu.bearbeiten.alles_loeschen"), command=self.neu)
        m_bearb.add_separator()
        m_bearb.add_command(label=tr("menu.bearbeiten.auswahl_loeschen"),
                            command=self.auswahl_loeschen)
        m_bearb.add_command(label=tr("menu.bearbeiten.alles_markieren"),
                            command=self.alle_markieren)
        menubar.add_cascade(label=tr("menu.bearbeiten"), menu=m_bearb)

        # Insert
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
        m_einf.add_command(label=tr("menu.einfuegen.radius"),
                           command=lambda: self._bem_art_starten("radius"))
        m_einf.add_command(label=tr("menu.einfuegen.durchmesser"),
                           command=lambda: self._bem_art_starten("durchmesser"))
        m_einf.add_separator()
        m_einf.add_command(label=tr("menu.einfuegen.viewport"),
                           command=self.viewport_modus_starten)
        m_einf.add_command(label=tr("menu.einfuegen.rahmen"),
                           command=self.rahmen_einfuegen)
        m_einf.add_command(label=tr("menu.einfuegen.schriftkopf_speichern"),
                           command=self.schriftkopf_vorlage_speichern)
        m_einf.add_separator()
        m_einf.add_command(label=tr("menu.einfuegen.schraffur"),
                           command=self.schraffur_anwenden)
        menubar.add_cascade(label=tr("menu.einfuegen"), menu=m_einf)

        # View
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
        m_ansicht.add_command(label=tr("menu.ansicht.seitenleiste"),
                              command=self.seitenleiste_umschalten)
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

        # Blocks
        m_bloecke = tk.Menu(menubar, tearoff=0,
                            bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                            activebackground=FARBEN["cyan"],
                            activeforeground=FARBEN["bg_dunkel"])
        m_bloecke.add_command(label=tr("menu.einfuegen.block_einfuegen"),
                              command=self.block_einfuegen)
        m_bloecke.add_command(label=tr("menu.einfuegen.block_erzeugen"),
                              command=self.block_erzeugen)
        m_bloecke.add_command(label=tr("menu.einfuegen.block_liste"),
                              command=self.block_liste,
                              accelerator="Strg+B" if SPRACHE["aktuell"] == "de" else "Ctrl+B")
        m_bloecke.add_separator()
        m_bloecke.add_command(label=tr("menu.bloecke.attdef"),
                              command=self.attdef_erstellen)
        m_bloecke.add_command(label=tr("menu.bloecke.attedit"),
                              command=self.attribute_bearbeiten)
        m_bloecke.add_separator()
        m_bloecke.add_command(label=tr("menu.bloecke.speichern"),
                              command=self.block_speichern_datei)
        m_bloecke.add_separator()
        m_bloecke.add_command(label=tr("menu.einfuegen.block_aufloesen"),
                              command=self.block_aufloesen)
        menubar.add_cascade(label=tr("menu.bloecke"), menu=m_bloecke)

        # Electrical
        m_elektro = tk.Menu(menubar, tearoff=0,
                            bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                            activebackground=FARBEN["cyan"],
                            activeforeground=FARBEN["bg_dunkel"])
        m_elektro.add_command(label=tr("menu.elektro.vpunkt"),
                              command=lambda: self._werkzeug_setzen("vpunkt"))
        m_elektro.add_command(label=tr("menu.elektro.verbindung"),
                              command=lambda: self._werkzeug_setzen("verbindung"))
        m_elektro.add_command(label=tr("menu.elektro.querverweis"),
                              command=lambda: self._werkzeug_setzen("querverweis"))
        m_elektro.add_separator()
        m_elektro.add_command(label=tr("menu.elektro.maske"),
                              command=lambda: self._werkzeug_setzen("maske"))
        m_elektro.add_command(label=tr("menu.elektro.klemme"),
                              command=lambda: self._werkzeug_setzen("klemme"))
        m_elektro.add_command(label=tr("menu.elektro.kabel"),
                              command=lambda: self._werkzeug_setzen("kabel"))
        m_elektro.add_command(label=tr("menu.elektro.koordinatenfeld"),
                              command=lambda: self._werkzeug_setzen("koordinatenfeld"))
        m_elektro.add_separator()
        m_elektro.add_command(label=tr("menu.elektro.geraet_erzeugen"),
                              command=self.geraet_erzeugen)
        m_elektro.add_command(label=tr("menu.elektro.geraet_speichern"),
                              command=self.block_speichern_datei)
        m_elektro.add_command(label=tr("menu.elektro.geraet_laden"),
                              command=self.block_einfuegen)
        menubar.add_cascade(label=tr("menu.elektro"), menu=m_elektro)

        # Language
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

        # Help
        m_hilfe = tk.Menu(menubar, tearoff=0,
                          bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"],
                          activebackground=FARBEN["cyan"],
                          activeforeground=FARBEN["bg_dunkel"])
        m_hilfe.add_command(label=tr("menu.hilfe.felder"), command=self.schriftkopf_felder_pruefen)
        m_hilfe.add_command(label=tr("menu.hilfe.info"), command=self.zeige_info_fenster)
        if _MAC:        # app menu "About KatieCAD" -> our own info window
            for _name in ("tkAboutDialog", "::tk::mac::ShowAbout"):
                try:
                    self.root.createcommand(_name, self.zeige_info_fenster)
                except tk.TclError:
                    pass
        menubar.add_cascade(label=tr("menu.hilfe"), menu=m_hilfe)

        eintraege = [(menubar.entrycget(i, "label"), self.root.nametowidget(
                          menubar.entrycget(i, "menu")))
                     for i in range(menubar.index("end") + 1)
                     if menubar.type(i) == "cascade"]
        if self._eigene_menueleiste():
            # Linux/X11: own bar without grab (see menuleiste.py)
            if self._menuleiste is None:
                self._menuleiste = MenuLeiste(
                    self.root, FARBEN["bg_mittel"], FARBEN["cyan"],
                    FARBEN["cyan"], FARBEN["bg_dunkel"])
                erstes = (self.root.pack_slaves() or [None])[0]
                if erstes is not None:
                    self._menuleiste.pack(side=tk.TOP, fill=tk.X, before=erstes)
                else:
                    self._menuleiste.pack(side=tk.TOP, fill=tk.X)
            self._menuleiste.setze(eintraege)
        else:
            self.root.config(menu=menubar)
        if self._menubar is not None and self._menubar is not menubar:
            try:
                self._menubar.destroy()
            except tk.TclError:
                pass
        self._menubar = menubar
        self._menues_schliessen_binden()

    def _eigene_menueleiste(self):
        """Own menu bar only on X11 (Linux); Windows/macOS stay native."""
        if os.environ.get("KATIECAD_NATIVE_MENU"):
            return False
        try:
            return self.root.tk.call("tk", "windowingsystem") == "x11"
        except tk.TclError:
            return False

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
        ttk.Button(tb, text="\u2630", width=3,
                   command=self.seitenleiste_umschalten).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(tb, text=tr("tb.werkzeug"), style="Title.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        for key in ("auswahl", "linie", "polylinie", "kreis", "bogen",
                    "rechteck", "text", "bemassung",
                    "stutzen", "brechen"):
            ttk.Radiobutton(tb, text=tr(f"tb.wz.{key}"), value=key,
                            variable=self.aktives_werkzeug,
                            command=self._werkzeug_toolbar
                            ).pack(side=tk.LEFT)

        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Label(tb, text=tr("menu.elektro") + ":",
                  style="Title.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        for key in ("vpunkt", "verbindung", "querverweis",
                    "maske", "klemme", "kabel", "koordinatenfeld"):
            ttk.Radiobutton(tb, text=tr(f"tb.wz.{key}"), value=key,
                            variable=self.aktives_werkzeug,
                            command=self._werkzeug_toolbar
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
        self.farbe_btn = self._farb_swatch(tb2, self.zeichenfarbe,
                                           self.farbe_waehlen)
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
        self.bg_btn = self._farb_swatch(
            tb3, bg_aktuell,
            lambda: self.bg_waehlen("layout" if self._ist_layout() else "modell"))
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
    # Layout switcher (bottom)
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
            self._titelfelder_aktualisieren()
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
            b = FlatButton(bar, text=text + (f" [{key_hint}]" if key_hint else ""),
                           padx=10, pady=4, command=cmd,
                           font=(UI_SCHRIFT, 9, "bold"))
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
        self.fang_pfeil = FlatButton(
            bar, text="▾", padx=4, pady=4,
            font=(UI_SCHRIFT, 8, "bold"),
            bg=FARBEN["bg_hell"], fg=FARBEN["cyan"],
            activebackground=FARBEN["bg_hover"],
            activeforeground=FARBEN["text_hell"],
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
        self._werkzeug_toolbar()

    def _werkzeug_toolbar(self):
        """Tool selection by the user: "Selection" clears the selection."""
        if self.aktives_werkzeug.get() == "auswahl":
            self.auswahl = []
        self._werkzeug_gewechselt()

    def _bem_art_starten(self, art):
        """Activates the dimension tool with radius/diameter preselected."""
        if art not in ("radius", "durchmesser"):
            return
        self.bem_art.set(art)
        self.aktives_werkzeug.set("bemassung")
        self._werkzeug_gewechselt()
        de = SPRACHE["aktuell"] == "de"
        self.status.set(
            ("Radius-Bemaßung: Kreis/Bogen anklicken, dann Textposition."
             if de and art == "radius" else
             "Radius dimension: click circle/arc, then text position."
             if art == "radius" else
             "Durchmesser-Bemaßung: Kreis/Bogen anklicken, dann Textposition."
             if de else
             "Diameter dimension: click circle/arc, then text position."))

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
    # Viewport bar
    # --------------------------------------------------------
    def _build_viewport_leiste(self):
        self.viewport_leiste = ttk.Frame(self.root, padding=(6, 3))

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
        self._trim_abbrechen()
        self._break_abbrechen()
        self._warte_auf_blockpunkt = False
        self._block_einfuege_name = None
        self._block_erzeuge_auswahl = None
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
    _farb_swatch = staticmethod(farb_swatch)

    def _bind_events(self):
        c = self.canvas
        c.bind("<Button-1>", self.on_click)
        c.bind("<B1-Motion>", self.on_drag_b1)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Double-Button-1>", self.on_doppelklick)
        m, r = BTN_MITTE, BTN_RECHTS
        c.bind(f"<Double-Button-{m}>", self.zoom_grenzen)
        c.bind(f"<Double-Button-{r}>", self.zoom_grenzen)
        c.bind(f"<Button-{m}>", self.on_pan_start)
        c.bind(f"<B{m}-Motion>", self.on_pan)
        c.bind(f"<ButtonRelease-{m}>", self.on_pan_end)
        c.bind(f"<Button-{r}>", self.on_rechtsklick_start)
        c.bind(f"<B{r}-Motion>", self.on_pan)
        c.bind(f"<ButtonRelease-{r}>", self.on_rechtsklick_end)
        if _MAC:       # Ctrl+click = right click (trackpad / one-button mouse)
            c.bind("<Control-Button-1>", self.on_rechtsklick_start)
            c.bind("<Control-ButtonRelease-1>", self.on_rechtsklick_end)
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
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<F2>", lambda e: self.blatt_umbenennen())
        self.root.bind("<F4>", lambda e: self.seitenleiste_umschalten())
        self.root.bind("<Control-Y>", lambda e: self.redo())
        self.root.bind("<Control-Shift-Z>", lambda e: self.redo())
        self.root.bind("<Control-Shift-z>", lambda e: self.redo())
        self.root.bind("<Control-c>", self.kopieren)
        self.root.bind("<Control-C>", self.kopieren)
        self.root.bind("<Control-Shift-C>", self.kopieren_mit_basispunkt)
        self.root.bind("<Control-Shift-c>", self.kopieren_mit_basispunkt)
        self.root.bind("<Control-x>", self.ausschneiden)
        self.root.bind("<Control-X>", self.ausschneiden)
        self.root.bind("<Control-v>", self.einfuegen)
        self.root.bind("<Control-V>", self.einfuegen)
        self.root.bind("<Control-d>", self.duplizieren)
        self.root.bind("<Control-Key-1>", self.eigenschaften_fenster)
        self.root.bind("<Control-D>", self.duplizieren)
        self.root.bind("<Control-p>", lambda e: self.drucken())
        self.root.bind("<Control-P>", lambda e: self.drucken())
        self.root.bind("<Control-s>", lambda e: self.speichern())
        self.root.bind("<Control-S>", lambda e: self.speichern())
        self.root.bind("<Control-f>", lambda e: self.suchen_ersetzen())
        self.root.bind("<Control-F>", lambda e: self.suchen_ersetzen())
        self.root.bind("<Control-b>", lambda e: self.block_liste())
        self.root.bind("<Control-B>", lambda e: self.block_liste())
        self.root.bind("<g>", self.zoom_grenzen)
        self.root.bind("<G>", self.zoom_grenzen)
        self.entry_eingabe.bind("<Tab>", self._on_tab)

    def _on_tab(self, event):
        self.entry_eingabe.insert(tk.INSERT, "  ")
        return "break"

    def _escape(self, event=None):
        if self._paste_aktiv:
            self._paste_abbrechen()
        if self._attdef_wartend is not None:
            self._attdef_wartend = None
            self._update_eingabe_hinweis()
            self.status.set(tr("msg.attdef.abgebrochen"))
            return
        wz_e = self.aktives_werkzeug.get()
        if wz_e == "kabel" and getattr(self, "_kabel_p1", None) is not None:
            self._kabel_p1 = None
            self._clear_temp()
            self.status.set(tr("msg.kabel.start"))
            return
        if wz_e == "leitung" and self._leitung_p1 is not None:
            self._leitung_p1 = None
            self._clear_temp()
            if self._leitung_dialog is not None:
                self._leitung_dialog.setze(None, None)
            return
        if wz_e in ELEKTRO_WERKZEUGE:
            self.aktives_werkzeug.set("auswahl")
            self._werkzeug_gewechselt()
            return
        if self._warte_auf_blockpunkt:
            self._warte_auf_blockpunkt = False
            self._block_einfuege_name = None
            self._clear_temp()
            self._update_eingabe_hinweis()
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Einfügen abgebrochen." if de else "Paste cancelled.")
            self.redraw()
            return
        if self._block_erzeuge_auswahl is not None:
            self._block_erzeuge_auswahl = None
            self._clear_temp()
            self._update_eingabe_hinweis()
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Block-Erzeugen abgebrochen." if de
                            else "Block creation cancelled.")
            self.redraw()
            return
        if self._griff_drag_el is not None:
            self._griff_drag_el = None
            self._griff_drag_id = None
        self._schraffur_pick_ende()
        self._eigenschaften_ende()
        self._bem_abbrechen()
        self._bogen_abbrechen()
        self._trim_abbrechen()
        self._break_abbrechen()
        self._warte_auf_basispunkt = False
        # (the base point of the clipboard is kept on ESC)
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
        self._kabel_p1 = None
        self._leitung_beenden()
        self.letzter_punkt = None
        self.aktuelle_polylinie = []
        self._pts = []
        self._op = None
        self._cmd_pending = None
        self._vp_fenster = None
        self._viewport_modus = False
        self._trim_abbrechen()
        self._break_abbrechen()
        self._clear_temp()
        self._eingabe_zuruecksetzen()
        self._update_eingabe_hinweis()
        self._update_kontext_widgets()
        if self.aktives_werkzeug.get() != "auswahl":
            self.auswahl_leeren()
        wz = self.aktives_werkzeug.get()
        if wz == "stutzen":
            self._trim_status = "grenzen"
            self._trim_grenzen = []
            self._trim_anzahl = 0
        elif wz == "brechen":
            self._break_status = "objekt"
            self._break_el = None
            self._break_p1 = None
        self._update_eingabe_hinweis()
        de = SPRACHE["aktuell"] == "de"
        self.status.set(("Werkzeug: " if de else "Tool: ")
                        + self.aktives_werkzeug.get())
        wz = self.aktives_werkzeug.get()
        if wz in ELEKTRO_WERKZEUGE:
            if self._ist_layout():
                self.aktives_werkzeug.set("auswahl")
                self.status.set(tr("msg.modell_noetig"))
            elif wz == "leitung":
                self._leitung_starten()
            elif wz == "querverweis":
                self._querverweis_starten()
            elif wz == "verbindung":
                self._verbindung_starten()
            elif wz == "vpunkt":
                self._vp_starten()
            elif wz == "maske":
                self._maske_starten()
            elif wz == "klemme":
                self._klemme_starten()
            elif wz == "koordinatenfeld":
                self.status.set(tr("msg.kf.platzieren"))
            elif wz == "kabel":
                self._kabel_p1 = None
                self.status.set(tr("msg.kabel.start"))

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
        if self.raster_punktiert.get():
            # Every dot is a canvas item and is re-created on EVERY redraw
            # (zoom/pan). The limit prevents tens of thousands of items on
            # large screens (memory/CPU).
            while (w / step_px + 1) * (h / step_px + 1) > 6000:
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
        if self._attdef_wartend is not None:
            self._attdef_wartend = None
            self._update_eingabe_hinweis()
            self.status.set(tr("msg.attdef.abgebrochen"))
            return
        if self._paste_aktiv:
            self._paste_abbrechen()
            self.redraw()
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Einfügen abgebrochen." if de else "Paste cancelled.")
            return
        if self._warte_auf_blockpunkt:
            self._warte_auf_blockpunkt = False
            self._block_einfuege_name = None
            self._clear_temp()
            self.redraw()
            self._update_eingabe_hinweis()
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Einfügen abgebrochen." if de else "Paste cancelled.")
            return
        if self._cmd_pending is not None:
            self._cmd_pending = None
            self._update_eingabe_hinweis()
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Abgebrochen." if de else "Cancelled.")
            return
        if self.aktives_werkzeug.get() == "stutzen":
            if self._trim_status == "grenzen":
                self._trim_grenzen_bestaetigen()
            else:
                self._trim_abbrechen()
                self._werkzeug_gewechselt()
            return
        if self.aktives_werkzeug.get() == "brechen":
            self._break_abbrechen()
            self._werkzeug_gewechselt()
            return
        if getattr(self, "_hatch_pick", None):
            self._schraffur_pick_ende()
            return
        if getattr(self, "_prop_pick", None) is not None:
            self._eigenschaften_ende()
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
            self._push_undo(vorher)
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
    # Object snap
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
            if isinstance(el, Kabel):
                sammle(el.x, el.y, "endpunkt", 0)
                sammle(el.x + el.laenge, el.y, "endpunkt", 0)
                continue
            if isinstance(el, Koordinatenfeld):
                a, b, c2, d2 = el.umriss_rect()
                for (qx, qy) in ((a, b), (c2, b), (c2, d2), (a, d2)):
                    sammle(qx, qy, "endpunkt", 0)
                continue
            if isinstance(el, Verbindung):
                sammle(el.x, el.y, "endpunkt", 0)
                for ax, ay, _d in el.anschluesse():
                    sammle(ax, ay, "endpunkt", 0)
                continue
            if isinstance(el, Klemme):
                sammle(el.x, el.y, "endpunkt", 0)
                for ax, ay in (el.anschluss_oben(), el.anschluss_unten()):
                    sammle(ax, ay, "endpunkt", 0)
                continue
            if isinstance(el, ElektroMaske):
                sammle(el.x, el.y, "endpunkt", 0)
                continue
            if isinstance(el, (Verbindungspunkt, Querverweis)):
                sammle(el.x, el.y, "endpunkt", 0)     # Connection point / base
                if isinstance(el, Querverweis):
                    sx, sy = el.spitze_punkt()
                    sammle(sx, sy, "endpunkt", 0)     # Arrow tip
                continue
            if isinstance(el, BlockReferenz):
                kinder = el.aufgeloest()
                treffer = self._finde_snap_in_liste(kinder, mx, my, tol, ref)
                if treffer is not None:
                    sammle(treffer[0], treffer[1], treffer[2], 0)
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
                      fill=FARBEN["bg_dunkel"], font=(UI_SCHRIFT, 9, "bold"),
                      tags="snapmarker")
        c.create_text(px + 15, py - 17, text=label, anchor=tk.SW,
                      fill=FARBEN["gelb"], font=(UI_SCHRIFT, 9, "bold"),
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
        if self._attdef_wartend is not None:
            pt = self._eingabepunkt(event)
            self.status.set(
                f"{self._attdef_wartend['tag']}: X = {pt[0] / einh:.2f}  "
                f"Y = {pt[1] / einh:.2f}  |  " + tr("msg.attdef.platzieren"))
            self._fadenkreuz(event.x, event.y)
            return
        if self._warte_auf_blockpunkt:
            pt = self._eingabepunkt(event)
            self._block_vorschau(pt)
            de = SPRACHE["aktuell"] == "de"
            self.status.set(
                (f"Block-Einfügepunkt: X = {pt[0] / einh:.2f}  "
                 f"Y = {pt[1] / einh:.2f}  |  Klick = platzieren, "
                 "ESC = abbrechen" if de else
                 f"Block insertion point: X = {pt[0] / einh:.2f}  "
                 f"Y = {pt[1] / einh:.2f}  |  Click = place, ESC = cancel"))
            self._fadenkreuz(event.x, event.y)
            return
        if self._block_erzeuge_auswahl is not None:
            pt = self._eingabepunkt(event)
            de = SPRACHE["aktuell"] == "de"
            self.status.set(
                (f"Block-Basispunkt: X = {pt[0] / einh:.2f}  "
                 f"Y = {pt[1] / einh:.2f}  |  Klick = bestätigen, "
                 "ESC = abbrechen" if de else
                 f"Block base point: X = {pt[0] / einh:.2f}  "
                 f"Y = {pt[1] / einh:.2f}  |  Click = confirm, ESC = cancel"))
            self._fadenkreuz(event.x, event.y)
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
        wz_m = self.aktives_werkzeug.get()
        if wz_m == "leitung" and not self._ist_layout():
            self._leitung_vorschau(event)
            return
        if wz_m == "querverweis" and self._qv_vorgabe and not self._ist_layout():
            self._qv_vorschau(event)
            return
        if (wz_m in ("verbindung", "maske", "klemme", "koordinatenfeld", "kabel")
                and not self._ist_layout()):
            if self._geister_vorschau(event, wz_m):
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

    def _block_vorschau(self, pt):
        self._clear_temp()
        if not self._block_einfuege_name:
            return
        d = self.block_bibliothek.get(self._block_einfuege_name)
        if d is None:
            return
        ref = BlockReferenz(pt[0], pt[1], d.name, d.elemente,
                            layer=self._block_layer(d.elemente),
                            farbe=self.zeichenfarbe,
                            linientyp=self.linientyp.get(),
                            eig_farbe=self.eigene_farbe.get(),
                            staerke=self._zahl(self.linienstaerke, 0.35))
        stil = {"farbe": FARBEN["gruen"], "w": 2, "dash": (5, 3)}
        tf, sk = self._ctx_zu_px, self._ctx_skala()
        for kind in ref.aufgeloest():
            self._zeichne_element(kind, tags=("vorschau",), tf=tf,
                                  skala=sk, stil=stil)
        px, py = self._ctx_zu_px(pt[0], pt[1])
        self.canvas.create_oval(px - 5, py - 5, px + 5, py + 5,
                                outline=FARBEN["orange"], width=2,
                                tags="vorschau")
        self.canvas.create_line(px - 10, py, px + 10, py,
                                fill=FARBEN["orange"], tags="vorschau")
        self.canvas.create_line(px, py - 10, px, py + 10,
                                fill=FARBEN["orange"], tags="vorschau")

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
                                fill=FARBEN["gelb"], font=(UI_SCHRIFT, 9, "bold"),
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
        if isinstance(el, Koordinatenfeld):
            # hit only frame/outline, not the interior (drawing happens inside)
            for zug in el.auswahl_linien():
                for a, b in zip(zug, zug[1:]):
                    if abstand_punkt_segment(x_mm, y_mm, a[0], a[1],
                                             b[0], b[1]) <= tol:
                        return True
            return False
        if isinstance(el, ZUSAMMENGESETZT):
            for kind in el.aufgeloest():
                if self._punkt_auf_element(kind, x_mm, y_mm, tol):
                    return True
            return False
        if isinstance(el, Viewport):
            return (el.x <= x_mm <= el.x + el.breite and
                    el.y <= y_mm <= el.y + el.hoehe)
        if isinstance(el, Bild):
            return (el.x - tol <= x_mm <= el.x + el.breite + tol
                    and el.y - tol <= y_mm <= el.y + el.hoehe + tol)
        if isinstance(el, Schraffur):
            return punkt_in_gedrehtem_rechteck(x_mm, y_mm, (el.bbox()[0]+el.bbox()[2])/2, (el.bbox()[1]+el.bbox()[3])/2, el.bbox()[2]-el.bbox()[0], el.bbox()[3]-el.bbox()[1], 0.0)
        if isinstance(el, Verbindungspunkt):
            return el.trifft(x_mm, y_mm, tol)
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
        vorher = vollstaendige_verbindungen(liste)
        vorher_l = vollstaendige_leitungen(liste)
        for el in self.auswahl:
            if el in liste:
                liste.remove(el)
        n = len(self.auswahl)
        self.auswahl = []
        n_v, n_l = verbindungen_bereinigen(liste, vorher, vorher_l)
        self.redraw()
        de = SPRACHE["aktuell"] == "de"
        msg = (f"{n} Element(e) gelöscht." if de
               else f"{n} element(s) deleted.")
        if n_v or n_l:
            msg += "  " + tr("msg.elektro.bereinigt", n=n_v, l=n_l)
        self.status.set(msg)

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

        if x1_px >= x0_px:
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
            if getattr(el, "NUR_KLICK", False):
                continue                 # Coordinate field: click only
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
        if isinstance(el, Koordinatenfeld):
            x1, y1, x2, y2 = el.umriss_rect()
            p1 = self.mm_to_px(x1, y2)
            p2 = self.mm_to_px(x2, y1)
            c.create_rectangle(p1[0] - 2, p1[1] - 2, p2[0] + 2, p2[1] + 2,
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
        if self._attdef_wartend is not None:
            x, y = self._eingabepunkt(event)
            self._attdef_platzieren(x, y)
            return
        if self._warte_auf_blockpunkt:
            x, y = self._eingabepunkt(event)
            self._block_einfuegen_an(x, y)
            return
        if getattr(self, "_hatch_pick", None):
            self._schraffur_klick(event)
            return
        if getattr(self, "_prop_pick", None) is not None:
            self._eigenschaften_klick(event)
            return
        if self._block_erzeuge_auswahl is not None:
            x, y = self._eingabepunkt(event)
            self._block_erzeugen_fertig((x, y))
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
        if werkzeug == "leitung" and kind == "modell":
            x, y = self.px_to_mm(event.x, event.y)
            self._leitung_klick(x, y)
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
        elif werkzeug == "stutzen":
            self._trim_klick(pt)
        elif werkzeug == "brechen":
            self._break_klick(pt)
        elif werkzeug == "vpunkt":
            self._vp_platzieren(x_mm, y_mm)
        elif werkzeug == "querverweis":
            self._qv_platzieren(x_mm, y_mm)
        elif werkzeug == "leitung":
            self._leitung_klick(x_mm, y_mm)
        elif werkzeug == "verbindung":
            self._verbindung_platzieren(x_mm, y_mm)
        elif werkzeug == "maske":
            self._maske_platzieren(x_mm, y_mm)
        elif werkzeug == "klemme":
            self._klemme_platzieren(x_mm, y_mm)
        elif werkzeug == "koordinatenfeld":
            self._feld_platzieren(x_mm, y_mm)
        elif werkzeug == "kabel":
            self._kabel_klick(x_mm, y_mm)

    # --------------------------------------------------------
    # Trim (TRIM)
    # --------------------------------------------------------
    def _trim_grenzen_bestaetigen(self):
        de = SPRACHE["aktuell"] == "de"
        n = len(self._trim_grenzen)
        if n == 0:
            self._trim_grenzen = [el for el in self._aktuelle_elemente_liste()
                                  if self._element_sichtbar(el)]
            n = len(self._trim_grenzen)
            if n == 0:
                self.status.set(tr("msg.stutzen.keine_grenze"))
                self._trim_abbrechen()
                return
        self._trim_status = "ziele"
        self._trim_anzahl = 0
        self.status.set(tr("msg.stutzen.grenzen_gewaehlt", n=n))
        self._update_eingabe_hinweis()

    def _element_sichtbar(self, el):
        l = self.layers.get(el.layer)
        return (l is None) or l.sichtbar

    def _element_auf_punkt_snap(self, x_mm, y_mm, tol_mm):
        liste = self._aktuelle_elemente_liste()
        for el in reversed(liste):
            if not self._element_sichtbar(el):
                continue
            if isinstance(el, Viewport):
                continue
            if isinstance(el, (Text, Bemassung, Schraffur)):
                continue
            if self._punkt_auf_element(el, x_mm, y_mm, tol_mm):
                return el
        return None

    def _schnitte_mit_grenzen(self, el, grenzen, tol_mm):
        schnitte = []
        if el in grenzen:
            return schnitte
        ziel_segs = self._el_segmente(el)
        for g in grenzen:
            if g is el or not self._element_sichtbar(g):
                continue
            if isinstance(g, Viewport):
                continue
            grenz_segs = self._el_segmente(g)
            for (z_a, z_b) in ziel_segs:
                for (g_a, g_b) in grenz_segs:
                    sp = linien_schnitt(z_a[0], z_a[1], z_b[0], z_b[1],
                                        g_a[0], g_a[1], g_b[0], g_b[1])
                    if sp is not None:
                        schnitte.append(sp)
            if isinstance(el, (Kreis, Bogen)):
                for (g_a, g_b) in grenz_segs:
                    for (x1, y1, x2, y2) in ((g_a[0], g_a[1], g_b[0], g_b[1]),):
                        sps = self._segment_kreis_schnitt(
                            x1, y1, x2, y2, el.cx, el.cy, el.r)
                        for sp in sps:
                            if isinstance(el, Bogen):
                                w = math.degrees(math.atan2(sp[1] - el.cy,
                                                            sp[0] - el.cx))
                                if not winkel_im_bogen(w, el.start, el.ende):
                                    continue
                            schnitte.append(sp)
        eindeutig = []
        for (px, py) in schnitte:
            if not any(abs(px - qx) < 1e-6 and abs(py - qy) < 1e-6
                       for (qx, qy) in eindeutig):
                eindeutig.append((px, py))
        return eindeutig

    def _el_segmente(self, el):
        segs = []
        if isinstance(el, Linie):
            segs.append(((el.x1, el.y1), (el.x2, el.y2)))
        elif isinstance(el, Rechteck):
            pts = [(el.x1, el.y1), (el.x2, el.y1),
                   (el.x2, el.y2), (el.x1, el.y2)]
            for i in range(4):
                segs.append((pts[i], pts[(i + 1) % 4]))
        elif isinstance(el, Polylinie):
            pts = list(el.punkte)
            if el.geschlossen and len(pts) >= 3:
                pts.append(pts[0])
            for i in range(len(pts) - 1):
                segs.append((pts[i], pts[i + 1]))
        elif isinstance(el, (Kreis, Bogen)):
            skala = max(1.0, self.view["zoom"] * self._ctx_skala() * 0.1)
            sw = 360.0 if isinstance(el, Kreis) else bogen_sweep(el.start, el.ende)
            n = max(24, int(sw / 5))
            if isinstance(el, Kreis):
                pts = bogen_punkte(el.cx, el.cy, el.r, 0, 360, n)
            else:
                pts = bogen_punkte(el.cx, el.cy, el.r, el.start, el.ende, n)
            for i in range(len(pts) - 1):
                segs.append((pts[i], pts[i + 1]))
        return segs

    def _segment_kreis_schnitt(self, x1, y1, x2, y2, cx, cy, r):
        dx, dy = x2 - x1, y2 - y1
        fx, fy = x1 - cx, y1 - cy
        a = dx * dx + dy * dy
        if a < 1e-18:
            return []
        b = 2 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - r * r
        disk = b * b - 4 * a * c
        if disk < 0:
            return []
        sq = math.sqrt(disk)
        ergebnis = []
        for t in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)):
            if -1e-9 <= t <= 1 + 1e-9:
                ergebnis.append((x1 + t * dx, y1 + t * dy))
        return ergebnis

    def _trim_klick(self, pt):
        de = SPRACHE["aktuell"] == "de"
        if self._trim_status == "grenzen":
            tol_mm = 8 / self._ctx_skala()
            el = self._element_auf_punkt_snap(pt[0], pt[1], tol_mm)
            if el is None:
                self.status.set(tr("msg.stutzen.keine_grenze"))
                return
            if el in self._trim_grenzen:
                self._trim_grenzen.remove(el)
            else:
                self._trim_grenzen.append(el)
            self.status.set(tr("msg.stutzen.start"))
            self.redraw()
            return
        if self._trim_status == "ziele":
            tol_mm = 8 / self._ctx_skala()
            ziel = self._element_auf_punkt_snap(pt[0], pt[1], tol_mm)
            if ziel is None:
                return
            self._trim_anwenden(ziel, pt)
            return

    def _trim_anwenden(self, ziel, klick_pt):
        de = SPRACHE["aktuell"] == "de"
        schnitte = self._schnitte_mit_grenzen(ziel, self._trim_grenzen,
                                             1e-3)
        if not schnitte:
            return
        liste = self._aktuelle_elemente_liste()
        if ziel not in liste:
            return
        neue_el = []
        if isinstance(ziel, Linie):
            reste = trim_linie(ziel.x1, ziel.y1, ziel.x2, ziel.y2,
                               schnitte, klick_pt)
            if not reste:
                neue_el = []
            else:
                for (x1, y1, x2, y2) in reste:
                    nl = Linie(x1, y1, x2, y2, layer=ziel.layer,
                               farbe=ziel.farbe, linientyp=ziel.linientyp,
                               eig_farbe=ziel.eig_farbe, staerke=ziel.staerke)
                    neue_el.append(nl)
        elif isinstance(ziel, Rechteck):
            pts = [(ziel.x1, ziel.y1), (ziel.x2, ziel.y1),
                   (ziel.x2, ziel.y2), (ziel.x1, ziel.y2)]
            teile = trim_polylinie(pts, True, schnitte, klick_pt)
            for (teil_pts, geschlossen) in teile:
                if len(teil_pts) >= 2:
                    neue_el.append(Polylinie(teil_pts, geschlossen=geschlossen,
                                              layer=ziel.layer,
                                              farbe=ziel.farbe,
                                              linientyp=ziel.linientyp,
                                              eig_farbe=ziel.eig_farbe,
                                              staerke=ziel.staerke))
        elif isinstance(ziel, Polylinie):
            teile = trim_polylinie(list(ziel.punkte), ziel.geschlossen,
                                   schnitte, klick_pt)
            for (teil_pts, geschlossen) in teile:
                if len(teil_pts) >= 2:
                    neue_el.append(Polylinie(teil_pts, geschlossen=geschlossen,
                                              layer=ziel.layer,
                                              farbe=ziel.farbe,
                                              linientyp=ziel.linientyp,
                                              eig_farbe=ziel.eig_farbe,
                                              staerke=ziel.staerke))
        elif isinstance(ziel, Bogen):
            reste = trim_bogen(ziel.cx, ziel.cy, ziel.r, ziel.start, ziel.ende,
                               schnitte, klick_pt)
            for (s, e) in reste:
                if bogen_sweep(s, e) > 1e-6:
                    neue_el.append(Bogen(ziel.cx, ziel.cy, ziel.r, s, e,
                                         layer=ziel.layer, farbe=ziel.farbe,
                                         linientyp=ziel.linientyp,
                                         eig_farbe=ziel.eig_farbe,
                                         staerke=ziel.staerke))
        elif isinstance(ziel, Kreis):
            winkel = sorted(set(
                norm360(math.degrees(math.atan2(p[1] - ziel.cy, p[0] - ziel.cx)))
                for p in schnitte))
            if len(winkel) < 2:
                return
            kw = norm360(math.degrees(math.atan2(klick_pt[1] - ziel.cy,
                                                 klick_pt[0] - ziel.cx)))
            sortiert = sorted(winkel)
            links = None
            rechts = None
            for w in sortiert:
                if w <= kw:
                    links = w
                if w > kw and rechts is None:
                    rechts = w
            if links is None:
                links = sortiert[-1] - 360.0
            if rechts is None:
                rechts = sortiert[0] + 360.0
            s = norm360(rechts)
            e = norm360(links)
            if bogen_sweep(s, e) > 1e-6:
                neue_el.append(Bogen(ziel.cx, ziel.cy, ziel.r, s, e,
                                     layer=ziel.layer, farbe=ziel.farbe,
                                     linientyp=ziel.linientyp,
                                     eig_farbe=ziel.eig_farbe,
                                     staerke=ziel.staerke))
        else:
            return
        self._snapshot()
        liste.remove(ziel)
        for el in neue_el:
            liste.append(el)
        self._trim_anzahl += 1
        self.redraw()
        self.status.set(tr("msg.stutzen.fertig", n=self._trim_anzahl))

    # --------------------------------------------------------
    # Break (BREAK)
    # --------------------------------------------------------
    def _break_klick(self, pt):
        de = SPRACHE["aktuell"] == "de"
        if self._break_status == "objekt":
            tol_mm = 8 / self._ctx_skala()
            el = self._element_auf_punkt_snap(pt[0], pt[1], tol_mm)
            if el is None:
                return
            self._break_el = el
            self._break_status = "p1"
            self._break_p1 = pt
            self._break_status = "p2"
            self.status.set(tr("msg.brechen.punkt2"))
            self.redraw()
            return
        if self._break_status == "p1":
            self._break_p1 = pt
            self._break_status = "p2"
            self.status.set(tr("msg.brechen.punkt2"))
            return
        if self._break_status == "p2":
            self._break_anwenden(self._break_el, self._break_p1, pt)
            return

    def _break_anwenden(self, ziel, p1, p2):
        de = SPRACHE["aktuell"] == "de"
        liste = self._aktuelle_elemente_liste()
        if ziel not in liste:
            self._break_abbrechen()
            return
        neue_el = []
        if isinstance(ziel, Linie):
            dx, dy = ziel.x2 - ziel.x1, ziel.y2 - ziel.y1
            L = math.hypot(dx, dy)
            if L < 1e-9:
                return
            ux, uy = dx / L, dy / L
            t1 = ((p1[0] - ziel.x1) * ux + (p1[1] - ziel.y1) * uy)
            t2 = ((p2[0] - ziel.x1) * ux + (p2[1] - ziel.y1) * uy)
            if t1 > t2:
                t1, t2 = t2, t1
            t1 = max(0.0, min(L, t1))
            t2 = max(0.0, min(L, t2))
            if t1 > 1e-9:
                neue_el.append(Linie(ziel.x1, ziel.y1,
                                     ziel.x1 + ux * t1, ziel.y1 + uy * t1,
                                     layer=ziel.layer, farbe=ziel.farbe,
                                     linientyp=ziel.linientyp,
                                     eig_farbe=ziel.eig_farbe,
                                     staerke=ziel.staerke))
            if t2 < L - 1e-9:
                neue_el.append(Linie(ziel.x1 + ux * t2, ziel.y1 + uy * t2,
                                     ziel.x2, ziel.y2,
                                     layer=ziel.layer, farbe=ziel.farbe,
                                     linientyp=ziel.linientyp,
                                     eig_farbe=ziel.eig_farbe,
                                     staerke=ziel.staerke))
        elif isinstance(ziel, Rechteck):
            pts = [(ziel.x1, ziel.y1), (ziel.x2, ziel.y1),
                   (ziel.x2, ziel.y2), (ziel.x1, ziel.y2)]
            mitte = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            schnitte = [p1, p2]
            teile = trim_polylinie(pts, True, schnitte, mitte)
            for (teil_pts, geschlossen) in teile:
                if len(teil_pts) >= 2:
                    neue_el.append(Polylinie(teil_pts, geschlossen=geschlossen,
                                              layer=ziel.layer,
                                              farbe=ziel.farbe,
                                              linientyp=ziel.linientyp,
                                              eig_farbe=ziel.eig_farbe,
                                              staerke=ziel.staerke))
        elif isinstance(ziel, Polylinie):
            mitte = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            schnitte = [p1, p2]
            teile = trim_polylinie(list(ziel.punkte), ziel.geschlossen,
                                   schnitte, mitte)
            for (teil_pts, geschlossen) in teile:
                if len(teil_pts) >= 2:
                    neue_el.append(Polylinie(teil_pts, geschlossen=geschlossen,
                                              layer=ziel.layer,
                                              farbe=ziel.farbe,
                                              linientyp=ziel.linientyp,
                                              eig_farbe=ziel.eig_farbe,
                                              staerke=ziel.staerke))
        elif isinstance(ziel, Bogen):
            reste = trim_bogen(ziel.cx, ziel.cy, ziel.r, ziel.start, ziel.ende,
                               [p1, p2], ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2))
            for (s, e) in reste:
                if bogen_sweep(s, e) > 1e-6:
                    neue_el.append(Bogen(ziel.cx, ziel.cy, ziel.r, s, e,
                                         layer=ziel.layer, farbe=ziel.farbe,
                                         linientyp=ziel.linientyp,
                                         eig_farbe=ziel.eig_farbe,
                                         staerke=ziel.staerke))
        elif isinstance(ziel, Kreis):
            erg = kreis_zu_bogen(ziel.cx, ziel.cy, ziel.r, p1, p2)
            if erg is None:
                return
            cx, cy, r, s, e = erg
            if bogen_sweep(s, e) > 1e-6:
                neue_el.append(Bogen(cx, cy, r, s, e,
                                     layer=ziel.layer, farbe=ziel.farbe,
                                     linientyp=ziel.linientyp,
                                     eig_farbe=ziel.eig_farbe,
                                     staerke=ziel.staerke))
        else:
            return
        self._snapshot()
        liste.remove(ziel)
        for el in neue_el:
            liste.append(el)
        self._break_abbrechen()
        self.aktives_werkzeug.set("auswahl")
        self._werkzeug_gewechselt()
        self.redraw()
        self.status.set(tr("msg.brechen.fertig"))

    # --------------------------------------------------------
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
        if isinstance(el, BlockReferenz) and el.attribut_definitionen():
            self.attribute_bearbeiten(el)
            return
        if isinstance(el, Verbindungspunkt):
            self._vp_bearbeiten(el)
            return
        if isinstance(el, Querverweis):
            self._qv_bearbeiten(el)
            return
        if isinstance(el, Verbindung):
            self._verbindung_bearbeiten(el)
            return
        if isinstance(el, (ElektroMaske, Klemme)):
            self._fest_bearbeiten(el)
            return
        if isinstance(el, Koordinatenfeld):
            self._feld_bearbeiten(el)
            return
        if isinstance(el, Kabel):
            self._kabel_bearbeiten(el)
            return
        if isinstance(el, AttributDefinition):
            self._attdef_bearbeiten(el)
            return
        vorher = self._zustand()
        dlg = PropertiesDialog(self.root, self, el)
        if dlg.result:
            self._push_undo(vorher)
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
            treffer = self._elemente_im_auswahlrechteck(bbox, "rechts")
            nur = {id(e) for e in self._op.get("objekte") or []}
            self.auswahl = [e for e in treffer if not nur or id(e) in nur]
            self.redraw()
            self._op_hinweis()
            return
        if abs(x1_px - x0_px) < 4 and abs(y1_px - y0_px) < 4:
            # Additive selection: a click on empty space keeps the selection
            # (deselect only with ESC or via the "Selection" tool).
            pass
        else:
            bbox = (min(x0_mm, x1_mm), min(y0_mm, y1_mm),
                    max(x0_mm, x1_mm), max(y0_mm, y1_mm))
            richtung = "links" if x1_px >= x0_px else "rechts"
            treffer = self._elemente_im_auswahlrechteck(bbox, richtung)
            self._letztes_fenster = ((bbox, [id(t) for t in treffer])
                                     if richtung == "rechts" else None)
            for t in treffer:
                if t not in self.auswahl:
                    self.auswahl.append(t)
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

    def _leitungen_automatisch(self):
        """Wires appear/disappear on their own (like Eplan P8)."""
        if self._ist_layout():
            return
        neu, weg, entfernt = leitungen_automatisch(self.elemente)
        self._elektro_layer_pruefen()
        if entfernt and self.auswahl:
            ids = {id(e) for e in entfernt}
            self.auswahl = [e for e in self.auswahl if id(e) not in ids]

    def redraw(self):
        c = self.canvas
        self._bild_live = []                # keeps the PhotoImages of this frame
        try:
            self._leitungen_automatisch()
            if not self._ist_layout():
                kabel_kreuzungen(self.elemente)
        except Exception as ex:
            print(f"[KatieCAD] Leitungen: {ex}")
        try:
            self._querverweise_aktualisieren()
        except Exception as ex:
            print(f"[KatieCAD] Querverweise: {ex}")
        try:
            self._geraete_aktualisieren()
        except Exception as ex:
            print(f"[KatieCAD] Geraete: {ex}")
        try:
            self._titelfelder_aktualisieren()
        except Exception as ex:
            print(f"[KatieCAD] Schriftkopf: {ex}")
        for tag in ("element", "blatt", "layout", "auswahl_highlight",
                    "vp_griffe", "griffe"):
            c.delete(tag)
        self._clear_temp()
        if len(self._font_cache) > 40:
            # No canvas items exist any more (see delete above):
            # release font objects, otherwise they grow with every zoom level.
            self._font_cache.clear()
        if not self._ist_layout():
            for el in self.elemente:
                l = self.layers.get(el.layer)
                if l and not l.sichtbar:
                    continue
                self._zeichne_element(el)
            self._zeichne_auswahl_highlights()
            self._zeichne_raster()
            self._eig_palette_nachziehen()
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
        if isinstance(el, ZUSAMMENGESETZT):
            if isinstance(el, Koordinatenfeld):
                # dashed viewport outline only in the model view
                kinder = el.aufgeloest(umriss=(tf is None and tags == ("element",)
                                               and not self._ist_layout()))
            else:
                kinder = el.aufgeloest()
            for kind in kinder:
                self._zeichne_element(kind, tags=tags, tf=tf,
                                      skala=skala, clip=clip, stil=stil)
            return
        if isinstance(el, Verbindungspunkt):
            self._zeichne_vp(el, tags, tf, skala, clip, stil)
            return
            
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

        if isinstance(el, Bild):
            self._zeichne_bild(el, tf, farbe, tags, clip)
            return

        if isinstance(el, Schraffur):
            c = self.canvas
            pts_px = [tf(x, y) for (x, y) in el.punkte]
            flat = [v for q in pts_px for v in q]
            
            if el.muster == "solid":
                c.create_polygon(*flat, fill=farbe, outline="", tags=tags)
            else:
                for (p1, p2) in el.geometrie_linien():
                    x1, y1 = tf(p1[0], p1[1])
                    x2, y2 = tf(p2[0], p2[1])
                    c.create_line(x1, y1, x2, y2, fill=farbe, width=1, tags=tags)
            return

        self._zeichne_prims(self._prims(el, sk), farbe, w, dash, tf, sk, tags, clip)

    def _bild_pil(self, el):
        """Decoded PIL image of a Bild element (small cache)."""
        from katiecad.fileio.bild_import import pil_bild
        cache = self.__dict__.setdefault("_bild_pil_cache", {})
        key = (len(el.daten), el.daten[:64], el.daten[-64:])
        if key not in cache:
            if len(cache) >= 6:
                cache.pop(next(iter(cache)))
            cache[key] = pil_bild(el.daten)
        return cache[key]

    def _zeichne_bild(self, el, tf, farbe, tags, clip):
        """Frame + the visible part of the image (cropped and scaled)."""
        c = self.canvas
        xa, ya = tf(el.x, el.y + el.hoehe)          # upper left (screen)
        xb, yb = tf(el.x + el.breite, el.y)         # lower right (screen)
        if xb < xa:
            xa, xb = xb, xa
        if yb < ya:
            ya, yb = yb, ya
        c.create_rectangle(xa, ya, xb, yb, outline=farbe, tags=tags)
        w, h = xb - xa, yb - ya
        if w < 2 or h < 2 or not el.daten:
            return
        xmin, ymin, xmax, ymax = clip
        vx1, vy1 = max(xa, xmin), max(ya, ymin)
        vx2, vy2 = min(xb, xmax), min(yb, ymax)
        if vx2 - vx1 < 1 or vy2 - vy1 < 1:
            return
        zw, zh = int(round(vx2 - vx1)), int(round(vy2 - vy1))
        if zw > 4000 or zh > 4000:
            return
        try:
            import base64, io
            from PIL import Image
            cache = self.__dict__.setdefault("_bild_tk_cache", {})
            box = (int(round((vx1 - xa) / w * el.pw)), int(round((vy1 - ya) / h * el.ph)),
                   int(round((vx2 - xa) / w * el.pw)), int(round((vy2 - ya) / h * el.ph)))
            key = (len(el.daten), el.daten[:48], box, zw, zh)
            ph = cache.get(key)
            if ph is None:
                im = self._bild_pil(el)
                box = (max(0, box[0]), max(0, box[1]),
                       min(el.pw, max(box[0] + 1, box[2])), min(el.ph, max(box[1] + 1, box[3])))
                teil = im.crop(box).resize((zw, zh), Image.BILINEAR)
                buf = io.BytesIO()
                teil.save(buf, "PNG")
                ph = tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
                if len(cache) >= 24:
                    cache.pop(next(iter(cache)))
                cache[key] = ph
            self._bild_live = getattr(self, "_bild_live", [])
            self._bild_live.append(ph)
            c.create_image(vx1, vy1, anchor="nw", image=ph, tags=tags)
            c.tag_lower(c.create_rectangle(xa, ya, xb, yb, outline="", tags=tags))
        except Exception as ex:
            print(f"[KatieCAD] Bild: {ex}")

    def _bild_zu_dxf(self, msp, el, attribs):
        """IMAGE entity: the picture is written next to the DXF file."""
        import base64
        ziel = getattr(self, "_export_ziel", None)
        if not ziel:
            msp.add_lwpolyline(el.rahmen(), close=True, dxfattribs=attribs)
            return
        self._dxf_bild_nr = getattr(self, "_dxf_bild_nr", 0) + 1
        basis = os.path.splitext(os.path.basename(ziel))[0]
        name = f"{basis}_bild{self._dxf_bild_nr}." + ("jpg" if el.format == "jpeg" else "png")
        pfad = os.path.join(os.path.dirname(os.path.abspath(ziel)), name)
        with open(pfad, "wb") as f:
            f.write(base64.b64decode(el.daten))
        d = msp.doc.add_image_def(filename=name, size_in_pixel=(el.pw, el.ph))
        msp.add_image(d, insert=(el.x, el.y), size_in_units=(el.breite, el.hoehe),
                      rotation=0, dxfattribs=attribs)

    def import_bild(self):
        """Inserts a raster image (PNG, JPG, ...) as a scalable element."""
        de = SPRACHE["aktuell"] == "de"
        titel = "Bild" if de else "Image"
        try:
            from katiecad.fileio import bild_import
        except Exception as ex:
            messagebox.showwarning(titel, str(ex))
            return
        if not bild_import.PIL_OK:
            messagebox.showwarning(titel, "Pillow nicht installiert:  pip install Pillow"
                                   if de else "Pillow is not installed:  pip install Pillow")
            return
        if self._ist_layout():
            self.status.set("Bitte in die Modell-Ansicht wechseln." if de
                            else "Please switch to model view.")
            return
        pfad = filedialog.askopenfilename(
            filetypes=[(("Bilder" if de else "Images"), bild_import.ENDUNGEN),
                       (("Alle Dateien" if de else "All files"), "*.*")])
        if not pfad:
            return
        try:
            b = bild_import.lade_bild(pfad)
        except RuntimeError as ex:
            messagebox.showerror(titel, str(ex))
            return
        breite = simpledialog.askfloat(
            titel, ("Breite des Bildes in mm (die Höhe folgt dem Seitenverhältnis):" if de
                    else "Width of the image in mm (height follows the aspect ratio):"),
            initialvalue=100.0, minvalue=0.1, maxvalue=100000.0, parent=self.root)
        if breite is None:
            return
        hoehe = breite * b["ph"] / float(b["pw"])
        cx, cy = self.px_to_mm(self.canvas.winfo_width() / 2.0,
                               self.canvas.winfo_height() / 2.0)
        daten = self._layer_daten()
        daten["eig_farbe"] = False
        daten["staerke"] = None
        self._snapshot()
        el = Bild(cx - breite / 2, cy - hoehe / 2, breite, hoehe, b["daten"],
                  b["format"], b["pw"], b["ph"], **daten)
        self._ziel_liste().append(el)
        self.auswahl = [el]
        self.redraw()
        self.status.set((f"Bild eingefügt ({b['pw']} x {b['ph']} Pixel). Größe: gelbe Ecke ziehen "
                         f"oder Skalieren-Befehl." if de else
                         f"Image inserted ({b['pw']} x {b['ph']} px). Resize: drag the yellow "
                         f"corner or use Scale."))

    def _zeichne_vp(self, el, tags, tf, skala, clip, stil):
        """Connection point: circle only in the model, label everywhere."""
        tf = tf or self.mm_to_px
        sk = skala if skala is not None else self.view["zoom"]
        if not self._ist_layout():
            farbe = stil["farbe"] if stil else self._effektive_zeichenfarbe(el)
            cx, cy = tf(el.x, el.y)
            r = max(3.0, el.radius * sk)
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    outline=farbe, width=2, tags=tags)
        t = el.text_element()
        if t is not None:
            self._zeichne_element(t, tags=tags, tf=tf, skala=skala,
                                  clip=clip, stil=stil)

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

    def _attr_ausschluss(self, ref):
        """Tags that are not prompted for (title block: automatic fields)."""
        if not TB.is_title_block(ref):
            return ()
        return {ad.tag for ad in ref.attribut_definitionen()
                if TB.is_auto_tag(ad.tag)}

    def _titelfelder_aktualisieren(self):
        """Automatic title block fields (page, date, ...) of all layouts."""
        layouts = getattr(self, "layouts", None) or []
        if not any(TB.is_title_block(e) for lay in layouts for e in lay.elemente):
            return
        p = self.projekt
        idx = p.aktiv if p is not None else 0
        for lay in layouts:
            info = TB.make_info(p, idx, SPRACHE["aktuell"], lay.format)
            TB.refresh_fields(lay.elemente, info, self.massstab.get())

    @staticmethod
    def _ordner_oeffnen(pfad):
        try:
            os.makedirs(pfad, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(pfad)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", pfad])
            else:
                subprocess.Popen(["xdg-open", pfad])
        except Exception as e:
            print(f"[KatieCAD] Ordner konnte nicht geoeffnet werden: {e}")

    def rahmen_einfuegen(self):
        """Sheet margin (left 20 mm, otherwise 5 mm) and title block from a
        template drawing (folder title_blocks). An existing title block
        is replaced."""
        if not self._ist_layout():
            self.status.set(tr("msg.tb.nur_layout"))
            return
        p = self.projekt
        ordner = TB.template_folders(p.ordner if p is not None else None)
        eintraege = [(tr("dlg.tb.ohne"), None)]
        eintraege += [(n, pf) for n, pf in TB.list_templates(ordner)]
        cfg = lade_konfiguration()
        dlg = TitleBlockDialog(
            self.root, eintraege, preselect=cfg.get("title_block"),
            on_open_folder=lambda: self._ordner_oeffnen(ordner[0]),
            folders_text=tr("dlg.tb.ordner_zeile", pfad=ordner[0]))
        if dlg.result is None:
            return
        wahl = dlg.result                       # "" = frame only
        elemente, name = [], ""
        if wahl and wahl != "builtin":
            try:
                elemente = TB.load_template(wahl, self._dict_zu_element)
            except (OSError, ValueError) as e:
                messagebox.showerror(tr("dlg.tb.titel"),
                                     tr("msg.tb.fehler", fehler=e),
                                     parent=self.root)
                return
            name = os.path.splitext(os.path.basename(wahl))[0]
        try:
            cfg["title_block"] = wahl
            speichere_konfiguration(cfg)
        except Exception:
            pass

        self._snapshot()
        b, h = ZEICHNUNGSFORMATE[self.layout_format]
        liste = self.layout_elemente

        def gleich(el, r):
            return (isinstance(el, Rechteck) and
                    all(abs(a - c) < 1e-6 for a, c in
                        zip((el.x1, el.y1, el.x2, el.y2), r)))
        aussen, innen = TB.frame_rects(b, h)
        alte = [r for r in TB.old_frame_rects(b, h) if r != innen]
        liste[:] = [e for e in liste
                    if not TB.is_title_block(e)
                    and not any(gleich(e, r) for r in alte)]
        basis = {"layer": "0", "farbe": FARBEN["cyan"],
                 "linientyp": "Volllinie (breit)", "eig_farbe": True, "staerke": 0.7}
        basis2 = {"layer": "0", "farbe": FARBEN["cyan"],
                  "linientyp": "Volllinie (schmal)", "eig_farbe": True, "staerke": 0.35}
        if not any(gleich(e, aussen) for e in liste):
            liste.append(Rechteck(*aussen, **basis))
        if not any(gleich(e, innen) for e in liste):
            liste.append(Rechteck(*innen, **basis2))
        if elemente:
            ref = TB.make_block(name, elemente, b, h, layer="0")
            info = TB.make_info(p, p.aktiv if p is not None else 0,
                                SPRACHE["aktuell"], self.layout_format)
            TB.refresh_fields(liste + [ref], info, self.massstab.get())
            self._attribute_abfragen(ref)
            liste.append(ref)
            self.auswahl = [ref]
            self.status.set(tr("msg.tb.eingefuegt", name=name))
        else:
            self.status.set(tr("msg.tb.nur_rahmen"))
        self.redraw()

    def schriftkopf_vorlage_speichern(self):
        """Saves the model drawing as a title block template."""
        if not self.elemente:
            self.status.set(tr("msg.tb.leer"))
            return
        ordner = TB.program_folder()
        try:
            os.makedirs(ordner, exist_ok=True)
        except OSError:
            pass
        pfad = filedialog.asksaveasfilename(
            parent=self.root, initialdir=ordner, defaultextension=".cadjson",
            filetypes=[("CAD file", "*.cadjson")],
            title=tr("menu.einfuegen.schriftkopf_speichern"))
        if not pfad:
            return
        try:
            self._json_atomar_schreiben(pfad, TB.template_data(self.elemente))
        except OSError as e:
            messagebox.showerror(tr("msg.speichern_fehlgeschlagen"), str(e),
                                 parent=self.root)
            return
        self.status.set(tr("msg.tb.gespeichert", pfad=pfad))

    # --------------------------------------------------------
    # Show/hide sidebar
    # --------------------------------------------------------
    def seitenleiste_umschalten(self):
        sl = self.seitenleiste
        if sl.ist_sichtbar():
            sl.ausblenden()
        else:
            sl.einblenden(vor=self.canvas)
        try:
            cfg = lade_konfiguration()
            cfg["sidebar_sichtbar"] = sl.ist_sichtbar()
            speichere_konfiguration(cfg)
        except Exception as e:
            print(f"[KatieCAD] Konfiguration: {e}")

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
    # Info window
    # --------------------------------------------------------
    def zeige_info_fenster(self):
        alt = getattr(self, "_info_fenster", None)
        try:
            if alt is not None and alt.winfo_exists():     # only one at a time
                alt.deiconify()
                alt.lift()
                alt.focus_force()
                return
        except tk.TclError:
            pass
        info_win = tk.Toplevel(self.root)
        self._info_fenster = info_win
        info_win.title(tr("info.titel") + " - KatieCAD")
        info_win.transient(self.root)
        info_win.configure(bg=FARBEN["bg_mittel"])
        info_win.resizable(False, False)

        aussen = tk.Frame(info_win, bg=FARBEN["bg_mittel"])
        aussen.pack(fill=tk.BOTH, expand=True)
        self._info_maskottchen(aussen)
        frame = tk.Frame(aussen, bg=FARBEN["bg_mittel"], padx=22, pady=16)
        frame.pack(side="left", fill=tk.BOTH, expand=True)

        title_row = tk.Frame(frame, bg=FARBEN["bg_mittel"])
        title_row.pack(anchor="w", fill="x")

        logo_path = _symbol_datei("KatieCAD.png")
        if logo_path is None:
            for k in ("KatieCAD.png", os.path.join(os.getcwd(), "KatieCAD.png")):
                if os.path.isfile(k):
                    logo_path = os.path.abspath(k)
                    break
        if logo_path is not None:
            logo_photo = None
            if PILLOW_VERFUEGBAR:
                try:
                    logo_img = Image.open(logo_path).convert("RGBA")
                    logo_img = logo_img.resize((72, 72), Image.Resampling.LANCZOS)
                    logo_photo = ImageTk.PhotoImage(logo_img)
                except Exception as e:
                    print(f"[KatieCAD] Logo (Pillow): {e}")
            if logo_photo is None:           # without Pillow/ImageTk: plain Tk
                try:
                    p = tk.PhotoImage(file=logo_path)
                    n = max(1, round(p.width() / 72))
                    logo_photo = p.subsample(n, n) if n > 1 else p
                except tk.TclError as e:
                    print(f"[KatieCAD] Logo konnte nicht geladen werden: {e}")
            if logo_photo is not None:
                logo_lbl = tk.Label(title_row, image=logo_photo,
                                    bg=FARBEN["bg_mittel"], bd=0,
                                    highlightthickness=0)
                logo_lbl.image = logo_photo
                logo_lbl.pack(side="left", padx=(0, 16))

        tk.Label(title_row, text="KatieCAD",
                 font=("Helvetica", 18, "bold"),
                 bg=FARBEN["bg_mittel"], fg=FARBEN["cyan"]).pack(side="left", anchor="w")

        tk.Frame(frame, bg=FARBEN["rand"], height=1).pack(fill="x", pady=(12, 8))

        tk.Label(frame, text=tr("info.untertitel"),
                 font=("Helvetica", 10, "italic"),
                 wraplength=440, justify="left",
                 bg=FARBEN["bg_mittel"], fg=FARBEN["text"]).pack(anchor="w", pady=(0, 6))

        tk.Frame(frame, bg=FARBEN["rand"], height=1).pack(fill="x", pady=8)

        tk.Label(frame, text=tr("info.gebaut_mit"),
                 font=("Helvetica", 9),
                 bg=FARBEN["bg_mittel"], fg=FARBEN["text"]).pack(anchor="w", pady=(0, 8))

        tk.Label(frame, text=tr("info.version"),
                 font=("Helvetica", 9),
                 bg=FARBEN["bg_mittel"], fg=FARBEN["text_dim"]).pack(anchor="w", pady=(0, 6))

        tk.Label(frame, text=tr("info.copyright"),
                 font=("Helvetica", 9),
                 bg=FARBEN["bg_mittel"], fg=FARBEN["text_dim"]).pack(anchor="w", pady=(0, 6))

        tk.Label(frame, text=tr("info.lizenz"),
                 font=("Helvetica", 9),
                 bg=FARBEN["bg_mittel"], fg=FARBEN["text_dim"]).pack(anchor="w", pady=(0, 6))

        btn_row = tk.Frame(frame, bg=FARBEN["bg_mittel"])
        btn_row.pack(fill="x", side="bottom", pady=(12, 0))

        def make_btn(text, cmd):
            b = ttk.Button(btn_row, text=text, command=cmd)
            return b

        make_btn(tr("info.btn_lizenz"), lambda: zeige_lizenz_fenster(info_win)).pack(side="left", padx=4)
        make_btn(tr("info.btn_log"), self.log_oeffnen).pack(side="left", padx=4)
        make_btn(tr("dlg.schliessen"), info_win.destroy).pack(side="right", padx=4)

        info_win.update_idletasks()
        info_win.minsize(info_win.winfo_reqwidth(), info_win.winfo_reqheight())
        mx = self.root.winfo_rootx() + self.root.winfo_width() // 2
        my = self.root.winfo_rooty() + self.root.winfo_height() // 2
        w = info_win.winfo_width()
        h = info_win.winfo_height()
        info_win.geometry(f"+{mx - w // 2}+{my - h // 2}")

    def _info_maskottchen(self, eltern, hoehe=300):
        """Mascot picture on the left of the About window (optional file
        KatieCAD_Maskottchen.png next to KatieCAD.png)."""
        pfad = _symbol_datei("KatieCAD_Maskottchen.png")
        if pfad is None:
            return
        bild = None
        if PILLOW_VERFUEGBAR:
            try:
                img = Image.open(pfad).convert("RGBA")
                b = max(1, round(img.width * hoehe / img.height))
                bild = ImageTk.PhotoImage(
                    img.resize((b, hoehe), Image.Resampling.LANCZOS))
            except Exception as e:
                print(f"[KatieCAD] Maskottchen (Pillow): {e}")
        if bild is None:
            try:
                p = tk.PhotoImage(file=pfad)
                n = max(1, round(p.height() / hoehe))
                bild = p.subsample(n, n) if n > 1 else p
            except tk.TclError as e:
                print(f"[KatieCAD] Maskottchen konnte nicht geladen werden: {e}")
                return
        lbl = tk.Label(eltern, image=bild, bg=FARBEN["bg_mittel"], bd=0,
                       highlightthickness=0)
        lbl.image = bild
        lbl.pack(side="left", padx=(14, 0), pady=10, anchor="s")

    def log_oeffnen(self):
        """Opens the program log in the system's text editor."""
        from katiecad.common import logbuch
        de = SPRACHE["aktuell"] == "de"
        pf = logbuch.pfad()
        if not pf or not os.path.exists(pf):
            messagebox.showinfo("Log", ("Es gibt noch keine Log-Datei." if de
                                        else "There is no log file yet."),
                                parent=self.root)
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(pf)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-t", pf], check=True)
            else:
                subprocess.run(["xdg-open", pf], check=True)
        except Exception as ex:
            messagebox.showwarning(
                "Log", (f"Die Log-Datei konnte nicht geöffnet werden ({ex}).\n"
                        f"Sie liegt hier:\n{pf}" if de else
                        f"The log file could not be opened ({ex}).\n"
                        f"It is located here:\n{pf}"), parent=self.root)

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
        self._trim_abbrechen()
        self._break_abbrechen()
        self._warte_auf_blockpunkt = False
        self._block_einfuege_name = None
        self._block_erzeuge_auswahl = None
        self._attdef_wartend = None
        self._undo_reset()
        self._layout_switcher_neu_aufbauen()
        self._update_kontext_widgets()
        bg = self.bg_modell
        self.canvas.config(bg=bg)
        self.bg_btn.config(bg=bg)
        self._mark_clean()
        if self.projekt is not None:
            self._mark_dirty()   # Sheet file must be rewritten
        self.redraw()
        self._zeichne_raster()
        self._viewport_modus_anzeige_aktualisieren()

    def speichern(self):
        if self.projekt is not None:
            return self.projekt_speichern()
        de = SPRACHE["aktuell"] == "de"
        pfad = filedialog.asksaveasfilename(
            defaultextension=".cadjson",
            filetypes=[("CAD-Datei" if de else "CAD file", "*.cadjson"),
                       ("Alle Dateien" if de else "All files", "*.*")])
        if not pfad:
            return False
        daten = self._zeichnung_daten()
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
        if self.projekt is not None and not messagebox.askyesno(
                tr("msg.projekt.titel"), tr("msg.projekt.einzeldatei"),
                parent=self.root):
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
        self._projekt_fuer_einzeldatei_schliessen()
        self._zeichnung_anwenden(daten)
        self._undo_reset()
        self.status.set((f"Geöffnet: {pfad}" if de else f"Opened: {pfad}"))

    def _dict_zu_element(self, d):
        d = dict(d)
        typ = d.pop("typ")
        if typ in ("solid", "linien"):      # Legacy format: hatching whose
            d["muster"] = typ               # element type was overwritten
            typ = "schraffur"
        if typ == "viewport":
            if "zoom" not in d and "massstab" in d:
                d["zoom"] = d.pop("massstab")
            d.pop("aktiv", None)
        if "staerke" not in d:
            d["staerke"] = None
        for _k in ("refs", "kontakte", "sym_bbox", "kreuzungen", "ziel"):
            d.pop(_k, None)             # computed values, also from files of 1.0.1
        try:
            if typ == "linie":      return Linie(**d)
            if typ == "kreis":      return Kreis(**d)
            if typ == "bogen":      return Bogen(**d)
            if typ == "rechteck":   return Rechteck(**d)
            if typ == "polylinie":  return Polylinie(**d)
            if typ == "text":       return Text(**d)
            if typ == "bemassung":  return Bemassung(**d)
            if typ == "viewport":   return Viewport(**d)
            if typ == "schraffur":  return Schraffur(**d)
            if typ == "bild":       return Bild(**d)
            if typ == "attdef":     return AttributDefinition(**d)
            if typ == "vpunkt":     return Verbindungspunkt(**d)
            if typ == "leitung":    return Leitung(**d)
            if typ == "querverweis": return Querverweis(**d)
            if typ == "verbindung": return Verbindung(**d)
            if typ == "maske":      return ElektroMaske(**d)
            if typ == "klemme":     return Klemme(**d)
            if typ == "koordinatenfeld": return Koordinatenfeld(**d)
            if typ == "kabel":      return Kabel(**d)
            if typ == "block":
                kinder_dicts = d.pop("elemente", [])
                kinder = []
                for kd in kinder_dicts:
                    kind = self._dict_zu_element(kd)
                    if kind is not None:
                        kinder.append(kind)
                return BlockReferenz(elemente=kinder, **d)
        except Exception as e:
            print(f"Fehler beim Laden: {e} - {d}")
        return None

    def _dxf_dokument(self):
        """Builds an ezdxf document from the current drawing."""
        doc = ezdxf.new(dxfversion="R2010")
        for name, l in self.layers.items():
            if name not in doc.layers:
                doc.layers.add(name, color=self._hex_zu_aci(l.farbe))
        msp = doc.modelspace()
        for el in self.elemente:
            self._element_zu_dxf(msp, el)
        return doc

    def export_dxf(self):
        self._export_cad("dxf")

    def export_dwg(self):
        self._export_cad("dwg")

    def _export_cad(self, art):
        de = SPRACHE["aktuell"] == "de"
        titel = art.upper()
        if not EZDXF_VERFUEGBAR:
            messagebox.showwarning(titel,
                ("ezdxf nicht installiert." if de else "ezdxf is not installed."))
            return
        pfad = filedialog.asksaveasfilename(
            defaultextension="." + art,
            filetypes=[((titel + "-Datei") if de else (titel + " file"), "*." + art),
                       ("Alle Dateien" if de else "All files", "*.*")])
        if not pfad:
            return
        try:
            self._export_ziel = pfad            # images are written next to it
            doc = self._dxf_dokument()
            if art == "dwg":
                from katiecad.fileio.cad_import import dxf_doc_als_dwg_speichern
                dxf_doc_als_dwg_speichern(doc, pfad)
            else:
                doc.saveas(pfad)
            self.status.set((f"{titel} exportiert: {pfad}" if de
                             else f"{titel} exported: {pfad}"))
        except Exception as e:
            messagebox.showerror(titel,
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
            elif isinstance(el, ZUSAMMENGESETZT):
                for kind in el.aufgeloest():
                    self._element_zu_dxf(msp, kind)
            elif isinstance(el, Verbindungspunkt):
                t_vp = el.text_element()
                if t_vp is not None:
                    self._element_zu_dxf(msp, t_vp)
            elif isinstance(el, Bild):
                self._bild_zu_dxf(msp, el, attribs)
            elif isinstance(el, Schraffur):
                if el.muster == "solid":
                    h = msp.add_hatch(dxfattribs=attribs)
                    h.set_solid_fill()
                    h.paths.add_polyline_path(list(el.punkte), is_closed=True)
                else:
                    for (p1, p2) in el.geometrie_linien():
                        msp.add_line(p1, p2, dxfattribs=attribs)
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

    def _cad_import(self, art):
        """Common import for DXF and DWG (art = 'dxf' | 'dwg')."""
        de = SPRACHE["aktuell"] == "de"
        titel = art.upper()
        if not CADIMPORT_VERFUEGBAR or not EZDXF_VERFUEGBAR:
            messagebox.showwarning(titel,
                ("ezdxf nicht installiert:  pip install ezdxf" if de
                 else "ezdxf is not installed:  pip install ezdxf"))
            return
        pfad = filedialog.askopenfilename(
            filetypes=[("DXF / DWG", "*.dxf *.dwg"),
                       (("DXF-Datei" if de else "DXF file"), "*.dxf"),
                       (("DWG-Datei" if de else "DWG file"), "*.dwg"),
                       (("Alle Dateien" if de else "All files"), "*.*")])
        if not pfad:
            return
        try:
            self.root.config(cursor="watch")
            self.root.update_idletasks()
        except Exception:
            pass
        try:
            erg = cadimport.importiere_datei(pfad, self.layers)
            if not erg.elemente:
                messagebox.showwarning(titel,
                    ("Es konnten keine Elemente importiert werden.\n"
                     if de else "No elements could be imported.\n") +
                    self._import_bericht(erg, de))
                return
            self._snapshot()
            self.elemente.extend(erg.elemente)
            self.layer_cb.config(values=list(self.layers.keys()))
            self.zoom_grenzen()
            msg = (f"{titel} importiert ({len(erg.elemente)} Elemente): {pfad}"
                   if de else
                   f"{titel} imported ({len(erg.elemente)} elements): {pfad}")
            self.status.set(msg)
            if erg.uebersprungen or erg.fehler or erg.hinweise:
                messagebox.showinfo(titel, msg + "\n\n" +
                                    self._import_bericht(erg, de))
        except Exception as e:
            messagebox.showerror(titel,
                (f"Fehler beim Import:\n{e}" if de else f"Import error:\n{e}"))
        finally:
            try:
                self.root.config(cursor="")
            except Exception:
                pass

    @staticmethod
    def _import_bericht(erg, de):
        z = []
        if erg.quelle:
            z.append(("Quelle: " if de else "Source: ") + erg.quelle)
        if erg.faktor != 1.0:
            z.append((f"Einheiten automatisch nach mm umgerechnet (x{erg.faktor:g})"
                      if de else f"Units converted to mm (x{erg.faktor:g})"))
        if erg.uebersprungen:
            z.append(("Nicht unterstützt (übersprungen): " if de
                      else "Unsupported (skipped): ") +
                     ", ".join(f"{k} x{v}" for k, v in
                               erg.uebersprungen.most_common()))
        if erg.fehler:
            z.append((f"Fehlerhafte Elemente: {erg.fehler}" if de
                      else f"Faulty elements: {erg.fehler}"))
        z += erg.hinweise
        return "\n".join(z)

    def import_dxf(self):
        self._cad_import("dxf")

    def import_dwg(self):
        self._cad_import("dwg")

    def import_pdf(self):
        """Imports one page of a PDF as vector geometry; PDF layers (optional
        content groups) become KatieCAD layers."""
        de = SPRACHE["aktuell"] == "de"
        titel = "PDF"
        try:
            from katiecad.fileio import pdf_import
        except Exception as ex:
            messagebox.showwarning(titel, (f"PDF-Import nicht verfügbar: {ex}" if de
                                           else f"PDF import not available: {ex}"))
            return
        if not pdf_import.PYPDF_OK:
            messagebox.showwarning(titel, ("pypdf nicht installiert:  pip install pypdf"
                                           if de else "pypdf is not installed:  pip install pypdf"))
            return
        if self._ist_layout():
            self.status.set("Bitte in die Modell-Ansicht wechseln." if de
                            else "Please switch to model view.")
            return
        pfad = filedialog.askopenfilename(
            filetypes=[(("PDF-Datei" if de else "PDF file"), "*.pdf"),
                       (("Alle Dateien" if de else "All files"), "*.*")])
        if not pfad:
            return
        try:
            n = pdf_import.seitenzahl(pfad)
        except Exception as ex:
            messagebox.showerror(titel, (f"Die PDF-Datei konnte nicht gelesen werden:\n{ex}"
                                         if de else f"The PDF could not be read:\n{ex}"))
            return
        seite = 1
        if n > 1:
            seite = simpledialog.askinteger(
                titel, (f"Welche Seite importieren? (1-{n})" if de
                        else f"Which page to import? (1-{n})"),
                initialvalue=1, minvalue=1, maxvalue=n, parent=self.root)
            if seite is None:
                return
        faktor = simpledialog.askfloat(
            titel, ("Maßstabsfaktor (1 = Papiergröße, z. B. 50 für einen Plot 1:50):"
                    if de else "Scale factor (1 = paper size, e.g. 50 for a 1:50 plot):"),
            initialvalue=1.0, minvalue=0.001, maxvalue=100000.0, parent=self.root)
        if faktor is None:
            return
        try:
            self.root.config(cursor="watch")
            self.root.update_idletasks()
        except Exception:
            pass
        try:
            erg = pdf_import.importiere_pdf(pfad, self.layers, seite, faktor)
            if not erg.elemente:
                messagebox.showwarning(titel, ("Es konnten keine Vektordaten importiert werden "
                                               "(gescanntes PDF?).\n" if de else
                                               "No vector data could be imported "
                                               "(scanned PDF?).\n") + self._import_bericht(erg, de))
                return
            self._snapshot()
            self.elemente.extend(erg.elemente)
            self.layer_cb.config(values=list(self.layers.keys()))
            self.zoom_grenzen()
            msg = (f"PDF importiert ({len(erg.elemente)} Elemente, {len(erg.neue_layer)} Layer): {pfad}"
                   if de else
                   f"PDF imported ({len(erg.elemente)} elements, {len(erg.neue_layer)} layers): {pfad}")
            self.status.set(msg)
            if erg.uebersprungen or erg.fehler or erg.hinweise:
                messagebox.showinfo(titel, msg + "\n\n" + self._import_bericht(erg, de))
        except Exception as e:
            messagebox.showerror(titel, (f"Fehler beim Import:\n{e}" if de
                                         else f"Import error:\n{e}"))
        finally:
            try:
                self.root.config(cursor="")
            except Exception:
                pass

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

        if self._attdef_wartend is not None:
            h(text=tr("msg.attdef.platzieren"))
            return
        if self._warte_auf_blockpunkt:
            h(text=tr("msg.block.einfuegepunkt"))
            return
        if self._block_erzeuge_auswahl is not None:
            h(text=tr("msg.block.basispunkt"))
            return

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
        elif w == "stutzen":
            if self._trim_status == "grenzen":
                h(text=tr("msg.stutzen.start"))
            else:
                h(text=tr("msg.stutzen.ziel"))
        elif w == "brechen":
            if self._break_status == "objekt":
                h(text=tr("msg.brechen.objekt"))
            elif self._break_status == "p1":
                h(text=tr("msg.brechen.punkt1"))
            else:
                h(text=tr("msg.brechen.punkt2"))
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
            if self._block_erzeuge_auswahl is not None:
                pt = self._parse_xy(text, einh)
                self.eingabe_var.set("")
                self._block_erzeugen_fertig(pt)
                return
            if w == "stutzen" and self._trim_status == "grenzen":
                self._trim_grenzen_bestaetigen()
                self.eingabe_var.set("")
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

    def _elektro_layer(self, name):
        """Creates an automatic electrical layer (E_*) if it is missing."""
        if name not in self.layers:
            farbe, staerke = ELEKTRO_LAYER.get(name, ("#c29bff", 0.35))
            self.layers[name] = Layer(name, farbe, staerke)
            try:
                self.layer_cb.config(values=list(self.layers.keys()))
            except Exception:
                pass
        return name

    def _layer_daten_fuer(self, name):
        """Like _layer_daten(), but on the given electrical layer."""
        daten = self._layer_daten()
        self._elektro_layer(name)
        daten["layer"] = name
        if not daten.get("eig_farbe"):
            daten["farbe"] = self.layers[name].farbe
        return daten

    def _andere_blaetter_daten(self):
        """JSON data of all other drawing sheets: [(index, path, dict)]."""
        p = self.projekt
        out = []
        if p is None:
            return out
        for i, b in enumerate(p.blaetter):
            if i == p.aktiv or getattr(b, "bericht", None):
                continue
            pfad = p.blatt_pfad(i)
            try:
                with open(pfad, "r", encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(d, dict):
                out.append((i, pfad, d))
        return out

    @staticmethod
    def _layer_aus_dicts(liste, benutzt):
        for d in liste:
            if isinstance(d, dict):
                benutzt.add(d.get("layer", "0"))
                kinder = d.get("elemente")
                if isinstance(kinder, list):
                    CadApp._layer_aus_dicts(kinder, benutzt)

    def ungenutzte_layer(self, projektweit=True):
        """Names of the layers that no object uses - in this drawing and,
        with a project, in no other sheet either (model, layouts, block
        contents). Layer 0 and the active layer are never listed."""
        benutzt = {"0", self.aktiver_layer.get()}

        def sammeln(liste):
            for el in liste:
                benutzt.add(getattr(el, "layer", "0"))
                kinder = getattr(el, "elemente", None)
                if isinstance(kinder, (list, tuple)):
                    sammeln(kinder)
        sammeln(self.elemente)
        for lay in self.layouts:
            sammeln(lay.elemente)
        kandidaten = list(self.layers)
        if projektweit and self.projekt is not None:
            for _i, _pf, d in self._andere_blaetter_daten():
                self._layer_aus_dicts(d.get("elemente", []), benutzt)
                for lay in d.get("layouts", []):
                    if isinstance(lay, dict):
                        self._layer_aus_dicts(lay.get("elemente", []), benutzt)
                for ld in d.get("layers", []):
                    if isinstance(ld, dict) and ld.get("name") not in kandidaten:
                        kandidaten.append(ld.get("name"))
        return [n for n in kandidaten if n not in benutzt]

    def layer_bereinigen_anwenden(self, namen, projektweit=True):
        """Removes the layers `namen` from this drawing and (project) from
        the layer tables of all other sheets."""
        for n in namen:
            self.layers.pop(n, None)
        if projektweit and self.projekt is not None:
            for _i, pfad, d in self._andere_blaetter_daten():
                alt = d.get("layers", [])
                neu = [ld for ld in alt
                       if not (isinstance(ld, dict) and ld.get("name") in namen)]
                if len(neu) != len(alt):
                    d["layers"] = neu
                    try:
                        self._json_atomar_schreiben(pfad, d)
                    except OSError as e:
                        print(f"[KatieCAD] Layer bereinigen: {e}")
            self._qv_cache.clear()

    def zu_element_springen(self, el):
        """Selects `el` and centres the view on it."""
        b = el.bbox()
        cw = self.canvas.winfo_width() or 1200
        ch = self.canvas.winfo_height() or 700
        bw, bh = max(b[2] - b[0], 1.0), max(b[3] - b[1], 1.0)
        zoom = min(cw * 0.3 / bw, ch * 0.3 / bh)
        zoom = max(1.0, min(zoom, 8.0))
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        self.view["zoom"] = zoom
        self.view["ox"] = cw / 2 - cx * zoom
        self.view["oy"] = ch / 2 + cy * zoom
        self.auswahl = [el]
        self.redraw()
        self._zeichne_raster()

    def suchen_ersetzen(self):
        if self._ist_layout():
            self.status.set("Suchen und Ersetzen gilt für die Zeichnung (Modell)."
                            if SPRACHE["aktuell"] == "de" else
                            "Find and replace works on the drawing (model).")
            return
        alt = getattr(self, "_such_dialog", None)
        try:
            if alt is not None and alt.winfo_exists():
                alt.deiconify()
                alt.lift()
                return
        except tk.TclError:
            pass
        self._such_dialog = SuchenErsetzenDialog(self.root, self)

    def _elektro_layer_pruefen(self, elemente=None):
        """Makes sure all E_* layers used by elements exist."""
        for el in (self.elemente if elemente is None else elemente):
            if getattr(el, "layer", None) in ELEKTRO_LAYER:
                self._elektro_layer(el.layer)

    def _block_layer(self, elemente):
        """Device blocks (with an electrical mask) go onto E_DEVICES."""
        if any(isinstance(k, ElektroMaske) for k in elemente):
            return self._elektro_layer(E_DEVICES)
        return self.aktiver_layer.get()

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
                out.append(("t", cx, cy, s, h, ang, "Arial", "mitte_zentriert"))
            return out
        return []

    def _el_polylinien(self, el, skala):
        if isinstance(el, Bild):
            return [(el.rahmen(), True)]
        if isinstance(el, Text):
            return [(el.rahmen(), True)]
        if isinstance(el, Schraffur):
            return [(el.punkte, True)]
        if isinstance(el, ZUSAMMENGESETZT):
            out = []
            for kind in el.aufgeloest():
                out.extend(self._el_polylinien(kind, skala))
            return out
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

        em = max(4, min(600, int(round(h_px / CAD_VERSALHOEHE))))
        f = self._font(fam, em)
        # The system font may be wider/narrower than Arial (e.g.
        # DejaVu on Linux). Adjust the size so that the width matches the
        # model width -> anchors (right/centred) are correct.
        w_soll = w_mm * skala
        w_px = max(f.measure(z) for z in zeilen)
        if w_px > 0 and w_soll > 0 and abs(w_px - w_soll) > 1.0:
            em2 = max(4, min(600, int(round(em * w_soll / w_px))))
            if em2 != em:
                em = em2
                f = self._font(fam, em)
        asc = f.metrics("ascent")
        desc = f.metrics("descent")
        ls = f.metrics("linespace")
        w_px = w_soll

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
        if self._warte_auf_blockpunkt:
            pt = self._eingabepunkt_px(self._maus_px[0], self._maus_px[1],
                                       None, marker=False)
            self._block_vorschau(pt)
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
                          font=(UI_SCHRIFT, 9, "bold"), tags="vorschau")

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
        elif w == "stutzen" and self._trim_status == "ziele":
            tol_mm = 8 / self._ctx_skala()
            ziel = self._element_auf_punkt_snap(pt[0], pt[1], tol_mm)
            if ziel is not None:
                self._zeichne_auswahl_highlight(ziel, farbe=FARBEN["orange"],
                                                tags=("vorschau",))
        elif w == "brechen" and self._break_status == "objekt":
            tol_mm = 8 / self._ctx_skala()
            ziel = self._element_auf_punkt_snap(pt[0], pt[1], tol_mm)
            if ziel is not None:
                self._zeichne_auswahl_highlight(ziel, farbe=FARBEN["orange"],
                                                tags=("vorschau",))

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

    def _eig_palette_nachziehen(self):
        pal = getattr(self, "_eig_palette", None)
        if pal is not None:
            sig = tuple(id(e) for e in self.auswahl)
            if sig != getattr(self, "_eig_sig", None):
                self._eig_sig = sig
                try:
                    pal.aktualisieren()
                except tk.TclError:
                    self._eig_palette = None

    def eigenschaften_fenster(self, event=None):
        """Properties window (Ctrl+1) for the selection."""
        pal = getattr(self, "_eig_palette", None)
        if pal is not None:
            try:
                pal.lift()
                pal.aktualisieren()
                return "break"
            except tk.TclError:
                pass
        self._eig_palette = EigenschaftenPalette(self.root, self)
        return "break"

    def eigenschaft_anwenden(self, feld, wert):
        from katiecad.model.eigenschaften import anwenden
        if not self.auswahl:
            return
        self._snapshot()
        n = anwenden(self.auswahl, feld, wert)
        self.redraw()
        pal = getattr(self, "_eig_palette", None)
        if pal is not None:
            pal.aktualisieren()
        self.status.set(tr("msg.eig.angewendet", n=n))

    def _stil_auf_auswahl(self, event=None):
        ziele = [e for e in self.auswahl
                 if not isinstance(e, (Viewport, Text, Bemassung, BlockReferenz,
                                       Schraffur, Querverweis, Verbindung,
                                       ElektroMaske, Klemme, Kabel, Koordinatenfeld))]
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
            vorher = list(self.auswahl)
            self.aktives_werkzeug.set("auswahl")
            self._pts = []
            self.letzter_punkt = None
            self._clear_temp()
            self._drag_modus = None
            # Objects already picked with a crossing window: no second drag
            fw = getattr(self, "_letztes_fenster", None)
            ids = {id(e) for e in vorher}
            if vorher and fw and fw[1] and set(fw[1]) <= ids:
                self.auswahl = vorher
                self._op = {"typ": "stretch", "stufe": "basis", "basis": None,
                            "objekte": vorher, "fenster": fw[0]}
                self.redraw()
                self._op_hinweis()
                self.status.set(("STRECKEN: Basispunkt angeben." if de
                                 else "STRETCH: specify base point."))
                return
            self.auswahl = vorher       # kept: only these get stretched
            self._op = {"typ": "stretch", "stufe": "fenster", "basis": None,
                        "objekte": vorher, "fenster": None}
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
                "scale": "SKALIEREN" if de else "SCALE",
                "mirror": "SPIEGELN" if de else "MIRROR",
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
            if op["typ"] == "mirror":
                t = ("Ersten Punkt der Spiegelachse angeben" if de
                     else "Specify the first point of the mirror line")
            else:
                t = ("Basispunkt angeben (klicken oder x,y)" if de
                     else "Specify base point (click or x,y)")
        else:
            if op["typ"] == "copy":
                t = (("Zielpunkt: klicken, 'x,y', '@dx,dy', 'L<Winkel' - "
                      "Enter/Rechtsklick = fertig") if de else
                     ("Target point: click, 'x,y', '@dx,dy', 'L<angle' - "
                      "Enter/right-click = done"))
            elif op["typ"] == "mirror":
                t = ("Zweiten Punkt der Spiegelachse angeben" if de else
                     "Specify the second point of the mirror line")
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
            if op["typ"] == "scale":
                self._op_skalieren_fertig()
                return
            op["stufe"] = "ziel"
            self._op_hinweis()
            return
        if op["stufe"] == "ziel":
            if op["typ"] == "mirror":
                self._op_spiegeln_fertig(pt)
                return
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
                n_ein = self._einrasten(op["objekte"])
                self._op_beenden(
                    (f"Verschoben um dx={dx / self._einh_faktor():.3f}, "
                     f"dy={dy / self._einh_faktor():.3f} {self.einheit.get()}"
                     if de else
                     f"Moved by dx={dx / self._einh_faktor():.3f}, "
                     f"dy={dy / self._einh_faktor():.3f} {self.einheit.get()}"))
            else:
                kopien = []
                for el in op["objekte"]:
                    k = self._dict_zu_element(el.to_dict())
                    if k is not None:
                        k.verschieben(dx, dy)
                        ziel.append(k)
                        kopien.append(k)
                self._einrasten(kopien)
                self.redraw()
                self.status.set(
                    (f"Kopiert (dx={dx / self._einh_faktor():.3f}, "
                     f"dy={dy / self._einh_faktor():.3f}). Weiteren Zielpunkt "
                     "angeben oder Enter/Rechtsklick = fertig." if de else
                     f"Copied (dx={dx / self._einh_faktor():.3f}, "
                     f"dy={dy / self._einh_faktor():.3f}). Specify another "
                     "target point or Enter/right-click = done."))

    def _op_skalieren_fertig(self):
        """Scale: factor from a small dialog, applied about the base point."""
        op = self._op
        de = SPRACHE["aktuell"] == "de"
        bx, by = op["basis"]
        text = simpledialog.askstring(
            "Skalieren" if de else "Scale",
            ("Skalierfaktor (z. B. 2 oder 0,5):" if de
             else "Scale factor (e.g. 2 or 0.5):"),
            initialvalue="2", parent=self.root)
        if text is None:
            self._op_beenden("Abgebrochen." if de else "Cancelled.")
            return
        try:
            f = float(text.strip().replace(",", "."))
            if not (1e-6 < f < 1e6):
                raise ValueError
        except ValueError:
            self.status.set("Ungültiger Faktor." if de else "Invalid factor.")
            self._op_beenden("Ungültiger Faktor." if de else "Invalid factor.")
            return
        self._snapshot()
        for el in op["objekte"]:
            el.skalieren(bx, by, f)
        self._op_beenden((f"Skaliert um Faktor {f:g}." if de
                          else f"Scaled by factor {f:g}."))

    def _op_spiegeln_fertig(self, pt):
        op = self._op
        de = SPRACHE["aktuell"] == "de"
        ax, ay = op["basis"]
        if math.hypot(pt[0] - ax, pt[1] - ay) < 1e-9:
            return
        loeschen = messagebox.askyesno(
            "Spiegeln" if de else "Mirror",
            ("Originalobjekte löschen?" if de else "Delete the original objects?"),
            default=messagebox.NO, parent=self.root)
        self._snapshot()
        if loeschen:
            for el in op["objekte"]:
                el.spiegeln(ax, ay, pt[0], pt[1])
        else:
            ziel = self._ziel_liste()
            kopien = []
            for el in op["objekte"]:
                k = self._dict_zu_element(el.to_dict())
                if k is not None:
                    k.spiegeln(ax, ay, pt[0], pt[1])
                    ziel.append(k)
                    kopien.append(k)
            self._einrasten(kopien)
        self._op_beenden("Gespiegelt." if de else "Mirrored.")

    def _stretch_anwenden(self, fenster, dx, dy):
        xmin, ymin, xmax, ymax = fenster

        def innen(x, y):
            return xmin <= x <= xmax and ymin <= y <= ymax

        nur = {id(e) for e in (self._op or {}).get("objekte") or []}
        for el in self._aktuelle_elemente_liste():
            l = self.layers.get(el.layer)
            if l and not l.sichtbar:
                continue
            if nur and id(el) not in nur:
                continue
            self._stretch_element(el, innen, dx, dy)

    def _stretch_element(self, el, innen, dx, dy):
        if isinstance(el, BlockReferenz):
            if innen(el.x, el.y):
                el.x += dx; el.y += dy
            return
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

            nur = {id(e) for e in op.get("objekte") or []}
            for el in self._aktuelle_elemente_liste():
                l = self.layers.get(el.layer)
                if l and not l.sichtbar:
                    continue
                if nur and id(el) not in nur:
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
                font=(UI_SCHRIFT, 9, "bold"), tags="vorschau",
                text=f"dx {dx / einh:.2f}  dy {dy / einh:.2f}")
            return

        if op["typ"] == "mirror":
            ax, ay = op["basis"]
            if math.hypot(pt[0] - ax, pt[1] - ay) > 1e-9:
                for el in op["objekte"]:
                    k = self._dict_zu_element(el.to_dict())
                    if k is None or isinstance(k, Viewport):
                        continue
                    k.spiegeln(ax, ay, pt[0], pt[1])
                    self._zeichne_element(k, tags=("vorschau",), tf=tf, skala=sk,
                                          stil=stil)
            bx_px, by_px = tf(ax, ay)
            px_, py_ = tf(*pt)
            self.canvas.create_line(bx_px, by_px, px_, py_, fill=FARBEN["gelb"],
                                    dash=(2, 3), tags="vorschau")
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
                                    font=(UI_SCHRIFT, 9, "bold"),
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
                                font=(UI_SCHRIFT, 9, "bold"), tags="vorschau",
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
        elif self.aktives_werkzeug.get() == "stutzen" and self._trim_status == "grenzen":
            self._trim_grenzen_bestaetigen()
        elif self.aktives_werkzeug.get() == "brechen":
            self._break_abbrechen()
            self._werkzeug_gewechselt()

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
        elif cmd in ("move", "copy", "copybase", "array", "rotate", "stretch",
                     "scale", "mirror"):
            self._op_start(cmd)
        elif cmd == "paste":
            self.einfuegen()
        elif cmd == "druck":
            self.drucken()
        elif cmd == "undo":
            self.undo()
        elif cmd == "redo":
            self.redo()
        elif cmd == "suchen":
            self.suchen_ersetzen()
        elif cmd == "matchprop":
            self.eigenschaften_uebertragen_start()
        elif cmd == "attdef":
            self.attdef_erstellen()
        elif cmd == "attedit":
            self.attribute_bearbeiten()
        elif cmd == "block:speichern":
            self.block_speichern_datei()
        elif cmd == "block:laden":
            self.block_laden_datei()
        elif cmd == "blatt:neu":
            self.blatt_neu()
        elif cmd == "delete":
            self.auswahl_loeschen()
        elif cmd == "zg":
            self.zoom_grenzen()
        elif cmd == "block:neu":
            self.block_erzeugen()
        elif cmd == "block:einfuegen":
            self.block_einfuegen()
        elif cmd == "block:liste":
            self.block_liste()
        elif cmd == "block:explode":
            self.block_aufloesen()
        elif cmd.startswith("bem:"):
            self._bem_art_starten(cmd[4:])
        elif cmd.startswith("tool:"):
            self.aktives_werkzeug.set(cmd[5:])
            self._werkzeug_gewechselt()
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
            m.add_command(label=tr("menu.bearbeiten.skalieren"),
                          command=lambda: self._op_start("scale"))
            m.add_command(label=tr("menu.bearbeiten.spiegeln"),
                          command=lambda: self._op_start("mirror"))
            if any(isinstance(e, BlockReferenz) and e.attribut_definitionen()
                   for e in self.auswahl):
                m.add_command(label=tr("menu.bloecke.attedit"),
                              command=self.attribute_bearbeiten)
            # NEW: explode block if a block is in the selection
            if any(isinstance(e, BlockReferenz) for e in self.auswahl):
                m.add_command(label=tr("menu.einfuegen.block_aufloesen"),
                              command=self.block_aufloesen)
            if any(hasattr(e, "texte_zuruecksetzen") for e in self.auswahl):
                m.add_command(label=tr("menu.bearbeiten.texte_zuruecksetzen"),
                              command=self.texte_zuruecksetzen)
            m.add_separator()
            m.add_command(label=tr("menu.bearbeiten.eigenschaften"),
                          command=self.eigenschaften_fenster)
            m.add_separator()
            m.add_command(label=("Löschen" if de else "Delete"),
                          command=self.auswahl_loeschen)
            m.add_separator()
        m.add_command(label=("Einfügen" if de else "Paste"), command=self.einfuegen)
        m.add_command(label=("Alles markieren" if de else "Select all"),
                      command=self.alle_markieren)
        m.add_command(label=("Zoom Grenzen" if de else "Zoom extents"),
                      command=self.zoom_grenzen)
        self._menue_zeigen(m, event.x_root, event.y_root)

    def texte_zuruecksetzen(self):
        """Puts the freely moved texts of the selected objects (terminals,
        masks, cables, pins, devices, cross references) back to their
        automatic position."""
        ziele = [e for e in self.auswahl if hasattr(e, "texte_zuruecksetzen")]
        if not ziele:
            return
        self._snapshot()
        for e in ziele:
            e.texte_zuruecksetzen()
        self.redraw()
        self.status.set(tr("msg.texte_zurueckgesetzt", n=len(ziele)))

    def _menue_zeigen(self, m, x, y):
        """Pops up a context menu. Windows/Mac: tk_popup. Linux (X11):
        tk_popup inside the button-release handler closes the menu at once
        (the grab is lost again), so it is posted a moment later WITHOUT a
        grab and closed again on focus loss, Escape or a click elsewhere."""
        if not sys.platform.startswith("linux"):
            try:
                m.tk_popup(x, y)
            finally:
                m.grab_release()
            return

        def schliessen(_e=None):
            try:
                m.unpost()
            except tk.TclError:
                pass
            try:
                self.root.unbind("<Button-1>", self._menue_bind)
            except (tk.TclError, AttributeError):
                pass

        def klick(e):
            if str(e.widget) != str(m):
                schliessen()

        def zeigen():
            try:
                try:
                    vorher = self.root.focus_get()
                except (KeyError, tk.TclError):
                    vorher = None
                m.post(x, y)

                def fokus_zurueck(_e=None):
                    # Give the keyboard focus back (otherwise keyboard
                    # input stays dead on Wayland/XWayland afterwards)
                    def los():
                        try:
                            (vorher or self.canvas).focus_force()
                        except tk.TclError:
                            try:
                                self.canvas.focus_force()
                            except tk.TclError:
                                pass
                    self.root.after(20, los)
                m.bind("<Unmap>", fokus_zurueck)
                m.bind("<Escape>", schliessen)
                self._menue_bind = self.root.bind("<Button-1>", klick, add="+")
            except tk.TclError as ex:
                print(f"[KatieCAD] Kontextmenü: {ex}")
        self.root.after(80, zeigen)

    def _zeichnung_anwenden(self, daten, layer_zuruecksetzen=False):
        """Replaces the work area with the contents of `daten`
        (format as in _zeichnung_daten)."""
        if layer_zuruecksetzen:
            self.layers = self._standard_layers()
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
        if self.aktiver_layer.get() not in self.layers:
            self.aktiver_layer.set("0")
        self.elemente = []
        for d in daten.get("elemente", []):
            el = self._dict_zu_element(d)
            if el:
                self.elemente.append(el)

        # Take over the block definitions of the file into the library -
        # names that already exist stay unchanged (placed blocks
        # carry their geometry themselves anyway). A single write.
        neue_bloecke = False
        for bd in daten.get("block_definitionen", []):
            try:
                d = BlockDefinition.from_dict(bd, self._dict_zu_element)
                if d.name not in self.block_bibliothek:
                    self.block_bibliothek.setze(d, persistieren=False)
                    neue_bloecke = True
            except Exception as ex:
                print(f"[KatieCAD] Block konnte nicht geladen werden: {ex}")
        if neue_bloecke:
            self.block_bibliothek._speichern()

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
        self._trim_abbrechen()
        self._break_abbrechen()
        self._warte_auf_blockpunkt = False
        self._block_einfuege_name = None
        self._block_erzeuge_auswahl = None
        self._attdef_wartend = None
        bg = self.bg_modell if not self._ist_layout() else self.bg_layout
        self.canvas.config(bg=bg)
        self.bg_btn.config(bg=bg)
        self._layout_switcher_neu_aufbauen()
        self._update_kontext_widgets()
        self._mark_clean()
        self.redraw()
        self._zeichne_raster()
        self._viewport_modus_anzeige_aktualisieren()
        try:
            self._layer_info_aktualisieren()
        except Exception:
            pass

    def _projekt_fuer_einzeldatei_schliessen(self):
        if self.projekt is not None:
            self.projekt = None
            self._undo_pro_blatt = {}
            self.seitenleiste.aktualisieren()
            self._update_titel()

    # ========================================================
    # NEW: drawing <-> dict/file (used by save/open
    #      and by project management)
    # ========================================================
    def _standard_layers(self):
        return {
            "0": Layer("0", "#c29bff", 0.35),
            "Konstruktion": Layer("Konstruktion", "#b886fb", 0.25),
            "Bemaßung": Layer("Bemaßung", "#ff2d95", 0.25),
            "Schrift": Layer("Schrift", "#d8d0e8", 0.35),
            "Verdeckt": Layer("Verdeckt", "#8b7ea8", 0.25),
        }

    def _zeichnung_daten(self):
        return {
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
            "block_definitionen": [
                d.to_dict() for d in
                (self.block_bibliothek.get(n) for n in self.block_bibliothek.namen())
                if d is not None
            ],
        }

    def _leere_zeichnung_daten(self, einstellungen_uebernehmen=True):
        """Data for an empty sheet. Unit, format, background and layers are
        taken from the current sheet (new sheet in a project) or set to
        defaults (first sheet)."""
        if einstellungen_uebernehmen:
            fmt, bg_l = self.layout_format, self.bg_layout
            layers = [l.to_dict() for l in self.layers.values()]
        else:
            fmt, bg_l = Layout.STANDARD_FORMAT, Layout.STANDARD_BG
            layers = [l.to_dict() for l in self._standard_layers().values()]
        return {
            "einheit": self.einheit.get(),
            "massstab": self.massstab.get(),
            "bg_modell": self.bg_modell,
            "layout_format": fmt,
            "bg_layout": bg_l,
            "raster_mm": self._zahl(self.raster_mm, 5.0),
            "fang_mm": self._zahl(self.fang_mm, 5.0),
            "layers": layers,
            "elemente": [],
            "layouts": [Layout("Layout1", fmt, bg_l).to_dict()],
            "aktives_layout": 0,
            "ansicht": "modell",
            "sprache": SPRACHE["aktuell"],
            "block_definitionen": [],
        }

    @staticmethod
    def _json_atomar_schreiben(pfad, daten):
        tmp = pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(daten, f, indent=2, ensure_ascii=False)
        os.replace(tmp, pfad)

    def _zeichnung_in_datei(self, pfad):
        """Writes the current drawing (raises OSError on errors)."""
        self._json_atomar_schreiben(pfad, self._zeichnung_daten())

    # ========================================================
    # NEW: project management
    # ========================================================
    def _projekt_aenderungen_klaeren(self):
        """Asks about unsaved changes. True = continue."""
        if not self._dirty:
            return True
        antwort = messagebox.askyesnocancel(
            tr("msg.projekt.titel"), tr("msg.projekt.speichern_frage"),
            parent=self.root)
        if antwort is None:
            return False
        if antwort:
            return bool(self.speichern())
        return True

    def _letzten_projektordner_merken(self, projekt):
        try:
            cfg = lade_konfiguration()
            cfg["letzter_projektordner"] = os.path.dirname(projekt.ordner)
            speichere_konfiguration(cfg)
        except Exception as e:
            print(f"[KatieCAD] Konfiguration: {e}")

    def _blatt_sichern(self):
        """Silently saves the current sheet if it was changed."""
        p = self.projekt
        if p is None or not self._dirty:
            return True
        try:
            self._zeichnung_in_datei(p.blatt_pfad(p.aktiv))
        except OSError as e:
            messagebox.showerror(tr("msg.projekt.titel"),
                                 tr("msg.projekt.fehler", fehler=e),
                                 parent=self.root)
            return False
        self._mark_clean()
        return True

    def _blatt_laden(self, index):
        """Loads sheet `index` of the project into the work area."""
        p = self.projekt
        pfad = p.blatt_pfad(index)
        try:
            with open(pfad, "r", encoding="utf-8") as f:
                daten = json.load(f)
            if not isinstance(daten, dict):
                raise ValueError("kein JSON-Objekt")
        except (OSError, ValueError):
            messagebox.showwarning(tr("msg.projekt.titel"),
                                   tr("msg.projekt.blatt_fehlt", pfad=pfad),
                                   parent=self.root)
            if os.path.exists(pfad):
                try:
                    import shutil
                    shutil.copy2(pfad, pfad + ".defekt")
                except OSError:
                    pass
            daten = self._leere_zeichnung_daten(einstellungen_uebernehmen=False)
            try:
                self._json_atomar_schreiben(pfad, daten)
            except OSError:
                pass
        p.aktiv = index
        self._zeichnung_anwenden(daten, layer_zuruecksetzen=True)
        stacks = self._undo_pro_blatt.get(pfad)
        if stacks:
            self._undo_stack, self._redo_stack = stacks
        else:
            self._undo_stack, self._redo_stack = [], []
        self._aktualisiere_undo_redo()
        self._mark_clean()
        try:
            self.zoom_grenzen()
        except Exception:
            pass
        self.seitenleiste.aktualisieren()
        self._update_titel()

    def projekt_erstellen(self):
        if not self._projekt_aenderungen_klaeren():
            return
        start = lade_konfiguration().get("letzter_projektordner", "")
        if not start or not os.path.isdir(start):
            start = os.path.expanduser("~")
        dlg = ProjektNeuDialog(self.root, start)
        if not dlg.result:
            return
        name, basis = dlg.result
        try:
            p = Projekt.erstellen(name, basis)
            b = p.blatt_hinzufuegen("Blatt 1")
            self._json_atomar_schreiben(
                p.blatt_pfad(b),
                self._leere_zeichnung_daten(einstellungen_uebernehmen=False))
            p.speichern()
        except ProjektFehler as e:
            code = str(e)
            msg = (tr("dlg.projekt.fehler." + code)
                   if ("dlg.projekt.fehler." + code) in TEXTE["de"] else code)
            messagebox.showerror(tr("msg.projekt.titel"), msg,
                                 parent=self.root)
            return
        except OSError as e:
            messagebox.showerror(tr("msg.projekt.titel"),
                                 tr("msg.projekt.fehler", fehler=e),
                                 parent=self.root)
            return
        self.projekt = p
        self._undo_pro_blatt = {}
        self._blatt_laden(0)
        p.speichern()
        self._letzten_projektordner_merken(p)
        self.status.set(tr("msg.projekt.erstellt", name=p.name, pfad=p.ordner))

    def projekt_oeffnen(self):
        if not self._projekt_aenderungen_klaeren():
            return
        start = lade_konfiguration().get("letzter_projektordner", "")
        kw = {"initialdir": start} if start and os.path.isdir(start) else {}
        pfad = filedialog.askopenfilename(
            parent=self.root, title=tr("menu.projekt.oeffnen"),
            filetypes=[(tr("dlg.projekt.dateityp"), "*" + PROJEKT_ENDUNG),
                       ("*.*", "*.*")], **kw)
        if not pfad:
            return
        self.projekt_aus_datei_oeffnen(pfad)

    def projekt_aus_datei_oeffnen(self, pfad):
        try:
            p = Projekt.laden(pfad)
        except ProjektFehler as e:
            code = str(e)
            msg = (tr("msg.projekt.keine_projektdatei") if code == "kein_projekt"
                   else tr("msg.projekt.fehler", fehler=code))
            messagebox.showerror(tr("msg.projekt.titel"), msg,
                                 parent=self.root)
            return False
        try:
            if not p.blaetter:
                b = p.blatt_hinzufuegen("Blatt 1")
                self._json_atomar_schreiben(
                    p.blatt_pfad(b),
                    self._leere_zeichnung_daten(einstellungen_uebernehmen=False))
                p.speichern()
        except OSError as e:
            messagebox.showerror(tr("msg.projekt.titel"),
                                 tr("msg.projekt.fehler", fehler=e),
                                 parent=self.root)
            return False
        self.projekt = p
        self._undo_pro_blatt = {}
        self._blatt_laden(p.aktiv)
        self._letzten_projektordner_merken(p)
        self.status.set(tr("msg.projekt.geoeffnet", name=p.name))
        return True

    def projekt_speichern(self):
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return False
        try:
            self._zeichnung_in_datei(p.blatt_pfad(p.aktiv))
            p.speichern()
        except OSError as e:
            messagebox.showerror(tr("msg.speichern_fehlgeschlagen"), str(e),
                                 parent=self.root)
            return False
        self._mark_clean()
        self.status.set(tr("msg.projekt.gespeichert", name=p.name))
        return True

    def _projekt_zuruecksetzen(self):
        """Leave the project without asking; the work area becomes empty."""
        self.projekt = None
        self._undo_pro_blatt = {}
        self._zeichnung_anwenden(
            self._leere_zeichnung_daten(einstellungen_uebernehmen=False),
            layer_zuruecksetzen=True)
        self._undo_reset()
        self._mark_clean()
        self.seitenleiste.aktualisieren()
        self._update_titel()

    def _menues_schliessen_binden(self):
        """Linux/X11: a menu opened from the menu bar can stay on screen when
        the window loses focus or when the user clicks elsewhere. Close all
        open menus in these cases."""
        def alle_menues(w):
            for c in w.winfo_children():
                if isinstance(c, tk.Menu):
                    yield c
                yield from alle_menues(c)

        def schliessen(event=None):
            try:
                for m in alle_menues(self.root):
                    try:
                        m.unpost()
                    except tk.TclError:
                        pass
            except Exception:
                pass

        def fokus_weg(event):
            if event.widget is self.root:
                schliessen()

        def klick(event):
            if not isinstance(event.widget, tk.Menu):
                schliessen()

        self._menues_schliessen = schliessen

        zustand = {"seit": None, "taste": 0.0}

        def dropdowns():
            """Currently open drop-down / popup menus (not the menu bar)."""
            leiste = str(self.root.cget("menu") or "")
            out = []
            for m in alle_menues(self.root):
                try:
                    if str(m) != leiste and m.winfo_ismapped():
                        out.append(m)
                except tk.TclError:
                    pass
            return out

        def taste(event=None):
            zustand["taste"] = time.monotonic()

        def pointer_woanders():
            """True if the mouse is not over any menu / the menu bar / the
            window frame - under XWayland the click into a foreign window
            never reaches Tk, the pointer simply stays where it left."""
            px, py = self.root.winfo_pointerxy()
            w = self.root.winfo_containing(px, py)
            if isinstance(w, tk.Menu):
                return False
            ry = self.root.winfo_rooty()
            if py < ry:                          # menu bar / title bar
                return py < ry - 80
            return True

        def wache():
            """Closes an open menu that is still on screen although the user
            has switched to another application (X11/XWayland)."""
            try:
                offen = dropdowns()
                if not offen:
                    zustand["seit"] = None
                else:
                    fremd = self.root.focus_displayof() is None
                    if not fremd:
                        fremd = (pointer_woanders()
                                 and time.monotonic() - zustand["taste"] > 5.0)
                    if not fremd:
                        zustand["seit"] = None
                    elif zustand["seit"] is None:
                        zustand["seit"] = time.monotonic()
                    elif time.monotonic() - zustand["seit"] >= 0.8:
                        zustand["seit"] = None
                        schliessen()
                        try:
                            self.root.tk.eval(
                                "catch {tk::MenuUnpost {%s}}"
                                % str(self.root.cget("menu")))
                        except tk.TclError:
                            pass
                        try:
                            g = self.root.grab_current()
                            if isinstance(g, tk.Menu):
                                g.grab_release()
                        except tk.TclError:
                            pass
            except Exception:
                pass
            self.root.after(300, wache)

        self.root.bind_all("<KeyPress>", taste, add="+")
        self.root.bind_all("<FocusOut>", lambda e: self.root.after(
            100, lambda: schliessen() if (dropdowns() and
                                         self.root.focus_displayof() is None) else None),
            add="+")
        self.root.after(300, wache)

        self.root.after(250, wache)
        self.root.bind("<FocusOut>", fokus_weg, add="+")
        self.root.bind("<Unmap>", fokus_weg, add="+")
        self.root.bind_all("<ButtonPress>", klick, add="+")

    def schriftkopf_felder_pruefen(self):
        """Shows the field names (tags) of the title block in the current
        layout and whether KatieCAD fills them in automatically."""
        text = TB.feld_bericht(self.layout_elemente)
        if not text:
            text = tr("msg.felder.keiner")
        messagebox.showinfo(tr("dlg.felder.titel"), text, parent=self.root)

    def projekt_eigenschaften(self):
        """Project data + revision table (used for title blocks on all sheets)."""
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        dlg = ProjektEigenschaftenDialog(self.root, p.daten, p.name)
        if dlg.result is None:
            return
        d = dlg.result
        # Fix the dates once (instead of "today" changing every day)
        heute = datetime.date.today()
        heute = (heute.strftime("%d.%m.%Y") if SPRACHE["aktuell"] == "de"
                 else heute.strftime("%Y-%m-%d"))
        if d.get("gezeichnet") and not d.get("datum"):
            d["datum"] = heute
        if d.get("geprueft") and not d.get("geprueft_datum"):
            d["geprueft_datum"] = d.get("datum") or heute
        p.daten = d
        try:
            p.speichern()
        except Exception as e:
            messagebox.showerror(tr("msg.projekt.titel"),
                                 tr("msg.projekt.fehler", fehler=e), parent=self.root)
        self._titelfelder_aktualisieren()
        self.redraw()
        self._mark_dirty()
        self.status.set(tr("msg.pe.gespeichert"))

    def schriftkopf_felder_pruefen(self):
        """Shows the fields of the title block on this sheet and whether
        they are filled in automatically (helps with own templates)."""
        zeilen = []
        for lay in self.layouts:
            for el in lay.elemente:
                if TB.is_title_block(el):
                    for ad in el.attribut_definitionen():
                        zeilen.append((round(-ad.y, 1), round(ad.x, 1), ad.tag))
        if not zeilen:
            messagebox.showinfo(tr("dlg.tbf.titel"), tr("msg.tbf.keiner"),
                                parent=self.root)
            return
        zeilen.sort(key=lambda t: (t[0], t[1]))
        text = "\n".join("%-26s %s" % (tag, tr("dlg.tbf.auto") if TB.is_auto_tag(tag)
                                       else tr("dlg.tbf.manuell"))
                         for _y, _x, tag in zeilen)
        messagebox.showinfo(tr("dlg.tbf.titel"), tr("msg.tbf.kopf") + "\n\n" + text,
                            parent=self.root)

    def projekt_umbenennen(self):
        """Rename project (project file and, if possible, the folder too)."""
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        name = _LayoutNameDialog(self.root, tr("msg.projekt.umbenennen"),
                                 p.name, label=tr("dlg.projekt.name")).result
        if name is None or name.strip() == p.name:
            return
        try:
            self._zeichnung_in_datei(p.blatt_pfad(p.aktiv))   # save open changes
            ordner_alt = p.ordner
            alt = p.name
            mit_ordner = p.umbenennen(name)
        except ProjektFehler as e:
            code = str(e)
            if code in ("leer", "zeichen", "ende", "reserviert", "existiert"):
                msg = tr("msg.projekt.name_" + code)
            else:
                msg = tr("msg.projekt.fehler", fehler=code)
            messagebox.showerror(tr("msg.projekt.titel"), msg, parent=self.root)
            return
        except OSError as e:
            messagebox.showerror(tr("msg.projekt.titel"),
                                 tr("msg.projekt.fehler", fehler=e), parent=self.root)
            return
        self._ge_cache = {}
        self._letzten_projektordner_merken(p)
        self.seitenleiste.aktualisieren()
        self._update_titel()
        self.status.set(tr("msg.projekt.umbenannt", alt=alt, name=p.name))

    def projekt_schliessen(self):
        if self.projekt is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        if not self._projekt_aenderungen_klaeren():
            return
        self._projekt_zuruecksetzen()
        self.status.set(tr("msg.projekt.geschlossen"))

    def projekt_loeschen(self):
        p = self.projekt
        offen = p is not None
        if not offen:
            start = lade_konfiguration().get("letzter_projektordner", "")
            kw = {"initialdir": start} if start and os.path.isdir(start) else {}
            pfad = filedialog.askopenfilename(
                parent=self.root, title=tr("menu.projekt.loeschen"),
                filetypes=[(tr("dlg.projekt.dateityp"), "*" + PROJEKT_ENDUNG)],
                **kw)
            if not pfad:
                return
            try:
                p = Projekt.laden(pfad)
            except ProjektFehler:
                messagebox.showerror(tr("msg.projekt.titel"),
                                     tr("msg.projekt.keine_projektdatei"),
                                     parent=self.root)
                return
        if not messagebox.askyesno(
                tr("msg.projekt.titel"),
                tr("msg.projekt.loeschen_frage", name=p.name,
                   n=len(p.blaetter), pfad=p.ordner),
                icon="warning", parent=self.root):
            return
        eingabe = simpledialog.askstring(
            tr("msg.projekt.titel"), tr("msg.projekt.loeschen_name"),
            parent=self.root)
        if eingabe is None or eingabe.strip() != p.name:
            return
        if offen:
            self._projekt_zuruecksetzen()
        ordner_weg, uebrig = p.loeschen()
        if ordner_weg or not uebrig:
            self.status.set(tr("msg.projekt.geloescht", name=p.name))
        else:
            messagebox.showinfo(
                tr("msg.projekt.titel"),
                tr("msg.projekt.geloescht_rest", name=p.name,
                   liste="\n".join(uebrig[:15])), parent=self.root)
            self.status.set(tr("msg.projekt.geloescht", name=p.name))

    # ---- Sheets --------------------------------------------------
    def blatt_wechseln(self, index):
        """Switches to sheet `index`; silently saves the current one.
        Returns: True on success."""
        p = self.projekt
        if p is None or not (0 <= index < len(p.blaetter)):
            return False
        if index == p.aktiv:
            return True
        if not self._blatt_sichern():
            return False
        self._stacks_merken(p.blatt_pfad(p.aktiv))
        self._blatt_laden(index)
        try:
            p.speichern()
        except OSError:
            pass
        self.entry_eingabe.focus_set()
        self.status.set(tr("msg.doku.bericht_blatt") if p.blaetter[index].bericht
                        else tr("msg.blatt.wechsel", nr=p.nummer(index),
                                name=p.blaetter[index].name))
        return True

    def blatt_neu(self):
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        name = _LayoutNameDialog(self.root, tr("msg.blatt.neu_titel"),
                                 p.neuer_blattname(),
                                 label=tr("dlg.blatt.name")).result
        if name is None:
            return
        if not self._blatt_sichern():
            return
        daten = self._leere_zeichnung_daten(einstellungen_uebernehmen=True)
        b = p.blatt_hinzufuegen(name)
        try:
            self._json_atomar_schreiben(p.blatt_pfad(b), daten)
            p.speichern()
        except OSError as e:
            p.blaetter.remove(b)
            messagebox.showerror(tr("msg.projekt.titel"),
                                 tr("msg.projekt.fehler", fehler=e),
                                 parent=self.root)
            return
        self._stacks_merken(p.blatt_pfad(p.aktiv))
        self._blatt_laden(p.blaetter.index(b))
        p.speichern()
        self.status.set(tr("msg.blatt.neu", name=b.name))

    def blatt_duplizieren(self):
        """Duplicates the active sheet completely (model, layouts, blocks)."""
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        name = _LayoutNameDialog(self.root, tr("msg.blatt.duplizieren_titel"),
                                 p.kopie_name(p.blaetter[p.aktiv].name),
                                 label=tr("dlg.blatt.name")).result
        if name is None:
            return
        if not self._blatt_sichern():
            return
        try:
            b = p.blatt_duplizieren(p.aktiv, name)
            p.speichern()
        except (OSError, ProjektFehler) as e:
            messagebox.showerror(tr("msg.projekt.titel"),
                                 tr("msg.projekt.fehler", fehler=e),
                                 parent=self.root)
            return
        self._stacks_merken(p.blatt_pfad(p.aktiv))
        self._blatt_laden(p.blaetter.index(b))
        p.speichern()
        self.status.set(tr("msg.blatt.dupliziert", name=b.name))

    def _blatt_auswahl(self):
        """Indices of the sheets selected in the sheet list (at least the
        active sheet)."""
        p = self.projekt
        sl = getattr(self, "seitenleiste", None)
        idx = []
        if sl is not None and hasattr(sl, "auswahl_indizes"):
            try:
                idx = [i for i in sl.auswahl_indizes() if 0 <= i < len(p.blaetter)]
            except Exception:
                idx = []
        return idx or [p.aktiv]

    def blatt_loeschen(self):
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        idxs = sorted(set(self._blatt_auswahl()))
        if len(idxs) >= len(p.blaetter):
            messagebox.showinfo(tr("msg.projekt.titel"),
                                tr("msg.blatt.letztes"), parent=self.root)
            return
        if len(idxs) == 1:
            frage = tr("msg.blatt.loeschen_frage", nr=p.nummer(idxs[0]),
                       name=p.blaetter[idxs[0]].name)
        else:
            frage = tr("msg.blatt.loeschen_mehrere", n=len(idxs))
        if not messagebox.askyesno(tr("msg.projekt.titel"), frage,
                                   icon="warning", parent=self.root):
            return
        aktiv_blatt = p.blaetter[p.aktiv]
        aktiv_weg = p.aktiv in idxs
        for idx in reversed(idxs):
            b = p.blaetter[idx]
            self._undo_pro_blatt.pop(p.blatt_pfad(b), None)
            p.blatt_entfernen(idx)
        if aktiv_weg:
            neu = min(idxs[0], len(p.blaetter) - 1)
            self._blatt_laden(neu)
        else:                              # the open sheet stays loaded
            p.aktiv = p.blaetter.index(aktiv_blatt)
            self.seitenleiste.aktualisieren()
            self._update_titel()
        try:
            p.speichern()
        except OSError:
            pass

    def blatt_umbenennen(self, index=None):
        """Renames a sheet (default: the active one); possible at any time."""
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        if index is None or not (0 <= index < len(p.blaetter)):
            index = p.aktiv
        b = p.blaetter[index]
        orte = sorted({x.einbauort for x in p.blaetter if x.einbauort})
        standard_art = tr("rep.art.zeichnung")
        arten = [standard_art, tr("blatt.art.gestell"), tr("blatt.art.uebersicht"),
                 tr("blatt.art.layout")]
        arten += sorted({x.art for x in p.blaetter if x.art and x.art not in arten})
        res = BlattEigenschaftenDialog(
            self.root, tr("msg.blatt.umbenennen"), b.name, b.einbauort, orte,
            mit_ort=not b.bericht, art=b.art or standard_art,
            beschreibung=b.beschreibung, art_vorschlaege=arten).result
        if res is None:
            return
        name, ort, art, beschr = res
        if art in (tr("rep.art.zeichnung"), "Schaltplan", "Circuit diagram"):
            art = ""                      # default kind
        if not name:
            messagebox.showinfo(tr("msg.projekt.titel"),
                                tr("msg.blatt.name_leer"), parent=self.root)
            return
        if b.bericht:
            ort, art, beschr = b.einbauort, b.art, b.beschreibung
        if (name == b.name and ort == b.einbauort and art == b.art
                and beschr == b.beschreibung):
            return
        b.name = name
        if not b.bericht:
            b.einbauort, b.art, b.beschreibung = ort, art, beschr
        try:
            p.speichern()
        except OSError as e:
            messagebox.showerror(tr("msg.projekt.titel"),
                                 tr("msg.projekt.fehler", fehler=e),
                                 parent=self.root)
        self._titelfelder_aktualisieren()
        if getattr(self, "layouts", None):
            self.redraw()
        self.seitenleiste.aktualisieren()
        self._update_titel()

    def blatt_verschieben(self, delta):
        """Moves the selected sheets (one or several) up (-1) or down (+1)."""
        p = self.projekt
        if p is None:
            return
        idxs = sorted(set(self._blatt_auswahl()))
        n = len(p.blaetter)
        if (delta < 0 and idxs[0] == 0) or (delta > 0 and idxs[-1] == n - 1):
            return                         # the block is already at the end
        aktiv_blatt = p.blaetter[p.aktiv]
        gewaehlt = [p.blaetter[i] for i in idxs]
        for i in (idxs if delta < 0 else reversed(idxs)):
            p.blatt_verschieben(i, delta)
        p.aktiv = p.blaetter.index(aktiv_blatt)
        try:
            p.speichern()
        except OSError:
            pass
        self.seitenleiste.aktualisieren()
        if len(gewaehlt) > 1 and hasattr(self.seitenleiste, "auswahl_setzen"):
            self.seitenleiste.auswahl_setzen([p.blaetter.index(b) for b in gewaehlt])
        self._update_titel()

    # ========================================================
    # NEW: block attributes (function texts)
    # ========================================================
    def attdef_erstellen(self):
        """ATTDEF: define an attribute and place it in the model."""
        if self._ist_layout():
            self.status.set(("Bitte in die Modell-Ansicht wechseln."
                             if SPRACHE["aktuell"] == "de"
                             else "Please switch to model view."))
            return
        dlg = AttributDefinitionDialog(
            self.root, hoehe=self._zahl(self.text_hoehe, 3.5))
        if not dlg.result:
            return
        self._attdef_wartend = dlg.result
        self.letzter_punkt = None
        self._update_eingabe_hinweis()
        self.status.set(tr("msg.attdef.platzieren"))
        self.entry_eingabe.focus_set()

    def _attdef_platzieren(self, x, y):
        d = self._attdef_wartend
        if not d:
            return
        self._snapshot()
        daten = self._layer_daten()
        if "Schrift" in self.layers:
            daten["layer"] = "Schrift"
            daten["farbe"] = self.layers["Schrift"].farbe
        daten["eig_farbe"] = True
        daten["staerke"] = None
        el = AttributDefinition(
            x, y, None, d["hoehe"], 0.0, self.text_schriftart.get(),
            einfuegepunkt=d.get("einfuegepunkt"),
            tag=d["tag"], prompt=d["prompt"], wert=d["wert"],
            sichtbar=d["sichtbar"], **daten)
        self._ziel_liste().append(el)
        self._attdef_wartend = None
        self._clear_temp()
        self.redraw()
        self._update_eingabe_hinweis()
        self.status.set(tr("msg.attdef.gesetzt", tag=el.tag))

    def _attdef_bearbeiten(self, el):
        vor = {"tag": el.tag, "prompt": el.prompt, "wert": el.wert,
               "hoehe": el.hoehe, "sichtbar": el.sichtbar,
               "einfuegepunkt": el.einfuegepunkt}
        dlg = AttributDefinitionDialog(self.root, vorgabe=vor)
        if not dlg.result:
            return
        r = dlg.result
        self._snapshot()
        el.tag, el.prompt, el.wert = r["tag"], r["prompt"], r["wert"]
        el.hoehe, el.sichtbar = r["hoehe"], r["sichtbar"]
        el.einfuegepunkt = r["einfuegepunkt"]
        el.inhalt = "<" + el.tag + ">"
        self.redraw()

    def _attribute_abfragen(self, ref):
        """Prompts for the attribute values on insertion (if any).
        Cancelling keeps the default values."""
        aus = self._attr_ausschluss(ref)
        if not [ad for ad in ref.attribut_definitionen() if ad.tag not in aus]:
            return
        dlg = BlockAttributeDialog(self.root, ref, ausschliessen=aus)
        if dlg.result:
            ref.setze_attribute(dlg.result)
            ref.setze_ausgeblendet(dlg.ausgeblendet)
            m = ref.geraet_maske()
            if m is not None and dlg.rolle:
                m.rolle = dlg.rolle
            if m is not None and dlg.spiegel:
                if m.spiegel != dlg.spiegel:
                    ref.sp_dx = ref.sp_dy = 0.0
                m.spiegel = dlg.spiegel

    def attribute_bearbeiten(self, ref=None):
        """ATTEDIT: edit the attribute values of a selected block."""
        if ref is None:
            kandidaten = [e for e in self.auswahl
                          if isinstance(e, BlockReferenz)]
            if not kandidaten:
                self.status.set(tr("msg.attedit.keine_auswahl"))
                return
            mit = [e for e in kandidaten if e.attribut_definitionen()]
            if not mit:
                self.status.set(tr("msg.attedit.keine_attribute"))
                return
            ref = mit[0]
        dlg = BlockAttributeDialog(self.root, ref,
                                   ausschliessen=self._attr_ausschluss(ref))
        if dlg.result is None:
            return
        self._snapshot()
        ref.setze_attribute(dlg.result)
        ref.setze_ausgeblendet(dlg.ausgeblendet)
        m = ref.geraet_maske()
        if m is not None and dlg.rolle:
            m.rolle = dlg.rolle
        if m is not None and dlg.spiegel:
            if m.spiegel != dlg.spiegel:
                ref.sp_dx = ref.sp_dy = 0.0
            m.spiegel = dlg.spiegel
        self._geraete_aktualisieren()
        self.redraw()
        self.status.set(tr("msg.attedit.fertig", name=ref.block_name))

    # ========================================================
    # NEW: block files (*.katieblock)
    # ========================================================
    def _block_dateiordner(self):
        p = self.projekt
        if p is None:
            return None
        return p.bloecke_ordner if os.path.isdir(p.bloecke_ordner) else p.ordner

    def block_speichern_datei(self):
        """Saves a block as a separate file (like WBLOCK)."""
        d = None
        refs = [e for e in self.auswahl if isinstance(e, BlockReferenz)]
        if refs:
            d = self.block_bibliothek.get(refs[0].block_name)
            if d is None:
                d = BlockDefinition(refs[0].block_name, (0.0, 0.0),
                                    refs[0].elemente)
        elif len(self.block_bibliothek) > 0:
            name = _BlockAuswahlDialog(
                self.root, self.block_bibliothek,
                titel=tr("dlg.block.speichern.titel"),
                knopf=tr("dlg.block.speichern.knopf"),
                hinweis=tr("dlg.block.speichern.hinweis")).result
            if not name:
                return
            d = self.block_bibliothek.get(name)
        if d is None:
            messagebox.showinfo(tr("msg.blockdatei.titel"),
                                tr("msg.blockdatei.nichts"), parent=self.root)
            return
        kw = {}
        start = self._block_dateiordner()
        if start:
            kw["initialdir"] = start
        pfad = filedialog.asksaveasfilename(
            parent=self.root, title=tr("dlg.block.speichern.titel"),
            defaultextension=BLOCK_ENDUNG,
            initialfile=vorschlag_dateiname(d.name),
            filetypes=[(tr("msg.blockdatei.dateityp"), "*" + BLOCK_ENDUNG),
                       ("*.*", "*.*")], **kw)
        if not pfad:
            return
        try:
            block_speichern(pfad, d)
        except BlockDateiFehler as e:
            messagebox.showerror(
                tr("msg.blockdatei.titel"),
                tr("msg.blockdatei.fehler", pfad=pfad, fehler=e),
                parent=self.root)
            return
        self.status.set(tr("msg.blockdatei.gespeichert", name=d.name,
                           pfad=pfad))

    def block_laden_datei(self):
        """Loads one or more block files into the library."""
        kw = {}
        start = self._block_dateiordner()
        if start:
            kw["initialdir"] = start
        pfade = filedialog.askopenfilenames(
            parent=self.root, title=tr("menu.bloecke.laden"),
            filetypes=[(tr("msg.blockdatei.dateityp"), "*" + BLOCK_ENDUNG),
                       ("*.*", "*.*")], **kw)
        if not pfade:
            return
        geladen = []
        for pfad in pfade:
            try:
                d = block_laden(pfad, self._dict_zu_element)
            except Exception as e:
                messagebox.showerror(
                    tr("msg.blockdatei.titel"),
                    tr("msg.blockdatei.fehler", pfad=pfad, fehler=e),
                    parent=self.root)
                continue
            if d.name in self.block_bibliothek:
                i = 2
                while f"{d.name}_{i}" in self.block_bibliothek:
                    i += 1
                neu = f"{d.name}_{i}"
                antwort = messagebox.askyesnocancel(
                    tr("msg.blockdatei.titel"),
                    tr("msg.blockdatei.existiert", name=d.name, neu=neu),
                    parent=self.root)
                if antwort is None:
                    continue
                if antwort is False:
                    d.name = neu
            self.block_bibliothek.setze(d)
            geladen.append(d.name)
        if not geladen:
            return
        self.status.set(tr("msg.blockdatei.geladen", n=len(geladen),
                           namen=", ".join(geladen)))
        if (len(geladen) == 1 and not self._ist_layout()
                and messagebox.askyesno(
                    tr("msg.blockdatei.titel"),
                    tr("msg.blockdatei.einfuegen_frage", name=geladen[0]),
                    parent=self.root)):
            self._block_einfuege_name = geladen[0]
            self._warte_auf_blockpunkt = True
            self.letzter_punkt = None
            self._update_eingabe_hinweis()
            self.status.set(tr("msg.block.einfuegepunkt"))
            self.entry_eingabe.focus_set()

    # ========================================================
    # NEW (electrical): cross-reference targets
    # ========================================================
    def _qv_texte_blatt(self, pfad):
        """Cross-reference texts of a (non-active) sheet, with cache."""
        try:
            st = os.stat(pfad)
            key = (st.st_mtime_ns, st.st_size)
        except OSError:
            return []
        hit = self._qv_cache.get(pfad)
        if hit and hit[0] == key:
            return hit[1]
        try:
            with open(pfad, "r", encoding="utf-8") as f:
                texte = qv_texte_aus_blattdaten(json.load(f))
        except (OSError, ValueError):
            texte = []
        self._qv_cache[pfad] = (key, texte)
        return texte

    def _querverweise_aktualisieren(self):
        """Computes the target of all cross references of the current sheet."""
        if not any(isinstance(e, Querverweis) for e in self.elemente):
            return
        p = self.projekt
        andere, nr = {}, 1
        if p is not None:
            nr = p.aktiv + 1
            for i, b in enumerate(p.blaetter):
                if i != p.aktiv:
                    andere[i + 1] = self._qv_texte_blatt(p.blatt_pfad(i))
        querverweis_ziele(self.elemente, nr, andere)

    def sidebar_breite_merken(self, px):
        try:
            cfg = lade_konfiguration()
            cfg["sidebar_breite"] = int(px)
            speichere_konfiguration(cfg)
        except Exception as e:
            print(f"[KatieCAD] Konfiguration: {e}")


    # ========================================================
    # NEW (electrical): device references, pin/junction on wires,
    # junction, electrical mask, terminal
    # ========================================================
    def _geraete_blatt(self, pfad):
        """(per, role, ind) of all devices of a non-active sheet."""
        try:
            st = os.stat(pfad)
            key = (st.st_mtime_ns, st.st_size)
        except OSError:
            return []
        if not hasattr(self, "_ge_cache"):
            self._ge_cache = {}
        hit = self._ge_cache.get(pfad)
        if hit and hit[0] == key:
            return hit[1]
        try:
            with open(pfad, "r", encoding="utf-8") as f:
                res = geraete_aus_blattdaten(json.load(f))
        except (OSError, ValueError):
            res = []
        self._ge_cache[pfad] = (key, res)
        return res

    def _geraete_aktualisieren(self):
        eigene = geraete(self.elemente, 1 if self.projekt is None
                         else self.projekt.aktiv + 1)
        if not eigene:
            return
        p = self.projekt
        andere, nr = {}, 1
        if p is not None:
            nr = p.aktiv + 1
            for i in range(len(p.blaetter)):
                if i != p.aktiv:
                    andere[i + 1] = self._geraete_blatt(p.blatt_pfad(i))
        for g in eigene:
            g["blatt"] = nr
        geraete_referenzen(eigene, nr, andere)

    def _einrasten(self, neue):
        """Pins/junctions/terminals/devices placed on top interrupt the
        wires they lie on."""
        if self._ist_layout() or not neue:
            return 0
        zoom = self.view["zoom"] if self.view["zoom"] else 1.0
        tol = min(1.0, max(0.2, 3.0 / zoom))
        n = leitungen_einrasten(self._ziel_liste(), list(neue), tol)
        if n:
            self.status.set(tr("msg.leitung.eingerastet", n=n))
        return n

    def geraet_erzeugen(self):
        """Electrical > Device from selection: select mask + pins + symbol,
        choose the insertion point, set name and main/auxiliary device."""
        if self._ist_layout():
            self.status.set(tr("msg.modell_noetig"))
            return
        masken = [e for e in self.auswahl if isinstance(e, ElektroMaske)]
        if not masken:
            in_block = any(isinstance(e, BlockReferenz) and e.geraet_maske() is not None
                           for e in self.auswahl)
            self.status.set(tr("msg.geraet.maske_im_block" if in_block
                               else "msg.geraet.keine_maske"))
            return
        if len(masken) > 1:
            self.status.set(tr("msg.geraet.mehrere"))
            return
        self.block_erzeugen(geraet=True)

    def _auf_leitung_einrasten(self, x, y):
        """If (x,y) lies on a wire, it is projected onto it and the
        wire is split (a pin / junction was placed on it)."""
        liste = self._ziel_liste()
        tol = 6.0 / self.view["zoom"]
        hit = naechster_leitungspunkt(liste, x, y, tol)
        if hit is None:
            return x, y
        _l, px, py = hit
        leitung_teilen(liste, px, py)
        return px, py

    # Junction
    def _verbindung_starten(self):
        vor = self._vb_vorgabe or {"arme": [0, 90, 180], "punkt": True, "ausrichtung": 0}
        dlg = VerbindungDialog(self.root, vor)
        if dlg.result is None:
            self.aktives_werkzeug.set("auswahl")
            self._werkzeug_gewechselt()
            return
        self._vb_vorgabe = dlg.result
        self.status.set(tr("msg.verb.platzieren", art=len(dlg.result["arme"])))

    def _neue_verbindung(self, x, y):
        v = self._vb_vorgabe
        return Verbindung(x, y, ausrichtung=v.get("ausrichtung", 0),
                          arme=v["arme"], punkt=v["punkt"],
                          layer=self._elektro_layer(E_LINES))

    def _verbindung_platzieren(self, x, y):
        if not self._vb_vorgabe:
            return
        self._snapshot()
        x, y = self._auf_leitung_einrasten(x, y)
        self._ziel_liste().append(self._neue_verbindung(x, y))
        self.redraw()
        self.status.set(tr("msg.verb.gesetzt"))

    def _verbindung_bearbeiten(self, el):
        dlg = VerbindungDialog(self.root, {"arme": el.arme,
                                           "punkt": el.punkt,
                                           "ausrichtung": el.ausrichtung})
        if dlg.result is None:
            return
        liste = self._aktuelle_elemente_liste()
        vorher = vollstaendige_verbindungen(liste)
        self._snapshot()
        el.arme = Verbindung.arme_normieren(dlg.result["arme"])
        el.punkt = dlg.result["punkt"]
        el.ausrichtung = dlg.result["ausrichtung"]
        verbindungen_bereinigen(liste, vorher - {id(el)})
        self.redraw()

    # ---- Electrical mask / terminal
    def _maske_starten(self):
        self.status.set(tr("msg.maske.platzieren"))

    def _klemme_starten(self):
        self.status.set(tr("msg.klemme.platzieren",
                           name=self._kl_werte.get("NUM", "")))

    def _maske_platzieren(self, x, y):
        dlg = FestMaskeDialog(self.root, tr("dlg.maske.titel"),
                              ElektroMaske.FELDER, self._mk_werte,
                              rolle=self._mk_rolle,
                              hinweis=tr("dlg.maske.hinweis"),
                              spiegel=getattr(self, "_mk_spiegel", "liste"))
        if dlg.result is None:
            return
        self._mk_werte = dict(dlg.result["werte"])
        self._mk_rolle = dlg.result["rolle"]
        self._mk_spiegel = dlg.result["spiegel"] or "liste"
        self._snapshot()
        daten = self._layer_daten_fuer(E_DEVICES)
        daten["staerke"] = None
        self._ziel_liste().append(
            ElektroMaske(x, y, dlg.result["werte"], rolle=dlg.result["rolle"],
                         spiegel=getattr(self, "_mk_spiegel", "liste"), **daten))
        self.redraw()
        self.status.set(tr("msg.maske.gesetzt"))

    def _klemme_platzieren(self, x, y):
        vor = dict(self._kl_werte)
        dlg = FestMaskeDialog(self.root, tr("dlg.klemme.titel"),
                              Klemme.FELDER, vor,
                              hinweis=tr("dlg.klemme.hinweis"))
        if dlg.result is None:
            return
        w = dict(dlg.result["werte"])
        self._snapshot()
        daten = self._layer_daten_fuer(E_CLAMPS)
        daten["staerke"] = None
        kl = Klemme(x, y, w, **daten)
        self._ziel_liste().append(kl)
        n_ein = self._einrasten([kl])
        w["NUM"] = naechste_bezeichnung(w.get("NUM", ""))
        self._kl_werte = w
        self.redraw()
        if not n_ein:
            self.status.set(tr("msg.klemme.gesetzt"))

    def _feld_platzieren(self, x, y):
        dlg = KoordinatenfeldDialog(self.root, self._kf_werte)
        if dlg.result is None:
            return
        self._kf_werte = dict(dlg.result)
        self._snapshot()
        daten = self._layer_daten()
        daten["staerke"] = None
        self._ziel_liste().append(Koordinatenfeld(x, y, **dlg.result, **daten))
        self.aktives_werkzeug.set("auswahl")
        self._werkzeug_gewechselt()
        self.redraw()
        self.status.set(tr("msg.kf.gesetzt"))

    def _kabel_klick(self, x, y):
        if self._ist_layout():
            return
        p1 = self._kabel_p1
        if p1 is None:
            self._kabel_p1 = (x, y)
            self.status.set(tr("msg.kabel.ende"))
            return
        if x - p1[0] < 1.0:
            self.status.set(tr("msg.kabel.ende"))
            return
        dlg = FestMaskeDialog(self.root, tr("dlg.kabel.titel"), Kabel.FELDER,
                              self._kb_werte, hinweis=tr("dlg.kabel.hinweis"))
        if dlg.result is None:
            return
        w = dict(dlg.result["werte"])
        self._snapshot()
        daten = self._layer_daten_fuer(E_CABLE)
        daten["staerke"] = None
        self._ziel_liste().append(Kabel(p1[0], p1[1], w, laenge=x - p1[0], **daten))
        w["CAB"] = naechste_bezeichnung(w.get("CAB", ""))
        self._kb_werte = w
        self._kabel_p1 = None
        self._clear_temp()
        self.redraw()
        self.status.set(tr("msg.kabel.gesetzt"))

    def _kabel_bearbeiten(self, el):
        kreuz = el.adern_liste()
        zusatz = [(k, tr("dlg.kabel.ader", n=i + 1, abstand=k), n)
                  for i, (k, n) in enumerate(kreuz)]
        dlg = FestMaskeDialog(self.root, tr("dlg.kabel.titel"), Kabel.FELDER,
                              el.werte, hinweis=tr("dlg.kabel.hinweis"),
                              zusatz=zusatz)
        if dlg.result is None:
            return
        self._snapshot()
        el.setze_werte(dlg.result["werte"])
        neu = dict(el.adern)
        for (k, _t, _n) in zusatz:
            text = dlg.result["zusatz"].get(k, "").strip()
            if text:
                neu[k] = text
            else:
                neu.pop(k, None)
        el.adern = neu
        self.redraw()

    def _feld_bearbeiten(self, el):
        dlg = KoordinatenfeldDialog(self.root, {
            "spalten": el.spalten, "zeilen": el.zeilen, "breite": el.breite,
            "hoehe": el.hoehe, "raster": el.raster})
        if dlg.result is None:
            return
        self._snapshot()
        el.spalten, el.zeilen = dlg.result["spalten"], dlg.result["zeilen"]
        el.breite, el.hoehe = dlg.result["breite"], dlg.result["hoehe"]
        el.raster = dlg.result["raster"]
        self.redraw()

    def _fest_bearbeiten(self, el):
        ist_maske = isinstance(el, ElektroMaske)
        dlg = FestMaskeDialog(
            self.root,
            tr("dlg.maske.titel") if ist_maske else tr("dlg.klemme.titel"),
            el.FELDER, el.werte, rolle=el.rolle if ist_maske else None,
            spiegel=el.spiegel if ist_maske else None,
            hinweis=tr("dlg.maske.hinweis") if ist_maske
            else tr("dlg.klemme.hinweis"))
        if dlg.result is None:
            return
        self._snapshot()
        el.setze_werte(dlg.result["werte"])
        if ist_maske and dlg.result["rolle"]:
            el.rolle = dlg.result["rolle"]
            neu = dlg.result["spiegel"] or "liste"
            if neu != el.spiegel:
                el.sp_dx = el.sp_dy = 0.0
            el.spiegel = neu
        self._geraete_aktualisieren()
        self.redraw()

    def _geister_vorschau(self, event, wz):
        """Preview (ghost image) for junction / mask / terminal."""
        pt = self._eingabepunkt(event)
        if wz == "verbindung":
            if not self._vb_vorgabe:
                return False
            ghost = self._neue_verbindung(pt[0], pt[1])
        elif wz == "maske":
            ghost = ElektroMaske(pt[0], pt[1], self._mk_werte,
                                 rolle=self._mk_rolle,
                                 layer=self.aktiver_layer.get())
        elif wz == "koordinatenfeld":
            ghost = Koordinatenfeld(pt[0], pt[1], **self._kf_werte,
                                    layer=self.aktiver_layer.get())
        elif wz == "kabel":
            p1 = getattr(self, "_kabel_p1", None)
            if p1 is None:
                ghost = Kabel(pt[0], pt[1], self._kb_werte, laenge=10.0,
                              layer=self.aktiver_layer.get())
            else:
                ghost = Kabel(p1[0], p1[1], self._kb_werte,
                              laenge=max(1.0, pt[0] - p1[0]),
                              layer=self.aktiver_layer.get())
            kabel_kreuzungen(list(self.elemente) + [ghost])
        else:
            ghost = Klemme(pt[0], pt[1], self._kl_werte,
                           layer=self.aktiver_layer.get())
        self._clear_temp()
        for k in (ghost.aufgeloest(umriss=True) if wz == "koordinatenfeld"
                  else ghost.aufgeloest()):
            self._zeichne_element(k, tags=("vorschau",))
        self._fadenkreuz(event.x, event.y)
        return True

    def _werkzeug_setzen(self, name):
        self.aktives_werkzeug.set(name)
        self._werkzeug_gewechselt()

    # ========================================================
    # NEW (electrical): connection points
    # ========================================================
    def _vp_starten(self):
        """Configure the pin first (dialog), then place it by clicking."""
        self._vp_vorgabe = None
        dlg = VerbindungspunktDialog(
            self.root, naechste_bezeichnung(self._vp_letzte_bez),
            self._vp_text_anzeigen,
            richtungen=getattr(self, "_vp_richtungen", (0, 90, 180, 270)))
        if dlg.result is None:
            self.aktives_werkzeug.set("auswahl")
            self._werkzeug_gewechselt()
            return
        self._vp_vorgabe = dlg.result
        self._vp_richtungen = tuple(dlg.result.get("richtungen", (0, 90, 180, 270)))
        self._vp_text_anzeigen = dlg.result["sichtbar"]
        self.status.set(tr("msg.vp.platzieren", name=dlg.result["wert"] or "-"))

    def _vp_platzieren(self, x, y):
        if not getattr(self, "_vp_vorgabe", None):
            self._vp_starten()
            if not getattr(self, "_vp_vorgabe", None):
                return
        class _R:                      # result holder (keeps the code below)
            pass
        dlg = _R()
        dlg.result = dict(self._vp_vorgabe)
        self._vp_letzte_bez = dlg.result["wert"]
        # Next pin gets the next number automatically
        self._vp_vorgabe["wert"] = naechste_bezeichnung(dlg.result["wert"])
        self._snapshot()
        x, y = self._auf_leitung_einrasten(x, y)
        daten = self._layer_daten_fuer(E_PIN)
        daten["staerke"] = 0.25
        vp = Verbindungspunkt(x, y, None, Verbindungspunkt.TEXT_HOEHE, 0.0,
                              self.text_schriftart.get(), tag="VP",
                              wert=dlg.result["wert"],
                              sichtbar=dlg.result["sichtbar"],
                              richtungen=dlg.result.get("richtungen", (0, 90, 180, 270)), **daten)
        self._ziel_liste().append(vp)
        self.redraw()
        self.status.set(tr("msg.vp.gesetzt", name=dlg.result["wert"] or "-"))

    def _vp_bearbeiten(self, el):
        dlg = VerbindungspunktDialog(
            self.root, el.wert, el.sichtbar, titel=tr("msg.vp.bearbeiten"),
            richtungen=(el.richtungen if el.richtungen is not None
                        else (0, 90, 180, 270)))
        if dlg.result is None:
            return
        self._snapshot()
        el.richtungen = dlg.result.get("richtungen", el.richtungen)
        el.wert = dlg.result["wert"]
        el.inhalt = el.wert
        el.sichtbar = dlg.result["sichtbar"]
        self.redraw()

    def _el_sichtbar(self, el):
        l = self.layers.get(el.layer)
        return not (l and not l.sichtbar)

    def _vp_name(self, vp):
        einh = self._einh_faktor()
        return (f"{vp.wert or '-'}   ({vp.x / einh:.1f} / {vp.y / einh:.1f})")

    # ========================================================
    # NEW (electrical): wire
    # ========================================================
    def _leitung_starten(self):
        self._leitung_p1 = None
        self._leitung_dialog = VerbindungspunkteDialog(
            self.root, self._leitung_dialog_geschlossen)
        self.status.set(tr("msg.leitung.hinweis"))

    def _leitung_beenden(self):
        self._leitung_p1 = None
        dlg, self._leitung_dialog = self._leitung_dialog, None
        if dlg is not None:
            try:
                dlg.schliessen_still()
            except tk.TclError:
                pass

    def _leitung_dialog_geschlossen(self):
        """Window was closed by the user -> end the tool."""
        self._leitung_dialog = None
        self._leitung_p1 = None
        self.aktives_werkzeug.set("auswahl")
        self._werkzeug_gewechselt()

    def _leitung_klick(self, x, y):
        if self._ist_layout():
            return
        tol = 10.0 / self.view["zoom"]
        ap = naechster_anschluss(self.elemente, x, y, tol, self._el_sichtbar)
        if ap is None:
            self.status.set(tr("msg.vp.keiner"))
            return
        dlg = self._leitung_dialog
        if self._leitung_p1 is None:
            self._leitung_p1 = ap
            if dlg is not None:
                dlg.setze(ap.name, None)
            return
        p1 = self._leitung_p1
        if math.hypot(ap.x - p1.x, ap.y - p1.y) < 1e-9:
            self.status.set(tr("msg.vp.gleicher"))
            return
        if dlg is not None:
            dlg.setze(p1.name, ap.name)
        self._snapshot()
        self._ziel_liste().append(
            Leitung(p1.x, p1.y, ap.x, ap.y, layer=self._elektro_layer(E_LINES)))
        self._leitung_p1 = None
        self._clear_temp()
        self.redraw()
        if dlg is not None:
            dlg.setze(None, None)
        self.status.set(tr("msg.leitung.erstellt"))

    def _leitung_vorschau(self, event):
        x, y = self.px_to_mm(event.x, event.y)
        aps = anschlusspunkte(self.elemente, self._el_sichtbar)
        tol = 10.0 / self.view["zoom"]
        ap = None
        bd = None
        for a in aps:
            d = math.hypot(a.x - x, a.y - y)
            if d <= tol and (bd is None or d < bd):
                ap, bd = a, d
        self._clear_temp()
        c = self.canvas
        # discreetly mark all possible connection points
        for a in aps[:800]:
            q = self.mm_to_px(a.x, a.y)
            c.create_rectangle(q[0] - 3, q[1] - 3, q[0] + 3, q[1] + 3,
                               outline=FARBEN["gelb"] if "gelb" in FARBEN else FARBEN["cyan"],
                               width=1, tags="vorschau")
        p1 = self._leitung_p1
        if p1 is not None:
            a1 = self.mm_to_px(p1.x, p1.y)
            b1 = self.mm_to_px(ap.x, ap.y) if ap else (event.x, event.y)
            c.create_line(*a1, *b1, fill=LEITUNG_FARBE, dash=(5, 3), width=2,
                          tags="vorschau")
            c.create_oval(a1[0] - 7, a1[1] - 7, a1[0] + 7, a1[1] + 7,
                          outline=FARBEN["magenta"], width=2, tags="vorschau")
        if ap is not None:
            q = self.mm_to_px(ap.x, ap.y)
            c.create_oval(q[0] - 7, q[1] - 7, q[0] + 7, q[1] + 7,
                          outline=FARBEN["cyan"], width=2, tags="vorschau")
        self._fadenkreuz(event.x, event.y)
        self.status.set(tr("msg.leitung.hinweis")
                        + (f"   [{ap.name}]" if ap else ""))

    # ========================================================
    # NEW (electrical): cross reference
    # ========================================================
    def _querverweis_starten(self):
        vor = self._qv_vorgabe or {"art": "abgehend", "richtung": 0, "text": "L1"}
        dlg = QuerverweisDialog(self.root, vor)
        if dlg.result is None:
            self.aktives_werkzeug.set("auswahl")
            self._werkzeug_gewechselt()
            return
        self._qv_vorgabe = dlg.result
        self._qv_status()

    def _qv_status(self):
        v = self._qv_vorgabe
        self.status.set(tr("msg.qv.platzieren", text=v["text"],
                           art=tr("dlg.qv.art." + v["art"])))

    def _neuer_querverweis(self, x, y):
        v = self._qv_vorgabe
        daten = self._layer_daten_fuer(E_LINES)
        if "Schrift" in self.layers:
            daten["farbe"] = self.layers["Schrift"].farbe
        daten["eig_farbe"] = True
        daten["staerke"] = None
        return Querverweis(x, y, v["text"], v["art"], v["richtung"],
                           extern=v.get("extern", False),
                           text_hoehe=v.get("text_hoehe"),
                           ziel_hoehe=v.get("ziel_hoehe"), **daten)

    def _qv_platzieren(self, x, y):
        if not self._qv_vorgabe:
            return
        self._snapshot()
        qv = self._neuer_querverweis(x, y)
        self._ziel_liste().append(qv)
        self.redraw()
        self.status.set(tr("msg.qv.gesetzt", text=qv.text))

    def _qv_vorschau(self, event):
        pt = self._eingabepunkt(event)
        self._clear_temp()
        for k in self._neuer_querverweis(pt[0], pt[1]).aufgeloest():
            self._zeichne_element(k, tags=("vorschau",))
        self._fadenkreuz(event.x, event.y)
        self._qv_status()

    # ========================================================
    # Project check
    # ========================================================
    def _pruefung_ausfuehren(self):
        from katiecad.electrical.pruefung import pruefe
        infos, indizes = self._zeichnungsblaetter_einlesen()
        if infos is None:
            return []
        return pruefe([(i, inf.name, inf.elemente)
                       for i, inf in zip(indizes, infos)],
                      {i: inf.einbauort for i, inf in zip(indizes, infos)})

    def projekt_pruefen(self):
        if self.projekt is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        if not self._blatt_sichern():
            return
        befunde = self._pruefung_ausfuehren()
        PruefungDialog(self.root, befunde, self._zu_befund, self._pruefung_ausfuehren)

    def _zu_befund(self, b):
        if not self.blatt_wechseln(b.blatt):
            return
        self.root.update_idletasks()
        z = self.view["zoom"]
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        self.view["ox"] = cw / 2 - b.x * z
        self.view["oy"] = ch / 2 + b.y * z
        self.redraw()
        self._zeichne_raster()
        self.status.set(b.text)

    def _qv_bearbeiten(self, el):
        dlg = QuerverweisDialog(self.root, {"art": el.art,
                                            "richtung": el.richtung,
                                            "text": el.text,
                                            "extern": el.extern,
                                            "text_hoehe": el.hoehe_text(),
                                            "ziel_hoehe": el.hoehe_ziel(),
                                            "bearbeiten": True})
        if dlg.result is None:
            return
        self._snapshot()
        el.text_hoehe = dlg.result.get("text_hoehe") or el.text_hoehe
        el.ziel_hoehe = dlg.result.get("ziel_hoehe") or el.ziel_hoehe
        if dlg.result.get("reset"):
            el.texte_zuruecksetzen()
        el.extern = dlg.result.get("extern", False)
        el.art = dlg.result["art"]
        el.richtung = dlg.result["richtung"]
        el.text = dlg.result["text"]
        self.redraw()

    # ========================================================
    # NEW (electrical): print several sheets
    # ========================================================
    def _blatt_druckkontext(self, index):
        """Returns an object with the attributes that pdf_erzeugen needs."""
        p = self.projekt
        if index == p.aktiv:            # including unsaved changes
            return SimpleNamespace(
                elemente=self.elemente, layers=self.layers,
                layouts=self.layouts, aktives_layout=self.aktives_layout,
                _einh_faktor=self._einh_faktor, dezimalkomma=self.dezimalkomma,
                bericht=p.blaetter[index].bericht)
        try:
            with open(p.blatt_pfad(index), "r", encoding="utf-8") as f:
                daten = json.load(f)
            layers = self._standard_layers()
            for ld in daten.get("layers", []):
                layers[ld["name"]] = Layer(ld["name"],
                                           ld.get("farbe", "#c29bff"),
                                           ld.get("staerke", 0.35),
                                           ld.get("sichtbar", True))
            elemente = [el for el in (self._dict_zu_element(d)
                                      for d in daten.get("elemente", [])) if el]
            layouts = [Layout.from_dict(ld, self._dict_zu_element)
                       for ld in daten.get("layouts", [])]
            if not layouts:
                layouts = [Layout("Layout1", Layout.STANDARD_FORMAT, "#1c132d")]
            ak = int(daten.get("aktives_layout", 0))
            ansicht = daten.get("ansicht", "modell")
            if ansicht.startswith("layout:"):
                try:
                    ak = int(ansicht.split(":", 1)[1])
                except ValueError:
                    pass
            ak = max(0, min(ak, len(layouts) - 1))
            faktor = EINHEITEN.get(daten.get("einheit", "mm"), 1.0)
            komma = self.dezimalkomma.get()
            return SimpleNamespace(
                elemente=elemente, layers=layers, layouts=layouts,
                aktives_layout=ak, _einh_faktor=lambda: faktor,
                dezimalkomma=SimpleNamespace(get=lambda: komma),
                bericht=p.blaetter[index].bericht)
        except Exception as ex:
            print(f"[KatieCAD] Blatt {index + 1} nicht lesbar: {ex}")
            return None

    def _kontexte_vorbereiten(self, indizes):
        """Print contexts of the sheets `indizes` with all computed values
        (wires, cross references, device references, title blocks)."""
        p = self.projekt
        kontexte, nicht_lesbar = [], []
        for i in indizes:
            name = f"{p.nummer(i)} {p.blaetter[i].name}"
            ctx = self._blatt_druckkontext(i)
            if ctx is None:
                nicht_lesbar.append(name)
            else:
                kontexte.append((i, name, ctx))
        # Compute cross-reference targets across ALL sheets of the project
        texte = {}
        for j in range(len(p.blaetter)):
            if j == p.aktiv:
                texte[j + 1] = qv_texte_aus_elementen(self.elemente)
            else:
                texte[j + 1] = self._qv_texte_blatt(p.blatt_pfad(j))
        for i, _, ctx in kontexte:
            leitungen_automatisch(ctx.elemente)
            kabel_kreuzungen(ctx.elemente)
            querverweis_ziele(ctx.elemente, i + 1,
                              {n: t for n, t in texte.items() if n != i + 1})
            geraete_referenzen(
                geraete(ctx.elemente, i + 1), i + 1,
                {j + 1: (geraete_aus_blattdaten_liste(self, j))
                 for j in range(len(p.blaetter)) if j != i})
            for lay in getattr(ctx, "layouts", []):
                TB.refresh_fields(lay.elemente,
                                  TB.make_info(p, i, SPRACHE["aktuell"], lay.format))
        return kontexte, nicht_lesbar

    def projekt_dxf_exportieren(self):
        """The whole project as ONE DXF file (sheets side by side, 4 per row)."""
        de = SPRACHE["aktuell"] == "de"
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        if not EZDXF_VERFUEGBAR:
            messagebox.showwarning("DXF", ("ezdxf nicht installiert." if de
                                           else "ezdxf is not installed."))
            return
        pfad = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".dxf", initialdir=p.ordner,
            initialfile=p.name + ".dxf",
            filetypes=[("DXF", "*.dxf")])
        if not pfad:
            return
        try:
            from katiecad.fileio.dxf_projekt import (seiten_sammeln,
                                                     dxf_projekt_schreiben)
            kontexte, nicht_lesbar = self._kontexte_vorbereiten(
                list(range(len(p.blaetter))))
            seiten, uebersprungen = seiten_sammeln(
                [(n, c) for _, n, c in kontexte], False)
            if not seiten:
                raise ValueError(tr("msg.druckp.keine_seiten"))
            doc = ezdxf.new(dxfversion="R2010")
            dxf_projekt_schreiben(doc, seiten, spalten=4)
            doc.saveas(pfad)
        except Exception as ex:
            messagebox.showerror("DXF", (f"Fehler:\n{ex}" if de
                                         else f"Error:\n{ex}"), parent=self.root)
            return
        self.status.set(tr("msg.dxfp.fertig", n=len(seiten), pfad=pfad))
        rest = uebersprungen + nicht_lesbar
        if rest:
            messagebox.showinfo("DXF", tr("msg.druckp.uebersprungen",
                                          liste="\n".join(rest)), parent=self.root)

    def projekt_drucken(self):
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        dlg = ProjektDruckDialog(self.root, p)
        if not dlg.result:
            return
        aktion, indizes, quelle, farbig, rahmen = dlg.result
        kontexte, nicht_lesbar = self._kontexte_vorbereiten(indizes)
        try:
            pdf, uebersprungen = pdf_mehrseitig_erzeugen(
                [(n, c) for _, n, c in kontexte], quelle, farbig, rahmen)
        except Exception as ex:
            messagebox.showerror("PDF", str(ex), parent=self.root)
            return
        n_seiten = len(kontexte) - len(uebersprungen)
        if aktion == "pdf":
            pfad = filedialog.asksaveasfilename(
                parent=self.root, defaultextension=".pdf",
                initialdir=p.ordner, initialfile=p.name + ".pdf",
                filetypes=[("PDF", "*.pdf")])
            if not pfad:
                return
            with open(pfad, "wb") as f:
                f.write(pdf)
            self.status.set(tr("msg.druckp.pdf_gespeichert",
                               n=n_seiten, pfad=pfad))
        else:
            fd, pfad = tempfile.mkstemp(suffix=".pdf", prefix="katiecad_")
            with os.fdopen(fd, "wb") as f:
                f.write(pdf)
            pdf_senden(pfad, aktion == "druck")
            self.status.set(tr("msg.druckp.fertig", n=n_seiten))
        rest = uebersprungen + nicht_lesbar
        if rest:
            messagebox.showinfo(
                tr("dlg.druckp.titel"),
                tr("msg.druckp.uebersprungen", liste="\n".join(rest)),
                parent=self.root)

    # ========================================================
    # Documentation: cover sheet, table of contents, lists
    # ========================================================
    def _zeichnungsblaetter_einlesen(self):
        """[BlattInfo] of all drawing sheets (without report sheets) or
        None if a sheet is not readable."""
        p = self.projekt
        infos, indizes = [], []
        for i in p.zeichnungsblaetter():
            ctx = self._blatt_druckkontext(i)
            if ctx is None:
                messagebox.showerror(
                    tr("dlg.doku.titel"),
                    tr("msg.projekt.blatt_fehlt", pfad=p.blatt_pfad(i)),
                    parent=self.root)
                return None, None
            leitungen_automatisch(ctx.elemente)
            kabel_kreuzungen(ctx.elemente)
            infos.append(SEI.BlattInfo(p.blaetter[i].name, ctx.elemente,
                                       p.blaetter[i].beschreibung,
                                       p.blaetter[i].einbauort,
                                       p.blaetter[i].art))
            indizes.append(i)
        return infos, indizes

    def dokumentation_erzeugen(self):
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        if not self._blatt_sichern():
            return
        ordner = TB.template_folders(p.ordner)
        eintraege = [(tr("dlg.doku.ohne_vorlage"), None)]
        eintraege += [(n, pf) for n, pf in TB.list_templates(ordner)]
        cfg = lade_konfiguration()
        vorgabe = cfg.get("title_block")
        vorgabe = vorgabe if vorgabe and vorgabe != "builtin" else None
        dlg = DokumentationDialog(self.root, eintraege, p.doku, p.daten,
                                  p.name, vorlage_vorgabe=vorgabe)
        res = dlg.result
        if res is None:
            return
        if not res["berichte"]:
            self.status.set(tr("msg.doku.keine_auswahl"))
            return
        p.daten = {**p.daten, **res["daten"]}      # keeps the revision table
        p.doku = {"berichte": res["berichte"], "vorlage": res["vorlage"],
                  "klemmen_geraete": res["klemmen_geraete"],
                  "format": res.get("format", "a4")}
        vorlage = None
        try:
            if res["vorlage"]:
                els = TB.load_template(res["vorlage"], self._dict_zu_element)
                vorlage = SEI.Vorlage(os.path.splitext(
                    os.path.basename(res["vorlage"]))[0], els)
            infos, _idx = self._zeichnungsblaetter_einlesen()
            if infos is None:
                return
            programm = os.path.dirname(TB.program_folder())
            vorne, hinten = SEI.berichte_erzeugen(
                infos, p.name, p.daten, set(res["berichte"]), vorlage,
                SPRACHE["aktuell"], SEI.spalten_ordner(programm, p.ordner),
                klemmen_in_geraeteliste=res["klemmen_geraete"],
                format=SEI.format_name(res.get("format")))
            basis = self._leere_zeichnung_daten(einstellungen_uebernehmen=True)
            neu_aktiv = ANW.ins_projekt(p, vorne, hinten, basis,
                                        self._json_atomar_schreiben,
                                        bg_layout=self.bg_layout)
            p.speichern()
        except Exception as e:           # also unexpected errors: never fail silently
            import traceback
            traceback.print_exc()        # ends up in the program log
            messagebox.showerror(tr("dlg.doku.titel"),
                                 tr("msg.doku.fehler", fehler=f"{type(e).__name__}: {e}"),
                                 parent=self.root)
            return
        self._blatt_laden(neu_aktiv)
        p.speichern()
        self.status.set(tr("msg.doku.fertig", vorn=len(vorne), hinten=len(hinten)))

    def dokumentation_csv(self):
        """Device list, terminal diagram and cable plan as CSV files."""
        p = self.projekt
        if p is None:
            self.status.set(tr("msg.projekt.kein_projekt"))
            return
        if not self._blatt_sichern():
            return
        ziel = filedialog.askdirectory(parent=self.root, initialdir=p.ordner,
                                       title=tr("msg.doku.csv_titel"))
        if not ziel:
            return
        infos, indizes = self._zeichnungsblaetter_einlesen()
        if infos is None:
            return
        programm = os.path.dirname(TB.program_folder())
        try:
            tabellen = SEI.tabellen_fuer_export(
                [(k, b.elemente) for k, b in enumerate(infos)],
                lambda k: indizes[k] + 1,
                SEI.spalten_ordner(programm, p.ordner),
                bool(p.doku.get("klemmen_geraete", True)),
                {k: b.einbauort for k, b in enumerate(infos)})
            namen = {t: tr("rep." + t) for t in tabellen}
            pfade = ANW.csv_exportieren(ziel, tabellen, namen)
        except OSError as e:
            messagebox.showerror(tr("dlg.doku.titel"),
                                 tr("msg.doku.fehler", fehler=e), parent=self.root)
            return
        self.status.set(tr("msg.doku.csv_fertig", n=len(pfade), ordner=ziel))

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

    # --------------------------------------------------------
    # Block commands
    # --------------------------------------------------------
    def block_erzeugen(self, geraet=False):
        self._geraet_modus = bool(geraet)
        de = SPRACHE["aktuell"] == "de"
        if self._ist_layout():
            self.status.set(("Bitte in die Modell-Ansicht wechseln." if de
                             else "Please switch to model view."))
            return
        if not self.auswahl:
            self.status.set(("Bitte zuerst Objekte markieren, dann B drücken."
                             if de else
                             "Please select objects first, then press B."))
            return
        self._block_erzeuge_auswahl = list(self.auswahl)
        self.letzter_punkt = None
        self._update_eingabe_hinweis()
        self.status.set(tr("msg.block.basispunkt"))
        self.entry_eingabe.focus_set()

    def _block_erzeugen_fertig(self, basispunkt):
        try:
            self._block_erzeugen_fertig_intern(basispunkt)
        except Exception as ex:
            import traceback
            traceback.print_exc()
            self._block_erzeuge_auswahl = None
            self._geraet_modus = False
            self._clear_temp()
            self.redraw()
            self._update_eingabe_hinweis()
            messagebox.showerror(tr("msg.block.fehler.titel"),
                                 tr("msg.block.fehler", fehler=ex),
                                 parent=self.root)

    def _block_erzeugen_fertig_intern(self, basispunkt):
        de = SPRACHE["aktuell"] == "de"
        if self._block_erzeuge_auswahl is None:
            return
        auswahl = self._block_erzeuge_auswahl
        self._block_erzeuge_auswahl = None
        self._clear_temp()
        self.redraw()

        bx, by = basispunkt
        relativ = []
        for el in auswahl:
            k = self._dict_zu_element(el.to_dict())
            if k is None:
                continue
            k.verschieben(-bx, -by)
            relativ.append(k)
        if not relativ:
            self.status.set(("Block ist leer - abgebrochen." if de
                             else "Block is empty - cancelled."))
            self._update_eingabe_hinweis()
            return

        vorschlag = self._naechster_block_name()
        try:
            geom = vorschau_geometrie(BlockDefinition(vorschlag, (0.0, 0.0), relativ))
        except Exception as ex:
            print(f"[KatieCAD] Vorschau: {ex}")
            geom = None
        ergebnis = BlockSpeichernDialog(
            self.root, geom, vorschlag, self._block_speicherordner(),
            vorschlag_dateiname).result
        if not ergebnis:
            self.status.set(("Block-Erzeugen abgebrochen." if de
                             else "Block creation cancelled."))
            self._update_eingabe_hinweis()
            return
        name = ergebnis["name"]

        if getattr(self, "_geraet_modus", False):
            self._geraet_modus = False
            maske = next((k for k in relativ if isinstance(k, ElektroMaske)), None)
            if maske is not None:
                dr = FestMaskeDialog(self.root, tr("dlg.geraet.titel"), (),
                                     rolle=maske.rolle,
                                     hinweis=tr("dlg.maske.hinweis"),
                                     spiegel=maske.spiegel)
                if dr.result is None:
                    self.status.set(("Block-Erzeugen abgebrochen." if de
                                     else "Block creation cancelled."))
                    self._update_eingabe_hinweis()
                    return
                maske.rolle = dr.result["rolle"] or "haupt"
                maske.spiegel = dr.result["spiegel"] or "liste"

        vp_tags_eindeutig(relativ)
        definition = BlockDefinition(name, (0.0, 0.0), relativ)
        self.block_bibliothek.setze(definition, persistieren=False)
        gespeichert = None
        if ergebnis["ordner"]:
            pfad = os.path.join(ergebnis["ordner"], vorschlag_dateiname(name))
            try:
                block_speichern(pfad, definition)
                gespeichert = pfad
                self._config_setzen("block_ordner", ergebnis["ordner"])
            except BlockDateiFehler as ex:
                messagebox.showerror(
                    tr("msg.blockdatei.titel"),
                    tr("msg.blockdatei.fehler", pfad=pfad, fehler=ex),
                    parent=self.root)

        self._snapshot()
        liste = self._aktuelle_elemente_liste()
        for el in auswahl:
            if el in liste:
                liste.remove(el)

        ist_geraet = any(isinstance(k, ElektroMaske) for k in relativ)
        if ist_geraet:
            for k in relativ:
                if isinstance(k, Verbindungspunkt):
                    k.layer = E_DEVICES
        ref = BlockReferenz(bx, by, name, definition.elemente,
                            layer=(self._elektro_layer(E_DEVICES) if ist_geraet
                                   else self.aktiver_layer.get()),
                            farbe=self.zeichenfarbe,
                            linientyp=self.linientyp.get(),
                            eig_farbe=self.eigene_farbe.get(),
                            staerke=self._zahl(self.linienstaerke, 0.35))
        self._attribute_abfragen(ref)
        liste.append(ref)
        self.auswahl = [ref]
        self.redraw()
        self._update_eingabe_hinweis()
        if gespeichert:
            self.status.set(tr("msg.bs.gespeichert", name=name, pfad=gespeichert))
        else:
            self.status.set(tr("msg.block.erzeugt", name=name,
                               n=len(definition.elemente)))

    def _config_setzen(self, schluessel, wert):
        try:
            cfg = lade_konfiguration()
            cfg[schluessel] = wert
            speichere_konfiguration(cfg)
        except Exception as ex:
            print(f"[KatieCAD] Konfiguration: {ex}")

    def _block_speicherordner(self):
        """Suggestion for the save folder of new blocks."""
        p = self.projekt
        if p is not None:
            return p.bloecke_ordner
        try:
            cfg = lade_konfiguration()
        except Exception:
            cfg = {}
        return cfg.get("block_ordner") or standard_ordner()

    def _block_wurzeln(self):
        wurzeln = []
        p = self.projekt
        if p is not None:
            wurzeln.append((tr("dlg.bb.wurzel_projekt"), p.bloecke_ordner))
        try:
            cfg = lade_konfiguration()
        except Exception:
            cfg = {}
        eigene = cfg.get("block_ordner") or standard_ordner()
        try:
            os.makedirs(standard_ordner(), exist_ok=True)
        except OSError:
            pass
        if os.path.isdir(symbol_ordner()):
            wurzeln.append((tr("dlg.bb.wurzel_symbole"), symbol_ordner()))
        wurzeln.append((tr("dlg.bb.wurzel_eigene"), standard_ordner()))
        if os.path.normpath(eigene) != os.path.normpath(standard_ordner()):
            wurzeln.append((os.path.basename(eigene) or eigene, eigene))
        for pf in cfg.get("block_wurzeln", []) or []:
            if self._ist_symbolordner(pf):      # the library is listed only once
                continue
            if all(os.path.normpath(pf) != os.path.normpath(w[1]) for w in wurzeln):
                wurzeln.append((os.path.basename(pf) or pf, pf))
        return wurzeln

    @staticmethod
    def _ist_symbolordner(pfad):
        """True for the program's symbol library - also for a stale or second
        copy that was saved as an extra folder earlier (named 'symbols')."""
        n = os.path.normpath(pfad)
        return (n == os.path.normpath(symbol_ordner())
                or os.path.basename(n).lower() in ("symbols", "symbolbibliothek"))

    def _block_bibliothek_migrieren(self):
        """One-time: store the blocks of the old internal library as files."""
        try:
            cfg = lade_konfiguration()
        except Exception:
            return
        if cfg.get("block_migriert") or len(self.block_bibliothek) == 0:
            return
        ziel = standard_ordner()
        n = len(self.block_bibliothek)
        if messagebox.askyesno(tr("dlg.bb.titel"),
                               tr("dlg.bb.migration", n=n, ordner=ziel),
                               parent=self.root):
            for name in self.block_bibliothek.namen():
                d = self.block_bibliothek.get(name)
                pf = os.path.join(ziel, vorschlag_dateiname(name))
                if d is not None and not os.path.exists(pf):
                    try:
                        block_speichern(pf, d)
                    except BlockDateiFehler as ex:
                        print(f"[KatieCAD] Block-Migration: {ex}")
        self._config_setzen("block_migriert", True)

    def _naechster_block_name(self):
        i = 1
        try:
            ordner = self._block_speicherordner()
        except Exception:
            ordner = None

        def belegt(n):
            if n in self.block_bibliothek:
                return True
            return bool(ordner) and os.path.exists(
                os.path.join(ordner, vorschlag_dateiname(n)))
        while belegt(f"Block{i}"):
            i += 1
        return f"Block{i}"

    def block_einfuegen(self):
        de = SPRACHE["aktuell"] == "de"
        if self._ist_layout():
            self.status.set(("Bitte in die Modell-Ansicht wechseln." if de
                             else "Please switch to model view."))
            return
        self._block_bibliothek_migrieren()
        dlg = BlockBrowserDialog(
            self.root, self._block_wurzeln(),
            lambda pf: block_laden(pf, self._dict_zu_element))
        standard = {os.path.normpath(w[1]) for w in self._block_wurzeln()}
        neu = [w[1] for w in dlg.wurzeln]
        try:
            cfg = lade_konfiguration()
            cfg["block_wurzeln"] = [pf for pf in neu if os.path.normpath(pf) not in
                                    {os.path.normpath(standard_ordner())}
                                    and not self._ist_symbolordner(pf)
                                    and (self.projekt is None or os.path.normpath(pf)
                                         != os.path.normpath(self.projekt.bloecke_ordner))]
            speichere_konfiguration(cfg)
        except Exception as ex:
            print(f"[KatieCAD] Konfiguration: {ex}")
        if not dlg.result:
            return
        try:
            d = block_laden(dlg.result, self._dict_zu_element)
        except Exception as ex:
            messagebox.showerror(tr("msg.blockdatei.titel"),
                                 tr("msg.blockdatei.fehler", pfad=dlg.result, fehler=ex),
                                 parent=self.root)
            return
        self.block_bibliothek.setze(d, persistieren=False)
        name = d.name
        self._block_einfuege_name = name
        self._warte_auf_blockpunkt = True
        self.letzter_punkt = None
        self._update_eingabe_hinweis()
        self.status.set(tr("msg.block.einfuegepunkt"))
        self.entry_eingabe.focus_set()

    def _block_einfuegen_an(self, x, y):
        de = SPRACHE["aktuell"] == "de"
        if not self._block_einfuege_name:
            return
        d = self.block_bibliothek.get(self._block_einfuege_name)
        if d is None:
            self._warte_auf_blockpunkt = False
            self._block_einfuege_name = None
            self._update_eingabe_hinweis()
            return
        self._snapshot()
        ref = BlockReferenz(x, y, d.name, d.elemente,
                            layer=self._block_layer(d.elemente),
                            farbe=self.zeichenfarbe,
                            linientyp=self.linientyp.get(),
                            eig_farbe=self.eigene_farbe.get(),
                            staerke=self._zahl(self.linienstaerke, 0.35))
        self._attribute_abfragen(ref)
        self._ziel_liste().append(ref)
        self._einrasten([ref])
        self.auswahl = [ref]
        self._warte_auf_blockpunkt = False
        name = self._block_einfuege_name
        self._block_einfuege_name = None
        self._clear_temp()
        self.redraw()
        self._update_eingabe_hinweis()
        self.status.set(tr("msg.block.eingefuegt", name=name,
                           x=x / self._einh_faktor(),
                           y=y / self._einh_faktor()))

    def block_liste(self):
        de = SPRACHE["aktuell"] == "de"
        self.block_einfuegen()

    def block_aufloesen(self):
        """EXPLODE: break selected block references into their child elements.

        - Other selected elements stay unchanged (and selected).
        - The exploded children are selected after exploding.
        - If nothing is selected, a hint is shown.
        """
        de = SPRACHE["aktuell"] == "de"
        if self._ist_layout():
            self.status.set(("Bitte in die Modell-Ansicht wechseln." if de
                             else "Please switch to model view."))
            return
        if not self.auswahl:
            self.status.set(tr("msg.explode.keine_auswahl"))
            return

        bloecke = [e for e in self.auswahl if isinstance(e, BlockReferenz)]
        if not bloecke:
            self.status.set(tr("msg.explode.keine_bloecke"))
            return

        self._snapshot()
        liste = self._aktuelle_elemente_liste()
        neue_auswahl = []
        anzahl_kinder = 0

        # other selected elements stay selected
        for el in self.auswahl:
            if not isinstance(el, BlockReferenz):
                neue_auswahl.append(el)

        for ref in bloecke:
            if ref not in liste:
                continue
            idx = liste.index(ref)
            kinder = [deepcopy(k) for k in ref.aufgeloest()]
            liste.pop(idx)
            for k in kinder:
                liste.insert(idx, k)
                idx += 1
            neue_auswahl.extend(kinder)
            anzahl_kinder += len(kinder)

        self.auswahl = neue_auswahl
        self.redraw()
        self.status.set(tr("msg.explode.fertig",
                           bloecke=len(bloecke),
                           elemente=anzahl_kinder))

    # --------------------------------------------------------
    # Hatching
    # --------------------------------------------------------
    # --------------------------------------------------------
    # Find and replace
    # --------------------------------------------------------

    # --------------------------------------------------------
    # Match properties
    # --------------------------------------------------------
    _EIG_ALLGEMEIN = ("layer", "farbe", "eig_farbe", "linientyp", "staerke")

    def eigenschaften_uebertragen_start(self):
        """Pick a source object, then click the objects that receive its
        layer, colour, line type, weight (and text height / hatch pattern)."""
        de = SPRACHE["aktuell"] == "de"
        self._prop_pick = {"quelle": None, "anzahl": 0}
        if self.aktives_werkzeug.get() != "auswahl":
            self.aktives_werkzeug.set("auswahl")
            self._werkzeug_gewechselt()
        self.status.set("EIGENSCHAFTEN ÜBERTRAGEN: Quellobjekt anklicken "
                        "(ESC = abbrechen)." if de else
                        "MATCH PROPERTIES: click the source object (ESC = cancel).")

    def _eigenschaften_ende(self):
        if self._prop_pick is not None:
            n = self._prop_pick.get("anzahl", 0)
            self._prop_pick = None
            de = SPRACHE["aktuell"] == "de"
            self.status.set((f"Eigenschaften auf {n} Objekt(e) übertragen." if de
                             else f"Properties applied to {n} object(s)."))

    def _eigenschaften_anwenden(self, quelle, ziel):
        """Copies the properties of `quelle` onto `ziel`; returns True if
        something was applied."""
        if ziel is quelle:
            return False
        for k in self._EIG_ALLGEMEIN:
            if hasattr(quelle, k) and hasattr(ziel, k):
                setattr(ziel, k, getattr(quelle, k))
        if isinstance(quelle, Text) and isinstance(ziel, Text):
            ziel.hoehe, ziel.schriftart = quelle.hoehe, quelle.schriftart
        if isinstance(quelle, Schraffur) and isinstance(ziel, Schraffur):
            ziel.muster, ziel.abstand, ziel.winkel = (quelle.muster,
                                                       quelle.abstand, quelle.winkel)
        return True

    def _eigenschaften_klick(self, event):
        de = SPRACHE["aktuell"] == "de"
        x, y = self.px_to_mm(event.x, event.y)
        el = self._element_unter_maus(x, y, 8 / self.view["zoom"])
        if el is None:
            return
        pp = self._prop_pick
        if pp["quelle"] is None:
            pp["quelle"] = el
            self.auswahl = [el]
            self.redraw()
            self.status.set("Quelle gewählt. Jetzt die Zielobjekte anklicken "
                            "(ESC / Rechtsklick = fertig)." if de else
                            "Source picked. Now click the target objects "
                            "(ESC / right-click = done).")
            return
        self._snapshot()
        if self._eigenschaften_anwenden(pp["quelle"], el):
            pp["anzahl"] += 1
        self.redraw()

    def _schraffur_pick_start(self):
        """Like AutoCAD: no selection needed - click into a closed area."""
        de = SPRACHE["aktuell"] == "de"
        dlg = SchraffurDialog(self.root)
        if not dlg.result:
            return
        self._hatch_pick = dlg.result
        self.status.set("SCHRAFFUR: In einen umschlossenen Bereich klicken "
                        "(ESC / Rechtsklick = fertig)." if de else
                        "HATCH: click inside a closed area "
                        "(ESC / right-click = done).")

    def _schraffur_pick_ende(self):
        if getattr(self, "_hatch_pick", None):
            self._hatch_pick = None
            de = SPRACHE["aktuell"] == "de"
            self.status.set("Schraffur beendet." if de else "Hatch finished.")

    def _schraffur_klick(self, event):
        de = SPRACHE["aktuell"] == "de"
        x, y = self.px_to_mm(event.x, event.y)
        liste = self._aktuelle_elemente_liste()
        sichtbar = [e for e in liste
                    if isinstance(e, (Polylinie, Rechteck, Kreis, Linie, Bogen))
                    and not (self.layers.get(e.layer)
                             and not self.layers[e.layer].sichtbar)]
        r = bereich_an_punkt(sichtbar, (x, y), tol=0.05)
        if r is None:
            self.status.set("Kein geschlossener Bereich an dieser Stelle."
                            if de else "No closed area at this point.")
            return
        pts, quelle = r
        typ, abstand, winkel = self._hatch_pick
        self._snapshot()
        idx = min((liste.index(q) for q in [quelle] if q in liste),
                  default=len(liste))
        sch = Schraffur(pts, muster=typ, abstand=abstand, winkel=winkel,
                        layer=quelle.layer, farbe=quelle.farbe,
                        eig_farbe=quelle.eig_farbe)
        liste.insert(idx, sch)
        self.auswahl = [sch]
        self.redraw()
        self.status.set("Schraffur erstellt - weiteren Bereich anklicken "
                        "oder ESC." if de else
                        "Hatch created - click another area or ESC.")

    def schraffur_anwenden(self):
        """Hatch selection: circles, rectangles, closed polylines as well as
        closed contours formed from lines/arcs/open polylines (end points
        must meet)."""
        de = SPRACHE["aktuell"] == "de"
        kandidaten = [e for e in self.auswahl
                      if isinstance(e, (Polylinie, Rechteck, Kreis, Linie, Bogen))]
        konturen = konturen_aus_elementen(kandidaten, tol=0.05)
        if not konturen:
            self._schraffur_pick_start()
            return

        dlg = SchraffurDialog(self.root)
        if not dlg.result:
            return
        typ, abstand, winkel = dlg.result

        self._snapshot()
        liste = self._aktuelle_elemente_liste()
        neue_schraffuren = []
        for pts, quellen in konturen:
            erstes = quellen[0]
            idx = min((liste.index(q) for q in quellen if q in liste),
                      default=len(liste))
            schraffur = Schraffur(pts, muster=typ, abstand=abstand,
                                  winkel=winkel, layer=erstes.layer,
                                  farbe=erstes.farbe,
                                  eig_farbe=erstes.eig_farbe)
            liste.insert(idx, schraffur)
            neue_schraffuren.append(schraffur)

        self.auswahl = neue_schraffuren
        self.redraw()
        self.status.set(f"{len(neue_schraffuren)} " +
                        ("Schraffur(en) erstellt." if de else "hatch(es) created."))


# ============================================================
def _symbol_datei(name):
    """Finds KatieCAD.ico / KatieCAD.png: program folder, assets/ or the
    PyInstaller data folder."""
    basen = [_PROJEKT_WURZEL, os.path.join(_PROJEKT_WURZEL, "assets"),
             getattr(sys, "_MEIPASS", ""), os.path.dirname(sys.executable)]
    for b in basen:
        if b:
            pfad = os.path.join(b, name)
            if os.path.isfile(pfad):
                return pfad
    return None


def fenstersymbol_setzen(root):
    """Window / task bar icon: KatieCAD logo instead of the Tk feather."""
    if sys.platform.startswith("win"):
        try:                       # own task bar group -> own icon
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "KatieCAD.App")
        except Exception:
            pass
        ico = _symbol_datei("KatieCAD.ico")
        if ico:
            try:
                root.iconbitmap(default=ico)
                return
            except Exception:
                pass
    png = _symbol_datei("KatieCAD.png")
    if png:
        try:
            if PILLOW_VERFUEGBAR:
                bild = Image.open(png).convert("RGBA").resize(
                    (256, 256), Image.Resampling.LANCZOS)
                foto = ImageTk.PhotoImage(bild)
            else:
                foto = tk.PhotoImage(file=png)
            root.iconphoto(True, foto)
            root._katiecad_symbol = foto          # keep a reference
        except Exception as e:
            print(f"[KatieCAD] Fenstersymbol nicht gesetzt: {e}")


def main():
    from katiecad.common import logbuch
    from katiecad.common.config import konfig_ordner
    from katiecad.manifest import VERSION as _V
    logbuch.installieren(konfig_ordner(),
                         f"KatieCAD {_V} - {sys.platform} - Python {sys.version.split()[0]}"
                         f" - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    root = tk.Tk()
    fenstersymbol_setzen(root)
    app = CadApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
