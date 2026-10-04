---
title: Na2Ca3Al2F14 on WISH, five banks, FullProf free set
description: >-
  A joint fit of Na2Ca3Al2F14 against all five WISH (ISIS) time-of-flight banks with the Jorgensen-Von Dreele profile, using the free parameters and excluded regions of the original FullProf refinement: 193 parameters.
---

# Na2Ca3Al2F14 on WISH, five banks, FullProf free set

A **joint** fit of Na<sub>2</sub>Ca<sub>3</sub>Al<sub>2</sub>F<sub>14</sub> against all five WISH (ISIS) time-of-flight banks (1/10, 2/9, 3/8, 4/7 and 5/6) with the Jorgensen-Von Dreele profile. It fits the same 193 parameters as the original FullProf refinement, with the same excluded regions: atomic positions and isotropic ADPs, and per bank the peak-shape, calibration, absorption and scale terms plus the background.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back.

## What is checked

`expected.json` compares the fitted positions and isotropic ADPs, and the number of free parameters, with the FullProf refinement (`kind: reference`, each within FullProf's own uncertainty), and pins edi's convergence facts (`kind: regression-pin`). CI and `pixi run verify` run this project through `python -m edi` on every pull request, and any value outside its tolerance fails the build (`tools/checks/cli_projects.py`). The source of every value is in `PROVENANCE.md`.
