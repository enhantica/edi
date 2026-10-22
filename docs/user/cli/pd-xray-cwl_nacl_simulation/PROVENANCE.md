# pd-xray-cwl_nacl_simulation — provenance

A calculated laboratory X-ray pattern of NaCl, with no measured data.

## Sources

- **Data:** none; the pattern is calculated.
- **Model:** diffraction-lib's tutorial `simulate-nacl-xray` (repository `easyscience/diffraction-lib`, develop
  `cb2cda7b`), licence BSD-3-Clause.

The model and instrument are those of
diffraction-lib's tutorial `simulate-nacl-xray` (develop `cb2cda7b`): Fm-3m, a = 5.62 Å, Biso 0.5 on both sites, Cu Kα1
(1.5406 Å), U, V, W = 0.1, −0.1, 0.1 with no Lorentzian width, and the polarization of a graphite monochromator
(coefficient 0.5, monochromator 2θ 26.565°), which is the state the tutorial ends in after comparing it with the
unpolarized pattern. The 2θ range (10 to 150° in steps of 0.02°) is edi's choice: the tutorial takes diffraction-lib's
default range. The X-ray form factors and dispersion tables are those edi's other X-ray projects use.

`project/` is built by `tools/cli_projects/build_catalogue_projects.py`.
