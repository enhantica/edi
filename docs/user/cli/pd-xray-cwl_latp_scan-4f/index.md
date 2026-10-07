---
title: LATP with two AlPO4 phases, synchrotron X-ray sequential scan
description: >-
  A sequential fit of Li1.3Al0.3Ti1.7(PO4)3 with two AlPO4 phases over four synchrotron X-ray scan files made from the
  owner's summed pattern: three phases, 54 parameters, constraints across each phase's displacement parameters, checked
  against the owner's FullProf fit.
---

# LATP with two AlPO4 phases, synchrotron X-ray sequential scan

A **sequential** fit of three phases in one constant-wavelength synchrotron X-ray experiment (λ = 0.28457 Å):
Li<sub>1.3</sub>Al<sub>0.3</sub>Ti<sub>1.7</sub>(PO<sub>4</sub>)<sub>3</sub> (`R -3 c`) with AlPO<sub>4</sub> in
`C 2 2 21` and in `P 63 m c`. The 54 parameters are each phase's scale, cell and displacement parameter, the LATP
positions, the shared pseudo-Voigt profile (U, W, η) and a 30-point line-segment background. Within each phase the
other atoms' Biso follow one free Biso through constraints (Analysis › Extra › Constraints), and Ti1 z equals Al1 z.

The scan has four files in `project/experiments/latp_scan`, each in the two-column shape of the owner's scan files:

| file | content |
| --- | --- |
| `pattern_0_0001.txt` | the summed pattern |
| `pattern_0_0002.txt` | the summed pattern × 0.96 |
| `pattern_0_0003.txt` | the summed pattern × 1.04, its first 20 points negative, as in a background-subtracted frame |
| `pattern_0_0004.txt` | zeros only, as in a frame with no beam |

Each file is fitted from the previous one's result. The negative points of the third file are skipped and counted,
and the fourth file is skipped as a dataset; both are listed in `analysis/scan-notes.csv`, and `edi fit` reports them
after the scan summary.

## Run it

```bash
python -m edi fit docs/user/cli/pd-xray-cwl_latp_scan-4f/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back.

## Against FullProf

The model is the owner's FullProf project, `fullprof/latp.pcr`, fitted on the summed pattern
`fullprof/s13_150_z20_xrd_sum.dat` (FullProf's reduced χ² 7.05). The first scan file is that pattern, so its row of
`analysis/results.csv` is a single fit of the same data:

| parameter | FullProf | edi (first file) | difference / edi e.s.d. |
| --- | --- | --- | --- |
| LATP a (Å) | 8.378689 | 8.37864(24) | −0.2 |
| LATP c (Å) | 20.743496 | 20.7436(12) | +0.1 |
| Ti1 z | 0.14041 | 0.14041(14) | 0.0 |
| P1 x | 0.28467 | 0.28462(48) | −0.1 |
| U | 0.378068 | 0.375(14) | −0.2 |
| W | 0.000659 | 0.000666(30) | +0.2 |
| η | 0.53317 | 0.533(17) | 0.0 |
| Li1 Biso (Å²) | 0.1898 | 0.184(55) | −0.1 |
| reduced χ² | 7.05 | 6.66 | |

Every value agrees within a quarter of its e.s.d. `expected.json` checks the same eight values of the last fitted
file against FullProf's, each within two edi e.s.d.s.

The models differ where edi has no counterpart or the owner chose otherwise, which is also why the χ² values differ:

- no per-phase overall B (FullProf's Bov): it is folded into the atoms' Biso;
- no absorption correction (FullProf's μR 0.3) and no polarization correction;
- FullProf's `Occ` values are converted to site occupancies (Ti1 0.85, Al1 0.15, the rest 1);
- the `P 63 m c` phase's Biso starts at 0.5 instead of FullProf's 0.

## What is checked

CI and `pixi run verify` run this project through `python -m edi` (`tools/checks/cli_projects.py`) and compare its
machine record with `expected.json`: the number of free parameters (54, FullProf's free set), the FullProf values
above, and the last fitted file's reduced chi-square and iteration count against regression pins. `PROVENANCE.md`
says where each value came from.
