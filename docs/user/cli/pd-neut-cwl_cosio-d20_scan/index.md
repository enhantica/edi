---
title: "Sequential fit: Co₂SiO₄, D20 temperature scan"
description: >-
  Fit Co₂SiO₄ to a cooling scan from D20 at ILL, 155 patterns from 497.4 to 52.3 K, one after another: each fit starts from the previous one's result. The magnetic frames at the lowest temperatures are left out.
---

# Sequential fit: Co₂SiO₄, D20 temperature scan

Fit Co₂SiO₄ to a cooling scan from D20 at ILL, 155 patterns from 497.4 to 52.3 K, one after another: each fit starts from the previous one's result. The magnetic frames at the lowest temperatures are left out.

The app lists it as **Co₂SiO₄ [Pnma] · D20 @ ILL**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_scan/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-cwl_cosio-d20_scan](../../tutorials/pd-neut-cwl_cosio-d20_scan.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-cwl_cosio-d20_scan/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. Only the template pattern starts this way; each later pattern starts from the fit before it.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_cosio-d20_scan/PROVENANCE.md).
