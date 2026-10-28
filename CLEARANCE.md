# Clearances

Every place where parts mate and an explicit clearance or tolerance has to be chosen. The **Today** column
is what the current model assumes: **nominal sizes everywhere, zero clearance.** The **Decision** column is
left open until the plywood thickness and laser kerf are measured.

Dimensions below are for the current geometry: slotted parts (supports, rail inner plies) and divider B 3"
tall, rail outer plies and divider A 4" tall, slots and fingers 1 1/2" deep. Everything stands on the drawer
floor; the tabs run from the slot floor (1 1/2" up) to the top of the part, so 1 1/2" of each tab sits in a slot.

**The nest has some spare:** at x = 3" the rows are 1/4" apart and 1" of the 34" side is left over, held as 1/2" of
padding at the top and bottom. The three `O A A` rows have only 1/4" to spare across the 48" width, so a clearance
that lengthens the rail outer plies or divider A is limited to about 1/8" per part there (`nest.py --max` finds the
new limit for `x`).

## A. Inputs that affect everything

| # | Item | Why it matters | Today | Decision |
|---|---|---|---|---|
| A1 | **Actual plywood thickness.** "3/8" baltic birch is often 9 mm (0.354") and varies by sheet. | Every slot, tab and stack height is built from this one number. | exactly 0.375" | measure, then set |
| A2 | **Laser kerf and compensation.** Show nominal size and let the laser software offset, or bake the offset into the drawing. | Slots come out larger and tabs smaller by about one kerf, and the correction goes the other way for each. | no compensation | measure (the long test pieces on the sheet have slots from −0.5 to +0.5 mm around nominal, the fine ones from −0.06 to +0.06 mm) |

## B. The assembly in the drawer

| # | Interface | Today | Decision |
|---|---|---|---|
| B1 | Support length vs drawer width (32 3/8"). | Exact. The supports hold the assembly in place side to side, so it has to be snug and still go in. Plywood also moves a little with humidity. | |
| B2 | Rail length, tab to tab, vs drawer depth (20"). | Exact. Same snug-but-installable question, front to back. | |

## C. Supports and rails

| # | Interface | Today | Decision |
|---|---|---|---|
| C1 | Support slot width vs outer-ply tab thickness (3/8"). | Exact. | |
| C2 | Support slot depth vs tab height (1 1/2" each). | Exact (`SLOT_CLR = 0` in `drawer.py`). Decide whether the tab should bottom out in the slot or stop short. | |
| C3 | Tab length vs support thickness (3/8"), so the tab end is flush with the drawer wall. | Exact. | |
| C4 | Rail body length (19 1/4") vs the gap between the supports' inner faces (20" − 2 × 3/8"). Applies to both the inner and outer plies. | Exact. | |
| C5 | Slot position tolerance across the support, which sets the gaps between rail pairs (12 7/8" and 9 7/8"). | Exact. | |

## D. Rail plies

| # | Interface | Today | Decision |
|---|---|---|---|
| D1 | Dowel hole diameter vs dowel. Real dowels are 0.245–0.25", and kerf makes the holes a little larger. | 1/4" exactly. Tighter gives better registration; looser makes glue-up easier.measure (the test pieces have holes from −0.5 to +0.5 mm around 1/4") |
| D2 | Dowel length vs the 3/4" stack. | Not specified. | |
| D3 | Glue line thickness. It adds to the rail's 3/4" width and shrinks the gap between rails. | Zero. | |
| D4 | Inner and outer ply edge alignment at the top and bottom after glue-up. | Flush, nothing set. | |

## E. Dividers in the rails

| # | Interface | Today | Decision |
|---|---|---|---|
| E1 | Rail slot width (3/8") vs divider thickness (3/8"). Sets whether dividers slide in easily. | Exact. | |
| E2 | Divider tab length vs inner ply thickness. If the tab is longer than the slot is deep, the divider bottoms out on the outer ply. | Exact. | |
| E3 | Divider overall length vs gap width (12 7/8" and 9 7/8"). This is the total side-to-side play. | Gap + 2 × 3/8", exact. | |
| E4 | Divider tab height (1") vs rail slot depth (1"). | Exact. | |
| E5 | Divider seating. It can rest on the drawer floor or on the slot floors (its tab bottoms are 1 1/2" up, level with them), but it shouldn't do both. The same applies to the rail outer plies in the support slots. | Not decided: both are nominally in contact, so one of them will bind. | |

## F. Process effects that eat into the clearances

| # | Item | Why it matters | Decision |
|---|---|---|---|
| F1 | Glue squeeze-out into the rail slots and dowel holes. | Can narrow the slots by a few thousandths of an inch. | |
| F2 | Finish thickness (paint or poly) on every sliding surface. | Typically 0.002–0.005" per surface. | |
| F3 | Laser burn taper and char on cut edges. | Changes the effective size of tight slots. | |

**Chain to watch:** the divider length depends on the gap, the gap depends on the slot spacing minus the rail
thickness, and the rail thickness depends on the plywood and the glue line. Any error in A1 or D3 carries
through into the dividers.

## G. Spacing in the nested layout (not a fit, but set explicitly)

| # | Item | Value |
|---|---|---|
| G1 | Padding at the sheet edges | 1/2" top and bottom, 1/4" left and right (held by the `O A A` rows) |
| G2 | Gap between rows | 1/4" |
| G3 | Gap between parts within a row | equalized with the end padding per row (1/8" in the three `O A A` rows, at least 1/4" at the ends) |
| G4 | Tabs on neighbouring plain parts | not interlocked; at least the 1/8" gap apart |
| G5 | Minimum clearance around a dowel hole to the part edge | hole radius + half the part gap (0.1875"); the holes sit mid-spine, 0.6" from the nearest edge on the inner ply |

## Next step

Measure the plywood (A1) and the kerf (A2), then propose starting values for B–E and add them to
`drawer.py` as named settings so they can be changed in one place. `SLOT_CLR` (C2/E4) is the first one
already wired in.
