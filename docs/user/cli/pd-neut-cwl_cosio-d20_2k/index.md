---
title: "Magnetic structure: Co₂SiO₄, D20, 2.3 K"
description: >-
  The olivine Co₂SiO₄ below its Néel temperature: constant-wavelength neutron powder data from D20 at ILL with the
  magnetic structure in Pnma.1, its moments drawn in the structure view.
---

# Magnetic structure: Co₂SiO₄, D20, 2.3 K

Co₂SiO₄ orders antiferromagnetically below about 50 K. At 2.3 K the D20 pattern carries magnetic reflections, such
as (100) near 2θ = 10.7° and (001) near 22.8°, that the nuclear structure in Pnma forbids. The magnetic space group is
Pnma.1 (BNS 62.441) with propagation vector k = 0. The site symmetry leaves Co1 free in all three moment components
and Co2 only along b.

The app lists it as **Co₂SiO₄ [Pnma.1] · D20 @ ILL**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_2k/project --dry` (fits without writing
  back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page. The structure view draws each cobalt's moment as an arrow; the
  toolbar shows or hides them, and the arrow length per Bohr magneton is set under Preferences, Appearance.
- **Python:** `edi.Project.load("docs/user/cli/pd-neut-cwl_cosio-d20_2k/project")`.

All three read the same files, in `docs/user/cli/pd-neut-cwl_cosio-d20_2k/project`.

## The model

The moments start along b at 1 μB: Co1 (0, 1, 0) μB and Co2 (0, 1, 0) μB along a, b and c, and the fit finds their
size and direction. Every displacement parameter is fixed at a fit of the paramagnetic pattern at
56.8 K, with Co1 and Co2 sharing one value. One dead detector cell at 64.6953° is excluded.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_cosio-d20_2k/PROVENANCE.md).
