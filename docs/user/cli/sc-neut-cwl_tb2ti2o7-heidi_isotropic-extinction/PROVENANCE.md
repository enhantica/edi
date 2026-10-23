# sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction: provenance

Built by `tools/cli_projects/build_sc_projects.py` from FullProf's files for the matching
diffraction-lib verification page (`tests/fixtures/single_crystal/fullprof/`). The structure,
extinction and starting scale are the page's FullProf values; the measured reflections are its
`.int` file. The parameters the page frees are free.

## Which values are references

Every value comes from the Becker-Coppens closed form (Becker and Coppens, Acta Cryst. A30, 1974) applied to FullProf's unextincted F2 and fitted to the same reflections with the same free parameters, computed once by a tool independent of edi and crysta. FullProf has no Becker-Coppens sphere model, so its own fit cannot be the reference (`../../../../tests/fixtures/single_crystal/fitting/becker-coppens/sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction/`, see the `README.md` there), never from edi or
crysta.

| quantity | kind | value | tolerance |
| --- | --- | --- | --- |
| `n_free` | reference | 2 | tol_abs 0 |
| `n_points_fitted` | reference | 220 | tol_abs 0 |
| `param.scale.value` | reference | 3.6799768101945864 | tol_abs 0.10288873814942545 |
| `param.domain_radius.value` | reference | 16.550771124907907 | tol_abs 2.225559273639577 |
| `reduced_chi_square` | reference | 76.79365259985084 | tol_abs 0.06, tol_rel 0.002 |

Each parameter bound is one s.u. of that fit; the reduced chi-square is the residual sum over N - p.
