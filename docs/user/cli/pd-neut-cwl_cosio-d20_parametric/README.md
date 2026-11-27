---
title: "Parametric fit: Co₂SiO₄, D20 scan with shared peak widths"
description: >-
  The 213 D20 patterns of the Co2SiO4 cooling scan fitted as one, with the peak widths U, V and W shared by all of them
  and every other parameter fitted per pattern.
---

# Parametric fit: Co₂SiO₄, D20 scan with shared peak widths

The [213-pattern cooling scan](../pd-neut-cwl_cosio-d20_scan-213f/index.md) of Co<sub>2</sub>SiO<sub>4</sub> on D20,
fitted in the **parametric** mode. The peak widths U, V and W describe the instrument, so they are **shared**: one
value of each, refined against all 213 patterns. Everything else (the scale, the background, the cell, the atoms and
the moments) is fitted per pattern, as in the sequential example.

The model and the data are the sequential example's; only `analysis/analysis.edi` differs. It sets
`_fitting_mode.type parametric` and lists the three shared parameters:

```text
loop_
_parametric_fit_shared.parameter_unique_name
d20.peak.broad_gauss_u
d20.peak.broad_gauss_v
d20.peak.broad_gauss_w
```

Every pattern starts from the template's values. In `analysis/results.csv` U, V and W have the same value and
uncertainty in every row, and every uncertainty is scaled by the reduced χ² of the whole scan.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_parametric/project --dry`.
- **App:** open the project; on the Analysis page the **Shared** column marks U, V and W, and Start fitting fits the
  whole scan at once. The Evolution chart is redrawn as the fit goes.
- **Python:** `edi.load(path).analysis.fit()` runs the project's mode.

`--dry` writes the results to a scratch directory and leaves the project unchanged; the scan data are read in place.

[Shared parameters and the parametric fit](../../guides/shared-parameters-and-the-parametric-fit.md) explains the
Shared column and the mode.
