---
title: "Rietveld fit: CeCoAl₃, POLARIS"
description: >-
  Fit CeCoAl₃ to time-of-flight neutron powder data from POLARIS at ISIS: structure and profile, with a 24-term Chebyshev background.
---

# Rietveld fit: CeCoAl₃, POLARIS

Fit CeCoAl₃ to time-of-flight neutron powder data from POLARIS at ISIS: structure and profile, with a 24-term Chebyshev background.

The app lists it as **CeCoAl₃ [Pmma] · POLARIS @ ISIS**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-tof_cecoal-polaris/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-tof_cecoal-polaris](../../tutorials/pd-neut-tof_cecoal-polaris.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-tof_cecoal-polaris/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-tof_cecoal-polaris/PROVENANCE.md).
