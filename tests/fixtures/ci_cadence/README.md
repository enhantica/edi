# Shipped CI cadence policy

The macOS and heavy Linux deferrals are already part of the accepted CI
policy. These regression inputs preserve their platform and event selections.
Nightly health reports a failed run with an issue; merge blocking is deferred. The earlier proposed
`macos-smoke`/`nightly-full` groups, separate `ci-nightly.yml`, and JSON execution
collector/validator interface are not requirements of this remaining task.

Before this correction, the passenger gates still demanded that superseded
interface and froze Linux's pre-deferral selection. After, the gates retain the
independently merged fast-path policy and exercise the drivers it actually uses.
`generate-shipped-policy.py` captures named accepted Git objects (crysta
`c7cfdf62`, edi `a341b981`) into `shipped-policy.json`; it never reads candidate
files. These are labelled regression inputs. The normative expectation is the
committed owner cadence policy: retained tests still execute in their declared
platform/event cohorts and failed execution cannot become successful evidence.

The original `baseline.json` retains every frozen identity and source-level
nonexecution obligation from its named Git object. Native case labels are stored
as SHA-256 identities, with the source path retained; the live inventory uses the
same encoding. Frozen Python node names retain their original spelling. The generators read the
original Git objects before encoding native labels, so the snapshot contains no
private process labels. The source audit is split into bounded batches,
with every original file and assertion retained. Edi's pre-existing deferred
scale source remains preserved, with its body/limit/fixture mutation controls;
restoring it was part of the superseded nightly design, not the reshaped scope.

`identity_migrations.py` names Python witnesses that were renamed or split after
the shipped snapshot. The cadence gate requires every successor and leaves
unmapped identities unchanged. Removal controls exercise each successor in both
ordinary execution groups; a migration cannot excuse dropping a test.

The current workflow's suite steps run as real Bash with an observed Pixi process
boundary. Accepted main supplies the required task calls and deferral environment.
Controls remove, skip, make advisory, swallow, relocate or empty a selected step.
The shipped Python-tier/system-part Bash drivers also execute: only their
expensive pytest/coverage subprocess is replaced. Assertions check the exact
selected roots, nightly exclusions, partition arguments and propagated process
exit status. Empty or invalid configuration must refuse before that boundary.
No test claims that these local controls are hosted CI evidence.

The earlier synthetic execution-path interpreter controls remain as regression
coverage of Actions expression, shell/environment, prerequisite, SDK qualification
and concurrency interpretation. Their planted JSON interface is a model input,
not a required product API. Actual nightly health and request retention are
independently gated in the hub. The real workflow uses schedule-separated
concurrency; preserving PR work is the coalescing requester's responsibility.

The bounded Actions model uses the documented loose numeric equality, case-insensitive string comparison and lowercase boolean rendering. Single-quoted literal contents are preserved, and `&&`/`||` retain the selected operand. Unsupported syntax, values and string conversions refuse explicitly. Runner-label arrays resolve structurally; they are not converted as expression strings. The cadence, prerequisite, execution-environment and SDK qualification consumers share this model. Concurrency compares case-insensitive group identities and distinguishes actual job keys and matrix instances independently of display names. Expectations come from the [Actions expression specification](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions) and [concurrency specification](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency), with edi's existing `e09_t75_workflow.py::actions_equal` as prior art; candidate workflows supply no expected semantic values.

The numeric-string boundary follows the [runner's `ParseNumber` behavior](https://github.com/actions/runner/blob/main/src/Sdk/DTExpressions2/Expressions2/Sdk/ExpressionUtility.cs): supported finite decimal forms include whitespace, a leading sign, leading zeros, decimal points and exponents. Hexadecimal/octal strings and nonfinite conversions explicitly refuse. Case identity is bounded to ASCII, avoiding Python Unicode folding as a substitute for the [runner's ordinal case comparison](https://github.com/actions/runner/blob/main/src/Sdk/DTExpressions2/Expressions2/EvaluationResult.cs). Unicode expression comparison and concurrency groups explicitly refuse; literal rendering preserves their contents.

## Review 18: retained Linux non-suite checks

Before this repair, `test_linux_keeps_frozen_groups_and_gate_commands` and
`test_linux_task_closure_cannot_reduce_the_frozen_execution` had been removed.
Their suite-only replacement admitted an unchanged step name with `run: true`.
Both named checks are restored for `pull_request` and the landed-head `push`.
They use the independently accepted shipped workflow and Pixi declarations;
the visible shipped-policy generator now also captures exactly the executable
source closure previously protected by the original baseline. The original
baseline remains unchanged. Declared nightly deferrals keep their shipped
policy; activation SDK pins are separately governed, not executable task code.

The restored gates preserve Linux job/matrix identities, required status,
step eligibility, shell/environment, non-suite commands, selected task
dependency commands, and the previously protected script bodies. Controls
replace the same-named cppcheck gate (crysta) or static-policy gate (edi) with
`true`, omit/duplicate/skip/weaken it, add a file-dependent execution condition,
move its runner, replace a selected
Pixi task, drop its build dependency, and replace the protected C++ driver.
These are bounded contract controls, not executions of the expensive gates.

## Accepted system-part policy after the app-sharing merge

Edi main `a341b98154b53ea2499213a6c60b87e1371e9ce8` supersedes
`bd72193898d2dc6fefb1d692703d1f7a4137c731` for these regression inputs.
It is the independently merged app-sharing policy, not the candidate branch.
The original `baseline.json` and its protected execution-source path set stay
unchanged. The shipped snapshot continues to capture that whole path set from
the accepted main object, including the selected task dependency commands.

| Event           | Former Linux selection | Former macOS selection            | Current selection on both platforms                   |
| --------------- | ---------------------- | --------------------------------- | ----------------------------------------------------- |
| Pull request    | Full system tier       | Exclude the three `nightly` paths | Exclude exactly the thirteen `nightly-only` paths     |
| Main push       | Full system tier       | Full system tier                  | Exclude exactly the thirteen `nightly-only` paths     |
| Schedule        | Full system tier       | Full system tier                  | Full system tier, including every `nightly-only` path |
| Manual dispatch | Full system tier       | Full system tier                  | Exclude exactly the thirteen `nightly-only` paths     |

The former driver used `EDI_SKIP_NIGHTLY_GROUP=true` for the macOS PR
deferral. The current driver excludes `nightly-only` by default, and includes it
only when `EDI_RUN_NIGHTLY_ONLY=true`; the accepted workflow sets that value
only for `schedule`. The receipt adapter maps its existing `full-cohort` control
to `true` and its `pr-deferral` control to `false`. The workflow controls observe
the actual switch on every platform/event pair, so reverting to the obsolete
skip flag cannot silently select a different cohort. Empty configuration, exact
exclusions, partition identity and nonzero process outcomes remain checked.

This adopts the accepted app-sharing merge described by the 2026-10-13
conductor decision narrowing the once-per-run probe work to nightly. Every
required Linux job, non-suite command and frozen executable closure is still
checked against that accepted policy; schedule-only system observers do not
authorize dropping regular Linux gates.

## Owner event policy of 2026-10-19

Owner records `682968ba1` and `7552dbd4b`, packet items 6 and 8, supersede
these historical PR cohorts. `event_policy.py` applies only those declared
changes to the original Git snapshots; both generators use it. Snapshot
inventories, assertions, task declarations and protected source closures retain
their independent original provenance. The snapshots name this overlay explicitly.

| Operation                         | Pull request | Main push      | Schedule | Full manual |
| --------------------------------- | ------------ | -------------- | -------- | ----------- |
| System parts, Linux and macOS     | Omitted      | Required       | Required | Required    |
| WebAssembly job                   | Omitted      | Required       | Required | Required    |
| ThreadSanitizer, Linux            | Omitted      | Required       | Required | Required    |
| App Python group, Linux and macOS | Omitted      | Required       | Required | Required    |
| Shard-time comparison             | Omitted      | Required route | Omitted  | Omitted     |
| `nightly-only` system files       | Omitted      | Omitted        | Included | Included    |

Before, artifact and timing routes required same-repo PR execution and the
collector asserted the PR head SHA. After, artifact sharing is exercised on all
three full-run events, and the timing route consumes the current push SHA versus
the selected previous main push. Distinct planted push and PR SHAs prevent an
obsolete PR operand from passing. Existing mutation identities are retained;
the historical timing test name does not define its event policy.

The retained Linux command and task-closure gates now cover all four events.
Missing-job, skipped, advisory and wrong-command/prerequisite controls exercise
each moved gate on each full-run event and on both declared desktop platforms.
The actual suite-step shells still propagate injected process failures.
No slower job or step becomes optional on push, schedule or full manual runs.

## Git messages and branch answers

Before, the source closure required the original remote helper byte for byte,
and git's redirect warning joined the branch answer. After,
`accepted-remote-streams.json` admits exactly the helper's stdout/stderr split,
with all other code frozen. `generate-remote-streams.py` reads both sides from
the named Git change; these are regression pins, not an independent oracle.
The original baseline and shipped snapshots stay unchanged. The source-fetch
observer supplies both output variables while preserving its command, failure,
ownership and source-stamp checks.

Independent planted replies exercise a valid ref and proven absence alongside
redirect warnings. A second ref, malformed stdout and a failed lookup still
refuse. Credentials planted in successful warnings, failure messages and
malformed answers must never appear in public output. Removal controls protect
the stream capture, temporary-file cleanup, retry bound, exact ref, single-answer
check and redaction.

Leading shell comments share cached command observations with the same body,
so the comment-only control no longer repeats the same subprocess scenarios.
Body changes and failure injections still receive their own observations.
