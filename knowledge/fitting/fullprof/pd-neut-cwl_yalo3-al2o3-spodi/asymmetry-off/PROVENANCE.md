# `pd-neut-cwl_yalo3-al2o3-spodi` -- FullProf fit with the asymmetry off

The fit of `../fit.pcr` with the four Bérar-Baldinozzi coefficients fixed at 0, the reference for every shared value of
this example. FullProf's Bérar-Baldinozzi form and edi's differ, and no mapping of the coefficients makes them agree, so
the full model is compared on R<sub>wp</sub> and the number of free parameters only (`../reference.json`), and every
other value here, against edi's fit of the project with the same coefficients fixed (the `asymmetry-off` variant of
the example's `expected.json`).

`fit.pcr` and its data were written by `tests/fixtures/example_catalogue/fullprof_inputs.py` from a copy of
`docs/user/cli/pd-neut-cwl_yalo3-al2o3-spodi/project` whose four coefficients are `0` and fixed. It differs from `../fit.pcr` only in
those coefficients' codes, now 0, the codes numbered after them, renumbered down by the codes removed, and the refined-parameter count,
56 -> 52. FullProf.2k 8.40 (`fp2k` sha256 `b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`) ran once, when this
reference was written, as `printf 'fit\n\n' | fp2k` in a copy of this folder; no check runs it. Convergence at
cycle 71; pooled R<sub>wp</sub> 4.68 % (with the asymmetry:
4.10 %).

FullProf's lines (`fit.sum`):

```text
=> Rp:  3.63     Rwp:  4.68     Rexp:    1.30 Chi2:  13.0      L.S. refinement
```

`reference.json` records the free parameters' values and uncertainties from `fit.out` and the edi name each code
belongs to.

## Files (sha256)

- `fit.pcr` `0b0f2c92579d7a28a1dec9666bacf38d7f8a587eec2d448049da9bb74e2564c5`
- `fit.dat` `2e7def691efd285ca655f60a1a4f4efaa04dca860bc3263f4c2bfb77a3000d2c`
- `fit.out` `1a6a0764535b7aeeb807c1d30c804faab0f66d1b2432f9f7a3a411c65b15e1dd`
- `fit.sum` `4d0d349866705cfc7bf9fdb6674b180f1f9c32d067f5ac243eca615e388e8b22`
- `reference.json` `0d79ffad4939ce3e0a79f6fdb44a67c66bed7985165dde0037525877c855d41b`
