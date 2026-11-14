# Machine report schema projection

Machine schema 9 adds stopping-rule metadata to the CLI report. This directory's
`migrate_report_schema.py` projects the existing CLI/native report fixtures into
that wire version. It does not run a fit. `schema9-projection.json` names the
exact committed source and before/after hashes of every projected artifact.
The unit gate reverses the projection and requires every original captured byte.

Only the leading schema value and the three added stop rows change. The older
captures did not observe those rows. They therefore carry the defined unavailable
metadata (`stopping_rule=none`, `stopping_value=nan`, `last_shift_su=nan`), rather
than an invented stopping rule or numeric observation. The new rows immediately
follow Rwp. All captured values, histories, timings, tolerances, reference labels,
input custody and producing-engine provenance remain from their original era.
This projection is not a new capture, and does not claim a current fit has unknown
stop metadata. Current numerical contract tests check the stopping values.

The CLI JSON and C++ views use the same projection; the existing artifact writer
is reused without importing or executing the engine. Re-running the visible
migration at its recorded source commit reproduces the projected artifacts.
Historical engine records, raw timing captures and older frozen goldens retain
their original schema; they remain references to the measurements they describe.
