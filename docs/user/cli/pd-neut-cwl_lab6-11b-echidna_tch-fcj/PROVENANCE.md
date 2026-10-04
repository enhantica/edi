# pd-neut-cwl_lab6-11b-echidna_tch-fcj — provenance

**Built, not copied**, by `tools/cli_projects/build_c13_t6_projects.py` from the vendored FullProf fitting reference `knowledge/fitting/fullprof/pd-neut-cwl_lab6-11b-echidna_tch-fcj/` (its own `PROVENANCE.md` names every file's sha256). The project is that `.pcr`'s model: its data file, excluded regions, profile, calibration, absorption, structure and background, every value at FullProf's converged state, and FullProf's free set (every parameter with a non-zero code is free). `expected.json` is written by the same script with `--expected <record-dir>` from a `python -m edi fit --report machine --verbosity full` record.

The reference is the **owner-authored** FullProf refinement of the 11B LaB6 data (`Npr 7`, TCH x FCJ, S/L = D/L
= 0.08 fixed; FullProf: converged, Rwp 8.19, chi2 8.87 on rerun).

## Translations

- **Occupancy.** A `.pcr` `Occ` is site occupancy x site multiplicity / general multiplicity; the project
  declares the site occupancy.
- **`Wdt`** is `_peak.cutoff_fwhm`.
- **Scattering lengths.** crysta's default table has no 11B. The structure declares the two values FullProf
  used: La 8.24 fm (its table, Sears 1992) and 11B 6.65 fm (the `.pcr`'s `Additional scattering factors`,
  0.665e-12 cm). They are declared together because a declared map and a declared source cannot be
  combined.
- **The B site.** FullProf writes B at (1/2, 1/2, z). crysta's Wyckoff 6f representative is (x, 1/2, 1/2), the
  same orbit under a cubic axis permutation, so the project's free coordinate is `B.fract_x` and its reference is
  FullProf's z.
- **Absorption.** FullProf's `muR` 0.7 is `_absorption.type cylinder-hewat`, `_absorption.mu_r 0.7`: the same
  CrysFML polynomial.
- **Shifts.** `SyCos`/`SySin` are `_instrument.calib_sample_displacement`/`_transparency`.
- **Background.** FullProf `Nba 0` is `_background.type polynomial` with `_background.origin` = `Bkpos` = 80° and
  the six coefficients (the last fixed at 0) as orders 0..5.

## Check run

`python -m edi fit <copy> --dry --report machine --verbosity full` (crysta `6f076a2d`): `status=done`,
`n_free=17`, `n_points_fitted=3077`, `iterations=2`, `reduced_chi_square=8.844222988`, `rwp=0.08176730916`, about
0.6 s. Every referenced parameter is within 0.30 of FullProf's standard uncertainty, and every background
coefficient within 0.20.

## expected.json

| quantity | kind | source |
| --- | --- | --- |
| `n_free` | reference | the `.sum`'s number of fitted parameters, 17 |
| `param.<name>.value`, `param.background[<m>].value` | reference, tolerance 4 sigma | `ECH0030684_LaB6_1p622A.sum` |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | the check run above |
