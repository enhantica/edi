# pd-neut-tof_ncaf-wish — provenance

Na₂Ca₃Al₂F₁₄ on WISH (ISIS): all five detector bank pairs (1/10, 2/9, 3/8, 4/7, 5/6) fitted jointly, Jorgensen–Von
Dreele profile, each bank with its own zero, DIFC, profile, absorption, scale and background. The example
catalogue's NCAF case, started the way a user's own measurement would be.

## Sources

- **Data, excluded regions, background positions and free set:** `pd-neut-tof_ncaf-wish-5bank_start-5`, whose free
  set is FullProf's (193 parameters, that project's `PROVENANCE.md`). The points are read from its `_data` loops by
  `tools/cli_projects/catalogue_tof_cases.py`; no fitted value is copied. Banks 4+7 and 5+6 are the 4043 and 4114
  included points of diffraction-lib's datasets `meas-ncaf-wish-b47` and `meas-ncaf-wish-b56` (`data/measured/` in
  `easyscience/diffraction` at commit `3ec801667904578ea39f1a4f4aa941866543a669`, sha256
  `e24493511795e5dc3390ad055ea43d346ef39c63dab68349a9deba00dfde2671` and
  `bcbb403374e705e2864d48b2dc803778252da9320ac5dc33bce4e94a225ef9dc`), licence BSD-3-Clause. Banks 1+10, 2+9 and
  3+8 are WISH (ISIS) measurements from that project's FullProf five-bank input; licence not recorded.
- **Model:** the same project and diffraction-lib's NCAF WISH tutorial (`docs/docs/tutorials/` at develop
  `cb2cda7b`), which fits two of the five banks only to keep its run short. I2₁3, cell 10.250256 Å fixed (each
  bank's DIFC is free), cut-off 8 FWHM, joint weights 1.

## The start

| parameter | start | why |
| --- | --- | --- |
| zero, per bank | 0, free | the catalogue's zero-shift rule |
| DIFC, per bank | 20772.9, 18660.1, 15105.5, 10389.9, 4985.32 (banks 5/6 to 1/10), free | the nominal values the source declares (its FullProf input); diffraction-lib names 20773.0 and 18660.0 for the first two |
| DIFA, 2θ | the source's values, fixed | instrument calibration |
| profile terms the source frees | the fitted values moved so the peaks start about 30 % narrower, to two significant figures: Gaussian variance terms (σ₁, σ₂) × 0.49, the Lorentzian γ₁ × 0.6, the rise α₀, α₁ × 1.3, the decay β₀, β₁ × 1.15; free | the owner's start for this case (2026-10-22): narrower, differently shaped peaks |
| profile terms the source fixes | the source's values, fixed | the instrument's resolution |
| ABSCOR1 | 0, free on banks 2/9 to 5/6, fixed on 1/10 | as the source |
| positions | the source's rounded to two decimals, free | the coordinate rule |
| Biso | 0.5 on every site, free | the displacement rule |
| scale | 40 per bank, free | one significant figure |
| background | the source's points, flat at the 10th percentile of each bank's fitted counts | the background rule; points the source fixes stay fixed |

193 parameters are free. The source has no displacement constraint (every Biso is free in FullProf), so none is added.

## Left out

diffraction-lib fits two banks; its start places every atom and Biso near the answer.

## Check run

`python -m edi fit <copy> --dry --report machine`: converged in 15 iterations, `n_free=193`, `n_points_fitted=18973`,
reduced χ² 9.4978, Rwp 7.695 % (banks 1/10 to 5/6: 4.66, 6.44, 7.89, 8.10, 8.28 %), about 5 s. The source project
reaches reduced χ² 9.4975 and Rwp 7.694 % from its own start; FullProf's global χ² for the same five banks is 9.96.
Each of the 16 independent positions and Biso values lies within 0.05 of its FullProf standard uncertainty of
FullProf's value.
