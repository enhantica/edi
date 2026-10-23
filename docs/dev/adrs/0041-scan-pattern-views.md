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
patterns are files read when asked for (ADR-0026), so the views read them in the background. On 2026-10-22 the owner
asked for the same views for a joint fit, where the WISH banks line up on the d axis.

## Decision

1. **Two tabs.** The Analysis page gains *Stacked* and *Map* after *Evolution*, enabled for a scan project and for a
   joint fit of several experiments (the owner, 2026-10-22). Evolution and Follow stay a scan's.
2. **What they draw.** Every dataset's measured pattern; for a joint fit, every experiment's. x across is the
   pattern's axis (§7) over every dataset's range together. Up is a scan dataset's first extracted value (the scan
   parameter, titled as the extract rule's column) once every dataset has one; until then, in a scan without an
   extract rule, and when the order is chosen (§7), the datasets in order: by file for a scan, whose datasets share a
   datablock, by datablock for a joint fit's experiments. Each row spans halfway to its neighbours, so in order each
   is one band of equal height. Datasets at the same scan value (a temperature held, or reached again) split that
   value's band equally in file order, each with its own band, row and baseline, so none hides another. The rows are labelled as the pattern chart labels a Bragg row, left of the plot, at
   each row's height: the experiment's icon and the row's scan value with its unit, its file's name or its datablock's,
   in the dataset's colour (the owner, 2026-10-22); on Stacked a label stands on its curve's baseline, its bottom at
   the row, and on the Map it is centred on its band. The Stacked view always labels its rows so, with no numeric scale;
   the Map does in order, and by scan value keeps its numeric scale, a position on it being a real value its colour is
   interpolated at. Both views always mark each dataset's row with a short tick just right of the plot's right edge, in
   the dataset's Stacked colour, kept inside the plot's height (the owner, 2026-10-22). When labels would come too close to
   read, an evenly spread share of them shows, the shown dataset's always among them, and the rest come back as a zoom
   spreads the rows.
3. **What is kept.** A scan's datasets are read in the background, a few at a time, the first time either tab shows;
   a joint fit's experiments are taken from the project after each edit and calculation. Each dataset keeps its
   measured points (x and intensity). Every time the views draw, each dataset is reduced for the range shown at the
   plot's own pixel columns: while the range holds no more points than columns the points themselves are drawn,
   with more each column's lowest and highest intensity (`scan_trace`, `scan_pixel_values`). A zoomed view is drawn
   from the measured points of its range, never by stretching or smoothing a reduction made for the whole range (the
   owner, 2026-10-22: the first build kept 1024 columns of the whole range and showed them as steps when zoomed). The views fill in
   as the reads arrive, with a count of how many are read. Results read again over the same files (after a run or an
   undo) keep what was read. A dataset that cannot be read is not drawn, and the views say so above the plot: how many
   could not be read and the first reason; with none read, the empty view says it. When the scan extracts a value but
   a dataset gives none, the rows stay in order by file and the views name that dataset.
4. **Stacked.** Each dataset is drawn as a line rising from its row, joining its points, or each pixel column's lowest
   and highest value, so a narrow peak keeps its height; the highest value of the scan reaches four rows above a row. A toolbar box sets how high the patterns
   rise, one to five times that, twice by default (the owner, 2026-10-22). Its rows are labelled (§2), not scaled: the height the patterns rise into above the top row stands for no scan value (the owner, 2026-10-22). The datasets take
   the colours §6 describes. Lower rows are drawn over higher ones. A line is 2 px, as the pattern chart's measured
   line, narrowing toward 1 px where neighbouring rows are closer than six pixels so a dense scan's lines never merge;
   the shown dataset is marked by the selected-pattern line (§8), not by a wider curve (the owner, 2026-10-22).
5. **Map.** Each pixel column takes the colour of its highest value, or, with no more points than columns, of the
   line joining the points at the column's centre. Up, each dataset is one band, out to halfway to its neighbouring
   rows, drawn from that dataset only and empty where it has no point. A toolbar toggle chooses stepped colour, the
   bands' edges hard, or smooth, the default, where a band blends into its neighbour's only in a zone a quarter of the
   way between the two rows either side of their edge, and never into or out of a column either leaves empty, so no
   band shows a neighbour's data. The rule is the same for scan values, files and datablocks (the owner, 2026-10-22):
   the first build blended from one row's centre to the next, which invented patterns between a sparse scan's rows
   (three files at 52, 299 and 497 K blended over about 250 K each) and filled half of a WISH bank's band with its
   neighbour's values where the bank had no data. Beyond the first and the last row, out to their extent, the colour
   is that dataset's. Either way the map is one image of the plot's own pixels, so no line shows between datasets: the
   first build drew each dataset as its own antialiased image rectangle with fractional edges, and every boundary
   pixel row, covered twice in part, let the background show through as a thin light line.
   A colour bar at the right is drawn through the same lookup as the map, and labelled with the intensities its ends
   stand for, each label centred on its end.
6. **Colours** (the owner, 2026-10-22). The Stacked and Map colours are chosen in the app's Preferences with the
   structures' and patterns' (ADR-0038 §3); the Map keeps a box on its toolbar for the same setting, beside its
   reverse and stepped or smooth switches. The colours stand in a toolbar group of their own: on the
   Map its colour box and a reverse button, on Stacked a reverse button alone that runs the Stacked colours the other
   way, each remembered with its colour setting (the owner, 2026-10-22). The Map lists the ramps below first, then the colour maps, and takes Edi Natural's
   ramp by default, for now (the owner, 2026-10-22); the Stacked view
   offers no ramp, as one colour's shades make neighbouring lines hard to tell apart (the owner, 2026-10-22). The
   choices: the colour maps viridis, magma, inferno and plasma (Smith, van der Walt and Firing; CC0; `data/colormaps` with their
   provenance), all perceptually uniform, reading in grey and to the common colour-vision deficiencies, and in either
   app theme; and for each colour scheme a ramp from the pattern chart's plot background in the current theme to the
   scheme's first measured colour, mixed in Oklab (ADR-0038's gradients). The Stacked view also offers the five
   schemes' own colours (ADR-0038: by place, a gradient past five), its default the app's scheme. A pattern on the
   Stacked view takes a map's colour at its place along the scan between a tenth and nine tenths of the map, so no line
   takes the background's colour. cividis and turbo were left out: their
   tables come under other licences, and turbo is not perceptually uniform. On the owner's asking for more pleasing maps
   than matplotlib's (2026-10-22), candidates were added for the owner to choose from, each with its source table and
   licence (`data/colormaps/PROVENANCE.md`, DEPENDENCIES.md): six of Fabio Crameri's Scientific colour maps, five
   of cmocean's, Google's Turbo, three ColorBrewer schemes and three of Peter Kovesi's CET maps; the ones not chosen
   are removed with their rows. On the owner's asking for maps with a light low end for the light theme, cmocean's
   tempo, ColorBrewer's Blues, Purples and YlOrRd and CET L17 and L18 joined them, and the Map's toolbar gained a
   reverse switch, remembered with the other settings, that runs any map the other way; the colour key follows it.
7. **Axes and toolbar.** Each view has a toolbar line above its plot, as the Pattern tab has (the owner,
   2026-10-22): the axes' types, the Map's colours, the zoom and the reset. Every axis type is one setting with each other
   selector of the same quantity: x is the project's own (2θ or TOF, or d-spacing read off the template's current d
   column through its own axis, the pattern chart's rule, ADR-0017 §15; a joint fit's experiment by its own d column,
   d offered once every experiment has one; a joint fit's experiments on different native axes, 2θ beside TOF, are
   shown on d only, since no one native scale holds them, and wait for a calculation to give it; the owner,
   2026-10-22, confirmed every joint fit and every axis the user picks), y places the rows by the scan value or the
   datasets in order (by file or by datablock) as the Evolution tab's x does, and the intensity scale (linear, square root or log; the Map's z) is the
   pattern chart's y scale. Intensity is spread over the scan's lowest to highest value on that scale, so a weak peak
   can be seen on the map as on the pattern. The box zoom is always on: a drag over the plot zooms to its box, and the
   reset, a secondary click (a touchpad's two-finger click, as on the pattern chart), another scan, another x axis or
   another row placing returns to the whole range. The plot starts below the toolbar, so nothing is cut at the top;
   when the chart is too narrow for one toolbar line, the buttons take a second line, each line centred as the
   pattern chart's. An axis box names its choice as its list does (`x: d-spacing` for the list's `d-spacing`; the owner, 2026-10-22),
   on the pattern chart too, and d can be chosen only once a calculation has given a current d column: until then
   the box is off and shows the axis drawn. The excluded regions are marked as the pattern chart marks them (ADR-0021 §4): its grey tint under the Stacked
   patterns, a wash towards the plot's background over the Map's colours, each on whole pixels so two rows' bands meet
   without a line. A scan's datasets share the template's regions, so its bands run the plot's height; a joint fit's
   experiment's run over its own row. The pattern chart's eraser button, *Show only the included range*, is on these
   toolbars too, with the same app setting, so the three charts switch together (the owner, 2026-10-22; the setting is
   `Charts/includedOnly`): on, x runs from the first to the last point
   outside every excluded region and the points inside them are not drawn, which leaves their tint as empty gaps, the
   pattern chart's tint on the Map too; off, the full range with the marks. The colours and the Map's switches are app
   settings (ADR-0031 §7, `ScanViews`, with the Map's smooth or stepped choice).
   The x axis takes as many ticks as its widest label leaves room for, so long values such as TOF never run into
   each other. Every axis's tick labels and titles, and the colour bar's, take the app's label font and size, as the pattern
   chart's axes do; the Evolution tab's tick labels too (the owner, 2026-10-22).
8. **Following a running scan.** The shown dataset is marked at all times by an open rectangle across the plot (the
   owner, 2026-10-22): its border is the Evolution tab's selected-pattern line at 1 px, black in the light theme and
   white in the dark, with a 1 px half-transparent line of the opposite colour just outside and another just inside,
   so it shows on the background and on every colour of every map. On the map it encloses the dataset's band, halfway
   to each neighbouring row; on the stacked view it encloses the dataset's line from its row up to its highest point
   in the range shown; never thinner than 8 px, so its lines and an empty inside always show: a thinner band, in a
   dense part of a scan, takes 8 px centred on the dataset's row (the owner, 2026-10-22); it moves when the rows are placed again (by
   scan value once every dataset is read). The shown dataset is the one the Pattern tab shows: with Follow on, a
   running scan moves it to each dataset as it is fitted, so the mark moves along the scan. The patterns themselves are the measured data, so they do not change while the scan runs. A click on a row
   shows that dataset, here and on the Pattern tab.

## Consequences

- Each dataset costs 24 bytes per measured point in these views (x, intensity and x on the axis shown, in double
  precision): about 12 MB for 162 datasets of 3 000 points, 120 MB for 500 of 10 000.
- Drawing reduces every dataset again, one pass over its points, so a redraw costs time in proportion to the scan's
  points.
- The views show measured data only. Calculated patterns of a finished scan are not read back for them.
- Both views draw from the same reads; opening the second costs nothing more.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| Each pattern as its own chart series | Rejected: hundreds of series made the chart slow. |
| Keeping 1024 columns of the whole range per dataset | Replaced (the owner, 2026-10-22): a zoomed view showed the columns as steps, not the measured points. |
| A rainbow (jet) colour map | Rejected: not perceptually uniform; it shows edges the data do not have and fails in grey. |
| Rows at equal heights, labelled with the scan value | Rejected while every dataset has a value: unequal steps along the scan would read as equal. |
| Reading the calculated patterns too | Deferred: a finished scan does not keep them, and recalculating each would cost a calculation per dataset. |
