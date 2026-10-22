# -*- coding: utf-8 -*-
"""
katiecad_bloecke.py - Blockdefinitionen als eigene Dateien (*.katieblock).
Enthaelt KEIN Tkinter.

Dateiformat (JSON):
    {"format": "katiecad-block", "version": 1, "block": {<BlockDefinition>}}

Die Definition enthaelt die Elemente in lokalen Koordinaten inkl.
Attributdefinitionen (AttributDefinition), siehe katiecad_core.
"""

import json
import os

from katiecad_core import BlockDefinition
from katiecad_projekt import _UNGUELTIG, BLOCK_ENDUNG

FORMAT_KENNUNG = "katiecad-block"
FORMAT_VERSION = 1


class BlockDateiFehler(Exception):
    pass


def vorschlag_dateiname(blockname):
    """Dateiname (ohne Ordner) passend zum Blocknamen."""
    n = _UNGUELTIG.sub("_", (blockname or "Block").strip()) or "Block"
    return n.rstrip(". ") + BLOCK_ENDUNG


def block_speichern(pfad, definition):
    daten = {"format": FORMAT_KENNUNG, "version": FORMAT_VERSION,
             "block": definition.to_dict()}
    try:
        os.makedirs(os.path.dirname(os.path.abspath(pfad)), exist_ok=True)
        tmp = pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(daten, f, indent=2, ensure_ascii=False)
        os.replace(tmp, pfad)
    except OSError as e:
        raise BlockDateiFehler(str(e))


def block_laden(pfad, element_factory):
    """Liest eine Blockdatei und gibt eine BlockDefinition zurueck."""
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            daten = json.load(f)
    except (OSError, ValueError) as e:
        raise BlockDateiFehler(str(e))
    if not isinstance(daten, dict):
        raise BlockDateiFehler("kein_block")
    if daten.get("format") == FORMAT_KENNUNG:
        bd = daten.get("block")
    elif "elemente" in daten and "name" in daten:   # nackte Definition
        bd = daten
    else:
        raise BlockDateiFehler("kein_block")
    if not isinstance(bd, dict):
        raise BlockDateiFehler("kein_block")
    d = BlockDefinition.from_dict(bd, element_factory)
    if not d.elemente:
        raise BlockDateiFehler("leer")
    return d
