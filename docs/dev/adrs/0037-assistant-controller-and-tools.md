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


### Shared current-Save worker admission

Normal and visible current-directory Save use the original native_accept_save_destination submission boundary. The empty parent and leaf are unused for a current destination; an explicit fresh destination keeps its existing validated picker path. The shared entry constructs the original job, rechecks the original receiver/currentness, marks submission in progress before the Worker can synchronously trace admission, clears that mark on either a thrown submit or the returned original ticket, and cancels only that original ticket if its owner retired during admission. The existing pending-task guard settles a refused or never-admitted operation once; it cannot confuse an in-progress submission with a task having no worker. No new Save operation, delayed admission, disk fallback, changed destination, human wait or larger resource allowance is introduced. Completion and its factual uncertainty remain the original shared exporter/adoption path. Removing duplicate submission logic does not establish the cause of a previously observed completion failure.


### Ordinary Save for an already-owned current project

The manual toolbar Main.saveProject -> Session.save -> ProjectViewModel.saveTo(current path) is the owning prior art for saving an existing genuine Session directory. The assistant's omitted/current destination now calls that same Session.save method once in both modes. Show actions supplies only the existing visual pointer/click cue at the original Save button; it dispatches no Save click/key or custom Save intent. A disabled already-unmodified toolbar action does not refuse the ordinary method. Name is unused, the original path/owner is preserved and no destination chooser appears. The current route constructs no assistant snapshot, protected exported copy, extra rounded calculation or PreparedSavedValues transaction. The obsolete result/reload allowance experiment is removed, restoring the qualified original five-argument calculation API and pre-experiment fresh export path. Explicit fresh Save As remains that distinct existing prior art and is not normalized into current saving.

The ordinary Save call is synchronous and keeps its actual app errors, scientific values/SUs/correlations, rounding/readback, Undo and presentation behavior. Session.save returns a bool; adopt_saved_values can decline an ordinary readback without turning that bool into an error, so current saving never infers reopened:true. saved/committed require a true ordinary return. active additionally requires the same original Session/project/path still unmodified and its original epoch/replacement; presentation_complete also requires no pending calculation. A separate ordinary disk/Session reopen is qualification, not an invented action. Failure remains uncertain, with no automatic retry or raw exception/model/path disclosure to the runtime. An already-entered synchronous Save cannot be undone by Stop; original actual facts settle once, while Stop/retirement still prevents subsequent work.

Only this invocation's early projectEdited is its own Save effect. The existing monotonic OwnEdit identity is consumed at Session.save entry before validation/error callbacks, forwarded immediately to saveTo entry and consumed there before its own validation. The four actual projectEdited emission sites use one private origin-carrying notification seam: ordinary/manual edits carry zero; only that Save's early notification carries the original token during its signal. Both Session's epoch/intent listener and the assistant listener match the exact owner/generation/origin. Nested/manual Save or parameter edits, early-error callbacks, later modified/path/report/directory callbacks and replacement owners cannot borrow a next-serial guess or scope-wide exemption. Existing PVM editing/currentness checks still reject overlapping edits, and genuine later edits retain their original retirement. No public notification API, event replay, new worker, scheduler, model cache or alternate persistence engine is introduced.


## Native selected-text action

The displayed official-runtime catalogue now wires read_selected_file at the original native admission/once-settlement boundary, independently of the restricted Controller manifest. Its exact closed request carries purpose, opaque file_id, byte offset and max_bytes bounded by SelectedFileLimits::read_bytes. No project, widget sequence or scientific edit is required. One current staged selected source is safely opened and streamed through its original hash/strict UTF-8 proof with fixed scratch and requested range only; unrelated files and whole collection/source images are not captured. Invalid, changed, missing, NUL/GPX or unsupported bytes refuse without text. Returned selected_text has the original file/collection/generation, strict UTF-8 text, total/start/end/next_offset and exact EOF/full-source complete facts, including zero and scalar-boundary cases. Explicit later reads retain the same identity; no cursor or automatic retry.

The closed outgoing SelectedText role validates all fields, byte-length/range and completeness relations before size/materialization. Valid maximum templates use actual remaining bytes and worst-escaped strict text, with original simultaneous scratch/raw/decoded/maximum/response/row/history roles admitted before growth. No policy limit increases or generic raw-string/exception projection. This is deliberate disclosure of selected source text, distinct from metadata-only inspection; arbitrary paths, binary deserialization and generated-file/converter workarounds remain unavailable. Reading never renews scientific write authority.

The original C++ intended names and dedicated host NAMES both include this exact additional function, preserving requested/advertised/dispatch/schema equality and duplicate/shadow rejection. The source patch digest therefore changes; only a genuinely rebuilt/qualified dedicated package with its real digest can satisfy that branch. Stock dedicated-OFF behavior is unchanged and no new archive/enforcement qualification is implied by source. Original source/account/selection/removal/Clear/Stop/late-call guards and reverse-ID once ownership remain. Later ordinary structure/atom action reachability and scientific interpretation correctness are separate capabilities.

### Selected-text live owners at the original codec boundary

The selected read proves original controller/account/project/selection epoch and exact admitted file/hash bindings directly; it does not serialize and parse the whole ProjectContext merely to compare selected metadata. Whole-target safe-open/hash/strict text proof is unchanged. Raw range and decoded text use exact owned arrays; the JSON text payload is a distinct simultaneous role. Borrowed Qt JSON string views validate/count large text without independent toString buffers; the original strict UTF-8/UTF-16 semantics and closed result relations remain.

A NativeRecord response maximum has no content consumer: all original consumers use only its encoded size, pending-role reservation or final clear. Keep its valid typed outcome maximum and store the conservative nested-response byte ceiling, rather than materializing an unused escaped document/string/JSON copy. Existing comparisons, once settlement and actual Qt encoding stay authoritative. Inner JSON bytes require at most twice their size inside another JSON string; its fixed empty wrapper owns delimiters. No response or policy limit is raised.

Actual projection, Qt encoder conversion/escaping scratch, encoded capacity, decoded array, independent response JSON, wire/line and optional holding backings each retain their own pre-growth role until death or exact transfer. Capacity checks reconcile the actual returned Qt buffers. The original transport queue, deadline, optional/required precedence and no-replay rules do not change. This is ownership of the existing codec's carriers, not a new serializer, allocator, file service, scientific workflow or memory/RSS measurement. A read that cannot fit the existing joint roles refuses without partial text; no chunk is silently reduced to fit retention.


### Finite ordinary structure catalogue

The app catalogue adds create_structure, edit_structure and edit_atom. Each invocation resolves exact current structure/site IDs, validates its complete closed request and resulting identity domain, and uses the original individual-action frame/receipt/disclosure transition. Create is separate from rename; symmetry edits invoke one original setter and return actual linked stored fields, including unresolved/cleared state. Atom append returns the actual early-pinned inserted identity; remove reports the original ID only after membership absence without dereferencing it. No-op compares stored canonical fields (original HM comparison, stored optional number/code, IDs/text and ADP type), before visible work or edit. Numeric scientific values are not duplicated in metadata actions. Closed outgoing atom_id/removed fields and metadata maxima remain under the original budgets.

Dedicated admission owns the original set_experiment_type root union too: the existing guard accepts a closed object root, or a sole-key nonempty oneOf of closed object alternatives. It does not append additionalProperties:false to a property-less union root or add a recursive schema framework. Canonical request schemas, intended names, converter and exact requested/advertised/full-schema/dispatch equality and duplicate/shadow/deferred rejection remain intact. The actual modified patch digest is the future dedicated package input; no archive/executable identity is fabricated and stock remains default OFF. Code-owned schemas/descriptions state concrete actions/options; project skills supply strategy, and restricted core capability lists remain separate.


### One ordinary experiment-settings adapter

`edit_experiment` adds one closed code-owned union for peak_profile(value), exclusion_append, exclusion_start(region,value), exclusion_end(region,value) and exclusion_remove(region), always with purpose and actual experiment ID. Profile enum values derive from the FIRST supported_peak_profiles selectors; the target's original mode/options must admit the token. Append uses ordinary generated identity/default bounds and returns the actual early-pinned row; later bound/remove operations name that real row. No profile/format catalogue is duplicated in skills. Numeric parameter tools, current scientific constraints and canonical no-op semantics remain unchanged.

App intended names, actual registration/arguments/read-write dispatch, original individual receipts, outgoing Region/profile/ID fields, context encoder/sizing and dedicated NAMES/closed-object-union requested-advertised-dispatch equality advance together. Maxima include escaped added strings/numbers and complete response nesting before write; current stream/context/file limits do not increase. The runtime patch's sourcePatchSha changes and must be bound by a genuinely rebuilt archive/executable/package proof; no old package is relabeled. Stock dedicated OFF stays OFF. This source adapter does not implement absorption/cutoff/weights/participation/phase links/calibration or establish PCR/TOF/multiphase scientific equivalence. Original current Save/Create/reader/ordinary structure Undo/live speed/general research guidance remain intact.


Experiment controls: row publication and registered option ownership

The original excluded-region Qt row cache is presentation, not membership authority.
Bound edits enter the existing CreationAction matcher and actual-member/readiness
boundary before equality or dereference, including synchronous removal/Undo signals.
Profile tokens belong to the original registered selector domain, not the 256-byte
member-ID domain. Their known requested payload and Qt/native preparation owners
are admitted before materialization and retained for both visible and normal calls;
terminal maxima use that actual token. A refused operation omits peak_profile unless
the canonical value equals the admitted request, rather than copying an unbounded
unrelated old token. Exclusion identities retain their original ID bound.
Names-only discovery uses only fixed action names. Full stock/dedicated thread
catalogues first walk borrowed original profile tokens, validate UTF-8 and charge
encoded catalogue, enum entries and overlapping decoded Qt strings under the
existing joint disclosure role. Both beam modes are included even without a
project; no discarded schema is built by names-only context. Existing catalogue
schema/dedicated equality, limits and normal transport accounting remain binding.


Original live versus retained native-call limits

CodexAgent's original stream_calls limit bounds outstanding server requests and
answer removes each settled request. The app native ledger deliberately retains
completed canonical/results/once facts until its original turn reset, matching
the original core completed-call cache domain. Native dispatch therefore applies
completed_calls to that retained ledger and stream_calls only to uncompleted
records; completed calls cannot prematurely exhaust the live-request count.
Duplicate original keys remain independently refused with no eviction/replay.
Existing byte/history/owner/currentness/admission limits remain unchanged. A true
count-capacity refusal uses the already-closed resource_exhausted result code,
without forwarding arbitrary messages or declaring the owner run's unknown cause.


Selected-text completion and original response ownership

Pending outcome/row/response slots are exclusive construction destinations, not
independent future owners stacked over every encoder scratch allocation. The
original finishing response temporarily stages that exact slot while all actual
fallbacks remain charged; on return the same slot owns the bounded local result,
and on failure it resumes the unchanged fallback. Actual final staged records
retain their real Qt payload owners without reserving another future final copy.
Maximum row content is no longer retained: all consumers require only its scalar
size, computed from the original empty-outcome row shell and outcome ceiling,
including canonical-item replacement/rollback. No maximum acts as scientific data.
The ordinary Qt writer remains unchanged. Its borrowed input walk also counts
actual string backing and its largest sequential escapedString/toString workspace
from pinned Qt6.11.2 rather than treating escaped document bytes as raw characters.
The transport appends LF in the same unique buffer; QProcess/holding copies keep
separate roles. Actual returned capacities and all original hard limits still check.
The one-file reader destroys file/hash/range/decoder scratch before response
completion while retaining its independently admitted exact output. Optional
history/archive presentation and the already-owned original fallback answer are
contained independently; exact record/receipt/RPC/transport generation are rechecked
before the sole answer attempt, including reentrant replacement and uncertain write.
Ordinary current Save remains Session.save; its preowned factual variants, original
first failure, source proofs, once/cancellation and scientific outcomes are unchanged.


Original structure cue local refusal observation

The existing opt-in edi.assistant.widget.lookup diagnostic records only the first
escaping local structure_cue stage: LOOKUP, CURRENT, EXPOSURE_REVEAL or
PREPARATION_INPUT, plus the original closed exception class and retained step,
kind and completed prefix. It does not query the UI again, dump a target/model or
change lookup, reveal, prepared input, ordinary mutation, timing or success guards.
Qt message-handler reentry is checked against the same weak receiver, original
record/receipt/helper/window/project/step and retained retirement/once facts before
old cleanup can continue. Disabled logging preserves the original exception path;
success/scheduled reveal adds no log or new observer. This is attribution of an
unproved visible-control failure, not a scientific/focus/geometry correction.


Original app calculation readout

The original PatternModel calculated(error)/markStale publication owns the chart
columns and its current published refusal. App native_state.calculations projects
those facts on each exact original dataset for context, inspect_project and
diagnostics, alongside existing global calculating/fitting/show_actions. It adds
no core Dataset status, calculation, cache, observer or scientific interpretation.
The pure calculatedPointCount getter reads only the existing published column size.
A missing exact view is pattern_available=false with other facts omitted; stale
columns/errors remain explicitly stale. The existing bounded_error readable-text
rule includes independent present/complete flags so omission cannot imply no error.
No published-point availability claim establishes visible legend/series state.
Original per-row names/text/JSON owners are admitted before growth and retained
through context/skill work and elapsed-message-handler callbacks; prepared project
attachment uses its own exact target, not the old current project. Existing closed
projection, disclosure, source identity, maxima and hard limits still govern.


Ordinary Save success reporting

The ordinary Session.save return and original active-owner fact already own
current-save success. Report a successful saved+active result plainly as Project
saved; do not turn an unrequested presentation/reopen observation into a save
failure or another save/wait/reopen operation. Real refusal, uncertainty, owner
change, explicitly requested verification and fresh verified export/adoption
remain factual. Tool help, both existing developer strategy paragraphs and the
connected project skill carry the same reporting rule; actual Save/result flags,
disk/science/Undo and native settlement are unchanged.


Send and connected-avatar circle interaction colour

The original AssistantComposer Send circle and AssistantPanel connected avatar
keep their existing contrast, size, enabled rules and actions. Their existing
enabled hover/down/visual-focus state paints the circle with themeAccent instead
of changing the glyph foreground. Default light/dark foreground and disabled
styles remain original. Disconnected Sign in retains its original foreground
interaction style and has no avatar circle. This extends the first existing
circle bindings, not a new control, colour constant or connection/input path.


Status-bar action circle paint bounds

The original AssistantWorking.iconExtent is the physical circle diameter shared
by the existing status speed and Stop buttons, distinct from a robot's larger
safe rotation envelope. Both existing backgrounds explicitly centre that square
paint bound and use the original composer's opaque contentBackground token.
Stop uses the original Composer solid stop glyph inside this full circle rather
than a smaller stop-circle glyph as its apparent outline. Original button hits,
visibility, speed choices/menu/live pacing, cancellation receiver and all working
animation/ownership remain unchanged; this is no new control or colour constant.


### Retained current failure remains visible after local disconnection

The FIRST AssistantPanel EdiNotice remains a selectable plain-text projection of
its original owner-bound noticeState. A local generic_fail already retains its
bounded lastError, but the connected chat column hides on disconnection. The
original signed-out area now reuses that notice above its unchanged centered
Sign in prompt, with explicit vertical scrolling for the existing bounded text.
Connected chronological anchors and signed-out presentation are mutually
exclusive; no error/archive copy or diagnostic message is manufactured. Existing
captureNotice empty/error/account/conversation/assistant replacement rules still
own clearing and identity. The original connection and Cancel/Stop actions keep
their geometry and behavior. This exposes the retained failure; it changes no
authentication/provider/logout, deadlines, retention, scientific or Save semantics
and establishes no cause for an earlier Create/disconnection failure.


### Structure visual cues obey the original input Request contract

The FIRST approved-file Load and ordinary current Save visual-only cues already
supply the AssistantWidgetInput Request's required prepareCommit/finishCommit
hooks. The shared individual structure/atom/experiment cue now supplies those
same no-op hooks, with their original captured/temporary roles admitted before
function transfer. The helper's existing required-callback guard is unchanged.
FileLoadCue still dispatches no device event or scientific commit; its completed
callback calls the same ordinary app method and validates actual receipts/member
state. OFF/no-op/owner/currentness/Stop/once/Undo behavior is unchanged. This closes
a deterministic malformed cue request at the observed preparation frontier,
not a new authorization/allowance or proof of provider sign-out causality.


### Ordinary setup controls follow their actual workflow pages

The existing parameter cursor owns the FIRST Structure cell and Instrument routes.
It also binds the current Structure's original site coordinate/occupancy and ADP
row roles, and the current Experiment's original profile, background intensity/term
and linked-scale roles. Scalar and array entries use the same category routing and
current registry/member/model checks. A table row not yet instantiated is revealed
through its original DataTable.revealRow against the exact source and row; the
subsequent cue still resolves the same canonical ParameterItem. No first-visible
row, Analysis fallback, hidden setter or scientific event input is introduced.
Original native validation and ordinary value setters/Undo remain authoritative.

Free flags/groups and fits stay on Analysis. Equal entries need no navigation or
setter. Normal value arrays retain their prevalidated atomic Edit/Undo and caller
order; their final page follows the last changed requested member, without
pretending an atomic array has separate visible per-entry transactions. A delegated
setup strategy plans Structure first, Experiment second, then Analysis release/fit;
it never sorts an explicit request or imposes phase permission. Genuine unavailable
controls, current-member changes and stale callbacks still refuse with actual
partial facts. This routing change does not establish the cause or cure of the
separate owner x5 Main-sidebar refusal.


### Initial setup binding includes manual semantic availability

The shared setup editor binding owns the original ParameterGrid usedByProfile
condition: Instrument and every offered profile-family row must carry a Boolean
true before scalar equality or whole-array admission. Current model membership
alone does not expose a field retained only because it is free. The same binding
requires original parameter refinability, the row's actual isotropic/tensor ADP
type, the active background layout's point/term family, and Boolean-enabled linked
scales. These are ordinary semantic editor conditions, distinct from temporary
collapse, clipping and virtual-row creation; those still use original reveal.
An unexposed later value cannot authorize an earlier array write, and equality
does not waive initial route admission. Original routes, caller order, setters,
Undo/once/currentness, Analysis free/fit and normal atomic edits remain unchanged.


### Plan setup in ordinary page and row order

For newly delegated setup the generated instructions finish Structure cell, then
each actual site row (identity/type/requested WP/coordinates/occupancy) before
appending the next; all ADPs follow together. Requested identity/symmetry
prerequisites remain scientific prerequisites. Experiment groups follow their
actual offered top-to-bottom order, then Analysis category batches and fit.
Initial-site reuse and canonical changed-only operations remain authoritative.
The existing set_free request can already express one complete eligible category;
its original header matcher uses Free-all only for the exact uniform set, while
subsets retain their real checkboxes. No new grouping API is needed.

This is planning for generated calls, not an executor sorting explicit arrays or
rewriting scientific intent. Caller order, dependency validation, OFF atomic Edit,
ordinary setters/Undo, current owner, once and factual partial outcomes are exact.
No numeric/refusal/deadline cause is claimed by this guidance correction.


### Actual app group order as fresh planning data (2026-10-19)

The first ordering authority is CategoryListModel::presentation_order, consumed by
Structure/Experiment CategoryGroup Repeaters. Its sidebar order can differ from
core parameter/file order: use that original model, not a second illustrative
sequence in agent prose. The existing native_state now projects interface_groups
for the exact current native members: page/member_id/category_id/tier/admitted,
in model order within Basic then Extras, including a category's Extras part.
These are category groups, not a copied widget inventory; compatibility is not
control enablement or a grant of otherwise unavailable scientific actions.

The projection is fresh with approved context and inspect/diagnostics results,
including for a continuing thread. Developer instructions and captured skills
still belong to original thread bootstrap; data does not silently rewrite those
instructions or reset the conversation. Generated setup plans read actual group
data, finish a group before the next, and preserve or explain necessary scientific
prerequisites. Explicit caller arrays stay in their original order; OFF remains
one atomic Edit, with ordinary same-value/once/Undo/current-owner behavior. No
within-call order flag or future-call scheduler is added. Layout data alone does
not guarantee model compliance across calls, so that remains a runtime outcome.

Current selected view, native member membership/generation and original category
model are checked around construction. Missing or contradictory owners refuse
the complete read rather than invent a fallback order. Native canonical ID and
decoded text, row/JSON and growing-array roles are admitted before allocation,
using existing disclosure limits; no new allowance or cached catalogue is added.
Actual empty/no-current-member pages have no rows. Genuine group expansion,
auto-collapse preference, selection, controls and all scientific methods remain
unchanged. This repairs missing/misleading planning data, not every reported
reopening/refusal or the separate operation-deadline issue.


Owner supersession: text entry is immediate and the action-speed preference is
removed. The original parameter/structure cue plus ordinary setter seam also
owns alias/constraint declarations, background IDs/positions and compound
experiment/exclusion/numeric fields. Existing prepared input, canonical member,
consumed/applied/published result and ordinary Undo remain authoritative; equal
values do not acquire a draft, cue or history record. The input helper edits
only the actual form/staged/filter or searchable-popup draft as one bounded
text replacement. The genuine offered-choice Return remains its selection
commit; no synthetic accepted/activated or direct index assignment is added.
Original pointer/navigation timings remain unscaled, as do scientific work,
readiness, deadlines, Stop and Working animation. No separate text executor,
model mutation through the helper, retry or permission/allowance is introduced.


Known pre-admission native refusals retain an app-owned closed code through the
original private outgoing projector. The existing native_owner/native_current
short-circuit predicates optionally report their first fixed failed group;
dispatch does not rerun them to guess a disjunct. Policy, original context,
owner/lifecycle, request/scientific freshness, pending operation, original-item
match, duplicate, capacity, argument class, busy calculation, visible mapping
and required project remain distinct at the actual source boundary. Typed
ActionRefusal/RecipeRefusal and source/policy/resource facts retain precedence.
Unclassified exceptions stay unclassified; no arbitrary message, what(), path,
account or input is forwarded. All added codes fit the original longest code
role, with the same actual sizing/projector/maximum and no limit increase.
These facts explain the gate, not proof of this owner's missing runtime actor,
permission to retry a write, or a new scientific/CIF/directory prerequisite.


### Correlated native work owns idle, human presentation waits own total

The original CodexAgent human-wait seam also owns one exact outstanding native
request/process-generation slot. Active correlated app work preserves only the
remaining inference idle interval; the original inference total stays bounded.
Only its genuine current ON helper waiting for its retained inactive window
additionally pauses total. App background during provider inference or a native
CPU worker without that presentation wait is not an exemption. Original human
question/fresh-SaveAs ownership remains separate. A single monotonic accounting
sample applies the union of paused roles once, without renewed budgets, duplicate
pause credit or fake activity. Original timer, control-write/ACK deadlines,
wire/retained bounds, EOF, Stop and finite revoke remain active.

Original RPC correlation gates precede native-work entry. Existing helper/window
lifecycle signals rederive only the current matched native receipt/record and
transport generation; stale edges cannot use captured old request data or a new
owner's interval. End/reply/reject/resolve and native retirement/settlement release
only the original slot. Operation-role transition/failure/process retirement
clear both wait owners with original expiry/remaining-total semantics. The
shared request key remains retained until matching release before removal. No
new timer/controller, deadline preference, timeout increase, retry, scientific
write/Undo or ordinary Save workflow is introduced. Source proof does not identify
which clock expired in the old owner run or claim a new native pass.


### Explicit ordinary relation-row adapter

Prior art is ADR0024 shared manual relation setters/removal and NativeWidget
Analysis Extra relation navigation/reveal/cues. One finite edit_relation action
reuses those same ordinary methods and matched PVM receipt in both modes, with
ON adding visual-only exact-control cues. Changed-only admission precedes any
page/cue, and deletion uses captured ID plus exact membership/absence checks, not
a post-delete dereference or a replacement row. Existing currentness/manual draft/
OnlyStop/once and ordinary recorded Undo remain authoritative. Returned relation_id
is a confirmed resulting identity only; partial/uncertain effects do not certify it.

Schema/names/classification/dispatch/static and full catalogue/pre-growth roles,
closed relation result field and removal/error maxima advance together. The same
app advertisement and dedicated NAMES list change; their real sourcePatchSha256
package/executable proof must be rebuilt before new dedicated advertisement is
qualified. No old package is relabelled or guard waived. Native app actions are
not copied into the restricted core skill capability registry.


### Three ordinary experiment scalar actions

The existing edit_experiment closed union additionally offers absorption_type,
cutoff_fwhm and dataset_weight, each with purpose, actual experiment ID and scalar
value. These three require the exact currently selected native member/view; the
older profile/exclusion member-selection behavior is unchanged. Absorption choices
are the original mode's offered file tokens, not copied skill options or all lower
registry aliases. Cutoff/weight accept finite numbers under original manual semantics,
with no invented positivity, normalization, automatic cutoff or fit-success promise.

Both modes invoke the FIRST ordinary setter once under the original matched
creation receipt/shared Undo. Show actions adds genuine page/tier/reveal and a
visual-only cue; dataset weight belongs to Analysis Extras Joint fit. No-op values
skip navigation/cue/method/history. Active/retired/consumed input, current-owner,
Stop and factual applied/published/partial outcomes retain their original meaning.

The existing closed Dataset child now reports absorption_type/options and
cutoff_fwhm alongside existing dataset_weight in inspect/context. A scalar result
uses datasets[0].id and its actual confirmed setting (options for absorption), never
a requested-value echo on refusal. Original projection, exact context sizing,
registered schema/argument/dispatch and encoded result maxima advance together.
The source-owned maximum scalar construction role stays in the original native
frame until result transfer; no extra retained execution state is added.

The pinned SDK c6e925c tokens.cpp closed AbsorptionType table has at most three
rows of at most16 bytes (TOF has two). Its original owning-vector scratch is admitted
before calls: initializer-list six strings, copied Spelling-vector six, result capacity
four, up to three same() argument temporaries, plus three vector headers. The
numeric bound contains no duplicated vocabulary; actual choices still come only
from the original SDK. Both catalogue modes' Qt/JSON owners and escaping are
counted separately. This is a logical-payload proof for the pinned source/toolchain,
not allocator RSS or an admission claim for a future SDK. The source guard refuses
an upgraded table outside that footprint; its pinned-source proof must be renewed
when the dependency changes. Original context/stream caps do not grow.

No new native name or dedicated patch bytes are required: edit_experiment already
belongs to the original closed catalogue/oneOf policy. Stock DEFAULT_OFF is not
blocked by an optional package producer. Existing dedicated requested/advertised/
dispatch schema equality and actual package/source-patch proof remain unchanged.
Ordinary Save, reader, Create/atom Undo, explicit relation edits, deadline accounting,
immediate text, profile and exclusions remain outside this focused scalar extension.


### Existing-member UI selection and actual current IDs

`edit_structure` and `edit_experiment` expose a closed `select` branch requiring only purpose, actual structure/experiment ID and operation. The first ordinary PVM current-index setters own the change; there is no assistant scientific action/history or second selection state. The existing original call/frame/visual-cue lifecycle owns the attempted/confirmed boundary: entry precedes synchronous setter callbacks, exact Session/epoch/project/member/currentness and actual selected-pointer readback confirm success. A changed UI selection with lost confirmation reports incomplete/uncertain without scientific applied/may-have-written or a guessed selected ID. Already-current no-ops skip page/cue/setter. Scan-file selection is explicitly unsupported by these new branches; no existing broader action is restricted.

The original fresh app-owned `native_state` projection adds optional `selected_structure_id` / `selected_experiment_id` from actual current native members, alongside their original interface groups. No core selection cache or scientific revision is invented. Closed projection, escaped result maxima and simultaneous canonical/Qt/JSON owners are admitted before growth under the existing roles and limits. The same code-owned schema/help/validation/dispatch is used in both modes; no tool name, dedicated policy patch, permission or package identity is fabricated. Successful selection reports complete/published and one settled step, scientific applied=false; it makes no rendered-frame claim and omits presentation_complete. Ordinary Save, previous scientific edit/Undo and the three experiment scalars keep their original methods and contracts.


### Registered guidance and code-owned capability authority

The original generic thread bootstrap stages the approved packages under its actual workspace and registers them through the runtime's skill workflow. Stock mode does not thereby promise every SKILL body is already in the prompt. Read the relevant actual registered path through an actually offered read-only mechanism when its body was not supplied; use a minimal relative path with balanced syntax and the existing purpose convention, preserving read bounds and completeness. This is not a new read_skill operation, arbitrary filesystem/scientific-input grant or permission to execute resource scripts. The original nonempty-policyPatch path still supplies bounded captured bodies and keeps its exact use-already-supplied/do-not-reread prefix. No all-body injection is added to stock mode.

The actually offered code-owned schemas/options/results are the capability authority; strategy text and the separate restricted compatibility index are not another generic native catalogue. The incomplete introductory mini-inventory is removed without adding a replacement list or changing registry, dispatch, compatibility validation, permissions or package proof. GSAS intake alone cannot certify creation/save/refinement/conversion/equivalence, while later observed ordinary app actions may be reported truthfully. Its binary GPX and genuine scientific prerequisites remain. The matched gsas-intake version/body/index digest advances together; other skill bodies and compatibility capabilities remain exact.


### Compound relation controls share the ordinary model path

The FIRST manual AliasListModel/ConstraintListModel methods and existing standalone edit_relation cue/apply path also own every compound add_relations scientific stage. Append, ID, offered target, expression and explicit enabled flag now reveal/cue the original full control and call that same ordinary model method once. FileLoadCue supplies all required callbacks but performs no scientific prepare/finish/device input; the completed callback prearms the exact existing WidgetRelationInput immediately before the ordinary method. The shared apply body continues compound widget_relation_done instead of finishing the RPC after one stage.

Original exact member/offered target, prepared consumed/applied/published receipt, canonical readback, ordinary per-change Undo and actual applied-prefix retention remain. Stored equal fields skip cue/setter/history; explicit false is never replaced by a presentation toggle. Local cleanup captures only its exact input, weak PVM and own-edit scope; old callbacks cannot clear a successor's input/scope or apply a later row/field. Original normal add_relations stays one atomic native batch, unrelated helper choice/form input stays intact, and no new relation executor, scientific setter or allowance exists. This is source consistency with the requested ordinary API design, not proof of the earlier unconfirmed alias failure's actor.

Strategy distinguishes append-only preservation from authorized existing-row changes: inspect exact actual IDs, preserve unrelated/user declarations and composition constraints, reuse/modify only an identified intended row through offered edit_relation, append only missing intended declarations, skip equal values and follow actual returned IDs. Default-looking alias names or a matching target confer no ownership, and invalid dependencies remain a real refusal rather than permission to rewrite them. Project-assistance body/version/index digest advance together; separate stock/GSAS guidance remains exact.


### Exact current phase-link controls

Existing edit_experiment adds only phase_append, phase_retarget, phase_enabled
and phase_remove, through the FIRST ordinary LinkedStructureListModel methods
and shared app history above. Both modes require the exact current experiment;
select is the separate existing UI operation. ON reveals/cues the genuine linked
structure control and then calls the same method as OFF, with no scientific
keyboard/choice/toggle dispatch. Disabled retarget and final stored-row removal
refuse before no-op/history. Explicit equal admitted retarget/enabled skips the
cue, setter and Undo. Append uses the original first unlinked project structure,
never a guessed name, and captures the actual early append identity.

The exact phase key is the existing dataset phases[].structure_id. A confirmed
result adds bounded phase_id and complete ordered datasets[0].phases; removal
returns the admitted old key, without reading an erased row. New IDs must be
used for later calls. Existing scale parameter actions and read-only derived
weight fractions remain separate. Actual consumed/applied/published, once,
owner/Stop/manual draft and truthful partial/uncertainty rules remain mandatory.
Pre-effect phase-bank sizing includes the actual append candidate or a
conservative escaped replacement row, false bool, bounded top identity and
still-live native/UTF-16/JSON/result owners; no limit or allowance increases.
No new tool name, optional package identity, parser, selection fallback or
implicit phase association is introduced. Code-owned schema/help describes
these finite operations; skills do not duplicate the catalogue.


### Connection wording follows the original managed-account flow

The FIRST official-agent connection path already checks the managed ChatGPT
account before requesting browser sign-in. A deadline, transport or context
failure can retire local execution readiness without logging out that account.
The disconnected panel and initial connection dialog therefore use the existing
neutral “Connect ChatGPT” wording and explain reuse of an available sign-in;
OpenAI's browser sign-in is conditional on the original account/login branch.
Cancel still sends no pending message, and the current outgoing-context review,
owner-bound failure notice, actual browser instructions and explicit Sign out
remain authoritative. This is presentation only: no authenticated flag, account
approval, process, deadline, retry or message-delivery behavior changes, and it
does not establish the cause of an observed disconnection.


### Bound existing parameter lookup work without changing admission

The FIRST visible parameter lookup uses its same free/numeric object-name
eligibility before geometry for controls it would discard. When lookup debug
logging is enabled and uncapped, the original unusable-control coverage and
record order remain; after the existing per-lookup budget and omission marker,
diagnostic-only property, conversion and ancestry reads stop. Candidate order,
canonical member binding, Main/tier, whole-row reveal, current owner, Stop,
ordinary setters, receipts, Undo and truthful refusals remain authoritative.
No target cache, traversal/dedup change, timer/settings/pacing adjustment or
scientific check is introduced or removed. This removes provably discarded
work; it does not establish a measured CPU improvement or the cause of a
reported Mac lag, chart warning or disconnection.


### Recoverable pre-write purpose-length refusal

The FIRST assistant_native_purpose validator still requires a nonblank string
of at most120 UTF-16 units and480 UTF-8 bytes, with its original control-character
refusal. Only its nonblank overlength branch now uses the existing typed
ActionRefusal pair purpose_too_long/purpose. The original shared pre-admission
catch exposes that exact pair for every registered native tool through the
existing closed action_error/action_field result projection; no raw purpose or
exception message is disclosed. Type, blank, control, schema and scientific
validation remain unchanged, and no app edit or native work has started there.

On this explicit refusal the caller can shorten only purpose to the declared
limit and issue a fresh call with the same scientific operands. Edi does not
normalize, execute or replay it automatically. Existing current-owner and once
checks still precede or govern the call; other refusals are not diagnosed by
this pair. Both tokens fit the original longest closed-token bounds and direct
reply admission measures the actual projection, so no response limit, field
family or allowance grows. This explains only actually overlong requests, not
shorter control, relation, deadline, rendering or connection failures.


### One working-logo diameter for both original Stop paints

The FIRST AssistantWorking physical icon diameter is shared through AppSizes;
its formula and rotation/visibility behavior are unchanged. StatusBar already
uses that iconExtent for its centered content-background circle, appBarBorder
and half-diameter stop glyph. AssistantComposer now paints the same circle and
proportional glyph, with its original message/content background and border,
inside the unchanged actionSize hit/layout slot. The circle is centered rather
than stretching to that larger tool-button slot.

Only paint changes: actual cancellation receivers, visibility/pressed retention,
steer/draft/send behavior, keyboard/accessibility and all layout reservations
remain. Existing enabled hover/down/focus foreground accent is retained; the
neutral Stop ink follows its original themed foreground on the content fill.
Send/avatar blue-background hover is unrelated and stays exact. No speed
control, component, backend or lifecycle behavior is introduced.


### Scalar string roles in ordinary relation preparation

The FIRST skill_json_text_units helper measures one borrowed JSON string before
admitting a decoded string owner. It remains strict for nonstrings, and deleted
object/array overloads prevent an aggregate from implicitly entering that scalar
contract. Relation preparation measures its already validated purpose, ID and
operation strings, plus value only when it is a string. Enabled's boolean and
remove's absent value require no decoded value-string role.

The original encoded argument-object charge, decoded-string temporary factor,
fixed frame/input roles and all retained-byte ceilings remain. This measurement
precedes allocation, exact member lookup, canonical no-op comparison and both
visible and normal execution. It does not change validation, ordinary relation
setters, receipt/Undo ownership or refusal semantics; it removes an unconditional
type refusal before those original paths can run.


### Setup planning and proved-refusal recovery

The common native bootstrap, original code-owned tool help and bundled project/
refinement strategy distinguish successful returned identities from intended
renames: refused prerequisites do not establish new IDs, and partial/uncertain
effects require actual inspection rather than sequence replay. The existing
purpose_too_long/purpose prewrite refusal permits a fresh shorter-purpose call
with unchanged science/current authority. A known prewrite target_unavailable/
experiment refusal with explicit no applied/published effects permits inspection
and a fresh actual-ID correction within that same objective; generic or uncertain
refusals do not. No automatic retry or resolver is added.

Delegated setup in both modes completes Structure and Experiment before grouped
Analysis flags/fits. Chosen and imported background anchors are initially planned
fixed while retaining exact source values/IDs/counts and desired final flags for
that later stage. Explicit incoming operations and immediate user scope remain
unchanged; the app does not defer their flags. Known-wavelength sample refinement
and genuinely anchored wavelength calibration remain distinct objectives; actual
setup/free sets and earlier failed prerequisites are checked before fitting.
FullProf only cross-refers to that generic strategy, preserving scientific source
mappings. Schemas/options, ordinary setters/Undo and identifiability guards stay
authoritative. No local exception text, new fit-reason code or scientific control
change is part of this guidance.


### Closed actual-origin fit reason

The first native fit completion may add only
`fit_reason: "unanchored_cw_dilation"` from its original typed FitReport ERROR
with no optimizer result/adoption/convergence. Unknown causes remain omitted.
The existing closed Result walk requires the exact token and explicit
error/adopted=false/converged=false facts before projection; status-derived code
precedence is unchanged. No arbitrary refusal message, model name, path or
exception text becomes model-facing. The existing run_fit description owns the
conditional sample/calibration/joint anchor help; skills do not duplicate an
error catalogue and no flags or retries change automatically.

The original pre-work numeric envelope includes this field's fixed JSON cost
and key/value owners from the existing Qt encoding measurement. Outcome,
response/nested text, row and history ceilings retain their existing limits and
simultaneous ownership. The original projection reservation also admits the
positive difference between the fixed key/value owners and twice their JSON
spelling before growth. No maximum-only string/object is allocated for the new
field. The actual completion/encoder and original currentness/once/Stop fences
remain authoritative. If fallible construction cannot retain the typed
outcome, the existing honest uncertain fallback may omit the reason; a retained
typed outcome is not erased after later presentation/storage failure. No extra
reply or fabricated success is introduced. SDK/public-source/package proofs
must advance genuinely; no future package identity is implied by this source.


### General source occupancy normalization and construction completion

The FIRST bundled fullprof-intake mapping remains conditional on the actual
nuclear source convention and site/general multiplicities. Recover the raw
fraction from general-position-normalized occupancy, then remove only an
established common positive phase factor from every site/species. Preserve
partial/shared-site fractions and verify multiplicity-weighted composition and
actual native readback. The corresponding already-mapped phase scale receives
the factor squared exactly once; other engine scale conventions remain separate.
This follows the FullProf July2001 manual physical pages41/102 and the original
crysta structure-factor/phase-intensity and cell-mass occupancy contracts, without
a space-group example, per-site clamping or an assumed normalization factor.

Project guidance owns actual returned-ID recovery and required-setting readback;
data loading can rename an untouched experiment. Supplied source flags/relations
describe the requested construction, not an implicit fit command. A failed
required profile edit prevents a completion claim, while a missing format parser
does not block existing offered app construction methods. Only skill prose and
matching version/digests change; no schema, mutation, validation, resource,
currentness, Undo, retry, SDK or runtime behavior is changed by this guidance.


### Page-first delegated setup and prewrite occupancy mapping

The FIRST current Structure cell/site/ADP bindings use the project registry and
current Structure models without an Experiment prerequisite. Ordinary page
following reflects the incoming action; it does not enforce a future plan.
Developer instructions now begin with the delegated procedure: complete cell,
each full Atom sites row before appending the next, then all Atomic displacement
rows across ALL requested Structure members before any Experiment, then all
requested Experiment members/groups in the fresh actual interface order before Analysis
flags and authorized fit stages. A profile is chosen in its own group before its
coefficients; only a genuine explained scientific dependency moves a prerequisite.
Background values enter fixed during planning, retaining source flags for later
Analysis. Explicit user scope, incoming arrays/operands and atomic edits remain
authoritative; no dispatcher reordering or scientific override is introduced.

The existing general FullProf occupancy/multiplicity and common-phase-factor
mapping is moved before occupancy writes, with partial/shared fractions, mapped
scale compensation and native readback retained. No space-group example, guessed
factor or engine conversion is added. Tool descriptions and bundled strategies
express the same order; schemas/options, validation, setters, authority, Undo and
resource/currentness limits are unchanged. This improves instruction salience,
not a claim of model compliance or a diagnosed provider/runtime cause.


### Disconnected assistant presentation

The FIRST Structure empty-state label and existing EmptyStateLabel own the
font, disabled colour, wrapping and sidebar-width margins for No ChatGPT
connection. The disconnected header Connect ChatGPT and pending Cancel
connection reuse the Composer Send button's borderless theme-contrast fill,
accent hover/pressed/focus and disabled colours. The empty-state prompt remains
centered. The retained notice and Cancel control share a bounded top viewport
with the existing unit gap; both remain scrollable above the prompt when space
is limited. Connected avatar paint, non-connecting Stop behavior,
notice ownership, connection offers and cancellation callbacks are unchanged.
This is presentation only; it changes no authentication or operation lifetime.


### Analysis group, fit and assessment loop

The FIRST native FitReport exposes actual status/adoption/convergence, while
ordinary FitViewModel/ProjectViewModel history restores a recorded fit separately
from an unadopted refusal. Delegated refinement instructions therefore finish all
Structure then all Experiment setup before Analysis, and release one justified
group, fit and inspect the actual outcome before selecting the next group. Keep
good stages; restore an adopted undesired fit only through an actually offered
ordinary operation still targeting it, then inspect state/free flags. Never undo
earlier science for a no-adoption refusal or replay an uncertain operation.

The present native catalogue does not expose Undo. Guidance cannot create that
capability: absent suitable restore, report the recovery limit without claiming
rollback or continuing from a rejected state. Existing manual Undo remains the
original app operation. No new optimizer, checkpoint controller, schema, physics,
flag override or runtime stage guard is added. Fill-only scope, explicit caller
arrays/constraints, anchors, currentness and ordinary history stay authoritative;
instruction repair is not guaranteed model compliance or fit quality.


### Header connection entry, pending cancellation and avatar

The FIRST AssistantPanel connection button owns the connection entry, with the
original guarded AssistantConnectionDialog offer and the connected account
avatar. Its painted text pill now shares the avatar's actual 0.75 tool-button
height, centered inside the unchanged full-height hit/focus area; text width may
use the available header space. Existing Send-style borderless theme/hover
colors remain unchanged.

The SAME header receiver shows Connect ChatGPT, then Cancel connection while
connecting, then the connected avatar. Actual connecting takes precedence even
when the account is already authenticated (for example, a pending settings
update); one derived pending/account-view binding owns every header presentation
and routing choice. Pending cancellation is enabled only by
the original canCancel and calls that same original assistant.cancel once;
it cannot start another offer or open the account dialog. Hide only the duplicate
connecting Cancel in the disconnected body. The original nonconnecting Stop,
notice owner/overflow, unit spacing and centered No ChatGPT connection empty
state remain. The body viewport uses authoritative current state/canCancel,
never a descendant's effective visibility. This is presentation/receiver routing,
not an authentication, connection-deadline or scientific behavior change.


### Sent attachment bubble natural width

The FIRST AssistantMessage user bubble keeps its original available message
width, right alignment, copy-button gutter, padding and Flow. Its natural
content width is the larger of the message text and the widest actual formatted
sent-file label. One shared formatter includes the byte count and text-export
suffix; the existing FontMetrics measures the same font explicitly used by
those labels. No elided/laid-out child width feeds the parent. Middle elision
remains only when the original available-width cap requires it. The original
bounded inputFiles validation, IDs, accessibility/copy/archive behavior and
nonuser/zero-file widths are unchanged. No parser, source copy or cache is added.


### Visible text-field cue geometry

The FIRST ParameterField/ParamTextField title is outside its editable TextField
background, in topInset. AssistantWidgetInput therefore centers that control's
cue on the actual inset rectangle, using the original Qt TextField scalar
geometry, not the title-inclusive item center or a font-derived offset. The
pinned Qt implementation uses those insets for its automatic background bounds;
its final scalar getters do not instantiate a deferred background item.

Untitled zero-inset fields retain their center; plain TextInput cells, buttons,
menus and scroll gutters retain their original geometry. Each original target
revalidation maps current local geometry through the same item transform and
checks the same window/ancestor visibility and clipping. Invalid or empty inset
geometry refuses. Target/receiver identity, full-row reveal, draft/currentness,
ordinary setter/receipt/Undo and Stop behavior are unchanged; no shadow target or
scientific input protocol is added.


### One final-target setup order for CIF and mapped Structure input

The FIRST create_cwl_project/NativeCwlCandidate and NativeCreateWidget path owns
both original CIF input and the closed scientifically mapped Structure target.
Native Structure/Cell/AtomSite/tensor constructors and original specs, setting,
ADP and relation completion prepare the mapped input; no default factory,
requested CIF, source parser or second executor is copied. Original recipe,
source and initial_parameters validation order and final override values stand.
Only after the FINAL candidate is valid does the same CategoryListModel
presentation order produce the ordinary control plan for either input.

The planner resolves actual UI owners: cell, each complete Atom sites row, then
ALL Atomic displacement rows, before Experiment creation and its actual groups.
An isotropic ADP belongs to the original ADP group despite its core atom_site
parameter category. Background values come from the final candidate and the
original position-derived IDs action follows all naming inputs. Independent
one-off arrays retain caller order. Equal canonical values skip scientific
setters/cues/Undo. Mapped ON invokes ordinary Create, reuses its actual one seed
and appends only later rows; FIRST Edit::add_structure now additionally returns
that actual one-atom identity before callbacks, with all prior receipt fields
and scientific operation unchanged. Ordinary row methods/receipts, partial
prefix/currentness/Stop/manual draft and original Undo remain the write owners.
OFF retains the original completely prepared population and one atomic Undo.

The original creation worker's scientific Project/PlainData/candidate graph is
an ordinary core working graph, as in the existing native readers/population;
the stream-retention cap is not a global scientific-engine heap/RSS policy.
The candidate is discarded before ordinary visible writes, never retained as a
second live scientific snapshot. New assistant-owned request decoding, selected
captures, metadata/worklist, Qt JSON, callbacks and result/history roles are
pre-admitted under existing caps and retained through their actual owners. No
new allocator/parser, arbitrary multiplier, cap increase or silent spare-role
donation defines scientific memory. This explicit distinction replaces any
claim that the transport cap measures arbitrary native engine allocations.

The boundary remains one Structure, one powder/CW/neutron/Bragg Experiment,
no project or the same scientifically empty owner. Source interpretation and
occupancy/scale mapping precede the target; validation never forces a dependent
field. Required source aliases/constraints/refinement flags are subsequent
explicit ordinary actions AFTER setup. Setup alone implies neither complete
source reconstruction, Analysis release, optimizer execution nor saving.
Stock default-off dedicated policy remains supported; any opted-in runtime
catalogue/schema proof must match actual offered bytes, never a fabricated
package/hash or historical qualification. Source review and a genuine fresh
producer/class gate are distinct from this implementation.


The prepared visible setup handoff also retains the FIRST original visible
originPaths / standalone pathRole admission. Before new SelectedFile holders
or original source validation/URL/hash work, it reserves their additional
headers beside the still-owned old selected vector slots, original path and
encoding overlap, hash/read scratch and actual snapshot-reader URL preparation.
The guard is declared before the local frame, so failure destroys that untracked
frame before releasing the reservation. On successful tracking, existing
native_bytes owns the actual frame/worker/source/path roles before the same
reservation transfers. CIF and mapped measurement-only handoffs share this
boundary; no metadata/plan slack, skipped rehash or new scientific snapshot
funds it. Original caps and source/currentness/refusal/Stop behavior stand.


### Genuine instruction continuity follows fresh-thread identity, not words

The FIRST generic_send/generic_acknowledge continuity path owns the genuine UI
instruction origin and completed public user rows. Its former continuation-word
tests missed ordinary attachment follow-ups and could exclude an actual user's
earlier instruction by spelling. A fresh same-project/generation/account backend
thread now receives those bounded, ordered completed rows as explicitly
context-only text using the exact original earlier-user prefix. The current real
instruction follows prior instructions and takes precedence; the original
approvedContext DATA item stays last. The existing live thread already has its
inputs, so it is not reseeded each turn.

Only an actual successful correlated input ACK, its original pending receipt,
current scope and exact genuine public user row establish the thread-input
marker and first objective anchor. Failed preflight, refused/retired/older ACK,
Clear, replacement and account retirement cannot advance them. Original thread
retirement/new-thread assignment resets the marker. The original exact committed
empty-owner project handoff retains its existing anchor transfer.

The complete input's encoded size, Qt JSON text/container owners and one largest
prior decode/concatenation scratch are admitted before history text grows under
the same original joint caps. The existing borrowed string-size walk accepts an
explicit cap here while all skill callers keep their prior default. No old
file/source bytes, grants, input-path capture or provider userMessage/assistant
text are promoted: capture_input_scopes still reads only the current real draft.
No phrase classifier, summary, obsolete backend reuse, retry or transport engine
is introduced. Clear and scope boundaries remain the original owners.


## Current-project fit-only ordinary Undo

The FIRST history/scientific contract is ADR0024's ordinary appbar Undo; the FIRST visible delivery convention is FileLoadCue followed by the same ordinary app method, as used for native imports and shared relation setters. `undo_fit` is the single purpose-only addition to the app catalogue (22 names including this action). It is a current-project mutation, not a generic history API, fit, reset, save or automatic recovery. The model must first inspect an adopted undesired fit within the authorized refinement scope. A later refused/unadopted fit must never trigger reversal of earlier accepted science.

`native_state.fit_undo_available` is a fresh semantic observation, never authorization or a GUI geometry promise. Use rechecks the exact original owner/account/generation/receipt, settled original readiness, latest actual adopted single/joint attempt and explicit top-fit history. ON additionally resolves the original enabled usable `appBar.button.undo`, cues it without device mutation, then calls PVM.undo once. OFF calls the identical ordinary method and semantic predicate without a window/geometry requirement. There is no sidebar navigation, disabled-control bypass, second reverse engine or new permission. Draft/manual takeover/OnlyStop/Stop/currentness remain original.

The preowned fit-only input retains consumed/started and actual EditOutcome scalars through ordinary PVM.undo/FitVM.undo/applyUndo/applyEdit. Native retirement and original fallback see applied before synchronous observers. Confirmed original-owner reversal reports edited/applied/published/complete and one step; actual application without confirmed publication/currentness reports applied_unconfirmed/uncertain and one spent step. Prewrite refusal reports false effects and zero steps. Unknown fallback remains unknown, not fabricated no-write. Existing Role::Result fields, safe closed codes and schema are reused; no raw exception/path/history/model dump or consumed wire field is introduced.

Existing role/cap policy remains unchanged. Additive fixed attempt/receipt/frame sizes are measured by actual types; native_state owns its bool/key before growth. Actual fixed result literal/key/value ownership extends every original outcome/response/nested-row maximum before mutation. Existing frame tracking retains live/retired callback and input ownership. No copied scientific snapshot, new global model-memory rule, metadata slack donation or raised cap is introduced. Optional dedicated NAMES and requested/advertised/full-schema/dispatch equality include the real new name. CMake and the original runtime producer derive sourcePatchSha256 from the genuinely amended patch; no archive/pin/package identity is invented. Stock default-OFF remains unchanged; opted-in package production/qualification is separate.


### Fit Undo facts belong to original settlement, before generic outcome selection

The FIRST `NativeRecord` already owns the owed response independently of a disposable widget. Its fixed fit-only payload now owns the exact ordinary input and two preprepared published-bit outcome/response/row variants. The payload is admitted before growth, remains measured through the original record (including a retired frame's record reference), and survives widget/prearm cleanup. No PVM scientific Undo, history, attempt eligibility, request schema, cap or clock changes.

One callback-free reconciliation requires exact original call record/receipt/RPC plus receiver/State and original project provenance, and selects uncertainty only from the actual applied receipt. It runs at original settlement entry before a generic result can be selected/stored/answered/reset, before the generic native catch chooses may-have-written status, and at cleanup. Immutable prepared banks use pinned Qt noexcept const-copy assignment, so repeat entrances/publication-bit updates do not consume the only fallback. Every retained alias remains counted under the original record destination and bank roles; no owner/account authority is renewed.

A known applied reversal always keeps false-success/applied-unconfirmed, actual publication bit, uncertain=true, complete=false and one spent step when only generic refusal/exception/retirement can be confirmed. A consistent stronger actual ordinary completion may still replace that fallback. Already answered/completed or successor calls cannot borrow the receipt. The emergency fallback does not invent a current calculation_pending observation; ordinary confirmed completion still supplies it. Unknown effects stay unknown. Direct cancel, context/account/project retirement, OFF late receiver/result-construction exceptions and ON fit-specific fallback all converge on the SAME original native_finish/record path; no alternate publisher, Undo replay, history walk, timer or framework is added.


## Terminal-only escaped server-request first cause

FIRST is the original native_failure_class active-catch classifier and C stdio failure boundary. The official serverRequest callback's existing escaped-handler notice identifies that catch only; it is not evidence of retention exhaustion, authentication failure or any particular tool. Its original input-current guard, visible notice, generic_fail retirement, strict rejection/answer and scientific outcome behavior stay unchanged.

Each synchronous invocation owns a fixed stack ServerRequestFailure with closed method category, active stage and first caught stage/class pointers. The handler receives only a synchronous reference; nested requests get separate records and no global/retained failure from an older request is borrowed. Method is TOOL_CALL, COMMAND_APPROVAL, FILE_APPROVAL, USER_INPUT or OTHER. Every stage is an app-owned literal; classes reuse the FIRST allocation/capacity/validation/state/exception/nonstandard map, never what() or a provider label.

At the first native std::exception catch the original dispatch stage/class is captured before scope checking, JSON, cancellation or refusal settlement. The existing Save suffix reads the frozen original dispatch stage, so later diagnostic-only stages cannot change it. If settlement throws to the outer catch, stderr names that secondary stage/class separately; otherwise an unhandled branch uses its active outer catch as the first cause and secondary NONE. After the same original input-current guard, one fixed C stdio line precedes the unchanged generic_fail. No raw method/params/IDs/path/URL/source/question/provider/credential/model/exception text enters it. Output failure is not authority or recovery. No Qt logger, new wire/context/tool, tracker, heap buffer/retained closure, clock/cap adjustment, retry or reauthentication is introduced. These facts can identify only a future source-bound occurrence; the owner's existing cause remains unknown.

## Compound background discovery and literature-based strategy selection

FIRST is native_cwl_recipe_schema/parse_native_cwl_recipe and the separate edit_background ordinary editor. Compound recipe.background remains a direct array of exact position/intensity numbers, with fixed intensities supplied by setup. Code-owned array/item help, tool/bootstrap and the two strategy skills distinguish it from standalone add/update's explicit free flag and from inspection's background.anchors output. Exclusion and initial-parameter row shapes stay exact; no parser/schema-validation/wire/cap change, silent stripping, flag override or extra stage is introduced. Desired final source flags are retained for authorized grouped Analysis after setup. Explicit immediate scope and uncertain/partial recovery remain authoritative.

The prior adaptive strategy skill names groups but does not make early alignment salient enough. Its concise operational route now distinguishes GUI fill order from scientific staging, cumulative release from conditional block cycling, and legitimate existing calibration from a need to adjust geometry. Scaled peak-position agreement precedes detailed profile/structural refinement when it is not already established; known wavelength/zero, chemistry and dependence are not silently freed. Current capabilities remain the execution boundary: no Le Bail/Pawley, weighted geometric-restraint, rigid-body, solver-switch or checkpoint-bank operation is invented.

Scientific prior art is Young (ed.), The Rietveld Method (OUP/IUCr 1993), chapter 1 §§1.7.1–1.7.7 (printed pp.32–36), Baerlocher chapter 10 §10.2, Von Dreele chapter 12 and Toraya chapter 14, https://doi.org/10.1093/oso/9780198555773.001.0001; and McCusker et al. (1999), Rietveld refinement guidelines, §§5 and 7, https://doi.org/10.1107/S0021889898009856. Physics owns the detailed source/page extraction and labelled selection synthesis in its Refinement strategy selection companion to chapter 8. The CW table is illustrative; neither it nor an X-ray scattering heuristic is a universal neutron/TOF release list. No scientific engine, controller, authority, Undo, OnlyStop, deadline or runtime behavior changes, and guidance does not prove model compliance.

## Complete-target exclusion fields follow the original row order

FIRST is ExcludedRegionsGroup's Start then End columns and the ordinary ExcludedRegionListModel.setStart/setEnd methods through PVM.apply_creation_control and Edit::excluded_region_bound. Those setters do not require changing End before Start when an appended row begins at its ordinary default. The shared complete-target CIF/mapped visible planner now always emits append, Start, End for each original row, rather than conditionally reversing fields from their values. Already-equal fields still skip their setter/cue/Undo through the existing canonical check.

The final recipe remains finite and ordered before execution. No endpoint is sorted, clamped or rewritten; ordinary append defaults/IDs, literal field values, validation, setter receipts/history, partial/Stop/currentness and Undo remain authoritative. A stopped sequence reports the actual requested Start-before-End prefix; this is not a combined or atomic GUI setter. Normal candidate population and standalone explicit caller order are unchanged. The original pattern evaluator already normalizes bound orientation while evaluating inclusion; no crossing guard, engine change or new executor is introduced.


## Closed mapped-target and conditional refinement guidance

Prior implementations: native_mapped_structure_schema and mapped_structure
validate one closed typed target; native tool descriptions and the shared
developer instructions route ordinary setup/refinement actions. Add exact
field-spelling help beside the existing schema without accepting aliases or
changing validation. Parent-level refusal remains truthful and never proves
setup completion. Constraint append retains its disabled editable draft and
ordinary explicit validated activation. Background naming receipts are unchanged.

Refinement instructions distinguish GUI setup order from conditional scientific
alignment. McCusker et al. (1999), section 5, requires peak-position agreement
before detailed profile/structure fitting and warns that cell and two-theta
corrections correlate (https://journals.iucr.org/j/issues/1999/01/00/gl0561/).
The possibility of an intensity-scale collapse under displaced peaks is a
least-squares inference, not a diagnosis of a particular run. Use actual
inspection and eligible ordinary Undo; keep known wavelength/calibration and
chemical constraints. No new solver, flag override or automatic retry is added.


## Settled output transfers to its original bounded owner

Prior implementations: generic_present/publish owns durable activity rows;
generic_items owns stream assembly and finalization evidence; native_finish
owns exact original/outcome/response/canonical receipt facts. After an activity
is truly finalized and its exact payload is in the bounded archive, its
redundant generic registry value can release to that existing owner. Finalized
native items use their completed canonical record, only without outstanding
shared/native callback ownership. Keep registry keys/counts/finalized markers;
all duplicate checks resolve the exact original object, not a hash or summary.
Private reasoning/user/assistant-text items and all unfinished work retain
their original full charges. No completion, reply or receipt is inferred.

A completed, answered, durably retained native terminal row can similarly
release its redundant row payload only with no shared record owner and an
actual matching archived host outcome. Original arguments, outcome, response,
canonical identity and once flags remain. Release occurs after generic item
frames unwind, before lowering the original callback-free transport charge;
current parsed/unread/write roles remain charged. Prepared fit-Undo alternative
settlement banks release only after completed/answered/durable settlement and
exclusive record/bank/input ownership; the actual typed outcome/response and
ordinary scientific history remain. Eligibility requires actual item completion;
cleanup runs after completion/returned requests or original coalesced archive
presentation, never as a streamed-text polling loop. No cap or allocator policy
changes. Missing originals and changed final items still refuse.

CodexAgent latches a closed local failure kind before its original failed
signal. Known capacity and operation-expiry branches distinguish those local
causes from an unclassified failure; explanation text is never parsed as
authority. Failure feedback preserves the original explanation and describes
retained task/project state without claiming provider-token expiry. Original
authentication/retirement/required-reply/currentness behavior is unchanged.
The actual account/read adapter exposes no proven stable account identity;
therefore cross-epoch automatic task replay remains guarded, with no email or
plan comparison, epoch reset, file-grant replay or unsupported thread resume.


## Invocation-local official event failure diagnostic

FIRST is ServerRequestFailure, native_failure_class and the non-Qt terminal
failure convention at the original official server-request receiver. Official
events now own the same fixed method-family/current-stage/first-catch-class facts
on one synchronous stack, shared by generic_event and both generic_item callers.
Nested events have independent stack records; no State-global first cause is
borrowed and no event payload or exception text is retained.

Both original catch owners emit at their unchanged publication guards: outer
input_current and account/updated inner publication_current after retirement.
First stage/class is latched before item restoration or account fallback.
Successful restoration resets the current stage before rethrowing the original
exception, so propagation is not mislabeled as a second failure. A new exception
during restoration keeps its distinct cleanup stage as secondary. Successful
terminal-item return explicitly restores its caller's next phase.

The fixed terminal line contains only closed method-family/stage/class labels.
It uses the original C stdio convention, without callback-capable Qt logging,
raw method/what()/IDs/paths/account/provider/scientific data, heap trace storage
or a new wire field. No new notice suffix is required; the original visible
sentence and all original fail/return/currentness/receipt/limits remain.
CAPACITY is an exception class, not proof of a particular exhausted byte budget.
This observes a future occurrence; it does not diagnose or fix a reported run,
retry an action, change a cap or recover an account/thread. Existing657 open
reasoning-retention and cross-epoch continuity limits remain explicit.
