---
title: LaB6 on Echidna with FCJ asymmetry, scale against FullProf
description: >-
  LaB6 on Echidna (ANSTO, constant wavelength) with the Thompson-Cox-Hastings pseudo-Voigt and Finger-Cox-Jephcoat axial-divergence asymmetry. The model is exactly the one FullProf computes, and only the scale is free.
---

# LaB6 on Echidna with FCJ asymmetry, scale against FullProf

LaB6 on Echidna (ANSTO, constant wavelength) with the Thompson-Cox-Hastings pseudo-Voigt and Finger-Cox-Jephcoat axial-divergence asymmetry. The model is exactly the one FullProf computes, and **only the scale is free**.

It is the CLI counterpart of the [`pd-neut-cwl_LaB6_fcj-asymmetry`](../../../dev/verification/pd-neut-cwl_LaB6_fcj-asymmetry.ipynb) verification page: where the page compares calculated patterns, this project fits FullProf's own data and checks the fitted scale lands on FullProf's.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_lab6-echidna_fcj-asymmetry/project --dry
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
