# `pd-neut-cwl_lab6-echidna_fcj-asymmetry` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-cwl_lab6`, set `ECH0030684_LaB6_1p622A_fcj`, pin `0d9f10e4`. Mirrors the upstream page **`pd-neut-cwl_LaB6_fcj-asymmetry`**. Instrument ECHIDNA (ANSTO; run prefix `ECH`). The Finger-Cox-Jephcoat asymmetry is on (`S_L` = `D_L` = 0.08).

Every parameter is fixed (a forward calculation). Its occupancies already follow the convention (k = 1), so it is **not re-fit**: its inputs and outputs are its source bytes, and every output replays under FullProf 8.40 apart from the run-date lines (checked at vendoring).

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8).

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P m -3 m` | `La` | 1 / 48 | 1 | 0.02083 |
| 1 | `P m -3 m` | `B` | 6 / 48 | 1 | 0.12500 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 42.9837 | 42.9837 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'ECH0030684_LaB6_1p622A_fcj\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 66.6 Rwp: 83.3 Rexp: 4.69 Chi2: 315.`.

## Files (sha256)

- `ECH0030684_LaB6_1p622A_fcj.bac` `6e9c617371a72357082cd201a44d7e8c1d0a104ef1f139d3ea3173c3ef592149`
- `ECH0030684_LaB6_1p622A_fcj.dat` `c41427269a36cad15936de9c11fea8c6719293a6e5acfe4146291efa8ed26cbc`
- `ECH0030684_LaB6_1p622A_fcj.pcr` `34aa5fb2745ecff3ea206126faf2c1055a45cabe0a43a17105e3efe76653f26a`
- `ECH0030684_LaB6_1p622A_fcj.prf` `791ed87f188bcdefcb668d81d144023d7c8f9cad8b05ed7b829ae420813b8d85`
- `ECH0030684_LaB6_1p622A_fcj.sum` `42289ad161634b6fed3c3047da295c824058e663d6ba5bed68ad9e8c0da08cd3`

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
