# Shipped CI cadence and reshaped E09-T79 policy

The owner reshaped E09-T79 on 2026-10-11. The packet's governing Reshaped scope
section says the macOS and heavy Linux deferrals already shipped, and limits
remaining acceptance gates to the remaining work. Nightly health reports a
failed run with an issue; merge blocking is deferred. The earlier proposed
`macos-smoke`/`nightly-full` groups, separate `ci-nightly.yml`, and JSON execution
collector/validator interface are not requirements of this remaining task.

Before this correction, the passenger gates still demanded that superseded
interface and froze Linux's pre-deferral selection. After, the gates retain the
independently merged fast-path policy and exercise the drivers it actually uses.
`generate-shipped-policy.py` captures named accepted Git objects (crysta
`c7cfdf62`, edi `bd72193`) into `shipped-policy.json`; it never reads candidate
files. These are labelled regression inputs. The normative expectation is the
committed owner cadence policy: retained tests still execute in their declared
platform/event cohorts and failed execution cannot become successful evidence.

The original `baseline.json` remains immutable and retains every frozen identity
and source-level nonexecution obligation. The old inventory generator still
reproduces that named Git object. The source audit is split into bounded batches,
with every original file and assertion retained. Edi's pre-existing deferred
scale source remains preserved, with its body/limit/fixture mutation controls;
restoring it was part of the superseded nightly design, not the reshaped scope.

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
