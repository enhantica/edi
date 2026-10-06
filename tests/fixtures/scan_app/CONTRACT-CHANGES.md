# E04-T16 gate adaptations, conductor seq 8

Authority: relay's committed decision record, 2026-10-06, **scan buttons follow the fit state**
(the reset, status-bar, Evolution chart and list decision); review-5 reply, F2/F3/F4/F9.
The decision supersedes the earlier packet's conflicting restart rule.

| Assertion / observation | Before | After |
| --- | --- | --- |
| Completed worker scenario | Start discarded a completed run and captured its CSV for Undo. | All fitted datasets disable Start. Reset fits removes CSV, provenance and run summary; one Undo restores every byte and the completed state. |
| First partial run Undo | Restored the earlier completed CSV implicitly discarded by Start. | After an explicit Reset, one partial-run Undo restores absence of every result file. The earlier completed result still has its own Reset Undo proof. |
| Template edit after completion | Invalidated Continue and made Start refit all files. | Retains visible stale results and provenance; completed Start stays disabled. Reset enables Start; its Undo restores the stale files and marker; the following explicit Reset/Start refits all datasets. |
| Incomplete scan / holes | Continue consumed only the prefix stop at file 40. | That exact optimizer-prefix proof remains after a template edit too; a second real-worker scenario starts at the first unfitted dataset and skips later fitted datasets. |
| Fit button consumer | Source labels followed running/continuable. | Execute labels and availability for null, empty, partial, complete and running state. Reset dispatches its own model and sits between Fit and Follow. |
| Status progress consumer | Required live producer, fill, polarity and fact order. | Keep those checks; require the progress bar as the final child of the right-anchored status row. |
| Evolution shown-dataset marker | Point selection selected the shared dataset. | Keep selection; execute marker position/visibility across empty/rebuilt points and pending projection while selection stays fixed, then verify movement on selection. This is a consumer-state claim, not a visual frame-rate claim. |
| Evolution zoom consumer | No gesture contract. | Execute box drag, pointer-centred wheel/touchpad notch and right-click reset; verify the actual four axis bindings follow two gesture ranges and release them on reset. Numeric wheel expectation is the pattern chart's existing 0.8-per-120-unit convention. |
| Selector previous/next | One click forwarded the bounded shared-index step. | Keep the bounded step; both effective previous/next consumers enable the base Qt button's held auto-repeat. |
| Project experiment names | No shortening contract. | Preserve short lists; actual delegate model has a bounded first/last list and a displayed middle ellipsis for large counts. |
| Direct joint cancellation (C11-T62) | Exercised direct joint callbacks on a declared scan. | Exercise the same cancellation routes on an admitted non-scan project; separately require a declared joint scan to refuse before any callback and preserve every file. Single cancellation remains unchanged. |
| Native scan opens (C11-T62) | A completion preceded any read of the next file. | Each completed file has an actual native read; only the next four dataset addresses may be prefetched. Nine files cross the bound, and a fifth-address escape is rejected. |
| Evolution CSV x convention | Prescribed the extract-rule id `temperature`. | Resolve the declared target `diffrn.ambient_temperature` or its rule id in the saved CSV, while preserving every rendered x/y/error assertion. |
| Worker Follow projection witness (F3) | Read the displayed pattern immediately at a native callback. | Wait for the committed fitted count and the shown measured columns matching independent ASCII hashes, then retain the same dataset identity, measured values and uncertainties assertions. A calculated frame may need later worker progress; this actor judges the measured columns only. Fitted-value and calculated-pattern checks remain in the CSV projection gates. |
| Worker completion / template-edit observation (F3) | Treated `running == false` and a synchronous parameter setter as a fully projected view. | Wait for `calculating == false` and the displayed pattern to settle after the worker has ended and after edits; capture the worker refusal so a refused Continue cannot masquerade as a completed run. The fitted dataset and optimizer work requirements remain unchanged. |
| Scoped producer dependencies | Every execution node constructed parity, transitions and the 100000-file benchmark. | Explicit module fixtures separate projection, transitions and scale. A scale node still invokes the complete benchmark; a projection/transition replay no longer starts unrelated scale work. |

New observers have live disconnected, constant or wrong-state controls. Reset and Continue still
use the actual app/core/worker; optimizer entries bind the fitted file and measured payload.
The scale actor remains unthrottled and its bounds remain unchanged.
