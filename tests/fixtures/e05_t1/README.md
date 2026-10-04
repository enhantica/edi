# CLI fit reference

`generate.py` executes `python -m edi fit` on private copies of every registered
single/joint CLI project. `cli.json`, `cli.hpp` and the full `.record` files freeze
that independent surface's fitted values, e.s.d.s, chi-square, status and iterations.
The manifest names the producer and SDK heads and hashes each input. No app or
FitJob result supplies an expectation. Elapsed times are provenance, never parity
expectations. Comparison uses the existing machine-record parity tolerance:
absolute 5e-10 and relative 5e-9 (`test_c09_t9_output_contract_and_cli.py`).

The core fit-stream gates expect the packet's FitJob next to LivePreview. The
initial executable interface follows LivePreview's owner-thread pattern:
`FitJob(Project&, work::Worker&, Hooks, Seams = {})`, `start()`, `cancel()` and
`running()`. Hooks carry `started(const FitPreamble&)`,
`iterated(const IterationRecord&)`, optional `frame(const FitFrame&)`, and
`finished(const FitReport&)`. `FitReport` carries `status`, optional `result`
(`FitResultBase`) and `refusal` (string). The final hook runs after atomic
write-back to the live project, or after refusal/supersession without write-back.
The optional test-only `Seams.polled(int)` observes the engine's cancel check
before the worker's token is read; production leaves it empty. Tests cancel the
actual worker token at a controlled check. Equivalent interfaces can be adapted.

The app gates click the production `fitting.start` control and observe
`ProjectViewModel.fit`: `running`, `status`, `iterations`, `goodnessOfFit` and
`results`. They use the app-bar Undo arrow and the actual `fit.results` dialog;
its Qt standard OK button closes it. Displayed metrics are compared at their
presentation precision (chi-square two decimals, Rwp four), while saved values
and parameters retain the machine parity tolerance. The CLI capture trace reads
parameters at the CLI's own `_fit` return boundary, before the writer rounds
values; it invokes the normal CLI entry point and performs no additional fit.

Gate 8's codec input is independent: `_fit_result` names come from diffraction-lib
`develop`, `src/easydiffraction/analysis/categories/fit_result/{base,lsq}.py`;
`analysis.py` defines objective chi_square and degrees of freedom. Synthetic time
123.375 tests the seconds conversion away from identity. CLI/app saves require
present positive time; they never compare a run's duration with a fixture's time.
Legacy committed projects remain inputs, with no changed committed project bytes.

`generate_stops.py` adds CLI-derived MaxIter and NoStep witnesses. Its documented
input edits create new projects under this fixture directory; no existing saved
project bytes change. The range-color gate uses the untouched input's
`ParameterSpec.range` with full-precision CLI fitted values, including the
negative Co1 ADP, and inspects the actual rendered value-cell color.

App timing captures owner-thread queued deliveries and animation timer work,
including the synchronous UI work they cause. Reports preserve raw samples and
feed `tools/ci/latency_bank.py --check`; an unbanked hand host only reports, while
a runner requires committed bank rows. Animation endpoint comparisons are
explicit regression checks against the prior instant presentation path.

`generate_refusal.py` commits a measured project with every parameter fixed and
the CLI's actual error report. Unlike a malformed file, it opens and calculates
before the fit fails. The popup Rwp comparison honors declared percent units
(the diffraction-lib `fit_helpers/reporting.py` convention multiplies by 100),
using two decimals for percent or four for a raw fraction.

Parameter-count oracle: `model_counts.json` comes from diffraction-lib
`Analysis._selected_parameters_for_fit`, never edi's all-family parameter walk.
The generator keeps the external count and selected names separately from the
engine-model projection: fixed TOF bank geometry is excluded; the declared TOF
coefficient slots and cylinder absorption fields, and CW asymmetry parameter
slots, follow the engine's declared model contract.
The external library commit, analysis source hash and every projection are
recorded. `generate_model_counts.py` runs in diffraction-lib's environment on
private copies; reader/backend labels are adapted, with model values unchanged.
Crysta's `generate.py` exports the two matching corpus cases from edi's fixture
directory. Before: `len(cli.json parameters)` (LBCO 61, NCAF three-bank 158).
After: the selected engine model (44 and 155), including fixed parameters.
All CLI values, uncertainties and the original project input bytes are retained.

`generate.py --only <new-project-id>` appends a newly registered single/joint
CLI oracle while retaining every existing case byte for byte. The appended case
names the actual imported artifact's linked engine source. Tests adds
`pd-xray-cwl_lif_single` after ; its two free polarization parameters are
fitted using the current engine. The independent selected-model count comes from
the same diffraction-lib selection and documented projection as the earlier cases.

's registered Chebyshev CeCoAl, polynomial PEARL and polynomial LaB6
examples append their author-time CLI records and native references without
replacing earlier oracles. The count generator's `--only` mode preserves prior
rows. Its external diffraction-lib selection maps the plain-power coefficient
storage to Chebyshev storage for counting only, supplies explicit term IDs, and
retains all coefficient values/free flags; it performs no fit or basis evaluation.
The manifest records that adaptation and retains previous provenance.

`background_projects.py` authors small closed-form inputs with independent
background declarations. The system gate crosses the public native fit/report,
delegated save, reload and historical-settings boundaries for all models and
mixed banks; it uses the prior line-segment path as a control.
For a publication-only metadata update, run
`python tests/fixtures/e05_t1/generate_model_counts.py --public-metadata`.
It removes private citations while retaining every scientific case byte and
the independent reference commit and source digest.
