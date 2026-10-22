# pd-neut-cwl_cosio-d20: provenance

Built by `tools/cli_projects/build_catalogue_projects.py` (`catalogue_cw_cases.py`).

- **Data:** the D20 (ILL) pattern of `pd-neut-cwl_cosio-d20_start-4`, read from its `_data` loop unchanged. That
  project's `PROVENANCE.md` names where the pattern comes from.
- **Model:** diffraction-lib's tutorial `refine-cosio-d20` (develop `cb2cda7b`) and `pd-neut-cwl_cosio-d20_start-4`:
  Co2SiO4 in `P n m a`, wavelength 1.87 Å fixed, 14 background points, and the tutorial's tie of Co2's Biso to Co1's.
  The peak shape is the source project's Thompson-Cox-Hastings pseudo-Voigt without asymmetry; the tutorial uses a
  pseudo-Voigt with Bérar-Baldinozzi asymmetry and frees one asymmetry term.
- **Start:** zero shift 0; U, V, W, Y at one significant figure of the fitted values (0.2, -0.5, 0.4, 0.01); Biso 0.5
  on every site; coordinates rounded to two decimals; cell 10.3, 6.0, 4.8 Å as the tutorial starts it; oxygen
  occupancies 1; scale 1; a flat background at the level read off the pattern.
- **Free (42):** the cell, the 11 free coordinates, the Biso of Co1 (Co2 follows), Si and the three oxygens, the three
  oxygen occupancies, the zero shift, U, V, W, Y, the scale and the 14 background points.
- **Descent:** the project declares `_minimizer.descent fast_descent`. From this start the default descent stops in a
  shallower minimum.
- **Left out:** the tutorial's minimizer choice; edi uses crysta.
