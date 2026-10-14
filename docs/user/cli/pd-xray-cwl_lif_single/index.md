---
title: LiF X-ray with the Kα doublet and absorption, against FullProf
description: >-
  LiF with Cu K-alpha X-rays (constant wavelength). The pattern is FullProf's calculated profile with the K-alpha doublet, the monochromator polarization and cylinder absorption; the doublet's intensity ratio and the absorption's muR are free and start away from FullProf's values.
---

# LiF X-ray with the Kα doublet and absorption, against FullProf

LiF with Cu Kα X-rays (constant wavelength). The measured pattern is FullProf's **calculated** profile with the Cu Kα doublet (`Lambda2` 1.5444 Å, `Ratio` 0.5), the monochromator polarization (`Cthm` 0.8) and the cylinder absorption (`muR` 0.9), and the model is FullProf's own. Two parameters are free and start away from FullProf's values: `setup_wavelength_2_to_1_ratio` at 0.4 and `mu_r` at 0.7.

It is the CLI counterpart of the [`pd-xray-cwl_LiF_doublet`](../../../dev/verification/pd-xray-cwl_LiF_doublet.ipynb) and [`pd-xray-cwl_LiF_single_absorption`](../../../dev/verification/pd-xray-cwl_LiF_single_absorption.ipynb) verification pages: where the pages compare calculated patterns at fixed parameters, this project fits the two parameters and checks that they land on FullProf's inputs, 0.5 and 0.9.

## Run it

```bash
python -m edi fit docs/user/cli/pd-xray-cwl_lif_single/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is fitted, and what is not

The doublet's second component adds the ratio times the pattern at the second wavelength, so the ratio is set by the shape of every split peak. The absorption scales each reflection by the Hewat transmission at its own Bragg angle, so `mu_r` is set by how the intensities fall with angle. The scale, the second wavelength and the polarization stay at FullProf's values (the scale at twice FullProf's 0.01: for characteristic radiation FullProf uses `1 + Cthm cos²(2θ)`, which is twice the polarization factor at `K = 0.5`).

## What is checked

`expected.json` holds two **references** and three **regression pins** for the `fast_descent` fit: the fitted `setup_wavelength_2_to_1_ratio` must land within 3·10⁻⁴ of FullProf's 0.5 and `mu_r` within 1·10⁻³ of 0.9 (measured: 0.4999274 and 0.9001989, the residue of crysta's 0.04 % relative difference from FullProf's pattern), and the chi-square, iteration count and Rwp are pinned to their measured values. The runner fits a copy of the project, declaring the descent as `_minimizer.descent` in the copy's `analysis/analysis.edi`, and compares every quantity. CI and `pixi run verify` run this project through `python -m edi` on every pull request, and any value outside its tolerance fails the build (`tools/checks/cli_projects.py`).
