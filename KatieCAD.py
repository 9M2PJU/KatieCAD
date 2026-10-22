# KatieCAD.py - Einstiegspunkt
import os
import sys
import tkinter as tk


# ---------------------------------------------------------------------------
# 1) Windows: eigene App-ID für die Taskleiste setzen
#    Muss VOR der Erzeugung des Tk-Fensters passieren, sonst gruppiert
#    Windows das Icon unter "python.exe" statt unter KatieCAD.
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "com.merecete.katiecad"
    )


# ---------------------------------------------------------------------------
# 2) Pfad zur Icon-Datei ermitteln
#    - Im Skript:  neben dieser .py-Datei
#    - In der EXE:  im temporären Entpackordner _MEIPASS
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    base_path = sys._MEIPASS  # type: ignore[attr-defined]
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

icon_path = os.path.join(base_path, "KatieCAD.ico")


# ---------------------------------------------------------------------------
# 3) Tk patchen, damit jedes Fenster automatisch das Icon bekommt
#    (katiecad_app.py muss dafür nicht verändert werden)
# ---------------------------------------------------------------------------
_original_tk_init = tk.Tk.__init__

def _tk_init_with_icon(self, *args, **kwargs):
    _original_tk_init(self, *args, **kwargs)
    try:
        self.iconbitmap(default=icon_path)
    except Exception:
        # Falls die ICO-Datei fehlt oder kein passendes Format hat,
        # soll die Anwendung trotzdem starten.
        pass

tk.Tk.__init__ = _tk_init_with_icon


# ---------------------------------------------------------------------------
# 4) Erst jetzt die eigentliche Anwendung starten
# ---------------------------------------------------------------------------
from katiecad_app import main

if __name__ == "__main__":
    main()
