# `pd-neut-tof_cecoal-polaris_chebyshev` -- FullProf verification project

**Verification twin** of [`knowledge/fitting/fullprof/pd-neut-tof_cecoal-polaris_chebyshev/`](../../../fitting/fullprof/pd-neut-tof_cecoal-polaris_chebyshev/PROVENANCE.md): that project's fitted state with every parameter fixed (all codes 0), the extraction output of this home (`Prf = 2`, `Ppl = 2`), and the scale fitted alone once, then fixed at the value `scale-fit.out` reports (its exact input beside it as `.inp`).

Origin of the fitting project: FullProf's own `Examples/` (`cecoal.pcr`, `cecoal.dat` byte-identical; vendored by edi #74): CeCoAl3, **Chebyshev background** (`Nba -5`), TOF, JvD profile. Instrument POLARIS (ISIS; the `.dat` header).

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P m m a` | `Ce` | 2 / 8 | 1 | 0.25000 |
| 1 | `P m m a` | `Co` | 2 / 8 | 1 | 0.25000 |
| 1 | `P m m a` | `Al1` | 2 / 8 | 1 | 0.25000 |
| 1 | `P m m a` | `Al2` | 2 / 8 | 1 | 0.25000 |
| 1 | `P m m a` | `Al3` | 4 / 8 | 1.02066 | 0.51033 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 1041.19 | 16660.1 | 0.2500002 | +6.41e-05 |

**Al3.** Al3 sits on 4j (x, 1/2, z) of P m m a, multiplicity 4 of 8; the other four sites are 2-fold. The source file normalises Occ to the 2-fold sites (Occ = site occupancy x m / 2), so its 2.04131 is a site occupancy of 1.020655 -- a fitted value (Occ is free, code 91) within its uncertainty of full occupancy, not a structural feature. Restated as 1.020655 x 4/8 = 0.5103275, the same factor 1/4 as every other site.

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'cecoal\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 3.28 Rwp: 5.34 Rexp: 3.99 Chi2: 1.79`.

## Files (sha256)

- `cecoal.bac` `2b3d1a38b6c44d836d33bcb5021e32f964d923cfab66b59fc686492e9afe003f`
- `cecoal.dat` `3c702bc31c5c6b435a3cb8d4b72cde2495a6a521ce336fd1be20e4df6c429790`
- `cecoal.pcr` `7935162473b190883432bb92a6a6e7881afa60b12eb23d53d1739886f16fe3ee`
- `cecoal.prf` `eb184a7c096953d3279cc20eba1f148911c345ad5f7a4386dc8499e6dc8924fb`
- `cecoal.sum` `3411164aae7c0fa23ad92da09bda68bf852c0556a8f1f0c8c110021c3451e6d1`
- `scale-fit.inp` `99cde05951f8efc5bef3b9375cb844520c1a08ee7325d29d0d689960c7151818`
- `scale-fit.out` `0757486722fbbf7bad315833ce5a6d2136f0c41347b39f90ae3cbb9292fa0683`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Ce": 1.0,
    "1:Co": 1.0,
    "1:Al1": 1.0,
    "1:Al2": 1.0,
    "1:Al3": 1.02066
  },
  "start_site_occupancies": {
    "1:Ce": 1.0,
    "1:Co": 1.0,
    "1:Al1": 1.0,
    "1:Al2": 1.0,
    "1:Al3": 1.02066
  },
  "old_scales": [
    1041.189
  ],
  "new_scales": [
    16660.06
  ],
  "fit_out": "scale-fit.out",
  "fit_inputs": {
    "scale-fit.out": "scale-fit.inp"
  },
  "al3_explanation": "Al3 sits on 4j (x, 1/2, z) of P m m a, multiplicity 4 of 8; the other four sites are 2-fold. The source file normalises Occ to the 2-fold sites (Occ = site occupancy x m / 2), so its 2.04131 is a site occupancy of 1.020655 -- a fitted value (Occ is free, code 91) within its uncertainty of full occupancy, not a structural feature. Restated as 1.020655 x 4/8 = 0.5103275, the same factor 1/4 as every other site."
}
```
