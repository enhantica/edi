# `pd-neut-tof_ceo2-pearl_polynomial` -- FullProf verification project

**Verification twin** of [`knowledge/fitting/fullprof/pd-neut-tof_ceo2-pearl_polynomial/`](../../../fitting/fullprof/pd-neut-tof_ceo2-pearl_polynomial/PROVENANCE.md): that project's fitted state with every parameter fixed (all codes 0), the extraction output of this home (`Prf = 2`, `Ppl = 2`), and the scale fitted alone once, then fixed at the value `scale-fit.out` reports (its exact input beside it as `.inp`).

Origin of the fitting project: FullProf's own `Examples/` (`Ceo2_PEARL.pcr`; the data `Examples/CeO2_PEARL.dat`, renamed for the case-sensitive stem lookup; vendored by edi #74): CeO2, **polynomial background** (`Nba 0`), TOF. Instrument PEARL (ISIS; the `.dat` header).

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `F m 3 m` | `Ce` | 4 / 192 | 1 | 0.02083 |
| 1 | `F m 3 m` | `O` | 8 / 192 | 1 | 0.04167 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 3.67228 | 2115.25 | 0.041665 | -7.08e-05 |

Both sites move by 1/24 exactly (Ce 4a: 0.5 -> 4/192; O 8c: 1.0 -> 8/192), but FullProf serialises Occ to five decimals (0.02083, 0.04167), so the stored factors are 0.04166 and 0.04167 -- a 2.4e-4 split that is rounding, not physics. With the mean factor the scale is conserved to -7.1e-05.

The data are the `XYDATA` conversion of the fitting project (see its `PROVENANCE.md`).

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'Ceo2_PEARL\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 4.43 Rwp: 5.29 Rexp: 2.70 Chi2: 3.84`.

## Files (sha256)

- `Ceo2_PEARL.bac` `df6b978499d80deaf81cd491ed1a6a0d5883ce7b4986d9459d8b76df3722a75a`
- `Ceo2_PEARL.dat` `ceb04a9ff25422f194e85ff07fd579c8570d86015fa5dd844de8232f5c765df1`
- `Ceo2_PEARL.pcr` `2ad78a3429799daa170e9d0b34830232fb3d39c968916a58d936bbf6fa49f2dc`
- `Ceo2_PEARL.prf` `6f85898471988666434ecb12bf38f286cb7d11fe19d8e52ff6f07b6dcee0ae89`
- `Ceo2_PEARL.sum` `c9cab892b5b669c640d27f9ea9398885a87567933c4b311f24dc3cd347d9e901`
- `scale-fit.inp` `6cb9d8b1989a7c0c8b2f19147e14c1301e192579754081365881caa7707215db`
- `scale-fit.out` `2a2d32de565d2e9f76c803ae4708a5efdc9f396e769d110cc761929f5df0ef7b`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Ce": 1.0,
    "1:O": 1.0
  },
  "start_site_occupancies": {
    "1:Ce": 1.0,
    "1:O": 1.0
  },
  "old_scales": [
    3.672277
  ],
  "new_scales": [
    2115.251
  ],
  "fit_out": "scale-fit.out",
  "fit_inputs": {
    "scale-fit.out": "scale-fit.inp"
  },
  "nonuniform_change": "Both sites move by 1/24 exactly (Ce 4a: 0.5 -> 4/192; O 8c: 1.0 -> 8/192), but FullProf serialises Occ to five decimals (0.02083, 0.04167), so the stored factors are 0.04166 and 0.04167 -- a 2.4e-4 split that is rounding, not physics. With the mean factor the scale is conserved to -7.1e-05."
}
```
