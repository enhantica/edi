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
units fit their content. Numeric columns share the remaining space equally.
Headers and row cells use the same widths and explicit alignments. In Analysis,
values and their header align right, with units aligned left in the adjacent
column so they sit next to the values. Text editors show the beginning of an overflowing value when idle and expose its full value
on hover. Free parameters are bold and green; invalid values retain red.

The analysis table offers name, variability and category filters. Its height
uses the available sidebar space after reserving the filters, slider, fitting
controls and Continue button. Tables that overflow show part of the next row.

Recent projects are saved in the app settings, with disk availability and a
remove action. Bundled examples use readable sample and instrument names.
About opens the dependency table only from its libraries link.

## Scope

Selected notes: 2, 4, 9, 10, the GUI portion of 11, 14–18, 22, 23, 25 and 26.
From the supplied GUI notes: atom/experiment/loop widths and IDs, measured-data
computed fields, overflowing values, free-value styling, analysis layout and
category filtering, recent/example project tables and About's dependency table.
The Text tab and persisted `.edi` vocabulary are unchanged by owner request.
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
