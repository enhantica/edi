---
title: Tb2Ti2O7 on HEiDi with extinction, scale and crystal radius
description: >-
  Tb2Ti2O7 on HEiDi (MLZ, constant wavelength) with Becker-Coppens isotropic extinction (Gaussian mosaic spread, mosaicity 35000). The scale and the crystal radius are free. FullProf uses its own extinction model, so, as on diffraction-lib's page, the two agree only roughly.
---

# Tb2Ti2O7 on HEiDi with extinction, scale and crystal radius

Tb2Ti2O7 on HEiDi (MLZ, constant wavelength) with Becker-Coppens isotropic extinction (Gaussian mosaic spread, mosaicity 35000). **The scale and the crystal radius are free.** FullProf uses its own extinction model, so, as on diffraction-lib's page, the two agree only roughly.

It is the CLI counterpart of diffraction-lib's `sc-neut-cwl_Tb2Ti2O7_isotropic-extinction` verification page: where the page compares calculated F² with FullProf's, this project fits the measured reflections FullProf computes.

## Run it

```bash
python -m edi fit docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What is checked

FullProf has no Becker-Coppens sphere model, so `expected.json` holds an independent
Becker-Coppens fit of the same scale and radius on the same reflections: the number of
reflections, the scale and radius each within one s.u. of that fit, and the reduced chi-square
within 0.2 %. CI and `pixi run verify` run this project through `python -m edi` on every pull
request (`tools/checks/cli_projects.py`); `PROVENANCE.md` names each value's source.
