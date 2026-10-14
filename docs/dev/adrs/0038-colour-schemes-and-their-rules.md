# Colour schemes and their rules

- **Status:** Accepted
- **Date:** 2026-10-14
- **Implementation:** 🟡 Partially implemented: the eighteen schemes, their tables and generator are in; the checks
  that hold every rule follow
- **Priority:** Medium

## Context

The first five schemes mixed colours of very different lightness and saturation, and several sat close to the red
calculated pattern, so the fit no longer stood out. The owner asked for calm, modern palettes that sit well with the
red calculated curve, in light and dark versions, with a choice of schemes. The study behind this decision (mockups
with measured points, the fit, filled structure contributions and scans; research on data-visualisation palettes and
colour preference) found:

- colour preference follows associations: blues, cyans and greens are liked, dark yellow, olive and brown disliked
  (Palmer and Schloss, 2010);
- a palette looks designed when its colours share lightness and saturation and differ in hue, in a perceptual space
  (Oklab);
- people tell apart about seven categorical colours at a glance (Healey, 1996); beyond that a gradient reads better;
- warm, saturated colours draw the eye, so the calculated pattern should be the only one on a chart;
- transparent fills that overlap mix into colours no legend shows, and strong colours are too strong as fills.

## Decision

1. **Eighteen schemes, Coast the default.** edi's own Coast, Garden, Peaceful, Fog forest and Sage, designed from
   nature palettes; the published data palettes Okabe-Ito, Paul Tol bright and muted, Tableau 10, Observable 10, IBM
   Carbon, ColorBrewer Dark2, Petroff and Vivid; and the app themes Nord, Solarized, Catppuccin and Apple. Each has
   light and dark colours, cited in `data/palettes/PROVENANCE.md` with its source and licence. An unknown stored scheme
   name reads as Coast.
2. **Measured data stay out of the calculated curve's hue range** (within 45° of either theme's calc hue in Oklab); a
   published colour inside it goes to the end of its set. A set has at most seven colours.
3. **Every colour keeps 3:1 contrast** against its theme's chart background, at least 0.10 Oklab from the calculated
   colour and 0.08 from the others in its set, as `PROVENANCE.md`'s rules state.
4. **Many datasets (a sequential fit) take a two-colour gradient** with lightness rising steadily from the first
   dataset to the last, a path between the two colours that avoids the calculated curve's hue range, and 3:1 contrast
   at every point along it, not only at the ends.
5. **Structure colours are muted**, up to five per scheme, each with its own hue and lightness step and distinct from
   the scheme's measured-data colours, so they stay apart as soft fills under the total curve.
6. **A report always takes the light colours.**

## Consequences

- The colour checks gate every rule above for every scheme, in both themes.
- A filled per-structure contribution (planned) uses the structure colours with a clear outline and fills that do not
  stack.

## Alternatives considered

- **Keep five schemes.** Rejected by the owner: too few choices and not pleasant enough.
- **Pure nature palettes for data lines.** Rejected: they rely on lightness steps, which the contrast rule removes;
  at one lightness their earthy colours become indistinguishable. They work as soft fills, so structures use them.
