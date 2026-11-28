---
title: La0.5Ba0.5CoO3 on HRPT, Le Bail
description: >-
  The La0.5Ba0.5CoO3 HRPT project with its structure switched to Le Bail: the cell, zero, peak profile and background are fitted, and the atoms stay in the structure for the switch back to Rietveld.
---

# La0.5Ba0.5CoO3 on HRPT, Le Bail

The [`pd-neut-cwl_lbco-hrpt`](../pd-neut-cwl_lbco-hrpt/index.md) project, unchanged except that its structure's
calculation method is Le Bail (`_structure.calc_method le_bail`). A Le Bail fit takes each reflection's intensity
from the measured pattern, so it varies only the cell, the 2θ zero, the profile (U, V, W, Y) and the five background
points: **11 parameters**.

The atom sites, their Biso values and the phase scale keep their free marks. The fit leaves them out, and they are
back when the structure is switched to Rietveld, which is the workflow this project shows: fit the cell and profile
with Le Bail, switch to Rietveld, and continue from there. See the
[Rietveld, Le Bail and Pawley](../../guides/rietveld-le-bail-and-pawley.md) guide.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_lbco-hrpt_le-bail/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values and the extracted intensities back. Add
`--report machine --verbosity full` for the versioned `key=value` record the checks read.

## What is checked

`expected.json` holds FullProf's Le Bail fit of the same start (`Jbt=2`) as references: the number of free
parameters, R<sub>wp</sub> within 5 % and the cell edge. The sources are in `PROVENANCE.md`.
