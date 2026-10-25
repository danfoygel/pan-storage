"""Nest every part onto one 48" x 34" sheet; write layout_48x34in.svg (preview) + cut_48x34in_sheet1.svg (1:1, inches).

Geometry comes from drawer.py: fingered parts (supports, rail inner plies) are 2 1/2" tall, plain parts (rail
outer plies, dividers) are 4" tall, tabs and slots are 1". Parts run along the 48" side, so the grain
(along the 48" side) runs across the strips and along the fingers.

The layout is two "bands" followed by four single rows (stack, top to bottom):
  band 1  (2 plain rows tall): 3 fingered strips (S, S, I) on the left, 2 x divider A on the right
  band 2  (2 plain rows tall): 3 fingered strips (I, I, I) on the left, 4 x divider A (2 pairs) on the right
  rows 5-8: one rail outer ply per row with dividers (O A B, O B B, O B B, O B B)
A band is as tall as two plain rows and a gap, which also holds three 2 1/2" strips with room to spare.
The tabs of the plain parts run from the slot floor to the top, taller than the notch beside them, so neighbouring plain parts cannot interlock.

usage: python3 nest.py [gap]      (default gap: spread the spare height evenly, rounded down to 0.001")
       SHEET_H=34 sets the sheet length (default 34)
"""
import math
import os
import sys

import drawer as d

EDGE = 0.25                     # padding at all four sheet edges (minimum)
SHEET_W, SHEET_H = 48.0, float(os.environ.get("SHEET_H", "34"))
T, TAB_R = d.T, d.TAB_R
H_F, H_P = d.H_FING, d.H_PLAIN
ROWS = 8                        # plain-row heights in the stack (2 + 2 + 4)
G = float(sys.argv[1]) if len(sys.argv) > 1 else math.floor((SHEET_H - 2 * EDGE - ROWS * H_P) / (ROWS - 1) * 1000) / 1000
NEED = {"S": 2, "I": 4, "O": 4, "A": 7, "B": 7}    # parts in the system


# ---- parts (profiles in (u along length, v up)) ------------------------------
def part(kind, name, pts, rnd, holes, L, h, tabbed, col):
    return dict(kind=kind, name=name, pts=pts, rnd=rnd, holes=holes, L=L, H=h, tabbed=tabbed, col=col)


def make_parts():
    sp, sr = d.notched(0, d.W, H_F, [(s, s + d.SLOT_W) for s in d.SLOTS], d.TAB)
    ip, ir = d.notched(d.BODY0, d.BODY1, H_F, [(y - d.NOTCH_W / 2, y + d.NOTCH_W / 2) for y in d.NOTCH_YS], d.TAB)
    ip = [(u - d.BODY0, v) for u, v in ip]
    out = {
        "S": part("S", "SUPPORT", sp, sr, [], d.W, H_F, False, d.SUP),
        "I": part("I", "RAIL INNER", ip, ir, [(y - d.BODY0, d.DOWEL_Z) for y in d.DOWEL_YS], d.BODY1 - d.BODY0, H_F, False, d.RIN),
        "O": part("O", "RAIL OUTER", d.RAIL_PROFILE, d.RAIL_RND, [(y, d.DOWEL_Z) for y in d.DOWEL_YS], d.D, H_P, True, d.ROUT),
    }
    for k, gi, col in (("A", 0, d.DIVC), ("B", 1, "#c084fc")):
        gl, gr = d.GAPS[gi]
        L = gr - gl + 2 * T
        dpts, drnd = d.divider_profile(L)
        out[k] = part(k, f"DIVIDER {k}  {d.frac(gr - gl)} gap", dpts, drnd, [], L, H_P, True, col)
    return out


PARTS = make_parts()


def path_d(pts, rounded, r):
    n, parts = len(pts), []
    for i, (x, y) in enumerate(pts):
        cmd = "L" if parts else "M"
        if i not in rounded:
            parts.append(f"{cmd}{x:.4f},{y:.4f}")
            continue
        (px, py), (nx, ny) = pts[i - 1], pts[(i + 1) % n]
        ka, kb = r / math.hypot(px - x, py - y), r / math.hypot(nx - x, ny - y)
        a = (x + (px - x) * ka, y + (py - y) * ka)
        b = (x + (nx - x) * kb, y + (ny - y) * kb)
        sweep = 1 if (x - px) * (ny - y) - (y - py) * (nx - x) > 0 else 0
        parts.append(f"{cmd}{a[0]:.4f},{a[1]:.4f} A{r},{r} 0 0 {sweep} {b[0]:.4f},{b[1]:.4f}")
    return " ".join(parts) + " Z"


PLACED, VIEW, TALLY = [], [], {}
CUTG = {"holes": [], "fingers": [], "plain": []}   # cut-file elements by operation


def put(key, x0, ytop, inv):
    """Place a part with its left edge at x0 and the top of its strip at ytop; inv = turned 180 degrees."""
    p = PARTS[key]
    L, h = p["L"], p["H"]

    def tf(u, v):
        return (x0 + L - u, ytop + v) if inv else (x0 + u, ytop + h - v)
    pts, holes = [tf(*q) for q in p["pts"]], [tf(*q) for q in p["holes"]]
    dd = path_d(pts, p["rnd"], TAB_R)
    PLACED.append(dict(name=p["name"], pts=d.rounded_profile(pts, p["rnd"], TAB_R, n=6)[0], holes=holes))
    TALLY[key] = TALLY.get(key, 0) + 1
    CUTG["fingers" if key in "SI" else "plain"].append(f'<path d="{dd}"/>')
    CUTG["holes"] += [f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{d.DOWEL_D / 2}"/>' for x, y in holes]
    VIEW.append(f'<path d="{dd}" fill="{p["col"]}" stroke="#1f2937" stroke-width="0.03" stroke-linejoin="round"/>')
    VIEW.extend(f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{d.DOWEL_D / 2}" fill="#ffffff" stroke="#1f2937" stroke-width="0.02"/>' for x, y in holes)
    VIEW.append(f'<text x="{x0 + L / 2:.3f}" y="{ytop + (1.0 if key == "O" else h / 2 + 0.15):.3f}" font-size="0.42" text-anchor="middle" fill="#111827">{p["name"].split("  ")[0]}</text>')
    return x0 + L


def row(keys, ytop, x_from=0.0, x_to=SHEET_W):
    """Parts left to right in [x_from, x_to] with padding = every gap (centred if alone). The tabs reach
    from the slot floor to the top, so neighbouring parts cannot interlock and each counts its full length."""
    parts = [PARTS[k] for k in keys]
    space = (x_to - x_from - sum(p["L"] for p in parts)) / (len(parts) + 1)
    x = x_from + space
    for k, p in zip(keys, parts):
        x = put(k, x, ytop, False) + space


def column(keys_dirs, y0, y1, x0):
    """Stack fingered strips between y0 and y1 with equal gaps; 'up' = fingers toward the top of the sheet.
    Fingers never face fingers: they point away, or at the solid back of the neighbouring strip."""
    gap = (y1 - y0 - H_F * len(keys_dirs)) / (len(keys_dirs) - 1)
    for i, (k, dr) in enumerate(keys_dirs):
        put(k, x0, y0 + i * (H_F + gap), dr == "down")


def build():
    y = EDGE
    band = 2 * H_P + G
    # band 1: S, S, I stacked on the left, divider A in each of the two plain rows on the right
    fx = (SHEET_W - (d.W + PARTS["A"]["L"])) / 3
    column([("S", "up"), ("S", "up"), ("I", "up")], y, y + band, fx)
    for i in range(2):
        put("A", 2 * fx + d.W, y + i * (H_P + G), False)
    y += band + G
    # band 2: I, I, I on the left, a pair of divider A in each of the two plain rows on the right
    pair_w = 2 * PARTS["A"]["L"]
    fx = (SHEET_W - (PARTS["I"]["L"] + pair_w)) / 3
    column([("I", "down"), ("I", "down"), ("I", "down")], y, y + band, fx)
    for i in range(2):
        row(["A", "A"], y + i * (H_P + G), fx + PARTS["I"]["L"], SHEET_W)
    y += band + G
    for keys in (["O", "A", "B"], ["O", "B", "B"], ["O", "B", "B"], ["O", "B", "B"]):
        row(keys, y)
        y += H_P + G
    return y - G + EDGE    # stack height used, including the bottom padding


STACK_USED = build()


# ---- layout check: overlaps, spacing, edge padding ---------------------------------
def _pt_seg(px, py, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / l2))
    cx, cy = a[0] + t * dx, a[1] + t * dy
    return math.hypot(px - cx, py - cy), (cx, cy)


def _cross(a, b, c, e):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, e) < 0 and o(c, e, a) * o(c, e, b) < 0


def _inside(pt, poly):
    x, y, inside = pt[0], pt[1], False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _bbox(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def poly_relation(A, B):
    """(crossing/containment?, smallest distance, point midway between the closest pair)."""
    a0, a1, a2, a3 = _bbox(A)
    b0, b1, b2, b3 = _bbox(B)
    if max(b0 - a2, a0 - b2, b1 - a3, a1 - b3) > G + 0.05:
        return False, math.inf, None
    best, where, crossing = math.inf, None, False
    sa = [(A[i], A[(i + 1) % len(A)]) for i in range(len(A))]
    sb = [(B[i], B[(i + 1) % len(B)]) for i in range(len(B))]
    for p, q in sa:
        pb = (min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1]))
        for r, s in sb:
            if max(min(r[0], s[0]) - pb[2], pb[0] - max(r[0], s[0]), min(r[1], s[1]) - pb[3], pb[1] - max(r[1], s[1])) > G + 0.05:
                continue
            if _cross(p, q, r, s):
                crossing, best, where = True, 0.0, ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
                continue
            for pt, seg in ((p, (r, s)), (q, (r, s)), (r, (p, q)), (s, (p, q))):
                dist, near = _pt_seg(pt[0], pt[1], *seg)
                if dist < best and not crossing:
                    best, where = dist, ((pt[0] + near[0]) / 2, (pt[1] + near[1]) / 2)
    if not crossing and best > 1e-9 and (_inside(A[0], B) or _inside(B[0], A)):
        crossing, best, where = True, 0.0, A[0]
    return crossing, best, where


def check_sheet(placed, oy, label):
    errs, min_gap, min_edge = [], math.inf, math.inf
    for i, a in enumerate(placed):
        x0, y0, x1, y1 = _bbox(a["pts"])
        margin = min(x0, y0 - oy, SHEET_W - x1, SHEET_H - (y1 - oy))
        min_edge = min(min_edge, margin)
        if margin < EDGE - 1e-6:
            errs.append((f"{label}: {a['name']} is {margin:.3f}\" from the sheet edge (needs {EDGE:g}\")", ((x0 + x1) / 2, (y0 + y1) / 2)))
        for hx, hy in a["holes"]:
            near = min(_pt_seg(hx, hy, a["pts"][k], a["pts"][(k + 1) % len(a["pts"])])[0] for k in range(len(a["pts"])))
            if not _inside((hx, hy), a["pts"]) or near < d.DOWEL_D / 2 + G / 2 - 1e-6:
                errs.append((f"{label}: dowel hole in {a['name']} is only {near - d.DOWEL_D / 2:.3f}\" from the part edge", (hx, hy)))
        for b in placed[i + 1:]:
            crossing, dist, where = poly_relation(a["pts"], b["pts"])
            if crossing:
                errs.append((f"{label}: OVERLAP between {a['name']} and {b['name']}", where))
            elif dist < G - 1e-6:
                errs.append((f"{label}: {a['name']} and {b['name']} are only {dist:.3f}\" apart (need {G:g}\")", where))
            if not crossing:
                min_gap = min(min_gap, dist)
    return errs, min_gap, min_edge


# ---- write files ---------------------------------------------------------------
ERRORS, MIN_GAP, MIN_EDGE = check_sheet(PLACED, 0, "sheet")
if TALLY != NEED:
    ERRORS.append((f"part counts {TALLY} do not match what the system needs {NEED}", (0, 0)))
VIEW_OY = 8
for msg, (mx, my) in ERRORS:
    VIEW.append(f'<circle cx="{mx:.3f}" cy="{my:.3f}" r="0.45" fill="#ef4444" fill-opacity="0.35" stroke="#dc2626" stroke-width="0.12"/>')

cut = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W:g}in" height="{SHEET_H:g}in" viewBox="0 0 {SHEET_W:g} {SHEET_H:g}">']
for gid, key, color in (("1_dowel_holes", "holes", "#ff0000"), ("2_fingered_parts_supports_and_rail_inner_plies", "fingers", "#0000ff"),
                        ("3_plain_parts_rail_outer_plies_and_dividers", "plain", "#008000")):
    cut.append(f'<g id="{gid}" fill="none" stroke="{color}" stroke-width="0.01">')
    cut += CUTG[key]
    cut.append("</g>")
cut.append("</svg>")
TAG = f"{SHEET_W:g}x{SHEET_H:g}in"
open(f"cut_{TAG}_sheet1.svg", "w").write("\n".join(cut))

desc = ", ".join(f"{TALLY[k]} x {PARTS[k]['name'].split('  ')[0]}" for k in "SIOAB")
head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 {SHEET_W + 2:g} {SHEET_H + VIEW_OY + 2:g}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect x="-1" y="-1" width="{SHEET_W + 2:g}" height="{SHEET_H + VIEW_OY + 2:g}" fill="#ffffff"/>',
        '<text x="0" y="1.2" font-size="1.5" font-weight="bold" fill="#111827">Pan &amp; Lid Drawer Storage - nested layout</text>',
        f'<text x="0" y="2.6" font-size="0.7" fill="#6b7280">3/8" baltic birch, parts run along the 48" side. Fingered parts (supports, rail inner plies) {H_F:g}" tall, plain parts (rail outer plies, dividers) {H_P:g}" tall; tabs and slots {d.TAB_T:g}".</text>',
        f'<text x="0" y="3.2" font-size="0.7" fill="#6b7280">Padding {EDGE:g}" minimum at the sheet edges, {G:g}" between rows.</text>',
        f'<text x="0" y="3.9" font-size="0.7" fill="#6b7280">Sheet {SHEET_W:g}" x {SHEET_H:g}": {desc}.</text>',
        '<text x="0" y="5.8" font-size="0.7" fill="#6b7280">Cut order (cut file colours): 1 red = dowel holes, 2 blue = fingered parts (supports, rail inner plies), 3 green = plain parts (rail outer plies, dividers).</text>']
if ERRORS:
    head.append(f'<text x="0" y="4.8" font-size="0.8" font-weight="bold" fill="#dc2626">LAYOUT ERRORS ({len(ERRORS)}): ' + "; ".join(m for m, _ in ERRORS[:3]).replace("&", "&amp;").replace('"', "&quot;") + (" ..." if len(ERRORS) > 3 else "") + "</text>")
else:
    head.append(f'<text x="0" y="4.8" font-size="0.8" font-weight="bold" fill="#15803d">Layout check passed: no overlaps; smallest gap between parts {MIN_GAP:.3f}&quot; (min {G:g}&quot;), smallest edge padding {MIN_EDGE:.3f}&quot; (min {EDGE:g}&quot;).</text>')
sheet = [f'<g transform="translate(0 {VIEW_OY})">', f'<rect x="0" y="0" width="{SHEET_W:g}" height="{SHEET_H:g}" fill="#fbf7ee" stroke="#6b7280" stroke-width="0.08"/>'] + VIEW + ["</g>"]
open(f"layout_{TAG}.svg", "w").write("\n".join(head + sheet + ["</svg>"]))
print("totals:", {k: TALLY[k] for k in "SIOAB"})
print(f"stack used {STACK_USED:.3f}\" of {SHEET_H:g}\" (bottom padding {SHEET_H - STACK_USED + EDGE:.3f}\")")
if ERRORS:
    print(f"LAYOUT ERRORS ({len(ERRORS)}):")
    for m, _ in ERRORS:
        print("  -", m)
    sys.exit(2)
print(f"layout check passed: smallest gap {MIN_GAP:.4f}, smallest edge padding {MIN_EDGE:.4f}")
