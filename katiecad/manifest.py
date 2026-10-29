# -*- coding: utf-8 -*-
"""
katiecad/manifest.py - Central list of all modules + version.
Used for a start-up self-check: are all modules present?
"""

VERSION = "1.1.1"

MODULE = {
    "katiecad.ui.app":            "CadApp: UI, events, tools, state, main()",
    "katiecad.ui.dialogs":        "All dialogs + licence window",
    "katiecad.ui.sidebar":        "Side bar: undo/redo + sheet list (resizable)",
    "katiecad.ui.widgets":        "Platform-independent buttons / colour swatches (macOS-safe)",
    "katiecad.model.core":        "Data model, geometry, electrical elements, PDF writer",
    "katiecad.model.project":     "Project management (folder, sheet list, *.katieprj)",
    "katiecad.model.titleblock": "Title block templates (title_blocks/), frame geometry, automatic fields",
    "katiecad.model.blocks":      "Block / device files (*.katieblock) read/write",
    "katiecad.electrical.logic":  "Electrical logic: cross references, device references, wires",
    "katiecad.fileio.pdf":        "PDF output from model/layout",
    "katiecad.fileio.cad_import": "DXF/DWG import (ezdxf, ODA File Converter)",
    "katiecad.common.i18n":       "UI texts DE/EN",
    "katiecad.common.config":     "Persistent user settings (language)",
}


def fehlende_module():
    """Returns the modules listed in MODULE that cannot be imported.
    Useful for a self-check at start-up."""
    import importlib.util
    fehlend = []
    for name in MODULE:
        try:
            if importlib.util.find_spec(name) is None:
                fehlend.append(name)
        except (ImportError, ValueError):
            fehlend.append(name)
    return fehlend
