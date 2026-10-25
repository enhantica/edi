---
title: Taurine on SENJU, scale against FullProf
description: >-
  Taurine on SENJU (J-PARC, time-of-flight neutron single-crystal diffraction): the 171 reflections FullProf fits (of 286), each with its own wavelength, isotropic displacements, no extinction. The structure is the one FullProf computes, and only the scale is free.
---

# Taurine on SENJU, scale against FullProf

Taurine on SENJU (J-PARC, time-of-flight neutron single-crystal diffraction): the 171 reflections FullProf fits (of 286), each with its own wavelength, isotropic displacements, no extinction. The structure is the one FullProf computes, and **only the scale is free**.

It is the CLI counterpart of diffraction-lib's `sc-neut-tof_taurine_basic` verification page: where the page compares calculated F² with FullProf's, this project fits the measured reflections FullProf computes.

## Run it

```bash
python -m edi fit docs/user/cli/sc-neut-tof_taurine-unknown_basic/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What is checked

`expected.json` holds FullProf's own fit of the same free parameters on the same reflections: the
number of reflections, the fitted scale within FullProf's uncertainty and the reduced chi-square
within 0.2 %. CI and `pixi run verify` run this project through `python -m edi` on every pull
request (`tools/checks/cli_projects.py`); `PROVENANCE.md` names each value's source.
