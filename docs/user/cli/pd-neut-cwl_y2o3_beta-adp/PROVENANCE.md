# pd-neut-cwl_y2o3_beta-adp — provenance

**Built, not copied**, by `tools/cli_projects/build_pd_neut_cwl_y2o3_beta_adp.py` from the vendored FullProf reference
`knowledge/verification/fullprof/pd-neut-cwl_y2o3_beta-adp/` (diffraction-lib's folder of the same name, its bytes unchanged). The
model is the `.pcr`'s: the three sites with their beta tensors, every site fully occupied (the `.pcr`'s Occ is site occupancy x
site multiplicity / general multiplicity), its 21 background points and its excluded regions, against FullProf's data `y2o3.dat`
with its own sigmas. The scale starts at the `.pcr` value, 1.0602, and is the only free parameter.

| quantity | kind | value | source |
| --- | --- | --- | --- |
| `n_points_fitted` | reference | 2509 | `scale-fit.out` `N-P+C = 2508` plus the one free parameter |
| `param.scale.value` | reference | 0.12779339 ± 0.00065268698 | `fullprof/scale-fit.out`, the final parameter summary (`Scale_ph1_pat1`) — the tolerance is FullProf's own uncertainty |
| `n_free` | reference | 1 | this project's declaration |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | 3, 6.675026351, 0.03200225019 | edi `python -m edi fit`, measured 2026-10-06 |

edi's fitted scale is 0.1277366, 0.09 of FullProf's uncertainty from its value. FullProf's own figures for the same fit — χ² 6.67,
Rwp 3.20 % — agree with the pins to their printed precision; they are not used as references because FullProf prints them to three
digits.

The pins gate drift only. `fullprof/scale-fit.inp` is the reference `.pcr` with the scale as its one free parameter (code 11) and
100 cycles, nothing else changed; `fullprof/scale-fit.out` is FullProf.2k 8.40's output (`fp2k` sha256
`b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`, `printf 'y2o3\n\n' | fp2k` in a copy of the reference
folder), run once at authoring time; no gate runs FullProf.

## Files (sha256)

- `fullprof/scale-fit.inp` `bb0d4dff3143705b3e6fc1f08348e9aa54e9dcc14d80d66c2d60d6b570513790`
- `fullprof/scale-fit.out` `62792bce9c6d712fa69c36ac33f9a3608630df143b6e5bb3cb1f2669b6120f37`
