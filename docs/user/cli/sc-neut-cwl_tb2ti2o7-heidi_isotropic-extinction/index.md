---
title: Tb2Ti2O7 on HEiDi with extinction, scale and domain radius
description: >-
  Tb2Ti2O7 on HEiDi (MLZ, constant wavelength) with isotropic Becker-Coppens extinction, mixed (Gaussian mosaic distribution, mosaic spread 101811 rad⁻¹). The scale and the domain radius are free. FullProf uses its own extinction model, so, as on diffraction-lib's page, the two agree only roughly.
---

# Tb2Ti2O7 on HEiDi with extinction, scale and domain radius

Tb2Ti2O7 on HEiDi (MLZ, constant wavelength) with isotropic Becker-Coppens extinction, mixed (Gaussian mosaic distribution, mosaic spread 101811 rad⁻¹). **The scale and the domain radius are free**, and the crystal radius follows the domain radius (a constraint), as the single radius of diffraction-lib's page. FullProf uses its own extinction model, so, as on diffraction-lib's page, the two agree only roughly.

It is the CLI counterpart of diffraction-lib's `sc-neut-cwl_Tb2Ti2O7_isotropic-extinction` verification page: where the page compares calculated F² with FullProf's, this project fits the measured reflections FullProf computes.

## Run it

```bash
python -m edi fit docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What is checked

FullProf has no Becker-Coppens sphere model, so `expected.json` holds an independent
Becker-Coppens fit of the same scale and domain radius on the same reflections: the number of
reflections, the scale and domain radius each within one s.u. of that fit, and the reduced chi-square
within 0.2 %. CI and `pixi run verify` run this project through `python -m edi` on every pull
request (`tools/checks/cli_projects.py`); `PROVENANCE.md` names each value's source.
