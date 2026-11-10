# `pd-neut-cwl_yap-spodi_3k` -- FullProf verification project

**Verification twin** of [`knowledge/fitting/fullprof/pd-neut-cwl_yap-spodi_3k/`](../../../fitting/fullprof/pd-neut-cwl_yap-spodi_3k/PROVENANCE.md): that project's fitted state with every parameter fixed (all codes 0), the extraction output of this home (`Prf = 2`, `Ppl = 2`), and the scale fitted alone once, then fixed at the value `scale-fit-1.out, scale-fit-2.out` reports (its exact input beside it as `.inp`).

Origin of the fitting project: **Owner-supplied** (found at `edi/tmp/fullprof/yap` on 2026-09-24, first proposed as edi PR #75, landed here instead): YAlO3 + Al2O3, **two phases**, CW neutrons. Instrument SPODI (FRM II). diffraction-lib carries no FullProf assets for its YAP tutorial; this project is what makes multiphase checkable. Committed here: the `.pcr` (from PR #75's `yap_3k.pcr`, occupancies restated and re-fit) and the data (PR #75's `YAP_3K.dat`, byte-identical, renamed to the `.pcr` stem because `fp2k` reads `<stem>.dat` by default). The by-products PR #75 also carried (`.cif`, `.hkl`, `.sym`, `.fst`, `.atm`, `.bvs`, `.cfl`, `.dis`, `_prof.cif`, `CFML_Restraints.tpcr`) are regenerable from these two files and are not carried.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `P b n m` | `Y` | 4 / 8 | 1 | 0.50000 |
| 1 | `P b n m` | `Al` | 4 / 8 | 1 | 0.50000 |
| 1 | `P b n m` | `O1` | 4 / 8 | 1 | 0.50000 |
| 1 | `P b n m` | `O2` | 8 / 8 | 1 | 1.00000 |
| 2 | `R -3 c` | `Al1` | 12 / 36 | 1 | 0.33333 |
| 2 | `R -3 c` | `O1` | 18 / 36 | 1 | 0.50000 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 27.897 | 27.8962 | 1 | -2.98e-05 |
| 2 | 0.04717 | 0.189141 | 0.4999963 | +2.43e-03 |

Phase 1 (YAlO3, P b n m, general multiplicity 8) already followed the convention (k = 1); phase 2 (Al2O3, R -3 c hexagonal, general multiplicity 36, not 18) moved by k = 1/2 on both sites. Per phase, the fit conserves scale x k^2: phase 1 -1.9e-5; phase 2 +4.6e-4 against the source value 0.04717, which is FullProf's own first-cycle step -- rerunning the UNCHANGED source .pcr gives 0.047191732, and 0.1887676 x 1/4 = 0.0471919 agrees with that to 4e-06.

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'yap_3k\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 3.21 Rwp: 4.08 Rexp: 1.31 Chi2: 9.69`.

## Files (sha256)

- `scale-fit-1.inp` `e74f2d068cdf33c711b5e89365563aa0beb27829d0ffd17656a774002dd5516e`
- `scale-fit-1.out` `1e7c470aad0d93200ddca4f9ba2be7c97ee2752a8636bed9b2f4d5fe0b2fcedf`
- `scale-fit-2.inp` `7e3f8a398e0253ff346f383a78d87829002fd6d6df5fc166942829abc0ffd85b`
- `scale-fit-2.out` `e98b60c4ba7d145a464840fe9a5be74142d8e9493978190847c768ecb0b258f7`
- `yap_3k.bac` `8225e493c938d0df1f7ca8f9428d9717d73899ff11ed480a963805f251f64e68`
- `yap_3k.dat` `ece2a18bf5b4bfcce3b215d5093199da3a63b7a6f963fb4789419b66d70b62e3`
- `yap_3k.pcr` `3bb32a144ff8c39c9dfedef711edf18f2ba6575191ef4b64414432c8efae94d1`
- `yap_3k.prf` `9c8ab87411d8d7229848297a7777d0a98a56ecb48d36603abb475aa420202291`
- `yap_3k.sum` `71116c17354039bcecd6493a9421a531062e1b0eb5eea951a232853df1ee1132`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Y": 1.0,
    "1:Al": 1.0,
    "1:O1": 1.0,
    "1:O2": 1.0,
    "2:Al1": 1.0,
    "2:O1": 1.0
  },
  "start_site_occupancies": {
    "1:Y": 1.0,
    "1:Al": 1.0,
    "1:O1": 1.0,
    "1:O2": 1.0,
    "2:Al1": 1.0,
    "2:O1": 1.0
  },
  "old_scales": [
    27.897,
    0.04717
  ],
  "new_scales": [
    27.89617,
    0.1891413
  ],
  "fit_out": [
    "scale-fit-1.out",
    "scale-fit-2.out"
  ],
  "fit_inputs": {
    "scale-fit-1.out": "scale-fit-1.inp",
    "scale-fit-2.out": "scale-fit-2.inp"
  },
  "nonuniform_change": "Phase 1 (YAlO3, P b n m, general multiplicity 8) already followed the convention (k = 1); phase 2 (Al2O3, R -3 c hexagonal, general multiplicity 36, not 18) moved by k = 1/2 on both sites. Per phase, the fit conserves scale x k^2: phase 1 -1.9e-5; phase 2 +4.6e-4 against the source value 0.04717, which is FullProf's own first-cycle step -- rerunning the UNCHANGED source .pcr gives 0.047191732, and 0.1887676 x 1/4 = 0.0471919 agrees with that to 4e-06."
}
```
