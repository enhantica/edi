---
title: "Joint fit: Na₂Ca₃Al₂F₁₄, WISH"
description: >-
  Fit Na₂Ca₃Al₂F₁₄ to time-of-flight neutron powder data from WISH at ISIS, all five detector bank pairs at once. Each bank has its own calibration and profile; the structure is shared.
---

# Joint fit: Na₂Ca₃Al₂F₁₄, WISH

Fit Na₂Ca₃Al₂F₁₄ to time-of-flight neutron powder data from WISH at ISIS, all five detector bank pairs at once. Each bank has its own calibration and profile; the structure is shared.

The app lists it as **Na₂Ca₃Al₂F₁₄ [I2₁3] · WISH @ ISIS**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-tof_ncaf-wish/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-neut-tof_ncaf-wish](../../tutorials/pd-neut-tof_ncaf-wish.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-neut-tof_ncaf-wish/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. The peaks start about 30 % narrower than they fit, with the shape moved towards Gaussian.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-tof_ncaf-wish/PROVENANCE.md).
