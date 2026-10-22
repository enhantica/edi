# Colour schemes and their rules

- **Status:** Accepted
- **Date:** 2026-10-14, revised 2026-10-21 (five Edi palettes replace the eighteen schemes)
- **Implementation:** ✅ Implemented: the five palettes, their tables and the count-aware assignment in the core
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

1. **Five palettes, Edi Natural the default.** Edi Natural, Edi Coast, Edi Garden, Edi Studio and Edi Contrast, listed
   in that order. Their colours are stored in `data/palettes/edi-*.tsv` exactly as approved and are never regenerated
   or retuned; `data/palettes/PROVENANCE.md` cites each colour's source. A stored scheme name that is not one of the
   five (the eighteen earlier schemes included) reads as Edi Natural, and the app keeps that choice.
2. **Roles.** Each palette has, in each theme, five measured colours in the order slate, blue, green, teal,
   violet (the first two swapped by the owner on 2026-10-22; slate made from each palette's former raspberry in Oklab: the same lightness, 0.38 of its chroma, hue
   250°, as raspberry sat too close to the rose calculated curve); five structure colours in the order orange, gold, brown, amber, olive; and three role colours: total
   calculation, background and difference. The first colour and the whole order are the same in both themes.
3. **Assignment.** Datasets and structures are assigned separately, each from its own group, by its place among its
   own kind. Up to five items take the first colours of the group in order. More than five take a gradient over the
   whole group instead, from the group's first colour to its second: item i of N, counted from zero, takes
   t = i / (N − 1), mixed in Oklab (Björn Ottosson, 2020), with the two ends the stored colours themselves and every
   result a valid sRGB colour. The gradient never cycles through the five and never follows them. A place past the
   last item takes the last item's colour, and no assignment divides by zero.
4. **One colour per dataset or structure.** Its measured curve, Bragg ticks, icon, report figures and, when they
   come, its structure curve and fill all take the colour of item 3.
5. **Drawing.** Widths, marker sizes, opacities and dashes stay as ADR-0017 §15 states them. Measured data are filled
   markers with connecting lines, drawn under the calculated curves; the total calculation is a line in its role
   colour with no fill; the background and the difference take their role colours.
6. **A report always takes the light colours.**
7. **Edi Contrast** is a custom palette for colour-vision differences, inspired by the Okabe–Ito palette and Paul
   Tol's schemes. It is not either of them, and it is no guarantee for every colour-vision deficiency.

## Consequences

- The palette data and the assignment live in the core (`core/src/palette.cpp`, the tables embedded at build time);
  QML, the report, the demos and the icons ask the core and hold no colour of their own.
- `tools/palettes/check.py` checks the tables' shape and that `PROVENANCE.md` lists the same values. It writes
  nothing, so no tool can overwrite the approved colours.
- The earlier rules that moved colours for contrast and distance no longer apply: the approved values are the data.

## Alternatives considered

- **Keep the eighteen schemes.** Rejected by the owner: too many choices, and the structure colours were too muted.
- **Cycle through the five colours past five items.** Rejected: two datasets of one scan would share a colour.
- **Append a gradient after the fifth colour.** Rejected: the first five would no longer follow the scan's order.
