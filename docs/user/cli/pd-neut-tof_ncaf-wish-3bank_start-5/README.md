---
title: Na2Ca3Al2F14 on WISH, three banks, FullProf-verified
description: >-
  A joint fit of Na2Ca3Al2F14 against three WISH (ISIS) time-of-flight banks (2/9, 4/7 and 5/6) with the Jorgensen-Von Dreele profile: 108 parameters — atomic positions and isotropic ADPs, and per bank the peak-shape, calibration, absorption and scale terms plus the background.
---

# Na2Ca3Al2F14 on WISH, three banks, FullProf-verified

A **joint** fit of Na<sub>2</sub>Ca<sub>3</sub>Al<sub>2</sub>F<sub>14</sub> against three WISH (ISIS) time-of-flight banks (2/9, 4/7 and 5/6) with the Jorgensen-Von Dreele profile: 108 parameters — atomic positions and isotropic ADPs, and per bank the peak-shape, calibration, absorption and scale terms plus the background.

It is the largest project in the set and the one whose fitted positions and ADPs are compared with an independent FullProf fit of the same three banks.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_ncaf-wish-3bank_start-5/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is checked

`expected.json` pins the result of each listed descent strategy (its `variants`): the runner fits a copy of the project once per variant, declaring that descent as `_minimizer.descent` in the copy's `analysis/analysis.edi`, and compares every quantity. Its `param.*` values are FullProf references (`kind: reference`); the `edi` block re-pins the convergence facts of edi's default invocation, which the runner checks too. CI and `pixi run verify` run this project through `python -m edi` on every pull
request, and any value outside its tolerance fails the build
(`tools/checks/cli_projects.py`).
