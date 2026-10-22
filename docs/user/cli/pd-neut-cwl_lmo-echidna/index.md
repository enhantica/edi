---
title: "Rietveld fit: LiNiO₂, ECHIDNA"
description: >-
  Fit the layered oxide LiNiO₂ to constant-wavelength neutron powder data from ECHIDNA at ANSTO. Li and Ni mix between two sites, held to full occupancy by constraints, and the profile has Finger-Cox-Jephcoat asymmetry.
---

# Rietveld fit: LiNiO₂, ECHIDNA

Fit the layered oxide LiNiO₂ to constant-wavelength neutron powder data from ECHIDNA at ANSTO. Li and Ni mix between two sites, held to full occupancy by constraints, and the profile has Finger-Cox-Jephcoat asymmetry.

The app lists it as **LiNiO₂ [R-3m] · ECHIDNA @ ANSTO**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-cwl_lmo-echidna/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-cwl_lmo-echidna](../../tutorials/pd-neut-cwl_lmo-echidna.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-cwl_lmo-echidna/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. Li1 starts at 0.95, 5 % Ni on the Li site, and the asymmetry terms stay fixed at 0.08: they describe the instrument's geometry.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_lmo-echidna/PROVENANCE.md).
