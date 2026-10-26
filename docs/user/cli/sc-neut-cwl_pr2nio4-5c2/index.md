---
title: "Single-crystal fit: Pr₂NiO₄, 5C2"
description: >-
  Fit the layered nickelate Pr₂NiO₄ to constant-wavelength neutron single-crystal data from 5C2 at LLB, with anisotropic displacements.
---

# Single-crystal fit: Pr₂NiO₄, 5C2

Fit the layered nickelate Pr₂NiO₄ to constant-wavelength neutron single-crystal data from 5C2 at LLB, with anisotropic displacements.

The app lists it as **Pr₂NiO₄ [Fmmm] · 5C2 @ LLB**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/sc-neut-cwl_pr2nio4-5c2/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [sc-neut-cwl_pr2nio4-5c2](../../tutorials/sc-neut-cwl_pr2nio4-5c2.ipynb) loads this project and works
  through it.

All three read the same files, in `docs/user/cli/sc-neut-cwl_pr2nio4-5c2/project`.

## The start

The project starts from zero: every displacement at 0 (Bani on every site but Od, which is Biso) and free, the free coordinates moved off their refined values, no extinction, and the scale to one significant figure.

## Sources

Where the data and the model come from, with the data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/sc-neut-cwl_pr2nio4-5c2/PROVENANCE.md).
