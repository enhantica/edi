---
title: Co2SiO4 on D20, three-temperature sequential scan
description: >-
  A sequential fit of Co2SiO4 over three D20 patterns measured at 52.3 K, 299.4 K and 497.4 K: the same 39-parameter model (cell, positions, ADPs, pseudo-Voigt profile, 2θ offset, scale, background) is fitted file by file, each fit starting from the previous one.
---

# Co2SiO4 on D20, three-temperature sequential scan

A **sequential** fit of Co<sub>2</sub>SiO<sub>4</sub> over three D20 patterns measured at 52.3 K, 299.4 K and 497.4 K: the same 39-parameter model (cell, positions, ADPs, pseudo-Voigt profile, 2θ offset, scale, background) is fitted file by file, each fit starting from the previous one.

It exercises the scan fitting mode: the per-file results land in `analysis/results.csv`, one row per temperature. It also exercises the declared minimization conditions: `analysis/analysis.edi` sets `_minimizer.descent fast_descent` and `_minimizer.chi_square_tolerance 1e-4`, every file's fit runs under them, and `analysis/results-provenance.csv` records them row by row.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is checked

`expected.json` names each file's quantity as `results[<temperature>].<column>` — the `results.csv` row whose `diffrn.ambient_temperature` is that temperature. Its values are regression pins of this project's own fit under those conditions, and each file's iteration count is pinned too (`kind` recorded per value; `PROVENANCE.md` says where each came from). CI and `pixi run verify` run this project through `python -m edi` on every pull
request, and any value outside its tolerance fails the build
(`tools/checks/cli_projects.py`).
