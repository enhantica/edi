---
title: Diamond on DREAM, scale against FullProf
description: >-
  Diamond against McStas-simulated reduced time-of-flight data from DREAM (ESS), with the Jorgensen profile on a 90° bank. The model is exactly the one FullProf fitted — profile, calibration, structure and its linear-interpolation background — and only the scale is free.
---

# Diamond on DREAM, scale against FullProf

Diamond against McStas-simulated reduced time-of-flight data from DREAM (ESS), with the Jorgensen profile on a 90° bank. The model is exactly the one FullProf fitted — profile, calibration, structure and its linear-interpolation background — and **only the scale is free**.

It is the CLI counterpart of the [`pd-neut-tof_diamond_dream`](../../../dev/verification/pd-neut-tof_diamond_dream.ipynb) verification page: where the page compares calculated patterns, this project fits FullProf's own data and checks the fitted scale lands on FullProf's.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_diamond-dream_basic/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is checked

`expected.json` holds two FullProf references — the number of fitted points (1948) and the fitted scale, within FullProf's own uncertainty — and labelled regression pins for the iterations, reduced χ² and Rwp. CI and `pixi run verify` run this project through `python -m edi` on every pull
request, and any value outside its tolerance fails the build
(`tools/checks/cli_projects.py`).
