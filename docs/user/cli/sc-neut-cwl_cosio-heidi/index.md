---
title: "Single-crystal fit: Co₂SiO₄ at three temperatures, HEiDi"
description: >-
  Fit one Co₂SiO₄ crystal at 300 K, 55 K and 2.5 K, each temperature its own structure and dataset, fitted independently, with the cobalt magnetic moments at 2.5 K.
---

# Single-crystal fit: Co₂SiO₄ at three temperatures, HEiDi

Fit one Co₂SiO₄ crystal at 300 K, 55 K and 2.5 K, each temperature its own structure and dataset, fitted independently, with the cobalt magnetic moments at 2.5 K.

The app lists it as **Co₂SiO₄ [Pnma] at 300 K, 55 K and 2.5 K · HEiDi @ MLZ (FRM II)**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/sc-neut-cwl_cosio-heidi/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [sc-neut-cwl_cosio-heidi](../../tutorials/sc-neut-cwl_cosio-heidi.ipynb) loads this project and works
  through it.

All three read the same files, in `docs/user/cli/sc-neut-cwl_cosio-heidi/project`.

## The start

Each structure starts from its published positions with one small isotropic-equivalent value for every displacement
tensor, no extinction and a rough scale. At 2.5 K the cobalt moments start at zero. The 2.5 K uncertainties are
estimated from the 55 K data, as the provenance explains.

## Sources

Where the data and the model come from, with the data files' checksums:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/sc-neut-cwl_cosio-heidi/PROVENANCE.md).
