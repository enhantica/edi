---
title: "Calculation without data: Tb₂Ti₂O₇, HEiDi"
description: >-
  Calculate the single-crystal neutron reflections of the pyrochlore Tb₂Ti₂O₇ on HEiDi at MLZ without any measured data. The structure, the wavelength and the extinction are in the project, and edi calculates every reflection up to the project's sin θ/λ limit.
---

# Calculation without data: Tb₂Ti₂O₇, HEiDi

Calculate the single-crystal neutron reflections of the pyrochlore Tb₂Ti₂O₇ on HEiDi at MLZ without any measured data. The structure, the wavelength and the extinction are in the project, and edi calculates every reflection up to the project's sin θ/λ limit.

The app lists it as **Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)**.

## Three ways to run it

- **Command line:** `python -m edi calc docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_simulation/project --dry` (calculates
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [sc-neut-cwl_tb2ti2o7-heidi_simulation](../../tutorials/sc-neut-cwl_tb2ti2o7-heidi_simulation.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_simulation/project`.

## The start

Nothing is fitted: the reflections are calculated from the model as the project holds it.

## Sources

Where the model comes from:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_simulation/PROVENANCE.md).
