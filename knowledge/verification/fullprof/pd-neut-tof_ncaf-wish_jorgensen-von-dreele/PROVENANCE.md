# `pd-neut-tof_ncaf-wish_jorgensen-von-dreele` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-tof_ncaf_jorgensen-von-dreele` (`.pcr` at pin `39ada82c`, `.gss`/`.irf` at `0d9f10e`, byte-identical between the two). Mirrors the upstream page **`pd-neut-tof_NCAF_jorgensen-von-dreele`**. Instrument WISH (ISIS; crysta fitting case `ncaf-wish`). The `.pcr` is multi-pattern, so FullProf 8.40 writes `tmpl_one_bank_1.prf` / `_1.bac`; they are committed, bytes unchanged, as `tmpl_one_bank.prf` / `.bac`, the names upstream and the page use.

Every parameter is fixed (a forward calculation). Its occupancies already follow the convention (k = 1), so it is **not re-fit**: its inputs and every replaying output are byte-identical to its source (the owner's refit is owed only where the occupancy convention changes the scale).

**One output regenerated**: the upstream `tmpl_one_bank.prf` did not replay -- a FullProf 8.40 run over the same `.pcr`, `.gss` and `.irf` differs in the last printed digit of `Icalc`/`Diff` on 518 rows (at most 0.21 counts). It is regenerated from the unchanged inputs (FullProf names it `tmpl_one_bank_1.prf`; committed under the upstream name); the `.pcr`, data, `.irf`, `.sum` and `.bac` are the upstream bytes and replay as committed.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `I 21 3` | `Ca1` | 12 / 24 | 1 | 0.50000 |
| 1 | `I 21 3` | `Al1` | 8 / 24 | 1 | 0.33333 |
| 1 | `I 21 3` | `Na1` | 8 / 24 | 1 | 0.33333 |
| 1 | `I 21 3` | `F1` | 24 / 24 | 1 | 1.00000 |
| 1 | `I 21 3` | `F2` | 24 / 24 | 1 | 1.00000 |
| 1 | `I 21 3` | `F3` | 8 / 24 | 1 | 0.33333 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 36.1737 | 36.1737 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'tmpl_one_bank\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 7.48 Rwp: 8.27 Rexp: 2.12 Chi2: 15.2`.

## Files (sha256)

- `55025-5_6raw.gss` `7562b86085370d5aa0ce3f866bd1164c437308c4e0394de895f6c28ececd478d`
- `TOF_irf_file.irf` `97c1e504407e3229af5c618e0fe8c49fdf8ab3ecd79a133939e492eb6d01243a`
- `tmpl_one_bank.bac` `5cd8fb9dbe7d2419082becadf95c7acbbba919e501cc711ef3e424897e420df9`
- `tmpl_one_bank.pcr` `9ad39c37848fd34af54ba8a3b054dad2f98b153a1ae9f5f4699b9d432f93acb5`
- `tmpl_one_bank.prf` `f006e845f18bd73044b229f17706ef1fcae11abc5e112b4485c346e07537d4f1`
- `tmpl_one_bank.sum` `ee3928bfdceffc1c869fe45e8d2f4c3fe1e1d2e2c6cca07dd5e60ffbfd8b817c`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Ca1": 1.0,
    "1:Al1": 1.0,
    "1:Na1": 1.0,
    "1:F1": 1.0,
    "1:F2": 1.0,
    "1:F3": 1.0
  },
  "start_site_occupancies": {
    "1:Ca1": 1.0,
    "1:Al1": 1.0,
    "1:Na1": 1.0,
    "1:F1": 1.0,
    "1:F2": 1.0,
    "1:F3": 1.0
  },
  "old_scales": [
    36.17374
  ],
  "new_scales": [
    36.17374
  ]
}
```
