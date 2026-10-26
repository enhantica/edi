# `pd-neut-xray-cwl_pbso4-d1a-lab` -- FullProf fit with the asymmetry off

The fit of `../fit.pcr` with the four Bérar-Baldinozzi coefficients fixed at 0, the reference for every shared value of
this example. FullProf's Bérar-Baldinozzi form and edi's differ, and no mapping of the coefficients makes them agree, so
the full model is compared on R<sub>wp</sub> and the number of free parameters only (`../reference.json`), and every
other value here, against edi's fit of the project with the same coefficients fixed (the `asymmetry-off` variant of
the example's `expected.json`).

`fit.pcr` and its data were written by `tests/fixtures/example_catalogue/fullprof_inputs.py` from a copy of
`docs/user/cli/pd-neut-xray-cwl_pbso4-d1a-lab/project` whose four coefficients are `0` and fixed. It differs from `../fit.pcr` only in
those coefficients' codes, now 0, the codes numbered after them, renumbered down by the codes removed, and the refined-parameter count,
51 -> 45. FullProf.2k 8.40 (`fp2k` sha256 `b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`) ran once, when this
reference was written, as `printf 'fit\n\n' | fp2k` in a copy of this folder; no check runs it. Convergence at
cycle 79; pooled R<sub>wp</sub> 8.94 % (with the asymmetry:
5.76 %).

FullProf's lines (`fit.sum`):

```text
=> Rp:  4.16     Rwp:  5.29     Rexp:    1.94 Chi2:  7.41      L.S. refinement
=> Rp:  12.0     Rwp:  15.6     Rexp:    4.88 Chi2:  10.3      L.S. refinement
```

`reference.json` records the free parameters' values and uncertainties from `fit.out` and the edi name each code
belongs to.

## Files (sha256)

- `fit.pcr` `07022611dc2dd72bf027eba3cc2fecce1cde9138b1610d47904a01efb8fa7477`
- `fit_1.dat` `9719cfa28a7ef039147580bc13ff192b6cff618ae93cc9f9ad1ffab0a536a2d8`
- `fit_2.dat` `e803994d3eaa1e2732d2902e6a535195c9ba2a6eef014b1e9dc4464fea70271b`
- `fit.out` `8db8a5eaa5630d63fb275d112f0b9dc5c6a9852e7b4316990be4ee47f649fcbd`
- `fit.sum` `04a1ac1437e225266f435b26fdcd3325240e62a3a68ff9b19df1a1fe3775f289`
- `reference.json` `2e5c71dcc9c20184f55b8e72f0fdfa6aa09e9d015734c637297004ea737c9ffb`
