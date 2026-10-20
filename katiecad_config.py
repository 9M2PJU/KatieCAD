# -*- coding: utf-8 -*-
"""
katiecad_config.py - Persistente Anwender-Einstellungen (z. B. Sprache).
Speichert in einem benutzerspezifischen Konfigverzeichnis:

    Windows:  %APPDATA%\\KatieCAD\\config.json
    macOS:    ~/Library/Application Support/KatieCAD/config.json
    Linux:    $XDG_CONFIG_HOME/KatieCAD/config.json
              (meist ~/.config/KatieCAD/config.json)

Fehlertolerant: fehlende oder kaputte Dateien führen still zum
Standardwert (Englisch).
"""

import json
import os
import sys

KONFIG_DATEI = "config.json"
STANDARD_SPRACHE = "en"                 # Erststart: Englisch
_UNTERSTUETZTE_SPRACHEN = ("de", "en")


def _konfig_verzeichnis():
    """Liefert ein plattformgerechtes Konfigverzeichnis."""
    if sys.platform.startswith("win"):
        basis = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(basis, "KatieCAD")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/KatieCAD")
    basis = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(basis, "KatieCAD")


def konfig_pfad():
    """Vollständiger Pfad zur Konfigurationsdatei."""
    return os.path.join(_konfig_verzeichnis(), KONFIG_DATEI)


def lade_konfiguration():
    """Gibt ein dict zurück. Fehlertolerant (immer mit gültiger 'sprache')."""
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
    """Schreibt die Konfiguration atomar. Fehler werden leise geloggt."""
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
    """Speichert nur den Sprachschlüssel; andere Felder bleiben erhalten."""
    if sprache not in _UNTERSTUETZTE_SPRACHEN:
        return
    daten = lade_konfiguration()
    daten["sprache"] = sprache
    speichere_konfiguration(daten)
