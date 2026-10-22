# 0045. Fit results tables and agreement factors

- **Status:** Accepted
- **Date:** 2026-10-21
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

The "Least-squares fit results" dialog listed everything in one table: the minimizer, the status, the time, the
iterations, the reduced χ², then every R factor, then each dataset's R factors and χ², then each phase's. With five
datasets the table ran off the bottom of the screen, the same factor appeared once per dataset in a long column, and
"%" was repeated in every label. The R-factor names were written flat (Rwp, R_Bragg) everywhere in the app.

## Decision

1. **Two tables.** The summary table keeps the rows down to the global reduced χ²: the overall status, the fitting
   time (written `1.3 s`), the iterations and the goodness of fit. The minimizer is not listed; the status bar names
   it.
2. **The agreement table.** Below the summary, one column per factor in the order FullProf prints them: R<sub>p</sub>,
   R<sub>wp</sub>, R<sub>exp</sub>, cR<sub>p</sub>, cR<sub>wp</sub> (background-corrected), then R<sub>Bragg</sub> and
   R<sub>F</sub> once per linked structure, the structure named under its header with its coloured icon. The global
   row ("All datasets") comes first, then one row per dataset with its coloured experiment icon. With a single
   dataset the global row is left out, since it would repeat the dataset's own. A factor that is not defined for a
   row, such as a phase factor over several datasets, stays empty. There is no χ² column.
3. **Per cent once.** The headers carry no "%"; one line under the table says that all R values are in %.
4. **The dialog fits the screen.** A long dataset list scrolls inside the agreement table.
5. **Subscripts everywhere.** Every R-factor name the app shows is written with its subscript through Qt's rich
   text: the dialog, the dataset line above the chart and the Report page. The stored texts stay plain, so search
   and the written reports are unchanged; the subscript is added where the text is drawn.
6. **The Report page's background** is the Text tab's.

## Consequences

- Comparing datasets is reading one column instead of finding the same label several times.
- A scan's summary keeps one table; its factors are in the Evolution tab.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep one table and group the rows by dataset | Rejected: still too long for several datasets, and the same factor is still hard to compare. |
| A χ² column in the agreement table | Rejected by the owner: χ² is in the summary, and it is not a per-cent factor. |
| Write the subscripts into the stored texts | Rejected: the reports and the search read the plain texts. |
