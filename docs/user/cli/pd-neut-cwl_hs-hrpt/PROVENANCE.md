# pd-neut-cwl_hs-hrpt — provenance

Herbertsmithite, ZnCu₃(OD)₆Cl₂, against HRPT (PSI) constant-wavelength neutron powder data.

## Sources

- **Model:** diffraction-lib's tutorial `refine-hs-hrpt` (develop `cb2cda7b`): the R-3m structure, its
  sites, the wavelength 1.89 Å, the Bérar-Baldinozzi asymmetric pseudo-Voigt, and every parameter the
  tutorial frees in any of its four stages.
- **Data:** `data/hs-hrpt.xye`, dataset `meas-hs-hrpt` of the repository `easyscience/diffraction` at
  commit `3ec801667904578ea39f1a4f4aa941866543a669` (path `data/measured/hs-hrpt.xye`), sha256
  `6aaaf3318eb83e85adaa11082d7b49249aa85f593f0e8be85e33ce3c231ca4ef`, licence BSD-3-Clause. The
  project embeds its 3220 points unchanged (2θ, counts, uncertainty).

## Start

The start a user's own measurement would have, built by `tools/cli_projects/build_catalogue_projects.py`:
zero shift 0; U, V, W at the tutorial's one-significant-figure values (0.1, −0.2, 0.2) with mixing η 0.5
and all four asymmetry coefficients 0; Biso 0.5 on every site; the tutorial's free coordinates to two
decimals (Cl z 0.197 becomes 0.2); a flat line-segment background of ten points at the 10th percentile
of the counts; scale 0.5; the tutorial's cell (6.85, 14.1 Å). Free: cell a and c, scale, zero shift,
U, V, W, η, the four asymmetry coefficients, the ten background points, O x/z, Cl z, H x/z and every
Biso (32 parameters).

## Differences from the tutorial

- diffraction-lib's Bérar-Baldinozzi profile carries the Thompson-Cox-Hastings X and Y; edi's
  carries one pseudo-Voigt mixing η (`mixing_eta_0`, with `mixing_eta_1` fixed at 0), so η replaces Y.
- The tutorial estimates its background automatically before fitting; here the background starts
  flat.
- The tutorial frees its parameters in four stages; here they are free together from the start.
- The tutorial's minimizer tolerance setting is left out; edi uses its own minimizer.

## Result from this start (local diagnostic)

From this start edi converges in 9 iterations to R<sub>wp</sub> 5.30 % and reduced χ² 2.15, with a
6.86399 Å, c 14.1417 Å and scale 0.5115. diffraction-lib's own tutorial record reports R<sub>wp</sub>
5.05 %, reduced χ² 1.95, a 6.86397 Å, c 14.1418 Å and scale 0.511.

## The check against FullProf

FullProf and edi write the Bérar-Baldinozzi asymmetry in different forms, and no mapping of the four
coefficients makes them agree; crysta tracks this difference in the asymmetry convention as a known issue.
So `expected.json` compares the full model with FullProf's on R<sub>wp</sub>, within 5 %, and on the number
of free parameters only. Every other fitted value is compared on a second fit of both programs with the four
coefficients fixed at 0: the record's `asymmetry-off` variant against FullProf's fit in
`knowledge/fitting/fullprof/pd-neut-cwl_hs-hrpt/asymmetry-off/`.
