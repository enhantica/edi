# pd-neut-cwl_lab6-11b-echidna_basic: provenance

Built by `tools/cli_projects/build_catalogue_projects.py` (`catalogue_cw_cases.py`).

- **Data:** the ECHIDNA (ANSTO) pattern of `pd-neut-cwl_lab6-11b-echidna_tch-fcj`, read from its `_data` loop
  unchanged. That project's `PROVENANCE.md` names where the pattern comes from. diffraction-lib has no tutorial for it.
- **Model:** the source project's: LaB6 (¹¹B-enriched) in `P m -3 m` with the cell fixed at 4.156885 Å, the scattering
  lengths B 6.65 fm and La 8.24 fm, the Thompson-Cox-Hastings pseudo-Voigt convolved with Finger-Cox-Jephcoat axial
  divergence (both FCJ parameters 0.08, fixed), cylinder absorption muR 0.7, a polynomial background about 80°, excluded
  regions 0-10° and 164-180°.
- **Start:** zero shift, sample displacement and transparency 0; wavelength 1.622 Å (the instrument's nominal value,
  free, since the standard calibrates it); U, V, W, Y at one significant figure (0.09, -0.4, 0.5, 0.05); the FCJ
  geometry at its known 0.08; Biso 0.5 on both sites; B x 0.2; scale 100; a flat background (the constant polynomial
  term at the level read off the pattern, four more terms at 0).
- **Free (17):** the source project's set: the wavelength, the zero shift, displacement and transparency, U, V, W, Y,
  B x, both Biso, the scale and the five polynomial terms. The cell stays fixed: it is the standard's.

The regression pins for reduced_chi_square, rwp were retaken with `python -m edi fit <project> --report machine` using crysta `2b75771b` and its continuous axial-offset FCJ quadrature.

**Re-pinned 2026-11-04.** The project declares the Shift/s.u. stop rule (`_minimizer.stop_rule shift_su`, 0.1; the χ²
change still ends a fit when it passes first), as every example does. Pins retaken with `python -m edi fit --report
machine` linked against crysta `609586d9`, `OMP_NUM_THREADS=1`: iterations 8 → 7; reduced_chi_square 8.821294727 →
8.821296155.
