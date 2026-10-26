---
title: Y2O3 with anisotropic beta ADPs, scale against FullProf
description: >-
  Y2O3 in I a -3 with every site's displacement given as FullProf's dimensionless beta tensor, constant-wavelength neutrons. The model is FullProf's own, its tensors tied by each site's symmetry, and only the scale is free.
---

# Y2O3 with anisotropic beta ADPs, scale against FullProf

Y2O3 in `I a -3` with constant-wavelength neutrons. Every site's displacement is FullProf's dimensionless **beta tensor** (`adp_type beta`), and each site's symmetry ties its components: Y1 on `24d` keeps four free (beta12 = beta13 = 0), Y2 on `8b` two (the 3-fold ties the rest), O1 on `48e` all six. The model is exactly the one FullProf calculates — profile, calibration, structure and its linear-interpolation background — and **only the scale is free**.

It is the CLI counterpart of the [`pd-neut-cwl_Y2O3_beta-adp`](../../../dev/verification/pd-neut-cwl_Y2O3_beta-adp.ipynb) verification page: where the page compares calculated patterns, this project fits FullProf's data and checks the fitted scale lands on FullProf's.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_y2o3_beta-adp/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is checked

`expected.json` holds two FullProf references — the number of fitted points (2509) and the fitted scale, within FullProf's own uncertainty — and labelled regression pins for the iterations, reduced χ² and Rwp. CI and `pixi run verify` run this project through `python -m edi` on every pull
request, and any value outside its tolerance fails the build
(`tools/checks/cli_projects.py`).
