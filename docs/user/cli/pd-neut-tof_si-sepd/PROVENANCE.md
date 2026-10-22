# pd-neut-tof_si-sepd — provenance

Silicon on SEPD (Argonne), one time-of-flight bank, Jorgensen–Von Dreele profile. The example catalogue's Si SEPD case,
started the way a user's own measurement would be.

## Sources

- **Data:** the measured points of `pd-neut-tof_si-sepd_start-2` (diffraction-lib's dataset `meas-si-sepd`), read
  from that project's `_data` loop by `tools/cli_projects/catalogue_tof_cases.py`. No fitted value is copied.
- **Model:** diffraction-lib's Si SEPD tutorial (`docs/docs/tutorials/` at develop `cb2cda7b`) and the same edi
  project: Fd-3m (origin choice 2), Si on 8a, bank 2θ 144.845°, DIFC 7476.91 and DIFA −1.54 µs/Å² fixed, α₁ 0.5971
  fixed, cut-off 8.2 FWHM.

## The start

| parameter | start | why |
| --- | --- | --- |
| d-to-TOF zero | 0, free | the catalogue's zero-shift rule |
| σ₀, σ₁, γ₁, β₀, β₁ | 3, 30, 3, 0.04, 0.01, free | one significant figure of the tutorial's values |
| α₁ | 0.5971, fixed | the instrument's value, fixed in the source |
| cell a | 5.431, free | the tutorial's start |
| Si Biso | 0.5, free | the catalogue's displacement rule |
| scale | 600, free | one significant figure of the tutorial's start |
| background | 14 points, flat at the 10th percentile of the counts, free | the source's points |

23 parameters are free: the source project's free set.

## Left out

diffraction-lib estimates the background automatically and fits in four stages with the `bumps (lm)` minimizer; this
project fits everything at once with edi's own minimizer.

## Check run

`python -m edi fit <copy> --dry --report machine`: converged in 10 iterations, `n_free=23`, `n_points_fitted=5600`,
reduced χ² 3.6111, Rwp 6.941 %, under a second. That is the minimum `pd-neut-tof_si-sepd_start-2` and `start-5`
reach (reduced χ² 3.6111, Rwp 6.941 %).
