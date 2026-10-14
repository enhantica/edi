# Paired normal-app scan observation

The nightly producer consumes two already-built normal apps and builds neither
app nor SDK. It invokes the shared DemoDriver `perf-162f` scenario:
`edi_app --demo <output> --demo-only perf-162f`, with
`EDI_DEMO_PERF_PROJECT` naming a fresh copy of the same stripped project.
The shared `strip_fit_state.py`, `compare.py` and `check_cli_run.py` live
here with repository formatting and context-managed file reads; their algorithms
are unchanged. Both desktop and CLI timing callers use these shared helpers.
`check_cli_run.py` checks CLI result rows before Reset; the desktop scenario
checks all 162 converged rows itself before recording fit time, then checks
cleared results/correlations, restored values and available Undo after Reset.
It waits for completion calculations before recording either interval.

Run `python -m pytest tests/fixtures/scan_pair/measure.py` as an explicit nightly
producer step, then the declared nightly tests with `EDI_SCAN_PAIR_EVIDENCE`
naming its JSON. An absent artifact fails. The producer records raw DemoDriver
TSV, actual exit status, binary/SDK build receipts, caller process boundaries,
common input digest, host, order and current run/head. It computes no verdict.
Fit and Reset milliseconds are added, then the shared comparator tests their
ratio of medians at 1.05. Five fresh pairs alternate order, with one warm-up per
app. Either build's spread above 3% is inconclusive and fails. This measurement
quality limit leaves the performance bound unchanged. Startup/preparation are
excluded. Actual Start, terminal work and settled Reset are included.
The scenario must retain adaptive updates, following, the visible chart and
unmodified solver settings. A fresh demo config retains those normal defaults.
Do not use the partial/refused scenarios or a delay environment in a real pair.
Those are negative controls of work completion and timing boundaries.

The separate short resume witness uses the normal-app test observer switch
`EDI_TEST_OBSERVERS=1`, which requires actual pytest context and refuses ordinary
launches: `edi_app --test-observer scan-cycle <project> resume`.
Publish `ready` after opening settles. Each JSON event carries the supplied
project, actual compiled app/SDK identities and fit running/scanning/counters.

The producer sends `{"command":"start","nonce":"..."}`. Report the same
nonce on subsequent documents. `inner_fit_started` identifies the actual inner
numerical fit and has `file` plus the free-parameter `start_values` map; a generic
processed-file callback or a replayed CSV row cannot replace that observation.
`file_fitted` reports actual fitted files. A `terminal` document is emitted on
the next event-loop turn after the scan is finished and its completion work
settles, with running/scanning false and the final counters. It also includes
the displayed terminal result's `success`, `iterations`, `reduced_chi_square`
and the actual model's `parameter_values` map. A completed resume acknowledges
Start without starting a worker and emits `terminal` with no inner-fit events.
For a completed scan, use the ordinary dataset selector to show the last
processed row before publishing ready; its persisted per-file result and model
values are then the displayed terminal projection. Do not make unavailable
Start launch a worker merely to produce an observation.

For `resume`, connect every public FitViewModel signal before Start. Name the
connections in ready.signals_watched and emit fit_signal with its signal name
for every actual emission, including after terminal. Report the complete
inner-fit/file-fitted event stream and then
wait live for 1200 ms after terminal before `quiet_complete`; the state and fit
signals must remain unchanged in that window. This is outside performance
measurement. The observer must keep its actual signal connections alive.

A bundle is a directory with `edi_app` and `receipt.json`. The receipt records
schema 1, `kind: normal-app`, `edi_commit`, `crysta_commit`, the executable
`binary_sha256`, and the shared observer's `observer_sha256`. The commits must
be the actual build identities, confirmed by build receipts and the executed binary hash. The
reference is the merge named in interface.json, with the observer only
backported; its app/core and SDK production contents must remain those commits.
Candidate/reference observers have the same instrumentation digest. The job
must retain the source/artifact build receipts; invented provenance is refused.
