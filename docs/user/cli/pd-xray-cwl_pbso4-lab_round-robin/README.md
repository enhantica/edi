---
title: PbSO4 X-ray round robin with the Kα doublet and Bérar-Baldinozzi asymmetry
description: >-
  PbSO4 (anglesite) from the X-ray Rietveld refinement round robin, Cu K-alpha doublet with monochromator polarization, with the pseudo-Voigt and Bérar-Baldinozzi asymmetry, its widths, mixing, asymmetry and scale fitted to the data.
---

# PbSO4 X-ray round robin with the Kα doublet and Bérar-Baldinozzi asymmetry

PbSO4 (anglesite), the laboratory X-ray data of the Rietveld refinement round robin (R. J. Hill, J. Appl. Cryst. 25, 589 (1992)), measured with the Cu Kα doublet and a monochromator. The model is FullProf's reference with the pseudo-Voigt (`cwl-pseudo-voigt-berar-baldinozzi`, FullProf's Npr 5) in place of FullProf's TCH pseudo-Voigt, which edi does not pair with Bérar-Baldinozzi. Its widths, mixing, four asymmetry coefficients and scale are free: **10 parameters**.

It is the CLI counterpart of the [`pd-xray-cwl_PbSO4_round-robin`](../../../dev/verification/pd-xray-cwl_PbSO4_round-robin.ipynb) verification page, which fits the same profile to FullProf's calculated pattern.

## Run it

```bash
python -m edi fit docs/user/cli/pd-xray-cwl_pbso4-lab_round-robin/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is checked

`expected.json` holds the point count FullProf fits and the size of the free set (references), and labelled regression pins of the fit's iteration count, reduced chi-square and Rwp. CI and `pixi run verify` run this project through `python -m edi` on every pull request, and any value outside its tolerance fails the build (`tools/checks/cli_projects.py`).
