# `pd-neut-tof_diamond-dream_basic` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-tof_diamond_dream`, pin `0d9f10e`. Mirrors the upstream page **`pd-neut-tof_diamond_dream`**. Instrument DREAM (ESS; McStas-simulated reduced data). Upstream it is a 15-parameter fit; here every parameter is fixed at that fit's values.

Every parameter is fixed (a forward calculation). fitted the scale alone once (`scale-fit.out`, full shifts; the exact input beside it as `.inp`) and fixed it at the value FullProf wrote to `.new`; nothing else moved.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `F d -3 m:1` | `C` | 16 / 192 | 1 | 0.08333 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 0.101178 | 14.5726 | 0.08333 | +1.23e-04 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'diamond\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 15.7 Rwp: 17.0 Rexp: 3.97 Chi2: 18.2`.

## Files (sha256)

- `diamond.bac` `8bd53aacb0a8bf36a3430e2d801e137a47b5040552a6a0e4ac82415e6b2b5ad7`
- `diamond.dat` `ee26f48918f03157cc66aa1e7033afe2623289e7ac43a2c15311c2d48048a456`
- `diamond.pcr` `08c1a10bffb432c901bc729e085fbae175a4c900dfd1324c830857984738c35f`
- `diamond.prf` `3587f1ec1d51d3820355f59556b16c4b6ad6c87d5215f0a3a50d93a73033edd4`
- `diamond.sum` `bfa1012564e31dd0101b2dd17399740e2dfb6b19b1fbbf785080d2af553936b1`
- `scale-fit.inp` `96b13c1f9edbf6ef3cc181a13c22ab59ebabb12d3b132dfafead17ef033c79b0`
- `scale-fit.out` `0d09d8459d8372f0e2f4dcb71778a1a6b40d4f717420ebc066e005b1e98b1233`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:C": 1.0
  },
  "start_site_occupancies": {
    "1:C": 1.0
  },
  "old_scales": [
    0.101178
  ],
  "new_scales": [
    14.57259
  ],
  "fit_out": "scale-fit.out",
  "fit_inputs": {
    "scale-fit.out": "scale-fit.inp"
  }
}
```
