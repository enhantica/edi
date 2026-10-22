---
title: Pr2NiO4 single crystal, scale against FullProf
description: >-
  Pr2NiO4 measured on a constant-wavelength neutron single-crystal diffractometer: 198 reflections, anisotropic displacements, no extinction. The structure is the one FullProf computes, and only the scale is free.
---

# Pr2NiO4 single crystal, scale against FullProf

Pr2NiO4 measured on a constant-wavelength neutron single-crystal diffractometer: 198 reflections, anisotropic displacements, no extinction. The structure is the one FullProf computes, and **only the scale is free**.

It is the CLI counterpart of diffraction-lib's `sc-neut-cwl_Pr2NiO4_basic` verification page: where the page compares calculated F² with FullProf's, this project fits the measured reflections FullProf computes.

## Run it

```bash
python -m edi fit docs/user/cli/sc-neut-cwl_pr2nio4_basic/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What is checked

**Registered, not executing yet.** It joins the executing set once its `expected.json` holds the
values FullProf reaches when it fits the same parameters on the same reflections.
