"""Write perspective.svg: just the 3D view of the finished assembly, with a birch plywood look.

Reuses the geometry and 3D drawing code from drawer.py (final 3.75" strips, 1 3/4" tabs and slots) and
adds veneer grain on the broad faces and the layered plies on the cut edges.
"""
import math
import os

os.environ["PART_H"] = "3.75"     # final strip height; drawer.py then leaves drawer.svg alone
os.environ["TAB_T"] = "1.75"

import drawer as d

W_PX, H_PX = 1400, 900


# ---- wood colours ------------------------------------------------------------------
BASE = (238, 219, 176)                      # birch veneer
VARIATION = {d.SUP: 1.00, d.ROUT: 0.965, d.RIN: 1.02, d.DIVC: 0.985}   # slightly different sheets


def wood(col, f):
    v = VARIATION.get(col, 1.0) * f
    return "#%02x%02x%02x" % tuple(min(255, int(c * v)) for c in BASE)


def tone(rgb, f):
    return "#%02x%02x%02x" % tuple(min(255, int(c * f)) for c in rgb)


d.shade = wood
d.DIVC = "#%02x%02x%02x" % tuple(int(c * 0.985) for c in BASE)    # divider tab tops are drawn with the raw colour
d.LINE = "#6f5128"                                                  # outlines: dark wood, not black


# ---- projection fit ------------------------------------------------------------------
pts = [d.proj(x, y, z) for x in (0, d.W) for y in (0, d.D) for z in (0, d.H)]
minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
box = (90, 70, W_PX - 180, H_PX - 140)
d.sc = min(box[2] / (maxx - minx), box[3] / (maxy - miny))
d.ox = box[0] + box[2] / 2 - (minx + maxx) / 2 * d.sc
d.oy = box[1] + box[3] / 2 - (miny + maxy) / 2 * d.sc


def screen_angle(a, b):
    (x0, y0), (x1, y1) = d.P(*a), d.P(*b)
    return math.degrees(math.atan2(y1 - y0, x1 - x0))


ANGLE = {"xz": screen_angle((0, 10, 2), (1, 10, 2)), "yz": screen_angle((16, 0, 2), (16, 1, 2))}

# ---- per-face wood effects -----------------------------------------------------------
n_clip = 0


def lerp(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def pts_attr(poly_pts):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in poly_pts)


def hook(kind, poly_pts, extra):
    global n_clip
    if kind == "edge":
        if extra:                      # tiny arc segments: skip the ply lines
            return
        p0, q0, q1, p1 = poly_pts
        d.add(f'<polygon points="{pts_attr(poly_pts)}" fill="#b98f52" fill-opacity="0.30"/>')
        for k in range(1, 5):          # 5-ply baltic birch: four glue lines through the thickness
            a, b = lerp(p0, p1, k / 5), lerp(q0, q1, k / 5)
            d.add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                  f'stroke="#8a6532" stroke-width="0.45" stroke-opacity="{0.75 if k % 2 else 0.45}"/>')
    else:                              # broad veneer face: grain along the part
        n_clip += 1
        xs, ys = [p[0] for p in poly_pts], [p[1] for p in poly_pts]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        r = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 2
        d.add(f'<clipPath id="g{n_clip}"><polygon points="{pts_attr(poly_pts)}"/></clipPath>'
              f'<g clip-path="url(#g{n_clip})"><rect x="{cx - r:.1f}" y="{cy - r:.1f}" width="{2 * r:.1f}" height="{2 * r:.1f}" '
              f'transform="rotate({ANGLE[extra]:.1f} {cx:.1f} {cy:.1f})" filter="url(#grain)" opacity="0.42"/></g>')


d.FACE_HOOK = hook

# ---- scene ---------------------------------------------------------------------------
d.out.clear()
d.add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_PX} {H_PX}" font-family="Helvetica, Arial, sans-serif">')
d.add('''<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f6f3ec"/><stop offset="1" stop-color="#e6e0d2"/></linearGradient>
<filter id="grain" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="0.010 0.40" numOctaves="3" seed="11"/>
  <feColorMatrix type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.29  0 0 0 0 0.11  1.9 0 0 0 -0.60"/>
</filter>
<filter id="blur"><feGaussianBlur stdDeviation="14"/></filter>
</defs>''')
d.add(f'<rect width="{W_PX}" height="{H_PX}" fill="url(#bg)"/>')

W_, D_, H_ = d.W, d.D, d.H
P = d.P
# soft shadow on the "table" under the drawer
sh = [P(0, 0, 0), P(W_, 0, 0), P(W_, D_, 0), P(0, D_, 0)]
d.add(f'<polygon points="{pts_attr([(x + 10, y + 22) for x, y in sh])}" fill="#1f2937" opacity="0.18" filter="url(#blur)"/>')

# the drawer box, drawn exactly as in drawer.svg (gray faces, 4" grid, dashed open edges)
d.drawer_box()

# assembly, back to front
d.support3(d.D - d.T, d.D)
items = []
for i, (xl, side, _) in enumerate(d.RAILS):
    items.append((xl, 0, "rail", xl, side, d.divider_ys(i // 2)))
for gi, (gl, gr) in enumerate(d.GAPS):
    for yc in d.divider_ys(gi):
        items.append((gl, -yc, "div", gl, gr, yc))
for it in sorted(items, key=lambda t: (t[0], t[1])):
    if it[2] == "rail":
        d.rail3(it[3], it[4], it[5])
    else:
        gl, gr, yc = it[3], it[4], it[5]
        d.prism([(gl, 0), (gr, 0), (gr, d.PART_H), (gl, d.PART_H)], {0, 1}, "xz", yc - d.T / 2, yc + d.T / 2, d.DIVC)
d.support3(0, d.T)
d.add("</svg>")

open("perspective.svg", "w").write("\n".join(d.out))
print("wrote perspective.svg")
