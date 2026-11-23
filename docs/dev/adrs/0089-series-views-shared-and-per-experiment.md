# 0089. Series views: Evolution by Shared and Per experiment, Map and Stacked by rows

- **Status:** Proposed
- **Date:** 2026-11-15
- **Implementation:** ⬜ Not implemented
- **Priority:** High
- **Forward constraint (binding on new features):** a series view draws from the two results files and from
  per-pattern summaries built for the rows on screen; it never reads every pattern, never keeps a pattern per point,
  and never reads a file on the GUI thread.

## Context

A series of joint fits (ADR-0088) records `analysis/results.csv` per point and `analysis/results_experiments.csv`
per point and experiment (ADR-0026, "Two results files"). Evolution today lists every column of one file in one
selector; Map and Stacked draw one row per dataset of a one-experiment scan and keep each read pattern. The owner
asked for: one Evolution chart and one selector with two sections, Shared and Per experiment, a per-experiment
parameter drawing a curve per experiment in its colour with legend entries to show or hide each, a right axis for a
second parameter, and a map or a chosen subset above about 10 experiments; Map and Stacked with a Rows selector
(Temperature points or Experiments) and a selector or slider for the fixed dimension, an "all experiments merged"
view in d with each pattern divided by its scale, by default temperature rows, all experiments merged, in d; derived
values read-only in the tables and listed in the Evolution selector; all of it responsive at 1,000 points × 100
patterns.

Prior art surveyed: series tables of one row per dataset with value and error columns (Mantid's
`PlotPeakByLogValue`, RietX's `SeriesResult`, SasView's batch grid, GSAS-II's sequential table and its plot of a
column against the series); Mag2Pol plots a parameter table against temperature; none has a per-dataset-per-step
table to draw curves per dataset from. Displayed-resolution reductions are edi's own (ADR-0026, the scan views).

## Decision

1. **Evolution sections.** The selector lists **Shared**: every column of `results.csv` (structure parameters and
   structure-level derived values), and every experiment parameter made "same for all experiments" (ADR-0087),
   listed once and read from the leader's rows; then **Per experiment**: every other column of
   `results_experiments.csv`, listed once by its name without the datablock. Derived values are listed in their
   section with a "derived" mark. A one-experiment scan shows one list, as now.
2. **Curves per experiment.** A per-experiment parameter draws one curve per experiment in that experiment's colour
   (the palette rule of ADR-0084), with a legend entry to show or hide each. "Compare with" picks a second parameter,
   drawn against a right axis in the same chart.
3. **More than 10 experiments.** A per-experiment parameter of more than 10 experiments opens as a map (points along
   x, experiments along y, colour the value, the s.u. in the tooltip); "Curves" switches to curves for chosen
   experiments, the first 10 by default, picked from a searchable list.
4. **Map and Stacked rows.** A Rows selector: **Temperature points** (one row per point; a selector picks one experiment
   or All experiments merged) or **Experiments** (one row per experiment; a slider picks the point). The scan's
   extracted value labels the point rows, as now. **All experiments merged** draws every experiment's pattern of the
   point on the d axis, each divided by its fitted overall scale (its first enabled linked structure's scale from
   `results_experiments.csv`; before a point is fitted, by its template's), so the banks align. Default for a series:
   Temperature points, All experiments merged, d.
5. **Per-pattern summaries.** Map and Stacked draw from summaries: for each row on screen, the pattern's lowest and
   highest intensity per pixel column over the shown range on the shared axis, the merged row the per-column extreme
   over its experiments. A worker builds them as rows come on screen, reading each pattern once for it, and keeps them
   in a cache of at most 64 MiB, dropped when the views are hidden. Nothing is stored in the project. A pattern read
   for a summary is released once summarised.
6. **Derived values in the tables.** The Linked structures table keeps its weight fraction column; the moments table
   gains read-only |M|, θ and φ columns with their s.u. under the red s.u. rule (ADR-0085). Every derived value and
   s.u. the app shows (tables, Evolution, report) is crysta's one result for it, taken through the constraints from the
   fit's covariance; edi computes none of them. The structure view's
   moment form (crystal axes, Cartesian, spherical) is unchanged.
7. **The GUI thread.** Reading results rows, building summaries, grouping files and listing folders run on workers.
   The scale run (ADR-0026, "Two results files") also records the longest GUI-thread stall.
8. **How well each point fits** (edi #140). After the parameters, both sections list the point's χ² (Shared: the
   reduced χ²; Per experiment: each experiment's χ²) and the agreement factors the results files record:
   R<sub>p</sub>, R<sub>wp</sub>, R<sub>exp</sub>, and R<sub>Bragg</sub> and R<sub>mag</sub> per structure. They
   are drawn without error bars, with their subscripts (ADR-0045), and a file written before them lists none until
   a resume rewrites it. The report's evolution charts follow the same list.

## Consequences

- At 1,000 points × 100 patterns a view holds summaries for at most the rows on screen, about a few MB.
- The merged view needs a fitted scale per experiment to align intensities; before a fit it uses the template's.
- Drawing curves for 100 experiments at once is not offered; the map replaces it.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Two charts or two selectors, one per file | Rejected by the owner: one chart, one selector, two sections |
| Keep every read pattern for Map and Stacked | Rejected: 100,000 patterns do not fit in memory |
| Summaries written to the project during the fit | Rejected: a second per-pattern store beside the results files; built on demand they cost one read per row shown |
| Normalise merged patterns by their maximum | Rejected: the maximum depends on the phase content of each bank; the fitted scale is what the owner asked for |

## Published sources

- B. H. Toby, *R factors in Rietveld analysis: how good is good enough?*, Powder Diffr. 21, 67–70 (2006),
  doi:10.1154/1.2179804 (each experiment's own goodness of fit is shown, not compared across experiments).
