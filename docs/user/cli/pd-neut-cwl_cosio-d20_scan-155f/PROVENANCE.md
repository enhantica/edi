# pd-neut-cwl_cosio-d20_scan-155f — provenance

Co2SiO4 on D20 (ILL), a cooling run of constant-wavelength neutron patterns fitted in sequence, each file starting from
the previous file's result. The model follows diffraction-lib's tutorial `refine-cosio-d20-tscan` (develop
`cb2cda7b`): space group, cell start, excluded regions, background positions, the free set and the Co1 and Co2 Biso
constraint.

## The patterns

The files are the first 155 of the 162-file cooling run in `pd-neut-cwl_cosio-d20_scan-162f`, copied byte for byte:
497.4 K down to 52.3 K. The last seven files (51.86 K down to 50.41 K) are left out because Co2SiO4 orders
magnetically there: the (100) and (001) magnetic peaks, at 2θ ≈ 10.7° and 22.8°, stand 3 to 60 standard deviations
above their level in the paramagnetic files (the integrated counts in ±0.35° around each position, against the spread
over files 91 to 150), and the nuclear model cannot fit them. At 52.3 K they are within 2 standard deviations.

## The start

The project starts the way a user's own measurement would: zero shift 0, the profile only roughly right (U, V, W, Y to
one significant figure: 0.2, −0.5, 0.4, 0.01), Biso 0.5 on every site, the coordinates of the fitted structure rounded
to two decimals, scale 1 and a flat background of 360 counts (the tenth percentile of the first file). The template
dataset, from which the run starts, is the first file (497.4 K).

`project/` is built by `tools/cli_projects/build_catalogue_projects.py`.
