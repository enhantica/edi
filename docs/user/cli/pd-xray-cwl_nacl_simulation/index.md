---
title: "Calculation without data: NaCl, laboratory X-ray"
description: >-
  Calculate a laboratory X-ray pattern of rock salt with Cu Kα₁ radiation and a monochromator's polarization correction, without any measured data.
---

# Calculation without data: NaCl, laboratory X-ray

Calculate a laboratory X-ray pattern of rock salt with Cu Kα₁ radiation and a monochromator's polarization correction, without any measured data.

The app lists it as **NaCl [Fm-3m] · Laboratory X-ray**.

## Three ways to run it

- **Command line:** `python -m edi calc docs/user/cli/pd-xray-cwl_nacl_simulation/project --dry` (calculates
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-xray-cwl_nacl_simulation](../../tutorials/pd-xray-cwl_nacl_simulation.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-xray-cwl_nacl_simulation/project`.

## The start

Nothing is fitted: the pattern is calculated from the model as the project holds it.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-xray-cwl_nacl_simulation/PROVENANCE.md).
