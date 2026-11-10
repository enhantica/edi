---
title: "Single-crystal fit: Tb₂Ti₂O₇, HEiDi"
description: >-
  Fit the pyrochlore Tb₂Ti₂O₇ to constant-wavelength neutron single-crystal data from HEiDi at MLZ, with anisotropic displacements and Becker-Coppens extinction.
---

# Single-crystal fit: Tb₂Ti₂O₇, HEiDi

Fit the pyrochlore Tb₂Ti₂O₇ to constant-wavelength neutron single-crystal data from HEiDi at MLZ, with anisotropic displacements and Becker-Coppens extinction.

The app lists it as **Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [sc-neut-cwl_tb2ti2o7-heidi](../../tutorials/sc-neut-cwl_tb2ti2o7-heidi.ipynb) loads this project and works
  through it.

All three read the same files, in `docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi/project`.

## The start

The project starts from rough values: anisotropic displacements at a small isotropic-equivalent value, the free O1 x moved off its refined value, mixed Becker-Coppens extinction with a crystal radius of 3 mm and the domain radius (from 25 μm) and mosaic spread (from 0) free, and the scale to one significant figure.

## Sources

Where the data and the model come from, with the data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi/PROVENANCE.md).
