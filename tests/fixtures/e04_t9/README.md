#  measurement inputs

`stress.hpp` is the deterministic D3 generator specified by the accepted packet P12.
It linearly interpolates the committed echidna measured values and uncertainties to
50 000 points, retaining both axis endpoints. It generates inputs only.

The hidden standalone sources are `tests/unit/cpp/e04_t9_latency_probe.cpp` and
`tests/unit/cpp/e04_t9_tsan_probe.cpp`. The former writes `latency-table.json` to
its working directory and prints the same JSON. Its optional first argument is
the source root containing the committed CLI projects. It accepts no bank argument and
never reads a bank. The latter must be compiled with ThreadSanitizer and run with
`OMP_NUM_THREADS=1`; a non-instrumented build refuses.

The measurement table contract is JSON schema 1, with `machine`, `commit`,
`samples`, `warmups`, and a `rows` list. A row identifies `dataset` (`D1`, `D2`,
`D3`) and `scenario` (`S1`, `S2`, `S3`); its `latency`, `calculation`, `wait` and
`overhead` objects each carry `median_ms` and `p95_ms`. S3 additionally carries
`presentation` with the same two statistics. Core measurement uses the test's
clock and requested-state observation; the table is measured evidence, not a
correctness reference.

The banking tool's checking seam is `python tools/ci/latency_bank.py --check
--table <table.json> --bank <bank.json>`. The bank is schema 1 with a `machines`
map keyed by the table's `machine`; each value has a `rows` list. Bank rows have
the same dataset/scenario identity, `commit`, `run`, and `metrics`. Ratcheted
metric names are `latency`, `overhead` (S1/S2), `presentation` (S3). Each metric
has `banked_ms`, `margin_ms`, and `values_ms` (the ten original run values).
The check compares medians in both directions, uses inclusive limits, refuses
missing CI rows, and reports an unbanked hand host. The command exits nonzero
for a regression or a re-bank obligation, printing the reason. These are the
accepted L6-L8 rules, with a concrete serialization for the banking seam.

For reproducible processing of retained fleet measurements, the writer also
accepts `--measurements <directory> --bank <bank.json>`, with exactly ten
`*.json` tables from the same machine and commit. The same bank assembly used
after ten real probe runs consumes those tables. This seam permits closed-form
tests of the median and noise margin without timing the host ten times.
