---
title: La0.5Ba0.5CoO3 on HRPT, start-2
description: >-
  La0.5Ba0.5CoO3 (cubic perovskite) against HRPT (PSI) constant-wavelength neutron powder data: 17 parameters — the cell edge, four isotropic ADPs, the pseudo-Voigt profile (U, V, W, Y), the 2θ offset, the scale, five background points and the March–Dollase preferred-orientation coefficient r (axis [0 0 1]).
---

# La0.5Ba0.5CoO3 on HRPT, start-2

La<sub>0.5</sub>Ba<sub>0.5</sub>CoO<sub>3</sub> (cubic perovskite) against HRPT (PSI) constant-wavelength neutron powder data: 17 parameters — the cell edge, four isotropic ADPs, the pseudo-Voigt profile (U, V, W, Y), the 2θ offset, the scale, five background points and the March–Dollase preferred-orientation coefficient r (axis [0 0 1]).

The start is **start-2** — rung 2 of the graded starting points recorded for the fitting corpus (1 is the farthest from the solution); the sibling project [`pd-neut-cwl_lbco-hrpt_start-4`](../pd-neut-cwl_lbco-hrpt_start-4/index.md) fits the same model, without the preferred-orientation row, from a
different start, so the pair exercises the descent from two different distances to the minimum.

**Preferred orientation.** The experiment carries one `_preferred_orientation` row, `march_r` free from 0.8. The data is
untextured, so r converges to 0.998; on a cubic structure r enters only at second order near 1, so its uncertainty is large (its
`PROVENANCE.md`). The kernel itself is verified against FullProf on the [LBCO preferred-orientation
page](../../../dev/verification/pd-neut-cwl_LBCO_preferred-orientation.ipynb).

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values
back. Add `--report machine --verbosity full` for the versioned `key=value` record the checks
read.

## What is checked

`expected.json` pins the result of each listed descent strategy (its `variants`): the runner fits a copy of the project once per variant, declaring that descent as `_minimizer.descent` in the copy's `analysis/analysis.edi`, and compares every quantity. CI and `pixi run verify` run this project through `python -m edi` on every pull
request, and any value outside its tolerance fails the build
(`tools/checks/cli_projects.py`).
