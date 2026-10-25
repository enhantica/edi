# FullProf authoring record

FullProf fp2k 8.40 (Feb2026, ILL) was run at authoring time on 25 October 2026.
Tests read these committed outputs and never invoke fp2k.

Start: `docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi/project`. `reference.json` binds every input and output byte.
`start.pcr` is `tests/fixtures/single_crystal/example_fits/tb2ti2o7/input.pcr` set back to the project's
own start: every beta 0.00050 (off-diagonals 0), O1 x 0.33000 and the scale 4.000. It allows 200
cycles with Eps 0.01 and relaxation 1.00; with the original 0.05 the fit had not converged after 200.
`start.int` holds the HEiDi reflections the project reads.

Reproduce: copy `start.pcr` and `start.int` to `fit.pcr` and `fit.int`, then run `printf 'fit\n\n' | fp2k`.
fp2k ends with exit 24, a Fortran end of file at its closing prompt after every output is written;
this is not a numerical failure. `run.log` keeps the session.

Converged in 15 cycles: 11 free parameters, 220 reflections, RF2w 2.98 %.

The models differ. edi fits Becker-Coppens extinction mixed with the crystal path; FullProf has no
such model and fits its own empirical one (Ext-Model 1, Ext1 free, code 111). edi frees 12
parameters, FullProf 11. So the case's `expected.json` keeps edi's result as regression pins only,
and FullProf's values are a comparison, not a reference.
