# 0050. Observed reflections and the fit cutoff

- **Status:** Accepted
- **Date:** 2026-10-24
- **Implementation:** ✅ Implemented
- **Priority:** High

## Context

A single crystal's weak reflections, F² within a few su of zero, are treated two ways in crystallography: a
threshold such as I > 2u(I) says which reflections the published R factors and counts are taken over (CIF's
`_reflns.threshold_expression`, SHELXL's R1), and a separate cutoff says which reflections the least squares uses
(FullProf's `Rmub`, SHELXL's `OMIT`). FullProf fits only F² > 3 su(F²) in the taurine example, so edi could not be
compared with it until both could be set.

## Decision

1. **Model and file.** A single-crystal experiment carries `_reflns.threshold_sigma` and `_reflns.threshold_basis`
   (`intensity` or `amplitude`), each absent until set; absent, the threshold is I > 2u(I). The analysis carries
   `_refine_ls.threshold_sigma`, absent until set; absent, every reflection is fitted. The reader checks them with
   crysta's rules, and the save, through crysta's writer, also writes the threshold expression, the counts, the R
   factors over all, observed and fitted reflections and each reflection's include status.
2. **The Reflections group** (Experiment page, Extras) shows the threshold above the reflection table: the multiple
   of the su, the basis as I or F, and the expression they make. Blank fields show the default as a placeholder.
3. **The Refinement group** (Analysis page, shown when the project has a single crystal) holds the fit cutoff, blank
   for all reflections.
4. A fit passes the cutoff to crysta, which fits only the reflections above it.

## Consequences

- A fit set up as FullProf's can be compared with it on the same reflections.
- Both settings are undoable edits like every other setting, and a project that sets neither keeps its files.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| One threshold for reporting and fitting | Rejected: the standards keep them apart, and fitting all data stays the default. |
| A Reflections group of its own on the Main tab | Rejected: the reflection table's group already has that name; the threshold sits above the table it applies to. |
