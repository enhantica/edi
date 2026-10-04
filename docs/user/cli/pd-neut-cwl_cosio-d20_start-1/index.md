---
title: Co2SiO4 on D20, start-1
description: >-
  Co2SiO4 (olivine, P n m a) against D20 (ILL) constant-wavelength neutron powder data: a single-experiment Rietveld fit of 43 parameters — the three cell edges, atomic positions, isotropic ADPs and three site occupancies, the pseudo-Voigt profile (U, V, W, Y), the 2θ offset, the scale and 14 background points.
---

# Co2SiO4 on D20, start-1

Co<sub>2</sub>SiO<sub>4</sub> (olivine, *P n m a*) against D20 (ILL) constant-wavelength neutron powder data: a single-experiment Rietveld fit of 43 parameters — the three cell edges, atomic positions, isotropic ADPs and three site occupancies, the pseudo-Voigt profile (U, V, W, Y), the 2θ offset, the scale and 14 background points.

The start is **start-1** — rung 1 of the graded starting points recorded for the fitting corpus (1 is the farthest from the solution); the sibling project [`pd-neut-cwl_cosio-d20_start-4`](../pd-neut-cwl_cosio-d20_start-4/index.md) fits the same model from a
different start, so the pair exercises the descent from two different distances to the minimum.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is checked

`expected.json` pins the result of each listed descent strategy (its `variants`): the runner fits a copy of the project once per variant, declaring that descent as `_minimizer.descent` in the copy's `analysis/analysis.edi`, and compares every quantity. CI and `pixi run verify` run this project through `python -m edi` on every pull
request, and any value outside its tolerance fails the build
(`tools/checks/cli_projects.py`).
