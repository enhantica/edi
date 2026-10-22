# 0041. Stacked patterns and a 2D map for a sequential fit

- **Status:** Accepted
- **Date:** 2026-10-22
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

A sequential fit runs over many datasets, often hundreds, taken along a temperature, a pressure or a time. The
Analysis page shows one dataset's pattern at a time, and the Evolution tab one fitted parameter across the scan
(ADR-0017 §19). What changes along the scan, a peak appearing, shifting or splitting, is easiest to see with every
pattern in one picture. The owner asked on 2026-10-14 for two such views beside the existing ones: all patterns one
above another in one chart, and a 2D map with x across, the scan parameter up and intensity as colour. A scan's
patterns are files read when asked for, never all held at once (ADR-0026), so the views must not keep them either.

## Decision

1. **Two tabs.** The Analysis page gains *Stacked* and *Map* after *Evolution*, enabled for a scan project only.
2. **What they draw.** Every dataset's measured pattern. x across is the pattern's own axis (2θ or TOF) over the
   first dataset's range. Up is the dataset's first extracted value (the scan parameter, titled as the extract rule's
   column) once every dataset has one; until then, and in a scan without an extract rule, the file index. Each
   dataset's row spans halfway to its neighbours.
3. **Kept small.** The datasets are read in the background, a few at a time, the first time either tab shows, and
   each is kept only as 1024 columns across the x range: the lowest and highest intensity in each. The views fill in
   as the reads arrive, with a count of how many are read. Results read again over the same files (after a run or an
   undo) keep what was read. A dataset that cannot be read is not drawn, and the views say so above the plot: how many
   could not be read and the first reason; with none read, the empty view says it. When the scan extracts a value but
   a dataset gives none, the rows stay by file index and the views name that dataset.
4. **Stacked.** Each dataset is drawn as a line rising from its row, joining each column's lowest and highest value,
   so a narrow peak keeps its height; the highest value of the scan reaches four rows above a row. The datasets take
   the colours of a palette (ADR-0038: by place, a gradient past five), the app's palette unless the view's toolbar picks
   another of the five. Lower rows are drawn over higher ones.
5. **Map.** Each column takes the colour of its highest value. Between two datasets' rows the value is interpolated
   linearly in proportion to the distance from each, so the colour changes smoothly from one dataset to the next with
   no bands (the owner, 2026-10-22); beyond the first and the last row, out to their extent, it is that dataset's.
   The colour map is **viridis** by default, or magma, inferno or plasma from the view's toolbar (Smith, van der Walt
   and Firing; CC0; `data/colormaps` with their provenance): all four are perceptually uniform and read in grey and to
   the common colour-vision deficiencies. A colour bar at the right is drawn through the same lookup as the map, and
   labelled with the intensities its ends stand for, each label centred on its end.
6. **The chart's y scale.** Both views take intensity on the pattern chart's y scale (linear, square root or log),
   spread over the scan's lowest to highest value, so a weak peak can be seen on the map as on the pattern.
   **Toolbar.** Each view has a toolbar line above its plot, as the Pattern tab has: the y scale, which is the
   pattern chart's, and the view's colours, the stacked view's palette or the map's colour map, kept as app settings
   (ADR-0031 §7, `ScanViews`). The plot starts below it, so nothing is cut at the top (the owner, 2026-10-22).
7. **Following a running scan.** A line marks the shown dataset's row at all times, white edged in black on the map
   so it shows on every colour, in the accent colour on the stacked view; it moves when the rows are placed again (by
   scan value once every dataset is read). The shown dataset is the one the Pattern tab shows: with Follow on, a
   running scan moves it to each dataset as it is fitted, so the line moves along the scan. The patterns themselves are the measured data, so they do not change while the scan runs. A click on a row
   shows that dataset, here and on the Pattern tab.

## Consequences

- A long scan costs about 8 kB per dataset in these views, whatever its pattern length.
- The views show measured data only. Calculated patterns of a finished scan are not read back for them.
- Both views draw from the same reads; opening the second costs nothing more.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| Each pattern as its own chart series | Rejected: hundreds of series made the chart slow, and every pattern would be held in full. |
| A rainbow (jet) colour map | Rejected: not perceptually uniform; it shows edges the data do not have and fails in grey. |
| Rows at equal heights, labelled with the scan value | Rejected while every dataset has a value: unequal steps along the scan would read as equal. |
| Reading the calculated patterns too | Deferred: a finished scan does not keep them, and recalculating each would cost a calculation per dataset. |
