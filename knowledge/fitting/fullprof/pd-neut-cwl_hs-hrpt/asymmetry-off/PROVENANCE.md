# `pd-neut-cwl_hs-hrpt` -- FullProf fit with the asymmetry off

The fit of `../fit.pcr` with the four Bérar-Baldinozzi coefficients fixed at 0, the reference for every shared value of
this example. FullProf's Bérar-Baldinozzi form and edi's differ, and no mapping of the coefficients makes them agree, so
the full model is compared on R<sub>wp</sub> and the number of free parameters only (`../reference.json`), and every
other value here, against edi's fit of the project with the same coefficients fixed (the `asymmetry-off` variant of
the example's `expected.json`).

`fit.pcr` and its data were written by `tests/fixtures/example_catalogue/fullprof_inputs.py` from a copy of
`docs/user/cli/pd-neut-cwl_hs-hrpt/project` whose four coefficients are `0` and fixed. It differs from `../fit.pcr` only in
those coefficients' codes, now 0, the codes numbered after them, renumbered down by the codes removed, and the refined-parameter count,
32 -> 28. FullProf.2k 8.40 (`fp2k` sha256 `b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`) ran once, when this
reference was written, as `printf 'fit\n\n' | fp2k` in a copy of this folder; no check runs it. Convergence at
cycle 57; pooled R<sub>wp</sub> 5.43 % (with the asymmetry:
5.30 %).

FullProf's lines (`fit.sum`):

```text
=> Rp:  4.34     Rwp:  5.43     Rexp:    3.62 Chi2:  2.26      L.S. refinement
```

`reference.json` records the free parameters' values and uncertainties from `fit.out` and the edi name each code
belongs to.

## Files (sha256)

- `fit.pcr` `cce98a3e991bf714212f1c6ec214f7b6de1804389593d56eca79891cf9ab9910`
- `fit.dat` `15b0703e44fb079cef882e1ceb8b14be2aab51ff618a0f906912d9827304e691`
- `fit.out` `2e2c20c440aa933f3e31e60c326836d2a7af400f0b14cae0c92cc4a90d1cd0a0`
- `fit.sum` `0bb0eb575994667ba17d42e54b486d4b44c24cb1a34a743ba7941bb03995464a`
- `reference.json` `c883f988ef12c8056f04c1210a268194a98a068da95449b802b38524524424b2`
