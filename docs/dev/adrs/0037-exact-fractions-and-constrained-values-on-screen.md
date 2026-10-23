# Exact fractions and constrained values on screen

- **Status:** Accepted
- **Date:** 2026-10-14
- **Implementation:** ⏳ Planned, with the parameter display precision work
- **Priority:** Medium

## Context

A coordinate on a special position is shown in full, `0.3333333333333333`, in the app, in its text mode and in the
report. A constrained occupancy in the LBCO example shows floating-point noise, `0.42000000000000004`, next to the free
value `0.58(3)` it is computed from. Both read badly, and the owner asked for exact fractions such as `1/3` and `1/2`.

The engine decides what the files hold: a symmetry-fixed value is written as its exact decimal without an s.u. (CIF
has no fraction syntax), and a constrained value carries the s.u. its constraint passes on, written by the IUCr rule,
with the CIF refinement flags `S` (special-position constraint) and `P` (site-occupancy constraint).

## Decision

1. **A value fixed by symmetry is shown as its exact fraction** wherever edi displays it for reading: the parameter
   tables, the text views and the HTML and PDF report. The fraction is recognised from the space group's constraint on
   that coordinate, not guessed from the digits: the multiples of 1/2, 1/3, 1/4, 1/6, 1/8 and 1/12 that the
   crystallographic special positions use, shown in lowest terms with no s.u. (`1/3`, `2/3`, `1/4`, `3/4`). A value
   the constraint does not fix is never turned into a fraction, however close it is to one.
2. **A constrained value is shown with the s.u. its constraint passes on**, rounded by the project's IUCr rule like a
   free value (`0.42(3)`), greyed and read-only like the other constrained values. Before a fit gives it an s.u., it
   is shown rounded to the precision of the values it is computed from, never with floating-point noise.
3. **The files keep the exact decimal**, as the engine writes it; a fraction is display only. The CIF report writes decimals,
   so a CIF reader never meets `1/3`.

## Consequences

- The parameter tables need the symmetry constraint of each coordinate, which crysta's site-symmetry constraints
  already provide.
- Editing a symmetry-fixed value stays impossible; editing never meets a fraction.

## Alternatives considered

- **Round to a fixed number of decimals (`0.3333`).** Rejected by the owner, who asked for exact fractions; a rounded
  decimal also hides that the value is exact.
- **Recognise fractions from the digits alone.** Rejected: a refined coordinate near `0.3333` would be shown as an exact
  `1/3` it is not.
