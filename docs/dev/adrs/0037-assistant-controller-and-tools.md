# Assistant controller and tools

Status: Implemented in part

The assistant shares edi's C++ core with the manual application (ADR-0009). Its public controller accepts trusted
user actions separately from normalized provider events. Only a user action approves the displayed plan. Complete
calls carry connection, turn, request, project and revision identities; the controller refuses a stale or unapproved
mutation before constructing an edit.

Parameter paths and metadata come from the existing parameter walk. Batch value assignments resolve and validate
all names before writing. The host applies the closed `edi::Edit` through its existing editor/preview door
(ADR-0020); a caller cannot supply a mutation callback. Equal writes outside that door are detected using the
same fit-input identities the existing FitJob checks, now shared in `fit_inputs.hpp`.

A candidate is a deep project copy. Its FitJob uses the existing worker and optimizer, then a checked typed edit
can adopt its parameter and fit-result state into the original identity-bearing rows. Rejected trials leave the
accepted project untouched. Scan artifact adoption and complete persistent recovery remain pending; assistant
scan execution explicitly refuses until that unit exists. The worker evaluates the current accepted copy independently before fitting the candidate, with matching free flags. Historical saved objectives do not serve as that baseline.

The Responses stream parser emits only complete public text, tool and terminal items. Account/project authority
is supplied by the native connection, not by provider text. Every JSON boundary rejects duplicate fields,
nonfinite numbers, invalid UTF-8, unsupported schemas and oversized messages. The shared report JSON reader is
reused; assistant-specific admission rules are applied at the assistant boundary.

The controller has no Qt, timers, network or credential storage. The host supplies an owner-thread event sink,
provider transport, typed edit door and optional monotonic clock. Worker deliveries remain ordered through the
existing `work::Post`. Independent tests link the real `edi::core` target; no production test command is added.

The repair checkpoint adds a complete executable free-set for each trial: every candidate parameter starts fixed,
and only independently refinable, profile-used paths in its approved group become free. ParameterEntry carries the
existing category's profile-use metadata; this extends the prior parameter walk rather than introducing a parallel
scientific registry. Candidate setup becomes immutable after its first fit. Accepted and fitted input identities
and work stamps must still match before evaluation. Fit result adoption prepares the complete owning result record
before the first scalar write, then moves it without throwing and retains existing identity-bearing rows.

FitJob's optional production cancellation predicate runs at the existing optimizer checkpoints, including the
owner-thread kit. The native kit measures its deadline with steady_clock without calling a GUI-bound clock on a
worker. IterationRecord now carries the engine's raw objective separately from reduced chi-square. Async completion
records a correlated scientific terminal and replaces the cached start acknowledgement; it distinguishes candidate
publication from live adoption. Questions use real controller-generated identities, offered options and a trusted
human answer command. A pending question holds continuation until its correlated answer or interruption settles.

Limits in assistant_limits.hpp declare finite byte/count policies. The parser charges wire events, incomplete
records, retained original items and complete call arguments. The controller coalesces adjacent text belonging to
one request and charges complete history/cache entries, context and outgoing requests. Pending work reserves future
terminal capacity. Original completed Responses output, including opaque reasoning and encrypted fields, is exposed
to the native adapter for exact replay; semantic duplicate comparison does not depend on JSON member order.

The public OpenAI capability policy is a shipped data resource in data/assistant, embedded through the same
configure-time resource pattern as palettes/report resources. Exact reviewed model IDs map to a closed effort
vocabulary; availability still comes solely from the user's account catalog. This is product policy, not a claim
about measured context windows or account entitlement. The compiled repair checkpoint is not a behavior/CI proof.
Independent quota exhaustion, delayed lifecycle events, real owner rendering and live sign-in remain verification
obligations; scan/recovery/conversion/provider/platform units remain incomplete.

A refused new message leaves the previous execution conversation unchanged. The controller prepares its user row,
context, complete outgoing request and reply before committing the new turn. A mutating tool likewise prepares its
complete history/cache nodes and original-scope result before calling the edit door or changing the candidate.
The original invocation scope remains the result's binding even when the action advances the project revision.
Candidate iteration limits are clamped only after admission and baseline-job preparation succeed.

Output exhaustion on an already bound request revokes its approval, interrupts the turn, cancels its worker and
keeps its isolated candidate for recovery. Stale input and a refused new user message have no such authority over
previous work. Connection replacement, disconnect and expiry retire the normalized execution history, tool and
answer receipts and conversation identity together. The retained GUI archive is a separate display record.
Repeated approval validates the existing allowance without resetting its original start time. Unknown model IDs
cannot enter the core capability list even with Provider default: current account availability and the shipped
exact capability map are both required. Completed public text/refusal items cannot accept later deltas.

The baseline raw objective is evaluated with the same built residual provider's `chi_square(provider.values())`
before optimization in both single and joint adapter paths. The provider already owns the current participating
phases, masked population, experimental uncertainties and joint bank weights. This uses crysta's public
`residual.hpp` evaluator, rather than reconstructing an objective from reduced chi-square or a historical result.
`fit_report.hpp::pre_fit_record` promises the starting Rwp and reduced chi-square; its returned record does not
promise a populated raw-objective member. Independent replay must still establish currency and comparability for
single/joint data, exclusions, weights and changed fixed settings. The broader publication, retention and native
failure repairs remain separate units; this scoped checkpoint does not establish their closure.

Publication helpers return an explicit outcome. A failed event or state preparation retires the scope and prevents
subsequent provider dispatch, normal-phase publication and successful acknowledgement. An already-started fit
keeps its prepared receipt and is cancelled for later settlement. A question's complete interrupted history/cache
alternative is prepared before exposing the question, so a failed question publication cannot leave an orphan
pending hold. Allocation and length failures pass through the typed resource funnel instead of becoming malformed
JSON or an ordinary invalid-argument tool result. New-command preparation still preserves prior work.

The Responses decoder binds public content to its required item, output index and content index. Each part keeps
its original kind and separate text/part completion state; later deltas cannot mutate finalized content. Text/refusal
done, content-part done, output-item done and terminal output must agree with the public text already emitted.
Multiple parts and messages remain independent; original complete output retains its opaque provider fields.
The protocol source is the official [Responses streaming-events reference](https://developers.openai.com/api/reference/resources/responses/streaming-events).
These scoped repairs do not complete the held terminal lease, native replay recovery or aggregate resource units.

Tool-result envelope construction stages its owning fields and moves the parsed result into the envelope.
It avoids a second recursive JSON copy through an initializer-list temporary during preparation. Resource
exceptions from any remaining read, copy or preflight stage propagate to the bound interruption funnel;
no ordinary acknowledgement or provider dispatch follows that failure. This is the same envelope and
original invocation binding, with no change to the admitted scientific result or resource policy.

Stop keeps its correlated question call until terminal preparation/commit succeeds. It revokes answer and
execution authority first, carries typed publication failure to acknowledging callers, and retains the call/hold
for retry if preparation still fails. A fresh message cannot replace that identity before settlement;
Stop remains available while its correlated terminal is pending. The common terminal path reserves history space and prepares its cache,
row and shown payload before consuming the hold or changing a pending receipt; it moves those prepared values
at commit. Completed outcomes remain immutable. Attach and connection replacement cannot acknowledge a new
scope after failed Stop settlement; void cancellation/deadline/manual-change callers expose interruption.

Provider part lookup proves a prior content_part.added identity; contiguous indices cannot declare themselves
through deltas or done markers. Completed item snapshots retain their separate fallback admission. A unique
output-position map covers messages, functions and opaque items, argument events validate the same required
position, and terminal output must account for every retained item without replacement or omission. Original
output is returned in position order. The documented reasoning_text variant retains its own reasoning owner
and opaque part lifecycle; no hidden reasoning is emitted as public assistant text. This also preserves final
original reasoning/encrypted fields for stateless continuation. Broader quota/retention and native replay
recovery remain separately held; these changes do not establish their closure.

A request retains its original project/revision separately from the current live revision. When an earlier
approved call in that same authenticated request changes the project, later calls still receive a complete
original-call-bound stale-revision outcome in history and the immutable receipt cache. They never execute
under a refreshed stamp. Foreign request/project/revision inputs retain their ordinary refusal. This extends
the existing closed edit door and semantic call identity rather than granting a provider new authority.
Failed native responses can supply a bounded generated explanation through the existing terminal message;
the core exposes that failure while retiring its execution scope.

Asynchronous admission prepares a complete original-bound pending result/activity and all core role
capacity before requesting the optional host TerminalRetention lease. A refusing or throwing reserve
starts no work and changes no candidate iteration setting. A committed start calls started once; its
false result revokes/cancels work while retaining the lease and actual candidate. Standalone headless
callers have no extra UI retaining role; real VM installation remains a separate required app unit.

Complete terminal settlement prepares its encoded envelope, history/cache replacements and ordinary
shown event before consuming any reservation. False host settlement leaves the pending core receipt
and hold unchanged, quarantines the lease and preserves the genuine candidate/report. The controller
borrows that report from its owned FitJob; local baseline/start failures have separately owned real
workflow refusal reports. Baseline unavailable/cancel, genuine candidate submission exceptions, fit
error/cancel, serialization, host retention and continuation all share that complete original-bound
settlement. A missing result never claims candidate publication, including pre-fit cancellation.

Stop revokes authority before fallible work and preserves running/pending reservations until actual
settlement. A failed delivery retains a real supplied human answer as immutable pending evidence;
retry or Stop settles that same answer rather than inventing a cancellation in its place. Completed
receipts cannot be overwritten. Explicit project/account/controller teardown releases old leases on
the owner thread after disabling their scope; queued old deliveries cannot publish into replacement
state. Quarantine is visible interruption, never a partial successful public result. These core
semantics do not establish real VM/archive persistence, all pre-growth quotas or live provider proof.

Provisional host reservations unwind on every pre-start preparation escape, including allocation and length
failures, before outer interruption/error reporting. Actual accepted running work keeps its committed lease.
Explicit project/account/conversation retirement is a distinct owner boundary from ordinary Stop: it fences
old requests, cancels old work and releases the retired owner's leases/holds/report even when its renderer
permanently refuses settlement. Ordinary Stop still preserves the actual pending report and capacity.
All continuation callers share one contained request-construction/dispatch boundary. Synchronous provider
callback or construction failure revokes the undelivered request and approval, retains already committed
answers/tool/scientific outcomes and visibly interrupts; initial send uses the same dispatch containment.
No fresh revision, auto-approval, synthetic outcome or new public getter is introduced.

Validated native disconnect/expiry/changed-connection observations retire execution before allocating any
replacement identity or catalog copy. Allocation failure leaves the old turn/approval/job/lease fenced and
a truthful nonexecuting disconnected state. Unchanged-ready/malformed input remains distinct. Explicit
detach does not require a new conversation identity to retire its owner; a later message prepares one
transactionally. A proposed new project attachment may prepare its identity before committing retirement,
so rejected new-owner preparation preserves the existing owner. No old request or outcome is retagged.
