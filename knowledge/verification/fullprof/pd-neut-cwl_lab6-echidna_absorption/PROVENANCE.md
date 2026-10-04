# `pd-neut-cwl_lab6-echidna_absorption` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-cwl_lab6`, set `ECH0030684_LaB6_1p622A_absorption`, pin `39ada82c`. Mirrors the upstream page **`pd-neut-cwl_LaB6_absorption`**. Instrument ECHIDNA (run prefix `ECH`).

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

FullProf.2k 8.40 (Feb2026-ILL): `printf 'ECH0030684_LaB6_1p622A_absorption\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 41.0 Rwp: 47.9 Rexp: 2.76 Chi2: 302.`.

## Files (sha256)

- `ECH0030684_LaB6_1p622A_absorption.bac` `66ca08f0fe55304143f5e6a4a43def3e85dbadbf2350c7fa2f52fabd940665fa`
- `ECH0030684_LaB6_1p622A_absorption.dat` `c41427269a36cad15936de9c11fea8c6719293a6e5acfe4146291efa8ed26cbc`
- `ECH0030684_LaB6_1p622A_absorption.pcr` `65841dda06ebfaa8d17e567ed1e635084bab83df48ab605a06af5d58d10d38a4`
- `ECH0030684_LaB6_1p622A_absorption.prf` `40d897f62aa26a762a42e2eb56d6ea829e90bbdefe2f431f89e130b1cbb2f560`
- `ECH0030684_LaB6_1p622A_absorption.sum` `52831cc5e68a8c822fb12e5fd4419535fd49605893058371bcd1458b08e963b6`

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
