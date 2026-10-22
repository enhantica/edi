# sc-neut-tof_taurine-unknown_basic: provenance

Built by `tools/cli_projects/build_sc_projects.py` from FullProf's files for the matching
diffraction-lib verification page (`tests/fixtures/single_crystal/fullprof/`). The structure,
extinction and starting scale are the page's FullProf values; the measured reflections are its
`.int` file. The parameters the page frees are free.

## Which values are references

Every value comes from FullProf's own fit of the same parameters on the same reflections
(`../../../../tests/fixtures/single_crystal/fitting/fullprof/sc-neut-tof_taurine-unknown_basic/`, see the `README.md` there), never from edi or crysta.

| quantity | kind | value | tolerance |
| --- | --- | --- | --- |
| `n_free` | reference | 1 | tol_abs 0 |
| `n_points_fitted` | reference | 171 | tol_abs 0 |
| `param.scale.value` | reference | 2.6886642 | tol_abs 0.025837642 |
| `reduced_chi_square` | reference | 24.41891246915446 | tol_abs 0.06, tol_rel 0.002 |

The scale's tolerance is FullProf's own uncertainty plus half its last printed digit; the
reduced chi-square is FullProf's residual sum over N - p.
