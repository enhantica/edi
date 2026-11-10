# `pd-neut-cwl_lab6-11b-echidna_tch-fcj` -- FullProf fitting project

Origin: An **owner-authored fit** (confirmed 2026-09-24; vendored by edi #74): TCH pseudo-Voigt (x) FCJ axial divergence (`Npr 7`), CW neutrons, 11B-enriched LaB6, `S_L = D_L = 0.08` fixed, cell fixed at 4.156885 A. Data byte-identical to `pd-neut-cwl_lab6-echidna_11b`. Instrument ECHIDNA (run prefix `ECH`).

A **fitting** project: parameters free, `Pcr = 2`. Its occupancies already follow the convention (k = 1), so it is **not re-fit**: its inputs and every replaying output are byte-identical to its source. Rerunning FullProf over the `.pcr` converges and reproduces the `.prf`/`.sum` apart from the run-date and CPU-time lines.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P m -3 m` | `La` | 1 / 48 | 1 | 0.02083 |
| 1 | `P m -3 m` | `B` | 6 / 48 | 1 | 0.12500 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 141.082 | 141.082 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'ECH0030684_LaB6_1p622A\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 6.09 Rwp: 8.19 Rexp: 2.75 Chi2: 8.87`.

## Files (sha256)

- `ECH0030684_LaB6_1p622A.dat` `c41427269a36cad15936de9c11fea8c6719293a6e5acfe4146291efa8ed26cbc`
- `ECH0030684_LaB6_1p622A.pcr` `87662d7d37bac643d8c9aaac88417b1647ee3b905464c9c4b16012a8b4f37073`
- `ECH0030684_LaB6_1p622A.prf` `d5266003533cd7d90fcfce8cb3bad49de9aa5136773993de684fa945214228dc`
- `ECH0030684_LaB6_1p622A.sum` `3f180a9bc12686e71741afc921fd613e5544854172097fdf070d476cfeb181bf`

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
    141.0817
  ],
  "new_scales": [
    141.0817
  ]
}
```
