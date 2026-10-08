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

## Examples and saving

A bundled example opens as a temporary copy, so a run never writes into the bundle. **Save As**
writes the project with its data and its `results.csv`.
