# Fit correlations computed once per fit and shared

Status: Proposed

Forward constraint: a per-file fit result (correlations today, per-phase R factors next) is made once, from that
file's fit, and kept as an immutable shared object. Nothing rebuilds a scan's results from the start, copies them for
an undo step or names them pair by pair in memory.

## Context

A fit's parameter correlations are rows of diffraction-lib's `_fit_parameter_correlation` loop. In edi, each row is a
`FitParameterCorrelation` in the `correlations` table (`ItemVec`) of the project's fit record (`FitResultRecord`). A row
holds two parameter unique names and the coefficient as text, so a loaded loop saves back byte for byte. crysta makes
the rows (`fit_correlations`) from a fit's covariance: for every pair it resolves both names and formats the
coefficient in its shortest round-trip form.

A sequential or independent scan keeps every file's pairs. Each file's rows arrive with the scan's per-file event
(`ScanFileRecord::correlations`). The core appends them to one list and assigns the whole list to the fit record when
the scan ends. The app keeps its own copy of every dataset's rows. Before each structural edit and each save it writes
all of them back into the record, and it reads them again afterwards. Reset fits and its Undo copy the fit record.
Since the template-only rule, a save writes only the template dataset's pairs.

On the 162-file D20 scan (`docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f`), measured on one Linux host, the command-line
fit (`python -m edi fit … --dry`) took 11.9 s end to end before correlations were added and 37.6 s after. A sampling
profile of the slow build puts 45.6 % of the time in the record's assignment at the end of the scan, 11.6 % in making
each file's rows, and the rest in the fits. The assignment is quadratic: `ItemVec`'s admission and row replacement
compare every row with every other, about 120 000 rows here. The app pays the same assignment on every structural edit
and save, and copies all the rows on Reset fits. The fits themselves did not get slower.

## Decision

1. **Computed once per fit, as numbers.** crysta gives a fit's correlations as numbers: the unique names of the fit's
   free columns and the coefficients of the upper triangle, in column order, as doubles. It formats nothing. Its
   `fit_correlations` keeps its signature and its rows, built on the numeric form, so crysta's own saved loop does not
   change. edi makes each file's correlations once, in that file's per-file event, from that file's fit result. It
   never recomputes an earlier file's correlations.
2. **Stored compactly.** A `CorrelationTable` is immutable. It holds a shared pointer to the column names and the
   coefficients as doubles in pair order (i before j, row by row). Pairs are given by position, with no strings per
   pair. A scan resolves names once: when a file's covariance labels equal the previous file's, its table shares the
   same names object, so a 162-file scan with one set of free parameters holds one names vector.
3. **Appended, never rebuilt.** The fit record gains `scan_results`, a map from file to
   `std::shared_ptr<const ScanFileResult>`, the file's immutable result bundle (decision 9), whose correlation table is
   its first member. The scan's per-file event inserts that file's bundle, replacing the file's earlier one if it had
   one. Nothing assigns, renumbers or copies the whole scan's pairs, at the end of a run or
   at any other time. The map is live state, not a category of the file.
4. **The saved loop holds only what a save writes.** The record's `correlations` table stays the persisted loop. For a
   single or joint fit it holds that fit's rows, as now. For a scan it holds the template file's rows (the declared
   template dataset, else the first file of the scan's listing, the one its report shows; `effective_scan_template_file`,
   2026-10-14), made from the template's table when the template's fit changes: the end of a run, a Single fit on a dataset, or their Undo. Ids
   run 1, 2, … in pair order, and the save writes each coefficient rounded as before, so the bytes match today's.
   Rows read from a file keep their ids and values until a fit replaces them. When the template's fit changes, rows read with another
   file move, unchanged, into that file's bundle unless a fit gave it one: the loop then holds the template's rows
   only, so the new rows' ids never collide with a read row's, and the moved rows are not saved, as the template-only
   rule wants. Undoing that fit puts the loop back as it was. A save therefore aggregates nothing, and an unchanged save
   writes the same loop.
5. **Shown lazily.** The Correlations tab takes the shown file's table, or the single fit's rows, and builds the matrix
   for that file only, from the doubles. Rows read from a file become numbers once, when first shown, and the tab keeps
   those numbers while it shows the same rows again.
6. **Shared, not copied.** Undo records, the scan template's stash, Reset fits and the results refresh hold the map of
   shared pointers, so copying the fit record copies pointers. The app keeps no second cache: its per-dataset view
   reads the record's map. Reset fits clears the map, and its Undo puts the same map back.
7. **Renames rewrite names, not pairs.** A rename that changes parameter unique names gives each names vector holding
   one of them a renamed copy, shared by every table that held the old vector. It also rewrites the persisted rows, as
   now, and gives a bundle's read rows renamed copies. The same rename rules apply (the block's own parameters by exact
   name).
8. **One general fix to `ItemVec`.** Admission and row replacement check duplicates and ownership with a hash of item
   pointers and keys, in linear time, for every loop. The scan exposed the quadratic check, and any large loop would
   hit it.
9. **The same storage for later per-file results.** The map's value is the per-file result bundle `ScanFileResult`
   (decision 3), whose first member is the correlation table. Per-phase R-factor rows join it as another immutable member, made in
   the same per-file event and shared the same way, so a later per-file result adds no second map and no copies.
10. **The saved format does not change.** The `_fit_parameter_correlation` loop keeps its columns, and a scan saves the
    template's pairs only.
11. **Rows hold numbers (amended 2026-10-24).** A row's coefficient is a double, in edi and in crysta. A single or joint
    fit's rows take crysta's doubles directly, and a loaded row's text is parsed once, when the file is read. Text is
    made only when saving. The chart, the report, Python's `correlation` and crysta's weight-fraction s.u. read the
    number. Before, every coefficient was spelled at full precision for each reader to parse back, and making that text
    was close to half of a large single-crystal fit's time.

The invariants below make these decisions exact; tests are written from them.

The Python surface keeps its shape. `FitResultBase.correlations` and a file record's correlations stay lists of
`FitParameterCorrelationItem`, made from the table when they are read. The machine report's `x-edi.correlations` keeps
its meaning.

## Invariants

| No. | Invariant |
| --- | --------- |
| I1 | A table's `names[k]` is the unique name of covariance column `k`, in the fit's free-column order (`covariance_labels`), with n columns. |
| I2 | `values` holds the n(n-1)/2 pairs i < j in row-major order: pair (i, j) is at position i·n − i(i+1)/2 + (j − i − 1). |
| I3 | Each value is `clamp(cov[i][j] / (sqrt(cov[i][i]) · sqrt(cov[j][j])), −1, 1)`, the same expression crysta evaluates today, so the double is the same. |
| I4 | No table is made, and the fit's correlations are empty as today, when the covariance is unavailable or not n × n, n < 2, a variance is not positive and finite, a label names no parameter, or a value is not finite. |
| I5 | A table shares the previous table's names object only when its covariance labels equal the previous labels in the same order. A changed or reordered column set resolves its own names. |
| I6 | Rows made from a table are numbered 1, 2, … in I2's order, with `source_kind` `deterministic`, the pair's two names, and the table's coefficient. They save as the rows edi made before this change, byte for byte. |
| I7 | Rows read from a file keep their ids, `source_kind`, names, values and file exactly, in the loop or, once the template's fit changes, in their file's bundle. They are never renumbered. A fit that replaces them writes I6 rows. |
| I8 | A read row's value is its text parsed once, when the file is read. |
| I9 | Python lists and the report are made when read: I6 rows from a table, I7 rows as read. |
| I10 | The Correlations matrix for a file is made from that file's table or read rows only, with today's level and count filter. |
| I11 | A rename replaces each names object holding a renamed parameter with one renamed copy, which every table that held the old object then holds. Values and pair order do not change. |
| I12 | A published table or bundle is never changed. Copying the fit record copies pointers only. |
| I13 | `ItemVec`'s linear checks keep its contracts: ownership by one collection, the refusal of a foreign item and unkeyed collections' reference semantics (ADR-0012); canonical-key identity and default ids (ADR-0016); held-row and column snapshots (ADR-0018); the same refusals with the same messages in the same order; and a refusal leaving the collection unchanged. |

## Consequences

- A scan's end, the app's edits and its saves no longer scale with the number of pairs the scan holds. A file costs one
  pass over its own coefficients. A save formats at most the template's pairs.
- The 162-file scan's correlations take about 1 MB of doubles and one names vector, instead of about 120 000 rows of
  five strings each.
- There are two forms to keep in agreement: a table and the persisted rows. The template's rows are always made from
  its table, and a test pins the saved bytes against today's.
- crysta gains a numeric correlation entry, so edi's pinned crysta build moves with this change. crysta's own saved
  output stays as it is.
- The category census lists the table and the per-file map as live results, not model categories, as it does for
  computed columns.

## Alternatives considered

- **Make `ItemVec`'s checks linear and change nothing else.** This removes the largest cost but keeps formatting every
  pair of every file, the app's write-back on each edit and save, and the copies on Reset fits. It does not reach the
  gate, and it leaves the storage that made the cost easy to add.
- **Keep each file's covariance and derive correlations when shown.** The covariance is about twice the size, and
  still needs the names. Correlations are cheap once nothing is formatted, so they are kept instead.
- **Save every file's pairs to a separate file.** This changes the saved project, which the template-only rule
  rejected.
