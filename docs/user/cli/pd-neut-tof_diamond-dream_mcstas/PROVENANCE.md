# pd-neut-tof_diamond-dream_mcstas — provenance

Diamond on DREAM (ESS), one McStas-simulated 90° time-of-flight bank, Jorgensen profile. The example catalogue's
diamond case: what `pd-neut-tof_diamond-dream_basic` checks with the scale alone, fitted here the way a user would.

## Sources

- **Data and model:** `pd-neut-tof_diamond-dream_basic` (built from the FullProf verification project
  `knowledge/verification/fullprof/pd-neut-tof_diamond-dream_basic/`; its `PROVENANCE.md` names the origin). The
  points are read from its `_data` loop by `tools/cli_projects/catalogue_tof_cases.py`; no fitted value is copied.
  Fd-3m (origin choice 1), C on 16c at (⅛, ⅛, ⅛) as in that model, bank 2θ 90°, DIFC 28385.86133 fixed, cut-off 30
  FWHM, the same excluded regions (below 9999 µs and above FullProf's TOF-max 66503.6875 µs).

## The start

| parameter | start | why |
| --- | --- | --- |
| zero | 0, free | the zero-shift rule |
| σ₀, σ₁, α₁, β₀ | 50000, 5000, 0.02, 0.01, free | one significant figure of the model's values; its four non-zero profile terms |
| cell a | 3.57, free | the model's 3.567 to two decimals |
| C Biso | 0.5, free | the displacement rule |
| scale | 10, free | one significant figure |
| background | 8 points, flat at the 10th percentile of the fitted counts, free | the background rule |

16 parameters are free: scale, zero, cell, Biso, four profile terms and eight background points.

## Check run

`python -m edi fit <copy> --dry --report machine`: converged in 10 iterations, `n_free=16`, `n_points_fitted=1948`,
reduced χ² 17.92, Rwp 16.75 %, under a second. The scale-only project pins reduced χ² 18.24 and Rwp 16.96 %, and
FullProf's own fit of the same model with 15 parameters free prints Rwp 16.9 and χ² 18.1. On one bank the zero and
the cell are strongly correlated: the fit ends at zero −56 µs and a 3.5692 Å, where the simulation used 3.567 Å.
