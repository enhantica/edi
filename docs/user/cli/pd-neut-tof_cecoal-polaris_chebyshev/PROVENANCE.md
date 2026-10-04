# pd-neut-tof_cecoal-polaris_chebyshev — provenance

**Built, not copied**, by `tools/cli_projects/build_c13_t6_projects.py` from the vendored FullProf fitting reference `knowledge/fitting/fullprof/pd-neut-tof_cecoal-polaris_chebyshev/` (its own `PROVENANCE.md` names every file's sha256). The project is that `.pcr`'s model: its data file, excluded regions, profile, calibration, absorption, structure and background, every value at FullProf's converged state, and FullProf's free set (every parameter with a non-zero code is free). `expected.json` is written by the same script with `--expected <record-dir>` from a `python -m edi fit --report machine --verbosity full` record.

## Translations

- **Occupancy.** A `.pcr` `Occ` is site occupancy x site multiplicity / general multiplicity; the project
  declares the site occupancy.
- **`Wdt`** is `_peak.cutoff_fwhm`.
- **Scattering lengths.** Sears (1992), `sears1992`: FullProf's own table.
- **Al3.** FullProf refines Al3 to a site occupancy of 1.020(8), outside crysta's admitted [0, 1] at load; the
  project starts it at 1, free as in FullProf.
- **Background.** FullProf `Nba -5` is `_background.type chebyshev` with all 24 coefficients as orders 0..23 (the
  last twelve fixed at 0) and the domain `_background.x_min`/`x_max` = the `.pcr`'s TOF-min/TOF-max, 3001.5891 and
  19004.6582 µs.
- **Extinction.** FullProf's TOF extinction is fixed at 0.0016 and crysta has none. It does not move the fit: the
  same `.pcr` with `Extinc` 0 converges at cycle 1 with chi2 1.80 and every coordinate unchanged.

## The reference is FullProf's least-squares fit, not the vendored `.sum`

The owner ruled on it; a maximum-likelihood fit is.

The vendored `.pcr` sets `Iwg = 1`: FullProf's **maximum-likelihood** refinement (its `.sum` prints "M.L.
refinement"), whose weights follow the calculated counts. edi fits by weighted least squares with the data's own
sigmas, so its minimum is a different estimator's, and the vendored `.sum` is not its reference — at it, the
Gaussian width sits 4.4 and the Co z 4.0 of FullProf's sigma away. `fullprof/ls-fit.inp` is the vendored `.pcr`
with two edits, `Iwg 1 -> 0` (least squares) and `NCY 15 -> 50`; FullProf.2k 8.40 (`fp2k` sha256
`b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`, `printf 'ls-fit\n\n' | fp2k` in a folder
holding it as `ls-fit.pcr` beside `cecoal.dat` as `ls-fit.dat`), run once at authoring time, converged at cycle 8 with
chi2 2.85 and wrote `ls-fit.sum` and `ls-fit.new`. No gate runs FullProf. edi's fit lands within 1.35 of FullProf's
sigma of every parameter in `ls-fit.sum` and within 1.71 of every background coefficient, at chi2 2.87.

- `fullprof/ls-fit.inp` `61947f3631c44404ebe3f64310dc2ccfdf4359a0ad6a9befe19a537a509811ec`
- `fullprof/ls-fit.sum` `225ca9d3562af13dcbdec805a9b9b2b0074cfed8502a013a3b432abe372260c5`
- `fullprof/ls-fit.new` `eb2cd6cfe7e00a1a60a82c905472786d70cb415a98737e6a25e0ed905f73d623`

## Check run

`python -m edi fit <copy> --dry --report machine --verbosity full` (crysta `6f076a2d`): `status=done`,
`n_free=32`, `n_points_fitted=3692`, `iterations=4`, `reduced_chi_square=2.869451006`, `rwp=0.02088086078`, about
0.9 s.

## expected.json

| quantity | kind | source |
| --- | --- | --- |
| `n_free` | reference | `ls-fit.sum`'s number of fitted parameters, 32 |
| `param.<name>.value`, `param.background[<m>].value` | reference, tolerance 4 sigma | `fullprof/ls-fit.sum` |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | the check run above |
