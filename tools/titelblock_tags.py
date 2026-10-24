# -*- coding: utf-8 -*-
"""Lists the fields (attribute tags) of a title block template and shows which
ones KatieCAD fills in automatically.

Usage (inside the repository folder):
    python tools/titelblock_tags.py title_blocks/MeinSchriftkopf.cadjson
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from katiecad.model import titleblock as TB   # noqa: E402


def finde(obj, out):
    if isinstance(obj, dict):
        if "tag" in obj and "prompt" in obj:
            out.append((obj.get("tag"), obj.get("prompt"),
                        round(float(obj.get("x", 0)), 1),
                        round(float(obj.get("y", 0)), 1)))
        for v in obj.values():
            finde(v, out)
    elif isinstance(obj, list):
        for v in obj:
            finde(v, out)


with open(sys.argv[1], "r", encoding="utf-8") as f:
    daten = json.load(f)
felder = []
finde(daten, felder)
felder.sort(key=lambda t: (-t[3], t[2]))        # top to bottom, left to right
print("%-24s %-10s %s" % ("Tag", "Auto?", "Position x/y (mm)"))
for tag, prompt, x, y in felder:
    print("%-24s %-10s %s / %s" % (tag, "ja" if TB.is_auto_tag(tag) else "NEIN", x, y))
