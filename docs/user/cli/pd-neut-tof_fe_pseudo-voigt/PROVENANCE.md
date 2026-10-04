# pd-neut-tof_fe_pseudo-voigt — provenance

**Built, not copied**, by `tools/cli_projects/build_c11_t57_projects.py` from the vendored FullProf
reference `knowledge/verification/fullprof/pd-neut-tof_fe_pseudo-voigt/` (diffraction-lib `0d9f10e4`,
upstream bytes). The model is the `.pcr`'s — the values the `pd-neut-tof_Fe_pseudo-voigt` verification
page seeds — with its 31 background points and excluded regions. The data are the `.dat` rows FullProf
reads: it takes the first six lines as comments (four `#` lines and two data rows), so the set starts at
its TOF-min. One row inside the excluded 130000-180000 µs region (134955 µs) has zero sigma, which edi
refuses; it takes edi's own loader rule (`ExperimentFactory.from_data_path`: a sigma below 1e-4 becomes
1) and, being excluded, weighs nothing. The scale starts at the `.pcr` value and is the only free
parameter.

| quantity | kind | value | source |
| --- | --- | --- | --- |
| `param.scale.value` | reference | 403.0724487 ± 3.3841672 | `scale-fit.out`, the final parameter summary (`Scale_ph1_pat1`) — the tolerance is FullProf's own uncertainty |
| `n_free` | reference | 1 | this project's declaration |
| `n_points_fitted` | regression pin | 2821 | edi `python -m edi fit`, see below |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | 2, 1426.708991, 0.7289898949 | edi `python -m edi fit`, measured 2026-09-26 with crysta at, merged as `55db2c3b` (#206) |

**The point count is a pin, not a reference.** FullProf reports `N-P+C = 2819` with one free
parameter, one less than the 2821 points edi fits. Deleting any single one of those 2821 rows from a
copy of the `.dat` lowers FullProf's count by one (measured at authoring time), so FullProf does fit
every one of them; the one-count difference is in how it reports the total, and is not explained here.
FullProf's own χ² (1427) and Rwp (72.9 %) for the same fit agree with the pins to their printed
precision.

The pins gate drift only. `fullprof/scale-fit.inp` is the reference `.pcr` with the scale as its one
free parameter (code 11), 100 cycles at full shifts and nothing else changed;
`fullprof/scale-fit.out` is FullProf.2k 8.40's output (`fp2k` sha256
`b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`, `printf 'fe\n\n' | fp2k` in a
copy of the reference folder), run once at authoring time; no gate runs FullProf.

## Files (sha256)

- `fullprof/scale-fit.inp` `1941443ddf12b9447f0ada8c5dddd076af850c56ef26fea9539c3867e96f9678`
- `fullprof/scale-fit.out` `62fa9aea9545d2db239c53879df48a78f66ad0bc78b6c2d68da20a29db6ba1d0`

**Deliberately unsupported values.** After the build, three values were set by hand so the app's message list
always has an example to show: `analysis/analysis.edi` declares
`_minimizer.type "bumps (lm)"` (the loader warns `unsupported _minimizer.type "bumps (lm)" - using crysta`
and the fit runs with crysta), and `experiments/beer.edi` declares `_calculator.type cryspy` (the loader
warns `unsupported _calculator.type "cryspy" - using crysta`), and `project.edi` declares
`_rendering_plot.type plotly` (the loader warns `unsupported _rendering_plot.type "plotly" - using auto`). None
changes a number above: this project is non-executing, the engine is crysta either way, and no host draws with
a declared renderer. A rebuild with `build_c11_t57_projects.py` would drop them; the builder does
not write them yet.
