# Temporary macOS cadence contract

The baseline comes from the Git object named in `baseline.json`. Its test identities, workflow, group declaration and task definitions were captured before the cadence change. They are independent acceptance inputs, not generated from candidate workflows. Regenerate only from that same object with `generate.py`.

Linux regular CI keeps `quick` on pull requests and `full` on main pushes. Both retain every baseline identity and Linux gate command. The macOS groups are `macos-smoke` and `nightly-full`, declared in `tests/test-groups.json`. A group contains `tiers` (relative to `tests/`) and optional exact `nodes`; their union must be nonempty and contain no duplicate or unknown identity. The smoke retains the native unit tier, including arm64 numeric pins, and Python thread, scalar/SIMD, import and CLI witnesses. The nightly includes every baseline test. Edi adds the restored scale cases on Linux and macOS without changing their assertions or limits.

`ci-nightly.yml` schedules full main runs and supports manual candidate runs. Nightly and regular workflows have separate concurrency identities and do not cancel active work. A nightly does not publish an SDK unless its producer jobs retain the regular qualification cohort.

The group authority declares `execution_report.command`: an argv array for its result validator. Tests append:

```
--expected PLAN.json --report RESULTS.json --head SHA --run-id ID --attempt N --platform PLATFORM
```

`PLAN.json` is a nonempty JSON array of exact test identities. `RESULTS.json` contains `head`, integer `run_id`, integer `attempt`, `platform`, and `tests`, an array of objects with `nodeid` and `outcome`. An admissible receipt has each planned identity exactly once, all with `outcome: passed` except the exact pre-existing platform outcomes in the frozen `platform_nonexecution` map, and matching provenance. That map preserves the Linux-only filesystem injection and edi cases whose frozen default delegates execution to the WebAssembly job. It admits no xfails and no new exception; a passing result for a formerly skipped case remains valid. Empty selections, substitutions at equal counts, duplicate identities, skips, expected failures, failures and foreign provenance refuse. The normal workflow must produce and validate these records from actual execution; standalone validator controls do not establish that a full nightly has run.

The independent gates are under the repository's hidden system tier. The fixtures contain no passing candidate implementation and never supply merge evidence.
