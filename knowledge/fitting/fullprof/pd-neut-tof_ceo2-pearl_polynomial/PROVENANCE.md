# `pd-neut-tof_ceo2-pearl_polynomial` -- FullProf fitting project

Origin: FullProf's own `Examples/` (`Ceo2_PEARL.pcr`; the data `Examples/CeO2_PEARL.dat`, renamed for the case-sensitive stem lookup; vendored by edi #74): CeO2, **polynomial background** (`Nba 0`), TOF. Instrument PEARL (ISIS; the `.dat` header).

A **fitting** project: parameters free, `Pcr = 2` (FullProf writes `.new`, never over the `.pcr`). restated the occupancies (below), moved the factor into the scale, and fitted every free parameter to convergence again: `full-fit.out` is that run (its first cycle carries the restated `Occ`; its exact input is `full-fit.inp`), and the committed `.pcr` is the `.new` it wrote, byte for byte. Rerunning FullProf over the committed `.pcr` converges and reproduces the committed `.prf`/`.sum` apart from the run-date and CPU-time lines.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8). FullProf's TOF extinction term scales with |F|^2, so a restated phase's `Extinc` moves by 1/k^2 with the scale.

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `F m 3 m` | `Ce` | 4 / 192 | 1 | 0.02083 |
| 1 | `F m 3 m` | `O` | 8 / 192 | 1 | 0.04167 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 3.67228 | 2115.27 | 0.041665 | -5.99e-05 |

Both sites move by 1/24 exactly (Ce 4a: 0.5 -> 4/192; O 8c: 1.0 -> 8/192), but FullProf serialises Occ to five decimals (0.02083, 0.04167), so the stored factors are 0.04166 and 0.04167 -- a 2.4e-4 split that is rounding, not physics. With the mean factor the scale is conserved to -6.0e-05.


## The PEARL data as plain X-Y-sigma (the chi2 explanation)

FullProf's RALF reader (`Ins = 12`) weights this file with sigma 100x too large relative to the
intensity it normalises, so the source fit printed Rexp 268.76 % and chi2 4.7e-4. The data are
now `XYDATA` (`Ins = 10`), written by `tools/fullprof/ralf_to_xydata.py` from the original RALF
bytes (`Ceo2_PEARL.ralf`, kept here, sha256 below) and the `.prf` of a FullProf run over them:
X = RALF TOF / 32 exactly; Y = the observed intensity FullProf read from the RALF file, taken from
the `Prf = 2` (IGOR) print of a RALF run -- its per-point normalisation I x 32 / (10 dt), dt the
forward bin width, to the print's 0.01; sigma = RALF sigma x Y / I for that point. All 2524 RALF
points are kept: FullProf does not read the last one (it has no following bin edge), so its Y uses
dt = the header's dt/t (0.0010) x TOF, the rule every other log-binned width follows to one raw unit
(about 1.6e-3 relative uncertainty for that point) -- the one value not produced by FullProf, and
outside the fitted TOF range. The same fit on the converted file prints Rp 4.43, Rwp 5.29, **Rexp
2.69**, **chi2 3.88** -- Rexp now agrees with the file's own sigma; later fits of this case inherit this explanation.


## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'Ceo2_PEARL\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 4.43 Rwp: 5.29 Rexp: 2.69 Chi2: 3.88`.

## Files (sha256)

- `Ceo2_PEARL.dat` `ceb04a9ff25422f194e85ff07fd579c8570d86015fa5dd844de8232f5c765df1`
- `Ceo2_PEARL.pcr` `12455e9758b27039ed61f307efbfc37cdd79803b0ab0f2e7687419ac2fecb767`
- `Ceo2_PEARL.prf` `1a72ca5e2bb6bf56ea346b9e2d8cc15ce96d452cbd958658d1fd3326224a9848`
- `Ceo2_PEARL.ralf` `7397e5c44f2193f86e49ac8680d5c3bd2499bafbb955e3698335d49693335ca7`
- `Ceo2_PEARL.sum` `4abca556b316be6556cbb56027ef73a4c377305ce182250814d95ac9c5c8a141`
- `full-fit.inp` `5dba3b3123e85d6c28eeb279243a9a8c5bdea9300439f5a634af889caa244c56`
- `full-fit.out` `1de8ce0089fa0903754a52052f6d406446b5e138d22ad3f8942fcee1c1c46d8d`

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
    2115.274
  ],
  "fit_out": "full-fit.out",
  "fit_inputs": {
    "full-fit.out": "full-fit.inp"
  },
  "nonuniform_change": "Both sites move by 1/24 exactly (Ce 4a: 0.5 -> 4/192; O 8c: 1.0 -> 8/192), but FullProf serialises Occ to five decimals (0.02083, 0.04167), so the stored factors are 0.04166 and 0.04167 -- a 2.4e-4 split that is rounding, not physics. With the mean factor the scale is conserved to -6.0e-05."
}
```
