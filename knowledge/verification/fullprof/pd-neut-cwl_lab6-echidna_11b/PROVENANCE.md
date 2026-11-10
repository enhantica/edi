# `pd-neut-cwl_lab6-echidna_11b` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-cwl_lab6`, set `ECH0030684_LaB6_1p622A_11B`, pin `39ada82c`. Mirrors the upstream page **`pd-neut-cwl_LaB6_11B`**. Instrument ECHIDNA (run prefix `ECH`).

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

FullProf.2k 8.40 (Feb2026-ILL): `printf 'ECH0030684_LaB6_1p622A_11B\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 31.5 Rwp: 59.1 Rexp: 2.76 Chi2: 460.`.

## Files (sha256)

- `ECH0030684_LaB6_1p622A_11B.bac` `d35819a839993fc1d967e8b946a72bc373d89f073d5a3b6964ee7a7efa821bf2`
- `ECH0030684_LaB6_1p622A_11B.dat` `c41427269a36cad15936de9c11fea8c6719293a6e5acfe4146291efa8ed26cbc`
- `ECH0030684_LaB6_1p622A_11B.pcr` `284cd7020a35427d8a3df107792fc74ff7f043e011eac896de6987f35bfa2530`
- `ECH0030684_LaB6_1p622A_11B.prf` `99c6851fedae979a0f84eeddff33ecd143025d8c462dabcf6160d9492ba9eb6e`
- `ECH0030684_LaB6_1p622A_11B.sum` `8ff10c7420dbf29c58fb2a00ce15db8415b5c7b5ebcef5d53e87396561d0ae61`

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
