"""Nest every part onto one 48" x 34" sheet; write layout_<orientation>_x<x>.svg (preview) and cut_<...>_sheet1.svg (1:1, inches).

Geometry comes from drawer.py. With x the height of the slotted parts (supports, rail inner plies), the rail outer
plies and divider A are x + 1 tall, divider B is x tall, and the fingers/slots are x / 2 deep.

The layout is built from rows (strips) of parts side by side, and rows with fingers are interleaved with rows
without fingers so the fingers can be cut first while the neighbouring plain rows are still solid stock:
  - a "fingered" row holds a support or a rail inner ply (and, beside it, a divider B, which is as tall as they
    are, or sometimes a divider A);
  - a "plain" row holds only rail outer plies and dividers;
  - no two fingered rows are adjacent and the first and last rows are plain, so every fingered row is flanked by
    plain rows, and its fingers face one of them.
The set of rows that needs the least total height is found exactly (dynamic programming over the parts left to
place), then the rows are ordered plain / fingered / plain / ... and the spare height is spread over the gaps.
The fingered rows run: a support row (support pushed to the right edge), the rail inner ply rows, then the other
support row (support pushed to the left edge).
The tabs of the tall parts run from the slot floor to the top, taller than the notch beside them, so neighbouring
parts cannot interlock and each takes its full length in a row. Every placement is checked outline by outline
(overlaps, gaps, edge padding, dowels).

usage: python3 nest.py [long|short] [--max]
  long (default): parts run along the 48" side, stacked along the 34" side.
  short:          parts run along the 34" side, stacked along the 48" side (if the grain runs along the 48" side,
                  it then runs along the fingers instead of across them; fits a smaller x).
  --max:          instead of nesting, report the largest x (1/16" steps) that fits (set X_FING to use it).
The spare height left over at the chosen x is spread evenly over the gaps between rows.
"""
import functools
import itertools
import math
import sys

import drawer as d

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
ORIENT = ARGS[0] if ARGS else "long"
FIND_MAX = "--max" in sys.argv
EDGE = 0.25                     # padding at all four sheet edges (minimum)
G = 0.125                       # smallest gap between parts
ROW_GAP_SET = 0.25              # gap between rows; the spare height beyond that goes into the padding at both ends of the stack
SHEET_W, SHEET_H = 48.0, 34.0
ROW_LEN, STACK = (SHEET_H, SHEET_W) if ORIENT == "short" else (SHEET_W, SHEET_H)
T, TAB_R = d.T, d.TAB_R
H_F, H_P = d.H_FING, d.H_PLAIN
FINGERED = "SI"
NEED = {"S": 2, "I": 4, "O": 4, "A": 7, "B": 7}    # parts in the system
LENGTH = {"S": d.W, "I": d.BODY1 - d.BODY0, "O": d.D, "A": d.GAPS[0][1] - d.GAPS[0][0] + 2 * T, "B": d.GAPS[1][1] - d.GAPS[1][0] + 2 * T}

# Test pieces (not part of the system): strips with a row of slots in one long edge and a row of dowel holes, to find
# the slot width and hole size that fit the plywood and the dowels. Two of them are stacked, flat edges facing, in the
# middle of each of the two rows with the rail inner plies, which are pushed to the outside edges to make room. The
# slot and the hole beneath it share one offset from nominal, which is engraved between them.
TEST_COUNT = 4                  # identical pieces: two in each of the two rows of rail inner plies
TEST_H = (H_F - G) / 2          # width of a strip across the fingers: two of them and the gap between fill the row
TEST_L = 8.5                    # length of the strip; the free middle of the rail inner ply rows is 8.75"
TEST_DEPTH = 0.5                # finger / slot depth: much shallower than the real 1 1/2" ones
TEST_PITCH = 0.75               # slot pitch, centre to centre (the same as the rail slots)
TEST_STEPS_MM = [k / 10 for k in range(-5, 6)]    # offset from nominal, mm: -0.5 ... +0.5 in 0.1 mm steps; slot width and hole diameter
TEST_NOMINAL = T                # the plywood thickness the slots are relative to (change to the measured value)
FINE_COUNT = 2                  # fine test pieces: one in each of the two rows with a support
FINE_L = 4.0                    # length of the strip; the free end of the support rows is 4.5"
FINE_H = H_F                    # as tall as the rail inner plies, with fingers (slots) on the top edge only
FINE_DEPTH = d.TAB              # slot / finger depth: the same 1 1/2" as the rail inner plies
FINE_STEPS_MM = [-0.06, -0.03, 0.0, 0.03, 0.06]   # offset from nominal, mm: five slots, finer steps
LABEL_H = 0.18                  # height of the engraved offset labels
LABEL_GAP = 0.09                # between a dowel hole and its label
HALF_WEB = 0.125                # the unlabelled in-between holes are raised until their edge is this far from the slot corners
LENGTH["T"], LENGTH["U"] = TEST_L, FINE_L


# ---- rows: exact search -----------------------------------------------------------
def plan_rows(x):
    """Fewest-height set of rows for the parts at slotted height x, with plain rows at both ends and no two
    fingered rows adjacent (so #plain rows >= #fingered rows + 1). Returns (stack height used incl. both paddings,
    [(counts as a dict, row height, fingered?)]) or None."""
    heights = {"S": x, "I": x, "B": x, "O": x + 1, "A": x + 1}
    kinds = "SIOAB"
    need = tuple(NEED[k] for k in kinds)
    types = []
    for c in itertools.product(*(range(n + 1) for n in need)):
        n_parts = sum(c)
        if n_parts and sum(LENGTH[k] * v for k, v in zip(kinds, c)) + (n_parts - 1) * G + 2 * EDGE <= ROW_LEN + 1e-9:
            types.append((c, max(heights[k] for k, v in zip(kinds, c) if v), any(v for k, v in zip(kinds, c) if k in FINGERED)))

    @functools.lru_cache(maxsize=None)
    def best(rem, balance):      # balance = #plain rows - #fingered rows so far
        if not any(rem):
            return (0.0, ()) if balance >= 1 else (math.inf, ())
        first = next(i for i, r in enumerate(rem) if r)
        res = (math.inf, ())
        for c, h, fingered in types:
            if c[first] and all(ci <= ri for ci, ri in zip(c, rem)):
                sub = best(tuple(ri - ci for ri, ci in zip(rem, c)), balance + (-1 if fingered else 1))
                if h + G + sub[0] < res[0]:
                    res = (h + G + sub[0], ((dict(zip(kinds, c)), h, fingered),) + sub[1])
        return res
    total, rows = best(need, 0)
    return None if math.isinf(total) else (total - G + 2 * EDGE, list(rows))


if FIND_MAX:
    print(f"{ORIENT}: sheet {SHEET_W:g} x {SHEET_H:g}, gap {G:g}, edge padding {EDGE:g}; stack must be <= {STACK:g}")
    fits = None
    for n in range(32, 80):       # x in 1/16" steps
        x = n / 16
        res = plan_rows(x)
        used = res[0] if res else None
        print(f"  x = {x:7.4f}  (plain {x + 1:7.4f}, fingers {x / 2:7.4f})  stack {'-' if used is None else f'{used:.3f}'}", flush=True)
        if used is not None and used <= STACK + 1e-9:
            fits = x
        elif fits is not None:
            break
    print(f"largest x that nests: {fits}")
    sys.exit(0)


# ---- parts (profiles in (u along length, v up)) ------------------------------
def part(kind, name, pts, rnd, holes, L, h, col):
    return dict(kind=kind, name=name, pts=pts, rnd=rnd, holes=holes, L=L, H=h, col=col, engrave=[])


def make_parts():
    sp, sr = d.notched(0, d.W, H_F, [(s, s + d.SLOT_W) for s in d.SLOTS], d.TAB)
    ip, ir = d.notched(d.BODY0, d.BODY1, H_F, [(y - d.NOTCH_W / 2, y + d.NOTCH_W / 2) for y in d.NOTCH_YS], d.TAB)
    ip = [(u - d.BODY0, v) for u, v in ip]
    out = {
        "S": part("S", "SUPPORT", sp, sr, [], d.W, H_F, d.SUP),
        "I": part("I", "RAIL INNER", ip, ir, [(y - d.BODY0, d.DOWEL_Z) for y in d.DOWEL_YS], d.BODY1 - d.BODY0, H_F, d.RIN),
        "O": part("O", "RAIL OUTER", d.RAIL_PROFILE, d.RAIL_RND, [(y, d.DOWEL_Z) for y in d.DOWEL_YS], d.D, H_P, d.ROUT),
    }
    for k, gi, col in (("A", 0, d.DIVC), ("B", 1, "#c084fc")):
        gl, gr = d.GAPS[gi]
        L = gr - gl + 2 * T
        dpts, drnd = d.divider_profile(L, d.DIV_H[gi])
        out[k] = part(k, f"DIVIDER {k}  {d.frac(gr - gl)} gap", dpts, drnd, [], L, d.DIV_H[gi], col)
    out["T"] = test_part("T", "TEST", TEST_L, TEST_H, TEST_DEPTH, TEST_STEPS_MM, lambda mm: f"{round(mm * 10):+d}" if mm else "0", True)
    out["U"] = test_part("U", "TEST FINE", FINE_L, FINE_H, FINE_DEPTH, FINE_STEPS_MM, lambda mm: f"{mm:+.2f}" if mm else "0.00", False)
    return out


SEGMENTS = {"a": ((0, 1), (1, 1)), "b": ((1, 1), (1, .5)), "c": ((1, .5), (1, 0)), "d": ((0, 0), (1, 0)),
            "e": ((0, 0), (0, .5)), "f": ((0, .5), (0, 1)), "g": ((0, .5), (1, .5))}
DIGITS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def label_strokes(text, cx, v0, h):
    """Single-line (seven-segment style) lettering for engraving: strokes [(u, v), (u, v)] for `text`, centred on u = cx
    with its baseline at v0 and characters h tall."""
    w, gap = 0.55 * h, 0.22 * h
    widths = [0 if ch == "." else w for ch in text]
    u = cx - (sum(widths) + gap * (len(text) - 1)) / 2
    out = []
    for ch, cw in zip(text, widths):
        if ch in DIGITS:
            out += [[(u + a * w, v0 + b * h) for a, b in SEGMENTS[sg]] for sg in DIGITS[ch]]
        elif ch in "+-":
            out.append([(u, v0 + h / 2), (u + w, v0 + h / 2)])
            if ch == "+":
                out.append([(u + w / 2, v0 + h / 2 - w / 2), (u + w / 2, v0 + h / 2 + w / 2)])
        elif ch == ".":
            out.append([(u, v0), (u, v0 + 0.06 * h)])
        u += cw + gap
    return out


def test_part(kind, name, length, height, depth, steps_mm, label_fmt, with_holes):
    """Strip `height` wide with a row of slots in its top edge, narrowest to widest from left to right, and under each slot
    its engraved offset from nominal. With holes: a dowel hole under each slot whose diameter has the same offset as the
    slot width, plus an unlabelled hole between each pair of those at the mean offset. The labels are short enough to
    leave room between them, so those in-between holes are raised towards the fingers, away from their neighbours."""
    n = len(steps_mm)
    slots, holes, labels = [], [], []
    spine = height - depth                                       # solid depth under the slot floors
    block = LABEL_H + (d.DOWEL_D + LABEL_GAP if with_holes else 0)
    margin = (spine - block) / 2                                 # the hole and the label are centred in it
    centres = [length / 2 + (k - (n - 1) / 2) * TEST_PITCH for k in range(n)]
    for c, mm in zip(centres, steps_mm):
        w = TEST_NOMINAL + mm / 25.4
        slots.append((c - w / 2, c + w / 2))
    v_mid = math.inf                                             # height of the in-between holes: as high as the slot corners allow
    for k in range(1, n if with_holes else 0):
        x, r = (centres[k] + centres[k - 1]) / 2, (d.DOWEL_D + (steps_mm[k] + steps_mm[k - 1]) / 2 / 25.4) / 2
        for cx in (slots[k - 1][1], slots[k][0]):
            if r + HALF_WEB > abs(cx - x):
                v_mid = min(v_mid, height - depth - math.sqrt((r + HALF_WEB) ** 2 - (cx - x) ** 2))
    for k, (c, mm) in enumerate(zip(centres, steps_mm)):
        if with_holes:
            holes.append((c, margin + d.DOWEL_D / 2, d.DOWEL_D + mm / 25.4))
            if k:                                                # an unlabelled hole between this slot's hole and the last one, at the mean offset
                holes.append((c - TEST_PITCH / 2, v_mid, d.DOWEL_D + (mm + steps_mm[k - 1]) / 2 / 25.4))
        labels += label_strokes(label_fmt(mm), c, margin + (d.DOWEL_D + LABEL_GAP if with_holes else 0), LABEL_H)
    pts, rnd = d.notched(0, length, height, slots, depth)
    p = part(kind, name, pts, rnd, holes, length, height, "#fbbf24" if with_holes else "#fde68a")
    p["engrave"] = labels
    return p


PARTS = make_parts()
for _k, _p in PARTS.items():
    assert abs(_p["L"] - LENGTH[_k]) < 1e-9


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
CUTG = {"engrave": [], "holes": [], "fingers": [], "plain": []}   # cut-file elements by operation


def to_sheet(lx, ly):
    """(row, stack) layout coordinates -> sheet coordinates (short: the rows are turned 90 degrees)."""
    return (lx, ly) if ORIENT == "long" else (STACK - ly, lx)


def put(key, x0, ytop, inv):
    """Place a part with its left edge at x0 and the top of its strip at ytop; inv = turned 180 degrees."""
    p = PARTS[key]
    L, h = p["L"], p["H"]

    def tf(u, v):
        return to_sheet(*((x0 + L - u, ytop + v) if inv else (x0 + u, ytop + h - v)))
    pts = [tf(*q) for q in p["pts"]]
    holes = [(*tf(*q[:2]), q[2] if len(q) > 2 else d.DOWEL_D) for q in p["holes"]]     # (x, y, diameter)
    strokes = [[tf(*q) for q in line] for line in p["engrave"]]
    dd = path_d(pts, p["rnd"], TAB_R)
    PLACED.append(dict(name=p["name"], pts=d.rounded_profile(pts, p["rnd"], TAB_R, n=6)[0], holes=holes))
    TALLY[key] = TALLY.get(key, 0) + 1
    CUTG["fingers" if key in "SITU" else "plain"].append(f'<path d="{dd}"/>')
    CUTG["holes"] += [f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{dia / 2:.4f}"/>' for x, y, dia in holes]
    lines = [" ".join(f"{'ML'[j > 0]}{x:.4f},{y:.4f}" for j, (x, y) in enumerate(line)) for line in strokes]
    CUTG["engrave"] += [f'<path d="{ln}"/>' for ln in lines]
    VIEW.append(f'<path d="{dd}" fill="{p["col"]}" stroke="#1f2937" stroke-width="0.03" stroke-linejoin="round"/>')
    VIEW.extend(f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{dia / 2:.4f}" fill="#ffffff" stroke="#1f2937" stroke-width="0.02"/>' for x, y, dia in holes)
    VIEW.extend(f'<path d="{ln}" fill="none" stroke="#b91c1c" stroke-width="0.025" stroke-linecap="round"/>' for ln in lines)
    if key in "TU":
        return
    tx, ty = to_sheet(x0 + L / 2, ytop + (0.75 if key == "O" else 0.5 * h) + 0.15)
    rot = "" if ORIENT == "long" else f' transform="rotate(90 {tx:.3f} {ty:.3f})"'
    VIEW.append(f'<text x="{tx:.3f}" y="{ty:.3f}" font-size="0.42" text-anchor="middle" fill="#111827" stroke="#ffffff" stroke-width="0.12" paint-order="stroke"{rot}>{p["name"].split("  ")[0]}</text>')


def row_order(rows):
    """Interleave: plain, fingered, plain, fingered, ..., plain (extra plain rows go at the end). The fingered rows
    go in this order: the first row with a support, the rows with only rail inner plies, the last row with a
    support. Returns the rows and a {row index: "left" | "right"} alignment for the support rows."""
    fing = [r for r in rows if r[2]]
    plain = [r for r in rows if not r[2]]
    supports = [r for r in fing if r[0].get("S")]
    fing = supports[:1] + [r for r in fing if not r[0].get("S")] + supports[1:]
    out, align = [], {}
    for i, f in enumerate(fing):
        out += [plain[i]]
        if f is supports[0]:
            align[len(out)] = "right"
        elif len(supports) > 1 and f is supports[-1]:
            align[len(out)] = "left"
        out += [f]
    return out + plain[len(fing):], align


def build():
    res = plan_rows(H_F)
    if res is None or res[0] > STACK + 1e-9:
        sys.exit(f"does not fit: x = {H_F:g} needs {'more than ' + format(STACK, 'g') if res is None else format(res[0], '.3f')}\" of the {STACK:g}\" side"
                 f" ({ORIENT} orientation); run `python3 nest.py {ORIENT} --max`")
    used, rows = res
    inner_rows = [i for i, (c, _, _) in enumerate(rows) if c["I"] and not any(v for k, v in c.items() if k != "I")]
    if len(inner_rows) != TEST_COUNT // 2:
        sys.exit(f"expected {TEST_COUNT // 2} rows holding only rail inner plies for the test pieces, found {len(inner_rows)}")
    for i in inner_rows:
        rows[i] = ({**rows[i][0], "T": 2}, rows[i][1], True)
    support_rows = [i for i, (c, _, _) in enumerate(rows) if c["S"]]
    if len(support_rows) != FINE_COUNT:
        sys.exit(f"expected {FINE_COUNT} rows with a support for the fine test pieces, found {len(support_rows)}")
    for i in support_rows:
        rows[i] = ({**rows[i][0], "U": 1}, rows[i][1], True)
    rows, align = row_order(rows)
    spare = STACK - sum(h for _, h, _ in rows)
    gap = ROW_GAP_SET
    pad = (spare - gap * (len(rows) - 1)) / 2             # rows are ROW_GAP_SET apart; the rest is padding at both ends of the stack
    if pad < EDGE:                                        # not enough spare height: shrink the row gaps instead
        gap, pad = (spare - 2 * EDGE) / (len(rows) - 1), EDGE
    y = pad
    for i, (counts, h, fingered) in enumerate(rows):
        keys = [k for k in "SIOAB" for _ in range(counts.get(k, 0))] + ["U"] * (counts.get("U", 0) > 0)
        free = ROW_LEN - sum(LENGTH[k] for k in keys)
        if counts.get("T"):                      # rail inner plies against the sheet edges, the test piece between them
            keys = ["I", "T", "I"]
            inner = (ROW_LEN - 2 * EDGE - sum(LENGTH[k] for k in keys)) / 2
            if inner < G - 1e-9 or h < 2 * TEST_H + G - 1e-9:
                sys.exit(f"the test pieces do not fit in the middle of the rail inner ply row ({inner:.3f}\" gap, needs {G:g}\")")
            x = EDGE
        elif i in align:                           # a support row is pushed against one side, its other parts beside it
            rank = {"U": 0, "S": 2}                  # the fine test piece goes at the free end, the support against the sheet edge
            keys.sort(key=lambda k: rank.get(k, 1) * (1 if align[i] == "right" else -1))
            inner = max(gap, G)
            x = ROW_LEN - EDGE - sum(LENGTH[k] for k in keys) - inner * (len(keys) - 1) if align[i] == "right" else EDGE
        else:
            space = free / (len(keys) + 1)       # end padding = every gap within the row ...
            inner = space
            if space < EDGE:                     # ... unless that would crowd the sheet edge: then pad EDGE and share the rest
                space, inner = EDGE, (free - 2 * EDGE) / (len(keys) - 1)
            x = space
        for k in keys:
            put(k, x, y, False)                  # fingers face the row above, which is plain
            if k == "T":                         # the second test piece below the first, turned round so its fingers face the plain row below
                if h < 2 * TEST_H + G - 1e-9:
                    sys.exit(f"two test pieces do not fit in a row {h:g}\" tall")
                put(k, x, y + h - TEST_H, True)
            x += LENGTH[k] + inner
        y += h + gap
    return used, gap, pad, rows


STACK_USED, ROW_GAP, STACK_PAD, ROWS = build()



NEAR = max(G, ROW_GAP) + 0.05     # parts farther apart than this are not compared outline by outline


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
    if max(b0 - a2, a0 - b2, b1 - a3, a1 - b3) > NEAR:
        return False, math.inf, None
    best, where, crossing = math.inf, None, False
    sa = [(A[i], A[(i + 1) % len(A)]) for i in range(len(A))]
    sb = [(B[i], B[(i + 1) % len(B)]) for i in range(len(B))]
    for p, q in sa:
        pb = (min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1]))
        for r, s in sb:
            if max(min(r[0], s[0]) - pb[2], pb[0] - max(r[0], s[0]), min(r[1], s[1]) - pb[3], pb[1] - max(r[1], s[1])) > NEAR:
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
        for hx, hy, hd in a["holes"]:
            near = min(_pt_seg(hx, hy, a["pts"][k], a["pts"][(k + 1) % len(a["pts"])])[0] for k in range(len(a["pts"])))
            if not _inside((hx, hy), a["pts"]) or near < hd / 2 + G / 2 - 1e-6:
                errs.append((f"{label}: dowel hole in {a['name']} is only {near - hd / 2:.3f}\" from the part edge", (hx, hy)))
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
if TALLY != {**NEED, "T": TEST_COUNT, "U": FINE_COUNT}:
    ERRORS.append((f"part counts {TALLY} do not match what the system needs {NEED} plus {TEST_COUNT} + {FINE_COUNT} test pieces", (0, 0)))
VIEW_OY = 8
for msg, (mx, my) in ERRORS:
    VIEW.append(f'<circle cx="{mx:.3f}" cy="{my:.3f}" r="0.45" fill="#ef4444" fill-opacity="0.35" stroke="#dc2626" stroke-width="0.12"/>')

cut = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W:g}in" height="{SHEET_H:g}in" viewBox="0 0 {SHEET_W:g} {SHEET_H:g}">']
for gid, key, color in (("1_engrave_test_piece_offset_labels", "engrave", "#ff00ff"), ("2_dowel_holes", "holes", "#ff0000"),
                        ("3_fingered_parts_supports_rail_inner_plies_and_test_pieces", "fingers", "#0000ff"),
                        ("4_plain_parts_rail_outer_plies_and_dividers", "plain", "#008000")):
    cut.append(f'<g id="{gid}" fill="none" stroke="{color}" stroke-width="0.01">')
    cut += CUTG[key]
    cut.append("</g>")
cut.append("</svg>")
TAG = f"{ORIENT}_x{H_F:g}"
open(f"cut_{TAG}_sheet1.svg", "w").write("\n".join(cut))

GRAIN_NOTE = ' (grain along the 48" side runs along the fingers)' if ORIENT == "short" else ""
desc = ", ".join(f"{TALLY[k]} x {PARTS[k]['name'].split('  ')[0]}" for k in "SIOABTU")
head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 {SHEET_W + 2:g} {SHEET_H + VIEW_OY + 2:g}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect x="-1" y="-1" width="{SHEET_W + 2:g}" height="{SHEET_H + VIEW_OY + 2:g}" fill="#ffffff"/>',
        '<text x="0" y="1.2" font-size="1.5" font-weight="bold" fill="#111827">Pan &amp; Lid Drawer Storage - nested layout</text>',
        f'<text x="0" y="2.3" font-size="0.7" fill="#6b7280">3/8" baltic birch; parts run along the {"34" if ORIENT == "short" else "48"}" side{GRAIN_NOTE}.</text>',
        f'<text x="0" y="3.0" font-size="0.7" fill="#6b7280">Slotted parts (supports, rail inner plies) and divider B {H_F:g}" tall; rail outer plies and divider A {H_P:g}" tall; fingers and slots {d.TAB_T:g}" deep.</text>',
        f'<text x="0" y="3.7" font-size="0.7" fill="#6b7280">Rows with fingers alternate with plain rows; {ROW_GAP:.3f}" between rows, {STACK_PAD:.3f}" padding at the ends of the stack and at least {EDGE:g}" at the ends of the rows.</text>',
        f'<text x="0" y="4.4" font-size="0.7" fill="#6b7280">Sheet {SHEET_W:g}" x {SHEET_H:g}": {desc}.</text>',
        '<text x="0" y="6.4" font-size="0.7" fill="#6b7280">Cut order (cut file colours): 1 magenta = engraved labels, 2 red = dowel holes, 3 blue = fingered parts, 4 green = plain parts.</text>',
        f'<text x="0" y="7.1" font-size="0.7" fill="#6b7280">Test pieces (offsets engraved): 4 x TEST, slots and dowel holes {TEST_STEPS_MM[0]:+g} to {TEST_STEPS_MM[-1]:+g} mm; 4 x TEST FINE, 5 slots {FINE_STEPS_MM[0]:+g} to {FINE_STEPS_MM[-1]:+g} mm, no holes.</text>']
if ERRORS:
    head.append(f'<text x="0" y="5.4" font-size="0.8" font-weight="bold" fill="#dc2626">LAYOUT ERRORS ({len(ERRORS)}): ' + "; ".join(m for m, _ in ERRORS[:3]).replace("&", "&amp;").replace('"', "&quot;") + (" ..." if len(ERRORS) > 3 else "") + "</text>")
else:
    head.append(f'<text x="0" y="5.4" font-size="0.8" font-weight="bold" fill="#15803d">Layout check passed: no overlaps; smallest gap between parts {MIN_GAP:.3f}&quot; (min {G:g}&quot;), smallest edge padding {MIN_EDGE:.3f}&quot; (min {EDGE:g}&quot;).</text>')
sheet = [f'<g transform="translate(0 {VIEW_OY})">', f'<rect x="0" y="0" width="{SHEET_W:g}" height="{SHEET_H:g}" fill="#fbf7ee" stroke="#6b7280" stroke-width="0.08"/>'] + VIEW + ["</g>"]
open(f"layout_{TAG}.svg", "w").write("\n".join(head + sheet + ["</svg>"]))
_h = PARTS["T"]["holes"]
_webs = sorted((math.hypot(a[0] - b[0], a[1] - b[1]) - (a[2] + b[2]) / 2, a[2] + b[2], i, j) for i, a in enumerate(_h) for j, b in enumerate(_h) if i < j)
_big = sorted(range(len(_h)), key=lambda i: -_h[i][2])[:2]
_bw = math.hypot(_h[_big[0]][0] - _h[_big[1]][0], _h[_big[0]][1] - _h[_big[1]][1]) - (_h[_big[0]][2] + _h[_big[1]][2]) / 2
print(f"test pieces: wall between the two largest dowel holes {_bw:.4f}\" ({_bw * 25.4:.2f} mm); thinnest wall between any two holes {_webs[0][0]:.4f}\" ({_webs[0][0] * 25.4:.2f} mm); in-between holes at {_h[2][1]:.4f}\" above the flat edge, main holes at {_h[0][1]:.4f}\"")
print("totals:", {k: TALLY[k] for k in "SIOABTU"})
print(f"x = {H_F:g} (plain {H_P:g}, fingers {d.TAB_T:g}); {ORIENT} orientation: {len(ROWS)} rows need {STACK_USED:.3f}\" of the {STACK:g}\" side at the minimum gap; row gap {ROW_GAP:.3f}\", padding {STACK_PAD:.3f}\" at the ends of the stack, {EDGE:g}\" at the ends of the rows")
print("rows, top to bottom: " + " | ".join(("F " if f else "P ") + ("ITI" if c.get("T") else "".join(k * c[k] for k in "SIOAB" if k in c) + ("+U" if c.get("U") else "")) for c, _, f in ROWS))
if ERRORS:
    print(f"LAYOUT ERRORS ({len(ERRORS)}):")
    for m, _ in ERRORS:
        print("  -", m)
    sys.exit(2)
print(f"layout check passed: smallest gap {MIN_GAP:.4f}, smallest edge padding {MIN_EDGE:.4f}")
