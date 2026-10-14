# Fit-quality inputs

The FCJ project is copied without numerical changes from edi's committed
`docs/user/cli/pd-neut-cwl_lab6-echidna_fcj-asymmetry/project`.
The two-start comparison is an invariance check, not a fitted golden.
The accompanying FullProf zero-start authoring trials are recorded in that
example's PROVENANCE.md. No test invokes FullProf.

`generate_gui.py` copies the existing editable GUI example and appends explicitly
chosen fractional metrics for two experiments sharing a phase. Corrected factors and
dimensionless chi-square have distinct values; these test display and lossless
storage, not fitted accuracy.
It also copies the rational normal-equation case from the pinned SDK source under
`build/crysta-src/tests/fitting/constraint-covariance/project`. The authoring source
was crysta `a1e0ba6da241d886259a58a3a6207903a923ce30`; those observations have the
independent polynomial target documented by that case. Re-run this generator after
`pixi run core-build` to reproduce the display input and the single, sequential and independent
uncertainty inputs. The scan inputs carry an authored prior uncertainty so undo
has a known state to restore after a scan fit.

## FullProf phase-factor subject

`fullprof/lbco.pcr` and `fullprof/lbco.prf` are the matched independent
input/output pair from diffraction-lib commit
`39ada82c8aef8b4657c4ae8c68e888668db0f38e`, directory
`docs/docs/verification/fullprof/pd-neut-cwl_lbco_basic/`.
The PCR SHA-256 is
`4ec747b9dc88dd798015d7061dccee6e9f31dc8f2448a82a943a0a965fd84581`;
the PRF SHA-256 is
`640490df5dd98482f561c7b1a3a7714ae860bc6fd709db1b40b37b5275dff1bb`.
The accompanying `lbco.sum` reports zero fitted parameters and supplies
R_Bragg 4.16% and R_F 4.38%.

`generate_fullprof_model.py` transcribes the PCR's cell, ADPs, occupancies,
profile, wavelength, zero offset, scale and background into `fullprof-model`.
The occupancies use the cubic general multiplicity 48 divided by the site's
multiplicity: 0.50016, 0.50016, 0.99984 and 0.97856, retaining PCR precision.
There is no preferred orientation term in the PCR; the generated model has
none. Every parameter is fixed. Included grid points and observations come
from the PRF; the matched corpus supplies their measurement uncertainties,
with exact observed-value agreement checked at every point.

Regenerate with this directory's PCR/PRF, the `lbco-hrpt-s2` corpus experiment
and an explicit output directory:

```bash
python tests/fixtures/fit_quality/generate_fullprof_model.py \
  --pcr tests/fixtures/fit_quality/fullprof/lbco.pcr \
  --prf tests/fixtures/fit_quality/fullprof/lbco.prf \
  --corpus <corpus>/project/experiments/hrpt.edi \
  --destination tests/fixtures/fit_quality/fullprof-model
```

The native phase gate calculates this fixed model and calls the public quality
API without a fit. It compares both phase factors to `lbco.sum`, using the
unchanged envelope derived from the existing fitted profile agreement.
The retained Python gate still fits the original corpus and checks its three
profile factors. Separate phase lifecycle gates retain actual fit, save,
reload and changed-free-set refit coverage. The fixed-model gate uses one
worker and restores the previous setting, avoiding a worker-team startup in
this small numerical reference.
