# ListView tables

Status: Accepted

## Context

The tables introduced in ADR-0017 use gui-components TableView, with column
widths set separately on headers and cells. Numeric columns compete with wide
row numbers, labels and controls. The gui-components `edi` branch provides
ListView, ListViewHeader, ListViewDelegate and ListViewTextInput with a shared
column-width definition and a half-row cue when more rows can be scrolled.

## Decision

Use those ListView types for every edi table, including dialogs and project
lists. Keep the upstream sources unmodified and pin the selected `edi` revision
with the archive and source-tree hashes used by ADR-0015.

Each table declares widths once. Read-only row numbers have blank headings and fit the largest displayed number;
icons, fit controls and remove buttons have compact fixed widths. Labels and
units fit their content, capped at a quarter of the table width so long identifiers
and paths cannot consume the numeric columns. Numeric columns share the remaining space equally.
Headers and row cells use the same widths and explicit alignments. In Analysis,
values, uncertainties and their headers align right, with units aligned left in the adjacent
column so they sit next to the values. Text editors show the beginning of an overflowing value when idle and expose its full value
on hover. Free parameters are bold and green; invalid values retain red.

The analysis table offers name, variability and category filters. The category
picker uses readable titles, icons and counts, with Structure and Experiment
parent groups and atom/peak subgroups. Every category represented in the parameter
walk is included, with counts and predicates derived from the same source rows.
Popups size before their first opening and keep their first option visible when
all options fit; longer lists scroll to the current selection. Its height
uses the available sidebar space after reserving the filters, slider, fitting
controls and Continue button. Tables that overflow show part of the next row.

Recent projects are saved in the app settings, with disk availability and a
remove action. Bundled examples use readable sample and instrument names.
About opens the dependency table only from its libraries link.
Table selector controls fit their current names and arrows within fixed column
bounds; names of different lengths keep their arrows close without moving the
other columns. Picker popups retain room for the alternative names.

## Scope

Selected notes: 2, 4, 9, 10, the GUI portion of 11, 14–18, 22, 23, 25 and 26.
From the supplied GUI notes: atom/experiment/loop widths and IDs, measured-data
computed fields, overflowing values, free-value styling, analysis layout and
category filtering, recent/example project tables and About's dependency table.
The original scope left the Text tab and persisted `.edi` vocabulary unchanged;
the identifier extension below adds persistent IDs to the existing background
and excluded-region loops.
ADP headers distinguish B/U isotropic and equivalent values, including B eq for
beta tensors. ADP conversion and chart/reflection physics remain separate concerns.

## Consequences

The prior tables, including scan extract columns, follow the same width policy.
The row models and their editing/undo paths remain the data source. Computed
pattern cells show only a published calculation and clear on refusal.

## Identifier correction

Row numbering and stored identifiers are distinct columns. Atom-site and
displacement identifiers are both editable through the same atom-site rename
operation. Analysis uses “s.u.” and “free” headings. The owner extended this
task on 2026-10-09 to add persistent editable IDs for background and excluded
region rows; these IDs belong to the data model and round-trip through `.edi`.

These rows extend ADR-0016/0018's ItemKey, ItemVec and RowSchema design. Legacy
constructors and files without IDs receive the first unused numeric ID on
admission, after reserving explicit IDs. Admission rolls back generated detached
IDs on refusal. Attached IDs must be nonempty and unique. Rename, deletion,
copy and save preserve the other rows' IDs. Exclusion bounds are recorded
row cells; numeric consumers receive their existing bounds-only snapshot.
The adapter carries both IDs and values into crysta's writer (ADR-0083); the
public Python exclusion property keeps its existing tuple-of-pairs interface.

The upstream ListView selection model binds an undefined model during page construction in
Qt 6.11. edi replaces that one component at the module seam with the pinned source plus
`model: listView.model ?? null` on ItemSelectionModel and a typed ListViewHeader
cast for the column-width lookup, allowing the replacement to pass edi's lint gate. The upstream checkout stays untouched;
the app lifecycle gate covers direct undefined initialization and attach/detach transitions.

## Parameter menus

The field and table-cell parameter menus use the same s.u./free terminology as
Analysis and show a units column whenever the parameter has units. Both pinned
parameter controls are replaced through ADR-0015's declared host seam; their edit
and fit-toggle behavior stays shared with the original controls.

## Opening project rows

Examples and Recent projects use an explicit row-parent mouse area for opening.
A second default-property TapHandler competes with the pinned delegate's selection
handler and can lose the click. Recent projects reserve the remove button's column
outside the opening area; missing projects stay visible without opening.
