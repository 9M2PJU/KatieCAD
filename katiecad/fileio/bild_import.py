# -*- coding: utf-8 -*-
"""
katiecad/fileio/bild_import.py - Read raster images for the Bild element
(NO Tkinter). Uses Pillow (HPND licence).

The image is stored INSIDE the drawing (base64), so drawings stay
self-contained and can be passed on. Large images are reduced to
MAX_SEITE pixels on the longer side; images without transparency are
stored as JPEG, others as PNG.
"""

import base64
import io

try:
    from PIL import Image
    PIL_OK = True
except ImportError:                                    # pragma: no cover
    Image = None
    PIL_OK = False

MAX_SEITE = 2400
ENDUNGEN = "*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp"


def lade_bild(pfad, max_seite=MAX_SEITE):
    """-> dict(daten, format, pw, ph) for Bild(...). Raises RuntimeError."""
    if not PIL_OK:
        raise RuntimeError("Pillow is not installed:  pip install Pillow")
    try:
        im = Image.open(pfad)
        im.load()
    except Exception as e:
        raise RuntimeError(f"The image could not be read: {e}")
    hat_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
    im = im.convert("RGBA" if hat_alpha else "RGB")
    if max(im.size) > max_seite:
        f = max_seite / float(max(im.size))
        im = im.resize((max(1, round(im.size[0] * f)), max(1, round(im.size[1] * f))),
                       Image.LANCZOS)
    buf = io.BytesIO()
    if hat_alpha:
        im.save(buf, "PNG", optimize=True)
        fmt = "png"
    else:
        im.save(buf, "JPEG", quality=88)
        fmt = "jpeg"
    return {"daten": base64.b64encode(buf.getvalue()).decode("ascii"),
            "format": fmt, "pw": im.size[0], "ph": im.size[1]}


def pil_bild(daten):
    """Decoded PIL image (RGB/RGBA) of the stored data."""
    im = Image.open(io.BytesIO(base64.b64decode(daten)))
    im.load()
    return im
