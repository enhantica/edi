<!-- scan-example -->
<!-- /scan-example -->

## Choose a dataset

On **Experiment**, use the selector above the pattern or the **Experiments** table to select a measurement. The selector supports searching in a long series.

Before fitting, the pattern uses the template settings. After fitting, selecting a dataset shows its fitted values and updates the relevant structure values too.

## Choose the starting-point rule

On **Analysis → Extra**, expand **Fitting mode**. **Sequential** starts each dataset from the preceding result; **Independent** starts each from the same template. **Single** fits only the shown dataset and makes that result the new template.

Check the template before running the full series. See [fitting modes](../../analysis/fitting-mode.md) for the starting-state rules.

## Inspect the scan declaration

Expand **Sequential fit** and **Scan extraction rules** on the same tab. Inspect the data directory, file pattern, order and rules used to extract values such as temperature from the measurement files. These groups show the saved scan declaration.

## Run, stop and continue

Press **Fit** at the right of the status bar, on any page, and follow the dataset counts beside it. While a run is under way the button reads **Stop**; stopping keeps the completed results. It then reads **Continue**, which resumes from the first unfitted file, or **Refit** after a change to the template, which fits every file again. **Reset**, next to it, clears every dataset's result for another run, and **Undo** restores the preceding results.

**Follow**, also in the status bar, displays the dataset currently being fitted. Selecting another dataset turns it off; select Follow again to follow progress. [Display and updates](../../analysis/parameters-shown.md) controls redraw frequency.

## Inspect the scan views

Use **Stacked** to compare the patterns one above another or **Map** to inspect intensity across the series as rows of colour. On Stacked, **Spacing** runs from **Overlay**, every pattern on one baseline, through **Close**, **Medium** and **Wide**, the default, to **Separate**, each pattern in its own band. Its legend, turned on from the toolbar, lists the files; click an entry to hide that pattern. On Map, choose the colour map, **Blue-Red** by default or **Viridis**, **Batlow**, **Inferno**, **Lapaz** or **Greys**, and its **Direction**: **Auto**, **Normal** or **Inverted**. **Subtract background** draws each pattern less the project's background, here and on the pattern chart. **Evolution** plots a fitted parameter with its uncertainty against a selected dataset value or its place in the scan. Select a point to inspect that dataset elsewhere in the app.

**Correlations** shows the selected dataset's last fit. Only the template dataset's correlations are retained when saving and reopening the project. After editing the template, earlier results remain visible but are marked out of date until refitted.

## Save the scan

Use **Save project as…** to keep the example together with its data and results. The run writes a row per dataset to `analysis/results.csv` as it progresses. Inspect the scan's report on **Report** and choose [which sections to export](../../report/index.md).
