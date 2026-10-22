---
title: "Joint fit: ferrite and austenite, BEER"
description: >-
  Calibrate the BEER instrument at ESS with two McStas-simulated banks of a ferrite and austenite duplex steel, fitted together: each bank has its own zero and resolution.
---

# Joint fit: ferrite and austenite, BEER

Calibrate the BEER instrument at ESS with two McStas-simulated banks of a ferrite and austenite duplex steel, fitted together: each bank has its own zero and resolution.

The app lists it as **Ferrite [Im-3m] / Austenite [Fm-3m] · BEER @ ESS**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-tof_ferrite-austenite-beer/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-tof_ferrite-austenite-beer](../../tutorials/pd-neut-tof_ferrite-austenite-beer.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-tof_ferrite-austenite-beer/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. The cells and the DIFC are fixed: this is a calibration.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-tof_ferrite-austenite-beer/PROVENANCE.md).
