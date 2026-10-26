# FullProf authoring record

FullProf fp2k 8.40 (Feb2026, ILL) was run at authoring time on 25 October 2026.
Tests read these committed outputs and never invoke fp2k.

Start: `docs/user/cli/sc-neut-cwl_pr2nio4-5c2/project`. `reference.json` binds every input and output byte.
`start.pcr` and `start.int` are `tests/fixtures/single_crystal/example_fits/pr2nio4_none/prnio.pcr` and
`prnio.int` unchanged (Pcr=2, 100 cycles), the file the project is built from.

Reproduce: copy `start.pcr` and `start.int` to `fit.pcr` and `fit.int`, then run `printf 'fit\n\n' | fp2k`.
fp2k ends with exit 24, a Fortran end of file at its closing prompt after every output is written;
this is not a numerical failure. `run.log` keeps the session.

Converged in 14 cycles: 23 free parameters, 198 reflections, RF2w 4.26 %.
`report_values` gives FullProf's values in edi's labels and units: betas as Bani (4 β a_i a_j,
orthogonal cell) and the scale times 64, FullProf's occupancy normalisation
(`tests/fixtures/single_crystal/README.md`).
