---
title: "Rietveld fit: Co₂SiO₄, D20"
description: >-
  Fit the olivine Co₂SiO₄ to constant-wavelength neutron powder data from D20 at ILL: coordinates, displacements and the oxygen occupancies.
---

# Rietveld fit: Co₂SiO₄, D20

Fit the olivine Co₂SiO₄ to constant-wavelength neutron powder data from D20 at ILL: coordinates, displacements and the oxygen occupancies.

The app lists it as **Co₂SiO₄ [Pnma] · D20 @ ILL**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-cwl_cosio-d20](../../tutorials/pd-neut-cwl_cosio-d20.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-cwl_cosio-d20/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. The project selects the fast descent (`_minimizer.descent fast_descent`).

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_cosio-d20/PROVENANCE.md).
