---
title: Tb2Ti2O7 on HEiDi, reflections excluded by indices and by d
description: >-
  Tb2Ti2O7 on HEiDi (MLZ, constant wavelength): the 220 reflections of the scale-only project, two left out by their
  indices and eight by a d range, absences excluded, no merging. Only the scale is free.
---

# Tb2Ti2O7 on HEiDi, reflections excluded by indices and by d

The 220 reflections of `sc-neut-cwl_tb2ti2o7-heidi_basic`, with the experiment declaring which of them the fit uses:

- `_excluded_reflection` lists (1 1 1) and (4 0 0);
- `_excluded_region` leaves out d from 0.85 to 0.90 Å (`_excluded_region.axis d_spacing`);
- `_reflns.merge none` keeps every reflection its own observation, and `_reflns.absences exclude` leaves out any
  systematic absence (this list has none).

Only the scale is free.

## Run it

```bash
python -m edi fit docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_exclusions/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back, with each reflection's
`_refln.include_status` and the counts.

## What is checked

`expected.json` holds the number of free parameters and the number of reflections the fit uses, both counted by hand
from the project's files (`PROVENANCE.md`). CI and `pixi run verify` run this project through `python -m edi`
(`tools/checks/cli_projects.py`).
