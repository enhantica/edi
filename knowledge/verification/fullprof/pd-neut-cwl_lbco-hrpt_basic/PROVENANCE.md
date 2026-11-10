# `pd-neut-cwl_lbco-hrpt_basic` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-cwl_lbco_basic`, pin `39ada82c`. Mirrors the upstream page **`pd-neut-cwl_LBCO_basic`**. Instrument HRPT (PSI; crysta fitting case `lbco-hrpt`).

Every parameter is fixed (a forward calculation). Its occupancies already follow the convention (k = 1), so it is **not re-fit**: its inputs and every replaying output are byte-identical to its source (the owner's refit is owed only where the occupancy convention changes the scale).

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P m -3 m` | `La` | 1 / 48 | 0.5 | 0.01042 |
| 1 | `P m -3 m` | `Ba` | 1 / 48 | 0.5 | 0.01042 |
| 1 | `P m -3 m` | `Co` | 1 / 48 | 1 | 0.02083 |
| 1 | `P m -3 m` | `O` | 3 / 48 | 0.9786 | 0.06116 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 9.40587 | 9.40587 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'lbco\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 5.62 Rwp: 7.22 Rexp: 6.36 Chi2: 1.29`.

## Files (sha256)

- `lbco.bac` `07f4b0b0371334c6b67bfebca0f75374e2e33685fdbf87ee877d673335833d03`
- `lbco.dat` `83c7f3d27d2e254367dd7dc3730261b9a5ebb811baaeed01fde050a7ba99be24`
- `lbco.pcr` `4ec747b9dc88dd798015d7061dccee6e9f31dc8f2448a82a943a0a965fd84581`
- `lbco.prf` `640490df5dd98482f561c7b1a3a7714ae860bc6fd709db1b40b37b5275dff1bb`
- `lbco.sum` `9a96665f826bd0b83e374992c8a56868094906a674ff4b348618ec8e774acde9`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:La": 0.5,
    "1:Ba": 0.5,
    "1:Co": 1.0,
    "1:O": 0.9786
  },
  "start_site_occupancies": {
    "1:La": 0.5,
    "1:Ba": 0.5,
    "1:Co": 1.0,
    "1:O": 0.9786
  },
  "old_scales": [
    9.40587
  ],
  "new_scales": [
    9.40587
  ]
}
```
