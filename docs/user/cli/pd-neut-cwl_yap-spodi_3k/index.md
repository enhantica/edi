---
title: YAlO3 and Al2O3 on SPODI, two phases
description: >-
  YAlO3 and corundum Al2O3 in one SPODI (FRM II) constant-wavelength neutron pattern, fitted as two phases with the
  pseudo-Voigt and Bérar-Baldinozzi asymmetry, from the owner's FullProf project.
---

# YAlO3 and Al2O3 on SPODI, two phases

YAlO3 (`P b n m`) and corundum Al2O3 (`R -3 c`) in one SPODI (FRM II) constant-wavelength neutron pattern, fitted as
two phases. Both share one profile, the pseudo-Voigt with Bérar-Baldinozzi asymmetry (FullProf's Npr 5), with the
cylinder absorption of the owner's FullProf project.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_yap-spodi_3k/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back.

## What is checked

The starting values are those of the owner's FullProf project ([PROVENANCE.md](PROVENANCE.md)). CI and
`pixi run verify` run this project through `python -m edi` (`tools/checks/cli_projects.py`) and check its number of
free parameters, fitted points and Rwp against FullProf's, and its reduced chi-square and iteration count against
regression pins. The [`pd-neut-cwl_YAP_multiphase`](../../../dev/verification/pd-neut-cwl_YAP_multiphase.ipynb)
verification page compares the calculated pattern with FullProf's at FullProf's parameters.
