# `pd-neut-tof_si-sepd_jorgensen` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-tof_si_jorgensen`, pin `39ada82c` (`.dat`/`.bac`/`.irf` at `0d9f10e`). Mirrors the upstream page **`pd-neut-tof_Si_jorgensen`**. Instrument SEPD (Argonne IPNS; crysta fitting case `si-sepd`).

Every parameter is fixed (a forward calculation). Its occupancies already follow the convention (k = 1), so it is **not re-fit**: its inputs and every replaying output are byte-identical to its source (the owner's refit is owed only where the occupancy convention changes the scale).

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `F d -3 m` | `Si` | 8 / 192 | 1 | 0.04167 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 381.315 | 381.315 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'arg_si\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 8.73 Rwp: 6.36 Rexp: 3.66 Chi2: 3.02`.

## Files (sha256)

- `TOF_irf_file.irf` `ce7205ce1af4ae1ac1cc284bb7db2d3662aa2507c4ff9fa5d561592015441ba7`
- `arg_si.bac` `c57797282df81c4fc93a6a834991f20c3e8b1cd26ef8b1864b57ddbdbae59633`
- `arg_si.dat` `261b9e2846b0b159dab906e144d5f05e36cdad36a42edf1df848720043568e5b`
- `arg_si.pcr` `234fe84471a18590e426a3c7aa2db651804827cce6f7b9659b0d80b1e1b82698`
- `arg_si.prf` `0f5bf0ac01390d394ec6bd8f8c6f503a66c18f997bfd78e01b8415a5486fbc36`
- `arg_si.sum` `7c4edf6bc43c3041c958d24c5ae4282c5ec23dcd43655f0218f58d77b1a4103b`

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
    381.3153
  ],
  "new_scales": [
    381.3153
  ]
}
```
