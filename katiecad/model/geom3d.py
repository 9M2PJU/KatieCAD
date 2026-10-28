# -*- coding: utf-8 -*-
"""
katiecad/model/geom3d.py - 3D geometry for the wireframe view (NO Tkinter, MIT).

* Kamera: orbit camera (parallel or perspective), Z axis up.
* Netz: wireframe + faces of a body (faces only for hidden-line removal).
* Mesh builders: prism / pyramid (any base polygon), sphere.
* sichtbare_linien(): hidden-line removal by ray casting.
* Cube for the view cube (faces, hit test).
All angles in degrees, lengths in mm.
"""

import math

EPS = 1e-9

# --------------------------------------------------------------------------
# vector helpers
# --------------------------------------------------------------------------
def v_sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def v_add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def v_mul(a, f): return (a[0] * f, a[1] * f, a[2] * f)
def v_dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def v_len(a): return math.sqrt(v_dot(a, a))
def v_norm(a):
    l = v_len(a)
    return (a[0] / l, a[1] / l, a[2] / l) if l > EPS else (0.0, 0.0, 1.0)


# --------------------------------------------------------------------------
# Camera
# --------------------------------------------------------------------------
# name -> (yaw, pitch)   yaw 0 = looking from the front (-Y), 90 = from the right (+X)
ANSICHTEN = {
    "oben": (0.0, 90.0), "unten": (0.0, -90.0),
    "vorne": (0.0, 0.0), "hinten": (180.0, 0.0),
    "rechts": (90.0, 0.0), "links": (270.0, 0.0),
    "iso_sw": (-45.0, 35.264), "iso_so": (45.0, 35.264),
    "iso_no": (135.0, 35.264), "iso_nw": (225.0, 35.264),
}


class Kamera:
    def __init__(self, yaw=-45.0, pitch=35.264, ziel=(0.0, 0.0, 0.0), abstand=800.0,
                 skala=2.0, perspektive=False):
        self.yaw, self.pitch = float(yaw), float(pitch)
        self.ziel = tuple(ziel)
        self.abstand = float(abstand)        # eye distance from the target (perspective)
        self.skala = float(skala)            # pixels per mm at the target
        self.perspektive = bool(perspektive)

    # ---- orientation ----------------------------------------------------
    def ansicht_setzen(self, name):
        yaw, pitch = ANSICHTEN[name]
        self.yaw, self.pitch = yaw, pitch

    def richtung_zum_auge(self):
        y, p = math.radians(self.yaw), math.radians(self.pitch)
        return (math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))

    def basis(self):
        """(right, up, forward) unit vectors in world coordinates."""
        e = self.richtung_zum_auge()
        f = v_mul(e, -1.0)
        y = math.radians(self.yaw)
        r = (math.cos(y), math.sin(y), 0.0)
        u = v_cross(r, f)
        return r, v_norm(u), f

    def auge(self):
        r, u, f = self.basis()
        return v_sub(self.ziel, v_mul(f, self.abstand))

    # ---- projection ------------------------------------------------------
    def proj(self, p, cx, cy):
        """-> (sx, sy, depth) or None if the point is behind the camera."""
        r, u, f = self.basis()
        if not self.perspektive:
            v = v_sub(p, self.ziel)
            return (cx + self.skala * v_dot(v, r), cy - self.skala * v_dot(v, u),
                    v_dot(v, f))
        v = v_sub(p, self.auge())
        z = v_dot(v, f)
        if z <= self.abstand * 0.02:
            return None
        k = self.skala * self.abstand / z
        return (cx + k * v_dot(v, r), cy - k * v_dot(v, u), z)

    def proj_segment(self, p, q, cx, cy):
        """Projected segment ((x1, y1), (x2, y2)) with near-plane clipping, or None."""
        if self.perspektive:
            r, u, f = self.basis()
            e = self.auge()
            near = self.abstand * 0.02
            zp = v_dot(v_sub(p, e), f)
            zq = v_dot(v_sub(q, e), f)
            if zp <= near and zq <= near:
                return None
            if zp <= near or zq <= near:
                t = (near - zp) / (zq - zp)
                m = v_add(p, v_mul(v_sub(q, p), t))
                if zp <= near:
                    p = m
                else:
                    q = m
        a, b = self.proj(p, cx, cy), self.proj(q, cx, cy)
        if a is None or b is None:
            return None
        return ((a[0], a[1]), (b[0], b[1]))

    def strahl(self, sx, sy, cx, cy):
        """Ray through the screen point: (origin, unit direction)."""
        r, u, f = self.basis()
        dx, dy = (sx - cx), -(sy - cy)
        if not self.perspektive:
            o = v_add(v_add(self.ziel, v_mul(r, dx / self.skala)), v_mul(u, dy / self.skala))
            return v_sub(o, v_mul(f, self.abstand)), f
        focal = self.skala * self.abstand
        d = v_add(v_add(v_mul(f, focal), v_mul(r, dx)), v_mul(u, dy))
        return self.auge(), v_norm(d)

    def auf_ebene(self, sx, sy, cx, cy, z=0.0):
        """Point where the ray through the screen point hits the plane Z = z, or None."""
        o, d = self.strahl(sx, sy, cx, cy)
        if abs(d[2]) < 1e-9:
            return None
        t = (z - o[2]) / d[2]
        if t < 0:
            return None
        return v_add(o, v_mul(d, t))

    # ---- navigation ------------------------------------------------------
    def orbit(self, dx_px, dy_px, empfindlichkeit=0.4):
        self.yaw = (self.yaw - dx_px * empfindlichkeit) % 360.0
        self.pitch = max(-90.0, min(90.0, self.pitch + dy_px * empfindlichkeit))

    def pan(self, dx_px, dy_px):
        r, u, f = self.basis()
        s = 1.0 / self.skala
        self.ziel = v_add(self.ziel, v_add(v_mul(r, -dx_px * s), v_mul(u, dy_px * s)))

    def zoom(self, faktor):
        self.skala = max(1e-4, min(1e4, self.skala * faktor))

    def anpassen(self, punkte, breite, hoehe, rand=40):
        """Frames all points in a window of breite x hoehe pixels."""
        if not punkte:
            return
        xs = [p[0] for p in punkte]; ys = [p[1] for p in punkte]; zs = [p[2] for p in punkte]
        self.ziel = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
        self.skala = 1.0
        r, u, f = self.basis()
        w = h = 1e-9
        for p in punkte:
            v = v_sub(p, self.ziel)
            w = max(w, abs(v_dot(v, r)) * 2)
            h = max(h, abs(v_dot(v, u)) * 2)
        self.skala = max(1e-4, min((breite - 2 * rand) / w, (hoehe - 2 * rand) / h))
        diag = math.sqrt((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2
                         + (max(zs) - min(zs)) ** 2)
        self.abstand = max(diag * 2.5, 50.0)


# --------------------------------------------------------------------------
# Mesh
# --------------------------------------------------------------------------
class Netz:
    """Wireframe (edges) + faces (only needed for hidden-line removal)."""

    def __init__(self):
        self.punkte = []      # (x, y, z)
        self.kanten = []      # (i, j)
        self.flaechen = []    # [i, j, k, ...] planar polygons

    def punkt(self, p):
        self.punkte.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.punkte) - 1

    def kante(self, i, j):
        if i != j:
            self.kanten.append((i, j))

    def flaeche(self, idx):
        self.flaechen.append(list(idx))

    def bbox(self):
        if not self.punkte:
            return None
        xs = [p[0] for p in self.punkte]; ys = [p[1] for p in self.punkte]
        zs = [p[2] for p in self.punkte]
        return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))

    def dreiecke(self):
        """All faces as triangles (a, b, c) in world coordinates."""
        out = []
        for fl in self.flaechen:
            pts = [self.punkte[i] for i in fl]
            for (i, j, k) in triangulieren(pts):
                out.append((pts[i], pts[j], pts[k]))
        return out


def _flaechen_normale(pts):
    n = (0.0, 0.0, 0.0)
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n = (n[0] + (a[1] - b[1]) * (a[2] + b[2]),
             n[1] + (a[2] - b[2]) * (a[0] + b[0]),
             n[2] + (a[0] - b[0]) * (a[1] + b[1]))
    return n


def triangulieren(pts):
    """Ear clipping of a planar polygon (3D points) -> [(i, j, k)]."""
    n = len(pts)
    if n < 3:
        return []
    if n == 3:
        return [(0, 1, 2)]
    nm = _flaechen_normale(pts)
    ax = max(range(3), key=lambda a: abs(nm[a]))          # dominant axis
    k1, k2 = [(1, 2), (2, 0), (0, 1)][ax]
    p2 = [(p[k1], p[k2]) for p in pts]
    orient = -1.0 if nm[ax] < 0 else 1.0

    def kreuz(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def im_dreieck(p, a, b, c):
        d1, d2, d3 = kreuz(a, b, p), kreuz(b, c, p), kreuz(c, a, p)
        neg = d1 < -1e-12 or d2 < -1e-12 or d3 < -1e-12
        pos = d1 > 1e-12 or d2 > 1e-12 or d3 > 1e-12
        return not (neg and pos)

    idx = list(range(n))
    out = []
    schutz = 0
    while len(idx) > 3 and schutz < 10 * n * n:
        schutz += 1
        gefunden = False
        for m in range(len(idx)):
            i0, i1, i2 = idx[m - 1], idx[m], idx[(m + 1) % len(idx)]
            a, b, c = p2[i0], p2[i1], p2[i2]
            if orient * kreuz(a, b, c) <= 1e-12:           # reflex / degenerate
                continue
            if any(im_dreieck(p2[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            out.append((i0, i1, i2))
            del idx[m]
            gefunden = True
            break
        if not gefunden:
            break
    if len(idx) == 3:
        out.append((idx[0], idx[1], idx[2]))
    elif len(idx) > 3:                                      # fallback: fan
        out.extend((idx[0], idx[j], idx[j + 1]) for j in range(1, len(idx) - 1))
    return out


def prisma_netz(profil, z0, hoehe, rund=False, senkrechte=8):
    """Prism over the closed base polygon `profil` from z0 to z0 + hoehe
    (hoehe may be negative). Round bodies draw only `senkrechte` vertical edges."""
    nz = Netz()
    n = len(profil)
    if n < 3:
        return nz
    z1 = z0 + hoehe
    ub = [nz.punkt((x, y, z0)) for (x, y) in profil]
    ut = [nz.punkt((x, y, z1)) for (x, y) in profil]
    for i in range(n):
        j = (i + 1) % n
        nz.kante(ub[i], ub[j]); nz.kante(ut[i], ut[j])
        nz.flaeche([ub[i], ub[j], ut[j], ut[i]])
    schritt = max(1, n // senkrechte) if rund else 1
    for i in range(0, n, schritt):
        nz.kante(ub[i], ut[i])
    nz.flaeche(ub); nz.flaeche(ut)
    return nz


def pyramide_netz(profil, z0, hoehe, spitze=None, rund=False, senkrechte=8):
    """Pyramid / cone: base polygon at z0, apex at z0 + hoehe above `spitze`
    (default: centre of the base)."""
    nz = Netz()
    n = len(profil)
    if n < 3:
        return nz
    if spitze is None:
        spitze = (sum(p[0] for p in profil) / n, sum(p[1] for p in profil) / n)
    ub = [nz.punkt((x, y, z0)) for (x, y) in profil]
    ap = nz.punkt((spitze[0], spitze[1], z0 + hoehe))
    for i in range(n):
        j = (i + 1) % n
        nz.kante(ub[i], ub[j])
        nz.flaeche([ub[i], ub[j], ap])
    schritt = max(1, n // senkrechte) if rund else 1
    for i in range(0, n, schritt):
        nz.kante(ub[i], ap)
    nz.flaeche(ub)
    return nz


def kugel_netz(mx, my, mz, r, laengen=16, breiten=8, zeichnen_laengen=8):
    """Sphere: latitude rings and `zeichnen_laengen` meridians drawn; the full
    grid is used for hidden-line occlusion."""
    nz = Netz()
    if r <= 0:
        return nz
    ringe = []
    sued = nz.punkt((mx, my, mz - r))
    for b in range(1, breiten):
        phi = -math.pi / 2 + math.pi * b / breiten
        z = mz + r * math.sin(phi)
        rr = r * math.cos(phi)
        ringe.append([nz.punkt((mx + rr * math.cos(2 * math.pi * k / laengen),
                                my + rr * math.sin(2 * math.pi * k / laengen), z))
                      for k in range(laengen)])
    nord = nz.punkt((mx, my, mz + r))
    for ring in ringe:
        for k in range(laengen):
            nz.kante(ring[k], ring[(k + 1) % laengen])
    schritt = max(1, laengen // zeichnen_laengen)
    for k in range(0, laengen, schritt):
        nz.kante(sued, ringe[0][k])
        for a, b in zip(ringe, ringe[1:]):
            nz.kante(a[k], b[k])
        nz.kante(ringe[-1][k], nord)
    for k in range(laengen):
        k2 = (k + 1) % laengen
        nz.flaeche([sued, ringe[0][k2], ringe[0][k]])
        for a, b in zip(ringe, ringe[1:]):
            nz.flaeche([a[k], a[k2], b[k2], b[k]])
        nz.flaeche([ringe[-1][k], ringe[-1][k2], nord])
    return nz


def kreis_profil(cx, cy, r, n=32, rot=0.0):
    return [(cx + r * math.cos(math.radians(rot) + 2 * math.pi * i / n),
             cy + r * math.sin(math.radians(rot) + 2 * math.pi * i / n)) for i in range(n)]


def rechteck_profil(x1, y1, x2, y2):
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


# --------------------------------------------------------------------------
# Hidden-line removal
# --------------------------------------------------------------------------
def _strahl_dreieck(o, d, tri):
    """Moeller-Trumbore: parameter t of the hit (o + t d) or None."""
    a, b, c = tri
    e1, e2 = v_sub(b, a), v_sub(c, a)
    pv = v_cross(d, e2)
    det = v_dot(e1, pv)
    if abs(det) < 1e-12:
        return None
    inv = 1.0 / det
    tv = v_sub(o, a)
    u = v_dot(tv, pv) * inv
    if u < -1e-9 or u > 1 + 1e-9:
        return None
    qv = v_cross(tv, e1)
    v = v_dot(d, qv) * inv
    if v < -1e-9 or u + v > 1 + 1e-9:
        return None
    return v_dot(e2, qv) * inv


def sichtbare_linien(netze, kamera, cx, cy, proben=14, min_px=10.0, zeichnen=None):
    """Hidden-line removal for a list of Netz objects.
    -> (sichtbar, verdeckt): lists of polylines [(sx, sy), ...] in pixels."""
    tris = []
    for nz in netze:
        tris.extend(nz.dreiecke())
    r, u, f = kamera.basis()
    eye = kamera.auge()
    tmp = []
    for t in tris:
        pj = [kamera.proj(p, cx, cy) for p in t]
        if any(p is None for p in pj):
            tmp.append((t, None))
        else:
            xs = [p[0] for p in pj]; ys = [p[1] for p in pj]
            tmp.append((t, (min(xs), min(ys), max(xs), max(ys))))
    tris = tmp
    # ray length for parallel projection: beyond all geometry
    alle = [p for nz in netze for p in nz.punkte]
    if alle:
        rad = max(v_len(v_sub(p, kamera.ziel)) for p in alle) + kamera.abstand
    else:
        rad = kamera.abstand
    sicht, verdeckt = [], []
    for nz in netze:
        if zeichnen is not None and id(nz) not in zeichnen:
            continue
        for (i, j) in nz.kanten:
            p, q = nz.punkte[i], nz.punkte[j]
            seg = kamera.proj_segment(p, q, cx, cy)
            if seg is None:
                continue
            (x1, y1), (x2, y2) = seg
            laenge = math.hypot(x2 - x1, y2 - y1)
            n = max(1, min(proben, int(laenge / min_px) + 1))
            if not tris:
                sicht.append([(x1, y1), (x2, y2)])
                continue
            teile = []
            for k in range(n):
                t0, t1 = k / n, (k + 1) / n
                tm = (t0 + t1) / 2
                pm = (p[0] + (q[0] - p[0]) * tm, p[1] + (q[1] - p[1]) * tm,
                      p[2] + (q[2] - p[2]) * tm)
                a = kamera.proj(pm, cx, cy)
                if a is None:
                    continue
                if kamera.perspektive:
                    o = eye
                else:
                    o = v_sub(pm, v_mul(f, rad))
                d = v_sub(pm, o)
                dl = v_len(d)
                if dl < 1e-9:
                    continue
                ok = True
                for tri, bb in tris:
                    if bb is not None and (a[0] < bb[0] - 1 or a[0] > bb[2] + 1
                                           or a[1] < bb[1] - 1 or a[1] > bb[3] + 1):
                        continue
                    t = _strahl_dreieck(o, d, tri)
                    if t is not None and t > 1e-6 and t < 1.0 - 1e-4:
                        ok = False
                        break
                s0 = (x1 + (x2 - x1) * t0, y1 + (y2 - y1) * t0)
                s1 = (x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1)
                teile.append((ok, s0, s1))
            _sammeln(teile, True, sicht)
            _sammeln(teile, False, verdeckt)
    return sicht, verdeckt


def _sammeln(teile, gewollt, ziel):
    zug = []
    for ok, s0, s1 in teile:
        if ok == gewollt:
            if not zug:
                zug = [s0, s1]
            else:
                zug.append(s1)
        elif zug:
            ziel.append(zug)
            zug = []
    if zug:
        ziel.append(zug)


# --------------------------------------------------------------------------
# Picking
# --------------------------------------------------------------------------
def abstand_punkt_segment(px, py, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    if l2 < 1e-12:
        return math.hypot(px - a[0], py - a[1])
    t = max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / l2))
    return math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy))


def abstand_zu_netz(netz, kamera, cx, cy, mx, my):
    """Smallest screen distance (pixels) from (mx, my) to the edges of the mesh."""
    best = None
    for (i, j) in netz.kanten:
        seg = kamera.proj_segment(netz.punkte[i], netz.punkte[j], cx, cy)
        if seg is None:
            continue
        d = abstand_punkt_segment(mx, my, seg[0], seg[1])
        if best is None or d < best:
            best = d
    return best


# --------------------------------------------------------------------------
# View cube
# --------------------------------------------------------------------------
WUERFEL_FLAECHEN = {          # view name -> (outward normal, 4 corners)
    "oben":   ((0, 0, 1),  [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
    "unten":  ((0, 0, -1), [(-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)]),
    "vorne":  ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
    "hinten": ((0, 1, 0),  [(1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)]),
    "rechts": ((1, 0, 0),  [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
    "links":  ((-1, 0, 0), [(-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)]),
}


def wuerfel_zeichnung(kamera, mx, my, groesse):
    """View cube centred at (mx, my) with half edge `groesse` pixels.
    -> [(name, [(x, y)...], (tx, ty), sichtbarkeit)] back to front; only
    faces turned towards the viewer are returned."""
    r, u, f = kamera.basis()
    zum_auge = v_mul(f, -1.0)
    s = groesse / math.sqrt(3.0)
    out = []
    for name, (nrm, ecken) in WUERFEL_FLAECHEN.items():
        q = v_dot(nrm, zum_auge)
        if q <= 0.02:
            continue
        pts = [(mx + s * v_dot(e, r), my - s * v_dot(e, u)) for e in ecken]
        c = (sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4)
        out.append((name, pts, c, q))
    out.sort(key=lambda t: t[3])
    return out


def punkt_in_polygon(px, py, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % n]
        if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def wuerfel_treffer(kamera, mx, my, groesse, px, py):
    """Name of the cube face under (px, py) or None."""
    for name, pts, _c, _q in reversed(wuerfel_zeichnung(kamera, mx, my, groesse)):
        if punkt_in_polygon(px, py, pts):
            return name
    return None


# --------------------------------------------------------------------------
# Work planes ("Ebene"): 9-tuple (ox, oy, oz,  ux, uy, uz,  vx, vy, vz);
# the normal is w = u x v. Local (x, y, z) -> world  o + x u + y v + z w.
# --------------------------------------------------------------------------
BODEN_EBENE = (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)


def ebene_basis(e):
    u = (e[3], e[4], e[5]); v = (e[6], e[7], e[8])
    return u, v, v_cross(u, v)


def ebene_punkt(e, x, y, z=0.0):
    u, v, w = ebene_basis(e)
    return (e[0] + x * u[0] + y * v[0] + z * w[0],
            e[1] + x * u[1] + y * v[1] + z * w[1],
            e[2] + x * u[2] + y * v[2] + z * w[2])


def ebene_lokal(e, p):
    u, v, w = ebene_basis(e)
    d = (p[0] - e[0], p[1] - e[1], p[2] - e[2])
    return (v_dot(d, u), v_dot(d, v), v_dot(d, w))


def netz_abbilden(nz, e):
    """Copy of mesh `nz` (local coordinates) mapped into the world via plane `e`."""
    out = Netz()
    out.punkte = [ebene_punkt(e, *p) for p in nz.punkte]
    out.kanten = list(nz.kanten)
    out.flaechen = [list(f) for f in nz.flaechen]
    return out


def ebene_von_flaeche(pts, zentrum):
    """Work plane of a planar face (list of 3D points); the normal points away
    from `zentrum` (the centre of the body)."""
    n = v_norm(_flaechen_normale(pts))
    if v_len(n) < 1e-12:
        return None
    mitte = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts),
             sum(p[2] for p in pts) / len(pts))
    if v_dot(n, v_sub(mitte, zentrum)) < 0:
        n = v_mul(n, -1.0)
    # u: first edge of the face, made perpendicular to n
    u = None
    for i in range(len(pts)):
        d = v_sub(pts[(i + 1) % len(pts)], pts[i])
        d = v_sub(d, v_mul(n, v_dot(d, n)))
        if v_len(d) > 1e-9:
            u = v_norm(d)
            o = pts[i]
            break
    if u is None:
        return None
    v = v_cross(n, u)
    return (o[0], o[1], o[2], u[0], u[1], u[2], v[0], v[1], v[2])


def strahl_auf_ebene(e, o, d):
    """Local (x, y) where the ray o + t d (t > 0) meets the plane, or None."""
    u, v, w = ebene_basis(e)
    nenner = v_dot(d, w)
    if abs(nenner) < 1e-9:
        return None
    t = v_dot(v_sub((e[0], e[1], e[2]), o), w) / nenner
    if t <= 0:
        return None
    p = v_add(o, v_mul(d, t))
    l = ebene_lokal(e, p)
    return (l[0], l[1])


def flaeche_treffer(nz, o, d):
    """Nearest face of mesh `nz` hit by the ray -> (t, face_index) or None."""
    best = None
    for fi, fl in enumerate(nz.flaechen):
        pts = [nz.punkte[i] for i in fl]
        for (i, j, k) in triangulieren(pts):
            t = _strahl_dreieck(o, d, (pts[i], pts[j], pts[k]))
            if t is not None and t > 1e-6 and (best is None or t < best[0]):
                best = (t, fi)
    return best

