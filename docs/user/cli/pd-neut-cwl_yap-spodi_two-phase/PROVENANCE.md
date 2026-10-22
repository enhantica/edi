# pd-neut-cwl_yap-spodi_two-phase: provenance

Built by `tools/cli_projects/build_catalogue_projects.py` (`catalogue_cw_cases.py`).

- **Data:** the SPODI (FRM II) 3 K pattern of `pd-neut-cwl_yap-spodi_3k`, read from its `_data` loop unchanged. That
  project's `PROVENANCE.md` names where the pattern comes from.
- **Model:** `pd-neut-cwl_yap-spodi_3k` and diffraction-lib's tutorial `refine-yap-3k` (develop `cb2cda7b`): YAlO3 in
  `P b n m` (the tutorial's `P n m a` in the `cab` setting, the same axes) and Al2O3 in `R -3 c`; one pseudo-Voigt with
  Bérar-Baldinozzi asymmetry shared by both phases, a constant mixing, the asymmetry limit 160°, cylinder absorption
  muR 0.0221, wavelength 1.54816 Å fixed, excluded regions 0-4° and 153.95-180°, the source project's 25 background
  positions.
- **Start:** zero shift 0; U, V, W and the mixing at one significant figure (0.04, -0.05, 0.1, 0.1), asymmetry 0;
  Biso 0.5 on every site; coordinates rounded to two decimals; cells rounded to two decimals; scales 30 and 0.2; a flat
  background at the level read off the pattern.
- **Free (56):** the source project's set: both cells, the free coordinates, every Biso, both scales, the zero shift,
  U, V, W, the mixing, the four asymmetry terms and the 25 background points.
- **Note:** the Al2O3 aluminium Biso ends slightly negative, as it does in the source project and in FullProf's fit of
  this pattern; the minor phase determines it poorly.
- **Left out:** the tutorial's automatic background estimate, its cryspy calculator and its bumps minimizer choice.
