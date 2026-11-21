# 0096. The UI update rule

- **Status:** Proposed
- **Date:** 2026-11-18
- **Implementation:** ⬜ Not implemented
- **Priority:** Highest
- **Forward constraint (binding on new features):** a new chart, table or page follows the five rules below: it does
  no work while hidden, refreshes only what is on screen, never builds data on the GUI thread, shows at most one
  swap per frame, and lays out its frame before its data. A new GUI-thread cost that grows with the data needs a
  measured reason in its ADR.

## Context

edi now opens projects far larger than the examples it was designed around: a sequential scan of about 44 000
patterns, a five-bank time-of-flight set, a 100 × 5 series of joint fits. With these, page switches lag, one page's
charts follow a change more slowly than another's, and the end of a series fit freezes the window for about two
seconds while about ten unrelated views republish. The profile of these scenarios
(summarised in the table below; software rendering on a shared Linux machine, so the times are relative) shows
the same four causes everywhere:

1. Views that are not on screen still receive every change and rebuild in full (a hidden page's charts and tables,
   the Report, a chart tab behind another).
2. A visible table or chart rebuilds all of its rows or points when one value changes (a model reset, a full series
   replace).
3. Data the views show is built on the GUI thread, in a loop over every pattern, point or row.
4. A chart creates its panes and axes when their data first arrives, so its first frames show a partial layout and the
   layout then moves.

Parts of the rule exist, view by view: ADR-0017 says a hidden chart draws nothing and draws once when shown (the
pattern chart and structure view controllers keep a dirty flag), ADR-0041 says the same for the scan views and draws
one frame's changes once at polish, ADR-0070 limits a held slider to the calculation and the charts, ADR-0020 makes the
calculation asynchronous and newest-wins on `edi::work::Worker`, and ADR-0089 keeps series reads off the GUI thread.
Each was written for one view, so the views that came later (the Evolution rebuild, the correlation rebuild, the
single-crystal stacked redraw, the parameter filter, table row measuring, the report build, the full project publish)
do not follow it. This ADR states the general rule every view follows and supersedes none of them: they become its
instances.

| Scenario (software rendering, shared machine) | Longest GUI gap | Dominant cost | Cause |
|---|---|---|---|
| Switch to Report with the 44k scan | 10–12 s | the report model built and converted on the GUI thread on every show after an edit | 3, 2 |
| Switch to Experiment with the 44k scan | 4 s | table rows measured for column widths; scan colours per pattern | 3 |
| Next/previous bank on Experiment (5-bank set) | ≈ 2 s (Analysis ≈ 0.35 s) | every sidebar group destroyed and recreated because its model object is replaced, then its table re-measured | 2 |
| Stacked view reading 43 802 patterns | continuous 100–340 ms | each delivered batch reduced and measured on the GUI thread; the hidden assistant panel's context rebuilt per batch | 1, 3 |
| End of a 100 × 5 series fit | 1.4 s (5.1 s in total) | two full project publications, the results index read, every view republished | 1, 3 |
| Next/previous dataset on Experiment › Pattern (44k scan) | 2.6–4.2 s a press (Analysis 0.25–0.8 s) | the 43 802-row experiments table re-measures its rows because each press announces every row changed; then the chart shows data before its panes and refreshes 1–3 more times | 2, 3, 4 |

## Decision

1. **Hidden views do not update.** A view that is not visible to the user (its page is not the current page, its tab
   is not the current tab, its window or popup is closed, or it is scrolled out of a list) does not rebuild when its
   data changes. Its model marks it *dirty*; when the view becomes visible it refreshes once, from the newest data.
   The test of visibility is one shared property each view reads (`shown`: the page is current and every enclosing
   tab is current and the window is not minimised), never `QQuickItem::isVisible()`, which stays true for a
   SwipeView or StackLayout child that is behind another. A hidden view's delegates and series may stay created; they
   are not fed. A view that is expensive even to keep is inside a `Loader` that is active only while shown.
2. **Visible views update only what changed and what is on screen.** Tables are virtual (`TableView`/`ListView`
   delegates for visible rows only, rows fetched on demand with `canFetchMore`/`fetchMore` for very long models).
   An incremental change is a ranged `dataChanged` or a row insert/remove; `beginResetModel` is used only when the set
   of rows itself is replaced (another project, another experiment, another filter). A chart series changes by
   replacing its points once per swap, never by clearing and appending point by point, and an unchanged series is not
   touched.
3. **Data is built off the GUI thread and swapped on it.** Everything that scales with the data (decimated chart
   points, stacked and map images, table snapshots, the evolution of a parameter over a series, report tables) is
   computed on a worker into an immutable snapshot. The GUI thread only swaps the newest snapshot in. Requests are
   newest-wins: a request superseded before it starts is dropped, one superseded while running is discarded on
   arrival, and a request for a hidden view is not made (rule 1).
4. **At most one swap per view per frame.** Publications are coalesced: changes arriving within one frame (or a
   view's coalescing interval, at most 100 ms) produce one refresh. At the end of a run the publications that do not
   concern the visible page are deferred to when their page is shown (rule 1), and the remaining ones are spread so
   that no single GUI-thread slice exceeds the budget below.
5. **Layout before data.** A chart's frame (every pane, axis, title and legend it can show for the current kind of
   data) is laid out before its data arrives and keeps its space when the data changes; the data then fills it in one
   swap. Big charts draw at pixel resolution: a line series is decimated to about two points per device pixel column
   (min/max per column), and Stacked and Map draw only the window of patterns on screen.

**The budget.** No GUI-thread slice longer than 100 ms in any of the measured scenarios, with the measurement tool's
own work excluded (the CI watchdog of this task, as in the series view's steady-fitting gate). A view whose refresh
cannot meet the budget for the largest supported data is split (rule 3) or windowed (rule 5), never accepted.

## Consequences

- Page and tab switches cost one refresh of the newly shown view, from data that is already built; nothing else.
- A shown view may display data one frame (or one coalescing interval) old; a hidden view's content is rebuilt when
  shown, so the first frame after a switch may show the previous snapshot for at most one interval.
- Every view model gains a dirty flag and a `shown` input, and every heavy builder moves to a worker with an immutable
  snapshot type. Tests count refreshes per view (zero while hidden, one on show) and fail on a GUI gap over the budget.
- Debugging moves from "who updated this" to "who marked this dirty"; the refresh counter per view makes that visible.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep views live and make each update cheaper | Rejected: cost still scales with the number of views, and a 44 000-pattern scan makes even a cheap per-pattern loop too slow |
| Destroy hidden pages (`Loader` inactive for every hidden page) | Rejected as the general rule: recreating a page costs more than refreshing it, and loses scroll and selection state; kept for views that are expensive to keep |
| Debounce every change by a timer | Rejected: delays the visible view too (ADR-0070 rejected it for the slider for the same reason) |
| Frozen bindings only (Qt 6.5 `when:` on Binding) | Partial: useful for QML-side properties, but the C++ models would still rebuild; used together with the dirty flag |
