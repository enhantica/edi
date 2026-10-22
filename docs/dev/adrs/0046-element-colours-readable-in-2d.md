# 0046. Element colours readable in 2D

- **Status:** Accepted
- **Date:** 2026-10-22
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

Element colours come from the Jmol and VESTA tables (ADR-0022 §4). In the 3D structure view they colour shaded
spheres, which read on both themes. Drawn flat, as atom icons and coloured labels in tables, the structure view's
legend and the report's legend, some are hard to see: sulfur's yellow on the light theme, lead's dark grey on the dark
one. The owner chose, on 2026-10-22, to adjust the colour's lightness rather than add outlines, halos or shading.

## Decision

1. **One rule.** Wherever an element colour is drawn in 2D, it is the scheme colour with its Oklab lightness moved,
   hue and chroma kept, by the least amount that gives at least 3:1 contrast (WCAG 2) with the background it is drawn
   on. It moves towards black or white, whichever the background contrasts with more. A colour that already has 3:1
   is drawn as it is. `edi::readable_colour` in the core is the only implementation.
2. **Backgrounds.** Tables and lists are measured against the theme's content background, the darker of the light
   rows and the lighter of the dark ones, so every row passes. The structure view's legend uses its own background
   and the report its white paper.
3. **3D unchanged.** The structure view's spheres keep the scheme colours exactly.
4. **Names kept.** The scheme selector still says jmol and vesta, since the tables themselves are unchanged. Its
   tooltip says the colours are adjusted for contrast in labels and tables.

## Consequences

Pale and dark elements read in every 2D place on both themes. A 2D colour can differ slightly from the 3D sphere of
the same element. New 2D uses of an element colour go through the same function with their own background.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| A contrasting outline or halo around the icon | Rejected by the owner: busier, and it does not help coloured text |
| Shaded icons like the 3D spheres | Rejected: icons are too small for shading to read |
| Our own lighter and darker tables per theme | Rejected: two more tables to keep, for the same result as the rule |
