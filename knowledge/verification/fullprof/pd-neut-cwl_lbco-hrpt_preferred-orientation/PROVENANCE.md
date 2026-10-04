# `pd-neut-cwl_lbco-hrpt_preferred-orientation` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-cwl_lbco_preferred-orientation`, pin `0d9f10e4` (`0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf`, on `master`; the corpus pin `39ada82c` carries an earlier `.prf`/`.sum` of the same inputs). Mirrors the upstream page **`pd-neut-cwl_LBCO_preferred-orientation`**. Instrument HRPT (PSI; crysta fitting case `lbco-hrpt`).

Every parameter is fixed (a forward calculation). The project is `pd-neut-cwl_lbco-hrpt_basic` with March–Dollase preferred orientation switched on (`Nor = 1`, `Pref1 = 1.2`, `Pref2 = 0.3`, axis `Pr1 Pr2 Pr3 = 0 0 1`); its `lbco.dat` and `lbco.bac` are byte-identical to that project's. Its occupancies already follow the convention (k = 1), so it is **not re-fit**: all five files are **inherited byte-identical from upstream** — none is authored here, and FullProf was not re-run for this copy.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8).

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

FullProf.2k 8.40 (Feb2026-ILL): `printf 'lbco\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line recorded in the inherited `lbco.sum`: `=> Rp: 5.84 Rwp: 7.39 Rexp: 6.36 Chi2: 1.35`.

## Files (sha256)

- `lbco.bac` `07f4b0b0371334c6b67bfebca0f75374e2e33685fdbf87ee877d673335833d03`
- `lbco.dat` `83c7f3d27d2e254367dd7dc3730261b9a5ebb811baaeed01fde050a7ba99be24`
- `lbco.pcr` `5759c765e3050ca6298ad7a3f5cbeb93cc76991bd4f9c36b4e39dcaffeda4403`
- `lbco.prf` `35dc25fbc63948be198b7ab7274c7e9ba98621bd796edc8c87d8a8e8909df89f`
- `lbco.sum` `1a01f3a87c4eca5eabed96dcf7040f339ded66f09a77b3d02fdeff3713807275`

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
