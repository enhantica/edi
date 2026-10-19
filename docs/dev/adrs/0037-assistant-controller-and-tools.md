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


## Human-selected immutable input and bounded reads

The existing Controller owns one bounded selected-byte collection. Its trusted update door validates
identity/generation, names/counts/raw bytes and the full prospective context/reply/storage before
no-throw moves commit the batch; refusal preserves prior collection and scientific state. No active
turn/fit/question/approved plan/terminal ownership is cancelled to make room. Explicit project owner
replacement retires the collection; automatic connection retirement keeps local bytes but invalidates
outgoing disclosure through the existing account/conversation lifecycle. Hosts must retire pending
chooser authority independently, using the approved initiating capability contract.

A request exposes only bounded descriptors; read_selected_file returns exact strict UTF-8 ranges with
collection/generation and original tool correlation. GPX/binary input stays unsupported rather than
executed. No path argument, provider upload, scientific converter or project mutation is introduced.
Existing full tool/result/history reservations apply to escaped read outcomes. Native/browser chooser,
pre-growth transfer and actual consent are separate required host implementation/qualification work;
this core preparation alone does not establish a functional add-files UI.

### Selected product guidance

The trusted host protocol adds bounded read-only skill_catalog and idle select_skill, separate from provider tools. The selected immutable workflow is guidance only. Selection and all current scientific metadata are supplied by the same context serializer before consent/dispatch and through inspect_project. Unsupported import/create/save capabilities remain absent; the shipped FullProf/GSAS intake workflows describe those limits.


### Native official-runtime tools in the displayed application

The single official agent loop registers only implemented DynamicToolSpec functions and answers the original reverse JSON-RPC ID for item/tool/call. A genuine admitted Send owns the original objective, approved full context/selected identities, exact project/WorkStamps, thread/turn and existing finite budgets. Model arguments cannot replace that receipt or expand capability/path scope; no keyword intent classifier or synthetic Controller plan approval is used. Scientific parameter preparation is shared core-private code with the restricted Controller, whose actual allowed groups and real approval policy remain intact. Native code uses the real ProjectViewModel editor and recorded free-flag Undo. It never invokes Python or a second provider conversation.

The initial native tools are inspect_project, list_parameters, diagnostics, set_parameters, set_free and run_fit; create/import/save/report/constraints are not advertised. Their purpose is explicit bounded metadata, projected into presentation without changing canonical provider items. The genuine outgoing context/disclosure names native action scope. Actual fit progress refreshes admitted activity; completion uses a once-owned app-internal FitViewModel callback carrying the actual FitReport and presentation-complete flag; it runs independently of fallible publication/restoration and runningChanged/finished. DONE/MAX_ITER/NO_STEP/CANCELLED/ERROR/SUPERSEDED/UNAVAILABLE remain distinct; a live displayed fit is not an isolated accepted-best trial.

Exact original item/tool/arguments and thread/turn/current owner proofs precede execution; turn-scoped original call IDs prevent repeated edits across replacement steer receipts, complete bounded terminal/response/history roles are admitted before mutation, and the original transport ID transfers at most once. Stop/Clear/context/account retirement cancel the real native fit and revoke receipt authority. External edits/replacement cannot be overwritten by a late action; native-owned validated edits advance their own expected WorkStamps. Actual storage failure retains a bounded outcome and blocks further work rather than certifying durability. This implementation still needs independent offline native gates and normal coherent builds; no provider, platform or full-workflow qualification is inferred.

Stop/Clear/context cancellation retains the outstanding native fit result reservation through the actual FitReport before completing its original RPC. A resolved reverse RPC releases transport charge independently and fences later writes; its real worker still settles. Project/process teardown retires that originating response authority before model destruction. No animation/busy property is used as worker completion.


### Native current-project integration: request, retention and final worker ownership

Genuinely accepted input receipts have monotonic admission serials. Out-of-order acknowledgements cannot restore an older objective; call associations survive receipt replacement for their originating thread/turn. The original dynamic tool namespace/tool/arguments remain immutable across live and terminal originals. Canonical provider fields remain separate from app-owned purpose/outcome, which are retained through provider completion and snapshots. Resolution notifications must match the stored original thread before releasing its reverse-RPC authority.

Before a native write or worker submission, the adapter owns a prepared uncertainty row/response, admits complete maximum bounded terminal wrappers against the existing history reservation calculation, and charges receipt identifiers, captured WorkStamps strings/collections, canonical items, outcome/response/UI roles and the bounded post-write context role against retained capacity. A failure to prepare/admit these roles executes no edit. Actual result ownership precedes archive/response delivery. Later allocation/storage failure preserves that ownership, blocks new native/context-dependent execution, and exposes a bounded app-owned retention warning without pretending persistence or signing out a genuine account. Explicit successful Clear may discard this held outcome. This is a finite recoverable reservation, not an allocator-failure delivery guarantee.

Native fit admission checks the actual FitJob-owned ticket state rather than the presentation running flag. Callback allocation precedes submission; genuinely unadmitted preparation failure releases the handle, while a submitted job survives UI failure with real cancellation and its final report owner intact. The once-owned callback is detached before fallible presentation, runs with the FitJob-owned actual report even if presentation throws, and independently contains its own settlement exceptions. Account sign-out initiation and teardown cancel local work immediately. Completed Clear/context replacement never recreates discarded rows; Stop may settle an existing row as interrupted with the actual report. Transport/worker settlement is separate from visibility and does not certify an unretained artifact.

Only a complete non-error bounded outgoing context can advance consent and receipt fingerprints after a native write. Read-only actions do not generate a spurious context revision. An actual edit whose resulting context cannot fit remains an actual edit/outcome, while further context-dependent Send/native continuation is fenced. No error-only JSON is treated as approved project data. Static escape review is not normal compile, offline peer/native execution, platform proof or full task acceptance.


### Joint retained-state registration and retired-worker recovery

A provider dynamic-item replacement stages its canonical association and any active maximum terminal alongside the prospective generic-item bytes. One registration admits that complete joint output together with CodexAgent's existing transport assembly/current-record roles before the generic map/charge commit. A pending accepted-input receipt is registered immediately in the same owner, not deferred until the next event. Failed preparation restores and re-registers the still-owned state, including when map allocation fails after prospective registration.

An actual finished FitJob releases its exact captured handle even if logout/fatal retirement already removed the original RPC. That release cannot answer a replacement call or claim a scientific terminal for an absent response owner. Successful explicit Clear uses one persisted-discard completion latch across connected, disconnected and signing-out states. Failed archive Clear retains its native recovery fence/records. Same-project disconnected Clear preserves the genuine cancelling worker handle until the actual report, then releases the discarded native charge/fence; sign-in never silently discards it. This is a scoped source correction, not runtime fault/deadline/platform qualification.


The already persisted native-discard latch also completes at a genuine project-owner replacement/close entrance after the old native worker/response authority is permanently retired. It does not wait for a callback from a destroyed old ProjectViewModel. A same-project still-running cancellation continues to hold; failed archive Clear never arms this release. This retires the obsolete owner without fabricating a completed fit report or settling a replacement call.


### Native value/free Undo and relation publication boundary

Native set_parameters and set_free call the same preowned recorded-edit entrance as the manual relation and free-batch editor. Normal app Undo exists before any live batch write. The native result reports edited only after actual application and presentation; an actual write followed by failed presentation reports applied_unconfirmed, retains its Undo and the app's recovery fence, and is not called a no-write refusal. Calculation remains asynchronous. The closed restore's joint collection preparation and exact changed-state narrowing are specified in ADR0024; the real applied receipt is specified in ADR0020. No restricted Controller approval or scientific model policy is bypassed, and no completed constrained trial/checkpoint/restore workflow is inferred from this primitive.


The recorded-edit successor also closes the preview-admission and owner-retirement siblings: actual preparation failure keeps an honest owed calculation without a phantom ticket, and synchronous Session replacement cannot destroy or continue the old publication stack into a replacement. Native reply/currentness remains bound to the original project, record and receipt after editing. Shared report/scan/save/Undo critical guards cannot bypass that fence; no additional provider authority or capability is registered by these repairs.


### Original-owner edit suppression

The native and restricted edit hooks suppress manual-change retirement only for their exact original generation/project and scoped edit token. Every success, exception and early retired-call return releases that token. Owner/call retirement invalidates it; a stale return cannot clear a newer reentrant token. A later genuine manual edit therefore still retires result/file/context/controller authority, even after the original native project/call was replaced or closed. Native outcome/RPC publication remains independently guarded by the original project, record and receipt. Binding/Session notification fences and scan Undo commit ownership are specified in ADR0020; they add no registered capability, Python dependency or authority over a replacement project.


### Native selected-file creation in an empty Session

The prior native request receipt, original-call ledger, joint retained-role reservation, real Worker and existing Session owner boundary also govern `create_cwl_project`. Its only filesystem inputs are two genuine selected IDs: Edi reopens its own regular snapshots, bounds sizes before allocation and verifies SHA-256 against the actual admitted bytes, not provider-supplied hashes/paths. The entire selected collection remains under its existing file/count/aggregate policy; the temporary verified copy and old/new Controller collections each own a bounded collection during preparation. These file-byte roles do not borrow provider JSON retention capacity. A host-owned temporary measurement snapshot is outside the runtime's writable workspace; core's existing classic/dot CIF and plain-data readers own scientific interpretation. The recipe explicitly supplies supported powder/CW/neutron/Bragg metadata, wavelength, zero, profile, scale, background, exclusions and initial parameters; no host-specific instrument or chemistry is inferred.

Preparation runs on the existing idle Worker and retains an exact cancellation ticket/final delivery. Stop, Clear, sign-out, context/owner replacement and original server-request resolution cancel that work and preserve the originating response ownership until actual completion or permanent owner retirement. No busy flag is a completion report. Reader refusal text is bounded before copying and final delivery is prepared before submission. The original empty Session and request must still match after core preparation and actual ProjectViewModel construction. The same move-stable semantic definition guard used for saved-result adoption protects native model construction.

A fresh Controller, actual selected IDs/bytes, complete bounded new context, strict final-model stamps, outcome/response/history roles and project signal connections are prepared before publication. One private, nonallocating attachment swap occurs immediately before Session's project pointer assignment, preserving the actual managed account/catalog/thread/original RPC/history and advancing only the creating request's context/stamps once. Normal `bind` is not used for that self-owned replacement. Session latches actual pointer publication before observers; a later throwing observer or reentrant replacement cannot delete a now-owned model or falsely report that creation never occurred. The prepared adopted outcome remains recoverable independently of fallible presentation or archive retention. An invalid recipe/currentness/resource failure leaves the original empty owner intact. No current project overwrite, save, convergence, calculation completion, native format conversion beyond the offered readers or working-folder authority is implied.


Creation admission owns a real Worker ticket, not just an allocated shared candidate. Receiver, final owning Delivery, Job and all captured submit arguments are prepared before installing native_creation. The full installation/charge/currentness/submit interval has unsubmitted rollback, releasing its temporary charge/hold while the original native call can retain/refuse once. Every cancellation/Clear/revoke/failure hold tests actual ticket admission; an allocation before submission cannot strand a false worker or require project replacement. Genuinely submitted cancellation still retains its exact real final-delivery/response owner.


### Native creation with shared recovery attachment

The prepared creation Controller and project signal hooks use the same original binding generation, guarded project and OwnEdit token as ordinary binding, with the genuine inactive preparation latch suppressing callbacks until commit. Native creation installs the actual Controller/project attachment proof at its nonallocating own-receipt/Session pointer commit. It preserves the original tool RPC/account/catalog/conversation/selected-byte ownership rather than using ordinary replacement bind. Session's committed latch is set before observers; later replacement/deletion cannot be mistaken for an unadmitted candidate or cause deletion through a stale unique_ptr. Actual adoption and presentation completion remain distinct. Shared Session/Clear/scan/Undo/Worker recovery semantics are retained; the pending failed-managed-Clear sibling from review165 must be corrected in the shared and creation derivative before application/qualification.


### Original creation completion after nested Session publication

An actual creation completion retains its own creation, installed attachment and original call record/receipt identity across host-model preparation and Session publication. Cleanup releases only those matching owners. Success, false-adoption and exceptional settlement can answer only that original call; A's already committed adopted outcome remains owned even when observers replace the Session and genuinely admit B. An older completion cannot clear B's worker/attachment, answer its RPC, renew its deadline or fence it. The existing response helper likewise stops after its captured record/receipt/RPC is retired or replaced across synchronous notification/transport-failure boundaries, including a throwing final notification after the original response has already settled.

Trailing discard/revoke/notification work is scoped to the binding, admitted-input serial and thread at entry, with no replacement call/creation/attachment permitted. A same-owner cancelled creation can still release its actual worker hold and advance its real pending Clear; a newer owner/input's settlement is never performed by the obsolete return. No new model loop, public lifecycle API, provider authority or runtime qualification is implied.


### Native response caller continuation ownership

The existing native final-response helper and all dispatch/fit caller continuations retain their original record, receipt and transport ID through synchronous notifications. A retired helper return cannot authorize a caller's old uncertainty fence. Fit completion clears only its exact finished handle; original and retired-response branches scope discard/revoke/advance/notification and catch fences to the binding, input serial, account epoch, thread and original call ledger at that real completion entrance. A legitimate successful discard may empty that old ledger; admitting a different call/record invalidates the old continuation. Same-owner Clear still releases the actual completed worker hold, while replacement input/owner/account controls are untouched. Preparation failure does not clear a new handle, and post-submit cancellation retains the original worker independently of fallible presentation. These private existing seams add no tool, engine, provider loop or public lifecycle API; static inspection is not runtime fault execution.


### Native affine append over the creation and recovery unit

The globally declared native catalog now adds add_relations as its eighth app tool, alongside the existing seven including create_cwl_project. Execution requires the actual current displayed structured model and original admitted objective/call/namespace/arguments; an empty or unsupported model refuses. The finite aliases/constraints batch has a real concise purpose, strict shape/types/count/text/complete-declaration bounds, exact parameter-path resolution and duplicate-ID refusal. Existing aliases and constraints remain. The private core helper validates the complete copied declaration with existing SDK grammar, dependence, cycles, symmetry/ranges/physical completion before live application. No independent solver, scientific-policy heuristic, property executor, chemical assumption, fake Controller approval or Python is introduced.

The actual preowned recorded-edit door uses structural publication for this declaration, retains ordinary app Undo before writes and distinguishes refusal from applied-unconfirmed publication. All current shared critical/lifetime/recovery, original RPC/receipt/currentness/outcome-reservation and reentrant completion guards remain. Created-project attachment/account/catalog/history and actual usage are not replaced. Native-only tool names remain in the app's DynamicToolSpec/native_actions and conditional skill guidance, never inserted as fictitious handlers in the restricted shared-index capability list. Both changed skill content digests/versions are updated together; their discovery stays automatic. This registration does not supply checkpoint/isolated shared-ADP candidate comparison, native save/report/working-folder or a claimed scientific result; those remain separate real operations.


### Recorded native input through genuine widgets

ADR0041's optional visible mode extends the prior ParameterItem/ProjectEditor and FitViewModel entrances rather than bypassing them. Ordinary manual setters retain their existing apply semantics. A private exact parameter/expected-value-or-free receipt temporarily selects the preowned recorded-edit path only for the genuine final widget event; unrelated setters refuse during that final event, and the original native record/receipt/currentness still owns the outcome and response. The complete finite helper/editor/string roles are charged before animation/input. No operation, path, account grant or tool is added to the native catalog.

FitViewModel separates fallible native-completion preparation from its existing start implementation, enabling the real QML Start button to admit the existing job after the original callback is owned. A token can discard only an unsubmitted matching preparation. Actual submitted work keeps cancellation/final-report ownership even when button presentation throws; the public QML entrance contains exceptions and stops admitted work rather than letting exceptions cross Qt. Default native start uses the same preparation and actual worker path. Original response and completion scopes guard UI restoration and all subsequent settlement after synchronous owner replacement. Static source inspection is not a GUI, worker-fault or runtime qualification.


Visible-input refusal contains diagnostic preparation itself. When it cannot prepare the actual row, the original preadmitted native outcome/response and exact request remain authoritative, further work is fenced, and any real fit still settles only from its final FitReport. Real manual takeover cancels this original call while leaving the user's actual controls exposed; it is neither a new objective nor a provider grant. These changes retain the same eight native tools and all ordinary-mode recorded edits, Undo, currentness and worker ownership.


### Retained native outcome is independent of completion (2026-10-16)

An app-owned uncertain/refused/interrupted result is distinct from provider item completion and from an actual edit, adoption or Worker report. Ordinary non-worker Stop/manual takeover/mode/window retirement settles its original prepared result through the existing bounded native_finish row/response path. The existing record marks a chosen host outcome independently of completed, so later immutable-associated provider item/completed or terminal snapshots keep that actual nativeOutcome even after contained preparation/publication failure. This flag grants no execution, provider terminal or durable archive success. Original response transfer remains once-only and storage failure retains the existing fence/prepared outcome.

Actual submitted FitReport/creation finalDelivery remains awaited; discard/context/Clear/permanent-close/no-response paths retain their existing authority and no-republication rules. Only still-owned visible history can be published; a cleared/replaced conversation is never revived by the outcome marker. Newer owner/call replacement after synchronous fallback publication stops the old response continuation. No target visibility delay/guard relaxation or claim that a refused/interrupted scientific input ran is introduced. This corrects the actual first153 response-versus-retained-row class, separately from later visible-create/batch candidates and the still-unobserved original lookup/takeover event origin.


### Opt-in native widget lookup diagnosis (2026-10-16)

The ordinary Qt category `edi.assistant.widget.lookup` is debug-disabled by default. Explicit `QT_LOGGING_RULES=edi.assistant.widget.lookup.debug=true` observes the original captured ParameterItem address/path, actual candidate typed QVariant conversion and QObject/ParameterItem result, plus the existing usableTarget result and immediately adjacent window/ancestor/clip operands. Exposure getters are observations after the original predicate, not a repeated predicate or a claim of instrumented helper-local values. Actual usable candidate property reads/conversions are retained once at their original point; enabled-only extra property inspection for unusable candidates is labelled originalPropertyRead=false. No account identifiers, request text, typed values or file contents are logged.

Only original tool/tab candidate names are diagnosed, so hidden instrument/cell controls do not consume the Analysis field trace. Each candidate conversion is emitted before its detailed exposure/ancestor trace, including failed conversion/cast/identity. The original once-scheduled lookup has a cap of 256 records with one explicit omission record. The cap is a diagnostic limit, not an acceptance bound; omissions remain visible. No new lookup entry/retry or NativeWidget size/resource admission change is added. Diagnostic-only getters/formatting run only while enabled and failures are contained; the functional lookup order, short-circuit exposure calls, identity comparison, input/timers/currentness and refusal/worker/once semantics remain. This is source diagnosis, not a visibility/replay fix or acceptance API. The independently retained host-outcome contract above is unchanged.


## Current native saving

The offered catalog adds `save_project({purpose,name})` in normal mode. The name
is a fresh ASCII single directory basename under the current genuine native
working-folder picker grant, never a provider/chat path or arbitrary write grant.
An explicit creation/refinement objective with that chosen folder delegates saving
before the final result, unless the user said not to save; no second scientific
plan or permission prompt is introduced. The app-only native operation is not
added to the restricted core-index prerequisite list. Bundled skill 1.5.5 and its
actual digest describe only the registered route. Visible mode refuses honestly.

The original RPC/turn/call record owns one save task, immutable admitted source,
actual Worker ticket and prepared final delivery. Source currentness is recorded
before copying; no copied model is falsely queried as current. Cancellation,
Clear, sign-out and owner/context changes revoke publication immediately while
retaining actual worker settlement. Every shared cancellation/clear/retirement
hold now accounts for both creation and save workers; an old final delivery only
releases its exact task/record and never answers a replacement call. Submitted
trace reentry cancels the original returned ticket, not a newer task.

The existing Edi-to-crysta save conversion is shared by ordinary directory saving
and the new admitted prepared-document finish. The latter passes exact settled
current columns and uses the same native scalar/loop writer; no recalculation,
second serializer, source-directory seeding or physics is introduced. Original
source/container/canonical-currentness/name-join roles are admitted before copy
and conversion; output uses the SDK's checked sink. Single/joint measured projects
without external report/scan assets are supported. Unsupported or absent current
calculation refuses before destination publication; raw selected inputs remain
unchanged and retained, while native observations/data-source metadata are saved
self-contained. No external raw assets are silently promised as copied.

The exact existing no-follow exporter receives the genuine pinned folder handle,
not a provider root string. Complete native documents are captured/hash-closed
and independently loaded in protected storage before export preparation. All
actual refusal/committed/reopened/active response and row roles are prepared and
charged before worker admission. The original record's factual state swaps at
each actual disk/reopen/active commit, so allocation or presentation failure cannot
turn an actual commit into a false no-write/refusal or a fabricated success.
Actual committed bytes are reverified/reopened through retained descriptors; only
then may prepared saved values land in the same live PVM/Session.

Success is `status:succeeded`, `committed:true`, `reopened:true`, `active:true`
with actual destination. `committed_unconfirmed` keeps independently true facts
if verification/adoption/presentation fails, never blindly retrying an existing
destination. A later user edit remains an edit; no post-save rollback overwrites
it. Original shared native outcome/history/once/canonical/currentness fences apply.

This code requires the paired crysta prepared-persistence API/packages, not the
old installed SDK. Source-only Edi publication or a locally replaced archive is
not a consumable save fix. Actual SDK package identities and Edi pin must follow
the existing paired PR/package process (ADR-0017); no digest is guessed here.


### Saved-value parameter walk uses the public common views

Saved-state preparation joins both `named_parameters(const Project&)` and
`named_dependents(const Project&)` against `named_slots(Project&)`. These public
views partition and expose the existing native writer's complete parameter walk;
the adapter does not call its namespace-private `parameter_slots` helper or
duplicate parameter-name grammar. Independent and dependent values retain the
same exact identity, uncertainty and free-state checks before publication.


### Closed save admission dispatch and exact document count

The primary RowSchema declares an empty fields tuple for every type. Admission
therefore traverses actual containers before considering a row schema, and only
a nonempty declared schema may admit an aggregate. Unknown future types fail to
compile instead of silently charging sizeof-only. Existing string/scalar/wrapper
and column handling remains; arrays, nested vectors/maps/strings and RowVec /
KeyedVec rows all contribute their complete borrowed payload before copying.

The unsupported scan route refuses its whole nondefault configuration, including
undeclared file_pattern/reverse/template/extract residue, before a complete model
copy. Actual parameter-slot counts and block/row IDs bound multiplied fit-state
and relation name joins; fixed spelling allowance alone never bounds a dynamic ID.

Inclusive document admission counts the real emitted project and analysis files,
each actual structure/bank, and report settings only when any optional setting is
present. False and empty optional settings are still present. Checked additions
precede reserve/copy; exact limits pass without raising host caps. The final sink
count/byte checks and same formatter/SF1 stream semantics remain authoritative.

The Edi snapshot also retains shared GeometrySource/ComputedSource records. Both
construction and retained-role admission count their actual input/relation text
before copying, including stale records from a formerly larger model; today's
row count alone never bounds that older retained payload.


### Rounded save calculation and unsuppressed presentation

The strict Edi loader restores measured/model values, never trusted computed
arrays. The existing original Worker calculates the real native reopen after
SU/value rounding and normal relation completion. Its staged immutable result
and completed dependent values are prepared before destination publication,
then resolved against the same live parameter identities. Existing pre-round
arrays are never relabelled current. Original WorkStamps/cancellation/folder
checks still gate disk publication and the no-callback saved-state landing.

The worker's result/delivery has its own reserved native retained role before
submission; complete source containers, recorded currentness strings and the
actual bank-by-structure canonical join are admitted. Currentness roles use
the same finite construction-copy policy, with checked multiplication. The
ordinary native calculation itself remains the existing engine operation; this
is not a new allocator guarantee or alternate calculation engine.

Native saving validates names at the exact existing exporter/Save As leaf
boundary. Spaces/Unicode are accepted within its 512 UTF-8-byte limit; path,
NUL, dot/trailing-name and fresh-destination safeguards remain unchanged. The
old initial ASCII restriction is superseded. The schema and effective skill
state that same domain without turning a chat path into a grant.

Persistence presentation does not emit a synthetic user projectEdited event.
The known successful landing refreshes only its original native call through
the existing explicit completion path. It holds no broad own-edit scope across
Session/PVM observers, so genuine nested edits/Undo/settings changes retain
their ordinary epoch/context/controller retirement. This also removes the
raw-State scope destructor previously reachable after receiver deletion.
Saved disk/active facts latch before observers and survive interrupted or
retired presentation; no manual edit is rolled back or absorbed into an old
approved request.


### Saved-calculation reservation preserves transport admission

The late saved calculation reserves the original snapshot's fully admitted
retained-model allowance before Worker submission. It does not claim all
remaining shared transport capacity: pending original RPC/frame owners retain
their ordinary admission. The worker checks actual staged data/reflection/
geometry buffers, completed-name/value rows and copied original stamps against
that preowned allowance before transfer. The temporary calculated Project is
not a second retained delivery model. A larger result refuses before disk
publication; no cap is raised and no successful archive/write is invented.


### Undeclared fitting mode in native persistence

Persistence admission uses the existing effective fitting-mode contract: an
empty declaration means single fitting, alongside explicit single and joint.
The check borrows the declaration before resource admission and does not copy
or rewrite it. The ordinary native analysis writer continues to serialize the
effective single mode. Unknown explicit modes, scan configuration and external
asset restrictions remain refusals; resource, currentness and saved-value
rounding checks are unchanged.


### Fixed native-save preparation diagnostics

A refused save exposes an app-owned diagnostic suffix in its existing original
tool outcome: [save_project:STAGE/CLASS]. STAGE is a fixed literal at dispatch,
argument validation, working-owner/name checks, task/snapshot/delivery/record
preparation, outcome/retained reservation, currentness or worker submission.
CLASS is ALLOCATION, CAPACITY, VALIDATION, STATE or EXCEPTION from the actual
standard exception type. No what(), paths, project/user/provider text, URL or
credential is copied into that suffix. Each original dispatch owns its stage on
its stack; synchronous nested calls cannot overwrite another invocation.

Existing original RPC/call/thread/currentness checks, refusal versus uncertain
may-have-written status, genuine admitted Worker cancellation/report ownership
and postcommit facts are unchanged. This identifies a reached preparation
refusal; it does not label an unknown stage as a filesystem failure, turn a
refusal into success, relax admission, or add telemetry/testing hooks.


### Typed retained saving roles and reusable worker payload

The fitted-save reservation above is superseded by typed retained ownership
and an explicit worker lifetime boundary. Construction/formatting still uses
its existing conservative scalar/copy admission. Retained numeric vectors have
one numeric slot per element; strings have their shell and text, without a
fictional string per numeric row. Inline members are not charged again as
independent slots. ItemVec row/table images and Written loop read tables remain
real owners. Immutable ComputedColumn/Column buffers are charged once by actual
buffer identity, including their pinned payload; sharing does not make them
free. Unknown future retained types fail compilation instead of bypassing the
walk. The late DataCategory already includes residual and is visited once.

After the existing formatter returns owning documents, the save worker destroys
its private snapshot.model before reopening/calculating the rounded image.
Nothing later reads that model; original WorkStamps remain separately owned for
currentness and final adoption. The task preowns one reusable payload slot,
charged as max(snapshot retained payload, calculation allowance), unchanged by
worker-thread phase transitions. It does not retain both model and new result
at once or dynamically lower its charge while observers run.

The finite calculation allowance is the released model payload slot, plus the
CalculationResult/stamp/completed-row shells/text and prospective computed-only
measured-row output: four doubles and one incl/excl string per measured point,
with owning vector/control shells. The released slot remains available for
variable reflection/geometry payload. This is a bounded transfer allowance,
not a claim that existing reflection counts bound a rounded/new calculation.
The actual complete staged result is admitted against it before task transfer;
larger output refuses before any disk commit. An unfitted source needs no
existing computed columns to reserve those measured-row roles. Resource caps
are unchanged. Original post-context, artifact, factual outcome, generic and
live transport owners keep their own admission and may still refuse genuine
capacity exhaustion. No successful save is inferred from accounting alone.


### Normal native actions follow the existing editor page

Normal-mode current-project value/free/relations/fit actions request the owning
existing QML workflow page before their ordinary native edit/worker path. Cell
and wavelength singleton values follow Structure/Experiment; other parameter
values, free flags and fitting follow Analysis Main, relations follow Analysis
Extra. Inspection and saving preserve the current page. This is explicit normal
mode presentation, not visible-mode pointer input or a second scientific door.

An actual manual numeric draft blocks navigation before blur. The host maps only
fixed page ids, and QML uses actual enabled AppState pages and retained loaders.
After real page/focus notification the original receiver/project/call/receipt
and native currentness must still match before any scientific action. A newer
owner is never resumed by the old continuation. This does not yet implement
visible sidebar/filter/scroll exposure, background insertion or visible save.


### Genuine visible Main sidebar navigation

After the actual app-bar pointer click, the visible native adapter clicks the
current enabled workflow's existing sideBar.tab.basic through the same real
input sequencer before locating the scientific field or fitting.start. The
request/current target gates apply to both events and every later timer; numeric
draft preflight remains before navigation. Both navigation callback preparation
and delivery are contained so a failed scheduling operation settles/refuses its
original call rather than leaving it active.

This closes Main versus Extra/Text/Settings exposure for the current editor and
fit button. It does not yet clear parameter filters or reveal undelegated rows;
those need the existing actual filter/list controls, not a longer arbitrary
delay, hidden model write or weakened clipping/parameter identity predicate.


### Original mouse ownership survives Qt delayed press replay (2026-10-16)

Qt6.11.2 Flickable clones a captured mouse press and later sends it through the same window; actual reached replay occurs after the original synchronous injection flag ends. Real widget input therefore uses an exact public QPointingDevice plus monotonic event timestamp identity bound to its original request. Three fixed slots retain the current move/press/release stamps; public monotonic-clock milliseconds preserve Qt elapsed-time meaning, with strict uniqueness on equal ticks rather than treating request ordinals as time. One small application-owned ordinary Qt event filter/device survives helper and window replacement. It examines only exact own-device QQuickWindow mouse events, checks original window/helper/request/serial and actual authority, and consumes retired or other-window events before widget dispatch. Child-item forwarding and every unrelated device/event retain normal Qt delivery. A clone from a canceled request cannot become a later request's scientific click. No time grace period, spontaneous/synthetic blanket, shorter press, global pressDelay change or direct model write is introduced. Existing pointer/click/typing timing and native prepareCommit/recorded edit/Undo/FitReport remain.

Ordinary user/QTest mouse devices and key/wheel/touch still cancel immediately with their original event/target preserved. Retirement is published before the existing outside balancing release; that exact synchronous cleanup release is allowed, but any nested delayed press remains rejected. On held-helper teardown the same retained owner queues only an outside release on the exact old device/stamp, rejects nested old presses and blocks new assistant admission until this real cleanup returns. If its original window has gone, public QPointerEvent device-point ungrab clears the old exclusive/passive grabs without sending to a newer window. Failed queue or cleanup retains the admission fence. No callback into the destructing helper is retained. Application ownership keeps the device and stale-event filter alive across a Flickable reparent/old-window teardown until normal application shutdown; no unbounded event map or retired-device list grows. The timestamp counter refuses exhaustion. Default-off input and existing diagnostics/outcome retention remain separate. This closes actual reached own replay misclassification, not the still-unobserved value lookup failure.


### Visible input tests the actual clip rectangle

The public QQuickItem clipRect, not painted glyph boundingRect, determines
whether an ancestor clips a real input point. QQuickTextInput may paint a
right-aligned number in a small glyph rectangle while accepting input across
its full control. The helper still requires finite window coordinates, positive
size, actual visible/enabled ancestors and current native ownership; only the
matching public clipping geometry is used. This follows the reached204 operands
and pinned Qt6.11.2 public TextInput clipRect contract, not a visibility bypass.


### Genuine Analysis parameter filter input

Visible Analysis parameter/free actions use the ordinary reset-filters button,
the smallest actually offered category through the existing category selector,
and actual row scrolling. Unit-cell rows remain unfiltered. The shared category
predicate owns both offered groups and native selection; no full parameter path
is typed as a filter for each row. Exact original ParameterItem/native-member
identity still owns every row action. Cancellation leaves the real presentation
in place rather than restoring stale filters over a manual input. Scientific
numeric draft ownership remains exclusive to the existing Value kind.

Original request/receipt/project/parameter/real window and every helper event
retain currentness checks; filter text is read back before final target lookup.
The final actual parameter pointer and exposed Value/Free control are still
required. Matching uses the existing common filter semantics; an unavailable
remaining target refuses honestly without direct/native fallback or another
parameter's edit. Filter paths and the enlarged run are precharged before UI.
No scientific may-have-written latch is set for navigation/filter input. Real
recorded edit/Undo starts only at the final original parameter control event.
Fit keeps its genuine fixed-open Start control and real final report.

This is a narrow exposure increment, not generic computer use or full visible
create/background/relation/batch/save support. Source197 own-event/clipRect
prerequisite remains separately reviewed/applied before runtime qualification.


### Relations through the existing human row controls

The first implementation is AliasesGroup/ConstraintsGroup, their original
AliasListModel/ConstraintListModel setters and ProjectEditor.apply_relation_edit
(ADR-0024). The duplicate RelationAppendGroup, its registration/insertion and
appendRelationForm entrance are removed. There is no extra Apply or hidden
staging model. The normal native add_relations tool keeps its complete validated
batch and one Undo; Show actions is a sequence of the same real human edits.

The visible route conditionally selects Analysis/Extra, expands the original
category header and reveals its exact current row through real wheel input.
Alias append, ID commit, parameter choice, constraint append, ID/expression
commit and activation each use their original model/editor. Existing parameter
popups use real searchable keyboard input or their finite ordinary choices.
An exact original action/member/value receipt is installed immediately before
the final genuine event. No direct model edit decorates a pointer action, no
synthetic clicked/accepted signal is emitted, and no widget index/scroll/group
state is assigned by the assistant. TextCell shares the original numeric editor's
paced draft/commit/cancel ownership; ordinary manual blur/Return still uses the
same model setter. Existing manual drafts and IME are preserved.

A newly appended manual constraint starts disabled, and its ID/expression cells
remain editable while disabled. This applies equally to humans and assistant
input: a complete declaration is entered before the existing toggle activates
it through the actual validator. Existing loaded enabled flags are unchanged.

Each real change retains its own normal recorded Undo. Current member identity,
actual model values and the original request/account/owner/window are checked
between steps; receipt refresh follows each own applied edit. Stop, takeover,
refusal or replacement preserves completed changes and answers the original
call once. Outcomes distinguish complete edited from partial/refused, expose
atomic:false and actual steps_completed, and retain uncertainty rather than
claiming unchanged science after a failed publication. These steps are not an
isolated trial, automatic rollback or a single-Undo transaction. Single-line
editor spellings and existing resource/deadline/viewport limits may refuse
before or during the sequence; never silently use normal mode instead.

The compiled instructions/tool description and bundled skill distinguish normal
batch semantics from visible human steps. No new tool name, capability or core
bootstrap requirement is added. Explicit keep-fixed/no-sharing/composition
instructions remain authoritative; existing free flags and missing declarations
are initial state, not implied prohibitions. The rejected parallel creation window remains a separate pending replacement,
not a completed human-route capability. Background follows its original row
controls as described in ADR-0043.

### Complete the same named empty project

Prior art: create_cwl_project originally required a null Session owner, prepared a new PVM/Controller and adopted it via Session replacement. That branch remains. A distinct normal-mode branch now captures the actual current empty PVM, original receipt/WorkStamps, selected immutable bytes and Session epoch. Native recipe/readers/Worker remain the same. It refuses scientific membership/relations/results/scan/report assets, changed owner and unfinished manual draft at admission and final apply. Existing project metadata/name/path/settings, source files, Controller/account/conversation/grants and prior Undo remain; recipe project metadata never replaces them.

The complete prepared scientific pair enters the same PVM applyEdit/preview/publication path with one dedicated preowned Undo, rather than membership-preserving applyRecordedEdit. Exact own-edit token suppression ends immediately on return/throw; ordinary unrelated edits and retirement retain their original semantics. The closed core commit latch owns actual applied outcome before observers, and original-only response cleanup cannot answer a newer call. Native finish advances only the same actual receipt through its complete-context/currentness/resource admission. Cancellation before commit leaves the owner empty; cancellation after an actual commit cannot manufacture a no-write result or roll back manual edits.

The result can report completed_existing, adopted, presentation_complete, calculation_pending and saved=false. This unit does not save files: a named owned directory remains at its original path and modified=true. Creation alone does not save files. Saving that named owner uses the distinct explicit current-directory Save contract described below; fresh-child Save As must not silently nest a project or claim the original directory saved. Visible creation/completion and saving use their respective genuine forms. No new tool/capability identifier or bootstrap allowlist entry is added; actual recipe/profile/input declarations and skill1.5.11/index digest remain synchronized.


### Temporary backend conversations

Prior art: generic_start_thread creates the official runtime context with actual
workspace roots, account/catalog/tools and effective-policy verification. Ordinary
turns already reuse its admitted live thread, while genuine Clear/context or
owner retirement settles original work before preparing another backend context.
Edi's bounded local assistant archive is a separate user-visible display record.

Every new thread/start now requests ephemeral: true, supported by the pinned
[ThreadStartParams](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/app-server-protocol/src/protocol/v2/thread.rs).
Readiness additionally requires the effective response thread.ephemeral to be a
boolean true. Missing, false, null, numeric or string values refuse through the
existing app-owned [thread/start: THREAD_EPHEMERAL] diagnostic, before publishing
ready/thread authority. All actual provider/account/root/policy/catalog checks
remain; no fallback accepts a durable backend thread or expands permissions.

The pinned runtime skips durable rollout/state-database thread persistence for
ephemeral conversations. This addresses newly created backend-history clutter,
not existing stored sessions, all runtime logs, telemetry or upstream retention.
No persistent name/archive/delete operation, personal history scan, global
configuration change or provider request is added by this lifecycle policy.
Clear still commits Edi's empty archive and settles original worker/input/control
owners before replacing model memory. Failed Clear preserves existing history
and recovery obligations; ordinary subsequent turns use their same live thread.

Backend restart does not resume ephemeral model memory. Edi's visible archive
can survive independently and must not be represented as restored model history.
Routine manual scientific edits currently retire the execution context and full
context-byte changes can still require disclosure confirmation. Stable project
conversation reuse and scope-based consent are separate required improvements;
this flag neither delivers them nor proves the owner's desktop grouping/title
behavior. Existing persistent clutter is not scanned or cleaned by this unit.


### Native creation through the ordinary import form

Prior art is the normal native create_cwl_project immutable-file/typed-recipe
Worker, the same-owner prepared population/Undo operation above, and the ordinary
manual Project import form (ADR-0017). Both entrances share creation_input and
creation_job; manual use requires no provider/RPC. The offline manual snapshot
uses the app-private temporary host directory and refuses overlap with either
actual runtime writable root. It does not reinterpret an empty workspace as cwd,
read arbitrary chat paths, alter a grant or trust a model-supplied file path.

Visible mode preowns a finite input sequence, form/row/editor/helper text roles,
original prepared result and exact account/receipt/Session/source authority before
showing controls. It uses real tabs, ComboBox opening/keyboard choices, paced text,
Add rows and the real final Apply. Apply parses the actual complete form and
requires equality with the original recipe and immutable selected IDs before the
shared native job is admitted. No scientific mutation happens while staging.
The global nine-tool catalog and strict bundled core capability prerequisites
are unchanged; project-assistance version1.5.12/index digest/effective instructions
advertise this actual route, with missing folder intake and visible saving still
explicit limits. Capacity or deadline refusal does not trigger normal-mode fallback.

Manual import captures source hashes, original Controller/Session/PVM and WorkStamps
before its worker. A current nonadopted failure keeps that same correctable intent;
Close/Stop/Clear, source/owner/account change and actual adoption do not renew it.
Same-owner population remains one real manual structural edit and scientific Undo:
it does not suppress ordinary projectEdited/context retirement or grant consent.
The closed population commit latch and preowned complete/uncertain view projections
retain the actual result despite that ordinary retirement. Publication requires
the original owner and the exact single ordinary Session/file-intent retirement;
explicit abandonment and newer owners/forms cannot be overwritten. No-project
manual adoption uses the original prepared Controller/adjacent Session commit,
with receiver and original identity checks after every reentrant publication.

Original tool final delivery remains once-owned. Stop/close after worker admission
sets cancellation and retains the actual final delivery/receipt; it never answers
or cancels a newer call. Form cleanup clears original task ownership before any
notification, balances only its original input helper, and makes exact-form QML
cleanup terminal. Manual takeover marks eventual sidebar restoration and defers
projection changes until its unchanged original event returns. Old callbacks,
queued tasks and original response tails fence receiver/call/receipt/account/
project/window/helper identity rather than treating a surviving shared widget as
authority. Saved=false and modified/path-preserved completion remain truthful;
this operation adds neither current-directory saving nor folder read admission.


### Native import recipe encoding admission

The common native import form and its manual/assistant Apply decoders share the
existing context-byte limit. Each decoder admits the actual complete UTF-8 length
before allocating its owning encoded recipe, using the bounded code-point
encoding walk already used for assistant diagnostics. The post-encoding byte
check and the existing JSON parser, typed recipe validation, original recipe
comparison and source/owner checks remain in place.

The form retains its bounded raw-draft preprocessing and additionally counts the
complete plain recipe's JSON spelling before `JSON.stringify`: field names,
punctuation, numeric spellings, Unicode and JSON escapes all count against the
same context-byte limit. The count admits equality at the limit. It does not use
a six-times estimate at the decoder limit, which would reject otherwise valid
Unicode or ASCII recipes. The existing JSON writer remains the sole serializer;
no parser, scientific operation, file authority or lifecycle behavior changes.


The recipe byte counter follows the pinned Qt writer and converter at malformed
UTF-16 boundaries too: an isolated surrogate retained by JSON.stringify contributes
zero bytes through that stateless UTF-8 conversion; a valid pair contributes four.
This matches the common decoders' actual Qt preflight and final guard without
changing parser policy, normalizing input or raising the admitted byte limit.


### Committed manual import presentation

The ordinary native Import form and the visible assistant route share native
creation, but a manual form's completed status is separate from new tool or
account authority. Same-project population uses the existing structural editor
and emits its normal project-change notifications. The Session, result manager
and disconnected context cleanup may each retire their own intents; those
notification counts are not a scientific-edit identity.

After the closed population or Session adoption has latched a real commit, the
manual projection checks the original live project and Session owner, binding,
input serial, immutable selected-source ID/content hashes, form ID and exact
creation/form ownership. It also retains the original connected/disconnected
state; a connected original must keep its exact account epoch, while ordinary
disconnected cleanup may retire its notification counter. Explicit Close, Stop, Clear or sign-out abandons that
intent before publication. A replacement owner, source change, newer form or
creation, or retired presentation cannot receive the older result. Notification
retirement alone does not erase an already committed import outcome. The same
check applies to successful and incomplete publication, for both existing-empty
and no-project manual imports. It grants no retry, disclosure consent or further
scientific write; genuine context retirement and Worker final delivery continue.

The original assistant RPC path retains its existing record, receipt, once-only
response and own-edit rules. This presentation change does not suppress model
notifications, undo a user's edits, change the parser or scientific data, or
alter one-step population Undo.


Exact-ID form Close, hide and destruction first find the matching live manual
draft, then the matching original manual task retained by native creation's
final delivery. The task can outlive its draft because the committed edit's own
notifications retire that draft. The existing cancellation helper marks explicit
abandonment before any callback; an old form ID cannot cancel a different new
draft, creation or visible request. This closes the public-caller path as well
as the helper path without treating ordinary notification retirement as Close.


### Same-project native conversation and disclosure scope

The native runtime separates an original action's scientific work stamps from
permission to disclose project inputs and from the backend conversation's
memory. The prior full-context equality remains the restricted/browser
compatibility rule. Native scope instead binds the actual PVM/core owner,
account epoch, immutable selected source ID/content identities, bounded raw
measurement content and topology, bundled skill/registered tool identity and
pinned physical folder capability. Metadata names or array summary counts alone
do not prove unchanged inputs. Raw written/membership identities cache exact
content hashes; equal rewrites can retain scope without walking arrays on every
unchanged UI getter. Inputs beyond the existing selected-input collection bound
refuse instead of falling back to weak summaries.

Routine same-owner scientific edits and ordinary fit completion still retire
old calls and await their original input/control/Worker obligations. If scope
is unchanged, settlement retains the real thread and workspace while clearing
per-turn presentation. A genuine project/input/root/capability/account change
upgrades retirement to fresh memory; a later ordinary edit cannot downgrade that
pending revocation. Original pre-ACK interruption, deadlines, archive failure,
account and final-delivery fences stay authoritative. Each admitted next turn
captures complete fresh GUI context into its exact native receipt rather than
copying an earlier consent snapshot.

Native scope approval is preowned across actual account bootstrap. A no-owner
native creation lands its prepared new-owner proof beside the existing adjacent
Controller/Session commit; same-owner edit/save refresh only their original
receipt after exact actual scope checks. Ordinary Save alone is not proof of
content identity. Manual imports never implicitly disclose their new project.
Clear commits real archive discard independently, then waits for settlement and
binds fresh model/UI memory. Only a preowned proof of the actual remaining input
subset, unchanged project/account/capability/folder scope may retain consent.
Failed discard or a newer owner cannot restore an old approval.

Proof/cache and simultaneously held metadata/encoding roles use the existing
combined native/item/progress budget. Scoped temporary-role charges survive
notification retirement and are released only by their own stack, with receiver
lifetime protection; they cannot release a newer operation's reservation. No cap
is raised and no raw model copy, second scientific serializer, new permission
system, provider history API or global setting is introduced. Generic scope
approval no longer retains an unused full-JSON consent copy; exact fresh context
still belongs to each admitted native receipt. Restricted compatibility keeps
its existing exact-context approval path.

Existing staging is never rewritten during reuse: it may contain provider
changes. It is not authoritative GUI state or an automatic import source. Fresh
per-turn GUI context, retained conversation and recoverable staged artifacts
remain separate. Sent attachment chip presentation is also separate from
immutable source authority: future acknowledgement UI must not revoke active
inputs merely to hide chips, nor reuse genuinely revoked content.

The capability proof fingerprints the embedded index and the actual registered
native names already admitted in context. Their typed schemas are immutable for
this process; changing the binary cannot reuse a live in-process proof. Scope
preparation does not rebuild tool-schema arrays. Proofs held locally across
Clear rebinding remain charged until that stack releases them. If this optional
remaining-scope proof cannot be admitted, Clear still clears memory and requires
fresh approval. Original owner/account/input fences surround settlement and
failure continuations, so an old callback cannot approve or retire a newer owner.


### Coherent native import row projection

The ordinary native CW import dialog and its visible assistant route share the
same staged row editor. Its actual ListModel determines the row roles: background
and exclusion rows have two numeric draft strings; initial-parameter rows have an
exact path and numeric draft string. Inputs and Instrument may keep that hidden
parameter model selected, so a tab label alone cannot choose another model's roles.

Each row load captures the original request, section, actual model and selected
index, reads both actual strings before publishing either, and owns one local
projection while text notifications run. Settling a model binding refreshes the
projection; an obsolete section/model/selection cannot write staged text. A nested
load owns its own loading fence, and old cleanup cannot release it. Add, Remove
and text updates use the same captured selection and actual model roles. Missing
roles refuse projection instead of becoming a string, zero or scientific default.
All literal drafts, recipe admission, selected-file authority, original Apply,
worker/commit/Undo and once-only outcome boundaries remain unchanged. The prior
relation form uses the same id/definition/enabled roles in both of its models; it
does not need an alternate role mapping or a new shared staging framework.

### Save form intent and recovery

The ordinary Save and Save As controls consume one original intent. The fresh-name
form retains its original owner, presentation token, chosen parent and literal
name before any notification can reenter it. Apply consumes that token before
closing; Close, rejection and destruction cancel only the exact original token.
A later form or project never inherits the earlier action. Genuine manual or IME
drafts survive assistant takeover retirement; cleanup restores only assistant-owned
staging. Assistant results and refusals belong to the original RPC, so the shared
footer does not add a second generic Save error modal for that operation.

Same-directory native saving publishes through the bounded ordinary formatter,
then verifies the published bytes and lands saved values on the same PVM. Full
loaded verification models are released before owner presentation callbacks.
Ordinary Save/Save As caller continuations retain weak original Session/PVM and
replacement identity across the common writer and every subsequent signal. A
retired presentation does not alter the writer's factual return or update a newer
owner's error, location or save-state presentation.

An exchanged current directory leaves its previous exact tree at the returned
recovery_directory sibling. Each captured/staged tree obeys the existing per-save
file/count/byte limits. Recovery trees remain on disk until the user removes them;
this is a conservative per-operation recovery policy, not a claim of globally
bounded disk use across repeated saves. No pathname-based automatic recursive
cleanup attempts to distinguish the old tree from a substituted foreign object.
Publication reports committed uncertainty immediately after a successful namespace
operation even if identity verification, reopen or presentation later refuses.

### Prepared saved-value metadata admission

The bounded Save landing admits new joins, copied correlation rows/columns,
parameter landing slots, temporary completed/written name maps, relation slots
and per-bank/per-structure source strings before constructing them. It reuses
the original borrowed parameter-name admission walk in join-only mode; ordinary
full source admission keeps its original counts. Actual calculation buffers and
original stamps move from their preowned result slot, with no second model
charge. The PVM wrapper also admits its object/control block and exact UTF-8
destination scratch before creating them. The legacy core entrypoint keeps its
existing behavior; assistant saving explicitly passes a finite remaining role.

The role is owned through the existing combined native/item/progress scope
reservation, including reentrant presentation and failure unwinding. Its limit
is the actual remaining capacity after source, calculation, UI and prepared
outcomes, never the scientific construction cap. No new capacity is introduced.


### Save final-delivery payload ownership

Worker settlement and retained payload lifetime are separate. Final Save delivery
holds a strong original task and a stack-scoped accounting link until its frame
returns. The ordinary active-worker slot still retires at the existing boundary;
this link never makes an old worker admitted or cancels a replacement. Active and
delivery aliases count each task, original receipt and record once. A discarded
row does not erase the original frame's payload charge, and an original final
context slot remains admitted while that frame can still use it. Nested delivery
unwinds in call order and cleanup touches only the same surviving receiver/State.

Final link removal is callback-free. The idle Worker's existing owner-thread
Post epilogue reconciles the transport charge after the delivered function and
its captures have been destroyed. Earlier local release guards measure all
remaining owners, including the still-live delivery task. No old worker stays
admitted to obtain this release, and an old estimate never subtracts from a new
call's ownership. If measurement cannot complete, the conservative prior charge
remains; no live payload is uncharged to manufacture capacity.

Receipt export now has an allocation-free byte/depth/token prepass over the
existing closed schema, before toStdString or strict-parser growth. Native Save
preowns input, AST/key/reader workspace through its original scoped metadata
role before constructing the exporter. This is admission only: the original JSON
parser, exact keys, UTF-8, hashes, file closure and original authority still decide
validity. Trailing malformed punctuation cannot discount an allocated prefix.
Exporter entry vectors, exact UTF-8 paths/hashes, JSON files/root/receipt,
closed verification sets and directory/Unicode work, protected readback and
publication paths share a finite preparation peak. The caller preowns its actual
remaining retained capacity before construction, then transfers to that counted
peak without a callback; the role remains through original final delivery.
The generated protected receipt uses the existing JSON formatter and borrowed
encoded-size walker. A larger readback receipt admits only the positive parser
workspace difference beside the already owned original parser role.

Typed picker/current-directory capabilities already carry physical paths. Their
export, namespace revalidation and protected loading use the common no-follow
component reader directly; the ordinary raw-parent Save As path keeps its
canonicalization and reserved-storage checks. The current-directory constructor
admits its known parent/leaf copies before splitting, including a filesystem-root
parent. No unknown replacement canonical string or guessed path expansion slot
is created by bounded export.

Protected readback reuses the first host-owned result snapshot factory at the
original admitted lease's physical parent, with parent/source/result descriptor
bonds before and after creation. It uses the explicit ordinary temporary-name
template, with exact text/UTF-8/split roles admitted before construction. Actual
committed bytes are still copied and hash/closure verified there before the real
loader; the original source snapshot never substitutes for postcommit readback.
The first snapshot factory retains its existing host-storage policy, and ordinary
manual exporters use that same implementation. No arbitrary filesystem seed,
new capacity, extra full model, alternate serializer, mutable-path cleanup or
claim of a perfect filesystem compare-and-swap is introduced.


### Background through its original row controls

BackgroundGroup's original Add, ID/position/intensity rows, parameter context
menu and Remove are the manual and visible entrances (ADR-0043). The duplicate
background setup form is removed; Add creates the ordinary default editable row
through the same closed editor and recorded Undo. Native normal mode retains
one strict operation; genuine visible actions prevalidate the final request and
perform separately prearmed real human edits, retaining each actual Undo and
complete/partial outcome. Exact row/bank/source/request identity, manual drafts,
Stop and replacement are checked between events. The existing private mouse
owner balances the actual button, including right-button retirement/deferred
cleanup; the exact parameter menu is dismissed by real Escape. No control state
is assigned to manufacture visibility, activation or a scientific result.


### Original text input ownership at commit callbacks

The shared TextCell manual/draft/IME and synchronous commit boundaries follow
ADR-0017/ADR-0024: genuine preedit/text detaches the clean binding without text
assignment, captures original delegate/project context and revises its draft
record for every real input. A single-entry commit retains that record and
lifetime across the model callback, reads only its captured current owner's
diagnostic and abandons obsolete cleanup. The helper verifies that the original
TextCell actually admitted assistant ownership before selection/typing. Actual
prearm/model validation/Undo and per-control applied outcomes remain unchanged.


### Original structure and experiment file entrances

The first Structure Load button and FileDialog now accept native .edi and
supported single-structure .cif. Native blocks keep the strict existing schema
loader; CIF calls the already existing structure_from_edi_text reader through
the same file reader. No alternate parser, conversion or scientific setup form
is introduced. The ordinary load preowns its structural Undo before the same
closed addition and retains actual applied state through presentation failure.
It adds to the original project, preserving its identity/metadata/settings/path.

Original structure, experiment-block and measured-data choosers capture the
project and exact data target when opened. Each native/browser answer consumes
its one original intent before invoking the same loader; replacement/duplicate
answers cannot target a new owner or clear a newer chooser. Existing browser
request IDs and native picker behavior are preserved. The existing FileDialog
instances have stable semantic identities for genuine subsequent input; these
changes do not claim native macOS-panel automation or a completed visible
creation route. The duplicate import-window removal and complete original
creation/field sequence remain a separate connected continuation.

The existing browser chooser's synchronous cancellation also retains its exact
receiver/request serial. If a callback deletes it or admits a new request, the
old begin refuses with zero; all existing callers stop before further member or
filesystem access. This preserves a newer browser picker rather than overwriting
its active ID. A never-opened original QML intent is consumed on refusal, so it
cannot block the next ordinary Load. This changes no file grant or science.


### One text terminal entrance and explicit row ownership

A TextCell commits only from editingFinished. Pinned Qt emits that signal before
accepted for the same Return; accepted keeps only the original base visual
feedback. It cannot capture/commit/clear a newer changed, identical or committed
IME draft admitted during the first synchronous publication. A genuine later
Return or focus loss still has its own editingFinished and commits normally.
The existing single-frame latch continues to prevent recursive notification
entry; it is not mistaken for proof against the later accepted signal tail.

The base ListViewDelegate places contentRow inside a FocusScope. TextCell's
immediate visual parent therefore is not the data delegate. Every original
TextCell declaration supplies its actual lexical delegate, source model and row
index explicitly. These bindings, current Session project, semantic control name
and lifetime retire original ownership on actual changes; value-role publication
does not become a new owner. No parent.model/index inference or synthetic input
is used. Existing draft/IME/binding/refusal/formatter/model/Undo/prearm behavior
and all unrelated original controls remain unchanged.

## Joint output capacity before retained construction

Prior implementation: CodexAgent::retainOutput owns the shared retained-output
limit, charging the VM's native/item/progress owners beside the current parsed
record and unread input. Native Save source capture, exporter/publication
preparation and visible input preparation previously subtracted only VM owners
when taking their remaining slot. Filling that slot made the next retainOutput
check fail whenever the original RPC record still occupied transport capacity.
This is local retained-output admission, not subscription or model quota.

The same transport now provides a callback-free remainingOutput query with the
exact existing checked subtraction and inclusive boundary. It neither reserves,
releases, publishes, reads input nor changes process/account/request state.
retainOutput uses that same predicate and keeps its original failure/termination
behavior. VM native_room combines native, item and progress owners with those
actual current transport roles. All remaining-slot constructions and disclosure
pre-growth admission use that common calculation. No fixed headroom, capacity
increase, current-data truncation or live-outcome eviction is introduced. Before
a transport exists, there is no transport-owned record or input to subtract.

The slot is still charged through native_charge before construction. Source
capture transfers it to the actual retained source image; exporter preparation
retains its existing exact smaller prepared role; publication retains its
conservative original scope until its local owners unwind. A failed original
constructor or retired owner keeps the existing release/receipt/uncertainty
rules. No callback runs between the query and scalar slot installation; callers
retain their existing rechecks after effects. The query is not a promise about
future input: later records and actual retained roles remain subject to the
unchanged guard. Fit/project values, Undo, source permission, writer/reopen/
adoption and factual committed outcomes are unchanged. No automatic Save retry
follows a capacity refusal, and an already committed destination is not retried.


### Save publication and final delivery retention

The original native Save exporter and prepared saved-state metadata retain their
whole admitted slots while their actual local owners are live. On success their
scope ends before `native_finish` performs the required changed-project disclosure
refresh. The same order holds on exceptions through normal unwinding. The rounded
calculation, original result and final-delivery task remain charged independently;
this does not borrow their capacity for a separately live refresh proof.

Temporary disclosure and exporter release guards subtract only their own ended
role and then recompute the current aggregate. The transport's internal release
operation can only lower its previously admitted output role for the same live
process generation; it has no callbacks, cannot admit growth, and leaves the old
conservative charge if accounting cannot complete. Original receiver, State, account and live process generation fence this
reconciliation. A new input or project on that same account and process is
measured as current ownership rather than charged by subtracting old estimates;
no former receipt or outcome supplies the replacement aggregate.

The existing idle Worker's queued Post seam destroys the delivered function and
its captured task before its release epilogue measures current ownership. The Save
preparation closure relinquishes its own no-longer-read task capture before
returning that final delivery. Reconciliation runs in this original owner-thread
event, with no timer, input retry or provider protocol change, before ordinary next
frame processing. During reentrant delivery all still-live local and task roles
remain charged. Retired processes and changed accounts or States are never revived or
lowered by old cleanup. Mandatory refresh, source permission, committed/reopened/
active latches, uncertainty, Stop and exactly-once response behavior are unchanged.

## Original human creation controls

Creation in Show actions uses the existing Project Create dialog, Structure Load,
Experiment Create and type/data/profile/instrument/phase/background/exclusion
controls, followed by Analysis Main. This replaces the parallel native import
form, its Project button and public form API; earlier form/row-model descriptions
above are superseded. Normal mode retains the same bounded native preparation,
reader, same-owner empty-project completion and atomic scientific Undo.

A visible operation parses its finite explicit recipe and verifies both admitted
readable file IDs before input. It owns its finite control plan and captured
source buffers before growth within the existing combined retention policy.
There is no unused preview project: the original structure and measurement
loaders supply validation and actual reader statistics when their real controls
accept. The first original experiment is created and its type is chosen before
data loading; the same validated model editors receive all subsequent values.
Existing scientific defaults are not described as supplied observations. A later
refusal leaves only genuine completed controls, with ordinary per-control Undo.
`complete`, `atomic:false`, `steps_completed`, actual reader counts and the current
adoption/calculation/presentation facts report that sequence; creation never
implies a fit or a save. Parameter/free multi-input parity and scoped folder
acquisition are separate unfinished capabilities.

The original FileDialog instance uses its standard toolkit fallback only for its
exact owned visible operation. The genuine current picker receives Ctrl+L and
literal protected capture-path input through its own breadcrumb and Return.
Neither selectedFile assignment nor emitted accepted substitutes for that input.
The original picker owner/experiment/token and immutable admitted source bytes
remain authoritative. Its configuration is restored only while the original
operation still owns it; a newer manual picker is preserved. This does not claim
native macOS-panel automation or grant a pathname mentioned in chat.

With no project, the original Create dialog's actual name/description and empty
location create the ordinary unsaved owner. Its existing Session pointer commit
prepares and installs the same controller/selected-input attachment without
retiring the original native RPC. The original name field follows the core's
no-path-separator rule, allowing ordinary Unicode names rather than imposing an
assistant-only ASCII subset. An existing scientifically empty saved owner skips
Create and keeps identity, metadata, settings and path. No nonempty project is
replaced. Stop, manual input, account/owner replacement and late callbacks keep
the original once receipt and factual edits. Cleanup uses exact original form,
helper, prearm and picker identities before each notifying continuation; it never
closes a newer picker or routes an old key release to a newly focused field.
The original asynchronous calculation signal resumes the next original step;
there is no pseudo-idle property or independent polling lifecycle.


The original creation control metadata is a finite `CreationAction` equivalent
to the existing relation-control metadata: experiment Add/type/name, profile
choice and exclusion Add/bounds. It is app-private and not a provider-selected
QObject/property executor. The original model control must consume the exact
prearm before its own closed edit. File prearms similarly bind the original
owner/member and admitted capture. Original structure/data and experiment-Add
Undo storage is prepared before the live edit; later presentation does not
invent a failed write. Post-publication model callers first check their original
weak receiver. Shared category selectors retain their original activation,
options and owner across selected callbacks, rather than reading a replacement
project's error or rebinding a newer choice.

Actual source capture, the finite plan's container/spellings, one helper/editor
and restoration role, bounded diagnostic/result fields, file/control receipts,
background preparation and simultaneous original CIF text are charged beside
the existing native record/post-context roles. Counts come from the original
reader receipt even when delivery/presentation becomes uncertain. Source-file
and model construction retain their existing reader/editor policies; the live
ordinary project and its Undo are not charged again as a duplicate preview.
No allowance, file limit, operation deadline or scientific value is raised.

## Original creation continuation and failure ownership

The original Structure and measurement FileDialogs keep configuration cleanup
ownership separately from assistant mutation authority. Manual takeover detaches
that authority while preserving the actual open picker and event. Exact original
configuration cleanup survives through ordinary accept/reject/visible teardown;
it cannot restore over a new intent. Retired unopened configuration is restored
synchronously before the next ordinary Load/assistant preparation, so deferred
cleanup alone cannot strand the original human door. Options and popup preference
are restored only while the same original configuration still owns them.

Shared group/outer viewport reveal discards only the create_expose helper. A live
background or parameter child resumes its same original member, step and applied
latch after the real reveal. Inner-row scrolling already follows that rule.
Revealing an already applied Add cannot create another child/Add or lose factual
per-control counts. Original controls and ordinary Undo remain the science path.

The existing Session creator has one shared implementation. Its ordinary dialog
uses createProjectWithOutcome to receive a caller-local success/current/error
snapshot, with the actual committed owner/replacement identity. replaceProject
writes that identity beside its real pointer commit before callbacks; no guessed
notification count is used. creationOutcomeCurrent rechecks it after notifying
error presentation. The same saved-location failure still leaves its actual new
project open unsaved and opens create.error, using the original error string.
An original dialog-operation object and owner/replacement checks prevent an old
return from presenting for a later Create or replacement, even with identical
input. The old bool createProject API calls that same implementation. Assistant
creation retains empty location/no-save and its existing original receipt.

Both noexcept child completion/refusal entrances contain the entire fallible
result transfer. Nonallocating scalar capture bonds actual applied counts once
before JSON retention; the original may-have-written latch is preserved. Creation
preowns the ordinary native uncertainty outcome/response/row before input and
counts these roles in native retention. If factual replacement construction fails,
those exact original prepared objects are swapped into the existing native_finish
path without allocating a new fallback or claiming zero writes. Delivered/discarded
facts are not overwritten. The original task/receipt/once and new-owner guards
still govern all later cleanup; no second result executor, rollback or hidden
backend edit is introduced. Actual event, allocation-fault and platform-picker
execution remains a separate qualification requirement.

## Edi-owned input and persistence; no assistant working-folder grant

This supersedes the earlier workspace-write/chosen-root and provider-result
handoff paths. There is no user-facing assistant working-folder choice, retained
root configuration, writable-root request, raw project/attachment staging or
model-authored saved-result receipt. The original application remains the only
scientific editor and project writer. Internal bundled instruction staging and
immutable selected-input caches are app-owned storage, not model write roots.

The existing CodexAgent process starts with the pinned read-only sandbox and
never approval policy. The thread/start effective response must confirm the
actual model, effort, provider, cwd, ephemeral thread and exact readOnly policy
with networkAccess false, never approval and user reviewer before inference.
Model/effort changes use the pinned thread/settings/update operation; its empty
acknowledgment is not proof. Only the actual matching settings notification can
restore readiness. Every turn carries that same read-only/never policy. Mismatch
fails closed through the original process/account lifecycle. The stock runtime
still exposes general reads and tools; this does not establish a strict Edi-only
tool ceiling, complete raw-data redaction or every inherited extension's write
behavior. Disclosure retains that limitation. No supported-but-unverified wire
field or prompt is treated as enforcement.

The prior selected-file cache and native readers remain authoritative. The
current genuine user's attachments and complete literal source lines can create
opaque scope IDs before the actual message admission. Only that message's
accepted receipt owns them. No scope is minted from model arguments, history,
assistant/tool text, paths embedded in prose, examples/exclusions/output blocks,
quoted blocks or code fences. A source line is an absolute local path, home path
or local file URL, optionally introduced by Input:, Source:, use, read, load,
import or from. Spaces need one complete matching quoted literal; traversal,
control characters, shell/glob syntax, ambiguous delimiters, remote/query URLs
and relative paths do not grant scope. Expansion/URL decoding recheck that same
local path boundary. Native path limits and the existing message/metadata budget
apply, rather than imposing the tool-ID bound on a pathname.

The registered acquire_inputs operation accepts only scope_id and purpose. It
captures immediate relevant regular files through pinned local handles, refuses
linked children, duplicate physical files, protected storage, changed identity,
invalid Unicode and existing count/payload/metadata limits. It does not follow
subdirectories. Original aliases can identify the pinned selected object; a
retarget cannot. The result has actual immutable collection IDs, occurrence
ordinals, reader hints and factual counts, not raw lines, paths, secret hashes or
an import success claim. Successful repetition returns its already admitted IDs.
Failed preparation admits none and keeps the previous selection. Collection
adoption is one existing Controller update. Its actual returned collection and
IDs, not guessed epoch deltas, advance only the original RPC's selected/disclosure
receipt. Factual admission is recorded before model signals, and an old
continuation cannot clear or overwrite a new owner's receipt. This avoids
self-retirement while the current Edi operation still owes its response.

Input representations are admitted before growth beside current transport and
native owners: exact literal/expanded spelling, canonicalization scratch, source
shell/vector storage, collection replacement maps, names/IDs/hashes, read buffer
and actual result wrappers. Completed source metadata stays charged while the
next source and eventual input receipt are constructed. Cache-stage roles remain
owned through the caller and release only after their old/replacement maps and
cleanup list die. Payload limits are the existing selected-file policy; there is
no cap increase, transport headroom constant or whole-model second charge.

Current save_project uses only the actual Session-owned saved directory with
its original source identity and bounded carried-record writer/reopen/adoption.
Fresh saving uses the original Save As chooser and name form for one operation.
No pending Worker or retained Job/task cycle exists before that genuine choice.
Session consumes its original intent before its start callback and calls the
original cancellation closure on retirement even if its token has already gone.
All normal/visible/Stop/replacement/scientific-change/error paths settle only the
old unsubmitted task; an admitted ticket retains its actual Worker and final
once-owned outcome. The picker-selected alias and physical destination remain
pinned for publication. Fresh output is no-replace and cannot nest inside the
captured source; current replacement retains the old recovery tree. Real
committed, reopened, active and presentation-complete facts remain separate.

Show actions uses the original Project/Structure/Experiment/Analysis groups and
the same real Save/Save As controls. A visible Save waits for the original parent
chooser, then enters the requested fresh name through the ordinary form. No
synthetic accepted signal or native callback is a substitute for visible input.
Ordinary manual draft/takeover semantics remain authoritative. The obsolete
import wizard is removed only with the connected original creation sequencer;
normal native creation remains the same validated reader/editor. The original
saved empty owner retains identity, name, path and metadata. Visible steps retain
ordinary Undo and truthful partial outcomes, not atomic batch fiction. Parameter
and free-flag multi-input visible batches are still a separate missing route.

Same-project routine edits can keep their legitimate thread. On a required
same-owner input refresh, a literal continue can carry the bounded genuine completed user messages from the current objective in their original
order as preceding supported user text items, followed by the exact new draft and current context. No assistant/developer/tool role or fabricated
history field is replayed. This context-only text is never reparsed for local
read authority, and its original account/project/generation must still match.
Clear removes the anchor; account/owner replacement cannot inherit it. No
persistent UUID, provider archive policy or cross-restart grant is added.

Source and syntax checks establish only the connected candidate. Packaged policy
responses, native OS/toolkit picker delivery, visible scientific controls, reentry,
allocation/IO faults, Save recovery and scientific/Undo execution require the
normal consumer and independent runtime qualification before release claims.

### Input classification and final policy admission ownership

Protected-path classification must name the object actually opened. The shared
input predicate therefore binds the original descriptor, the physical classified
path and the selected spelling together. Unix reuses the writer's original
component-wise no-follow physical descent and final identity check; a mutable
symlink parent cannot redirect that classified path. The ordinary Windows file
reader uses the normalized name returned for its actual opened handle and its
native file identity, rather than blessing a separate canonical-path lookup.
GetFinalPathNameByHandleW's normalized-handle contract is documented by
[Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew).
The same bond is checked before capture and immediately before collection
adoption at both the opaque-scope and ordinary selected-file entrances. Ordinary
selection keeps its original open handles and content/identity stamps until that
whole collection attempt ends. A fixed selected alias remains valid; A→B→A
classification and parent-link swaps cannot classify B while reading A. Linked
children and protected paths remain refused. Retained proof paths/containers and
one native classification scratch role enter the existing joint metadata budget;
no pathname/tool-ID cap or new payload allowance is introduced.

A dependent input belongs to its original selected model/effort and verified
actual policy, not only the thread/account/project. Policy invalidation and
readback carry an original monotonic identity; exhaustion refuses new inference
without interrupting mandatory cleanup. Final before-write admission checks this
identity, exact selected/effective settings, verified policy and nonconnecting
state before and after native retention, row publication and optional-Usage
preemption. Equal settings without a new transition remain valid. A superseded
unwritten input releases only its original maps and pending row, retains its
original draft/once semantics and cannot settle the newer settings deadline,
restore old preferences or fence a newer account. Already written input keeps its
factual accepted identity. Failed pending-row archive cleanup is a real storage
failure, never evidence of a successful wire write or permission to discard B.

The physical input leaf is opened under the original read domain, separately from result-tree naming. In particular, lawful Unix source names ending in a dot or space (including a fixed selected alias to that physical leaf) are not normalized or rejected by the writer's basename rule. The same classified descriptor, original spelling, no-follow parent walk and final object/currentness checks still govern both input entrances; result publication keeps its stricter leaf validation.


### Human wait owns no inference time

The original native Save As intent and single app question are human-input
boundaries, rather than continued inference. Their exact outstanding server request
and original transport generation own one pause of the existing inference clocks.
Entry checks the original expiry without callbacks; duplicate entry cannot renew
the pause, and a different request or retired generation cannot replace it. The
original inference total and idle timestamps advance by exactly the human interval
on exit, retaining their remaining budgets. Real protocol activity keeps its
ordinary meaning. Current-directory Save has no human wait. Fresh Save resumes
before its original destination enters preparation or the Worker.

The original reply, rejection, resolution, Stop/revoke transition, failure and
process retirement release that wait once. Actual control-acknowledgement and
required-write deadlines, output/wire limits, process EOF and revoke limits remain
active throughout. Waiting neither fabricates activity nor repeats a scientific
operation, uncertain write or protocol response. The request key shares its
existing retained owner until it is cleared before removal; no payload or timer
framework is introduced. VM receiver, owner, account, source, call and Session
intent proofs remain independent requirements. Local transport failure is not
provider account logout: reconnect still requires fresh disclosure and actual
account reading, and never sets authenticated state merely to repair the UI.


### Current-save completion first cause

The existing native first-failure diagnostic also covers the original asynchronous Save completion before cleanup or fallback publication. Its closed stage identifies receipt preparation, bounded export construction, prepared progress, saved-value preparation, namespace publication, reopen, adoption, presentation or final response. The active exception is classified without its text. The same original call and receiver must still match; committed, reopened, active and presented are the task's existing factual latches, not inferred applied/published facts. The SAVE role's zero bound explicitly attributes no byte bound. Existing first-cause precedence and non-Save records remain unchanged. C stdio introduces no Qt message-handler callback, allocation, payload or path disclosure. This observation changes neither persistence nor the refusal/uncertainty outcome and does not establish a causal Save repair.

Closed action-refusal labels are compared by text, including labels stored separately from their compiled literal. Pointer identity is not a semantic refusal predicate. Both original-file classification and public closed refusal projection retain their existing field/error mapping.
