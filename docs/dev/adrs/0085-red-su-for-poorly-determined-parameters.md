# 0085. A red s.u. for a poorly determined or strongly correlated parameter

- **Status:** Accepted
- **Date:** 2026-11-11
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

After a fit, the Analysis table showed every s.u. alike. A parameter the data cannot pin down, such as two B iso
values sharing one site in LBCO on HRPT (0.40 with s.u. 1900 and 3000), looked as settled as any other until the
Correlations tab was opened. The owner asked for such values to be flagged in the table itself (2026-11-01 and
2026-11-11). Some parameters may rightly sit at or near zero, such as a zero shift or an asymmetry term, and a
large s.u. beside a near-zero value says nothing bad about them.

## Decision

After a fit, a free parameter's s.u. is shown red for either of two reasons, one colour for both:

1. **Poorly determined:** |s.u.| > |value|, unless crysta's dictionary marks the item `near_zero`.
2. **Strongly correlated:** |r| ≥ 0.95 (`kStrongCorrelation`) with another free parameter of the same fit.

Its tooltip says why, one line per reason that applies: "s.u. larger than the value", and "strongly correlated
with <partner> (r = 0.97)" naming the strongest partner. One function, `edi::su_marks`, decides both for every
form: the app's Analysis table, the report and notebook tables (red, the reasons in the cell's title) and the CLI
table (a `!` after the s.u., the reasons listed under the table).

The `near_zero` items are crysta's dictionary (the `near_zero` column): atom coordinates, the anisotropic
off-diagonal terms, magnetic moment components and form-factor weights, the TOF and 2θ zero offsets and the
quadratic and reciprocal TOF terms, sample displacement and transparency, every asymmetry and FCJ term, the TOF
rise and decay terms, the Gaussian variance, Caglioti U and V, every Lorentzian, size and strain term, the
pseudo-Voigt mixing terms, extinction and absorption coefficients, the March-Dollase random fraction and
background coefficients. Cell lengths and angles, scale, isotropic and diagonal displacements, occupancy,
Caglioti W, wavelengths and background anchor intensities are not exempt.

## Consequences

A badly determined or confounded parameter shows where it is edited. The exempt list lives in one table beside
the parameter definitions, so a new parameter is decided there. A scan's per-file correlations are not marked:
the table shows the template's fit.

## Alternatives considered

- A separate warning colour and icon for correlations: dropped by the owner (2026-11-11), one red and two tooltips
  read more simply.
- A relative threshold per parameter family in the GUI: a guess outside the dictionary, and different in each form.
