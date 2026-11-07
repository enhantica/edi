# `pd-neut-cwl_lmo-echidna` -- FullProf fit with the asymmetry off

The fit of `../fit.pcr` with the FCJ asymmetry (S/L and D/L, fixed at 0.08 in the example) set to 0, the reference for
every shared value of this example. FullProf integrates the FCJ aberration on its own ladder of nodes and edi
continuously in the axial offset, so with the asymmetry on the two fits settle on cells several of edi's standard
uncertainties apart. The full model is compared on R<sub>wp</sub> and the number of free parameters only
(`../reference.json`), and every other value here, against edi's fit of the project with the same coefficients at 0
(the `asymmetry-off` variant of the example's `expected.json`).

`fit.pcr` and its data were written by `tests/fixtures/example_catalogue/fullprof_inputs.py` from a copy of
`docs/user/cli/pd-neut-cwl_lmo-echidna/project` whose two FCJ coefficients are `0`. It differs from `../fit.pcr` only in
those two values; the coefficients were fixed already, so no code changes and the refined-parameter count stays 24.
FullProf.2k 8.40 Feb2026 (`fp2k` sha256 `b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`) ran once, when this reference was written, as
`printf 'fit\n\n' | fp2k` in a copy of this folder; no check runs it. It ends with exit status 24 on reading past the
end of its input, after writing every output, as the fit beside it does. Convergence at cycle 264; R<sub>wp</sub>
7.40 % (with the asymmetry: 5.07 %).

FullProf's lines (`fit.sum`):

```text
=> Rp:  5.33     Rwp:  7.40     Rexp:    3.23 Chi2:  5.24      L.S. refinement
```

`reference.json` records the free parameters' values and uncertainties from `fit.out` (the parser of
`finalize_fullprof.py`) and the edi name each code belongs to; the codes are the same as `../reference.json`'s.

## Files (sha256)

- `fit.pcr` `44f73641713545b752eec77428476aa973b8452d62f1b92a9a14524b4b0bc631`
- `fit.dat` `b8624d669feb9a14800bbba7e4e71cfb4c23aba323f884ba89c57c9345cdbc20`
- `fit.out` `7027643c3262677020c9e8d4e8098b7057c818508e4586dec0271ced1cec1590`
- `fit.sum` `51a80c9b0c4126d2b7bfb34c5b7bfcafdcf30f0c8481acb17b7a706c8300004b`
- `reference.json` `b55a8f49b20f1561ba56cd171933f6e1146a06e4f403d9a1152701acc25ba8fc`
