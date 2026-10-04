# threshold breach list — edi (quiet-box re-measured baseline)

Re-measured 2026-08-26 (refreshed post-move at `5047dd84` after the unit-tier disposition moves).
Python tiers: `pixi run per-pr-measure` (serial), start 1-minute load 1.71 against
`QUIET_THRESHOLD_LOAD_1M = 2.0`; in-run load samples (max 16.5) are the measured suite's own
unpinned-OMP threads (its crysta-consumer fits), not contention. C++ tier: one solo timed Release
run per case (process wall clock) at `e20b4012`, start load 1.76, max sample 1.76 — the three
previously declared `UNMEASURED` holes are closed at 0.006–0.009 s (startup floor 0.005 s) and
now survive regeneration (the foreign-value carry fix in tools/checks/per_pr_runtimes.py), so the
`unit/cpp` tier is measured with zero breaches and zero holes.

Added 42 native unit cases measured solo on 2026-09-01 with
`build/tests/core/edi_tests --duration=true --no-skip=true`. The initial combined shapes exposed
two bound breaches (0.110 s and 0.169 s); splitting the independent assertions, without dropping
any, reduced the slowest new row to 0.096 s. All 45 native rows are now banked.

⛔ Every bound is UNCHANGED. edi declares no fitting corpus, so the `fitting` bound does not
apply. This list replaces the 2026-08-25 baseline under the do-not-inherit rule; near-bound
members flip run-to-run at ±10 ms (three of the four new rows sit exactly at 0.100–0.120 s), and
the dispositions for the input list live in
`tests/threshold-dispositions.json`.

**Zero rows (2026-08-26, post step-5):** every tier meets its ruled bound with no exceptions.
The last row (the `c06_t2` fixture-cost guard) resolved WITH the step-5 marker retirement as a
ruling-39 deletion-with-a-note — its subject (the marker-based exclusion a module cost could
escape) no longer exists; the note naming the lost claim and the surviving coverage lives in
`tests/threshold-dispositions.json`.

**Two temporary rows (2026-10-01, edi PR #93):** the two five-bank NCAF WISH projects run their
pinned fit in the `system` tier and breach its 5 s bound. Owner decision (development hub
`knowledge/decision-records.md`, "edi PR #93's two five-bank fits land as temporary threshold
breaches until ") lands them as listed breaches, with the projects kept `executing: true`.
Cause:, the crysta engine running about 4x slower inside edi than on its own; the fix (edi
`b5f8352`, crysta `ce21eba6`/`a4d5c2cd`) is on the `-structure-categories` branches.
Removal condition: re-measure both nodes once merges into edi main, and drop each row whose test
then meets the 5 s bound. The runtimes were measured serially by
`pixi run per-pr-measure` from a start 1-minute load of 3.33, above the 2.0 quiet bound.

| tier | measured n | bound | breaches | % | max | unmeasured |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `unit/py` | 117 | 0.1 s | **0** | 0.0% | — | 0 |
| `unit/cpp` | 45 | 0.1 s | **0** | 0.0% | 0.096 s | 0 |
| `integration` | 102 | 1.0 s | **0** | 0.0% | — | 0 |
| `system` | 77 | 5.0 s | **2** | 2.6% | 72.180 s | 0 |
| **total** | **341** | | **2** | | | **0** |

## Breaches, per tier, slowest first

### `unit/py` — bound 0.1 s, 0 breach(es)

- none

### `unit/cpp` — bound 0.1 s, 0 breach(es)

- none

### `integration` — bound 1.0 s, 0 breach(es)

- none

### `system` — bound 5.0 s, 2 breach(es)

- 72.180 s — `tests/system/py/test_c34_t24_cli_variants.py::test_every_executing_project_runs_every_pinned_variant_from_project_data[pd-neut-tof_ncaf-wish-5bank_start-5-0]`
  - cause:, crysta about 4x slower inside edi (fix: edi `b5f8352`, crysta
    `ce21eba6`/`a4d5c2cd`, on `-structure-categories`). Remove when, re-measured after
    Merges into edi main, it meets the 5 s bound.
- 48.760 s — `tests/system/py/test_c34_t24_cli_variants.py::test_every_executing_project_runs_every_pinned_variant_from_project_data[pd-neut-tof_ncaf-wish-5bank_start-fullprof-0]`
  - cause:, crysta about 4x slower inside edi (fix: edi `b5f8352`, crysta
    `ce21eba6`/`a4d5c2cd`, on `-structure-categories`). Remove when, re-measured after
    Merges into edi main, it meets the 5 s bound.
