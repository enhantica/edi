# pd-neut-tof_cecoal-polaris_basic — provenance

CeCoAl₃ on POLARIS (ISIS), one time-of-flight bank, Jorgensen–Von Dreele profile, cylinder absorption, a 24-term
Chebyshev background. The example catalogue's CeCoAl₃ case, started the way a user's own measurement would be.

## Sources

- **Data and model:** `pd-neut-tof_cecoal-polaris_chebyshev`, built from FullProf's own example (the fitting project
  `knowledge/fitting/fullprof/pd-neut-tof_cecoal-polaris_chebyshev/`). The points are read from its `_data` loop by
  `tools/cli_projects/catalogue_tof_cases.py`; no fitted value is copied. Pmma, bank 2θ 145°, DIFC 6176.03076 fixed,
  cut-off 4.2 FWHM, the same excluded regions and Chebyshev domain (3001.5891 to 19004.6582 µs).

## The start

| parameter | start | why |
| --- | --- | --- |
| zero | 0, free | the zero-shift rule |
| DIFA | −1.92194, free | the calibration value the source declares |
| σ₁, γ₁ | 40, 5, free | one significant figure of the source's values |
| α₁, β₀, β₁ | 0.2971, 0.043085, 0.002867, fixed | the instrument's resolution, fixed in the source |
| ABSCOR1 | 0, free | no absorption until fitted |
| cell | 7.65, 4.05, 6.91 Å, free | the source's cell to two decimals |
| Ce z, Co z, Al2 z, Al3 x and z | 0.38, 0.81, 0.04, 0.07, 0.70, free | the source's positions to two decimals |
| Al3 occupancy | 1, free | as the source |
| Biso | 0.5 on every site, free | the displacement rule |
| scale | 20000, free | one significant figure |
| background | constant term at the 10th percentile of the fitted counts, orders 1 to 11 at 0, all twelve free; orders 12 to 23 fixed at 0 | the background rule on the source's free terms |

32 parameters are free: the source project's free set.

## Check run

`python -m edi fit <copy> --dry --report machine`: converged in 5 iterations, `n_free=32`, `n_points_fitted=3692`,
reduced χ² 2.8695, Rwp 2.088 %, under a second. That is the source project's minimum (reduced χ² 2.8695, Rwp
2.088 %); FullProf's least-squares fit of the same model prints χ² 2.85 and Rwp 2.08.
