# pd-neut-tof_ceo2-pearl_polynomial — provenance

**Built, not copied**, by `tools/cli_projects/build_c13_t6_projects.py` from the vendored FullProf fitting reference `knowledge/fitting/fullprof/pd-neut-tof_ceo2-pearl_polynomial/` (its own `PROVENANCE.md` names every file's sha256). The project is that `.pcr`'s model: its data file, excluded regions, profile, calibration, absorption, structure and background, every value at FullProf's converged state, and FullProf's free set (every parameter with a non-zero code is free). `expected.json` is written by the same script with `--expected <record-dir>` from a `python -m edi fit --report machine --verbosity full` record.

## Translations

- **Occupancy.** A `.pcr` `Occ` is site occupancy x site multiplicity / general multiplicity; the project
  declares the site occupancy.
- **`Wdt`** is `_peak.cutoff_fwhm`.
- **Scattering lengths.** Sears (1992), `sears1992`: FullProf's own table.
- **Background.** FullProf `Nba 0` is `_background.type polynomial` with `_background.origin` = `Bkpos` = 7000 µs and
  the six coefficients as `_background.order` 0..5.

## The chi-square

The data are the XYDATA conversion of FullProf's `Ceo2_PEARL.ralf` that made, and this project pins statistics
only from it. FullProf's RALF reader (`Ins = 12`) weights the original file with sigmas 100 times too large for
the intensities it normalises, so a fit of the RALF file printed Rexp 268.76 % and chi2 4.7e-4 — a statistic of
the reader, not of the fit. The converted file (`Ins = 10`) carries X = RALF TOF / 32, Y = the intensity
FullProf read, and sigma = RALF sigma x Y / I, so its own sigmas are consistent with its intensities: FullProf's
fit of it prints Rp 4.43, Rwp 5.29, **Rexp 2.69**, **chi2 3.88**. The reference's `PROVENANCE.md` records the
conversion and its one non-FullProf value (the last point, outside the fitted range).

## Check run

`python -m edi fit <copy> --dry --report machine --verbosity full`:
`status=done`, `n_free=19`, `n_points_fitted=2237`, `iterations=1`, `reduced_chi_square=3.877572872`,
`rwp=0.05293503604`, about 0.5 s. FullProf: chi2 3.88, Rwp 5.29 %. Every referenced
parameter is within 0.27 of FullProf's standard uncertainty, and every background coefficient within 1.19.

## expected.json

| quantity | kind | source |
| --- | --- | --- |
| `n_free` | reference | the `.sum`'s number of fitted parameters, 19 |
| `param.<name>.value`, `param.background[<m>].value` | reference, tolerance 4 sigma | `Ceo2_PEARL.sum`, FullProf's refined values and standard uncertainties |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | the check run above |
