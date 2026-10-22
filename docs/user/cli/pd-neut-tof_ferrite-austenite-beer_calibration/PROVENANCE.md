# pd-neut-tof_ferrite-austenite-beer_calibration — provenance

Ferrite and austenite (duplex steel) on two BEER (ESS) time-of-flight banks, S2 and N2, McStas-simulated, fitted
jointly with a pseudo-Voigt profile. An instrument calibration: both phases' cells are known and fixed, and each
bank's zero and resolution (σ₀, σ₁, σ₂, γ₀) are fitted. The example catalogue's BEER case, started the way a user's
own measurement would be.

## Sources

- **Data:** the two banks of `pd-neut-tof_ferrite-austenite-beer_joint` (diffraction-lib's dataset
  `meas-ferrite-austenite-beer`, files `Duplex_in_HR_for_IRF_S2.dat` and `_N2.dat`), read from that project's
  `_data` loops by `tools/cli_projects/catalogue_tof_cases.py`. No fitted value is copied.
- **What is calibrated and free:** diffraction-lib's BEER calibration tutorial (`docs/docs/tutorials/` at develop
  `cb2cda7b`): per bank the zero, σ₀, σ₁, σ₂ and γ₀; each phase's scale shared by the two banks; the displacement;
  the background. The cells (ferrite 2.886 Å, austenite 3.6468 Å) and each bank's DIFC and 2θ (from the data files'
  headers, as in the edi project) stay fixed.
- **Kept from the edi project:** one Biso shared by the two iron phases (`biso_austenite = biso_ferrite`, as FullProf
  ties them), its excluded regions, its 31 background positions per bank (the last fixed), joint weights 0.5.

## The start

| parameter | start | why |
| --- | --- | --- |
| zero, per bank | 0, free | the zero-shift rule |
| σ₀, σ₁, σ₂, γ₀, per bank | 900, 1000, 300, 5, free | one significant figure of the edi project's values |
| phase scales | ferrite 400, austenite 100, free on S2; N2's follow S2's | one significant figure; shared as in the tutorial |
| Biso | 0.5, free (ferrite), austenite tied to it | the displacement rule |
| background | 31 points per bank, flat at the 10th percentile of the fitted counts, the first 30 free | the background rule |

73 parameters are free: per bank the zero, four profile terms and 30 background points; two scales; one Biso.

## Left out

diffraction-lib estimates the background automatically, frees and then fixes it, and fits each phase's Biso apart;
the edi project fits each bank's phase scales apart. The edi project's calculator choice (`cryspy`) is not carried:
edi computes with crysta.

## Check run

`python -m edi fit <copy> --dry --report machine`: converged in 6 iterations, `n_free=73`, `n_points_fitted=5642`,
reduced χ² 6.891, Rwp 7.131 % (S2 7.20 %, N2 7.06 %), under a second. The edi joint project, with each bank's scales
apart and FullProf's background, pins reduced χ² 6.925 and Rwp 7.147 %; FullProf prints Rwp 7.20 % (S2) and 7.06 %
(N2). The fitted zeros are −10.29 µs (S2) and −2.09 µs (N2), as in FullProf's fit.
