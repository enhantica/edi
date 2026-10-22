---
title: "Two-phase fit: La₀.₅Ba₀.₅CoO₃ and Si, McStas"
description: >-
  Fit two phases, La₀.₅Ba₀.₅CoO₃ and silicon, to a time-of-flight pattern simulated with McStas.
---

# Two-phase fit: La₀.₅Ba₀.₅CoO₃ and Si, McStas

Fit two phases, La₀.₅Ba₀.₅CoO₃ and silicon, to a time-of-flight pattern simulated with McStas.

The app lists it as **La₀.₅Ba₀.₅CoO₃ [Pm-3m] / Silicon [Fd-3m] · McStas simulation**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-tof_lbco-si-mcstas/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-tof_lbco-si-mcstas](../../tutorials/pd-neut-tof_lbco-si-mcstas.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-tof_lbco-si-mcstas/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. As in diffraction-lib's tutorial, the zero shift stays fixed, and so do the Co and La Biso.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-tof_lbco-si-mcstas/PROVENANCE.md).
