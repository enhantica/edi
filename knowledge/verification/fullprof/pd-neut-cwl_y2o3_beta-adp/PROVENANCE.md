# `pd-neut-cwl_y2o3_beta-adp` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder of the same name at `0d9f10e4` (last changed in `a29d6207`). Mirrors the upstream page **`pd-neut-cwl_Y2O3_beta-adp`**. No source names the instrument.

Every parameter is fixed (a forward calculation). The three sites carry anisotropic displacements as FullProf's
dimensionless beta (`exp(-h^T beta h)`). The occupancies already follow the convention (k = 1), so the project is
**not re-fit**: every file is the upstream bytes, the same bytes as `tests/fixtures/anisotropic_adps/fullprof/`.

**Version.** The upstream outputs were written by FullProf.2k 7.95 (Jan2023). FullProf.2k 8.40 (Feb2026-ILL), run
over the same `.pcr` and data, reproduces the `.bac` byte for byte and the calculated profile to within 4.72 counts
(0.0145 % of the point), the last printed digit; the `.sum` differs in its version line and printed precision. The
upstream bytes are kept, as gate 2 of the task asks.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8).

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `I a -3` | `Y1` | 24 / 48 | 1 | 0.50000 |
| 1 | `I a -3` | `Y2` | 8 / 48 | 1 | 0.16667 |
| 1 | `I a -3` | `O1` | 48 / 48 | 1 | 1.00000 |

## Displacements (`.pcr`, beta)

| site | Wyckoff | beta11 | beta22 | beta33 | beta12 | beta13 | beta23 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Y1` | 24d | 0.00303 | 0.00272 | 0.00295 | 0.00000 | 0.00000 | -0.00025 |
| `Y2` | 8b | 0.00304 | 0.00304 | 0.00304 | -0.00013 | -0.00013 | -0.00013 |
| `O1` | 48e | 0.00299 | 0.00310 | 0.00273 | -0.00007 | -0.00020 | -0.00001 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 1.0602 | 1.0602 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'y2o3\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp:  653.     Rwp:  708.     Rexp:    9.60                        Chi2: 0.544E+04`.

## Files (sha256)

- `y2o3.bac` `63c4b14fb2a38aaea0f753413aae03903e04a8045c914160f79ee955944593c5`
- `y2o3.dat` `0b3bc38ed073536f503a27776704853e735b6aaaaaa4bdbd4af8146bfd2bbf61`
- `y2o3.pcr` `42a7e816ac4609c00112dca15e4030b94688d53dbd802771dfcb645aa760e2e0`
- `y2o3.prf` `52d13e5a517015487ab4a1160fe9444679b8c314663a6225cffc76a49836ac9e`
- `y2o3.sum` `0ef96e229c309d4f3bb948f649c920194696063e0d67956f348eb35b2729868e`

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
