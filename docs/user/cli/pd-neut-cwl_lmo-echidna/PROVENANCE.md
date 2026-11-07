# pd-neut-cwl_lmo-echidna — provenance

A layered LiNiO₂ model with Li/Ni mixing between its two cation sites, against ECHIDNA (ANSTO)
constant-wavelength neutron powder data.

## Sources

- **Model:** diffraction-lib's tutorial `refine-lmo-echidna` (develop `cb2cda7b`): the R-3m structure
  with Li1/Ni1 sharing 3b and Ni2/Li2 sharing 3a, the five constraints (each site's two displacements
  equal; Ni1 = 1 − Li1, Li2 = 1 − Li1, Ni2 = Li1 for the occupancies), the wavelength 1.6215 Å, the
  Thompson-Cox-Hastings profile with FCJ axial-divergence asymmetry (S/L = H/L = 0.08), the cylinder
  absorption µR 0.3, the excluded regions below 12° and above 162°, and every parameter the tutorial
  frees.
- **Data:** `data/ech_lmo.dat`, dataset `meas-lmo-echidna` of the repository `easyscience/diffraction`
  at commit `3ec801667904578ea39f1a4f4aa941866543a669` (path `data/measured/ech_lmo.dat`), sha256
  `11926e7692aa4d08aa91ea4f9d82a71fd4e42aa1dbd473d3f6b8394564310fd4`, licence BSD-3-Clause. The project
  embeds its 3200 points unchanged.

## Start

The start a user's own measurement would have, built by `tools/cli_projects/build_catalogue_projects.py`:
zero shift, sample displacement and sample transparency 0; U, V, W and Y at the tutorial's
one-significant-figure values (0.1, −0.3, 0.4, 0.1); Biso 0.5 on every site; O z 0.26; 5 % Ni on the Li site
(Li1 0.95, Ni1 0.05, and through the constraints Li2 0.05, Ni2 0.95), the mixing typical of LiNiO₂; a flat
line-segment background of nine points at the 10th percentile of the
counts; scale 10; the tutorial's cell (2.88, 14.18 Å). Free: cell a and c, scale, zero shift,
displacement, transparency, U, V, W, Y, the nine background points, O z, the Li1 occupancy, and the
Biso of O, Li1 and Ni2 (24 parameters; the constraints carry the rest).

**One stated change.** The FCJ geometry stays at the tutorial's instrument values, fixed, as the tutorial
has it. Started at 0 and free, no trial step from it could be evaluated and the fit stopped after one
iteration at R<sub>wp</sub> 30.5 %.

## Differences from the tutorial

- The tutorial's crysfml calculator and bumps (lm) minimizer are left out; edi uses its own calculation
  and minimizer.
- The tutorial estimates its background automatically before fitting; here it starts flat.
- O's displacement is free here: the tutorial keeps it fixed at its fitted value, which this start does
  not have.

## Result from this start (local diagnostic)

From this start edi converges in 18 iterations to R<sub>wp</sub> 5.00 % and reduced χ² 2.39, with
a 2.87514 Å, c 14.18322 Å, scale 15.85 and Li1 occupancy 0.985 (1.5 % Ni on the Li site).
diffraction-lib's own tutorial record reports R<sub>wp</sub> 5.02 %, reduced χ² 2.41, a 2.875254 Å,
c 14.18372 Å and scale 15.99. Zero shift, displacement and transparency are strongly correlated here: the
descent first meets its convergence test at R<sub>wp</sub> 13 % with the Li1 occupancy at its bound, and the
final linear step shows that this is not the minimum, so the descent goes on to 5.00 %. An edi built on an engine
that stops at that first convergence test ends at 13 %. The fully ordered start (Li1 1) reaches the same
minimum in 6 iterations, but FullProf cannot fit from it.

The regression pins for reduced_chi_square were retaken with `python -m edi fit <project> --report machine` using crysta `2b75771b` and its continuous axial-offset FCJ quadrature.

**Re-pinned 2026-11-04.** The project declares the Shift/s.u. stop rule (`_minimizer.stop_rule shift_su`, 0.1; the χ²
change still ends a fit when it passes first), as every example does. Pins retaken with `python -m edi fit --report
machine` linked against crysta `609586d9`, `OMP_NUM_THREADS=1`: iterations 6 → 5.

**FullProf references with the asymmetry off, 2026-11-07.** FullProf takes the FCJ aberration on a ladder of nodes and
edi continuously in the axial offset, so with S/L and D/L at 0.08 the two fits settle on cells several of edi's standard
uncertainties apart (a 2.87488 against 2.87516 Å). As for the Bérar-Baldinozzi examples, the full model is now compared on
R<sub>wp</sub> and the number of free parameters, and every shared value on the `asymmetry-off` variant, against FullProf's
fit with S/L and D/L at 0 (`knowledge/fitting/fullprof/pd-neut-cwl_lmo-echidna/asymmetry-off/`). That variant's edi fit
agrees with it (a 2.872489 Å, c 14.170136 Å in FullProf's).
