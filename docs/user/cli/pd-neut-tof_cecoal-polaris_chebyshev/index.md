---
title: CeCoAl3 on POLARIS, Chebyshev background
description: >-
  CeCoAl3 against POLARIS (ISIS) time-of-flight neutron powder data with the Jorgensen-Von Dreele profile and FullProf's 24-term Chebyshev background: 32 parameters — the cell, eight coordinates, five isotropic ADPs, the Al3 occupancy, the Gaussian (σ₁) and Lorentzian (γ₁) widths, the TOF zero and quadratic terms, the absorption, the scale and twelve background coefficients.
---

# CeCoAl3 on POLARIS, Chebyshev background

CeCoAl3 against POLARIS (ISIS) time-of-flight neutron powder data with the Jorgensen-Von Dreele profile and FullProf's 24-term Chebyshev background: 32 parameters — the cell, eight coordinates, five isotropic ADPs, the Al3 occupancy, the Gaussian (σ₁) and Lorentzian (γ₁) widths, the TOF zero and quadratic terms, the absorption, the scale and twelve background coefficients.

The background is `_background.type chebyshev`: the sum of `_background.coef` times the Chebyshev polynomial of each row's `_background.order`, over the domain `_background.x_min`..`_background.x_max`. Every value starts at FullProf's converged state and FullProf's free set is free, so the fit shows whether
edi's minimum is FullProf's.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_cecoal-polaris_chebyshev/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What is checked

`expected.json` holds FullProf's refined value of every parameter FullProf reports a standard
uncertainty for — the profile, calibration, scale, structure and every background coefficient — as
an **independent reference** with a tolerance of four of FullProf's standard uncertainties, and
FullProf's free-parameter count. The iteration count, reduced chi-square and Rwp are **regression
pins** from edi. CI and `pixi run verify` run this project through `python -m edi` on every pull
request, and any value outside its tolerance fails the build (`tools/checks/cli_projects.py`).
`PROVENANCE.md` names every source.
