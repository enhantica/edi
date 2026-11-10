# pd-neut-cwl_yalo3-al2o3-spodi: provenance

Built by `tools/cli_projects/build_catalogue_projects.py` (`catalogue_cw_cases.py`).

## Sources

- **Data:** the SPODI (FRM II) 3 K pattern of `pd-neut-cwl_yap-spodi_3k`, read from its `_data` loop unchanged: the
  2959 points from 4.05° to 151.95° of diffraction-lib's dataset `meas-yap-spodi` (`data/measured/yap-spodi-3k.xye`
  in `easyscience/diffraction` at commit `3ec801667904578ea39f1a4f4aa941866543a669`, sha256 `b5ad23ef8155568e1d7aecb100f6f53bedc1fa3a9dcfaa0aa19aebccb3207e39`),
  licence BSD-3-Clause.
- **Model:** `pd-neut-cwl_yap-spodi_3k` and diffraction-lib's tutorial `refine-yap-3k` (develop `cb2cda7b`): YAlO3 in
  `P b n m` (the tutorial's `P n m a` in the `cab` setting, the same axes) and Al2O3 in `R -3 c`; one pseudo-Voigt with
  Bérar-Baldinozzi asymmetry shared by both phases, a constant mixing, the asymmetry limit 160°, cylinder absorption
  muR 0.0221, wavelength 1.54816 Å fixed, excluded regions 0-4° and 153.95-180°, the source project's 25 background
  positions.

## The start

- **Start:** zero shift 0; U, V, W and the mixing at one significant figure (0.04, -0.05, 0.1, 0.1), asymmetry 0;
  Biso 0.5 on every site; coordinates rounded to two decimals; cells rounded to two decimals; scales 30 and 0.2; a flat
  background at the level read off the pattern.
- **Free (56):** the source project's set: both cells, the free coordinates, every Biso, both scales, the zero shift,
  U, V, W, the mixing, the four asymmetry terms and the 25 background points.
- **Note:** the Al2O3 aluminium Biso ends slightly negative, as it does in the source project and in FullProf's fit of
  this pattern; the minor phase determines it poorly.
- **Left out:** the tutorial's automatic background estimate, its cryspy calculator and its bumps minimizer choice.

## The check against FullProf

FullProf and edi write the Bérar-Baldinozzi asymmetry in different forms, and no mapping of the four
coefficients makes them agree; crysta tracks this difference in the asymmetry convention as a known issue.
So `expected.json` compares the full model with FullProf's on R<sub>wp</sub>, within 5 %, and on the number
of free parameters only. Every other fitted value is compared on a second fit of both programs with the four
coefficients fixed at 0: the record's `asymmetry-off` variant against FullProf's fit in
`knowledge/fitting/fullprof/pd-neut-cwl_yalo3-al2o3-spodi/asymmetry-off/`.

**Re-pinned 2026-11-07.** Under Shift/s.u. a fit now also needs the full undamped step to be below the tolerance, and a
χ² plateau tries that step once before it ends the fit. Pins retaken with `python tools/checks/cli_projects.py` linked
against crysta `4643af79`, `OMP_NUM_THREADS=1`: iterations 36 → 38; reduced_chi_square 9.731270484 → 9.731254057.

**Re-pinned 2026-11-09 to the CI build.** edi CI run 42607911778 (crysta `361b2b64`) stops this fit at 37 iterations
with reduced χ² 9.731261117 on both Linux and macOS: iterations 38 → 37; reduced_chi_square 9.731254057 → 9.731261117.
A local GCC build of the same sources stopped at 38; the fit ends on a Shift/s.u. knife edge that floating-point
contraction can move by one iteration, and the pin follows CI.

**χ² change, 2026-11-09.** Under Shift/s.u. this fit ends on a knife edge: the iteration count follows crysta's Jacobian
code path, which the machine selects (37 and 38 on CI hosts, 38 locally with SIMD, 39 on the scalar path), and no shift
tolerance moves it. The project therefore declares `_minimizer.stop_rule chi_square_change`, the one example that does,
under which every path stops at 36 iterations with reduced χ² 9.731270484: iterations 37 → 36; reduced_chi_square
9.731261117 → 9.731270484.

**Re-pinned 2026-11-10.** Fast descent is now the default descent. Measured with `python -m edi fit --report machine
--verbosity full` linked against crysta `697f33ee`, `OMP_NUM_THREADS=4`: reduced_chi_square 9.731270484 → 9.731273171;
asymmetry-off iterations 18 → 19; asymmetry-off reduced_chi_square 12.88691907 → 12.88658333. No `reference` value
moved.
