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
