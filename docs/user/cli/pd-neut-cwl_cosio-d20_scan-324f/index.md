---
title: Co2SiO4 on D20, 324-file scan down and up
description: >-
  A sequential fit of Co2SiO4 over 324 D20 patterns, cooling from 497.4 K to 50.4 K and warming back over the same temperatures: the same 39-parameter model is fitted file by file, each fit starting from the previous successful one.
---

# Co2SiO4 on D20, 324-file scan down and up

A **sequential** fit of Co<sub>2</sub>SiO<sub>4</sub> over 324 D20 patterns: 162 measured cooling from 497.4 K to 50.4 K, then the same 162 temperatures warming back. The same 39-parameter model (cell, positions, ADPs, pseudo-Voigt profile, 2θ offset, scale, background) is fitted file by file, each fit starting from the previous successful one.

It is the regression case for a sequential scan that once followed a wrong minimum going down (a reflection at the 180° Bragg limit trapped the chain, fixed in crysta). Because the same files are fitted in both directions, the two halves of `analysis/results.csv` can be compared temperature by temperature.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project --dry
```

`--dry` writes the results to a scratch directory and leaves the project unchanged; the scan data are read in place, never copied. Drop it to keep `analysis/results.csv`. Press Ctrl+C once to stop cleanly after the current step (exit status 130): every finished file stays in `analysis/results.csv`, and running the same command again resumes from the next file. A second Ctrl+C exits at once.

## What is checked

`expected.json` pins the number of free parameters and the terminal record of the scan (`kind` recorded per value; `PROVENANCE.md` says where each came from). The fit takes about 30 s, too slow for CI, so the project is registered `offline: true` and runs only on request: `python tools/checks/cli_projects.py --offline` fits it through `python -m edi` and fails on any value outside its tolerance. CI and `pixi run verify` run the other projects.
