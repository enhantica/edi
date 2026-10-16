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
