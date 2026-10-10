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

The independently authored `policy.json` fixes exact behavioral smoke witnesses and full-nightly job/step identities. These expectations do not come from new workflows or their candidate health contract. Each required event and platform must connect its real selected Pixi environment, task closure, collector, validator, and artifact in one required job. Conditions, runner architecture, prerequisite jobs, failure propagation and qualification are checked at that boundary. Workflow and job concurrency are evaluated across branches, workflows and consecutive runs: queued predecessors must also survive, so a shared concurrency group is insufficient even with cancellation disabled.

Declare `execution_report.run.command` as the collector argv. The process controls append `--group GROUP --platform PLATFORM --output-dir DIR`; native controls additionally append `--native-binary PATH` to execute a planted doctest-shaped transport. The collector writes `DIR/expected.json` and `DIR/results.json`, binds GitHub head/run/attempt variables, and returns nonzero for failed or unexecuted selections. Python controls execute planted nodes in every Python tier, including edi app integration; native controls execute unit, integration and system identities. The normal workflow validates and uploads that exact directory. The planted transports make no product numerical claim.

The new `test_ci_native_modes.py` witness runs the selected SDK in separate scalar and SIMD processes, checks real dispatch counters, and compares the same nontrivial Jorgensen–von Dreele pattern with the existing ADR-0035 tolerances. It replaces no native unit pin.

Execution tracing supports the default Bash shell and explicit `bash`, the repository-root working directory, and merged workflow/job/step environment values. Custom shells, other working directories and shell-initialization/probe overrides refuse explicitly. Named collector tasks accept no trailing arguments or `--skip-deps`; the frozen SDK pack task forwards its required positional arguments. These bounded forms are exercised on Linux regular groups, macOS smoke and both scheduled/manual full groups. Collector and validator overrides are exercised separately. SDK qualification uses the same boundary; crysta controls admit paired Linux/macOS producers before independently damaging either producer. The tracer runs in its own temporary directory and cannot perform relative build cleanup in the product checkout.

Concurrency resolves each configured supported event and its matching main, slot or repair ref. Consecutive push, schedule and manual runs receive the same queued-successor protection as PR runs, at workflow and job scope.

The restored scale source is compared against the frozen executable AST, including imports, fixtures, assertions and limits; only the module docstring may change. Mutation controls reject weakened or missing bodies. Both regular Linux groups must retain every frozen small-scan identity.
