---
title: Taurine on SENJU, six datasets fitted together
description: >-
  Taurine on SENJU at J-PARC, by time-of-flight neutron single-crystal diffraction: the six datasets of FullProf's taurine project, one experiment each with its own scale, fitted together from FullProf's positions and beta tensors, every one free, and FullProf's anisotropic Larson extinction (its model 4) with x11, x22 and x33 free and shared by the six datasets through constraints. As FullProf, the fit uses only reflections with F² > 3 su(F²).
---

# Taurine on SENJU, six datasets fitted together

Taurine on SENJU at J-PARC, by time-of-flight neutron single-crystal diffraction: the six datasets of FullProf's taurine project, one experiment each with its own scale, fitted together from FullProf's positions and beta tensors, every one free, and FullProf's anisotropic Larson extinction (its model 4) with x11, x22 and x33 free and shared by the six datasets through constraints. As FullProf, the fit uses only reflections with F² > 3 su(F²).

## Run it

```bash
python -m edi fit docs/user/cli/sc-neut-tof_taurine_fit/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What it is for

A fitting exercise that the app also offers as an example. It is registered but not executing:
it has no reference values, only the starting point.
