---
title: "Single-crystal fit: taurine, SENJU"
description: >-
  Fit the amino-sulfonic acid taurine to six time-of-flight neutron single-crystal datasets from SENJU at J-PARC together, each reflection measured at its own wavelength.
---

# Single-crystal fit: taurine, SENJU

Fit the amino-sulfonic acid taurine to six time-of-flight neutron single-crystal datasets from SENJU at J-PARC together, each reflection measured at its own wavelength.

The app lists it as **Taurine [P2₁/c] · SENJU @ J-PARC**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/sc-neut-tof_taurine-senju/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [sc-neut-tof_taurine-senju](../../tutorials/sc-neut-tof_taurine-senju.ipynb) loads this project and works
  through it.

All three read the same files, in `docs/user/cli/sc-neut-tof_taurine-senju/project`.

## The start

The project starts away from FullProf's fit: every beta tensor 0, four coordinates moved by 0.005, FullProf's scales and the anisotropic Larson extinction 0, every one free.

## Sources

Where the data and the model come from, with the data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/sc-neut-tof_taurine-senju/PROVENANCE.md).
