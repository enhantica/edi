# `pd-neut-tof_cecoal-polaris_chebyshev` -- FullProf fitting project

Origin: FullProf's own `Examples/` (`cecoal.pcr`, `cecoal.dat` byte-identical; vendored by edi #74): CeCoAl3, **Chebyshev background** (`Nba -5`), TOF, JvD profile. Instrument POLARIS (ISIS; the `.dat` header).

A **fitting** project: parameters free, `Pcr = 2` (FullProf writes `.new`, never over the `.pcr`). restated the occupancies (below), moved the factor into the scale, and fitted every free parameter to convergence again: `full-fit.out` is that run (its first cycle carries the restated `Occ`; its exact input is `full-fit.inp`), and the committed `.pcr` is the `.new` it wrote, byte for byte. Rerunning FullProf over the committed `.pcr` converges and reproduces the committed `.prf`/`.sum` apart from the run-date and CPU-time lines.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P m m a` | `Ce` | 2 / 8 | 1 | 0.25000 |
| 1 | `P m m a` | `Co` | 2 / 8 | 1 | 0.25000 |
| 1 | `P m m a` | `Al1` | 2 / 8 | 1 | 0.25000 |
| 1 | `P m m a` | `Al2` | 2 / 8 | 1 | 0.25000 |
| 1 | `P m m a` | `Al3` | 4 / 8 | 1.02066 | 0.51033 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 1041.19 | 16659 | 0.2500002 | -1.28e-06 |

**Al3.** Al3 sits on 4j (x, 1/2, z) of P m m a, multiplicity 4 of 8; the other four sites are 2-fold. The source file normalises Occ to the 2-fold sites (Occ = site occupancy x m / 2), so its 2.04131 is a site occupancy of 1.020655 -- a fitted value (Occ is free, code 91) within its uncertainty of full occupancy, not a structural feature. Restated as 1.020655 x 4/8 = 0.5103275, the same factor 1/4 as every other site.

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'cecoal\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 3.28 Rwp: 5.34 Rexp: 3.97 Chi2: 1.80`.

## Files (sha256)

- `cecoal.dat` `3c702bc31c5c6b435a3cb8d4b72cde2495a6a521ce336fd1be20e4df6c429790`
- `cecoal.pcr` `4c453bde47e18eda8bdb867ef955e373b19c25a49db405fe0030e4599d5c1252`
- `cecoal.prf` `29a90a2f724fb244a038501bea87f90a8367f6791b7f044388e629946d8740dc`
- `cecoal.sum` `6e62f6f7ea4a3c060e75904dcb849868b90e8f80f539f9d910089d3a78f215b5`
- `full-fit.inp` `3855505b5abf332eb83cd835b87593f4197d1ebf6be336c29cbe49f20850eba2`
- `full-fit.out` `6382985e787acd9131cfae19c17eb7408ecf1a4f8b1c2844843d7e4c06275792`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Ce": 1.0,
    "1:Co": 1.0,
    "1:Al1": 1.0,
    "1:Al2": 1.0,
    "1:Al3": 1.02066
  },
  "start_site_occupancies": {
    "1:Ce": 1.0,
    "1:Co": 1.0,
    "1:Al1": 1.0,
    "1:Al2": 1.0,
    "1:Al3": 1.02066
  },
  "old_scales": [
    1041.189
  ],
  "new_scales": [
    16658.97
  ],
  "fit_out": "full-fit.out",
  "fit_inputs": {
    "full-fit.out": "full-fit.inp"
  },
  "al3_explanation": "Al3 sits on 4j (x, 1/2, z) of P m m a, multiplicity 4 of 8; the other four sites are 2-fold. The source file normalises Occ to the 2-fold sites (Occ = site occupancy x m / 2), so its 2.04131 is a site occupancy of 1.020655 -- a fitted value (Occ is free, code 91) within its uncertainty of full occupancy, not a structural feature. Restated as 1.020655 x 4/8 = 0.5103275, the same factor 1/4 as every other site."
}
```
