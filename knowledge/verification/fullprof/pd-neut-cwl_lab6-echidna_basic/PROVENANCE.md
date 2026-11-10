# `pd-neut-cwl_lab6-echidna_basic` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-cwl_lab6`, set `ECH0030684_LaB6_1p622A_baseline`, pin `39ada82c`. Mirrors the upstream page **`pd-neut-cwl_LaB6_basic`**. Instrument ECHIDNA (ANSTO; run prefix `ECH`).

Every parameter is fixed (a forward calculation). Its occupancies already follow the convention (k = 1), so it is **not re-fit**: its inputs and every replaying output are byte-identical to its source (the owner's refit is owed only where the occupancy convention changes the scale).

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P m -3 m` | `La` | 1 / 48 | 1 | 0.02083 |
| 1 | `P m -3 m` | `B` | 6 / 48 | 1 | 0.12500 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 42.9837 | 42.9837 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'ECH0030684_LaB6_1p622A_baseline\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 32.6 Rwp: 47.5 Rexp: 2.76 Chi2: 297.`.

## Files (sha256)

- `ECH0030684_LaB6_1p622A_baseline.bac` `a3fe5fcf1e9a5a43d5e854ce840dc84aa6862a1f747d1f7b5e72fff9b0366e3c`
- `ECH0030684_LaB6_1p622A_baseline.dat` `c41427269a36cad15936de9c11fea8c6719293a6e5acfe4146291efa8ed26cbc`
- `ECH0030684_LaB6_1p622A_baseline.pcr` `a6e38ea30cdf0c029a1960cbb96fae1617143b1811b01a15f8e20f8393d724d5`
- `ECH0030684_LaB6_1p622A_baseline.prf` `8d0484e615c778e6789aa60668c1649f50a151ff22e0958bd6eb0a2e43a2e481`
- `ECH0030684_LaB6_1p622A_baseline.sum` `26d2d0f4e7ae195bba13b1d34fb8300ef1ce71a1cca1cbe3c5a2ba041cbd6af8`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:La": 1.0,
    "1:B": 1.0
  },
  "start_site_occupancies": {
    "1:La": 1.0,
    "1:B": 1.0
  },
  "old_scales": [
    42.98374
  ],
  "new_scales": [
    42.98374
  ]
}
```
