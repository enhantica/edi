# `pd-neut-tof_si-sepd_ikeda-carpenter` -- FullProf verification project

**Verification twin** of [`knowledge/fitting/fullprof/pd-neut-tof_si-sepd_ikeda-carpenter/`](../../../fitting/fullprof/pd-neut-tof_si-sepd_ikeda-carpenter/PROVENANCE.md): that project's fitted state with every parameter fixed (all codes 0), the extraction output of this home (`Prf = 2`, `Ppl = 2`), and the scale fitted alone once, then fixed at the value `scale-fit.out` reports (its exact input beside it as `.inp`).

Origin of the fitting project: Built by the conductor from FullProf's `Examples/arg_si.pcr` (vendored by edi #74): profile switched to **Ikeda-Carpenter (x) pseudo-Voigt** (`Npr 13`), the four IC shape terms fixed (alph0 0, alph1 0.879, beta0 21.668, kappa 75.321), the author's own 16 parameters free. Data `Examples/arg_si.dat`, renamed to the stem. Instrument SEPD (crysta fitting case `si-sepd`).

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `F d 3 m` | `Si` | 8 / 192 | 1 | 0.04167 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 0.680728 | 392.032 | 0.04167 | -1.25e-05 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'arg_si_ic\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 8.42 Rwp: 5.52 Rexp: 3.66 Chi2: 2.27`.

## Files (sha256)

- `arg_si_ic.bac` `6c6b6b040c9bb6f75ea735d3ed0636cb1e02f5e84f20d7d192eb5a06782bcddb`
- `arg_si_ic.dat` `261b9e2846b0b159dab906e144d5f05e36cdad36a42edf1df848720043568e5b`
- `arg_si_ic.pcr` `939daa310d81250da1bd28e726ed23178a56b230a5565f7fe0e0cf1b79825b3d`
- `arg_si_ic.prf` `0208f8f8381d574be25297d678c911410e1ac4f62ccc84e7d7508005c1edc3e5`
- `arg_si_ic.sum` `6499767b1a5a4da790f7e798e3c53f2230a2fba6717dd142ce092176f6245b9b`
- `scale-fit.inp` `c216e86aa823ea3070165670e4dda24c2b5e38b1cbb926cf0d981f5d9c7e78d4`
- `scale-fit.out` `34c8a55e3697ae3c6f73bd777f80681be9091011c3b3c135ae384eb8ae2a0be9`

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
    0.6807285
  ],
  "new_scales": [
    392.032
  ],
  "fit_out": "scale-fit.out",
  "fit_inputs": {
    "scale-fit.out": "scale-fit.inp"
  }
}
```
