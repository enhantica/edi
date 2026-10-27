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
