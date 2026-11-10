# `pd-neut-cwl_pbso4_basic` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder of the same name, pin `39ada82c`. Mirrors the upstream page **`pd-neut-cwl_PbSO4_basic`**. No source names the instrument, so the id carries none.

Every parameter is fixed (a forward calculation). Its occupancies already follow the convention (k = 1), so it is **not re-fit**: its inputs and every replaying output are byte-identical to its source (the owner's refit is owed only where the occupancy convention changes the scale).

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P n m a` | `Pb` | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `S` | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `O1` | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `O2` | 4 / 8 | 1 | 0.50000 |
| 1 | `P n m a` | `O3` | 8 / 8 | 1 | 1.00000 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 1.4679 | 1.4679 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'pbso4\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 3.47 Rwp: 4.24 Rexp: 1.95 Chi2: 4.72`.

## Files (sha256)

- `pbso4.bac` `e7a9a2551558c8fd8159b85adaaf7ad5e15fce173fc9fcd950defaaade7154c8`
- `pbso4.dat` `637bfde3bb1adb24045fb688c2a0cdfd424bf7bc9956f267a11053ba82a944e2`
- `pbso4.pcr` `b1f962c0d10c3ac50fa63c550d5aa85e463626c53ab346b6ef473cf5c0b73538`
- `pbso4.prf` `c85bf109a776be3257fd8b8d69cb554435a1d106de54444aadc5bfa9fe15e907`
- `pbso4.sum` `00ae2424b0ce876f2ed173cc51ca88d48fb2e704b071fd8e6366d9055fc92768`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Pb": 1.0,
    "1:S": 1.0,
    "1:O1": 1.0,
    "1:O2": 1.0,
    "1:O3": 1.0
  },
  "start_site_occupancies": {
    "1:Pb": 1.0,
    "1:S": 1.0,
    "1:O1": 1.0,
    "1:O2": 1.0,
    "1:O3": 1.0
  },
  "old_scales": [
    1.4679
  ],
  "new_scales": [
    1.4679
  ]
}
```
