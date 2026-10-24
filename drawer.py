"""Generate drawer.svg: plan, front/right elevations, 3D perspective and part details
for the pan & lid storage system.

Axes (inches): x = left->right (W), y = front->back (D), z = up (H).
All parts are 3/8" baltic birch, 4" tall.
"""
import math
import os
from math import gcd

W, D, H = 32.375, 20.0, 9.5
S = 20  # px per inch in the flat views

# ---- parts geometry ---------------------------------------------------------
T = 0.375            # plywood thickness
PART_H = float(os.environ.get("PART_H", "4.0"))   # height of every part (nest.py may shrink it)
TAB_T = float(os.environ.get("TAB_T", "1.9375"))   # tab height on rail outer ply / dividers; under half the strip so nested tabs keep a gap
SLOT_CLR = 0.0       # extra slot depth beyond the tab height (to be set in the clearance pass)
TAB = TAB_T + SLOT_CLR   # slot depth from the top (supports, rail inner ply) - matches the tab height
SLOT_W = T           # support slot width: only the outer ply has tabs
PITCH = 1.0          # support slot pitch, center to center
X0 = 2.0             # left edge of slot 0 (leaves 2" spare at each end)
SLOTS = [X0 + PITCH * k for k in range(-1, 30)]          # 31 slots in the supports
RAIL_W = 2 * T       # glued outer + inner ply


def _rail(k, side):
    sx = SLOTS[k + 1]
    return (sx if side == "L" else sx - T, side, sx)


# rails: (left edge, 'L' = outer ply on the left i.e. left rail of a pair, support slot x)
RAILS = [_rail(0, "L"), _rail(14, "R"), _rail(17, "L"), _rail(28, "R")]
GAPS = [(RAILS[0][0] + RAIL_W, RAILS[1][0]), (RAILS[2][0] + RAIL_W, RAILS[3][0])]
NOTCH_YS = [D / 2 + 0.75 * (k + 0.5) for k in range(-12, 12)]  # 24 rail slots, 3/4" centers, centered
NOTCH_W = 0.375
DOWEL_YS = [1.0, 5.5, 10.0, 14.5, 19.0]   # 1/4" alignment dowel holes through both plies, outer ones 5/8" in from the body ends (symmetric, so plies can flip)
DOWEL_Z = 1.0
DOWEL_D = 0.25
BODY0, BODY1 = T, D - T                                    # rail body between the supports
# placeholder dividers: (gap index, y center) -- just to show how they sit
DIVIDERS = [(0, 7.375), (0, 12.625), (1, 10.375)]
USED = {r[2] for r in RAILS}

LINE = "#1f2937"
DIM = "#b45309"
FILL = "#f3f4f6"
GRID = "#d1d5db"
SUP = "#3b82f6"
ROUT = "#15803d"
RIN = "#4ade80"
DIVC = "#a855f7"
VOID = "#ffffff"


def shade(hexcol, f):
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % tuple(min(255, int(c * f)) for c in (r, g, b))


out = []
add = out.append


def frac(v):
    n = round(v * 16)
    whole, n = divmod(n, 16)
    if n == 0:
        return f'{whole}"'
    g = gcd(n, 16)
    f = f"{n // g}/{16 // g}"
    return f'{whole} {f}"' if whole else f'{f}"'


def rect(x, y, w, h, fill=FILL, stroke=LINE, sw=2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def line(x1, y1, x2, y2, stroke=LINE, sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def text(x, y, s, size=14, anchor="middle", fill=LINE, weight="normal", rot=None):
    r = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"{r}>{s}</text>')


def poly(pts, fill, stroke=LINE, sw=2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    s = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    add(f'<polygon points="{s}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"{d}/>')


TAB_R = 0.125  # radius on the outer corners of every tab (inches)


def rpoly(pts, fill, rounded, r, sw=1):
    """Polygon in px with a circular radius r (px) on the convex vertices listed in `rounded`."""
    n, d = len(pts), []
    for i, (x, y) in enumerate(pts):
        cmd = "L" if d else "M"
        if i not in rounded:
            d.append(f"{cmd}{x:.1f},{y:.1f}")
            continue
        (px_, py_), (nx, ny) = pts[i - 1], pts[(i + 1) % n]

        def toward(bx, by):
            k = r / math.hypot(bx - x, by - y)
            return x + (bx - x) * k, y + (by - y) * k
        a, b = toward(px_, py_), toward(nx, ny)
        sweep = 1 if (x - px_) * (ny - y) - (y - py_) * (nx - x) > 0 else 0
        d.append(f"{cmd}{a[0]:.1f},{a[1]:.1f} A{r:.1f},{r:.1f} 0 0 {sweep} {b[0]:.1f},{b[1]:.1f}")
    add(f'<path d="{" ".join(d)} Z" fill="{fill}" stroke="{LINE}" stroke-width="{sw}" stroke-linejoin="round"/>')


def dim_h(x1, x2, y, label, size=14):
    line(x1, y - 6, x1, y + 6, DIM)
    line(x2, y - 6, x2, y + 6, DIM)
    add(f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" stroke="{DIM}" stroke-width="1.2" marker-start="url(#arr)" marker-end="url(#arr)"/>')
    text((x1 + x2) / 2, y - 6, label, size, fill=DIM, weight="bold")


def dim_v(x, y1, y2, label):
    line(x - 6, y1, x + 6, y1, DIM)
    line(x - 6, y2, x + 6, y2, DIM)
    add(f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" stroke="{DIM}" stroke-width="1.2" marker-start="url(#arr)" marker-end="url(#arr)"/>')
    text(x - 8, (y1 + y2) / 2, label, 14, fill=DIM, weight="bold", rot=-90)


def rail_halves(xl, side):
    """((x0, x1, color) for the outer ply, same for the inner ply)."""
    if side == "L":
        return (xl, xl + T, ROUT), (xl + T, xl + RAIL_W, RIN)
    return (xl + T, xl + RAIL_W, ROUT), (xl, xl + T, RIN)


def notched(xa, xb, top, slots, depth):
    """Outline (u, v) of a strip with slots open at the top: slots = [(u0, u1), ...] ascending."""
    pts, rounded = [(xa, 0), (xa, top)], set()
    for s0, s1 in slots:
        rounded |= {len(pts), len(pts) + 3}  # the two finger corners flanking each slot
        pts += [(s0, top), (s0, top - depth), (s1, top - depth), (s1, top)]
    return pts + [(xb, top), (xb, 0)], rounded | {0, 1, len(pts), len(pts) + 1}   # plus the four outer plate corners


def divider_ys(gap_index):
    return [y for g, y in DIVIDERS if g == gap_index]


CW, CH = 1700, 1300
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" font-family="Helvetica, Arial, sans-serif">')
add('<defs><marker id="arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
    f'<path d="M0,1 L10,5 L0,9 z" fill="{DIM}"/></marker></defs>')
add(f'<rect width="{CW}" height="{CH}" fill="#ffffff"/>')
text(40, 48, "Pan &amp; Lid Drawer Storage", 26, "start", weight="bold")
text(40, 72, f"Drawer interior {frac(W)} W  x  {frac(D)} D  x  {frac(H)} H   (grid = 4&quot;)   |   all parts 3/8&quot; baltic birch, 4&quot; tall", 15, "start", fill="#6b7280")

# legend
lx = 1000
for i, (col, name) in enumerate([(SUP, "Supports (2)"), (ROUT, "Rail outer ply (4)"), (RIN, "Rail inner ply (4)"), (DIVC, "Dividers (examples)")]):
    rect(lx + i * 175, 30, 18, 18, col, LINE, 1)
    text(lx + i * 175 + 26, 44, name, 13, "start")

# ---------------- Plan (top) view ----------------
px, py = 110, 130
pw, ph = W * S, D * S


def pp(x, y):
    return px + x * S, py + ph - y * S


def prect(x0, x1, y0, y1, fill, sw=1):
    a, b = pp(x0, y1), pp(x1, y0)
    rect(a[0], a[1], b[0] - a[0], b[1] - a[1], fill, LINE, sw)


text(px, py - 22, "PLAN (top)", 16, "start", weight="bold")
rect(px, py, pw, ph)
for gx in range(4, int(W) + 1, 4):
    line(px + gx * S, py, px + gx * S, py + ph, GRID)
for gy in range(4, int(D) + 1, 4):
    line(px, py + ph - gy * S, px + pw, py + ph - gy * S, GRID)
for y0, y1 in ((0, T), (D - T, D)):
    prect(0, W, y0, y1, SUP)
    for sx in SLOTS:
        if sx not in USED:
            prect(sx, sx + SLOT_W, y0, y1, VOID)
for xl, side, _ in RAILS:
    outer, inner = rail_halves(xl, side)
    prect(outer[0], outer[1], 0, D, outer[2])
    prect(inner[0], inner[1], BODY0, BODY1, inner[2])
    for yc in NOTCH_YS:
        prect(inner[0], inner[1], yc - NOTCH_W / 2, yc + NOTCH_W / 2, VOID, 0.6)
for gi, (gl, gr) in enumerate(GAPS):
    for yc in divider_ys(gi):
        prect(gl - T, gr + T, yc - T / 2, yc + T / 2, DIVC)
text(px + pw + 14, py + ph - 4, "FRONT", 12, "start", fill="#6b7280")
text(px + pw + 14, py + 14, "BACK", 12, "start", fill="#6b7280")
dim_h(px, px + pw, py + ph + 34, frac(W))
dim_v(px - 34, py, py + ph, frac(D))
# chain of dimensions along the width
xa, xb = RAILS[0][0], RAILS[1][0] + RAIL_W
xc, xd = RAILS[2][0], RAILS[3][0] + RAIL_W
chain = [0, xa, GAPS[0][0], GAPS[0][1], xb, xc, GAPS[1][0], GAPS[1][1], xd, W]
cy = py + ph + 76
for a, b in zip(chain, chain[1:]):
    line(px + a * S, cy - 6, px + a * S, cy + 6, DIM)
    line(px + a * S, cy, px + b * S, cy, DIM, 1.2)
    if b - a > 1:
        text(px + (a + b) / 2 * S, cy - 6, frac(b - a), 12, fill=DIM, weight="bold")
line(px + W * S, cy - 6, px + W * S, cy + 6, DIM)
text(px, cy + 20, "spare / rail 3/4&quot; / gap / rail 3/4&quot; / spare / rail / gap / rail / spare", 11, "start", fill="#6b7280")

# ---------------- Front elevation ----------------
fx, fy = px, py + ph + 150
fw, fh = W * S, H * S


def fp(x, z):
    return fx + x * S, fy + fh - z * S


def frect(x0, x1, z0, z1, fill, sw=1):
    a, b = fp(x0, z1), fp(x1, z0)
    rect(a[0], a[1], b[0] - a[0], b[1] - a[1], fill, LINE, sw)


text(fx, fy - 22, "FRONT ELEVATION (front support in front of everything)", 16, "start", weight="bold")
rect(fx, fy, fw, fh)
for gx in range(4, int(W) + 1, 4):
    line(fx + gx * S, fy, fx + gx * S, fy + fh, GRID)
for gz in range(4, int(H) + 1, 4):
    line(fx, fy + fh - gz * S, fx + fw, fy + fh - gz * S, GRID)
_pts, _rnd = notched(0, W, PART_H, [(s, s + SLOT_W) for s in SLOTS], TAB)
rpoly([fp(u, v) for u, v in _pts], SUP, _rnd, TAB_R * S)
for sx in SLOTS:
    if sx in USED:
        frect(sx, sx + SLOT_W, PART_H - TAB_T, PART_H, ROUT)
dim_h(fx, fx + fw, fy + fh + 34, frac(W))
dim_v(fx - 34, fy, fy + fh, frac(H))
dim_v(fx + fw + 26, fy + fh - PART_H * S, fy + fh, '4"')
dim_v(fx + fw + 54, fy + fh - PART_H * S, fy + fh - (PART_H - TAB) * S, f'{TAB:g}"')

# ---------------- Right side elevation ----------------
sx0, sy0 = fx + fw + 120, fy
sw_, sh_ = D * S, H * S


def sp(y, z):
    return sx0 + y * S, sy0 + sh_ - z * S


text(sx0, sy0 - 22, "RIGHT ELEVATION", 16, "start", weight="bold")
rect(sx0, sy0, sw_, sh_)
for gy in range(4, int(D) + 1, 4):
    line(sx0 + gy * S, sy0, sx0 + gy * S, sy0 + sh_, GRID)
for gz in range(4, int(H) + 1, 4):
    line(sx0, sy0 + sh_ - gz * S, sx0 + sw_, sy0 + sh_ - gz * S, GRID)
rail_profile = [(0, PART_H), (D, PART_H), (D, PART_H - TAB_T), (BODY1, PART_H - TAB_T),
                (BODY1, 0), (BODY0, 0), (BODY0, PART_H - TAB_T), (0, PART_H - TAB_T)]
rpoly([sp(y, z) for y, z in rail_profile], ROUT, {0, 1, 2, 4, 5, 7}, TAB_R * S)
for y0, y1 in ((0, T), (D - T, D)):
    a, b = sp(y0, PART_H), sp(y1, 0)
    rect(a[0], a[1], b[0] - a[0], b[1] - a[1], SUP, LINE, 1)
text(sx0 + 4, sy0 + sh_ + 56, "FRONT", 12, "start", fill="#6b7280")
text(sx0 + sw_ - 4, sy0 + sh_ + 56, "BACK", 12, "end", fill="#6b7280")
dim_h(sx0, sx0 + sw_, sy0 + sh_ + 34, frac(D))
dim_v(sx0 + sw_ + 34, sy0, sy0 + sh_, frac(H))

# ---------------- 3D perspective ----------------
YAW, PITCH_A = math.radians(-28), math.radians(28)
CAM_DIST, FOCAL = 120.0, 100.0


def proj(x, y, z):
    x, y, z = x - W / 2, y - D / 2, z - H / 2
    x1 = x * math.cos(YAW) - y * math.sin(YAW)
    y1 = x * math.sin(YAW) + y * math.cos(YAW)
    y2 = y1 * math.cos(PITCH_A) - z * math.sin(PITCH_A)
    z2 = y1 * math.sin(PITCH_A) + z * math.cos(PITCH_A)
    k = FOCAL / (CAM_DIST + y2)
    return x1 * k, -z2 * k


corners = [proj(x, y, z) for x in (0, W) for y in (0, D) for z in (0, H)]
minx, maxx = min(c[0] for c in corners), max(c[0] for c in corners)
miny, maxy = min(c[1] for c in corners), max(c[1] for c in corners)
box_x, box_y, box_w, box_h = 880, 100, 780, 520
sc = min(box_w / (maxx - minx), box_h / (maxy - miny)) * 0.95
ox = box_x + box_w / 2 - (minx + maxx) / 2 * sc
oy = box_y + box_h / 2 - (miny + maxy) / 2 * sc


def P(x, y, z):
    a, b = proj(x, y, z)
    return ox + a * sc, oy + b * sc


def face(pts3, fill, sw=0.8):
    poly([P(*p) for p in pts3], fill, LINE, sw)


def pline(p, q, stroke=GRID, sw=1, dash=None):
    line(p[0], p[1], q[0], q[1], stroke, sw, dash)


def box3(x0, x1, y0, y1, z0, z1, col, top=True, front=True, right=True):
    if right:
        face([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], shade(col, .7))
    if front:
        face([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], shade(col, .85))
    if top:
        face([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], col)


_cy1 = -CAM_DIST * math.cos(PITCH_A)
CAM = (_cy1 * math.sin(YAW) + W / 2, _cy1 * math.cos(YAW) + D / 2, CAM_DIST * math.sin(PITCH_A) + H / 2)


def rounded_profile(pts, rounded, r, n=4):
    """Expand the listed convex vertices into n-segment arcs; returns (points, smooth-edge flags)."""
    res, smooth, m = [], [], len(pts)
    for i, (x, y) in enumerate(pts):
        if i not in rounded:
            res.append((x, y))
            smooth.append(False)
            continue
        (px_, py_), (nx, ny) = pts[i - 1], pts[(i + 1) % m]
        ux, uy = px_ - x, py_ - y
        l = math.hypot(ux, uy)
        ux, uy = ux / l, uy / l
        vx, vy = nx - x, ny - y
        l = math.hypot(vx, vy)
        vx, vy = vx / l, vy / l
        cx, cy = x + (ux + vx) * r, y + (uy + vy) * r
        a0, a1 = math.atan2(-vy, -vx), math.atan2(-uy, -ux)
        d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n + 1):
            t = a0 + d * k / n
            res.append((cx + r * math.cos(t), cy + r * math.sin(t)))
            smooth.append(k < n)
    return res, smooth


FACE_HOOK = None   # optional callback(kind, px_points, extra) for each prism face; perspective.py uses it for the wood look


def prism(profile, rounded, plane, off0, off1, col, skip_x_right=False, skip_top=False):
    """Extrude a (u, v) profile: plane 'yz' extrudes along +x, 'xz' along +y."""
    pts, smooth = rounded_profile(profile, rounded, TAB_R)
    m = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % m][1] - pts[(i + 1) % m][0] * pts[i][1] for i in range(m))
    sgn = 1 if area > 0 else -1

    def to3(u, v, off):
        return (off, u, v) if plane == "yz" else (u, off, v)

    def nrm(nu, nv):
        return (0, nu, nv) if plane == "yz" else (nu, 0, nv)

    def visible(n, pt):
        return sum(n[k] * (CAM[k] - pt[k]) for k in range(3)) > 0

    def bright(n):
        return min(1.0, .7 + .3 * max(n[2], 0) + .15 * max(-n[1], 0))

    for i in range(m):
        p, q = pts[i], pts[(i + 1) % m]
        du, dv = q[0] - p[0], q[1] - p[1]
        l = math.hypot(du, dv)
        if l < 1e-9:
            continue
        n = nrm(sgn * dv / l, -sgn * du / l)
        if not visible(n, to3((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (off0 + off1) / 2)):
            continue
        if skip_x_right and n[0] > 0.99:
            continue
        if skip_top and n[2] > 0.99:
            continue
        c = shade(col, bright(n))
        quad = [P(*to3(*p, off0)), P(*to3(*q, off0)), P(*to3(*q, off1)), P(*to3(*p, off1))]
        poly(quad, c, c if smooth[i] else LINE, 0.6 if smooth[i] else 0.8)
        if FACE_HOOK:
            FACE_HOOK("edge", quad, smooth[i])
    axis = (1, 0, 0) if plane == "yz" else (0, 1, 0)
    for n, off in (((-axis[0], -axis[1], 0), off0), (axis, off1)):
        if visible(n, to3(pts[0][0], pts[0][1], off)):
            cap = [P(*to3(*p, off)) for p in pts]
            poly(cap, shade(col, bright(n)), LINE, 0.8)
            if FACE_HOOK:
                FACE_HOOK("cap", cap, plane)


def support3(y0, y1):
    prism([(0, 0), (W, 0), (W, PART_H - TAB), (0, PART_H - TAB)], {0, 1}, "xz", y0, y1, SUP, skip_top=True)
    for sx in SLOTS:  # slot floors
        if sx not in USED:
            face([(sx, y0, PART_H - TAB), (sx + SLOT_W, y0, PART_H - TAB), (sx + SLOT_W, y1, PART_H - TAB), (sx, y1, PART_H - TAB)], shade(SUP, .6))
    edges = [0.0]
    for sx in SLOTS:
        edges += [sx, sx + SLOT_W]
    edges.append(W)
    for a, b in zip(edges[0::2], edges[1::2]):
        # a wall next to a used slot is hidden by the rail
        hidden = any(abs(b - sx) < 1e-9 and sx in USED for sx in SLOTS)
        rnd = {2, 3}
        prism([(a, PART_H - TAB), (b, PART_H - TAB), (b, PART_H), (a, PART_H)], rnd, "xz", y0, y1, SUP, skip_x_right=hidden)


RAIL_PROFILE = [(0, PART_H), (D, PART_H), (D, PART_H - TAB_T), (BODY1, PART_H - TAB_T),
                (BODY1, 0), (BODY0, 0), (BODY0, PART_H - TAB_T), (0, PART_H - TAB_T)]


def rail3(xl, side, ys):
    outer, inner = rail_halves(xl, side)
    for x0, x1, col in sorted([outer, inner]):
        if (x0, x1, col) == outer:   # outer ply has the end tabs
            prism(RAIL_PROFILE, {0, 1, 2, 4, 5, 7}, "yz", x0, x1, col)
        else:                        # inner ply stops at the supports; slots are real geometry
            prof, rnd = notched(BODY0, BODY1, PART_H, [(yc - NOTCH_W / 2, yc + NOTCH_W / 2) for yc in NOTCH_YS], TAB)
            prism(prof, rnd, "yz", x0, x1, col)
    for yc in NOTCH_YS:
        if yc in ys:  # divider tab fills the slot
            y0, y1 = yc - NOTCH_W / 2, yc + NOTCH_W / 2
            face([(inner[0], y0, PART_H), (inner[1], y0, PART_H), (inner[1], y1, PART_H), (inner[0], y1, PART_H)], DIVC)


BOX_EDGE = "#1f2937"


def drawer_box():
    """The drawer interior: back wall, left wall and floor with a 4" grid; the front and right sides are
    left open and shown dashed. Shared by the drawing and perspective.py so both look identical."""
    poly([P(0, D, 0), P(W, D, 0), P(W, D, H), P(0, D, H)], "#e5e7eb")
    poly([P(0, 0, 0), P(0, D, 0), P(0, D, H), P(0, 0, H)], "#d1d5db")
    poly([P(0, 0, 0), P(W, 0, 0), P(W, D, 0), P(0, D, 0)], "#f9fafb")
    for gx in range(4, int(W) + 1, 4):
        pline(P(gx, 0, 0), P(gx, D, 0))
        pline(P(gx, D, 0), P(gx, D, H))
    for gy in range(4, int(D), 4):
        pline(P(0, gy, 0), P(W, gy, 0))
        pline(P(0, gy, 0), P(0, gy, H))
    for gz in range(4, int(H) + 1, 4):
        pline(P(0, D, gz), P(W, D, gz))
        pline(P(0, 0, gz), P(0, D, gz))
    for p, q in [((0, D, 0), (W, D, 0)), ((0, D, 0), (0, 0, 0)), ((W, D, 0), (W, 0, 0)), ((0, 0, 0), (W, 0, 0)),
                 ((0, D, 0), (0, D, H)), ((W, D, 0), (W, D, H)), ((0, 0, 0), (0, 0, H)),
                 ((0, D, H), (W, D, H)), ((0, D, H), (0, 0, H))]:
        pline(P(*p), P(*q), BOX_EDGE, 2)
    for p, q in [((W, D, H), (W, 0, H)), ((0, 0, H), (W, 0, H)), ((W, 0, 0), (W, 0, H))]:
        pline(P(*p), P(*q), "#6b7280", 1.5, "6 4")


text(box_x, py - 22, "PERSPECTIVE (front and right walls omitted for clarity)", 16, "start", weight="bold")
drawer_box()

support3(D - T, D)
items = []
for i, (xl, side, _) in enumerate(RAILS):
    items.append((xl, 0, "rail", xl, side, divider_ys(i // 2)))
for gi, (gl, gr) in enumerate(GAPS):
    for yc in divider_ys(gi):
        items.append((gl, -yc, "div", gl, gr, yc))
for it in sorted(items, key=lambda t: (t[0], t[1])):
    if it[2] == "rail":
        rail3(it[3], it[4], it[5])
    else:
        gl, gr, yc = it[3], it[4], it[5]
        box3(gl, gr, yc - T / 2, yc + T / 2, 0, PART_H, DIVC)
support3(0, T)

a, b = P(0, 0, H), P(W, 0, H)
text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 26, frac(W), 14, fill=DIM, weight="bold")
a, b = P(W, 0, H), P(W, D, H)
text((a[0] + b[0]) / 2 + 24, (a[1] + b[1]) / 2 - 8, frac(D), 14, fill=DIM, weight="bold")
a, b = P(0, 0, 0), P(0, 0, H)
text(a[0] - 14, (a[1] + b[1]) / 2, frac(H), 14, "end", fill=DIM, weight="bold")

# ---------------- Part details ----------------
ty = 980
text(110, ty, "PARTS (cut list)", 18, "start", weight="bold")


def dp(ox_, oy_, h, pts, fill, sw=1, rounded=()):
    px_pts = [(ox_ + u * S, oy_ + h * S - v * S) for u, v in pts]
    if rounded:
        rpoly(px_pts, fill, rounded, TAB_R * S, sw)
    else:
        poly(px_pts, fill, LINE, sw)


def drect(ox_, oy_, h, u0, u1, v0, v1, fill, sw=1):
    rect(ox_ + u0 * S, oy_ + h * S - v1 * S, (u1 - u0) * S, (v1 - v0) * S, fill, LINE, sw)


# support
sy1 = ty + 40
_pts, _rnd = notched(0, W, 4, [(s, s + SLOT_W) for s in SLOTS], TAB)
dp(110, sy1, 4, _pts, SUP, rounded=_rnd)
text(110, sy1 + 4 * S + 22, f"SUPPORT x2   {frac(W)} x 4&quot; x 3/8&quot;   |   {len(SLOTS)} slots, 3/8&quot; wide x {TAB:g}&quot; deep, 1&quot; centers, first slot at {frac(SLOTS[0])}", 14, "start", weight="bold")

# rail plies
ry = sy1 + 4 * S + 80
rail_profile_uv = rail_profile
dp(110, ry, 4, rail_profile_uv, ROUT, rounded={0, 1, 2, 4, 5, 7})
BL = BODY1 - BODY0
_pts, _rnd = notched(0, BL, 4, [(yc - BODY0 - NOTCH_W / 2, yc - BODY0 + NOTCH_W / 2) for yc in NOTCH_YS], TAB)
dp(560, ry, 4, _pts, RIN, rounded=_rnd)
for _y in DOWEL_YS:
    for _ox, _u in ((110, _y), (560, _y - BODY0)):
        add(f'<circle cx="{_ox + _u * S:.1f}" cy="{ry + (4 - DOWEL_Z) * S:.1f}" r="{DOWEL_D / 2 * S:.1f}" fill="#ffffff" stroke="{LINE}" stroke-width="1"/>')
text(110, ry + 4 * S + 72, f"{len(DOWEL_YS)} x 1/4&quot; dowel holes, {', '.join(frac(y) for y in DOWEL_YS)} from front, 1&quot; up", 12, "start", fill="#374151")
text(560, ry + 4 * S + 72, f"same {len(DOWEL_YS)} dowel holes, same positions (aligns to outer ply)", 12, "start", fill="#374151")
text(110, ry + 4 * S + 22, "RAIL OUTER PLY x4", 14, "start", weight="bold")
text(110, ry + 4 * S + 40, f"{frac(D)} x 4&quot; x 3/8&quot;; end tabs {TAB_T:g}&quot; tall x 3/8&quot; long (body {frac(BODY1 - BODY0)} between supports)", 12, "start", fill="#374151")
text(110, ry + 4 * S + 56, "all outside corners R 1/8&quot;", 12, "start", fill="#374151")
text(560, ry + 4 * S + 22, "RAIL INNER PLY x4", 14, "start", weight="bold")
text(560, ry + 4 * S + 40, f"{frac(BL)} x 4&quot; x 3/8&quot;, no tabs; {len(NOTCH_YS)} slots 3/8&quot; wide x {TAB:g}&quot; deep, 3/4&quot; centers", 12, "start", fill="#374151")
text(560, ry + 4 * S + 56, "glue inner + outer: 3/4&quot; thick rail", 12, "start", fill="#374151")

# dividers
for i, (gi, label, qty) in enumerate([(0, "A", 2), (1, "B", 1)]):
    gl, gr = GAPS[gi]
    g = gr - gl
    L = g + 2 * T
    ox_ = 1010 if i == 0 else 1010 + (GAPS[0][1] - GAPS[0][0] + 2 * T) * S + 40
    ts = PART_H - TAB_T
    dp(ox_, ry, 4, [(0, PART_H), (L, PART_H), (L, ts), (L - T, ts), (L - T, 0), (T, 0), (T, ts), (0, ts)], DIVC, rounded={0, 1, 2, 4, 5, 7})
    text(ox_, ry + 4 * S + 22, f"DIVIDER {label} (example x{qty})", 14, "start", weight="bold")
    text(ox_, ry + 4 * S + 40, f"top {frac(L)}, body {frac(g)} x 4&quot; x 3/8&quot;", 12, "start", fill="#374151")
    text(ox_, ry + 4 * S + 56, f"tabs {TAB_T:g}&quot; tall x 3/8&quot; long, corners R 1/8&quot;", 12, "start", fill="#374151")

add("</svg>")

if PART_H == 4.0:  # an overridden part height (used by nest.py) must not overwrite the drawing
    with open("drawer.svg", "w") as f:
        f.write("\n".join(out))
    print("wrote drawer.svg")
