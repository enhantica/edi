---
title: "Calculation without data: Si, time of flight"
description: >-
  Calculate a time-of-flight neutron pattern of silicon without any measured data. For a time-of-flight instrument a time window means nothing without a calibration, so the calculation range follows from the instrument's d-to-TOF calibration.
---

# Calculation without data: Si, time of flight

Calculate a time-of-flight neutron pattern of silicon without any measured data. For a time-of-flight instrument a time window means nothing without a calibration, so the calculation range follows from the instrument's d-to-TOF calibration.

The app lists it as **Silicon [Fd-3m] · SEPD @ Argonne**.

## Three ways to run it

- **Command line:** `python -m edi calc docs/user/cli/pd-neut-tof_si_simulation/project --dry` (calculates
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-tof_si_simulation](../../tutorials/pd-neut-tof_si_simulation.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-tof_si_simulation/project`.

## The start

Nothing is fitted: the pattern is calculated from the model as the project holds it.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-tof_si_simulation/PROVENANCE.md).
