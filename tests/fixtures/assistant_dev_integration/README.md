# Assistant integration source baseline

`baseline.json` freezes selected existing dev identities at
`e782d2d84a984c8d9df86e6e6c4df361baf89f2c` before the selective assistant port.
Each file digest is SHA-256 of `git show <source_commit>:<path>`, collected by the
independent tests lane on 2026-10-27. GUI and SDK values are the existing declared
pins in `cmake/EdiGuiBase.cmake` and `pixi.toml` at that same revision.

The owning dev estimator algorithm is reused, and the existing exact-fraction,
colour and scan-view ADR identities remain intact. Assistant ADRs receive new
identities. These are source-preservation gates, not numerical correctness or
native integration evidence. Other integration surfaces intentionally remain
adaptable and are checked through existing ordinary app behavior tests and new
native OFF/ON witnesses.

The resource gate checks the published skill index against actual shipped bytes.
Its expected-red baseline is the absent assistant skill bundle on unported dev;
the preservation cases are positive controls. It does not infer tool execution,
model intelligence, research entitlement or scientific success from prose.

The stamp codec freezes the prior dev geometry/calculation byte traversal and
peak field order. Its relation fixture binds declared `.edi` cell names directly
to native cell fields, with no call to the current naming producer. This finite
alias reference rejects unsupported non-cell targets rather than silently
omitting them; it does not claim a complete independent name catalogue. Current
native model field types and the opaque editor-record API remain shared inputs.

The pre-growth witness uses the unit carrier's existing ordinary new/new[]
instrumentation to observe input-sized row containers, source strings and alias
naming scratch, with an actual allocating positive control for each. It does not
define a process-wide allocator/RSS guarantee or require allocation-free refusal
diagnostics. Every observed fixture is prepared before instrumentation is armed.

The finite cell-name reference also preserves the original eligibility filter
from `e782d2d8:core/src/io.cpp:4363-4370`: dependent parameters are omitted by
`named_parameters`. Known cell-target validation and eligible source membership
are separate. The cubic silicon fixture intentionally contains an independent
length-a source and a dependent length-b target; the latter has no independent
source-value payload in the old relation encoding. Original raw failures are
retained; this restores a missing reference rule rather than rebasing to a new
producer's output.
