# FullProf authoring record

FullProf fp2k 8.40 (Feb2026, ILL) was run at authoring time on 25 October 2026.
Tests read these committed outputs and never invoke fp2k.

Start: `docs/user/cli/sc-neut-tof_taurine-senju/project`. `reference.json` binds every input and output byte.
`start.pcr` is `tests/fixtures/single_crystal/example_fits/taurine_converged/input.pcr` set back to the
project's own start: S1 x 0.20800, O1 y 0.23701, N1 z 0.33658 and C1 x 0.33574, every beta 0, and
the three extinction terms 0, with LF line endings. `start.int` is that folder's `taurine.int`, the six
SENJU datasets the project reads.

Reproduce: copy `start.pcr` and `start.int` to `fit.pcr` and `fit.int`, then run `printf 'fit\n\n' | fp2k`.
fp2k ends with exit 24, a Fortran end of file at its closing prompt after every output is written;
this is not a numerical failure. `run.log` keeps the session.

Converged in 40 cycles: 135 free parameters, 947 reflections, RF2w 12.2 %.
The project's ADPs are betas, as FullProf's, so `report_values` carries them unconverted.
