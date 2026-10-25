---
title: Co2SiO4 on D20, 162-file cooling scan
description: >-
  A sequential fit of Co2SiO4 over 162 D20 patterns, cooling from 497.4 K to 50.4 K: the same 39-parameter model fitted file by file, each fit starting from the previous successful one.
---

# Co2SiO4 on D20, 162-file cooling scan

A **sequential** fit of Co<sub>2</sub>SiO<sub>4</sub> over 162 D20 patterns measured while cooling from 497.4 K to
50.4 K: the first half of the [324-file scan](../pd-neut-cwl_cosio-d20_scan-324f/index.md). The same 39-parameter model
(cell, positions, ADPs, pseudo-Voigt profile, 2θ offset, scale, background) is fitted file by file, each fit starting
from the previous successful one. It is also an example in the desktop and web apps.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project --dry
```

`--dry` writes the results to a scratch directory and leaves the project unchanged; the scan data are read in place.
Drop it to keep `analysis/results.csv`. Press Ctrl+C once to stop cleanly after the current step: every finished file
stays in `analysis/results.csv`, and running the same command again resumes from the next file.

## What is checked

`expected.json` pins the number of free parameters (`PROVENANCE.md` says where it comes from; the terminal record of the
scan joins it once the scan has been run here). The fit takes several seconds, so the project is registered `offline: true`
and runs only on request: `python tools/checks/cli_projects.py --offline`.
