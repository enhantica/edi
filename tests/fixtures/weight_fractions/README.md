# Single-structure weight fractions

Before the owner decision of 2026-10-17, saved experiments with at most one
enabled linked structure omitted `_linked_structure.weight_fraction`. After it,
every linked experiment carries the column: the enabled row is exactly `1.0`
without uncertainty; disabled rows retain `.` and take no share.

`single_phase_bytes.historical_single_fraction` validates the complete column,
its position, original column set, all row widths, enabled flags and exact new
cells before removing only the added column declaration and row suffixes. It
leaves multiphase outputs unchanged. Old input and saved-byte hashes are retained,
with every other byte and the full file inventory still compared. Missing,
duplicate, uncertain, wrong-valued and disabled-share cells are exercised as
rejection controls; a scale change must remain visible to the old comparator.

The historical saved-project gates use this mapping only for the pre-column
comparison. Current save/reload fixed points keep their whole new files. The
original single-phase calculation and fit captures pin scientific parameters,
patterns and metrics, not writer bytes; weight fractions remain derived values
and add no fitted parameter slot, so those inventories need no adaptation.

The app check supersedes its earlier empty-single-phase expectation with unity.
Its read-only, fitting prohibition, live uncertainty role, separate context menu
and unavailable-cell checks remain. The Node consumer executes the actual QML
property and parameter bindings with the real number-display functions; it
checks literal `1.0`, the existing nontrivial multiphase value/error, and the
unavailable-cell case. It does not claim native GUI execution.
