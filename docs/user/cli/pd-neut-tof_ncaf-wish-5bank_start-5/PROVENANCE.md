# pd-neut-tof_ncaf-wish-5bank_start-5 — provenance

The five-bank counterpart of `pd-neut-tof_ncaf-wish-3bank_start-5`, added on the owner's request (2026-09-30). Registered
**executing**: CI and `pixi run verify` run it through `python -m edi fit` on every pull request (about 16 s).

## Sources

- **FullProf reference:** `fullprof/tmpl_five_banks_p1.{pcr,out,sum}`, copied byte-identical from crysta `origin/main`
  at `fb9ffbe3`, path `tools/spikes/fullprof_ncaf_multibank/` (FullProf 8.40, `fp2k`). The `.out` refines 193
  parameters.
- **Data, excluded regions, background nodes and free set:** crysta `tools/spikes/ncaf_5bank_edi_perturbed/` at the
  same commit. Its data is FullProf's own converted intensity, and its excluded regions equal the `.pcr`'s for every
  pattern (pattern 1–5 = `wish_5_6`, `wish_4_7`, `wish_3_8`, `wish_2_9`, `wish_1_10`).
- **Layout and start convention:** `pd-neut-tof_ncaf-wish-3bank_start-5`. The structure file is that project's.

## The free set: 193, as in the FullProf `.out`

The spike's 189 free parameters, plus ABSCOR1 on patterns 1–4 (`.pcr` codes 91, 651, 971, 1331); ABSCOR1 stays fixed
at 0 on `wish_1_10`, as in the `.pcr`. Each bank's free flags were compared with the `.pcr` refinement codes: peak
shape, Zero and Dtt1, absorption, scale and background on patterns 1–4, and Zero, Dtt1, scale and background (34 of
36 nodes) on pattern 5.

## The start

Per bank, the peak-shape parameters and the scale are the `.pcr`'s input values. Positions come from the three-bank
project's structure file, and every Biso starts at 1.0. Backgrounds, Zero and ABSCOR1 start at 0.
Owner settings (2026-09-30): `_peak.cutoff_fwhm 8` on every experiment and `_minimizer.chi_square_tolerance 1e-4`.

## Check run

`python -m edi fit <copy> --dry --report machine` (edi at `f5ea155`, its default descent): converged in 5 iterations,
`n_free=193`, `n_points_fitted=18973`, `reduced_chi_square=9.497535494`, `rwp=0.07694458606`, about 13 s. FullProf's
global user-weighted χ² (Bragg contribution) for the same five banks is 9.96 (`fullprof/tmpl_five_banks_p1.sum`).
Per bank, Rwp agrees with FullProf within 0.02 % and Σw·r² within 0.4 %. Every fitted position and Biso, and every
per-bank parameter, is within 0.36 of FullProf's σ. Two differences are open as crysta issues: `wish_5_6`'s
out-of-order first background nodes, and uncertainties about 0.44 of FullProf's.

## expected.json

FullProf references (`kind: reference`): `n_free` and each independent position and Biso, each with FullProf's sigma
as its tolerance. Regression pins (`kind: regression-pin`) from the `python -m edi fit` run above: `iterations`,
`n_points_fitted`, `reduced_chi_square` and `rwp`. They gate drift, not correctness.

**Follower free flags removed.** Al1, Na1 and F3 sit on `x,x,x`, where y and z follow x, and the structure flagged all
three axes free. A free flag on a dependent is ignored with a warning and saved bare, so every load warned about the
two follower flags; the structure now flags x alone. The free set is unchanged and the project still reproduces its
pins (`tools/checks/cli_projects.py --project`).
