# pd-neut-cwl_lab6-echidna_fcj-asymmetry — provenance

**Built, not copied**, by `tools/cli_projects/build_c11_t57_projects.py` from the vendored FullProf
reference `knowledge/verification/fullprof/pd-neut-cwl_lab6-echidna_fcj-asymmetry/` (diffraction-lib
`0d9f10e4`, upstream bytes). The model is the `.pcr`'s — the values the
`pd-neut-cwl_LaB6_fcj-asymmetry` verification page seeds, S/L = D/L = 0.08 — against the `.dat` FullProf
reads, with the `.pcr` excluded regions and its 2Thmax `163.756378` as the upper exclusion (edi has no
range, and the file's last point, 163.75638, lies just above it). The scale starts at the `.pcr` value
and is the only free parameter.

**One translation.** FullProf's background is a 6th-degree polynomial (`Nba` = 0), which edi cannot
express. It becomes a line-segment background with one anchor
per `.bac` point — FullProf's own background values, moved from its zero-corrected axis to the native
one by `Zero` — so at each data point it is FullProf's background to the `.bac`'s printed precision.

| quantity | kind | value | source |
| --- | --- | --- | --- |
| `n_points_fitted` | reference | 3076 | `scale-fit.out` `N-P+C = 3075` plus the one free parameter |
| `param.scale.value` | reference | 28.2777214 ± 0.6023792 | `scale-fit.out`, the final parameter summary (`Scale_ph1_pat1`) — the tolerance is FullProf's own uncertainty |
| `n_free` | reference | 1 | this project's declaration |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | 2, 261.5811433, 0.4457889832 | edi `python -m edi fit`, measured 2026-09-26 with crysta at, merged as `55db2c3b` (#206) |

FullProf's scale-only fit converges far from the `.pcr` scale (42.98): the upstream page is a
calculation, and its model does not fit these data well (FullProf χ² 263, edi 261.6). That is what this
project checks: the same model, fitted the same way, lands on the same scale.

The pins gate drift only. `fullprof/scale-fit.inp` is the reference `.pcr` with the scale as its one
free parameter (code 11), 100 cycles at full shifts and nothing else changed;
`fullprof/scale-fit.out` is FullProf.2k 8.40's output (`fp2k` sha256
`b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`, `printf 'ECH0030684_LaB6_1p622A_fcj\n\n' | fp2k` in a
copy of the reference folder), run once at authoring time; no gate runs FullProf.

## Files (sha256)

- `fullprof/scale-fit.inp` `bb45ccb30ce32631844256f68d937ed92e7f343501770c49805517d73731a66e`
- `fullprof/scale-fit.out` `f5b8d75b37a667de9d0dbf27eb19e1471e4cfe024117b7c3d1cdc052edba6a04`
