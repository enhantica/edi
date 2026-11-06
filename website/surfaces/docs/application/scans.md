---
template: gui.html
---

# :fa5-calculator: Work with a scan

A scan uses one template experiment for an ordered series of measurements. Open a scan from **Project → Main → Examples** to explore its datasets and results.

<!-- scan-example -->
This example is **pd-neut-cwl_cosio-d20_scan**: Co₂SiO₄ [Pnma], D20 @ ILL.
<!-- /scan-example -->

## Choose a dataset

On **Experiment**, use the selector above the pattern or the **Experiments** table to select a measurement. The selector supports searching in a long series.

Before fitting, the pattern uses the template settings. After fitting, selecting a dataset shows its fitted values and updates the relevant structure values too.

<!-- gui-guide:choose-a-dataset -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-experiment-before.png?v=9fc8afcf68b7" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-scan-experiment-before-overview-scans-choose-a-dataset-0-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-experiment-before.png?v=9fc8afcf68b7" width="1480" height="800" clip-path="url(#gui-clip-scan-experiment-before-overview-scans-choose-a-dataset-0-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-experiment-before-overview-scans-choose-a-dataset-0-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#62992;</span>Experiments (155)"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select an experiment or dataset.</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-experiment-before.png?v=9fc8afcf68b7" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Experiments (155)"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Experiments (155)"><title>Experiments (155)</title><defs><clipPath id="gui-clip-scan-experiment-before-overview-scans-choose-a-dataset-0-group-experiments"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-experiment-before.png?v=9fc8afcf68b7" width="1480" height="800" clip-path="url(#gui-clip-scan-experiment-before-overview-scans-choose-a-dataset-0-group-experiments)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-experiment-before-overview-scans-choose-a-dataset-0-group-experiments-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,509.5]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 630.500 L768.000 630.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Choose the starting-point rule

On **Analysis → Extra**, expand **Fitting mode**. **Sequential** starts each dataset from the preceding result; **Independent** starts each from the same template. **Single** fits only the shown dataset and makes that result the new template.

Check the template before running the full series. See [fitting modes](fitting-modes.md) for the starting-state rules.

<!-- gui-guide:choose-the-starting-point-rule -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose sequential, independent or single-dataset fitting.</p>
<a class="gui-image-link" href="../assets/gui/scan/scan-mode.png?v=3dae24f71fee" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-scan-mode-overview-scans-choose-the-starting-point-rule-0-group-fitting_mode"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-mode.png?v=3dae24f71fee" width="1480" height="800" clip-path="url(#gui-clip-scan-mode-overview-scans-choose-the-starting-point-rule-0-group-fitting_mode)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-mode-overview-scans-choose-the-starting-point-rule-0-group-fitting_mode-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M768.000 159.000 L1482.000 159.000 L1482.000 282.000 L768.000 282.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Inspect the scan declaration

Expand **Sequential fit** and **Scan extraction rules** on the same tab. Inspect the data directory, file pattern, order and rules used to extract values such as temperature from the measurement files. These groups show the saved scan declaration.

<!-- gui-guide:inspect-the-scan-declaration -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61643;</span>Sequential fit"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the scan&#x27;s data directory, file pattern and order</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-declaration.png?v=0e3cb321fe87" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan&#x27;s data directory, file pattern and order"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan&#x27;s data directory, file pattern and order"><title>Inspect the scan&#x27;s data directory, file pattern and order</title><defs><clipPath id="gui-clip-scan-declaration-overview-scans-inspect-the-scan-declaration-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-declaration.png?v=0e3cb321fe87" width="1480" height="800" clip-path="url(#gui-clip-scan-declaration-overview-scans-inspect-the-scan-declaration-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-declaration-overview-scans-inspect-the-scan-declaration-0-1" data-gui-area="sidebar" data-gui-parts="[[770,287,710,119]]" d="M768.000 285.000 L1482.000 285.000 L1482.000 408.000 L768.000 408.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61616;</span>Scan extraction rules"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect values extracted from each dataset</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-extraction.png?v=60a8f9d1aa76" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect values extracted from each dataset"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect values extracted from each dataset"><title>Inspect values extracted from each dataset</title><defs><clipPath id="gui-clip-scan-extraction-overview-scans-inspect-the-scan-declaration-1"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-extraction.png?v=60a8f9d1aa76" width="1480" height="800" clip-path="url(#gui-clip-scan-extraction-overview-scans-inspect-the-scan-declaration-1)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-extraction-overview-scans-inspect-the-scan-declaration-1-1" data-gui-area="sidebar" data-gui-parts="[[770,329,710,141]]" d="M768.000 327.000 L1482.000 327.000 L1482.000 472.000 L768.000 472.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Run, stop and continue

Press **Fit** at the right of the status bar, on any page, and follow the dataset counts beside it. While a run is under way the button reads **Stop**; stopping keeps the completed results. It then reads **Continue**, which resumes from the first unfitted file, or **Refit** after a change to the template, which fits every file again. **Reset**, next to it, clears every dataset's result for another run, and **Undo** restores the preceding results.

**Follow**, also in the status bar, displays the dataset currently being fitted. Selecting another dataset turns it off; select Follow again to follow progress. [Display and updates](display.md) controls redraw frequency.

<!-- gui-guide:run-stop-and-continue -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
<a class="gui-image-link" href="../assets/gui/scan/scan-progress-controls.png?v=9364c00b0afd" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-scan-progress-controls-overview-scans-run-stop-and-continue-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-progress-controls.png?v=9364c00b0afd" width="1480" height="800" clip-path="url(#gui-clip-scan-progress-controls-overview-scans-run-stop-and-continue-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-progress-controls-overview-scans-run-stop-and-continue-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M-2.000 756.000 L1482.000 756.000 L1482.000 802.000 L-2.000 802.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Inspect the scan views

Use **Stacked** to compare the patterns one above another or **Map** to inspect intensity across the series as rows of colour. On Stacked, **Spacing** runs from **Overlay**, every pattern on one baseline, through **Close**, **Medium** and **Wide**, the default, to **Separate**, each pattern in its own band. Its legend, turned on from the toolbar, lists the files; click an entry to hide that pattern. On Map, choose the colour map, **Blue-Red** by default or **Viridis**, **Batlow**, **Inferno**, **Lapaz** or **Greys**, and its **Direction**: **Auto**, **Normal** or **Inverted**. **Subtract background** draws each pattern less the project's background, here and on the pattern chart. **Evolution** plots a fitted parameter with its uncertainty against a selected dataset value or its place in the scan. Select a point to inspect that dataset elsewhere in the app.

**Correlations** shows the selected dataset's last fit. Only the template dataset's correlations are retained when saving and reopening the project. After editing the template, earlier results remain visible but are marked out of date until refitted.

<!-- gui-guide:inspect-the-scan-views -->
<div class="gui-viewer" markdown="1">


=== "Stacked"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the scan in the stacked view</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-analysis-stacked.png?v=a6e69c670050" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan in the stacked view"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan in the stacked view"><title>Inspect the scan in the stacked view</title><defs><clipPath id="gui-clip-scan-analysis-stacked-overview-scans-inspect-the-scan-views-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-analysis-stacked.png?v=a6e69c670050" width="1480" height="800" clip-path="url(#gui-clip-scan-analysis-stacked-overview-scans-inspect-the-scan-views-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-analysis-stacked-overview-scans-inspect-the-scan-views-0-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Map"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the scan in the map view</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-analysis-map.png?v=c831ef7dabf4" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan in the map view"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan in the map view"><title>Inspect the scan in the map view</title><defs><clipPath id="gui-clip-scan-analysis-map-overview-scans-inspect-the-scan-views-1"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-analysis-map.png?v=c831ef7dabf4" width="1480" height="800" clip-path="url(#gui-clip-scan-analysis-map-overview-scans-inspect-the-scan-views-1)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-analysis-map-overview-scans-inspect-the-scan-views-1-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Evolution"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect a fitted parameter across the scan</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-evolution.png?v=229c84be6799" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect a fitted parameter across the scan"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect a fitted parameter across the scan"><title>Inspect a fitted parameter across the scan</title><defs><clipPath id="gui-clip-scan-evolution-overview-scans-inspect-the-scan-views-2"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-evolution.png?v=229c84be6799" width="1480" height="800" clip-path="url(#gui-clip-scan-evolution-overview-scans-inspect-the-scan-views-2)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-evolution-overview-scans-inspect-the-scan-views-2-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Correlations"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect correlations for the selected measurement</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-correlations.png?v=ec364d5e279f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect correlations for the selected measurement"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect correlations for the selected measurement"><title>Inspect correlations for the selected measurement</title><defs><clipPath id="gui-clip-scan-correlations-overview-scans-inspect-the-scan-views-3"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-correlations.png?v=ec364d5e279f" width="1480" height="800" clip-path="url(#gui-clip-scan-correlations-overview-scans-inspect-the-scan-views-3)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-correlations-overview-scans-inspect-the-scan-views-3-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Save the scan

Use **Save project as…** to keep the example together with its data and results. The run writes a row per dataset to `analysis/results.csv` as it progresses. Inspect the scan's report on **Report** and choose [which sections to export](reports.md).

<!-- gui-guide:save-the-scan -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the report view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-report-basic.png?v=e4948f6eef6a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-scan-report-basic-overview-scans-save-the-scan-0-workflow-report-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-report-basic.png?v=e4948f6eef6a" width="1480" height="800" clip-path="url(#gui-clip-scan-report-basic-overview-scans-save-the-scan-0-workflow-report-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-report-basic-overview-scans-save-the-scan-0-workflow-report-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-report-basic.png?v=e4948f6eef6a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-scan-report-basic-overview-scans-save-the-scan-0-workflow-report-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-report-basic.png?v=e4948f6eef6a" width="1480" height="800" clip-path="url(#gui-clip-scan-report-basic-overview-scans-save-the-scan-0-workflow-report-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-report-basic-overview-scans-save-the-scan-0-workflow-report-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
