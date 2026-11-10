---
title: "Sequential magnetic fit: Co₂SiO₄, D20 scan from 2.3 K"
description: >-
  A sequential fit of Co2SiO4 over 213 D20 patterns from 2.3 K to 497.4 K with the magnetic structure, fitted from the
  lowest temperature up, each fit starting from the previous one.
---

# Sequential magnetic fit: Co₂SiO₄, D20 scan from 2.3 K

A **sequential** fit of Co<sub>2</sub>SiO<sub>4</sub> over the whole cooling scan on D20: the 162 patterns of the
[162-file scan](../pd-neut-cwl_cosio-d20_scan-162f/README.md) and the 51 measured below 50 K, down to 2.3 K. The model is
the [2.3 K example](../pd-neut-cwl_cosio-d20_2k/index.md)'s, with the magnetic structure in Pnma.1, and the fit runs
from the lowest temperature up: the first file is the 2.3 K example's own fit, and each later one starts from the
previous result. The moments stay free at every temperature and fall towards zero as the temperature approaches the
Néel temperature, about 50 K.

The app lists it as **Co₂SiO₄ [Pnma.1] · D20 @ ILL**, with the sequential-fit and magnetic tags.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_scan-213f/project --dry`.
- **App:** open it from the Examples on the Home page; the Analysis page fits the scan file by file and follows it.
- **Python:** the [tutorial](../../tutorials/pd-neut-cwl_cosio-d20_scan-213f.ipynb).

`--dry` writes the results to a scratch directory and leaves the project unchanged; the scan data are read in place.
Drop it to keep `analysis/results.csv`. Press Ctrl+C once to stop cleanly after the current step: every finished file
stays in `analysis/results.csv`, and running the same command again resumes from the next file.

## What is checked

`expected.json` pins the number of free parameters and the terminal record of the scan (`PROVENANCE.md` says where
each comes from). The fit of 213 files takes a while, so the project is registered `offline: true` and runs only on
request: `python tools/checks/cli_projects.py --offline`.
