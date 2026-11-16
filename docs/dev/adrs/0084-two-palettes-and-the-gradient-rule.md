# 0084. Two palettes, and a gradient for many datasets

- **Status:** Accepted
- **Date:** 2026-11-10
- **Implementation:** ✅ Implemented: the two palettes, the role positions, the gradient rule and the Preferences strips
- **Priority:** Medium
- **Amends:** ADR-0038 §1–4 and §7

## Context

ADR-0038 offered five palettes of eleven colours. In use, five choices were more than anyone needed, the structure
colours were hard to tell apart as fills, and the separate Stacked colour choice (any palette or one of six colour
maps) could disagree with the palette the Pattern view used. A view of many datasets went on through eleven discrete
colours before it became a gradient, although nobody can tell eight colours apart at a glance, let alone eleven.

## Decision

1. **Two palettes, Main the default.** Main and Colour-blind safe, stored in `data/palettes/main.tsv` and
   `colour-blind-safe.tsv` with their provenance in `data/palettes/PROVENANCE.md`. Any earlier palette name reads as
   Main, except the earlier colour-blind palette, which reads as Colour-blind safe.
2. **Colours by role.** Each palette lists, in each theme: experiments 1 and 2, structures 1 to 3 (orange, teal,
   magenta), then six colours that further experiments and structures share in the order they are added. The total
   calculated curve has its own colour per palette; the background and difference greys are edi's own.
3. **Positions.** Experiments take positions 0 and 1, structures 2 to 4, and both share positions 5 to 10. A block
   keeps its position while it exists, as before. Past position 10, items take Oklab shades between experiment 1's and
   experiment 2's colours (ADR-0038 §3).
4. **One rule for Pattern and Stacked.** A view that draws several datasets together gives them the palette's free
   experiment colours while there are enough: experiments 1 and 2 and the six shared colours, so eight, fewer when
   structures 4 and up already use shared colours. From one more on, every dataset takes an evenly spaced Oklab shade
   from experiment 1's colour at the first to experiment 2's at the last, ending exactly on both
   (`edi::pattern_set_colour`). The Stacked view follows the palette; it no longer has a choice of its own. The Map
   view keeps its own colour map.
5. **Preferences.** One Palette selector for every chart. Under each colour selector a thin strip shows the colours it
   gives: the palette's eleven colours, the Map's colour map, and the moment arrows' colours.
6. **Colour-blind safe dark, experiment 2.** It was made lighter and more saturated (`#BAB58E` in place of `#AEA381`)
   so the whole experiment gradient stays at least 8 CIEDE2000 from the dark background grey, keeping the palette's
   colour-blind distances (PROVENANCE.md).

## Consequences

- A stored Stacked choice is no longer read; the Stacked view takes the palette.
- Reports follow the palette as before, in its light colours.
- A gradient shows the order of a series, not which dataset is which: the legend, hover and selection name each
  dataset.

## Alternatives considered

- **CIELAB instead of Oklab for the gradient.** Rejected: its middle runs greyer and closer to the background grey,
  and edi already mixes in Oklab.
- **A dashed background line when a gradient is shown.** Not needed once the Colour-blind safe dark experiment 2 was
  moved away from grey.
- **Keep the colour maps for Stacked.** Rejected by the owner: one selector for Pattern and Stacked.


## Verification after the palette transition

The native presentation/report boundary uses both active palettes and preserves
its light/dark, per-structure identity and overflow checks. Its expected colours
come from the exact approved palette document in published release b16f9867,
with the source hash recorded beside the generated fixture and independent Oklab
mixing retained. Earlier five-palette owner captures remain historical inputs;
they are not rewritten to make the new product reproduce retired colour schemes.
Role-style expectations use the same approved Main colours and retain all width
and marker requirements.
