# -*- coding: utf-8 -*-
"""
katiecad_manifest.py - Zentrale Liste aller Module + Version.
Dient als Anker fuer neue Chats: pruefen, ob alle Dateien da sind.
"""

VERSION = "0.2.0"

MODULE = {
    "katiecad.py":           "Einstiegspunkt",
    "katiecad_app.py":       "CadApp: UI, Events, Werkzeuge, State",
    "katiecad_core.py":      "Datenmodell, Geometrie, PDF-Writer",
    "katiecad_i18n.py":      "UI-Texte DE/EN",
    "katiecad_dialogs.py":   "Alle Dialoge + Lizenzfenster",
    "katiecad_pdf.py":       "PDF-Ausgabe aus Modell/Layout",
}


def fehlende_module():
    """Gibt eine Liste der in MODULE gelisteten, aber nicht importierbaren
    Dateien zurueck. Nuetzlich fuer einen Selbstcheck beim Start."""
    import importlib.util
    fehlend = []
    for name in MODULE:
        mod = name[:-3] if name.endswith(".py") else name
        if importlib.util.find_spec(mod) is None:
            fehlend.append(name)
    return fehlend
