---
title: Tb2Ti2O7 on HEiDi, fitted from a rough start
description: >-
  Tb2Ti2O7 on HEiDi (MLZ, constant wavelength), starting from small anisotropic displacements (Uani), a displaced O1 coordinate and a rough scale. Its extinction is isotropic Becker-Coppens, mixed: the crystal radius is fixed at 0.025 mm, and the domain radius (from 25 um) and the mosaic spread (from 0) are free.
---

# Tb2Ti2O7 on HEiDi, fitted from a rough start

Tb2Ti2O7 on HEiDi (MLZ, constant wavelength), starting from small anisotropic displacements (Uani), a displaced O1 coordinate and a rough scale. Its extinction is isotropic Becker-Coppens, mixed: the crystal radius is fixed at 0.025 mm, and the domain radius (from 25 um) and the mosaic spread (from 0) are free.

## Run it

```bash
python -m edi fit docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_fit/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What it is for

A fitting exercise that the app also offers as an example. It is registered but not executing:
it has no reference values, only the starting point.
