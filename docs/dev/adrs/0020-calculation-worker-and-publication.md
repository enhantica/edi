# ADR-0020 — The calculation worker and the publication transaction

- **Status:** Proposed (plan accepted 2026-10-02)
- **Date:** 2026-10-02
- **Implementation:** 🟡 Partially implemented — the worker, the transaction, the preview and the app's use of them
  are built; the fit on the worker (§9) and the app's Start fitting are built
- **Amended:** 2026-10-03 ([ADR-0023](0023-web-build.md)) — §1: built with `EDI_WORKER_OWNER_THREAD` (the
  single-thread WebAssembly build) the Worker starts no thread and runs each job on the owner thread, in its turn among the
  calls it posts there; every §1 guarantee holds, and the owner thread is busy while a job runs
- **Priority:** High
- **Forward constraint (binding on new features):** no app code calculates on the GUI thread, and nothing writes a
  calculation's result into the live project except `edi::publish`. Background work goes through `edi::work::Worker`;
  a result that is no longer the newest request is never shown.

## Context

The app calculated the pattern synchronously on the GUI thread after every edit (`ProjectViewModel::recalculate`).
Measured on 2026-10-02 at edi `4128c3bd`, one calculation takes 5 to 20 ms on a single-bank project, 48 to 66 ms on
a 50 000-point pattern and about 170 ms on the five-bank WISH project, so every slider move froze the window for
that long. The visualisation plan (2026-09-29) asks for a worker with a project snapshot, a request generation,
cancellation, rejection of stale results and publication on the GUI thread, and for a separate ordered stream that
a fit's iterations and result will use. The data contract's rule 07 asks for one transaction that publishes
everything a calculation produced, or nothing.

crysta has such a transaction for its own model. edi's model is separate, so edi needs the counterpart.
crysta's forward calculation has no cancel hook; only fits take one.

## Decision

### 1. Three Qt-free parts in the core

- **`edi::work::Worker`** (`edi/worker.hpp`): one worker thread. Jobs run one at a time in submission order. A job
  may emit deliveries and returns a final delivery; every delivery runs on the owner thread, exactly once, in order.
  A later submission never replaces, skips or reorders a job or a delivery. `cancel` only sets the job's token; a
  cancelled job still returns its final delivery. The destructor cancels every token, waits for the running job and
  delivers nothing afterwards. Deliveries reach the owner thread only through the `Post` function given at
  construction; in the app that is a queued invocation on the project view-model.
- **The transaction** (`edi/calculation.hpp`): `snapshot_for_work` copies the live project and records its stamps;
  `calculate` runs `Project::calculate()` on the copy, on any thread; `publish` compares every stamp with the live
  project and then writes every experiment's computed columns, residual and `_refln` and every structure's geometry,
  or writes nothing and answers `Superseded`. After `Published` the live project is in the state a direct
  `Project::calculate()` would have left, saved files included.
- **`edi::LivePreview`** (`edi/live_preview.hpp`): the preview protocol over the two.

### 2. Only the newest request publishes

Every edit is written to the live project at once and is a request. One calculation is in flight at a time; its
generation is the newest request's number when it is snapshotted. When its delivery runs, it publishes only if its
generation is still the newest request. Otherwise it is rejected: nothing is written and nothing is shown. A change
that is refused is not a request and wrote nothing (§8). After the last request exactly one publication follows,
for that request. A result
that the transaction refuses (a write that went round `LivePreview`) changes nothing, and one calculation of the
current state follows.

Between an admitted edit and the publication that serves it, the app keeps the last frame and says that it is one:
every experiment's pattern reports `stale`, and the chart's `current` is false, from the edit until the newest
request publishes. A rejected result does not clear it, and a refused edit does not set it.

The cost is stated, not hidden: when requests arrive faster than a calculation finishes, nothing publishes until they
stop. The owner kept this handling on 2026-10-02.

### 3. Thread ownership

The live project belongs to the owner thread. A job touches only its snapshot, which shares nothing mutable with
the live project. crysta is used from both threads with no global lock: each thread uses its own objects, which is
what crysta describes. crysta's type registries and edi's own peak-type table are not locked, so
`edi::register_peak_type` refuses while a `Worker` exists.

### 4. Cancellation is at checkpoints

A preview reads its token before the calculation and after it. A forward calculation in progress is not
interrupted. A fit reads the token between iterations, through crysta's `should_cancel`.

### 5. Latency is measured and guarded, never a limit

By the owner's decision of 2026-10-02 no latency value is an acceptance criterion. Every dataset is measured and
reported with the calculation's share, and a ratchet over committed medians, with a margin from measured run-to-run
noise, fails a later change that makes the chart slower. The measured tables are added here when the task closes.

### 6. The freshness encoding

`calculation_inputs` encodes the data arrays in bulk. Two encodings are equal exactly when every number has the same
bit pattern, as before; the encoding is compared in memory and never saved.

### 7. The calculation traces its own start and end

`edi::calculate` reports `Calculating` as its first act and `Calculated` as its last, through the snapshot's `trace`.
The two events are therefore inside whatever times the call, and a test's own clock around the calculation contains
the trace's interval. `LivePreview` no longer traces them around the call. A test seam that replaces the calculation
without running `edi::calculate` gets the pair when it returns.

The owner can count them: `LivePreview::Hooks::calculating` and `calculated` receive the same two events, for every
calculation the worker runs, a superseded one included. They are handed to the owner thread in the job's own ordered
stream (`work::Emit`), so each arrives in order and before that calculation's publication or rejection, and never after
the `LivePreview` is gone. The app announces them as `ProjectViewModel::calculationStarted` and `calculationFinished`.

### 8. An edit is one declared operation, and a refused one wrote nothing

`LivePreview::apply` takes an `edi::Edit` and nothing else. An `Edit` is made only by the named operations of
`edi/edit.hpp`; it cannot be made from a callable. The set is closed and in that one file.

No operation is a template. Each names the model's own types: an assignment, one of the model's plain fields (a flag,
recorded or plain, a number, a text, an optional integer, a text that records its writes) with a value of that field's
type; a recorded number has no assignment, so a parameter's value goes through its range check and a background point's
position through its own operation; a row operation, one of the model's collections (atom sites, background points and texture rows are added; those,
structures and experiments are removed) with a row of its own type. So the only code an `Edit` runs inside `apply` is
edi's and the standard library's: a value the caller converts is converted at the call, before the `Edit` exists, and a
row is copied by its model type's own copy. An id is written by a named operation that first refuses an item a
collection other than the model's own holds: a caller's keyed type derived from a model type would bring its own rename
rule (`KeyTraits`), which could write and then throw. Since the model's fields record their writes (ADR-0018), a
refusal must come before the write, never as a write undone: the texture axis checks the axis it would leave, and the
excluded regions check the row, before they write.

Each operation is all-or-nothing by its own stated rule:

- one assignment, which cannot fail, or whose field refuses before it writes (an id, refused by its collection);
- a validated setter, which checks first with the library's rule and message (`assign_value`, the analysis settings,
  the selectors, the renames);
- one collection mutator, which leaves the collection as it was when it refuses (ADR-0016 §2);
- several objects at once, checked whole and then added in one mutation (a batch of loaded experiments).

So an edit that is refused wrote nothing. The model, its write identities, its records, the request number and the
publication it holds are untouched because nothing touched them, and a calculation in flight still publishes. That
is the whole claim. The door has no rollback and makes no promise about one, and it makes no promise about a change
that is not an `Edit`, because none can be passed to it. An allocation failing inside an operation's write is outside
the claim.

The app's door (`ProjectEditor::apply`) takes the same type, so every app edit names its operation. An operation
the app needs and the set lacks is added to `edi/edit.hpp`, with the rule that makes it whole.

A generic rollback was built first and withdrawn (code reviews 1 to 3): `apply` took any callable, copied the
project before it and restored the copy when the callable threw. Three reviews in a row found a route it missed:
partial writes kept, the identity-bearing records not restored, rows moved between owners restored in an order that
refused. Undoing anything a callable might do to the whole object graph is a claim over every identity and
attachment the model has or will have. No caller in the product needs it: each app edit already was one core call.

### 9. A fit runs on the worker and writes the live project once, at its end

`edi::FitJob` (`edi/fit_job.hpp`) runs a fit as one job on the same worker:

- **The fit is the CLI's.** The job fits a snapshot of the project by its fitting mode, through the entry the CLI's fit
  takes (`edi.Analysis.fit`): `Project::fit` for `single`, `Project::fit_joint` for `joint`. The scan modes are not run
  here. So the app's fit of a project and the CLI's fit of the same project are the same computation.
- **The stream is ordered and never dropped.** The preamble, each accepted iteration and the end are deliveries in the
  job's own stream (`work::Emit`), the end last. Nothing of the fit is delivered after its end, and a closed
  `FitJob` delivers nothing.
- **Frames.** A streamed `IterationRecord` carries the step's parameter values by identity path, read from crysta's
  record. Between iterations, and only after the owner has shown the previous frame (`frame_shown`), the job writes
  those values onto a second copy, completes its symmetry, calculates it and delivers each experiment's pattern as a
  frame. A slow owner sees fewer frames; the fit's own copy is touched by the fit alone, so its numbers do not move.
- **Cancel** sets the job's token, which the fit reads through crysta's `should_cancel` between iterations. A cancelled
  fit ends with its partial result, as crysta returns it.
- **The end writes once.** On the owner thread, a fit that returned a result other than `ERROR` is taken only if
  nothing it depends on was written since the snapshot: the calculation stamps (`unchanged_since`, the comparison
  `publish` makes) and the fit's own inputs, which those stamps do not carry — every parameter's value, uncertainty,
  free flag and fit start write identities (an equal-value write included), the fitting mode, the minimizer settings
  and the banks' joint weights. Then
  `copy_parameter_states` writes every parameter's value, uncertainty and fit start from the fitted copy, and
  `publish` writes the pattern the fit's own last calculation left, staged under the stamps the live project now has
  (`stage_computed`). The live project is then in the state a direct fit would have left. Otherwise nothing is
  written: a refusal or a failed fit reports `ERROR` with its reason, a write during the fit `SUPERSEDED`.
- **The result is recorded** (the owner, 2026-10-02): `Project::fit` and `Project::fit_joint` record the fit's
  result on the project (`FitResultRecord`, diffraction-lib's `_fit_result` names plus the producing `descent`, so
  a reopened result names its own minimizer, with each bank's share of a joint fit on its experiment), the CLI's
  fit and the app's alike. Its `profile_function` and
  `background_function` name the peak profile and the background model (`_background.type`) the banks declared,
  each left out when the banks differ; a scan clears it, an undo clears it, and the job copies it onto the live
  project with the parameters (`copy_fit_result`). A save hands it to crysta's writer, which writes `_fit_result`
  and `_fit_result_bank` in `analysis.edi` only while one is held; a load reads it back, so a reopened project
  shows its last fit. A file without it loads as before, and a project without one saves its old bytes, so
  `analysis.edi` takes no schema step.
- **Undo** is an `Edit` (`Edit::undo_fit`): `restore_fit_start`, which is `undo_fit` without its calculation, runs on
  a copy, and the restored parameters are written onto the project; the door's calculation follows on the worker.

The app does not edit the project while a fit runs: the door refuses an edit then.

## Consequences

- The window stays responsive while a calculation runs; the chart, the tables and the saved text change together,
  when a publication arrives.
- Closing a project waits for the calculation in flight.
- A fit and a preview share the one worker thread. While a fit runs the app refuses edits, so no preview waits
  behind it (§9).
- Each frame of a running fit costs one calculation on the worker, at most one per frame shown.
- The web build has no thread yet: its executor is a recorded gap for E07 (ADR-0006), behind the same contract.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Hold slider values outside the model while a calculation runs, and publish each result | Rejected in plan review: an older result would publish after a newer value was requested |
| Build the presentation on the worker | Rejected: decimating one curve of 50 000 points takes about 0.2 ms, so the GUI thread builds it and a zoom needs no hand-over |
| One mutex around every crysta call | Rejected: it would stall the GUI thread for the whole background calculation |
| A Qt worker (`QThread`) in the app | Rejected: product logic lives in the core (ADR-0009), and the core tier is what CI runs |
| The door takes any callable, and a copy of the project taken before it is restored when it throws | Withdrawn after three code reviews each found a route the restore missed (§8): the guard is over everything a change might do to the object graph, so the class stays open |
| Stage a change on a copy and commit it back into the live objects by value | Rejected: the commit back is that same restore, now on every edit, and every change would have to address a project it is given instead of the objects it holds |
| The door takes any callable, and every caller must validate before it writes | Rejected: a rule the type does not hold is kept until the first caller that breaks it |
