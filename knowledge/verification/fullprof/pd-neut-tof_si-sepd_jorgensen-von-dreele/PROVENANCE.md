# `pd-neut-tof_si-sepd_jorgensen-von-dreele` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-tof_si_jorgensen-von-dreele`, pin `39ada82c` (`.dat`/`.bac`/`.irf` at `0d9f10e`). Mirrors the upstream page **`pd-neut-tof_Si_jorgensen-von-dreele`**. Instrument SEPD (crysta fitting case `si-sepd`).

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

FullProf.2k 8.40 (Feb2026-ILL): `printf 'arg_si\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 8.17 Rwp: 5.98 Rexp: 3.66 Chi2: 2.66`.

## Files (sha256)

- `TOF_irf_file.irf` `82e7d3f808011332d06eeeff35253b6f3931ff5979a73d04bb268af9568f926a`
- `arg_si.bac` `5288467734eff47d8fb9d0967c25b15ce94d90f9680926e07b4d555e8052a56c`
- `arg_si.dat` `261b9e2846b0b159dab906e144d5f05e36cdad36a42edf1df848720043568e5b`
- `arg_si.pcr` `e930b99b7bd150fa93a92fa89d7a5b9870624f8465eacb036d3b7e893dfd9851`
- `arg_si.prf` `e80cbf2650f8ae80a7bd2cac4213e1e36d38be25ecf849d3b1a5da82649771b1`
- `arg_si.sum` `e773630034a6bbbafe7d14584d4c1a6c330af67bba0ba67fa752b8bd1a8464e9`

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
