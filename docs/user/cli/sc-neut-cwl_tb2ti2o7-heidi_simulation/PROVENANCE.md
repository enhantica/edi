# sc-neut-cwl_tb2ti2o7-heidi_simulation — provenance

Calculated single-crystal neutron reflections of Tb2Ti2O7 on HEiDi, with no measured data: the model and the
instrument are enough for edi to calculate every reflection, and changing a value shows its effect at once.

## Sources

- **Data:** none; the reflections are calculated up to sin θ/λ = 0.95 Å⁻¹.
- **Model:** the start of the case `sc-neut-cwl_tb2ti2o7-heidi`, from diffraction-lib (develop
  `cb2cda7be6117199be8f8cac0a666a7bccd32d90`)'s verification page `sc-neut-cwl_tbti_anisotropic-adp` (FullProf
  `tbti.pcr`): the Fd-3m structure, its sites and the wavelength 0.793 Å, licence BSD-3-Clause. diffraction-lib's
  tutorial `refine-tbti-heidi` fits the same crystal.

The project holds that case's structure, instrument and extinction as they start (Uani 0.0026 Å² on every site, O1 x
at 0.33, the scale 4, isotropic Becker-Coppens extinction with the crystal radius 3 mm, the domain radius 25 μm and
the mosaic spread 0), with nothing free and no reflections: the experiment's sin θ/λ limit replaces the measured list.

## Pins

`expected.json` holds the number of reflections (211) and the checksum of their calculated intensities, taken with
`python -m edi calc --dry --report machine`. They show the calculation stays the same; they are not a reference.
