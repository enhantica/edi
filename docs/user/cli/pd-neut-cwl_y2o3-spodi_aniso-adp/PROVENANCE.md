# pd-neut-cwl_y2o3-spodi_aniso-adp: provenance

Built by `tools/cli_projects/build_catalogue_projects.py` (`catalogue_cw_cases.py`).

- **Data:** the constant-wavelength neutron pattern of `pd-neut-cwl_y2o3_beta-adp` (FullProf's `y2o3.dat` from
  diffraction-lib's verification folder, with its own sigmas), read from its `_data` loop unchanged. It was measured
  on SPODI at FRM II (the owner, 2026-10-22); the FullProf input's title gives a Ge(551) monochromator and 1.548 Å.
- **Model:** the source project's: Y2O3 in `I a -3`, every site's displacement an anisotropic β tensor tied by its site
  symmetry (Y1 on `24d` keeps four components, Y2 on `8b` two, O1 on `48e` six), a Thompson-Cox-Hastings pseudo-Voigt
  with no Lorentzian part, wavelength 1.54822 Å fixed, excluded regions 0-12° and 137.5-180°, the source's 21
  background positions. diffraction-lib has no tutorial for it.
- **Start:** zero shift 0; U, V, W at one significant figure (0.04, -0.07, 0.1); every β tensor the isotropic
  equivalent of Biso 0.5 (β11 = β22 = β33 = B a*²/4 = 0.001110, off-diagonal 0); coordinates rounded to two decimals;
  cell 10.61 Å; scale 0.1; a flat background at the level read off the pattern.
- **Free (43):** the cell, the four free coordinates, the 12 independent β components, U, V, W, the zero shift, the
  scale and the 21 background points. The source project frees the scale only.
