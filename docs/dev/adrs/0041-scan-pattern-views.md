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
2. **What they draw.** Every dataset's measured pattern. x across is the pattern's axis (§7) over the first
   dataset's range. Up is the dataset's first extracted value (the scan parameter, titled as the extract rule's
   column) once every dataset has one; until then, in a scan without an extract rule, and when the file index is
   chosen (§7), the file index. Each dataset's row spans halfway to its neighbours.
3. **Kept small.** The datasets are read in the background, a few at a time, the first time either tab shows, and
   each is kept only as 1024 columns across the x range: the lowest and highest intensity in each. The views fill in
   as the reads arrive, with a count of how many are read. Results read again over the same files (after a run or an
   undo) keep what was read. A dataset that cannot be read is not drawn, and the views say so above the plot: how many
   could not be read and the first reason; with none read, the empty view says it. When the scan extracts a value but
   a dataset gives none, the rows stay by file index and the views name that dataset.
4. **Stacked.** Each dataset is drawn as a line rising from its row, joining each column's lowest and highest value,
   so a narrow peak keeps its height; the highest value of the scan reaches four rows above a row. The datasets take
   the colours §6 describes. Lower rows are drawn over higher ones.
5. **Map.** Each column takes the colour of its highest value. Between two datasets' rows the value is interpolated
   linearly in proportion to the distance from each, so the colour changes smoothly from one dataset to the next (the
   owner, 2026-10-22); a toolbar toggle switches to stepped colour, each dataset one band out to halfway to its
   neighbours, and back, smooth being the default. Beyond the first and the last row, out to their extent, the colour
   is that dataset's. Either way the map is one image of the plot's own pixels, so no line shows between datasets: the
   first build drew each dataset as its own antialiased image rectangle with fractional edges, and every boundary
   pixel row, covered twice in part, let the background show through as a thin light line.
   A colour bar at the right is drawn through the same lookup as the map, and labelled with the intensities its ends
   stand for, each label centred on its end.
6. **Colours** (the owner, 2026-10-22). Both views offer the same choices beside their own: the colour maps viridis
   (the Map's default), magma, inferno and plasma (Smith, van der Walt and Firing; CC0; `data/colormaps` with their
   provenance), all perceptually uniform, reading in grey and to the common colour-vision deficiencies, and in either
   app theme; and for each colour scheme a ramp from the pattern chart's plot background in the current theme to the
   scheme's first measured colour, mixed in Oklab (ADR-0038's gradients). The Stacked view also offers the five
   schemes' own colours (ADR-0038: by place, a gradient past five), its default the app's scheme. A pattern on the
   Stacked view takes a map's colour at its place along the scan between a tenth and nine tenths of the map, or a
   ramp's from a quarter of the way, so no line takes the background's colour. cividis and turbo were left out: their
   tables come under other licences, and turbo is not perceptually uniform. On the owner's asking for more pleasing maps
   than matplotlib's (2026-10-22), candidates were added for the owner to choose from, each with its source table and
   licence (`data/colormaps/PROVENANCE.md`, DEPENDENCIES.md): six of Fabio Crameri's Scientific colour maps, five
   of cmocean's, Google's Turbo, three ColorBrewer schemes and three of Peter Kovesi's CET maps; the ones not chosen
   are removed with their rows. On the owner's asking for maps with a light low end for the light theme, cmocean's
   tempo, ColorBrewer's Blues, Purples and YlOrRd and CET L17 and L18 joined them, and the Map's toolbar gained a
   reverse switch, remembered with the other settings, that runs any map the other way; the colour key follows it.
7. **Axes and toolbar.** Each view has a toolbar line above its plot, as the Pattern tab has (the owner,
   2026-10-22): the axes' types, the colours, the zoom and the reset. Every axis type is one setting with each other
   selector of the same quantity: x is the project's own (2θ or TOF, or d-spacing read off the template's current d
   column through its own axis, the pattern chart's rule, ADR-0017 §15), y places the rows by the scan value or the
   file index as the Evolution tab's x does, and the intensity scale (linear, square root or log; the Map's z) is the
   pattern chart's y scale. Intensity is spread over the scan's lowest to highest value on that scale, so a weak peak
   can be seen on the map as on the pattern. The box zoom is always on: a drag over the plot zooms to its box, and the
   reset, a secondary click (a touchpad's two-finger click, as on the pattern chart), another scan, another x axis or
   another row placing returns to the whole range. The plot starts below the toolbar, so nothing is cut at the top;
   when the chart is too narrow for one toolbar line, the buttons take a second line, each line centred as the
   pattern chart's. An axis box names its choice as its list does (`x: d` for the list's `d`; the owner, 2026-10-22),
   on the pattern chart too, and d can be chosen only once a calculation has given a current d column: until then
   the box is off and shows the axis drawn. The colours are app settings (ADR-0031 §7, `ScanViews`, with the Map's smooth or stepped choice).
8. **Following a running scan.** A line marks the shown dataset's row at all times, the same line as the Evolution
   tab's mark of the shown dataset (the owner, 2026-10-22): 2 px, edged on each side by 1 px of half-transparent
   colour, black edged in white in the light theme and white edged in black in the dark one, so it shows on the plot
   background and on every colour of every map; it moves when the rows are placed again (by
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
