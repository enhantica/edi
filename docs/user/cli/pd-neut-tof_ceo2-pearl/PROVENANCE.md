# pd-neut-tof_ceo2-pearl — provenance

CeO₂ (NBS SRM 674a) on PEARL (ISIS), one time-of-flight bank, Jorgensen–Von Dreele profile, cylinder absorption, a
six-term polynomial background. A calibration: the standard's cell is fixed and the bank's zero, DIFC and DIFA are
fitted. The example catalogue's CeO₂ case, started the way a user's own measurement would be.

## Sources

- **Data and model:** `pd-neut-tof_ceo2-pearl_polynomial`, built from FullProf's own example (the fitting project
  `knowledge/fitting/fullprof/pd-neut-tof_ceo2-pearl_polynomial/`). The points are read from its `_data` loop by
  `tools/cli_projects/catalogue_tof_cases.py`; no fitted value is copied. The data are a PEARL (ISIS) measurement from FullProf's
  examples; licence not recorded. Fm-3m, cell 5.410495 Å fixed, bank 2θ 90°,
  cut-off 8 FWHM, the same excluded regions, polynomial origin 7000 µs.

## The start

| parameter | start | why |
| --- | --- | --- |
| zero | 0, free | the zero-shift rule |
| DIFC | 4680, free | a nominal value: the source declares none apart from its fitted 4677.93, so three significant figures of it |
| DIFA | 1.7621, free | the calibration value the source declares |
| α₁, β₀, β₁, σ₁, σ₂, γ₁ | 0.3, 0.03, 0.03, 80, 4, 5, free | one significant figure of the source's values |
| ABSCOR1 | 0, free | no absorption until fitted |
| Biso | 0.5 on both sites, free | the displacement rule |
| scale | 2000, free | one significant figure |
| background | constant term at the 10th percentile of the fitted counts, orders 1 to 5 at 0, all free | the background rule |

19 parameters are free: the source project's free set.

## Check run

`python -m edi fit <copy> --dry --report machine`: converged in 5 iterations, `n_free=19`, `n_points_fitted=2237`,
reduced χ² 3.8776, Rwp 5.294 %, under a second, with DIFC 4677.88. That is the source project's minimum (reduced χ²
3.8776, Rwp 5.294 %); FullProf's fit of the same model prints χ² 3.88 and Rwp 5.29.
