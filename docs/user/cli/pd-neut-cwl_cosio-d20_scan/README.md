---
title: Co2SiO4 on D20, 155-file nuclear scan
description: >-
  A sequential fit of Co2SiO4 over 155 D20 patterns, cooling from 497.4 K to 52.3 K, with the nuclear model only: each fit starts from the previous one's result.
---

# Co2SiO4 on D20, 155-file nuclear scan

A **sequential** fit of Co<sub>2</sub>SiO<sub>4</sub> over 155 D20 patterns measured while cooling from 497.4 K to 52.3 K.
The magnetic frames at the lowest temperatures are left out, so the nuclear model fits every file. Each fit starts from
the previous one's result; only the template pattern starts from rounded values (zero shift 0, profile terms to one
significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background). The app's scan example is
now the [213-file magnetic scan](../pd-neut-cwl_cosio-d20_scan-213f/index.md), which runs down to 2.3 K.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_scan/project --dry
```

`--dry` writes the results to a scratch directory and leaves the project unchanged; drop it to keep
`analysis/results.csv`.

## What is checked

`expected.json` pins the template fit against FullProf's (`PROVENANCE.md` says where each value comes from).
