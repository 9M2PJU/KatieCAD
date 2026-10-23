# -*- coding: utf-8 -*-
"""Derives the missing icon formats from the KatieCAD logo in the main
folder (KatieCAD.png; KatieCAD.ico is used as it is when present).
Writes build/KatieCAD.icns (macOS) and, if no KatieCAD.ico exists,
build/KatieCAD.ico."""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build")
os.makedirs(OUT, exist_ok=True)
png = os.path.join(ROOT, "KatieCAD.png")
if not os.path.isfile(png):
    raise SystemExit("KatieCAD.png not found in " + ROOT)

im = Image.open(png).convert("RGBA")
if not os.path.isfile(os.path.join(ROOT, "KatieCAD.ico")):
    im.save(os.path.join(OUT, "KatieCAD.ico"),
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
try:
    im.resize((1024, 1024)).save(os.path.join(OUT, "KatieCAD.icns"))
except Exception as e:                      # icns is only needed on macOS
    print("icns skipped:", e)
print("icons written to", OUT)
