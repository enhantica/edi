---
title: Si on SEPD, start-2
description: >-
  Si against SEPD (Argonne) time-of-flight neutron powder data with the Jorgensen-Von Dreele profile: 23 parameters — the cell edge, the isotropic ADP, the exponential decay (β₀, β₁), Gaussian (σ₀, σ₁) and Lorentzian (γ₁) widths, the TOF zero offset, the scale and 14 background points.
---

# Si on SEPD, start-2

Si against SEPD (Argonne) time-of-flight neutron powder data with the Jorgensen-Von Dreele profile: 23 parameters — the cell edge, the isotropic ADP, the exponential decay (β₀, β₁), Gaussian (σ₀, σ₁) and Lorentzian (γ₁) widths, the TOF zero offset, the scale and 14 background points.

The start is **start-2** — rung 2 of the graded starting points recorded for the fitting corpus (1 is the farthest from the solution); the sibling project [`pd-neut-tof_si-sepd_start-5`](../pd-neut-tof_si-sepd_start-5/index.md) fits the same model from a
different start, so the pair exercises the descent from two different distances to the minimum.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_si-sepd_start-2/project --dry
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
