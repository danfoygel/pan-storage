# Clearances

Every place where parts mate and an explicit clearance or tolerance has to be chosen, and what was decided. The
values are named settings at the top of [`drawer.py`](drawer.py), so each one can be changed in one place and the
drawings and cut files regenerate:

| Setting | Value | Used for |
|---|---|---|
| `T` | 9.4 mm (0.370"), measured | plywood thickness, the base of every slot, tab and rail width |
| `SLIP` | **0 until measured** | added to `T` for every slot: support slots (C1) and rail slots (E1) |
| `DOWEL_SLIP` | **0 until measured** | added to the 1/4" dowel for every dowel hole (D1) |
| `TAB_LIFT` | 1/16" | tabs start this far above the slot floor (C2, E4, E5) |
| `TAB_SHORT` | 1/32" | tabs stop this far short of the far face of the part they pass through (C3, E2) |
| `RAIL_END_CLR` | 1/32" in all | rail bodies shorter than the space between the supports (C4) |
| `DIV_END_CLR` | 1/32" in all | divider bodies shorter than their gap (E3) |

**Setting `SLIP` and `DOWEL_SLIP`:** the test pieces' slots are `T` + the engraved offset and their holes are 1/4" +
the offset, so the label of the slot (or hole) that is snug but goes in by hand *is* the slip: a long-piece label of
"+1" is +0.1 mm, so `SLIP = 0.1 / 25.4`. Narrow it down with the fine pieces (set `FINE_STEPS_MM` in `nest.py`
around that value first). Fit-test with the finish you will use.

All sizes in the drawing are finished sizes: **the laser software applies the kerf offset** (A2).

## A. Inputs that affect everything

| # | Item | Decision |
|---|---|---|
| A1 | Actual plywood thickness | **9.4 mm (0.370")**, measured. `T` in `drawer.py`; the test pieces are relative to it (`TEST_NOMINAL = T`). |
| A2 | Laser kerf and compensation | **The laser software offsets for kerf.** The drawing is at finished size. |

## B. The assembly in the drawer

| # | Interface | Decision |
|---|---|---|
| B1 | Support length vs drawer width | **No added clearance.** The 32 3/8" input already has about 1/16" of play. |
| B2 | Rail length vs drawer depth | **No added clearance.** The 20" input already has about 1/16" of play (the rails are a further 1/16" short over the tabs, from C3). |

## C. Supports and rails

| # | Interface | Decision |
|---|---|---|
| C1 | Support slot width vs outer-ply tab | Slot = `T` + `SLIP`. |
| C2 | Support slot depth vs tab height | **Slots stay 1 1/2" deep; the tabs start `TAB_LIFT` = 1/16" higher**, at 1 9/16", so they never bottom out (2 7/16" tall on the rail outer plies and divider A, 1 7/16" on divider B). |
| C3 | Tab length vs support thickness | **1/32" short** (`TAB_SHORT`): the tab end stops 1/32" inside the support's outer face. |
| C4 | Rail body length vs the space between the supports | **1/32" short in all** (`RAIL_END_CLR`), 1/64" at each end. |
| C5 | Slot position tolerance across the support | Laser accuracy; no clearance. |

## D. Rail plies

| # | Interface | Decision |
|---|---|---|
| D1 | Dowel hole diameter vs dowel | Hole = 1/4" + `DOWEL_SLIP`. |
| D2 | Dowel length | Not modelled: the dowels are bought or cut by hand, not lasered. |
| D3 | Glue line thickness | **Zero.** The rail is 2 × `T` = 0.740". |
| D4 | Inner and outer ply edge alignment | Bottoms flush, set by the dowels. |

## E. Dividers in the rails

| # | Interface | Decision |
|---|---|---|
| E1 | Rail slot width vs divider thickness | Slot = `T` + `SLIP`. |
| E2 | Divider tab length vs inner ply thickness | **1/32" short** (`TAB_SHORT`), so the tab end never touches the outer ply. |
| E3 | Divider body length vs gap | **1/32" short in all** (`DIV_END_CLR`). |
| E4 | Divider tab height vs rail slot depth | As C2: the tabs start 1/16" above the slot floor. |
| E5 | Divider seating | **On the drawer floor.** The tabs clear the slot floors by 1/16", for the rail outer plies too. |

## F. Process effects

| # | Item | Decision |
|---|---|---|
| F1 | Glue squeeze-out into the rail slots and dowel holes | No separate allowance; keep glue out of the slots, and `SLIP` covers the rest. |
| F2 | Finish thickness | No separate allowance; fit-test with the finish on so the measured `SLIP` includes it. |
| F3 | Laser burn taper and char | No separate allowance; it shows up in the test pieces and so in `SLIP`. |

**Chain to watch:** the divider length depends on the gap, the gap depends on the slot spacing minus the rail
thickness, and the rail thickness is 2 × `T` (glue line zero). With `T` = 0.370" the gaps are 12.890" and 9.890"
(5/1000" wider than with 3/8" plywood, per ply). A change to `T` carries through into the dividers.

## Resulting sizes

| Part | Size |
|---|---|
| Rail outer ply | 19.938" over the tabs, 19.229" body, tabs 0.354" long × 2 7/16" tall (from 1 9/16" up) |
| Rail inner ply | 19.229" long, slots `T` + `SLIP` wide × 1 1/2" deep |
| Divider A | 13.567" over the tabs, 12.859" body (12.890" gap), tabs 2 7/16" tall |
| Divider B | 10.567" over the tabs, 9.859" body (9.890" gap), tabs 1 7/16" tall |
| Support | 32 3/8", slots `T` + `SLIP` wide × 1 1/2" deep |

## G. Spacing in the nested layout (not a fit, but set explicitly)

| # | Item | Value |
|---|---|---|
| G1 | Padding at the sheet edges | 1/2" top and bottom, at least 1/4" left and right |
| G2 | Gap between rows | 1/4" |
| G3 | Gap between parts within a row | equalized with the end padding per row (at least 1/8" between parts, 1/4" at the ends) |
| G4 | Tabs on neighbouring plain parts | not interlocked; at least the 1/8" gap apart |
| G5 | Minimum clearance around a dowel hole to the part edge | hole radius + half the part gap (0.1875"); the holes sit mid-spine, 0.6" from the nearest edge on the inner ply |

## Next step

Cut the long test pieces, read off `SLIP` and `DOWEL_SLIP`, refine `SLIP` with the fine pieces, put both values in
`drawer.py` and regenerate (`python3 drawer.py && python3 nest.py && python3 perspective.py`).
