# pd-neut-cwl_cosio-d20_scan — provenance

Co2SiO4 on D20 (ILL), a cooling run of constant-wavelength neutron patterns fitted in sequence, each file starting from
the previous file's result. The model follows diffraction-lib's tutorial `refine-cosio-d20-tscan` (develop
`cb2cda7b`): space group, cell start, excluded regions, background positions, the free set and the Co1 and Co2 Biso
constraint.

## Sources

- **Data:** the patterns of diffraction-lib's D20 cooling scan, dataset `meas-cosio-d20-scan-156f`
  (`data/measured/cosio-d20-scan-156f.zip` in `easyscience/diffraction` at commit `3ec801667904578ea39f1a4f4aa941866543a669`, sha256
  `5ce20209ce52382f547269d93d511707ab6795d5f681b7cb77ba713705be5baa`), licence BSD-3-Clause. The files here are
  named by their order and temperature; matched by temperature, each holds every point of its file in that
  dataset, with one or two more rows at the ends of the range.
- **Model:** diffraction-lib's tutorial `refine-cosio-d20-tscan` (repository `easyscience/diffraction-lib`, develop
  `cb2cda7b`), licence BSD-3-Clause.

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
