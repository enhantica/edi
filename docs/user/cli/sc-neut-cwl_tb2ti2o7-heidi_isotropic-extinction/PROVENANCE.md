# sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction: provenance

Built by `tools/cli_projects/build_sc_projects.py` from FullProf's files for the matching
diffraction-lib verification page (`tests/fixtures/single_crystal/fullprof/`). The structure,
extinction and starting scale are the page's FullProf values; the measured reflections are its
`.int` file. The parameters the page frees are free.

## Which values are references

Every value comes from FullProf's own fit of the same parameters on the same reflections
(`../../../../tests/fixtures/single_crystal/fitting/fullprof/sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction/`, see the `README.md` there), never from edi or crysta.

| quantity | kind | value | tolerance |
| --- | --- | --- | --- |
| `n_free` | reference | 2 | tol_abs 0 |
| `n_points_fitted` | reference | 220 | tol_abs 0 |
| `param.scale.value` | reference | 3.4961121 | tol_abs 0.10108793 |
| `reduced_chi_square` | reference | 82.69535362484258 | tol_abs 0.06, tol_rel 0.002 |

The scale's tolerance is FullProf's own uncertainty plus half its last printed digit; the
reduced chi-square is FullProf's residual sum over N - p.

FullProf fits its own extinction model (model 1, Ext1), not the Becker-Coppens radius this project frees, so its values do not describe the same model. diffraction-lib marks the same difference on its page. This project stays out of the executing set until that is settled.
