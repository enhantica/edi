# pd-neut-tof_si_simulation — provenance

A calculated time-of-flight neutron pattern of silicon, with no measured data, on the SEPD bank (2θ 144.845°) of the
fitted Si case.

## Sources

- **Data:** none; the pattern is calculated.
- **Model:** diffraction-lib's tutorial `simulate-si-tof` (repository `easyscience/diffraction-lib`, develop `cb2cda7b`),
  licence BSD-3-Clause.

Every setting is that of diffraction-lib's tutorial `simulate-si-tof` (develop `cb2cda7b`): Fd-3m
(origin choice 2), a = 5.431 Å, Biso 0.5, the bank's d-to-TOF calibration, the Jorgensen profile (diffraction-lib's
default time-of-flight profile), a flat background of 500 and the range 5000 to 15000 μs in steps of 2 μs. The
profile cutoff (12 FWHM) is edi's own setting.

`project/` is built by `tools/cli_projects/build_catalogue_projects.py`.
