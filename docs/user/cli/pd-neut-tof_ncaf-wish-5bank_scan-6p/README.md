---
title: Na2Ca3Al2F14 on WISH, a six-point series of five-bank joint fits
description: >-
  A sequential series of six points, each a joint fit of the five WISH banks of Na2Ca3Al2F14: one file per bank per point, the structure shared, each bank keeping its own scale, calibration and background.
---

# Na2Ca3Al2F14 on WISH, a six-point series of five-bank joint fits

A **series of joint fits**: six points, each with one file per WISH bank, and each point fitted jointly over the five
banks of Na<sub>2</sub>Ca<sub>3</sub>Al<sub>2</sub>F<sub>14</sub>. The structure is shared by the banks; each bank keeps
its own scale, calibration, peak shape and background. Each point starts from the previous point's values as they
were written to the results files.

The data are synthetic: each point is the project calculated at a slightly larger cell and slightly different bank
scales, with noise of the measured uncertainties added (`PROVENANCE.md`). The cell stays fixed, as in the source project, so
each bank's time-of-flight calibration takes up the expansion. `analysis/analysis.edi` declares the series:
the folder `data` and one file pattern per bank, the text the `*` matches naming the point.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_ncaf-wish-5bank_scan-6p/project --dry
```

`--dry` leaves the project unchanged; drop it to keep `analysis/results.csv` (one row per point) and
`analysis/results_experiments.csv` (one row per point and bank).

## What is checked

`expected.json` names each point's quantity as `results[<point>].<column>`, the `results.csv` row of that point. The
number of free parameters is FullProf's (`kind: reference`); each point's χ² and iteration count are regression pins
of this project's own fit. CI and `pixi run verify` run this project
through `python -m edi` on every pull request, and any value outside its tolerance fails the build
(`tools/checks/cli_projects.py`).
