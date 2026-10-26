---
title: "Rietveld fit: Y₂O₃, SPODI"
description: >-
  Fit cubic Y₂O₃ to constant-wavelength neutron powder data from SPODI at FRM II, with anisotropic displacement tensors whose components the site symmetry ties together.
---

# Rietveld fit: Y₂O₃, SPODI

Fit cubic Y₂O₃ to constant-wavelength neutron powder data from SPODI at FRM II, with anisotropic displacement tensors whose components the site symmetry ties together.

The app lists it as **Y₂O₃ [Ia-3] · SPODI @ FRM II**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-cwl_y2o3-spodi/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-cwl_y2o3-spodi](../../tutorials/pd-neut-cwl_y2o3-spodi.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-cwl_y2o3-spodi/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. The β tensors start at the isotropic equivalent of Biso 0.5.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_y2o3-spodi/PROVENANCE.md).
