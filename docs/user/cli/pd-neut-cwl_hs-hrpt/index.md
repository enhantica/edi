---
title: "Rietveld fit: herbertsmithite, HRPT"
description: >-
  Fit herbertsmithite, ZnCu₃(OD)₆Cl₂, a deuterated kagome antiferromagnet, to constant-wavelength neutron powder data from HRPT at PSI, with a pseudo-Voigt profile and Bérar-Baldinozzi asymmetry.
---

# Rietveld fit: herbertsmithite, HRPT

Fit herbertsmithite, ZnCu₃(OD)₆Cl₂, a deuterated kagome antiferromagnet, to constant-wavelength neutron powder data from HRPT at PSI, with a pseudo-Voigt profile and Bérar-Baldinozzi asymmetry.

The app lists it as **ZnCu₃(OD)₆Cl₂ [R-3m] · HRPT @ PSI**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-cwl_hs-hrpt/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-cwl_hs-hrpt](../../tutorials/pd-neut-cwl_hs-hrpt.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-cwl_hs-hrpt/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_hs-hrpt/PROVENANCE.md).
