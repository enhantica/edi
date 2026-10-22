# pd-neut-cwl_lbco-hrpt_basic: provenance

Built by `tools/cli_projects/build_catalogue_projects.py` (`catalogue_cw_cases.py`).

- **Data:** the HRPT (PSI) pattern of `pd-neut-cwl_lbco-hrpt_start-4`, read from its `_data` loop unchanged. That
  project's `PROVENANCE.md` names where the pattern comes from.
- **Model:** diffraction-lib's tutorial `refine-lbco-hrpt-from-data` (develop `cb2cda7b`): La0.5Ba0.5CoO3 in
  `P m -3 m`, La and Ba sharing the `1a` site, Thompson-Cox-Hastings pseudo-Voigt, wavelength 1.494 Å fixed, excluded
  regions 0-5° and 165-180°, five background points. As in the tutorial's last step, Ba's Biso is tied to La's.
- **Start:** the 2θ zero at HRPT's own 0.6°, as the instrument's calibration gives it and as the tutorial starts it;
  U, V, W, Y at one significant figure of the fitted values (0.08, -0.1, 0.1, 0.08); Biso 0.5 on every site; cell
  3.88 Å as the tutorial starts it; scale 9; a flat background at the level read off the pattern.
- **Why the zero is not 0:** this pattern's zero shift is 0.62°. From 0, with the cell at 3.88 Å, the high-angle peaks
  line up but the low-angle ones sit up to 0.5° away, more than their width, and a fit with every parameter free
  settles at R<sub>wp</sub> 39 % with a quarter of the scale, broad peaks and a negative Co Biso. With only the scale,
  zero, cell and background free it finds the zero from 0; with everything free it needs a start of 0.25° or more.
- **Free (15):** the cell, the Biso of La (Ba follows), Co and O, the zero shift, U, V, W, Y, the scale and the five
  background points.
- **Left out:** the tutorial's automatic background estimate (a flat background stands in for it), its cryspy and
  CrysFML calculator switches and its lmfit minimizer choice; edi uses crysta.
