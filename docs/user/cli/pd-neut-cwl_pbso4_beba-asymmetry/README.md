---
title: PbSO4 on D1A with the pseudo-Voigt and Bérar-Baldinozzi asymmetry
description: >-
  PbSO4 on D1A (ILL, constant wavelength), the Rietveld round-robin data, with the pseudo-Voigt and Bérar-Baldinozzi asymmetry, its widths, mixing, asymmetry and scale fitted to the data.
---

# PbSO4 on D1A with the pseudo-Voigt and Bérar-Baldinozzi asymmetry

PbSO4 on D1A (ILL, constant wavelength), the Rietveld round-robin data, with the pseudo-Voigt (`cwl-pseudo-voigt-berar-baldinozzi`, FullProf's Npr 5) and Bérar-Baldinozzi asymmetry. Its widths, mixing, four asymmetry coefficients and scale are free: **10 parameters**.

**The model changed on 2026-10-05.** Until then this project carried FullProf's own model, the TCH pseudo-Voigt with Bérar-Baldinozzi asymmetry, with only the scale free and that scale checked against FullProf's. That profile pair is no longer in edi, so the project was re-fitted on the pseudo-Voigt, starting from FullProf's Gaussian widths and its asymmetry coefficients carried to the paper's convention. The fit reaches Rwp 3.63 % and reduced χ² 3.48, where the old model's scale-only fit gave 3.66 % and 3.53.

It is the CLI counterpart of the [`pd-neut-cwl_PbSO4_beba-asymmetry`](../../../dev/verification/pd-neut-cwl_PbSO4_beba-asymmetry.ipynb) verification page, which fits the same profile to FullProf's calculated pattern.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_pbso4_beba-asymmetry/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is checked

**Registered, not executing**. CI and `pixi run verify` neither run this project nor check its
`expected.json`.

`expected.json` holds the point count FullProf fits (a reference) and labelled regression pins of
this fit; `PROVENANCE.md` names each.
