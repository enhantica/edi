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
scan execution explicitly refuses until that unit exists. A project without a recorded baseline objective cannot
automatically adopt an improvement yet.

The Responses stream parser emits only complete public text, tool and terminal items. Account/project authority
is supplied by the native connection, not by provider text. Every JSON boundary rejects duplicate fields,
nonfinite numbers, invalid UTF-8, unsupported schemas and oversized messages. The shared report JSON reader is
reused; assistant-specific admission rules are applied at the assistant boundary.

The controller has no Qt, timers, network or credential storage. The host supplies an owner-thread event sink,
provider transport, typed edit door and optional monotonic clock. Worker deliveries remain ordered through the
existing `work::Post`. Independent tests link the real `edi::core` target; no production test command is added.
