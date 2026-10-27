# Colour schemes and their rules

- **Status:** Accepted
- **Date:** 2026-10-14, revised 2026-10-21 (five Edi palettes replace the eighteen schemes) and 2026-10-26 (one
  figure palette of eleven colours for experiments and structures)
- **Implementation:** ✅ Implemented: the five palettes, their tables and the position assignment in the core
- **Priority:** Medium

## Context

The first version of this decision (2026-10-14) offered eighteen schemes: five of edi's own, nine published data
palettes and four app themes, each adapted by a generator to contrast and distance rules. In use the choice was too
wide, the structure colours were too muted to tell apart as Bragg ticks and icons, and the calculated, background and
residual curves kept fixed colours that did not belong to any scheme. The owner reviewed a study of five candidate
palettes, each with measured-data colours, structure colours and role colours in both themes, ordered so that the most
distinct colours come first, and approved them with their exact values on 2026-10-21.

The study behind the order, kept for reference: colour preference follows associations, with blues, cyans and greens
liked (Palmer and Schloss, 2010); people tell apart about seven categorical colours at a glance (Healey, 1996), and
beyond that a gradient reads better; a palette looks designed when its colours share lightness and saturation and
differ in hue in a perceptual space (Oklab).

## Decision

The 2026-10-26 revision replaces the five Edi palettes and their separate measured and structure groups. On the
owner's mockups, two groups gave neighbouring experiments and structures colours that were hard to tell apart, the
first colours of both groups were spent before the best ones of either, and a project with many experiments ran out of
colours early. The owner chose, by eye, five palettes of eleven colours each that experiments and structures share.

1. **Five palettes, Earth the default.** Earth, Classic, Soft, Natural and Colour-blind safe, listed in that order.
   Their colours are stored in `data/palettes/*.tsv` exactly as approved and are never regenerated or retuned;
   `data/palettes/PROVENANCE.md` records them. A stored palette of the earlier five reads as its nearest new one: Edi
   Natural and Edi Coast as Natural, Edi Garden and Edi Studio as Classic, Edi Contrast as Colour-blind safe (the
   nearest by mean Oklab distance, except Edi Contrast, which goes to the palette made for the same purpose). Any other
   stored name reads as Earth. The app keeps the palette it reads.
2. **One palette for every item.** Preferences offer one palette choice for experiments and structures; the app, the
   report, the CLI and Python use the same one. Each palette has, in each theme, eleven figure colours in the order
   items take them and three role colours: the total calculation, the same crimson in every palette (`#AD1A6B` light,
   `#FC4F81` dark), and the background and difference greys.
3. **Positions.** Each experiment and structure holds a position in the palette's order, from 0. A block keeps its
   position while it exists; a new one takes the lowest free position its kind may take, so removing a block frees its
   colour for the next. In Earth a structure never takes position 0 or 1, which are kept for experiments; in the other
   four palettes any item takes any position. A project opened, with no positions yet, gives them to its experiments in
   their order and then to its structures. Positions 0 to 10 take the palette's colours; a position p past them takes
   a shade between its first two colours, mixed in Oklab (Björn Ottosson, 2020), at t = (p - 10) / (n - 10) where n is
   one past the last position the project uses, so no shade repeats either end. `edi::colour_positions` and
   `edi::figure_colour` are the only implementation.
4. **One colour per block.** An experiment's measured curve, icon and report figures, and a structure's Bragg ticks,
   icon and curve, all take the colour at its position. A scan's datasets take, in order, the positions the project's
   structures leave free, on the pattern chart and on Stacked alike; a view showing more patterns than the palette has
   colours gives them only colours 1 and 2, from colour 1 at the first to colour 2 at the last through Oklab shades (the
   owner, 2026-10-27).
5. **Drawing.** Widths, marker sizes, opacities and dashes stay as ADR-0017 §15 states them. Measured data are filled
   markers with connecting lines, drawn under the calculated curves; the total calculation is a line in its role
   colour with no fill; the background and the difference take their role colours.
6. **Light exports.** The PDF and HTML reports and every saved chart picture take the light colours, whatever the
   app's theme, and any colour rule that follows the theme (a Map direction of Auto, ADR-0041) resolves as in the light
   theme there.
7. **Colour order in Preferences.** Beside the palette choice, positions 1 to 11 in the palette's colours: a position
   the open project uses shows its block's icon in that colour, a free one a plain square, and the calculated colour is
   set apart as the calculator icon labelled "calc". One line under it says each new experiment or structure takes the
   next free colour. It follows the open project as blocks are added and removed.
8. **Colour-blind safe** was chosen by comparing the colours under simulated protanopia, deuteranopia and tritanopia;
   it is no guarantee for every colour-vision deficiency.

## Consequences

- The palette data and the assignment live in the core (`core/src/palette.cpp`, the tables embedded at build time);
  QML, the report, the demos and the icons ask the core and hold no colour of their own. The open project holds each
  block's position; the report is given the app's positions so its figures match the pages.
- Positions are not saved: a project opened again gives its experiments the first positions, then its structures, so
  a block added between two others in an earlier session can come back in another colour.
- `tools/palettes/check.py` checks the tables' shape and that `PROVENANCE.md` lists the same values. It writes
  nothing, so no tool can overwrite the approved colours.
- The earlier rules that moved colours for contrast and distance no longer apply: the approved values are the data.

## Alternatives considered

- **Keep separate measured and structure groups.** Rejected by the owner (2026-10-26): the first colours of both groups
  were used before the best colours of either, and an experiment and a structure could look alike.
- **Save each block's position in the project.** Not done: the position is a choice of view, which ADR-0031 keeps out
  of the project's files, and the reopened order is the one a new project would take.

- **Keep the eighteen schemes.** Rejected by the owner: too many choices, and the structure colours were too muted.
- **Cycle through the five colours past five items.** Rejected: two datasets of one scan would share a colour.
- **Append a gradient after the fifth colour.** Rejected for the earlier five-colour groups: the first five would no
  longer follow the scan's order. With eleven colours the owner chose shades of the first two past the eleventh
  (2026-10-26), as a scan of more than eleven datasets needs more colours than any palette can tell apart.
