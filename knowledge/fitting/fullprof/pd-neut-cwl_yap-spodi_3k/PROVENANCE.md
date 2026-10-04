# `pd-neut-cwl_yap-spodi_3k` -- FullProf fitting project

Origin: **Owner-supplied** (found at `edi/tmp/fullprof/yap` on 2026-09-24, first proposed as edi PR #75, landed here instead): YAlO3 + Al2O3, **two phases**, CW neutrons. Instrument SPODI (FRM II). diffraction-lib carries no FullProf assets for its YAP tutorial; this project is what makes multiphase checkable. Committed here: the `.pcr` (from PR #75's `yap_3k.pcr`, occupancies restated and re-fit) and the data (PR #75's `YAP_3K.dat`, byte-identical, renamed to the `.pcr` stem because `fp2k` reads `<stem>.dat` by default). The by-products PR #75 also carried (`.cif`, `.hkl`, `.sym`, `.fst`, `.atm`, `.bvs`, `.cfl`, `.dis`, `_prof.cif`, `CFML_Restraints.tpcr`) are regenerable from these two files and are not carried.

A **fitting** project: parameters free, `Pcr = 2` (FullProf writes `.new`, never over the `.pcr`). restated the occupancies (below), moved the factor into the scale, and fitted every free parameter to convergence again: `full-fit.out` is that run (its first cycle carries the restated `Occ`; its exact input is `full-fit.inp`), and the committed `.pcr` is the `.new` it wrote, byte for byte. Rerunning FullProf over the committed `.pcr` converges and reproduces the committed `.prf`/`.sum` apart from the run-date and CPU-time lines.

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
| 1 | 27.897 | 27.8965 | 1 | -1.86e-05 |
| 2 | 0.04717 | 0.188768 | 0.4999963 | +4.49e-04 |

Phase 1 (YAlO3, P b n m, general multiplicity 8) already followed the convention (k = 1); phase 2 (Al2O3, R -3 c hexagonal, general multiplicity 36, not 18) moved by k = 1/2 on both sites. Per phase, the fit conserves scale x k^2: phase 1 -1.9e-5; phase 2 +4.6e-4 against the source value 0.04717, which is FullProf's own first-cycle step -- rerunning the UNCHANGED source .pcr gives 0.047191732, and 0.1887676 x 1/4 = 0.0471919 agrees with that to 4e-06.

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'yap_3k\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 3.21 Rwp: 4.08 Rexp: 1.30 Chi2: 9.88`.

## Files (sha256)

- `full-fit.inp` `a797d0ce9db456d0a6e7560ae4f045501a391d156f14a72def0ab8544c562b14`
- `full-fit.out` `3c5220fe7607cebaa23c76139adf4b9465df7f0adf6a1927dc04a4ce2c279d42`
- `yap_3k.dat` `ece2a18bf5b4bfcce3b215d5093199da3a63b7a6f963fb4789419b66d70b62e3`
- `yap_3k.pcr` `fc133b5a9ab27421cb85eccdb5160f3d5cc3232062bfb3597f4d9d154e5073b0`
- `yap_3k.prf` `0f35abf6ac9cd48de396a94bf0cd2a2d430b5cc8a5af7c433f7653179892fd7e`
- `yap_3k.sum` `ab4c99ba6ae1a7a1a8e086118fb40ccdba9bac90da01e44c7887376bf9b424c5`

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
    27.89648,
    0.1887676
  ],
  "fit_out": "full-fit.out",
  "fit_inputs": {
    "full-fit.out": "full-fit.inp"
  },
  "nonuniform_change": "Phase 1 (YAlO3, P b n m, general multiplicity 8) already followed the convention (k = 1); phase 2 (Al2O3, R -3 c hexagonal, general multiplicity 36, not 18) moved by k = 1/2 on both sites. Per phase, the fit conserves scale x k^2: phase 1 -1.9e-5; phase 2 +4.6e-4 against the source value 0.04717, which is FullProf's own first-cycle step -- rerunning the UNCHANGED source .pcr gives 0.047191732, and 0.1887676 x 1/4 = 0.0471919 agrees with that to 4e-06."
}
```
