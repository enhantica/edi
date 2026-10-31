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

The app-owned `ParamTextField` override applies that idle overflow alignment to
standalone parameter entries, matching the FIRST `ParameterCell` policy rather
than inheriting the pinned `TextField`'s unconditional right alignment. This also
covers `ValueField` and the appearance scale/probability entries through their
existing shared control. Fitting text and active editing retain right alignment;
units padding, canonical and narrow tokens, cursor/draft/IME ownership, commit
paths and table-specific column alignment remain unchanged. The global style and
pinned GUI sources are not changed.

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

Messages retain their content-dependent row heights. Their wrapped label binds
its initial width to the resolved text column before the delegate applies widths;
the legacy label's height-dependent default width would otherwise make wrapping
and row height depend on each other during construction.

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

The upstream ListView selection model bound an undefined model during page construction in
Qt 6.11. The fix, `model: listView.model ?? null` on ItemSelectionModel and a typed ListViewHeader
cast for the column-width lookup, is now in the gui-components `edi` branch, so edi builds its ListView unmodified;
the app lifecycle gate covers direct undefined initialization and attach/detach transitions.

## One row and cell design (2026-10-21)

Every table uses ListView cells only: `ListViewLabel` for text (headers and rows alike, so both have the same
margins), `ListViewButton`, `ListViewCheckBox`, `ListViewComboBox`, `ListViewParameter` and `ListViewTextInput`, from
the gui-components `edi` branch; no `TableView*` type is left in edi's QML (the owner, 2026-10-21). Every table's rows
are `Components/TableRow.qml`, the base's ListViewDelegate. The list's moving accent marker shows the current row, and
the row's number, a `ListViewLabel` with `marksCurrentRow`, turns bold in the accent colour on that row (ADR-0017
§11). A table that has a current row selects no row (`DataTable.marksCurrentRow`).

The report preview's tables (`Pages/Report/ReportTable.qml`) are document tables that mirror the HTML report's, with
decimal-aligned numbers and no row interaction, so they are not ListViews.

## Parameter menus

The field and table-cell parameter menus use the same s.u./free terminology as
Analysis and show a units column whenever the parameter has units. The field control is
replaced through ADR-0015's declared host seam; the table cell is the base's `ListViewParameter`, which carries the
units column and the lazy menu and takes the s.u. and free titles as properties.

A menu is made the first time it opens, never with its control: a page holds
hundreds of parameters, and building every menu up front was most of a large
project's page build. The free toggle reports through the control's
`fitToggled` signal, so a consumer needs no menu to exist.

## Opening project rows

Examples and Recent projects use an explicit row-parent mouse area for opening.
A second default-property TapHandler competes with the pinned delegate's selection
handler and can lose the click. Recent projects reserve the remove button's column
outside the opening area; missing projects stay visible without opening.

## Numbers in parameter cells

A parameter's value is rounded to its uncertainty's first digit, or to six
significant digits without one (`NumberText`). The width of its cell never
changes the text: a long value starts at the left and clips at the cell's edge,
without an ellipsis, and editing shows the full value. The sidebar's parameter
fields follow the same rule. A derived, read-only value such as a linked
structure's weight fraction is shown the same way, with its uncertainty in the
value's menu rather than in the cell.

A value at or above 1e6, or below 1e-4 and not zero, is written in scientific
notation with four significant digits, and its uncertainty in the same exponent
with three decimals: `2.290e7` with s.u. `0.010e7`. The exponent has no `+`.
The threshold follows the owner's request for the large intensities of a
sequential fit; plain numbers outside parameter cells keep their own rule.

## Column widths (2026-10-27)

One rule in `DataTable`, which every table and every generated group uses (the owner, 2026-10-24 and 2026-10-27).
The row-number column fits its digits, and every text or value column fits its header and its widest shown cell,
each with one margin (three table spacings), so neighbouring columns sit equally far apart and every header stands
over its values. A number cell is measured by the number it would show, a label by its natural width, an editor by
its text, and a cell holding a combo box by the box: its widest option, a small gap and the arrow, its icon
included. The last data column, aligned left, takes the rest of the row: a text there stretches, a number leaves the
space after it empty; no column before another data column takes spare width. Button columns keep their widths at
the right edge. A row too narrow for its texts first gives up the last column's room, then the margins, and only
then narrows the texts, where a number shows its short form. Every row has the same cells as its header (a column
per structure is an empty cell on a row without a curve), and a row or header whose cells change is sized again,
since the base centres each row. Atom sites, atomic displacements and the Analysis parameters keep layouts of their
own: equal columns for the first two; for the parameters the name in full, then value and s.u. at three tenths of
the rest each and min and max at two tenths, with free at the right.


### 2026-10-28: deferred fitting belongs to the actual table

All four deferred fitColumns requests share one Qt.callLater scheduling door. A
plain lifetime token coalesces pending requests and is retired by the original
DataTable destruction handler before a queued callback can resolve its QML
methods. The live callback clears its pending bit before fitting, so padding or
new-row changes during fitting can request the ordinary next pass. Column kinds,
measurements, widths, filler padding and virtualized-row layout are unchanged.
This uses the same original-QML lifetime pattern as the project page's deferred
Create callbacks; it adds no timer, ignored warning or appearance rule.

Signal entry paths retain that same plain lifetime token before dispatching table
methods. Header width application and the fitting pass recheck it after mutating
cells, so a destruction callback cannot turn their next lookup into a call on a
retired QML table. The token belongs to the original table, never a model or its
replacement.

### 2026-10-28: retain the original row inside mutating width helpers

The first ListView width distributor is the pinned GUI component's applyWidths.
DataTable keeps its exact sequential resolved-width assignment locally so each
observable cell write can be followed by a check of the original table lifetime,
model/revision and row/cell identities before another lookup or write. Filler
padding computes both values before its first write and checks the same owner
between left and right padding. Alignment callers retain that obligation too.
The normal width distribution, measurement and coalesced fit rules do not change.

At original table destruction, its pinned header/delegate Connections are disabled
before their listView references are released, preventing late inherited callbacks
from resolving removed derived methods. Other fit signal entries retain the plain
lifetime token before dispatch. This changes neither the pinned dependency nor live
layout, and adds no timer or ignored-warning path.


## Native table procedures with the original view records

ApplicationInfo executes DataTable's column projection, fitting/measurement, row/cell ownership, padding/alignment, delayed scheduling, destruction, cache updates, reveal and keyboard procedures. The pinned base ListView remains the visual control; the existing fittedWidths/rowWidths maps, Map objects, revision and lifetime records remain on the same view. No second model, width cache, controller or broader currentness rule is introduced. Each original row ownership predicate retains its parent/model/revision and member-reference checks around observable assignments.

The procedures call the current engine's real property, method, coercion, array and intrinsic iterator operations. For-in follows the pinned compiler's enumeration path without IteratorClose; for-of retains original completion/close behavior. Literal construction bypasses inherited setters while original later writes retain them. Native callback values preserve formal arity, original captures and function/lifetime identity; width fitting remains queued by Qt's existing delayed-call queue. Original model notifications and exact text-cache invalidation order remain, including read/measurement dependencies. Scientific models and Undo writes are untouched.

QML keeps state declarations, visual delegates, direct bindings and named one-call forwarding methods. Complete desktop/browser compilation and live row/model mutation, destruction, geometry, font, key and error verification remain required after the full migration.


## Retiring a table during QML destruction

The existing `DataTable` cleanup first disables its rows' connections to the table and then clears
those rows' `listView` references. The native implementation retains both passes, row identity checks,
and the column-fit lifetime token. During this destruction callback, QObject properties used to find
those connections are read through the native meta-object's stored value, rather than the general
script getter. Qt's general getter flushes pending bindings, which can try to enable a binding while
its QML context is being destroyed. Live table reads keep the normal script getter and dependency
capture; this exception applies only to retirement and introduces no saved copy or second owner.

This repairs destruction-time binding activation. It does not establish that every earlier QML
lookup avoided activation, or qualify unrelated layout, parameter, or persistence behavior.
