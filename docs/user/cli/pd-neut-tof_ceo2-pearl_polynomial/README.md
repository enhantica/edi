---
title: CeO2 on PEARL, polynomial background
description: >-
  CeO2 (NBS SRM 674a) against PEARL (ISIS) time-of-flight neutron powder data with the Jorgensen-Von Dreele profile and FullProf's six-term polynomial background: 19 parameters — the TOF calibration, the exponential rise and decay (α₁, β₀, β₁), the Gaussian (σ₁, σ₂) and Lorentzian (γ₁) widths, the absorption, two isotropic ADPs, the scale and six background coefficients.
---

# CeO2 on PEARL, polynomial background

CeO2 (NBS SRM 674a) against PEARL (ISIS) time-of-flight neutron powder data with the Jorgensen-Von Dreele profile and FullProf's six-term polynomial background: 19 parameters — the TOF calibration, the exponential rise and decay (α₁, β₀, β₁), the Gaussian (σ₁, σ₂) and Lorentzian (γ₁) widths, the absorption, two isotropic ADPs, the scale and six background coefficients.

The background is `_background.type polynomial`: the sum of `_background.coef` times (x / `_background.origin` − 1) to the power of each row's `_background.order`. Every value starts at FullProf's converged state and FullProf's free set is free, so the fit shows whether
edi's minimum is FullProf's.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_ceo2-pearl_polynomial/project --dry
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
