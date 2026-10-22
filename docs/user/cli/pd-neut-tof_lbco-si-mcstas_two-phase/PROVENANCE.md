# pd-neut-tof_lbco-si-mcstas_two-phase — provenance

La₀.₅Ba₀.₅CoO₃ with a silicon impurity, against a time-of-flight neutron powder pattern simulated with
McStas.

## Sources

- **Model:** diffraction-lib's tutorial `refine-lbco-si-mcstas` (develop `cb2cda7b`): the two cubic
  structures, the bank at 2θ 94.909° with DIFC 58724.77 µs/Å (zero and DIFA 0, fixed, as the tutorial
  has them), the Jorgensen profile, the thirteen background points, the excluded regions below
  40000 µs and above 108000 µs, and every parameter the tutorial frees.
- **Data:** `data/lbco-si-mcstas.xye`, dataset `meas-lbco-si-mcstas` of the repository
  `easyscience/diffraction` at commit `3ec801667904578ea39f1a4f4aa941866543a669` (path
  `data/measured/lbco-si-mcstas.xye`), sha256
  `0aeab4909604e14c0b0263a7ba5c926b7fca9f8e4223421f4672ec641fc0c915`, licence BSD-3-Clause. The project
  embeds its 1000 points unchanged.

## Start

The start a user's own measurement would have, built by `tools/cli_projects/build_catalogue_projects.py`:
the Gaussian σ₀, σ₁, σ₂ and the rise and decay coefficients at one significant figure (50000, −50000,
20000; α₁ 0.01; β₀ 0.006, β₁ 0.004); Biso 0.5 on every site; the background points flat at the 10th
percentile of the counts; scales 4 and 0.2; the tutorial's cells (3.8909, 5.43 Å). Free: both cells,
both scales, σ₀, σ₁, σ₂, α₁, β₀, β₁, the thirteen background points and the Biso of Co and O
(25 parameters).

**One stated change.** The A-site (La, Ba) and Si displacements stay fixed at 0.5, as the tutorial keeps
them fixed. Freed with Co's, they traded off against it (Co went to −0.46 Å², La to 0) and the fit
stopped at R<sub>wp</sub> 18.2 %.

## Differences from the tutorial

- The tutorial's minimizer tolerance setting is left out; edi uses its own minimizer.
- The fixed displacements are 0.5 Å² here; the tutorial's are 0.2 (La, Ba) and 0.89 (Si).

## Result from this start (local diagnostic)

From this start edi converges in 24 iterations to R<sub>wp</sub> 5.04 % and reduced χ² 4.16, with LBCO
a 3.89027 Å, Si a 5.43249 Å and scales 42.5 and 0.309. diffraction-lib's own tutorial record reports
R<sub>wp</sub> 4.59 %, reduced χ² 3.45, a 3.89045 and 5.43284 Å and scales 39.7 and 0.331. The scales
differ by about 7 % because the fixed displacements differ. Started from the tutorial's own values, edi
reaches R<sub>wp</sub> 4.58 % and scales 39.70 and 0.331.
