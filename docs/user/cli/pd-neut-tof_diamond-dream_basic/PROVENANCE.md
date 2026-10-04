# pd-neut-tof_diamond-dream_basic — provenance

**Built, not copied**, by `tools/cli_projects/build_pd_neut_tof_diamond_dream.py` from the vendored
FullProf reference as vendored by (byte-identical to diffraction-lib `0d9f10e`, at edi
`fce50e3:knowledge/verification/fullprof/pd-neut-tof_diamond_dream/`). renamed this project
from `pd-neut-tof_diamond_dream` under the id rule, content unchanged, and restated that reference as
`knowledge/verification/fullprof/pd-neut-tof_diamond-dream_basic/` (every parameter fixed, `Occ` in the
fractional convention, scale fitted alone; see that folder's `PROVENANCE.md`); the reference values below
are the `0d9f10e` ones. The model is the one FullProf fitted:
the `.pcr` structure, profile and calibration — the values the `pd-neut-tof_diamond_dream`
verification page seeds — with the fitted background heights from `diamond.sum`, the measured
pattern from `diamond.dat`, the `.pcr` excluded regions, and its TOF-max `66503.6875` as an upper
exclusion (edi has no range, and FullProf does not fit the file's last point). The scale starts at
FullProf's fitted value and is the only free parameter.

## Which values are references

| quantity | kind | value | source |
| --- | --- | --- | --- |
| `n_points_fitted` | reference | 1948 | `diamond.sum` `N-P+C = 1933` plus the 15 free parameters (`.pcr`) |
| `param.scale.value` | reference | 14.56962854 ± 0.10866658 | `diamond.sum` overall scale `0.101177976 ± 0.000754629`, × 144 (the `.pcr`'s `Occ = 1.0` on the 16c site of `F d -3 m:1`; see the verification page) — the tolerance is FullProf's own uncertainty |
| `n_free` | reference | 1 | this project's declaration: the scale is the one free parameter |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | 2, 18.24025953, 0.169634072 | edi `python -m edi fit`, measured 2026-09-24 at edi `5881af1` with crysta `973b34bd` |

The pins gate drift only. FullProf's own figures for the same fit — `Rwp 16.9`, `Chi2 18.1` — are
printed to three digits, with 15 parameters free rather than one, so they are not used as
references for edi's Rwp or χ²; edi's `rwp = 0.1696` agrees with them to that precision.
