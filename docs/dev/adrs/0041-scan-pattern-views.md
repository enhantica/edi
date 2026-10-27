# 0041. Stacked patterns and a 2D map for a sequential fit

- **Status:** Accepted
- **Date:** 2026-10-22, amended 2026-10-26 (one spacing selector, Map colour maps and direction, toolbar groups) and
  2026-10-27 (selection colours, read-outs, legend clicks, the dark Map, selector capitals)
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
4. **Stacked.** Each dataset is drawn as a line rising from its baseline, joining its points, or, with more than four
   points to a device pixel column, each column's first, lowest, highest and last point in their order, so a narrow
   peak keeps its height (§9). The vertical axis is the plot's height H, 0 to 1, and one toolbar box, *spacing*, places
   the patterns on it (the owner, 2026-10-26), changing them linearly from overlaid to fully separated: Overlay, Close,
   Medium, Wide and Separate, s = 0, 0.25, 0.5, 0.75 and 1. For N patterns each is h = H (1 − s) + (H / N) s tall and
   the i-th from the bottom has its baseline at i s H / N, so the stack always fills the plot: Overlay puts every
   baseline on one line at the plot's full height, Separate gives each pattern its own band H / N tall
   (`edi::stacked_placement`). Wide is the default for any number of patterns. A project keeps its step (ADR-0031 §1,
   in the app's settings keyed by its folder), so it reopens at the step it was left at. The rule replaces the
   offset and height boxes of 2026-10-24, whose 10 % offset already shrank each of 162 patterns to a sliver. Each
   pattern spans its own lowest to highest value, so every pattern has the same height; at Separate it spans its values
   in the x range shown, so a zoom that leaves large peaks out still fills each band and no two patterns overlap. Its rows are labelled (§2),
   not scaled. The datasets take the colours §6 describes. Lower rows are drawn over higher ones. A line is 2 px, as
   the pattern chart's measured line, narrowing toward 1 px where neighbouring rows are closer than six pixels so a
   dense scan's lines never merge. One placement serves the lines, the labels, the row ticks, the clicks and the
   excluded regions' tint.
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
   stand for, each label centred on its end, in scientific notation with two significant digits (`1.4e4`; the owner,
   2026-10-27). With only the included range shown, the intensity range, of the Map's colours and of every Stacked
   pattern at every spacing, comes from the included points only, and showing the excluded ones again restores it.
6. **Colours** (the owner, 2026-10-26). The Stacked lines take the app's figure palette (ADR-0038), each dataset the
   colour at the position of its place in the scan, or, with more datasets than the palette has colours, only its first
   two colours, from colour 1 at the first dataset to colour 2 at the last through Oklab shades (`edi::pattern_set_colour`,
   the owner, 2026-10-27); or a palette or colour map chosen in Preferences; a pattern on a
   colour map takes the map's colour at its place along the scan between a tenth and nine tenths of the map, so no
   line takes the background's colour, and a reverse button runs the Stacked colours the other way. The Map takes one
   of six colour maps, in this order: **Blue-Red** (the default), Viridis, Batlow, Inferno, Lapaz and Greys
   (`data/colormaps/PROVENANCE.md`), chosen on its toolbar and in Preferences. In the dark theme the Map's plot area is
   black, the rest of the chart its usual background, so low values stand apart from empty areas as on white in the
   light theme (the owner, 2026-10-27). Blue-Red runs from just off the plot area through blue to red, mixed in Oklab:
   `#FFFFFF`, `#3F7FBF`, `#C8323C` in the light theme and `#181818`, `#6AA6EA`, `#FC4F81` in the dark. The maps are named as the app shows them, capitalised, and the colour-map box draws each
   map's colour bar beside its name, in its list and for the current choice. A name means one set of colours in one
   order, low to high; a *direction* box beside it chooses which end takes the low values: **Auto** (the default) puts
   the end nearer the plot area's colour, by distance in Oklab, at the low values, so a map starts light in the light
   theme and dark in the dark theme and follows a theme switch; Normal runs the map as named; Inverted the other way
   (`edi::scan_map_inverted`). The bars and the colour key follow the direction. A project keeps its direction choice,
   never the direction Auto resolved to; an export resolves Auto as in the light theme (ADR-0038 §6). The earlier
   choices (matplotlib's magma and plasma, the other candidates and each palette's ramp) are retired; a stored one
   reads as Blue-Red.
7. **Axes and toolbar.** Each view has a toolbar above its plot, laid out by the one rule of every chart (the owner,
   2026-10-24): the boxes and the buttons (the included range, the highlight, the zoom and the reset) on one line
   centred above the plot when they fit. The boxes stand in groups a group's spacing apart (the owner, 2026-10-26): the
   axes' types (x, y and z), then on Stacked the spacing alone, and on the Map the colour map and its direction. A box
   names its value after a lower-case prefix with a capital first (`y: Datablock`, `z: Linear`, `spacing: Separate`),
   unless the value is a symbol whose case matters (`x: 2θ`, `x: d-spacing`, `x: TOF`), on every chart (the owner,
   2026-10-27). Every axis type is one setting with each other
   selector of the same quantity: x is the project's own (2θ or TOF, or d-spacing read off the template's current d
   column through its own axis, the pattern chart's rule, ADR-0017 §15; a joint fit's experiment by its own d column,
   d offered once every experiment has one; a joint fit's experiments on different native axes, 2θ beside TOF, are
   shown on d only, since no one native scale holds them, and wait for a calculation to give it; the owner,
   2026-10-22, confirmed every joint fit and every axis the user picks), y places the rows by the scan value or the
   datasets in order (by file or by datablock) as the Evolution tab's x does, and the intensity scale (linear, square root or log; the Map's z) is the
   pattern chart's y scale. Intensity is spread over the scan's lowest to highest value on that scale, so a weak peak
   can be seen on the map as on the pattern. The box zoom is always on: a drag over the plot zooms to its box, and the
   reset, a secondary click (a touchpad's two-finger click, as on the pattern chart), another scan, another x axis or
   another row placing returns to the whole range. On the Stacked view the wheel scrolls the shown range up and down
   the stack, keeping its height, from the lowest baseline to the highest pattern's top, so a stack taller than the plot
   (a zoomed one) can be read to its last dataset. The plot starts below the toolbar, so nothing is cut at the top;
   when the chart is too narrow for one toolbar line, the buttons take a second line, each line centred as the
   pattern chart's. An axis box names its choice as its list does (`x: d-spacing` for the list's `d-spacing`; the owner, 2026-10-22),
   on the pattern chart too, and d can be chosen only once a calculation has given a current d column: until then
   the box is off and shows the axis drawn. The excluded regions are marked as the pattern chart marks them (ADR-0021 §4): its grey tint under the Stacked
   patterns, a wash towards the plot's background over the Map's colours, each on whole pixels so two rows' bands meet
   without a line. A scan's datasets share the template's regions, so its bands run the plot's height; a joint fit's
   experiment's run over its own row: on the Map its band, on the Stacked view its pattern, from its baseline to its top
   as §4 places it. The pattern chart's eraser button, *Show only the included range*, is on these
   toolbars too, with the same app setting, so the three charts switch together (the owner, 2026-10-22; the setting is
   `Charts/includedOnly`): on, x runs from the first to the last point
   outside every excluded region and the points inside them are not drawn, which leaves their tint as empty gaps, the
   pattern chart's tint on the Map too; off, the full range with the marks. The colours and the Map's switches are app
   settings (ADR-0031 §7, `ScanViews`, with the Map's smooth or stepped choice).
   The x axis takes as many ticks as its widest label leaves room for, so long values such as TOF never run into
   each other. Every axis's tick labels and titles, and the colour bar's, take the app's label font and size, as the pattern
   chart's axes do; the Evolution tab's tick labels too (the owner, 2026-10-22).
8. **The shown dataset and a running scan.** The shown dataset is the one the Pattern tab shows. With *Highlight the
   selected dataset* on, one app setting for every chart of several datasets and on by default (the owner, 2026-10-24),
   it is drawn on top in its colour; on Stacked every other one, its curve, its row name and its legend entry, is drawn
   in the theme's disabled colour (the owner, 2026-10-27), and on the Map every other row's band is blended toward the
   background. Off, every dataset is drawn alike: on Stacked the shown one's name is bold in its own colour on the axis
   and in the legend; on the Map it is bold in the accent colour. A Map placing its rows by value, which names no row,
   marks the shown one by that bold label beside its row, highlighting on or off. The open rectangle that marked it
   before is retired. Hovering a line or band shows a read-out as the pattern chart's, by the hovered Stacked curve or
   at the pointer on the Map: the dataset's icon and name in its colour, then its intensity there (`meas: 1,192.23`).
   The toolbar's read-out button, the pattern chart's, shows or hides it on all three charts (the owner, 2026-10-27).
   A click on a line or band
   shows that dataset, here and on the Pattern tab. With Follow on, a running scan moves the shown dataset to each
   dataset as it is fitted or, with every pattern shown, as it is shown (ADR-0029 §8). The patterns themselves are the
   measured data, so they do not change while the scan runs.
9. **Drawing** (the owner, 2026-10-25; the measurements are in
   [scan view timings](../design/scan-view-timings.md)). The Stacked lines are drawn on the GPU by `ScanLines`, a
   scene-graph item whose shader places each pattern's line at its row and height and draws it antialiased: 64
   patterns to a node, one quad per segment of a reduced trace. A new row placing, height, colour or y range only
   gives the shader new values. Without a GPU the lines are painted with `QPainter` instead, which is faster there:
   a software OpenGL renderer such as Mesa's llvmpipe rasterises every quad on the CPU. The app reads what Qt draws
   with in the first frame it renders (the graphics API and, on OpenGL, the renderer), writes it to stderr at startup
   and shows it in Preferences, Develop, where the user can choose GPU or the painter instead of Automatic; the choice
   is kept per machine. Qt Quick's own software backend cannot run the shader, so there the lines are always painted.
   The Map stays one image of the plot's pixels, made again only when what it shows changes.
   **The lines are drawn as well as the pattern chart's** (the owner, 2026-10-25): the same width, antialiased, with
   no notch or doubled colour where segments meet, at the screen's device pixels. The trace is reduced at device pixel
   columns, not item pixels, so a high-DPI screen gets its full resolution; it follows the points in their order
   (`edi::scan_polyline`) rather than a stroke from each column's lowest to its highest value, which drew stairs. On
   the GPU each segment's quad reaches past both ends by half the width and a device pixel, and the shader gives a
   pixel only to the nearest of the segment and its two neighbours (ties to the earlier), so joins are round and each
   pixel is drawn once along the line; the fringe fades over one device pixel. The painter strokes each pattern as
   one path with round joins, its width in item pixels at any ratio. With the shown dataset highlighted, the other
   lines take the disabled colour, opaque, rather than drawn translucent, so a line crossing itself up and down a
   narrow peak stays one even colour.
   Each dataset's reduction (its trace, or the Map's pixel columns) is kept until its points, the x range, the plot's
   width, the y scale or the included range change: a colour, a reversal or a row placing reduces nothing, and a
   change of the shown dataset draws nothing. The changes of one frame are drawn once, at the frame's polish. A view
   on a page or tab not shown draws nothing, whatever asks for it: a change, a polish or paint already queued when it
   was hidden, a resize or a renderer chosen meanwhile. It notes that it is out of date and draws once, with the
   latest data, when it is shown again, as the pattern chart does (ADR-0017). The two pages' views share their
   datasets, so one change would otherwise be reduced and drawn four times. The row
   labels are kept while the rows are placed again: only a label's text, place and colour follow, and the room they
   take is measured once after their widths change.
10. **Legend and background** (the owner, 2026-10-26). The Stacked toolbar has a legend button, as the pattern chart's,
   off by default (an app setting): a box at the plot's top right lists each dataset's line in its colour and its row's
   text, coloured as the row names are (§8); past fifteen datasets only the first, the shown and the last, then how many
   more there are. A click on an entry hides its pattern or shows it again, as on the pattern chart (the owner,
   2026-10-27). A *subtract background* button, beside the included range on the pattern chart,
   Stacked and the Map and one app setting for all three, off by default, draws every pattern less the project's
   background at each point: its points or terms, fitted or not, as the calculation evaluates them (a scan's datasets
   the template's, linear between its points; a joint fit's experiment its own). A pattern with no background set is
   drawn as it is, and when no shown pattern has one the button is disabled, its tooltip saying why. No background is
   estimated for it. The pattern chart then draws the measured and calculated curves less the background, the
   background at zero and each structure's curve rising from zero; the residual is unchanged.

## Consequences

- Each dataset costs 24 bytes per measured point in these views (x, intensity and x on the axis shown, in double
  precision): about 12 MB for 162 datasets of 3 000 points, 120 MB for 500 of 10 000.
- A new x range, plot width or y scale reduces every dataset again, one pass over its points; nothing else does.
- With a GPU the Stacked view keeps its vertices on the GPU: about 2 million for the 324-file scan, 28 bytes each.
- Without a GPU a painted redraw of the 324-file scan takes about 125 ms here, over the 100 ms a redraw should take.
- The views show measured data only. Calculated patterns of a finished scan are not read back for them.
- Both views draw from the same reads; opening the second costs nothing more.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| Each pattern as its own Qt Graphs series (measured 2026-10-25) | Rejected: Qt Graphs prepares every point of every series on the GUI thread for each frame. A change took about 0.5 s for 324 patterns and 3.8 s for 1 000 on an Apple M2, and about 2 s for 324 without a GPU. How the series are fed makes little difference: on the M2 a whole-list replace from C++ or from QML and an appended list are within 10 % of each other; appending point by point is up to twice as slow; a model mapper on hundreds of series drew no frame within its timeout. A colour change, which feeds no point, still costs most of an update. |
| ScanLines everywhere | Rejected without a GPU: llvmpipe takes 240 to 480 ms per change for the 324-file scan at 1 px, the painter about 125 ms. |
| The painter everywhere | Rejected with a GPU: on an M2 it takes 66 ms per change for 324 patterns and 187 ms for 1 000; ScanLines takes 8 to 36 ms. |
| Keeping 1024 columns of the whole range per dataset | Replaced (the owner, 2026-10-22): a zoomed view showed the columns as steps, not the measured points. |
| A rainbow (jet) colour map | Rejected: not perceptually uniform; it shows edges the data do not have and fails in grey. |
| Rows at equal heights, labelled with the scan value | Rejected while every dataset has a value: unequal steps along the scan would read as equal. |
| Reading the calculated patterns too | Deferred: a finished scan does not keep them, and recalculating each would cost a calculation per dataset. |
