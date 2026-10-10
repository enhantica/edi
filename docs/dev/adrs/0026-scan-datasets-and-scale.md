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
