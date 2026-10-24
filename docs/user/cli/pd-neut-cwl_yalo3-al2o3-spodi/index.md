---
title: "Two-phase fit: YAlO₃ and Al₂O₃, SPODI"
description: >-
  Fit two phases, YAlO₃ and corundum Al₂O₃, in one constant-wavelength neutron pattern from SPODI at FRM II, measured at 3 K, with a shared Bérar-Baldinozzi profile and cylinder absorption.
---

# Two-phase fit: YAlO₃ and Al₂O₃, SPODI

Fit two phases, YAlO₃ and corundum Al₂O₃, in one constant-wavelength neutron pattern from SPODI at FRM II, measured at 3 K, with a shared Bérar-Baldinozzi profile and cylinder absorption.

The app lists it as **YAlO₃ [Pbnm] / Al₂O₃ [R-3c] · SPODI @ FRM II**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-cwl_yalo3-al2o3-spodi/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-cwl_yalo3-al2o3-spodi](../../tutorials/pd-neut-cwl_yalo3-al2o3-spodi.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-cwl_yalo3-al2o3-spodi/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_yalo3-al2o3-spodi/PROVENANCE.md).
