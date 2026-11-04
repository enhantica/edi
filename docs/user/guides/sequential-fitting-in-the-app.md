# Sequential fitting in the app

A scan is a directory of data files measured one after another, for example a diffraction pattern
every few kelvin while a sample cools. The project describes one experiment, the template, and
`_sequential_fit` in `analysis/analysis.edi` names the directory and the files to fit. The app
lists every file of the scan as a dataset of that experiment and fits them one by one with the
same engine as `python -m edi fit`.

The bundled example *pd-neut-cwl_cosio-d20_scan-162f* is a ready scan to try: the cooling run of
Co₂SiO₄ on D20, 162 files from 497 K down to 50 K.

## Datasets

On the Experiment page the Experiments table lists one row per file, in fitting order, with how
the last run ended on it (Fit), its file and the value each extract rule takes from it, such as
the temperature. The selector above the chart lists the same datasets; with more than ten entries
it has a search field, which matches any part of the entry, the temperature included.

Choosing a dataset shows its measured points with the template's settings. Once the scan has
been fitted, it shows that dataset's fitted values from `analysis/results.csv` on the Experiment
and Structure pages, and the pattern calculated from them. A file is read only when it is shown
or fitted.

The Correlations tab shows the chosen dataset's parameter correlations from its last fit. A save
keeps only the template dataset's, so after the project is opened again the other datasets' tabs
say their correlations are kept only for the template.

## Running a scan

Set the fitting mode to `sequential` or `independent` and press **Start fitting** on the Analysis
page. A sequential run starts each file from the previous file's fitted values; an independent
run starts every file from the template. The run writes one row per file to
`analysis/results.csv` as it goes.

While it runs, the status bar shows a bar filled by files, with the count, the percentage and the
last file inside, and beside it the converged and failed counts, the time, the time left and the
last χ². A failed count above zero is red.

**Follow**, next to the fitting button, is on when a run starts: the pattern tab shows each file
as it is fitted. Choosing another dataset turns it off; press it to turn it on again.

How often the pattern is redrawn is set on the Analysis page's Settings tab, under **Pattern
updates during a scan**, and kept on this computer:

- **Adaptive** (the default): the newest fitted file whenever the screen is free, at most twice a
  second. A slow scan shows every file, a fast one skips some.
- **About once a second**: the same, at most once a second.
- **Every pattern, fit waits for the display**: every file is drawn, and the fit waits for each
  drawing. On the Stacked view or the Map, each file in turn becomes the shown dataset. On a slow
  display this makes the run longer.
- **Every pattern, display catches up**: every file is drawn in order, but the fit never waits.
  When the display falls behind, the status bar shows **Showing N of M**, and the remaining files
  are drawn after the run ends.
- **Only at the end**: no pattern while the run fits; the last file is shown when it ends.

The fitting button reads **Start fitting** while no file is fitted and **Continue fitting** while
some are not, for example after **Stop fitting**, which keeps the files fitted so far. Continuing
fits from the first unfitted file. Once every file is fitted the button is disabled. **Reset
fits**, between the fitting button and Follow, clears every file's result so the scan can be
fitted again; it is one Undo step. Undo after a run puts back the results the run replaced.

When the run ends, the results window shows its outcome, the files fitted, the converged and
failed counts and the χ² range, with **Show evolution** to see the results as a chart.

## The template dataset

A single fit (fitting mode `single`) on the shown dataset makes its result the template, and that
dataset the template dataset, saved as `_sequential_fit.template_file`. It carries the word
*template* in the selector and in the table, and the project opens on it. From Python the same is
`project.analysis.template_file = '<file>'`, which takes the file's data and changes no
parameter.

## Evolution

The Analysis page's **Evolution** tab plots one fitted parameter across the datasets, with its
uncertainty, against the extracted value or the file's place in the scan. Choose the parameter in
the selector above the chart. A click on a point shows that dataset everywhere.

After an edit of the template, the old results stay visible and are marked *out of date* in the
status bar and on the Evolution tab until the next run replaces them.

## Stacked and Map

The Analysis page's **Stacked** tab draws every file's pattern above the others, and **Map** draws them as rows of
colour. Their toolbars group the boxes: the axes (x, y and z), then on Stacked the spacing, and on the Map the colour
map and its direction.

- **Spacing** sets how far apart the stacked patterns are: Overlay (every pattern on one baseline, full height),
  Close, Medium, Wide (the default) or Separate (each pattern in its own band). The change is linear from one end to
  the other, so Close already separates the patterns a little without shrinking them much. At Separate each pattern
  fills its band with what the zoom shows, so zooming away from large peaks shows the small ones larger. The project
  remembers the step on this computer.
- **Colour map**: Blue-Red (the default), Viridis, Batlow, Inferno, Lapaz or Greys, each shown with its colour bar.
  In the dark theme the Map's plot area is black. **Direction**: Auto (the default) starts the map at the plot area's
  colour, white in the light theme and black in the dark one, and follows a theme switch; Normal and Inverted fix it.
  The project remembers the choice.
- **Subtract background**, beside the included-range button, here and on the pattern chart: each pattern is drawn
  less the project's background (its points or terms, fitted or not). It is off by default, and disabled when no
  shown pattern has a background.
- **Legend** on Stacked: each file's line and name, or for more than fifteen files the first, the selected one and
  the last with how many more. Click an entry to hide its pattern, and again to show it.
- **Highlight the selected dataset**: on Stacked the selected file keeps its colour and every other one is drawn in
  grey, its curve, name and legend entry alike; off, all keep their colours and the selected name is bold. The Map
  marks the selected row with its label either way.
- **Read-outs**: hovering a pattern or a band shows its name in its colour and the intensity there. The speech-bubble
  button, as on the pattern chart, turns them off and on.

With only the included range shown, the intensity range leaves the excluded points out, on the pattern chart,
Stacked and the Map's colours.

The colours of experiments, structures and Stacked lines come from the **Palette** in Preferences, Appearance:
Earth (the default), Classic, Soft, Natural or Colour-blind safe. Under the choice, the palette's eleven colours show
in the order new blocks take them: a colour the open project uses shows its block's icon, a free one a square, and
the calculated curve's colour, the same in every palette, shows as the calculator icon. Each new experiment or
structure takes the next free colour; in Earth the first two are kept for experiments. A scan with more files than
the palette has colours runs from its first colour to its second. Saved reports and pictures always use the light
theme's colours.

## Examples and saving

A bundled example opens as a temporary copy, so a run never writes into the bundle. **Save As**
writes the project with its data and its `results.csv`.
