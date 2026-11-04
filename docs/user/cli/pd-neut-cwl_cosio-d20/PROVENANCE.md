# pd-neut-cwl_cosio-d20: provenance

Built by `tools/cli_projects/build_catalogue_projects.py` (`catalogue_cw_cases.py`).

## Sources

- **Data:** the D20 (ILL) pattern of `pd-neut-cwl_cosio-d20_start-4`, read from its `_data` loop unchanged: the 1418
  points of diffraction-lib's dataset `meas-cosio-d20` (`data/measured/cosio-d20.xye` in `easyscience/diffraction` at commit `3ec801667904578ea39f1a4f4aa941866543a669`, sha256
  `72ff3c5902cc9e87b7a9a6f4d87081e6367f1477a7958914e3d89c87ddc164e9`), licence BSD-3-Clause.
- **Model:** diffraction-lib's tutorial `refine-cosio-d20` (develop `cb2cda7b`) and `pd-neut-cwl_cosio-d20_start-4`:
  Co2SiO4 in `P n m a`, wavelength 1.87 Å fixed, 14 background points, and the tutorial's tie of Co2's Biso to Co1's.
  The peak shape is the source project's Thompson-Cox-Hastings pseudo-Voigt without asymmetry; the tutorial uses a
  pseudo-Voigt with Bérar-Baldinozzi asymmetry and frees one asymmetry term.

## The start

- **Start:** zero shift 0; U, V, W, Y at one significant figure of the fitted values (0.2, -0.5, 0.4, 0.01); Biso 0.5
  on every site; coordinates rounded to two decimals; cell 10.3, 6.0, 4.8 Å as the tutorial starts it; oxygen
  occupancies 1; scale 1; a flat background at the level read off the pattern.
- **Free (42):** the cell, the 11 free coordinates, the Biso of Co1 (Co2 follows), Si and the three oxygens, the three
  oxygen occupancies, the zero shift, U, V, W, Y, the scale and the 14 background points.
- **Descent:** the project declares `_minimizer.descent fast_descent`. From this start the default descent stops in a
  shallower minimum.
- **Left out:** the tutorial's minimizer choice; edi uses crysta.
