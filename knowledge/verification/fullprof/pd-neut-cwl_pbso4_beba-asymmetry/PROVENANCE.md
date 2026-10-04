# `pd-neut-cwl_pbso4_beba-asymmetry` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-cwl_pbso4_beba-asymmetry`, pin `0d9f10e4`. Mirrors the upstream page **`pd-neut-cwl_PbSO4_beba-asymmetry`**. No source names the instrument, so the id carries none.

**Authored, not upstream bytes, in one value.** The upstream `.pcr` applies the Bérar-Baldinozzi correction below `AsyLim` = 160°. The owner's direction compares every Bérar-Baldinozzi variant at ONE limit, 180°, so the `.pcr` here is the upstream file (sha256 `b4f1ec62dd50fc73a48ec66bf2c285a4b865a7415d519390aea1ce0c45827e1b`) with `AsyLim` 160.00 → 180.00 and nothing else changed, and the `.prf`/`.sum`/`.bac` were regenerated ONCE from it at authoring time — the one run is the tests lane's, committed with its provenance in crysta `tests/fixtures/c11_t57_profiles/beba/fullprof180/` and copied here byte-identically (an independent second run differed only in its timestamps); FullProf's `.out` confirms *"Asymmetry correction for angles lower than 180.000 degrees"*. Against the upstream 160° profile the calculated intensities differ only near 155° (max 0.02 counts, relative L2 3×10⁻⁶). The `.dat` is the upstream bytes. No gate runs fp2k.

Every parameter is fixed (a forward calculation); the occupancies already follow the convention (k = 1). **This is not the Bérar-Baldinozzi oracle**: FullProf's P1–P4 are not in the paper's convention (as inferred from its output in diffraction-lib issue 166), so the page's oracle is cryspy and this profile is its documented divergence record.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8).

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
| 1 | 1.46382 | 1.46382 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'pbso4\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 7.23 Rwp: 6.84 Rexp: 3.64 Chi2: 3.54`.

## Files (sha256)

- `pbso4.bac` `a7ee9ccd9fd7b10713495817b715b87b38cf2cb97c561750b4e09a83eb34103a`
- `pbso4.dat` `637bfde3bb1adb24045fb688c2a0cdfd424bf7bc9956f267a11053ba82a944e2`
- `pbso4.pcr` `23791b9d6564fc5d3e2840d3fb6dced4fbbe7ab480e0915aa1434f3886559c65`
- `pbso4.prf` `071e2b81921e0c47b12819db5a65ec3cc2efa92d914bb46746cb7c3faa35107b`
- `pbso4.sum` `42128272cb26869839a4b7a406c8a34e38c0f70ddb83eb6f671246587e65158b`

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
    1.463815
  ],
  "new_scales": [
    1.463815
  ]
}
```
