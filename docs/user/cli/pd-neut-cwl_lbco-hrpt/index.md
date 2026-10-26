---
title: "Rietveld fit: La₀.₅Ba₀.₅CoO₃, HRPT"
description: >-
  Fit the cubic perovskite La₀.₅Ba₀.₅CoO₃ to constant-wavelength neutron powder data from HRPT at PSI. La and Ba share one site, and Ba's displacement follows La's.
---

# Rietveld fit: La₀.₅Ba₀.₅CoO₃, HRPT

Fit the cubic perovskite La₀.₅Ba₀.₅CoO₃ to constant-wavelength neutron powder data from HRPT at PSI. La and Ba share one site, and Ba's displacement follows La's.

The app lists it as **La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-cwl_lbco-hrpt/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-cwl_lbco-hrpt](../../tutorials/pd-neut-cwl_lbco-hrpt.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-cwl_lbco-hrpt/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. One exception: the 2θ zero starts at 0.3°. From 0 the low-angle peaks sit more than a peak width away and the fit settles in a wrong minimum; the case's `PROVENANCE.md` has the measurements.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_lbco-hrpt/PROVENANCE.md).
