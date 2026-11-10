---
title: Fe on BEER with the TOF pseudo-Voigt, scale against FullProf
description: >-
  Ferrite on BEER (ESS, time of flight) with the non-convoluted pseudo-Voigt on a 90° bank. The model is exactly the one FullProf computes, and only the scale is free.
---

# Fe on BEER with the TOF pseudo-Voigt, scale against FullProf

Ferrite on BEER (ESS, time of flight) with the non-convoluted pseudo-Voigt on a 90° bank. The model is exactly the one FullProf computes, and **only the scale is free**.

It is the CLI counterpart of the [`pd-neut-tof_Fe_pseudo-voigt`](../../../dev/verification/pd-neut-tof_Fe_pseudo-voigt.ipynb) verification page: where the page compares calculated patterns, this project fits FullProf's own data and checks the fitted scale lands on FullProf's.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_fe_pseudo-voigt/project --dry
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
