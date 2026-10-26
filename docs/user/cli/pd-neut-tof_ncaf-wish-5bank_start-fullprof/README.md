---
title: Na2Ca3Al2F14 on WISH, five banks, from FullProf's own start
description: >-
  The five-bank Na2Ca3Al2F14 WISH joint fit started at every value of the original FullProf refinement: the same 193 free parameters and excluded regions, beginning at FullProf's minimum.
---

# Na2Ca3Al2F14 on WISH, five banks, from FullProf's own start

The five-bank **joint** fit of Na<sub>2</sub>Ca<sub>3</sub>Al<sub>2</sub>F<sub>14</sub> against all five WISH (ISIS) time-of-flight banks, started at every value of the original FullProf refinement: atomic positions, isotropic ADPs, and per bank the peak-shape, calibration, absorption, scale and background values. The free set and the excluded regions are the same 193 parameters as FullProf's. The companion project `pd-neut-tof_ncaf-wish-5bank_start-5` starts away from this minimum and reaches the same one.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back.

## What is checked

`expected.json` compares the fitted positions and isotropic ADPs, and the number of free parameters, with the FullProf refinement (`kind: reference`, each within FullProf's own uncertainty), and pins edi's convergence facts (`kind: regression-pin`). CI and `pixi run verify` run this project through `python -m edi` on every pull request, and any value outside its tolerance fails the build (`tools/checks/cli_projects.py`). The source of every value is in `PROVENANCE.md`.
