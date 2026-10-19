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
  the job prepares the complete parameter-row join, owning fit-result record and the fitted copy's computed
  arrays before its first live write. The internal `PreparedPublication` (`core/src/publication.hpp`) also resolves
  completed dependents and allocates every computed/geometry source and encoding buffer in that preparation.
  Preparation failure reports `ERROR` through the ordinary finished callback with accepted state unchanged; stale
  inputs report `SUPERSEDED`. Only a fully prepared bundle writes the conditional scalar states, moves its record
  and bank shares, then publishes the fitted arrays without replacing identity-bearing model rows. The live
  project is then in the state a direct fit would have left.

  The first manual FitJob path and ordinary `publish`/LivePreview share this preparation/commit boundary. The
  synchronous owner-thread commit changes no collection shape, text or measured data. Scalar values and write
  identities have fixed-width canonical encodings, so source buffers prepared at their complete width can be
  refilled without growth after scalar writes; no anisotropic-parameter temporary vector is built there. Array,
  geometry and record moves are nonthrowing. An injected publication-preparation failure cannot publish a partial
  fit or skip its finished callback. This boundary does not claim that every controller/native/UI terminal,
  worker-start or continuation failure has been implemented or verified.

- **The result is recorded** (the owner, 2026-10-02): `Project::fit` and `Project::fit_joint` record the fit's
  result on the project (`FitResultRecord`, diffraction-lib's `_fit_result` names plus the producing `descent`, so
  a reopened result names its own minimizer, with each bank's share of a joint fit on its experiment), the CLI's
  fit and the app's alike. Its `profile_function` and
  `background_function` name the peak profile and the background model (`_background.type`) the banks declared,
  each left out when the banks differ; a scan clears it, an undo clears it, and the job copies it onto the live
  project in the prepared parameter/result commit. A save hands it to crysta's writer, which writes `_fit_result`
  and `_fit_result_bank` in `analysis.edi` only while one is held; a load reads it back, so a reopened project
  shows its last fit. A file without it loads as before, and a project without one saves its old bytes, so
  `analysis.edi` takes no schema step.

- **Undo** is an `Edit` (`Edit::undo_fit`): `restore_fit_start`, which is `undo_fit` without its calculation, runs on
  a copy, and the restored parameters are written onto the project; the door's calculation follows on the worker.

The app does not edit the project while a fit runs: the door refuses an edit then.

### 10. The engine's thread count

The Develop preference "Engine threads" (ADR-0017 §12) sets how many threads crysta uses for every fit and
calculation in the process.

- **Auto** (0, the default) keeps the engine's own thread policy, which honours `OMP_NUM_THREADS` when it is set.
  **A count N** replaces that policy and the environment: the user chose it, so the environment does not override it.
- **Saved per machine**, under `develop/engineThreads` in the app's settings file, never in a project.
  `Globals/Preferences.qml` applies it once the window is complete and again on every change.
- **Process-wide.** `edi::set_engine_threads` hands the count to crysta, and each parallel fill reads it when it
  starts, on whichever thread runs it (the worker, a fit job). Nothing is set per thread, because OpenMP's own setting
  would reach only the thread that made it.
- **The whole team takes part.** With a count N, a fill split into at least N chunks runs on N threads. On the
  desktop the count is the OpenMP region's team. In the multithread web build crysta's own pool starts threads when
  first asked for them and keeps them; a fill waits a tenth of a second at most for the N − 1 threads it admits to
  join, and each then takes its own share of the chunks, so the calling thread cannot finish the work before the
  others start. A browser that cannot start a worker in time gets a fill on the threads that did start, never a stalled
  one.
- **No result depends on it**: a fit or a calculation gives the same numbers for every choice.
- The single-thread web build has one thread and shows the preference disabled. The diagnostics show the preference
  and the engine's resulting worker count.

## Consequences

- The window stays responsive while a calculation runs; the chart, the tables and the saved text change together,
  when a publication arrives.
- Closing a project waits for the calculation in flight.
- A fit and a preview share the one worker thread. While a fit runs the app refuses edits, so no preview waits
  behind it (§9).
- Each frame of a running fit costs one calculation on the worker, at most one per frame shown.
- The web build has no thread yet: its executor is a recorded gap for E07 (ADR-0006), behind the same contract.

## Alternatives considered

| Alternative                                                                                       | Verdict                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hold slider values outside the model while a calculation runs, and publish each result            | Rejected in plan review: an older result would publish after a newer value was requested                                                                                   |
| Build the presentation on the worker                                                              | Rejected: decimating one curve of 50 000 points takes about 0.2 ms, so the GUI thread builds it and a zoom needs no hand-over                                              |
| One mutex around every crysta call                                                                | Rejected: it would stall the GUI thread for the whole background calculation                                                                                               |
| A Qt worker (`QThread`) in the app                                                                | Rejected: product logic lives in the core (ADR-0009), and the core tier is what CI runs                                                                                    |
| The door takes any callable, and a copy of the project taken before it is restored when it throws | Withdrawn after three code reviews each found a route the restore missed (§8): the guard is over everything a change might do to the object graph, so the class stays open |
| Stage a change on a copy and commit it back into the live objects by value                        | Rejected: the commit back is that same restore, now on every edit, and every change would have to address a project it is given instead of the objects it holds            |
| The door takes any callable, and every caller must validate before it writes                      | Rejected: a rule the type does not hold is kept until the first caller that breaks it                                                                                      |

The first manual FitJob owns its actual completed FitReport. The existing finished callback borrows it
on the owner thread until the next admitted start or destruction; failed start preparation preserves
that borrow. The final Outcome and delivery are prepared before worker submission. Worker-side
preparation failure returns that existing delivery rather than allocating another terminal after the
optimizer. Publication still prepares every owning result/computed buffer before any live scalar write.
A failed finished consumer cannot destroy the real report, and teardown disables publication before
cancelling and releases owners without throwing. This shares report lifetime with assistant trials;
there is no extra public report getter or separate fitting backend. The Worker's existing queued,
ordered delivery contract remains required; arbitrary external Post/trace transport failure is not
converted into a fabricated scientific result.


## Post-fit relation fingerprints

Prepared publication must describe the same adopted scalar state in computed and geometry sources. Relation currentness includes alias target values and their last-write identities, even for an unused alias. Preparation resolves the existing name join and records fixed-width value/write-ID offsets in the exact canonical relation encoding, checks those slots before any live scalar write, and prepares all owning source strings. Commit refreshes those existing slots after fitted/completed values are written, for both source families. It performs no map construction, declaration traversal, string resizing or allocation. The canonical byte format remains two sixteen-character lowercase hexadecimal words for each present target's double bits and write identity.

This owns the existing PreparedPublication path shared by FitJob and ordinary calculation publication: retained data, geometry and relation stamps must all refer to the adopted state. Existing full preflight/stale/manual-edit rejection is preserved; no second expensive calculation, chart-only repaint, ignored currentness, changed optimizer strategy or weakened scientific expectation is used as a repair. Alias-free, repeated-target, missing-target and dependent-value cases follow the same existing encoding semantics. Exact owner-project/platform reproduction and real actor results remain separate qualification; a current drawing is not proof of a scientifically adequate refinement.


## Actual edit versus later publication failure

`LivePreview::apply` retains its closed-Edit refusal boundary. An optional owner-local applied receipt is set only after that operation returns, before any later trace, completion/publication hook or request construction. A later exception preserves that receipt. The app uses it to retain the already owned recorded Undo and distinguish an applied/unconfirmed presentation from a genuine refusal; it never restores an old model merely because a UI observer failed. Reentrant edits and fitting are refused while publication is in progress. A held publication failure blocks subsequent mutation until an actual Undo/reopen recovery; the current dataset/worker guards remain authoritative.


## Retryable preview admission and synchronous owner retirement

The prior request path published in_flight before WorkSnapshot/job preparation. The same existing preview now prepares snapshot and callable first, leaves owed true until actual Worker queue admission returns a ticket, and only then publishes the real in-flight owner. Completion clears the finished ticket. A failed pre-admission snapshot/callable/queue attempt therefore cannot make Undo cancel phantom work. Coalesced owner-thread preparation failure retains owed and reports a preparation refusal through the normal observer; an actual next edit/Undo can retry. Worker token registration is removed on a pre-queue failure. Genuinely queued work and existing external Post semantics are not converted into unadmitted work or replayed.

LivePreview apply/recalculate hold the State locally across hooks and stop requests after closure. Session retirement marks the old PVM before replacement, disconnects its Session signals, and closes its preview. The old sealed-file lease lives with that retired PVM. A private nonallocating publication-depth scope prevents deletion while a synchronous publication/edit/Undo/fit owner stack is active: no DeferredDelete event is scheduled until its final scope returns. An idle replaced owner retains targeted eager cleanup; no global deferred-delete drain can delete another active retired stack. PVM publication stops after actual row/property observer calls if the owner retired. Native dispatch compares its original project/record/receipt before answering, and never clears a replacement call's own-edit marker. Real fit completion still settles its original callback; a retired owner does not present or answer a replacement.

This is the existing Qt/Session ownership seam, not a public lifetime API, new callback framework, altered animation policy or a permission grant. Direct arbitrary deletion of a QObject from outside its declared Session ownership is not introduced as a supported model operation. Platform/allocator/runtime proof is separate from this source design.


### Scan Undo commit ownership and synchronous attachment retirement

The shared scan-file reversal owns capacity for every staged, moved-aside and moved-in file before its first write; the staged receipt owns a partial write too. Existing scan-run JSON decoding is prepared before reversal. `ScanSession::putFiles` exposes the actual completed file-commit latch, and adopts that prepared provenance with a nonthrowing move. Its caller preowns the owning fit records and the resolved shown-data/parameter projection before entering that file operation. After actual file commit those prepared model obligations commit through nonthrowing moves/scalar writes before any observer. Only this completed restoration permits consuming the ScanRun Undo. A later index/calculation/Qt presentation failure retains the applied warning/fence and cannot replay the file reversal. A refused or incompletely reversed file operation retains the original Undo and the real OS/kept-aside diagnostic. Existing file count, paths and scientific values are unchanged.

The existing closed scan-view operation and ScanRun Undo share one internal preparation/commit implementation. General Edit resolves its names at execution as before; Undo resolves and owns the same operation before disk reversal. The recorded shown values cover every original named slot, including its already completed dependents; restoration publishes those saved values without a new scientific normalization assumption.

Assistant binding captures a guarded target and advances its generation before synchronous retirement notifications. Every continuation which can invoke a callback checks that exact binding; a candidate Controller stays locally owned through attachment. Session uses a private exact attachment result and a monotonic replacement token, stops immediately after a superseding attachment, and never overwrites the newer owner's example/warnings. Managed-result restoration and candidate cleanup use guarded owners; no old stack deletes a newly retired active owner or restores an obsolete attachment. This remains app-private lifetime/currentness handling, not an external API or a guarantee against arbitrary QObject deletion.


### Same-Session Clear during attachment

A conversation/file-selection retirement callback can request Clear while Session has already committed a new model and Assistant still borrows the retiring old one. The existing Session-only attachment stack coalesces that real Clear until the attachment stack unwinds; it then performs the actual archive/cancellation operation before returning to Session. Normal and delayed Clear rebind to Session's actual project, not a pre-target Assistant borrow. The matching installed Controller/project is the attachment proof after same-Session Clear; a genuine nested Session replacement still supersedes via Session's replacement token. A committed ordinary target therefore finishes its metadata/connections/publication. A managed candidate not yet committed is canceled by Clear and the real prior Session owner is reattached instead. The native prepared-creation path already commits its Controller/Session pointers adjacently and must retain that rule in its union.

Disconnected Clear persists its real archive discard before retirement-time binding callbacks; failure preserves the original leases/history. Successful Clear is not lost merely because a later binding is superseded. Authenticated immediate/deferred Clear keeps its existing real cancellation/ACK/terminal/deadline ownership and chooses the current host project when it finally rebinds. No queued user-input replay, new model, public synchronization API or provider/account flag is introduced.


### Failed deferred Clear and managed precommit cancellation

The private attachment drain returns NotRequested, Discarded or Failed from the actual archive commit latch, separately from Controller/project identity. A genuine Clear requested before managed adoption or export reopen cancels that candidate regardless of archive/preparation success. The assistant restores the trusted actual Session owner before executing the fallible Clear and before candidate cleanup. If restoration cannot complete, the candidate borrow is detached and the existing Session restoration/refusal path owns the failure; no candidate is authorized by a matching stale proof. Failed archive discard retains its original history/leases/diagnostic, while a genuine committed discard remains committed through later preparation failure. Ordinary already-committed replacement may finish its actual metadata/attachment with the warning retained. An actual disk export canceled before reopen reports exported-but-not-opened only for the still-current replacement. No original worker/RPC/ACK/terminal/deadline ownership or provider authority is changed.


### Fit origin owns automatic results presentation (2026-10-16)

The existing FitViewModel/Main results-modal path separates real completion from automatic presentation. At ended(), the original native completion callback is moved locally before any fallible or reentrant publication; its presence identifies an assistant-origin fit. This includes both startNative and the visible action's prearmed genuine Start fitting button. That immutable per-completion decision flows through single/joint and scan presentation without consulting current sidebar visibility, Show actions, a later callback slot or a newer fit.

Actual result adoption, charts, status, result rows, Undo and existing finished/scanFinished signals remain unchanged. After eligible manual results and their normal completion observers publish, a separate automaticResultsRequested signal asks Main to open its existing modal. Assistant-origin fits do not request it; their original real FitReport/native RPC/history still settle through the existing completion. Refused/nonadopted results do not gain a popup. Retired owners do not request presentation; exceptions retain existing completion and failure handling. The status-bar results button remains an explicit way to open actual recorded results for either origin. This is a presentation policy, not result suppression, fabricated fit success or an extra fit engine.


### Same-owner empty scientific completion

Prior art: native selected-CIF/XYE composition prepares an isolated project; ordinary loadStructure/loadExperiments use separate structural Edit calls. Completing a named empty owner needs one closed dual-collection operation, not Session replacement, Project assignment or two fallible live adds. EmptyProjectPopulation owns the already validated structure+measured experiment before commit; populate_empty_project checks scientific emptiness then moves both prepared ItemVecs nonthrowingly, retaining their target host and relinking nested rows. Its adjacent committed latch precedes all preview/Qt publication. Metadata/path/settings and project identity are never assigned. Undo checks exact inserted row identities and absent dependent scientific additions, prepares both empty collections, then clears only the pair without overwriting later metadata/settings.


The same-owner empty-population fit-residue comparison uses the authoritative nonempty FitResultCategory::columns (scalar/string/optional fields), not the unspecialized engine RowSchema for this app record. Its nonempty assertion and explicit correlations/scan-results checks remain shared by admission, final completion and Undo.


## Bounded scientific stamp capture

The existing work_stamps owner-thread capture and canonical source encoder are
the first implementation of scientific freshness. Its bounded overload accepts
a construction-byte allowance. A nonallocating count sink shares the exact
original geometry/calculation/relation traversal with the byte writer, including
measured axes/intensity/uncertainty buffers and equal-write identities. It admits
container/string payloads and the original relation name-resolution scratch
before retaining source encodings. Checked arithmetic rejects insufficient
capacity; no partial stamp is returned and no scientific field is omitted.
The original unbounded API and unchanged_since byte comparisons remain intact.

Counting and capture are synchronous on the same live owner thread, without
callbacks or event processing. This is a payload/container allowance, not an
allocator-RSS promise. Callers retain the actual model owner and recheck their
original lifetime/currentness after surrounding callbacks. Assistant input,
own-edit refresh, creation attachment and fresh inspection use the same bounded
entry; their local, old/new and late-callback roles remain jointly charged. A
new inspection receipt never changes stamps shared by an earlier operation.


### Closed applied identity before observation

The original LivePreview apply door retains its bool receipt and gains an additive typed Edit::AppliedResult destination. The same closed named Edit executes once and returns its actual appended/replacement Structure or ExperimentBase identity. LivePreview writes that preowned result and the applied flag before note_edit, Applied tracing, edited hooks, requests or publication. Other edits return an empty identity; no public callable constructor or arbitrary scientific executor is introduced. The original apply overload and Edit call operator delegate to the same operation semantics.

PVM's existing prearmed creation/file input owns the receipt, so an Applied observer, thrown publication, retirement or UI-owner deletion cannot erase the factual original identity. Post-callback use still requires original owner/input and actual membership; a pointer is not a lifetime or authorization grant. Published remains separate from applied, and the original Undo/partial facts survive. Capture never infers a later current row. Early original-control settlement records may_have_written from this real applied latch, not a guessed row or replay.


### Native executable process defaults

The original SDK executable bootstrap (crysta ADR-0063) is explicitly whole-linked
from `crysta::process_defaults` at the native app, CLI and engine-consuming
registered test/probe executable boundaries. The ordinary core, app/shared
libraries, Python modules and Qt-only tools do not acquire it transitively.
Emscripten keeps its existing serial/pool behavior and does not link the archive.
CMake 3.24 is required for the explicit WHOLE_ARCHIVE link.

No policy is copied into app main or a launcher. Caller-variable presence, even
empty wait variables, remains caller control; a saved positive Engine threads
preference still overrides Auto as before. The original SDK runtime detection and
bounded libgomp re-exec remain its implementation. Native deployments require
a qualified SDK release exporting this target and a coordinated source pin;
current older SDK binaries are not attested by this source change. No measured
GUI responsiveness improvement follows from this integration alone.


The first existing package import in core uses CMake's GLOBAL promotion so the
same imported targets are visible to sibling CLI and outer native probe
executables after add_subdirectory. This changes visibility, not link interfaces;
shared libraries and Python modules still do not inherit executable startup.
The consumer's existing common SDK shape check requires the bootstrap archive's
recorded SHA-256 and matching present bytes, alongside core, CLI and runtime.
Both fetch (including unpacked-prefix reuse) and explicit SDK checks enter that
same admission before reporting a qualified package. A download marker alone
does not qualify modified extracted bytes or an absent bootstrap digest.
