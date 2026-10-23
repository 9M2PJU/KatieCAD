# -*- coding: utf-8 -*-
"""
katiecad/common/config.py - Persistent user settings (e.g. language).
Stores them in a user-specific configuration directory:

    Windows:  %APPDATA%\\KatieCAD\\config.json
    macOS:    ~/Library/Application Support/KatieCAD/config.json
    Linux:    $XDG_CONFIG_HOME/KatieCAD/config.json
              (usually ~/.config/KatieCAD/config.json)

Fault tolerant: missing or broken files silently fall back to the
default value (English).
"""

import json
import os
import sys

KONFIG_DATEI = "config.json"
STANDARD_SPRACHE = "en"                 # First start: English
_UNTERSTUETZTE_SPRACHEN = ("de", "en")


def _konfig_verzeichnis():
    """Returns a platform-appropriate configuration directory."""
    if sys.platform.startswith("win"):
        basis = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(basis, "KatieCAD")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/KatieCAD")
    basis = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(basis, "KatieCAD")


def konfig_pfad():
    """Full path to the configuration file."""
    return os.path.join(_konfig_verzeichnis(), KONFIG_DATEI)


def lade_konfiguration():
    """Returns a dict. Fault tolerant (always with a valid 'sprache')."""
    pfad = konfig_pfad()
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            daten = json.load(f)
        if not isinstance(daten, dict):
            daten = {}
    except (OSError, ValueError):
        daten = {}
    sprache = daten.get("sprache")
    if sprache not in _UNTERSTUETZTE_SPRACHEN:
        sprache = STANDARD_SPRACHE
    daten["sprache"] = sprache
    return daten


def speichere_konfiguration(daten):
    """Writes the configuration atomically. Errors are logged quietly."""
    pfad = konfig_pfad()
    try:
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        tmp = pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(daten, f, indent=2, ensure_ascii=False)
        os.replace(tmp, pfad)
    except OSError as e:
        print(f"[KatieCAD] Konfiguration konnte nicht gespeichert werden: {e}")


def speichere_sprache(sprache):
    """Stores only the language key; other fields are preserved."""
    if sprache not in _UNTERSTUETZTE_SPRACHEN:
        return
    daten = lade_konfiguration()
    daten["sprache"] = sprache
    speichere_konfiguration(daten)
