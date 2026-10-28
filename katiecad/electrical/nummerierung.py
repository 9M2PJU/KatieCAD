# -*- coding: utf-8 -*-
"""
katiecad/electrical/nummerierung.py - Automatic device numbering (MIT, no Tk).

Devices whose designation (IND) is only a prefix without a number
('-K', 'K', '-K?') get the next free number: -K1, -K2 ... The numbers
continue after the highest number that already exists in the whole
project. Only main symbols (role "haupt") are numbered; auxiliary parts
are matched to their main symbol by the identical designation and are
not touched.

Works on element objects (open sheet) and on the plain dicts of the JSON
sheet files (other sheets).
"""

import re

_ZAHL_AM_ENDE = re.compile(r"^(.*?)(\d+)$")


def _typ(el):
    return el.get("typ") if isinstance(el, dict) else getattr(el, "typ", None)


def _get(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def geraete_felder(el):
    """-> (holder, key, rolle, x, y) of the IND field of a device or None."""
    t = _typ(el)
    if t == "maske":
        werte = _get(el, "werte")
        if isinstance(werte, dict) and "IND" in werte:
            return (werte, "IND", _get(el, "rolle", "haupt"),
                    _get(el, "x", 0.0), _get(el, "y", 0.0))
    elif t == "block":
        attr = _get(el, "attribute")
        if isinstance(attr, dict) and "IND" in attr:
            if isinstance(el, dict):
                maske = next((k for k in el.get("elemente", []) or []
                              if isinstance(k, dict) and k.get("typ") == "maske"), None)
                rolle = maske.get("rolle", "haupt") if maske else None
            else:
                m = el.geraet_maske() if hasattr(el, "geraet_maske") else None
                rolle = m.rolle if m is not None else None
            if rolle is not None:
                return (attr, "IND", rolle, _get(el, "x", 0.0), _get(el, "y", 0.0))
    return None


def zerlegen(ind):
    """'-K12' -> ('-K', 12);  '-K' / '-K?' -> ('-K', None);  '' -> (None, None)"""
    s = str(ind or "").strip()
    if not s or s.upper() == "IND":      # empty or the field name of the template
        return None, None
    m = _ZAHL_AM_ENDE.match(s)
    if m:
        return m.group(1), int(m.group(2))
    return s.rstrip("?*").strip() or None, None


def plan(blaetter, ziel_blaetter=None, start=1):
    """Computes the new designations.

    blaetter:      [(blatt, elemente)] in project order (all sheets)
    ziel_blaetter: set of sheets to be numbered (None = all)
    -> (aenderungen, ohne_praefix): aenderungen = [(holder, key, alt, neu,
    blatt)], ohne_praefix = number of main symbols with an empty IND."""
    hoechste = {}
    offen = []                           # (blatt, -y, x, holder, key, praefix)
    ohne = 0
    for blatt, elemente in blaetter:
        for el in elemente:
            f = geraete_felder(el)
            if f is None:
                continue
            holder, key, rolle, x, y = f
            wert = holder.get(key, "")
            praefix, nr = zerlegen(wert)
            if praefix is None:
                if rolle == "haupt" and (ziel_blaetter is None or blatt in ziel_blaetter):
                    ohne += 1
                continue
            if nr is not None:
                hoechste[praefix] = max(hoechste.get(praefix, start - 1), nr)
            elif rolle == "haupt" and (ziel_blaetter is None or blatt in ziel_blaetter):
                try:
                    yy, xx = -float(y), float(x)
                except (TypeError, ValueError):
                    yy, xx = 0.0, 0.0
                offen.append((blatt, yy, xx, holder, key, praefix))
    order = {b: i for i, (b, _e) in enumerate(blaetter)}
    offen.sort(key=lambda o: (order.get(o[0], 0), round(o[1], 1), o[2]))
    aenderungen = []
    for blatt, _y, _x, holder, key, praefix in offen:
        n = hoechste.get(praefix, start - 1) + 1
        hoechste[praefix] = n
        aenderungen.append((holder, key, holder.get(key, ""), f"{praefix}{n}", blatt))
    return aenderungen, ohne


def anwenden(aenderungen):
    for holder, key, _alt, neu, _blatt in aenderungen:
        holder[key] = neu
    return len(aenderungen)
