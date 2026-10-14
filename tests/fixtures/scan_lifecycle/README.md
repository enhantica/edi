# Sequential scan terminal observation

The normal CI-built app runs `--test-observer scan-lifecycle <project>` only
with `EDI_TEST_OBSERVERS=1` and the existing pytest context. No fixture compiles
an app or uses a private observer executable. The input is a disposable copy of
the retained three-temperature Co2SiO4 scan; two and three-file cases exercise
counts derived from the independently authored file list. One minimizer
iteration keeps this a lifecycle observation, without claiming convergence or
independent diffraction accuracy. The app must fit all files rather than cancel.

The observer opens that exact project, attaches to every signal declared in
`FitViewModel`'s public signal section, calls the ordinary fit Start once, and
records each signal with a monotonic timestamp and freshly read live properties.
It writes one JSON document to stdout after the scan ends and the quiet window
elapses. The normal app remains open, connected and processing events throughout
that window; it must not cancel, close/reset the project, disconnect its signals
or suppress their delivery to obtain a quiet result.

The document contains `project`, actual `mode`, discovered `files`,
`signals_watched`, and ordered `events`. Each event has `kind` (`signal` or
`sample`), `ms`, and `running`, `scanning`, `scanProcessed`, `scanFitted`,
`scanTotal`, `scanProgress`, `elapsed`, `iterations`, `status`, `outcome`,
`scanText` and `eta`; signal records additionally identify `signal`. Attach before
Start. Capture the real `scanFinished` boundary, followed by at least an immediate
sample and a final sample after `quiet_ms` in `interface.json`. Any fit signal
arriving in that interval remains in the trace and makes the gate fail.

The 1200 ms quiet window exceeds the status timer's one-second cadence. Successful
completion is independently checked against every input filename and actual
`analysis/results.csv` rows. Counter/progress/read-only state expectations come
from input cardinality and terminal invariants, not engine-generated goldens.
The controls exercise idle-only, missing-end, still-running, over-counting,
late signal, changing elapsed text, short observation and nonfinite traces.
