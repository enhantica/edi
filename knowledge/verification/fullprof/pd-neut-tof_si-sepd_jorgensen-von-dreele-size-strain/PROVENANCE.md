# `pd-neut-tof_si-sepd_jorgensen-von-dreele-size-strain` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-tof_si_jorgensen-von-dreele-size-strain`, pin `39ada82c` (`.dat`/`.bac` at `0d9f10e`; no `.irf` upstream). Mirrors the upstream page **`pd-neut-tof_Si_jorgensen-von-dreele-size-strain`**. Instrument SEPD (crysta fitting case `si-sepd`).

Every parameter is fixed (a forward calculation). Its occupancies already follow the convention (k = 1), so it is **not re-fit**: its inputs and every replaying output are byte-identical to its source (the owner's refit is owed only where the occupancy convention changes the scale).

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `F d -3 m` | `Si` | 8 / 192 | 1 | 0.04167 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 388.849 | 388.849 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'arg_si\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 23.9 Rwp: 17.9 Rexp: 3.66 Chi2: 23.8`.

## Files (sha256)

- `arg_si.bac` `5288467734eff47d8fb9d0967c25b15ce94d90f9680926e07b4d555e8052a56c`
- `arg_si.dat` `261b9e2846b0b159dab906e144d5f05e36cdad36a42edf1df848720043568e5b`
- `arg_si.pcr` `ec0c1edf292209f97a07d7f0a19dc99dc13a36f80ad25419d5105452812d4bfe`
- `arg_si.prf` `f184ab3dfc8478abef7e6ee9fa3922ec2951bc22ace621afb7321b54c73ce729`
- `arg_si.sum` `66457a12c718a3f41a9bfb04e4c470b1c86f4d43a8c361068c9cb1345b28f5c4`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Si": 1.0
  },
  "start_site_occupancies": {
    "1:Si": 1.0
  },
  "old_scales": [
    388.8488
  ],
  "new_scales": [
    388.8488
  ]
}
```
