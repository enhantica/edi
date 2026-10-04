# `pd-neut-cwl_y2o3_isotropic-adp` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder of the same name, pin `39ada82c`. Mirrors the upstream page **`pd-neut-cwl_Y2O3_isotropic-adp`**. No source names the instrument. The data file is upstream `y2o3.dat`, renamed to the `.pcr` stem because `fp2k` reads `<stem>.dat` by default.

Every parameter is fixed (a forward calculation). Its occupancies already follow the convention (k = 1), so it is **not re-fit**: its inputs and every replaying output are byte-identical to its source (the owner's refit is owed only where the occupancy convention changes the scale).

**One output regenerated**: the upstream `y2o3_isotropic_adp.sum` did not replay -- it stops at line 27, where a FullProf 8.40 run over the same `.pcr` and data continues for 194 more lines (angular range, phase and final-cycle blocks). It is regenerated from the unchanged inputs; the `.pcr`, data, `.prf` and `.bac` are the upstream bytes and replay as committed.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `I a -3` | `Y1` | 24 / 48 | 1 | 0.50000 |
| 1 | `I a -3` | `Y2` | 8 / 48 | 1 | 0.16667 |
| 1 | `I a -3` | `O1` | 48 / 48 | 1 | 1.00000 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 1.0602 | 1.0602 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'y2o3_isotropic_adp\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 49.0 Rwp: 121. Rexp: 1.24 Chi2: 0.950E+04`.

## Files (sha256)

- `y2o3_isotropic_adp.bac` `a0e3fbdd25c98e65cd3123f9ec445015a4ec14a57707026bb23e6986a8e9e3eb`
- `y2o3_isotropic_adp.dat` `0b3bc38ed073536f503a27776704853e735b6aaaaaa4bdbd4af8146bfd2bbf61`
- `y2o3_isotropic_adp.pcr` `52f92a16e31a3745cf19c0ceee0c18f2180edbb34f0bae94fe3f27e9b637edf2`
- `y2o3_isotropic_adp.prf` `7b70793eb5b3556de446371b98876c62dfff5775dc5d8e41ef80ac5eca82b2f5`
- `y2o3_isotropic_adp.sum` `721fea6c55fd689ffb0fddfdc489bc5f122305a8db701b2ea9904e2ead91f582`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Y1": 1.0,
    "1:Y2": 1.0,
    "1:O1": 1.0
  },
  "start_site_occupancies": {
    "1:Y1": 1.0,
    "1:Y2": 1.0,
    "1:O1": 1.0
  },
  "old_scales": [
    1.0602
  ],
  "new_scales": [
    1.0602
  ]
}
```
