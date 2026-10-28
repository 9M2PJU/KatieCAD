# -*- coding: utf-8 -*-
"""
katiecad/model/geom2d.py - Pure 2D geometry helpers (MIT, no Tk).

measure, fillet, chamfer, ellipse and spline point generation.
"""

import math


def messung(p1, p2):
    """-> dict(dx, dy, abstand, winkel) between two points; winkel in degrees
    (0..360, counter-clockwise, 0 = +X)."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    d = math.hypot(dx, dy)
    w = math.degrees(math.atan2(dy, dx)) % 360.0 if d > 1e-12 else 0.0
    return {"dx": dx, "dy": dy, "abstand": d, "winkel": w}


def schnitt_geraden(a1, a2, b1, b2):
    """Intersection of the infinite lines a1-a2 and b1-b2 or None."""
    d1 = (a2[0] - a1[0], a2[1] - a1[1])
    d2 = (b2[0] - b1[0], b2[1] - b1[1])
    det = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(det) < 1e-12:
        return None
    t = ((b1[0] - a1[0]) * d2[1] - (b1[1] - a1[1]) * d2[0]) / det
    return (a1[0] + t * d1[0], a1[1] + t * d1[1])


def _einheit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n > 1e-12 else (0.0, 0.0)


def _ecke(l1, l2):
    """Corner S of two lines (each ((x1,y1),(x2,y2))) and the unit directions
    from S along each line, pointing to the longer side of the line (the part
    that is kept). -> (S, u1, u2, len1, len2) or None."""
    s = schnitt_geraden(l1[0], l1[1], l2[0], l2[1])
    if s is None:
        return None
    res = []
    for a, b in (l1, l2):
        da = math.hypot(a[0] - s[0], a[1] - s[1])
        db = math.hypot(b[0] - s[0], b[1] - s[1])
        far = a if da >= db else b
        u = _einheit((far[0] - s[0], far[1] - s[1]))
        res.append((u, max(da, db), far))
    return s, res[0][0], res[1][0], res[0][1], res[1][1], res[0][2], res[1][2]


def abrunden(l1, l2, r):
    """Fillet of two lines.
    -> dict(neu1, neu2, mitte, r, w0, w1) or None.
    neu1/neu2: the shortened lines; the arc runs from `w0` to `w1` (degrees,
    counter-clockwise) around `mitte`. r == 0 -> only joined at the corner
    (arc keys None). Returns None if parallel or radius too large."""
    e = _ecke(l1, l2)
    if e is None:
        return None
    s, u1, u2, la, lb, f1, f2 = e
    cosw = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
    ang = math.acos(cosw)                    # angle between the legs
    if ang < 1e-6 or abs(ang - math.pi) < 1e-6:
        return None
    if r <= 0:
        return {"neu1": (s, f1), "neu2": (s, f2), "mitte": None, "r": 0.0,
                "w0": None, "w1": None}
    t = r / math.tan(ang / 2.0)              # tangent length
    if t >= la - 1e-9 or t >= lb - 1e-9:
        return None
    t1 = (s[0] + u1[0] * t, s[1] + u1[1] * t)
    t2 = (s[0] + u2[0] * t, s[1] + u2[1] * t)
    bis = _einheit((u1[0] + u2[0], u1[1] + u2[1]))
    dm = r / math.sin(ang / 2.0)
    m = (s[0] + bis[0] * dm, s[1] + bis[1] * dm)
    a1 = math.degrees(math.atan2(t1[1] - m[1], t1[0] - m[0])) % 360.0
    a2 = math.degrees(math.atan2(t2[1] - m[1], t2[0] - m[0])) % 360.0
    # the short arc: counter-clockwise from w0 to w1
    if (a2 - a1) % 360.0 <= 180.0:
        w0, w1 = a1, a2
    else:
        w0, w1 = a2, a1
    return {"neu1": (t1, f1), "neu2": (t2, f2), "mitte": m, "r": r,
            "w0": w0, "w1": w1}


def fase(l1, l2, d1, d2=None):
    """Chamfer of two lines with distances d1 (on l1) and d2 (on l2).
    -> dict(neu1, neu2, fase=(p1,p2)) or None."""
    if d2 is None:
        d2 = d1
    e = _ecke(l1, l2)
    if e is None:
        return None
    s, u1, u2, la, lb, f1, f2 = e
    if d1 <= 0 and d2 <= 0:
        return {"neu1": (s, f1), "neu2": (s, f2), "fase": None}
    if d1 >= la - 1e-9 or d2 >= lb - 1e-9:
        return None
    p1 = (s[0] + u1[0] * d1, s[1] + u1[1] * d1)
    p2 = (s[0] + u2[0] * d2, s[1] + u2[1] * d2)
    return {"neu1": (p1, f1), "neu2": (p2, f2), "fase": (p1, p2)}


def ellipse_punkte(cx, cy, a, b, rot_deg=0.0, n=96, w0=0.0, w1=360.0):
    """Points of an ellipse (semi-axes a along rot_deg, b perpendicular).
    A full ellipse repeats no point (closed polyline); partial arcs include
    both ends."""
    voll = abs(w1 - w0 - 360.0) < 1e-9
    cr, sr = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
    pts = []
    anz = n if voll else n + 1
    for i in range(anz):
        t = math.radians(w0 + (w1 - w0) * (i / n))
        x, y = a * math.cos(t), b * math.sin(t)
        pts.append((cx + x * cr - y * sr, cy + x * sr + y * cr))
    return pts


def spline_punkte(stuetz, geschlossen=False, seg=16):
    """Catmull-Rom spline through the support points (centripetal-free,
    uniform). -> list of points including the first and last support point
    (closed: the first point is not repeated)."""
    p = list(stuetz)
    n = len(p)
    if n < 3:
        return list(p)
    out = []
    rng = range(n) if geschlossen else range(n - 1)
    for i in rng:
        if geschlossen:
            p0, p1, p2, p3 = p[(i - 1) % n], p[i], p[(i + 1) % n], p[(i + 2) % n]
        else:
            p0 = p[i - 1] if i > 0 else (2 * p[0][0] - p[1][0], 2 * p[0][1] - p[1][1])
            p1, p2 = p[i], p[i + 1]
            p3 = p[i + 2] if i + 2 < n else (2 * p[-1][0] - p[-2][0],
                                             2 * p[-1][1] - p[-2][1])
        for k in range(seg):
            t = k / seg
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t
                                    + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                             for j in (0, 1)))
    if not geschlossen:
        out.append(tuple(p[-1]))
    return out


def winkel_zwischen(c, p, q):
    """-> (w0, w1) ccw degrees of the short sector from ray c->p to c->q."""
    a = math.degrees(math.atan2(p[1] - c[1], p[0] - c[0])) % 360.0
    b = math.degrees(math.atan2(q[1] - c[1], q[0] - c[0])) % 360.0
    return (a, b) if (b - a) % 360.0 <= 180.0 else (b, a)


def ecken_runden(punkte, geschlossen, art, r=0.0, d1=0.0, d2=None, nur=None):
    """Fillets or chamfers the corners of a polygon / polyline.

    art: "abrunden" (radius r) or "fase" (distances d1, d2).
    nur: index of the only corner to treat (None = all possible corners;
    the end points of an open polyline are never treated).
    -> (segmente, anzahl): segmente = [("l", p, q) | ("b", cx, cy, r, w0, w1)]
    in drawing order, anzahl = number of treated corners."""
    if d2 is None:
        d2 = d1
    n = len(punkte)
    ecken = {}                                   # idx -> (t_in, t_out, daten)
    for i in range(n):
        if not geschlossen and (i == 0 or i == n - 1):
            continue
        if nur is not None and i != nur:
            continue
        v, a, b = punkte[i], punkte[i - 1], punkte[(i + 1) % n]
        u1 = _einheit((a[0] - v[0], a[1] - v[1]))
        u2 = _einheit((b[0] - v[0], b[1] - v[1]))
        cosw = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
        ang = math.acos(cosw)
        if ang < 1e-6 or abs(ang - math.pi) < 1e-6:
            continue
        if art == "abrunden":
            if r <= 0:
                continue
            t = r / math.tan(ang / 2.0)
            ecken[i] = (t, t, (u1, u2, ang))
        else:
            if d1 <= 0 and d2 <= 0:
                continue
            ecken[i] = (d1, d2, (u1, u2, ang))
    # drop corners that do not fit on their edges
    geaendert = True
    while geaendert:
        geaendert = False
        for i in list(ecken):
            j = (i + 1) % n
            if (not geschlossen and i == n - 1):
                continue
            L = math.hypot(punkte[j][0] - punkte[i][0], punkte[j][1] - punkte[i][1])
            ta = ecken[i][1]
            tb = ecken[j][0] if j in ecken else 0.0
            if ta + tb > L + 1e-9:
                for k in (i, j):
                    if k in ecken:
                        del ecken[k]
                geaendert = True
                break
        # the incoming side of a corner must also fit the previous edge
        # (handled by the loop above, which looks at every edge)
    seg = []
    kanten = range(n) if geschlossen else range(n - 1)
    for i in kanten:
        j = (i + 1) % n
        p, q = punkte[i], punkte[j]
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        ux, uy = ((q[0] - p[0]) / L, (q[1] - p[1]) / L) if L > 1e-12 else (0, 0)
        a = p
        if i in ecken:
            a = (p[0] + ux * ecken[i][1], p[1] + uy * ecken[i][1])
        b = q
        if j in ecken:
            b = (q[0] - ux * ecken[j][0], q[1] - uy * ecken[j][0])
        if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-9:
            seg.append(("l", a, b))
        if j in ecken and (geschlossen or j < n - 1):
            v = punkte[j]
            t_in, t_out, (u1, u2, ang) = ecken[j]
            p1 = (v[0] + u1[0] * t_in, v[1] + u1[1] * t_in)
            p2 = (v[0] + u2[0] * t_out, v[1] + u2[1] * t_out)
            if art == "abrunden":
                bis = _einheit((u1[0] + u2[0], u1[1] + u2[1]))
                dm = r / math.sin(ang / 2.0)
                m = (v[0] + bis[0] * dm, v[1] + bis[1] * dm)
                w0 = math.degrees(math.atan2(p1[1] - m[1], p1[0] - m[0])) % 360.0
                w1 = math.degrees(math.atan2(p2[1] - m[1], p2[0] - m[0])) % 360.0
                if (w1 - w0) % 360.0 > 180.0:
                    w0, w1 = w1, w0
                seg.append(("b", m[0], m[1], r, w0, w1))
            else:
                seg.append(("l", p1, p2))
    return seg, len(ecken)


def _kreuz(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _abstand_strecke(a, b, p):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-18 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def seite_links(punkte, geschlossen, klick):
    """+1 if `klick` lies left of the nearest edge of the polyline, else -1."""
    n = len(punkte)
    kanten = range(n) if geschlossen else range(n - 1)
    best, vz = None, 1
    for i in kanten:
        a, b = punkte[i], punkte[(i + 1) % n]
        d = _abstand_strecke(a, b, klick)
        if best is None or d < best:
            best = d
            vz = 1 if _kreuz(a, b, klick) >= 0 else -1
    return vz


def versatz_polylinie(punkte, geschlossen, abstand, seite=1):
    """Parallel polyline at `abstand` (>0) to the left (seite=+1) or right
    (seite=-1) with mitred corners. -> list of points or None if the result
    degenerates (an edge reverses or collapses)."""
    pts = [tuple(p) for p in punkte]
    # remove duplicate neighbours
    sauber = []
    for p in pts:
        if not sauber or math.hypot(p[0] - sauber[-1][0], p[1] - sauber[-1][1]) > 1e-9:
            sauber.append(p)
    if geschlossen and len(sauber) > 1 and math.hypot(
            sauber[0][0] - sauber[-1][0], sauber[0][1] - sauber[-1][1]) < 1e-9:
        sauber.pop()
    pts = sauber
    n = len(pts)
    if n < 2 or (geschlossen and n < 3):
        return None
    d = abstand * seite
    kanten = []
    rng = range(n) if geschlossen else range(n - 1)
    for i in rng:
        a, b = pts[i], pts[(i + 1) % n]
        e = _einheit((b[0] - a[0], b[1] - a[1]))
        nx, ny = -e[1] * d, e[0] * d
        kanten.append(((a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny)))
    m = len(kanten)
    ecken = []
    if not geschlossen:
        ecken.append(kanten[0][0])
    idx = range(m) if geschlossen else range(1, m)
    for i in idx:
        k0, k1 = kanten[i - 1], kanten[i]
        s = schnitt_geraden(k0[0], k0[1], k1[0], k1[1])
        if s is None:
            s = k1[0]
        ecken.append(s)
    if not geschlossen:
        ecken.append(kanten[-1][1])
    # for closed polygons ecken[i] belongs to vertex i (edge i-1 -> edge i)
    # check: every new edge keeps its direction
    for i in range(m):
        if geschlossen:
            a, b = ecken[i], ecken[(i + 1) % n]
        else:
            a, b = ecken[i], ecken[i + 1]
        ka = kanten[i]
        if ((b[0] - a[0]) * (ka[1][0] - ka[0][0])
                + (b[1] - a[1]) * (ka[1][1] - ka[0][1])) <= 0:
            return None
    return ecken
