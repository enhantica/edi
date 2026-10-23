---
title: 11B LaB6 on ECHIDNA, TCH x FCJ
description: >-
  The owner's 11B-enriched LaB6 refinement against ECHIDNA (ANSTO) constant-wavelength neutron powder data: the Thompson-Cox-Hastings pseudo-Voigt with Finger-Cox-Jephcoat axial divergence (S/L = D/L = 0.08, fixed), Hewat cylinder absorption (μR = 0.7, fixed) and FullProf's polynomial background — 17 parameters: the zero, the sample displacement and transparency shifts, the wavelength, U, V, W, Y, the B coordinate, two isotropic ADPs, the scale and five background coefficients.
---

# 11B LaB6 on ECHIDNA, TCH x FCJ

The owner's 11B-enriched LaB6 refinement against ECHIDNA (ANSTO) constant-wavelength neutron powder data: the Thompson-Cox-Hastings pseudo-Voigt with Finger-Cox-Jephcoat axial divergence (S/L = D/L = 0.08, fixed), Hewat cylinder absorption (μR = 0.7, fixed) and FullProf's polynomial background — 17 parameters: the zero, the sample displacement and transparency shifts, the wavelength, U, V, W, Y, the B coordinate, two isotropic ADPs, the scale and five background coefficients.

The background is `_background.type polynomial` (origin 80°); the structure declares FullProf's two scattering lengths, La 8.24 fm and 11B 6.65 fm. Every value starts at FullProf's converged state and FullProf's free set is free, so the fit
shows whether edi's minimum is FullProf's.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_lab6-11b-echidna_tch-fcj/project --dry
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
