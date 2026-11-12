# 0026. Scan datasets and their scale

- **Status:** Accepted
- **Date:** 2026-10-06
- **Implementation:** 🟡 Partially implemented: datasets, runs, the template dataset and the bounded read-ahead are shipped; the scale gate runs to 100,000 files
- **Priority:** High
- **Forward constraint (binding on new features):** nothing may keep an object per scan file in memory or read every file up front; `analysis/results.csv` stays the one store of a scan's results.

## Context

A scan project fits one template experiment against every file of a data directory, through
crysta's sequential driver (crysta ADR on the sequential fit). The app lists the files as
datasets, runs the scan and shows each dataset's result. Measured scans have hundreds of files;
the owner set the design target at 1,000,000 files so that the app never has to be redesigned for
a long experiment.

## Decision

1. **The file list is the only per-file state kept.** Listing the scan reads the directory, never
   the files (`edi::scan_datasets`, crysta's own listing). A file is read when it is shown or
   fitted. 1,000,000 names are tens of megabytes.
2. **`results.csv` is the store of results.** A run appends one row per file. The app reads the
   new row from the end of the file as each file completes, and the whole file only when a project
   opens or a run ends. No fitted model is kept per file.
3. **Bounded read-ahead.** crysta's driver reads at most four files ahead of the fit on a worker
   thread, so the fit does not wait for the disk; the single-threaded web build reads each file
   when it fits it.
4. **Views draw what is on screen.** The Experiments table and the selector popup are list views
   that create rows only for what is visible. The Evolution chart draws points through one scene
   graph item and, above 5,000 points, keeps the lowest and the highest point per x bucket.
5. **The gate.** A synthetic scan of 100,000 files, generated at test time from one data file, runs
   to the end. Peak memory after file 100,000 is within 10 % of the peak after file 1,000, and the
   median time per file over the last 1,000 files is within 1.2 times the median over files 1,001
   to 2,000. Flat memory and flat time per file at 100,000 files are what carry the design to
   1,000,000.

## Consequences

- A run's cost per file does not grow with the number of files done, and memory does not grow
  with the scan's length beyond the file names.
- The app's dataset views read `results.csv`; a results file edited by hand is what they show.
- Sorting or filtering the datasets by a fitted value needs a pass over `results.csv`; nothing
  indexes it.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep each dataset's fitted model in memory | Rejected: memory grows with the scan, 1,000,000 models do not fit. |
| Read every file when the project opens | Rejected: minutes of reading before anything shows, for files most users never select. |
| A database beside `results.csv` | Deferred: one more store to keep in step, for queries nobody asks yet. |

## Amendment, 2026-10: skipped and refused files

crysta writes no `results.csv` row for a file with no intensity above zero, records a file whose fit was refused
after the solver ran as a failed row, and lists both, with each file's skipped negative points, in
`analysis/scan-notes.csv`. edi reads that file by one rule wherever it reads it (the results index, the live index
as rows arrive, and `edi fit`): the header, complete lines of four cells, `negative_points` a decimal integer of at
most 12 digits, `skipped_dataset` `True` or `False`, each scan file named once. A file that breaks the rule is an
explicit refusal of the index, not a silently different state. A dataset is **processed** when it has a row or is
skipped; Start, Continue, Reset, the live count and the scan summary count processed datasets, so a scan whose
remaining files are all skipped is complete.

A skipped file sends no event of its own, so the live index reads the notes appended before each new row, and the
app indexes the files on disk again when the run returns, before the running bar closes: files skipped after the
last row count for every ending (complete, stopped, failed). A refusal while a run writes refuses the whole index,
as a full read would, and is shown at once; nothing more is published until the full read at the end succeeds.
When that read refuses too, the datasets, evolution and counts stay as last accepted, the run keeps its own
outcome (Failed, Stopped, else Refused), and no summary is built from the refused read.
A scan whose processed files were all skipped is still a scan that ran: it has a scan summary and run provenance,
and a single fit after it is recorded as the last run. `results.csv`, `results-provenance.csv` and
`scan-notes.csv` may be absent, but a path that exists must be a regular file (`edi::scan_state_present`, asked by
every reader before it opens one): a directory there is refused, never read as no results or as an empty file,
and a fresh run or Reset that sets the result files aside refuses it too.


## Amendment, 2026-11: bounded GUI sizing and pattern styles

The dataset selector's widths are measured in C++ with QFontMetricsF. Its option measurement is kept until its
font, model, text role or sampled text changes; fit-outcome changes do not invalidate a name measurement.
Small lists are measured in full; above 1,000 entries the sample is the first 200, as for long tables. The current
display text is measured separately, so a later, longer selected name fits too. QML binds the resulting widths;
it does not traverse the model or create delegates to measure selector text. Measurements queued in one event
turn are combined, and changing the selected dataset does not remeasure the sample.

The Pattern chart requests just the displayed dataset's measured style, with the same palette rule as Stacked.
The palette lookup tests only enough free positions to decide whether the palette is exhausted; it never
allocates a position per dataset to compute one colour. Repeated publication of the same immutable correlation
table reuses its matrix; a different table or a change from row data still rebuilds it.

This repairs the selector and pattern-style work added after the original streaming fit. The existing table
delegate sampling is retained; replacing that sizing machinery throughout the app is separate work.


## Folder loading and template-first workflow

The measured-data Load menu accepts a whole local folder. It lists supported data filenames on a worker,
then uses the existing linked `loadDatasets` route: one scan declaration and only the first file loaded as the
template. It copies and hashes no data files. Several selected files continue to use the same route.

A loaded scan stays in Single mode for the template fit until the user chooses Sequential or Independent.
Option-list replacement publishes a revision, and every type selector observes it when locating its stored token;
changing an option list cannot leave the selector showing its first entry in place of the actual mode.
Evolution is visible whenever the project has a scan, including while the template is fitted in Single mode.
The dataset-choice explanation wraps inside the dialog. Empty collections use “No … yet”; a failed search keeps
its search-specific wording.


## Fit conditions in the result row

The scan index accepts the four `fit_result` condition columns written by crysta, validates their numbers and
termination, and reads each dataset's reason from the same row as its result. Live file-completion events carry
that reason directly; they no longer open a provenance file for every fitted dataset. The old separate ledger
is read only for a legacy CSV without the condition columns. The driver's backward-compatible migration owns
combining and removing that legacy file. Reset and Undo still preserve a legacy sidecar when an old project has one.


## Followed-dataset colour updates

Changing the followed dataset updates only its palette index. Its scan-wide positions are allocated when
membership or palette positions change. Each pattern controller caches the scan's small style table and
updates only its measured colour for a new dataset; changing structure positions, membership, scheme or
experiment invalidates that cache. The general palette allocators advance their free-position cursors and
use indexed occupancy rather than restarting a linear membership search for each item. This removes the
scan-wide palette rebuild triggered by Adaptive, timed and display-waiting follow updates, and the same
quadratic allocation during initial project setup. Colour order and held-position rules are unchanged.


## Incremental scan-view ranges

Reading a batch extends the axis and intensity ranges from each pattern's cached extrema. A pattern's generation,
axis, exclusions, intensity scale and background-subtraction settings determine whether its extrema are reusable.
Unchanged patterns are not rescanned as later files arrive. File-index row positions, labels and stacked placement
stay fixed while loading; extracted-value ordering is resolved when every file has been read. Rendering keeps its
existing per-pattern reductions and pixel-sized map image. This removes repeated full-data range scans during
Map/Stacked loading without changing their raw-data retention policy.


Catch-up retains a drawing queue only while Pattern, Stacked or Map can display it. Hiding those views discards
their queued presentation; Evolution still receives every result row. Manually choosing a dataset stops Follow
both during fitting and while a completed fit's visible queue is draining.
