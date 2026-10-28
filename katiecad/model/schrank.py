"""Standard control cabinets as 3D blocks (generic 'Schaltschrank', no brand names).

All sizes in mm. A cabinet is built from simple boxes: body, optional mounting plate and an
optional plinth (a plain box under the cabinet). The list contains common sizes; any other
size can be entered freely."""
from katiecad.model.core import Gruppe3D, quader

# (height, width, depth, mounting plate width, mounting plate height)
SCHRAENKE = (
    (1600, 600, 400, 499, 1496),
    (1800, 600, 300, 499, 1696),
    (1800, 800, 300, 699, 1696),
    (1800, 1200, 300, 1099, 1696),
    (2000, 600, 300, 499, 1896),
    (2000, 1800, 600, 1699, 1896),
    (1200, 800, 300, 745, 1175),
    (300, 300, 210, 250, 275),
    (380, 300, 210, 250, 355),
    (380, 380, 210, 330, 355),
    (500, 500, 210, 450, 475),
)
SOCKEL_HOEHEN = (0, 100, 150, 200)
PLATTE_DICKE = 3.0
PLATTE_ABSTAND = 15.0           # mounting plate: distance to the rear wall
TUER_DICKE = 2.0                # door sheet thickness
WAND_DICKE = 1.5                # side panel thickness
GRIFF_DICKE = 8.0               # handle plate protrudes from the door front
SPALT = 3.0                     # door / side panels sit slightly inset (gap, visible in wireframe)


def vorgabe_name(s):
    """Display text of a list entry: 'H x W x D'."""
    return f"{s[1]} x {s[0]} x {s[2]}  (B x H x T)"


def platte_vorschlag(breite, hoehe):
    """Mounting plate size for free cabinet sizes."""
    return max(10.0, breite - 100.0), max(10.0, hoehe - 100.0)


def schrank_bauen(breite, hoehe, tiefe, x=0.0, y=0.0, z=0.0, platte=None, sockel=0.0,
                  tuer=False, seite_l=False, seite_r=False, griff_links=False):
    """Cabinet as a 3D block. Front towards -Y, rear wall at y + depth.
    platte = (width, height) of the mounting plate or None; sockel = plinth height (0 = none).
    (x, y, z) is the base corner of the whole block (floor level)."""
    teile = []
    z0 = z + sockel
    if sockel and sockel > 0:
        teile.append(_bez(quader(x, y, x + breite, y + tiefe, z, sockel), "Sockel"))
    teile.append(_bez(quader(x, y, x + breite, y + tiefe, z0, hoehe), "Schaltschrank"))
    if platte:
        pb, ph = platte
        px = x + (breite - pb) / 2.0
        pz = z0 + (hoehe - ph) / 2.0
        py2 = y + tiefe - PLATTE_ABSTAND
        teile.append(_bez(quader(px, py2 - PLATTE_DICKE, px + pb, py2, pz, ph), "Montageplatte"))
    if tuer:                       # door: thin panel on the front face (inside the cabinet depth)
        teile.append(_bez(quader(x + SPALT, y, x + breite - SPALT, y + TUER_DICKE,
                                 z0 + SPALT, hoehe - 2 * SPALT), "Tür"))
    if tuer:                       # rectangular handle plate with square lock insert, right (default) or left
        gb = min(40.0, breite * 0.15)
        gh = min(120.0, hoehe * 0.3)
        if griff_links:
            gx1 = x + SPALT + 20.0
            gx2 = min(x + breite - SPALT - 5.0, gx1 + gb)
        else:
            gx2 = x + breite - SPALT - 20.0
            gx1 = max(x + SPALT + 5.0, gx2 - gb)
        gz = z0 + min(hoehe * 0.55, hoehe - gh - 20.0) - gh / 2.0
        teile.append(_bez(quader(gx1, y - GRIFF_DICKE, gx2, y, gz, gh), "Türgriff"))
        sq = min(24.0, gb * 0.6)
        cx, cz = (gx1 + gx2) / 2.0, gz + gh / 2.0
        teile.append(_bez(quader(cx - sq / 2, y - GRIFF_DICKE - 4.0, cx + sq / 2, y - GRIFF_DICKE,
                                 cz - sq / 2, sq), "Schloss"))
    for aktiv, x1, bez in ((seite_l, x, "Seitenwand links"),
                           (seite_r, x + breite - WAND_DICKE, "Seitenwand rechts")):
        if aktiv:                  # side panels: thin panels on the left / right face
            teile.append(_bez(quader(x1, y + SPALT, x1 + WAND_DICKE, y + tiefe - SPALT,
                                     z0 + SPALT, hoehe - 2 * SPALT), bez))
    name = f"Schaltschrank {breite:g}x{hoehe:g}x{tiefe:g}"
    if platte:
        name += " + MP"
    if tuer:
        name += " + Tür"
    return Gruppe3D(teile, name=name)


def _bez(k, bez):
    k.bez = bez
    return k
