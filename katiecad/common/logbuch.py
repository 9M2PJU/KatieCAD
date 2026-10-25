# -*- coding: utf-8 -*-
"""
katiecad/common/logbuch.py - program log (NO Tkinter).

Records everything the program prints (stdout/stderr, e.g. "[KatieCAD] ...",
load errors, tracebacks) with a time stamp, so that it can be shown in the
info window - even in the packaged program without a terminal.
"""
import sys
import time
import threading
from collections import deque

MAX_ZEILEN = 2000
_zeilen = deque(maxlen=MAX_ZEILEN)
_lock = threading.Lock()
_installiert = False
_datei = None
_pfad = None
DATEINAME = "katiecad-log.txt"


def pfad():
    """Path of the current log file (or None)."""
    return _pfad


class _Tee:
    def __init__(self, original, kanal):
        self._orig, self._kanal, self._rest = original, kanal, ""

    def write(self, s):
        try:
            if self._orig is not None:
                self._orig.write(s)
        except Exception:
            pass
        try:
            self._rest += s
            while "\n" in self._rest:
                zeile, self._rest = self._rest.split("\n", 1)
                if zeile.strip():
                    eintragen(zeile, self._kanal)
        except Exception:
            pass
        return len(s)

    def flush(self):
        try:
            if self._orig is not None:
                self._orig.flush()
        except Exception:
            pass

    def isatty(self):
        return False

    encoding = "utf-8"

    def __getattr__(self, name):
        return getattr(self._orig, name)


def eintragen(text, kanal="info"):
    with _lock:
        t = time.strftime("%H:%M:%S")
        _zeilen.append((t, kanal, str(text)))
        if _datei is not None:
            try:
                _datei.write(f"{t}  {'!' if kanal == 'fehler' else ' '}  {text}\n")
                _datei.flush()
            except Exception:
                pass


def _datei_oeffnen(verzeichnis, kopf):
    """Opens the log file of this session (the previous one becomes .old)."""
    global _datei, _pfad
    import os
    try:
        os.makedirs(verzeichnis, exist_ok=True)
        pf = os.path.join(verzeichnis, DATEINAME)
        if os.path.exists(pf):
            try:
                os.replace(pf, pf + ".old")
            except OSError:
                pass
        _datei = open(pf, "w", encoding="utf-8")
        _pfad = pf
        _datei.write(kopf + "\n" + "-" * 60 + "\n")
        _datei.flush()
    except Exception:
        _datei = None


def installieren(verzeichnis=None, kopf="KatieCAD"):
    """Mirrors stdout/stderr into the log (once) and, if a directory is
    given, into a log file there."""
    global _installiert
    if _installiert:
        return
    _installiert = True
    if verzeichnis:
        _datei_oeffnen(verzeichnis, kopf)
    sys.stdout = _Tee(sys.stdout, "info")
    sys.stderr = _Tee(sys.stderr, "fehler")


def text():
    with _lock:
        return "\n".join(f"{t}  {'!' if k == 'fehler' else ' '}  {z}"
                         for t, k, z in _zeilen)


def anzahl_fehler():
    with _lock:
        return sum(1 for _t, k, _z in _zeilen if k == "fehler")


def leeren():
    with _lock:
        _zeilen.clear()
