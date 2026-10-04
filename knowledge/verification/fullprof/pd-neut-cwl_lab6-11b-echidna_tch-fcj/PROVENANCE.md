# `pd-neut-cwl_lab6-11b-echidna_tch-fcj` -- FullProf verification project

**Verification twin** of [`knowledge/fitting/fullprof/pd-neut-cwl_lab6-11b-echidna_tch-fcj/`](../../../fitting/fullprof/pd-neut-cwl_lab6-11b-echidna_tch-fcj/PROVENANCE.md): that project's fitted state with every parameter fixed (all codes 0), the extraction output of this home (`Prf = 2`, `Ppl = 2`), and the scale fitted alone once, then fixed at the value `scale-fit.out` reports (its exact input beside it as `.inp`).

Origin of the fitting project: An **owner-authored fit** (confirmed 2026-09-24; vendored by edi #74): TCH pseudo-Voigt (x) FCJ axial divergence (`Npr 7`), CW neutrons, 11B-enriched LaB6, `S_L = D_L = 0.08` fixed, cell fixed at 4.156885 A. Data byte-identical to `pd-neut-cwl_lab6-echidna_11b`. Instrument ECHIDNA (run prefix `ECH`).

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P m -3 m` | `La` | 1 / 48 | 1 | 0.02083 |
| 1 | `P m -3 m` | `B` | 6 / 48 | 1 | 0.12500 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 141.082 | 141.07 | 1 | -8.22e-05 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'ECH0030684_LaB6_1p622A\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 6.09 Rwp: 8.19 Rexp: 2.76 Chi2: 8.82`.

## Files (sha256)

- `ECH0030684_LaB6_1p622A.bac` `90bcc0893ba9d5d554b305a2457a632216a92500c17351f98e0ed341deca6dbd`
- `ECH0030684_LaB6_1p622A.dat` `c41427269a36cad15936de9c11fea8c6719293a6e5acfe4146291efa8ed26cbc`
- `ECH0030684_LaB6_1p622A.pcr` `91e91b712bf08bda39b58edc826fd0ca774e231008f1cef9bc43ee7dde8f6fcd`
- `ECH0030684_LaB6_1p622A.prf` `f43ba2e6db5f856b859037fa3c31ae843bfc0c7d31caf3c8fe391e682930c68e`
- `ECH0030684_LaB6_1p622A.sum` `39b063fc724f84fff428876b6531f8581371161c8d91a050582241a34bd2d107`
- `scale-fit.inp` `cbc7c1cbcee7a39b7e9e41f1fee2850293f655dc72a3021448607100169096c8`
- `scale-fit.out` `2d10c0e979ba8336d6c9e8c7aa2caf71e6ff6a68e0b7369ddff3f1170cfe7a2d`

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
    141.0701
  ],
  "fit_out": "scale-fit.out",
  "fit_inputs": {
    "scale-fit.out": "scale-fit.inp"
  }
}
```
