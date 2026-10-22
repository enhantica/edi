---
title: "Rietveld fit: Si, SEPD"
description: >-
  Fit silicon to time-of-flight neutron powder data from SEPD at Argonne, with the Jorgensen-Von Dreele profile.
---

# Rietveld fit: Si, SEPD

Fit silicon to time-of-flight neutron powder data from SEPD at Argonne, with the Jorgensen-Von Dreele profile.

The app lists it as **Silicon [Fd-3m] · SEPD @ Argonne**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-tof_si-sepd/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-tof_si-sepd](../../tutorials/pd-neut-tof_si-sepd.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-tof_si-sepd/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. The instrument's d-to-TOF calibration (DIFC, DIFA) is the measured one, fixed.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-tof_si-sepd/PROVENANCE.md).
