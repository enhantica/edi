---
title: "Joint fit: PbSO₄, neutron and X-ray"
description: >-
  Fit PbSO₄ to two patterns at once, the Rietveld round robin's neutron pattern from D1A at ILL and its laboratory X-ray pattern: one structure, two experiments.
---

# Joint fit: PbSO₄, neutron and X-ray

Fit PbSO₄ to two patterns at once, the Rietveld round robin's neutron pattern from D1A at ILL and its laboratory X-ray pattern: one structure, two experiments.

The app lists it as **PbSO₄ [Pnma] · D1A @ ILL and laboratory X-ray**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-xray-cwl_pbso4-d1a-lab/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-xray-cwl_pbso4-d1a-lab](../../tutorials/pd-neut-xray-cwl_pbso4-d1a-lab.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-xray-cwl_pbso4-d1a-lab/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-xray-cwl_pbso4-d1a-lab/PROVENANCE.md).
