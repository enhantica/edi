---
title: Taurine on SENJU, fitted from a rough start
description: >-
  Taurine on SENJU at J-PARC, by time-of-flight neutron single-crystal diffraction, starting from an isotropic displacement of 1.5 on every atom and a scale of 1.
---

# Taurine on SENJU, fitted from a rough start

Taurine on SENJU at J-PARC, by time-of-flight neutron single-crystal diffraction, starting from an isotropic displacement of 1.5 on every atom and a scale of 1.

## Run it

```bash
python -m edi fit docs/user/cli/sc-neut-tof_taurine_fit/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What it is for

A fitting exercise that the app also offers as an example. It is registered but not executing:
it has no reference values, only the starting point.
