# 0047. Element colours readable in 2D

- **Status:** Accepted
- **Date:** 2026-10-22, amended 2026-10-26 (2:1 instead of 3:1; the scheme names Jmol and VESTA)
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

Element colours come from the Jmol and VESTA tables (ADR-0022 §4). In the 3D structure view they colour shaded
spheres, which read on both themes. Drawn flat, as atom icons and coloured labels in tables, the structure view's
legend and the report's legend, some are hard to see: sulfur's yellow on the light theme, lead's dark grey on the dark
one. The owner chose, on 2026-10-22, to adjust the colour's lightness rather than add outlines, halos or shading.

## Decision

1. **One rule.** Wherever an element colour is drawn in 2D, it is the scheme colour with its Oklab lightness moved by
   the least amount that gives at least 2:1 contrast (WCAG 2) with the background it is drawn on, towards black or
   white, whichever the background contrasts with more. A colour that already has 2:1 is drawn byte for byte as it is.
   The hue is always kept, and the chroma too wherever sRGB can show it at the new lightness. Where it cannot (bright
   yellows and greens on white, deep blues and reds on dark grey), the colour keeps as much chroma as sRGB allows there.
   `edi::readable_colour` in the core is the only implementation, one function for both schemes, Jmol and VESTA. The
   owner lowered the ratio from 3:1 on 2026-10-26: at 3:1 most colours moved far from their source and H and C became
   the same grey on the light theme; at 2:1 the average move on 31 common elements is about half, and H (`#AEADAD`) and C
   (`#909090`) differ. Pairs alike in the source tables themselves (Sr and Ba, Tb and Dy) stay alike; the symbol beside
   the icon tells them apart.
2. **Backgrounds.** A table cell's colour reads on every underlay it can have: both alternating row colours, the
   hover tint and the page behind the table, so the colour is the furthest moved of these, and one that reads on all
   keeps its bytes. The
   structure view's legend is measured against its own background and the report against its white paper.
3. **3D unchanged.** The structure view's spheres keep the scheme colours exactly.
4. **Names.** The scheme selector shows the schemes as their authors spell them, Jmol and VESTA (the option values stay
   diffraction-lib's `jmol` and `vesta`). Its tooltip says the colours are adjusted for contrast in labels and tables.

## Consequences

Pale and dark elements read in every 2D place on both themes. A 2D colour can differ slightly from the 3D sphere of
the same element. New 2D uses of an element colour go through the same function with their own background.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| A contrasting outline or halo around the icon | Rejected by the owner: busier, and it does not help coloured text |
| Shaded icons like the 3D spheres | Rejected: icons are too small for shading to read |
| Our own lighter and darker tables per theme | Rejected: two more tables to keep, for the same result as the rule |
