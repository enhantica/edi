---
title: "Rietveld fit: PbSO₄, laboratory X-ray"
description: >-
  Fit PbSO₄ to the Rietveld round robin's laboratory X-ray pattern, with the Cu Kα doublet and Bérar-Baldinozzi asymmetry.
---

# Rietveld fit: PbSO₄, laboratory X-ray

Fit PbSO₄ to the Rietveld round robin's laboratory X-ray pattern, with the Cu Kα doublet and Bérar-Baldinozzi asymmetry.

The app lists it as **PbSO₄ [Pnma] · Laboratory X-ray**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-xray-cwl_pbso4-lab/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-xray-cwl_pbso4-lab](../../tutorials/pd-xray-cwl_pbso4-lab.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-xray-cwl_pbso4-lab/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-xray-cwl_pbso4-lab/PROVENANCE.md).
