---
title: PbSO4 on D1A with Bérar-Baldinozzi asymmetry, scale against FullProf
description: >-
  PbSO4 on D1A (ILL, constant wavelength), the Rietveld round-robin data, with the pseudo-Voigt and Bérar-Baldinozzi asymmetry. The model is the one FullProf fitted, its asymmetry coefficients carried to the paper's convention, and only the scale is free.
---

# PbSO4 on D1A with Bérar-Baldinozzi asymmetry, scale against FullProf

PbSO4 on D1A (ILL, constant wavelength), the Rietveld round-robin data, with the pseudo-Voigt and Bérar-Baldinozzi asymmetry. The model is the one FullProf fitted, its asymmetry coefficients carried to the paper's convention, and **only the scale is free**.

It is the CLI counterpart of the [`pd-neut-cwl_PbSO4_beba-asymmetry`](../../../dev/verification/pd-neut-cwl_PbSO4_beba-asymmetry.ipynb) verification page: where the page compares calculated patterns, this project fits FullProf's own data and checks the fitted scale lands on FullProf's.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_pbso4_beba-asymmetry/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is checked

**Registered, not executing**. This project fits the scale alone against FullProf's verification
parameter set, so its fit is poor in both engines. CI and
`pixi run verify` neither run it nor check its `expected.json`. It becomes executing, with a fit of its
full `.pcr` parameter set, once every feature that fit needs exists.

`expected.json` holds the FullProf reference from a scale-only FullProf fit of the same model and data
(the scale, within FullProf's own uncertainty) and labelled regression pins; `PROVENANCE.md` names each.
