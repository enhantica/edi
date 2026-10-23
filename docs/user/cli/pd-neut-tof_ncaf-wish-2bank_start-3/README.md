---
title: Na2Ca3Al2F14 on WISH, two banks, start-3
description: >-
  A joint fit of Na2Ca3Al2F14 against two WISH (ISIS) time-of-flight banks (4/7 and 5/6) with the Jorgensen profile: 20 parameters — six isotropic ADPs shared by both banks, and per bank the rise (α₁), decay (β₀, β₁) and Gaussian (σ₂) terms, the d-to-TOF offset and linear calibration, and the scale.
---

# Na2Ca3Al2F14 on WISH, two banks, start-3

A **joint** fit of Na<sub>2</sub>Ca<sub>3</sub>Al<sub>2</sub>F<sub>14</sub> against two WISH (ISIS) time-of-flight banks (4/7 and 5/6) with the Jorgensen profile: 20 parameters — six isotropic ADPs shared by both banks, and per bank the rise (α₁), decay (β₀, β₁) and Gaussian (σ₂) terms, the d-to-TOF offset and linear calibration, and the scale.

The start is **start-3** — rung 3 of the graded starting points recorded for the fitting corpus (1 is the farthest
from the solution).

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is checked

`expected.json` pins the result of each listed descent strategy (its `variants`): the runner fits a copy of the project once per variant, declaring that descent as `_minimizer.descent` in the copy's `analysis/analysis.edi`, and compares every quantity.

The project declares `_minimizer.chi_square_tolerance 1e-4` in its `analysis/analysis.edi` — the
tolerance crysta pinned these values under. CI and `pixi run verify` run this project through
`python -m edi` on every pull request, and any value outside its tolerance fails the build
(`tools/checks/cli_projects.py`).
