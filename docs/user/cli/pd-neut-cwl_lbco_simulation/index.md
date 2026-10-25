---
title: "Calculation without data: La₀.₅Ba₀.₅CoO₃, HRPT"
description: >-
  Calculate a constant-wavelength neutron pattern of the cubic perovskite La₀.₅Ba₀.₅CoO₃ without any measured data. The structure, the HRPT instrument, the peak profile and the background are in the project, and edi calculates the pattern over the project's 2θ range.
---

# Calculation without data: La₀.₅Ba₀.₅CoO₃, HRPT

Calculate a constant-wavelength neutron pattern of the cubic perovskite La₀.₅Ba₀.₅CoO₃ without any measured data. The structure, the HRPT instrument, the peak profile and the background are in the project, and edi calculates the pattern over the project's 2θ range.

The app lists it as **La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI**.

## Three ways to run it

- **Command line:** `python -m edi calc docs/user/cli/pd-neut-cwl_lbco_simulation/project --dry` (calculates
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-cwl_lbco_simulation](../../tutorials/pd-neut-cwl_lbco_simulation.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-cwl_lbco_simulation/project`.

## The start

Nothing is fitted: the pattern is calculated from the model as the project holds it.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_lbco_simulation/PROVENANCE.md).
