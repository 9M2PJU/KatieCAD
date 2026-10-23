# -*- coding: utf-8 -*-
"""Creates a simple placeholder icon (assets/KatieCAD.png/.ico/.icns).
Replace the PNG by your own artwork and run this script again
(it only generates the missing formats if assets/KatieCAD.png exists)."""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
os.makedirs(OUT, exist_ok=True)
png = os.path.join(OUT, "KatieCAD.png")

if not os.path.exists(png):
    n = 1024
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, n - 40, n - 40), 180, fill=(28, 19, 45, 255))
    d.rounded_rectangle((40, 40, n - 40, n - 40), 180, outline=(194, 155, 255, 255), width=24)
    red = (255, 40, 40, 255)
    d.line((220, 512, 804, 512), fill=red, width=44)      # wire
    d.line((512, 220, 512, 804), fill=red, width=44)
    d.ellipse((512 - 90, 512 - 90, 512 + 90, 512 + 90), fill=red)   # junction dot
    for (x, y) in ((220, 512), (804, 512), (512, 220), (512, 804)):
        d.ellipse((x - 40, y - 40, x + 40, y + 40), fill=(194, 155, 255, 255))
    im.save(png)

im = Image.open(png).convert("RGBA")
im.save(os.path.join(OUT, "KatieCAD.ico"),
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
try:
    im.resize((1024, 1024)).save(os.path.join(OUT, "KatieCAD.icns"))
except Exception as e:                      # icns is only needed on macOS
    print("icns skipped:", e)
print("icons written to", OUT)
