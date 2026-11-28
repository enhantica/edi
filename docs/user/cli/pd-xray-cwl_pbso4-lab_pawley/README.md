---
title: PbSO4 laboratory X-ray, Pawley
description: >-
  PbSO4 from the Rietveld round robin's laboratory X-ray pattern as a Pawley fit: a structure with only its cell and space group, one fitted intensity per reflection, and the cell, zero, peak profile, asymmetry and background.
---

# PbSO4 laboratory X-ray, Pawley

The laboratory X-ray pattern of [`pd-xray-cwl_pbso4-lab`](../pd-xray-cwl_pbso4-lab/index.md), fitted with a structure
that has only a cell and a space group, `P n m a`, and no atoms. Its calculation method is Pawley
(`_structure.calc_method pawley`): every reflection's intensity is a fitted parameter with its own s.u. The fit also
varies the cell, the 2θ zero, U, V, W, the mixing, two asymmetry terms and the six Chebyshev background terms.

This is how a Pawley fit is used before a structure is known: to check the cell and space group, and to extract
intensities for structure solution. The scale cannot be fitted under Pawley; it keeps the value of the Rietveld
project. See the [Rietveld, Le Bail and Pawley](../../guides/rietveld-le-bail-and-pawley.md) guide.

## Run it

```bash
python -m edi fit docs/user/cli/pd-xray-cwl_pbso4-lab_pawley/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values and the extracted intensities back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What is checked

FullProf has no Pawley mode, so `expected.json` takes FullProf's Le Bail fit of the same start (`Jbt=2`) as its
reference: the number of fitted points, R<sub>wp</sub> within 10 % and the three cell lengths. The sources are in
`PROVENANCE.md`.
