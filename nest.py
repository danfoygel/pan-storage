"""Nest every part onto 48" x 33" sheets and write layout.svg (preview) + cut_sheetN.svg (1:1, inches).

Geometry comes from drawer.py. Parts are 4" strips laid along the 33" side (grain runs across the
strips, i.e. along the fingers); layout is built as rows then rotated 90 degrees onto the sheet;
tabbed parts (rail outer ply, dividers) alternate 180 degrees so their tab steps interlock.
"""
import functools
import math
import os
import sys

# usage: python3 nest.py long|short [strip_height [dividers_of_each_size]]
ORIENT = sys.argv[1] if len(sys.argv) > 1 else "long"
if len(sys.argv) > 2:
    os.environ["PART_H"] = sys.argv[2]   # shrink the parts (tab/slot depth stays 2") to fit one more row

EDGE = 0.25                     # padding at all four sheet edges (minimum)
SHEET_W, SHEET_H = 48.0, float(os.environ.get("SHEET_H", "35"))   # sheet as seen: 48 wide, SHEET_H tall
ROW_LEN, STACK = (SHEET_W, SHEET_H) if ORIENT == "long" else (SHEET_H, SHEET_W)
# 4th argument: gap between parts in inches, or "auto" = spread the spare strip space over the gaps
GAP_ARG = sys.argv[4] if len(sys.argv) > 4 else "0.125"
_H0 = float(os.environ.get("PART_H", "4.0"))
SPREAD = len(sys.argv) > 5 and sys.argv[5] == "spread"   # 5th argument: spread each row's parts over the row length
EQUAL = len(sys.argv) > 5 and sys.argv[5] == "equal"     # ... or make the end padding equal the gaps in each row
if GAP_ARG in ("auto", "max"):
    _n = int((STACK - 2 * EDGE + 0.125 + 1e-9) // (_H0 + 0.125))
    G = (STACK - 2 * EDGE - _n * _H0) / (_n - 1)                    # use all the spare strip space
    if GAP_ARG == "auto":
        G = math.floor(G * 32 + 1e-9) / 32                          # rounded down to 1/32"
else:
    G = float(GAP_ARG)

os.environ.setdefault("TAB_T", repr(math.floor((_H0 - G) / 2 * 32 + 1e-9) / 32))

import drawer as d

H = d.PART_H
T = d.T
CAP = ROW_LEN - 2 * EDGE + 1e-9
MAX_ROWS = int((STACK - 2 * EDGE + G + 1e-9) // (H + G))
# first strip position: centred in the sheet when the gap is "auto", otherwise tight against the near edge
FIRST = EDGE + ((STACK - 2 * EDGE - (MAX_ROWS * H + (MAX_ROWS - 1) * G)) / 2 if GAP_ARG in ("auto", "max") else 0.0)
MIN_EACH = int(sys.argv[3]) if len(sys.argv) > 3 else 5   # at least this many dividers of each size


# ---- parts (profiles in (u along length, v up)) ------------------------------
def part_support():
    pts, rnd = d.notched(0, d.W, H, [(s, s + d.SLOT_W) for s in d.SLOTS], d.TAB)
    return dict(kind="S", name="SUPPORT", pts=pts, rnd=rnd, holes=[], L=d.W, tabbed=False, col=d.SUP)


def part_outer():
    return dict(kind="O", name="RAIL OUTER", pts=d.RAIL_PROFILE, rnd={0, 1, 2, 4, 5, 7},
                holes=[(y, d.DOWEL_Z) for y in d.DOWEL_YS], L=d.D, tabbed=True, col=d.ROUT)


def part_inner():
    pts, rnd = d.notched(d.BODY0, d.BODY1, H, [(y - d.NOTCH_W / 2, y + d.NOTCH_W / 2) for y in d.NOTCH_YS], d.TAB)
    pts = [(u - d.BODY0, v) for u, v in pts]
    return dict(kind="I", name="RAIL INNER", pts=pts, rnd=rnd,
                holes=[(y - d.BODY0, d.DOWEL_Z) for y in d.DOWEL_YS], L=d.BODY1 - d.BODY0, tabbed=False, col=d.RIN)


def part_divider(kind, gap_index, col):
    gl, gr = d.GAPS[gap_index]
    g = gr - gl
    L = g + 2 * T
    ts = H - d.TAB_T
    pts = [(0, H), (L, H), (L, ts), (L - T, ts), (L - T, 0), (T, 0), (T, ts), (0, ts)]
    return dict(kind=kind, name=f"DIVIDER {kind}  {d.frac(g)} gap", pts=pts, rnd={0, 1, 2, 4, 5, 7},
                holes=[], L=L, tabbed=True, col=col)


PARTS = {
    "S": part_support(), "O": part_outer(), "I": part_inner(),
    "A": part_divider("A", 0, d.DIVC), "B": part_divider("B", 1, "#c084fc"),
}
ORDER = "SIOAB"


# ---- rows ---------------------------------------------------------------------
def row_length(counts):
    parts = [PARTS[k] for k, n in zip(ORDER, counts) for _ in range(n)]
    if not parts:
        return 0
    tabbed = sum(p["tabbed"] for p in parts)
    nontabbed = len(parts) - tabbed
    saved = T * (tabbed - 1) if tabbed > 1 else 0
    return sum(p["L"] for p in parts) + G * (len(parts) - 1) - saved + (0 if nontabbed <= 2 else 1e9)


ROW_TYPES = []
for c in [(s, i, o, a, b) for s in range(2) for i in range(3) for o in range(3) for a in range(5) for b in range(6)]:
    if sum(c) and row_length(c) <= CAP:
        ROW_TYPES.append(c)


def pareto(items):
    """items: {(A, B): rows}; drop dominated entries."""
    keep = {}
    for (a, b), rows in items.items():
        if not any((a2 >= a and b2 >= b and (a2, b2) != (a, b)) for (a2, b2) in items):
            keep[(a, b)] = rows
    return keep


@functools.lru_cache(maxsize=None)
def best(rows_left, s, i, o):
    """Pareto set {(A, B): [row types]} using exactly the needed structural parts in <= rows_left rows."""
    if s == i == o == 0:
        res = {(0, 0): ()}
    else:
        res = {}
    if rows_left == 0:
        return res if (s == i == o == 0) else {}
    out = dict(res)
    for t in ROW_TYPES:
        ts, ti, to, ta, tb = t
        if ts > s or ti > i or to > o:
            continue
        for (a, b), rows in best(rows_left - 1, s - ts, i - ti, o - to).items():
            key = (a + ta, b + tb)
            if key not in out:
                out[key] = (t,) + rows
    return pareto(out)


def pick(options):
    """Reach MIN_EACH of both divider sizes first, then maximize the total."""
    return max(options.items(), key=lambda kv: (min(min(kv[0]), MIN_EACH), sum(kv[0])))


sheet1_choice = pick(best(MAX_ROWS, 2, 4, 4))
(A1, B1), rows1 = sheet1_choice


def divider_rows(a_need, b_need):
    for r in range(1, MAX_ROWS + 1):
        opts = {k: v for k, v in best(r, 0, 0, 0).items() if k[0] >= a_need and k[1] >= b_need}
        if opts:
            return pick(opts)
    raise SystemExit("cannot place the dividers on one extra sheet")


sheets = [list(rows1)]
total_A, total_B = A1, B1
if min(A1, B1) < MIN_EACH:
    (A2, B2), rows2 = divider_rows(max(0, MIN_EACH - A1), max(0, MIN_EACH - B1))
    sheets.append(list(rows2))
    total_A += A2
    total_B += B2


# ---- placement ----------------------------------------------------------------
def place_row(counts):
    parts = [PARTS[k] for k, n in zip(ORDER, counts) for _ in range(n)]
    nt = [p for p in parts if not p["tabbed"]]
    tb = [p for p in parts if p["tabbed"]]
    seq = nt[:1] + tb + nt[1:]
    x, res, flip, prev = EDGE, [], False, None
    for p in seq:
        if prev is not None:
            x = prev_end + G - (T if prev["tabbed"] and p["tabbed"] else 0)
        inv = False
        if p["tabbed"]:
            inv, flip = flip, not flip
        res.append((p, x, inv))
        prev, prev_end = p, x + p["L"]
    if EQUAL:                        # left padding = every gap between parts = right padding
        inter = sum(1 for (p, _, _), (q, _, _) in zip(res, res[1:]) if p["tabbed"] and q["tabbed"])
        space = (ROW_LEN - sum(p["L"] for p, _, _ in res) + T * inter) / (len(res) + 1)
        out, x, prev = [], space, None
        for p, _, inv in res:
            if prev is not None:
                x = prev_end + space - (T if prev["tabbed"] and p["tabbed"] else 0)
            out.append((p, x, inv))
            prev, prev_end = p, x + p["L"]
        return out
    slack = (ROW_LEN - EDGE) - prev_end
    if SPREAD and len(res) > 1:      # widen every gap in the row equally so the row ends at the far padding line
        res = [(p, x + i * slack / (len(res) - 1), inv) for i, (p, x, inv) in enumerate(res)]
    elif SPREAD:                     # a lone part is centred in its row
        res = [(p, x + slack / 2, inv) for p, x, inv in res]
    return res


def transform(p, x0, ytop, inv, oy):
    L = p["L"]

    def tf(u, v):
        lx, ly = (x0 + L - u, ytop + v) if inv else (x0 + u, ytop + H - v)
        if ORIENT == "long":
            return lx, ly + oy
        return STACK - ly, lx + oy   # rotate the row layout 90 degrees onto the sheet
    return [tf(*q) for q in p["pts"]], [tf(*h) for h in p["holes"]]


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


PLACED = []   # parts of the sheet being drawn, for the layout check


def sheet_elements(rows, oy, cut):
    els, tally = [], {}
    for ri, counts in enumerate(rows):
        ytop = FIRST + ri * (H + G)
        for p, x0, inv in place_row(counts):
            pts, holes = transform(p, x0, ytop, inv, oy)
            dd = path_d(pts, p["rnd"], d.TAB_R)
            if not cut:
                PLACED.append(dict(name=p["name"], pts=d.rounded_profile(pts, p["rnd"], d.TAB_R, n=6)[0], holes=holes))
            if cut:
                els.append(f'<path d="{dd}" fill="none" stroke="#ff0000" stroke-width="0.01"/>')
                els += [f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{d.DOWEL_D / 2}" fill="none" stroke="#ff0000" stroke-width="0.01"/>' for x, y in holes]
            else:
                els.append(f'<path d="{dd}" fill="{p["col"]}" stroke="#1f2937" stroke-width="0.03" stroke-linejoin="round"/>')
                els += [f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{d.DOWEL_D / 2}" fill="#ffffff" stroke="#1f2937" stroke-width="0.02"/>' for x, y in holes]
                if ORIENT == "long":
                    tx, ty, rot = x0 + p["L"] / 2, oy + ytop + 3.72, ""
                else:
                    tx, ty = STACK - (ytop + 3.72), oy + x0 + p["L"] / 2
                    rot = f' transform="rotate(90 {tx:.3f} {ty:.3f})"'
                els.append(f'<text x="{tx:.3f}" y="{ty:.3f}" font-size="0.42" text-anchor="middle" fill="#111827"{rot}>{p["name"]}</text>')
            tally[p["kind"]] = tally.get(p["kind"], 0) + 1
    return els, tally


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
TAG = (ORIENT if H == 4.0 else f"{ORIENT}_extra_row") + (f"_h{H:g}_gap{G:.3f}" if GAP_ARG in ("auto", "max") else "") + ("_spread" if SPREAD else "") + ("_equal" if EQUAL else "") + (f"_{SHEET_H:g}in" if SHEET_H != 35.0 else "")
GAP_Y = 6.0
tot = {}
view = []
ERRORS, MIN_GAP, MIN_EDGE = [], math.inf, math.inf
for si, rows in enumerate(sheets):
    oy = 7 + si * (SHEET_H + GAP_Y)
    view.append(f'<rect x="0" y="{oy}" width="{SHEET_W}" height="{SHEET_H}" fill="#fbf7ee" stroke="#6b7280" stroke-width="0.08"/>')
    PLACED.clear()
    els, tally = sheet_elements(rows, oy, False)
    view += els
    e, g_, ed = check_sheet(PLACED, oy, f"sheet {si + 1}")
    ERRORS += e
    MIN_GAP, MIN_EDGE = min(MIN_GAP, g_), min(MIN_EDGE, ed)
    for msg, (mx, my) in e:
        view.append(f'<circle cx="{mx:.3f}" cy="{my:.3f}" r="0.45" fill="#ef4444" fill-opacity="0.35" stroke="#dc2626" stroke-width="0.12"/>')
    desc = ", ".join("%d x %s" % (n, PARTS[k]["name"].split("  ")[0]) for k, n in sorted(tally.items(), key=lambda kv: ORDER.index(kv[0])))
    view.append(f'<text x="0" y="{oy - 0.6}" font-size="0.9" font-weight="bold" fill="#111827">Sheet {si + 1} of {len(sheets)} - 48" x {SHEET_H:g}"   ({desc})</text>')
    for k, n in tally.items():
        tot[k] = tot.get(k, 0) + n
    cut = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W}in" height="{SHEET_H}in" viewBox="0 0 {SHEET_W} {SHEET_H}">']
    cut += sheet_elements(rows, 0, True)[0]
    cut.append("</svg>")
    open(f"cut_{TAG}_sheet{si + 1}.svg", "w").write("\n".join(cut))

H_TOTAL = 7 + len(sheets) * (SHEET_H + GAP_Y)
head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 {SHEET_W + 2} {H_TOTAL}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect x="-1" y="-1" width="{SHEET_W + 2}" height="{H_TOTAL}" fill="#ffffff"/>',
        '<text x="0" y="1.2" font-size="1.5" font-weight="bold" fill="#111827">Pan &amp; Lid Drawer Storage - nested layout</text>',
        f'<text x="0" y="2.6" font-size="0.7" fill="#6b7280">3/8" baltic birch, parts run along the {"48" if ORIENT == "long" else "35"} side. Padding {EDGE:g}" minimum at the sheet edges ({FIRST:.3f}" at the near edges of the strips), {G:g}" between parts; part height {H:g}" ({MAX_ROWS} rows). Tab height {d.TAB_T:g}". Tabbed parts alternate 180 degrees so the tab steps interlock.</text>',
        f'<text x="0" y="3.6" font-size="0.7" fill="#6b7280">Totals: {tot.get("S", 0)} supports, {tot.get("O", 0)} rail outer plies, {tot.get("I", 0)} rail inner plies, '
        f'{total_A} divider A ({d.frac(d.GAPS[0][1] - d.GAPS[0][0])} gap), {total_B} divider B ({d.frac(d.GAPS[1][1] - d.GAPS[1][0])} gap).</text>']
if ERRORS:
    head.append(f'<text x="0" y="4.7" font-size="0.8" font-weight="bold" fill="#dc2626">LAYOUT ERRORS ({len(ERRORS)}): ' + "; ".join(m for m, _ in ERRORS[:3]).replace("&", "&amp;").replace('"', "&quot;") + (" ..." if len(ERRORS) > 3 else "") + "</text>")
else:
    head.append(f'<text x="0" y="4.7" font-size="0.8" font-weight="bold" fill="#15803d">Layout check passed: no overlaps; smallest gap between parts {MIN_GAP:.3f}&quot; (min {G:g}&quot;), smallest edge padding {MIN_EDGE:.3f}&quot; (min {EDGE:g}&quot;).</text>')
open(f"layout_{TAG}.svg", "w").write("\n".join(head + view + ["</svg>"]))
print("sheets:", len(sheets), "totals:", tot, "dividers A/B:", total_A, total_B)
for si, rows in enumerate(sheets):
    print(f"sheet {si + 1}:", [dict(zip(ORDER, r)) for r in rows])
if ERRORS:
    print(f"LAYOUT ERRORS ({len(ERRORS)}):")
    for m, _ in ERRORS:
        print("  -", m)
    sys.exit(2)
print(f"layout check passed: smallest gap {MIN_GAP:.4f}, smallest edge padding {MIN_EDGE:.4f}")
