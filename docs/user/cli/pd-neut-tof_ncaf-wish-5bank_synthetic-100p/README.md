---
title: Na2Ca3Al2F14 on WISH, a synthetic 100-point series of five-bank joint fits
description: >-
  A series of joint fits of 100 points, each with one file per WISH bank of Na2Ca3Al2F14, for looking at a long series in the app.
---

# Na2Ca3Al2F14 on WISH, a synthetic 100-point series of five-bank joint fits

A **series of joint fits** of 100 points, each a joint fit of the five WISH banks of
Na<sub>2</sub>Ca<sub>3</sub>Al<sub>2</sub>F<sub>14</sub>: 500 files in `project/data`, one per bank per point. It is
the same series as the six-point `pd-neut-tof_ncaf-wish-5bank_scan-6p`, made longer, so that the app's views of a
series can be looked at with many points.

The data are synthetic (`PROVENANCE.md`). The project is not in the executing set: fitting all 100 points takes a
few minutes.

## Open it

In the app, open the folder `docs/user/cli/pd-neut-tof_ncaf-wish-5bank_synthetic-100p/project`, or choose the example
in the examples list. From the command line:

```bash
python -m edi fit docs/user/cli/pd-neut-tof_ncaf-wish-5bank_synthetic-100p/project --dry
```
