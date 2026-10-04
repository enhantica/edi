---
title: LiF X-ray with the polarization factor, against FullProf
description: >-
  LiF with Cu K-alpha1 X-rays (constant wavelength). The pattern is FullProf's calculated profile with its monochromator polarization term; the polarization coefficient and the monochromator angle are free and start away from FullProf's values.
---

# LiF X-ray with the polarization factor, against FullProf

LiF with Cu Kα₁ X-rays (constant wavelength). The measured pattern is FullProf's **calculated** profile with its monochromator polarization term (`Cthm` 0.8, `Rpolarz` 0.5), and the model is FullProf's own. The two polarization parameters are free and start away from FullProf's values: `setup_polarization_coefficient` at 0.4 and `setup_monochromator_twotheta` at 20°.

It is the CLI counterpart of the [`pd-xray-cwl_LiF_single_polarization`](../../../dev/verification/pd-xray-cwl_LiF_single_polarization.ipynb) verification page: where the page compares calculated patterns at fixed parameters, this project fits the two parameters and checks that they land on FullProf's inputs, 0.5 and 26.565° (`acos(√0.8)`).

## Run it

```bash
python -m edi fit docs/user/cli/pd-xray-cwl_lif_single/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is fitted, and why the scale is not

The intensity of each reflection is multiplied by `P = 1 − K + K cos²(2θ_m) cos²(2θ)`. With the scale `s`, the pattern depends on `s (1 − K)` and `s K cos²(2θ_m)` only, so the scale, `K` and `2θ_m` together carry two independent numbers. The scale is therefore fixed, at twice FullProf's 0.01: for characteristic radiation FullProf uses `1 + Cthm cos²(2θ)`, which is twice `P` at `K = 0.5`.

## What is checked

`expected.json` holds two **references** and three **regression pins** for the `fast_descent` fit: the fitted `setup_polarization_coefficient` must land within 5·10⁻⁵ of FullProf's 0.5 and `setup_monochromator_twotheta` within 0.15° of 26.565° (measured: 0.4999921 and 26.633°, the residue of crysta's 0.06 % relative difference from FullProf's pattern), and the chi-square, iteration count and Rwp are pinned to their measured values. The runner fits a copy of the project, declaring the descent as `_minimizer.descent` in the copy's `analysis/analysis.edi`, and compares every quantity. CI and `pixi run verify` run this project through `python -m edi` on every pull request, and any value outside its tolerance fails the build (`tools/checks/cli_projects.py`). crysta's corpus case `lif-xray-s1` is the same project, timed by crysta's A/B performance gate.
