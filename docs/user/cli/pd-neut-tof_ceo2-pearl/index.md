---
title: "Calibration fit: CeO₂, PEARL"
description: >-
  Fit the CeO₂ standard to time-of-flight neutron powder data from PEARL at ISIS: the calibration and the profile, with a polynomial background.
---

# Calibration fit: CeO₂, PEARL

Fit the CeO₂ standard to time-of-flight neutron powder data from PEARL at ISIS: the calibration and the profile, with a polynomial background.

The app lists it as **CeO₂ [Fm-3m] · PEARL @ ISIS**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-tof_ceo2-pearl/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-tof_ceo2-pearl](../../tutorials/pd-neut-tof_ceo2-pearl.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-tof_ceo2-pearl/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. The cell is the standard's, fixed, so the fit calibrates the instrument against it.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-tof_ceo2-pearl/PROVENANCE.md).
