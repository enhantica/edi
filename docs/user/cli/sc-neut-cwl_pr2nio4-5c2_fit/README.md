---
title: Pr2NiO4 on 5C2, fitted from a rough start
description: >-
  Pr2NiO4 on 5C2 (LLB, constant wavelength), starting from isotropic displacements of 0.5 on every atom, displaced coordinates and a rough scale. Isotropic displacements cannot describe this structure well, so the fit ends near a reduced chi-square of 300.
---

# Pr2NiO4 on 5C2, fitted from a rough start

Pr2NiO4 on 5C2 (LLB, constant wavelength), starting from isotropic displacements of 0.5 on every atom, displaced coordinates and a rough scale. Isotropic displacements cannot describe this structure well, so the fit ends near a reduced chi-square of 300.

## Run it

```bash
python -m edi fit docs/user/cli/sc-neut-cwl_pr2nio4-5c2_fit/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What it is for

A fitting exercise that the app also offers as an example. It is registered but not executing:
it has no reference values, only the starting point.
