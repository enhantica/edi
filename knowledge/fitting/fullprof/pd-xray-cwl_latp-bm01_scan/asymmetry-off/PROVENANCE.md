# `pd-xray-cwl_latp-bm01_scan` -- FullProf fit with the asymmetry off

The fit of `../fit.pcr` with the four Bérar-Baldinozzi coefficients fixed at 0, the reference for every shared value of
this example. FullProf's Bérar-Baldinozzi form and edi's differ, and no mapping of the coefficients makes them agree, so
the full model is compared on R<sub>wp</sub> and the number of free parameters only (`../reference.json`), and every
other value here, against edi's fit of the project with the same coefficients fixed (the `asymmetry-off` variant of
the example's `expected.json`).

`fit.pcr` and its data were written by `tests/fixtures/example_catalogue/fullprof_inputs.py` from a copy of
`docs/user/cli/pd-xray-cwl_latp-bm01_scan/project` whose four coefficients are `0` and fixed. It differs from `../fit.pcr` only in
those coefficients' codes, now 0, the codes numbered after them, renumbered down by the codes removed, and the refined-parameter count,
59 -> 57. FullProf.2k 8.40 (`fp2k` sha256 `b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`) ran once, when this
reference was written, as `printf 'fit\n\n' | fp2k` in a copy of this folder; no check runs it. Convergence at
cycle 37; pooled R<sub>wp</sub> 4.71 % (with the asymmetry:
4.57 %).

FullProf's lines (`fit.sum`):

```text
=> Rp:  3.95     Rwp:  4.71     Rexp:    0.00 Chi2: 0.155E+09  L.S. refinement
```

`reference.json` records the free parameters' values and uncertainties from `fit.out` and the edi name each code
belongs to.

## Files (sha256)

- `fit.pcr` `a2f009e0937616688759e52f213b1d133374229a384c82d87c47001329b3c627`
- `fit.dat` `30581794f38c5998848b7364d5a92ddb81d481196022a50dd27797dc6855a69a`
- `fit.out` `55090c27066ea9768570570f0ce73313870d46d4de8ff481dd3774b593cbae70`
- `fit.sum` `019879ce02594f30858f2863145a0e0164dee1844452a10745fe53853ea5b8fe`
- `reference.json` `2381ba12ca417a0955f3235f8e8d24f1425831ee707f1b12c05bd54f9b76d02c`
