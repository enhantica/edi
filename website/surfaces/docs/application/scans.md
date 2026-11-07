---
template: gui.html
---

# :fa5-calculator: Work with a scan

A scan uses one template experiment for an ordered series of measurements. Open a scan from **Project → Main → Examples** to explore its datasets and results.

<!-- scan-example -->
This example is **pd-neut-cwl_cosio-d20_scan-213f**: Co₂SiO₄ [Pnma.1], D20 @ ILL.
<!-- /scan-example -->

## Choose a dataset

On **Experiment**, use the selector above the pattern or the **Experiments** table to select a measurement. The selector supports searching in a long series.

Before fitting, the pattern uses the template settings. After fitting, selecting a dataset shows its fitted values and updates the relevant structure values too.

<!-- gui-guide:choose-a-dataset -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-experiment-before.png?v=615db9aa89a5" data-gui-dark="e8ce2449c273" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-scan-experiment-before-overview-scans-choose-a-dataset-0-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-experiment-before.png?v=615db9aa89a5" data-gui-dark="e8ce2449c273" width="1480" height="800" clip-path="url(#gui-clip-scan-experiment-before-overview-scans-choose-a-dataset-0-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-experiment-before-overview-scans-choose-a-dataset-0-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#62992;</span>Experiments (213)"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select an experiment or dataset.</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-experiment-before.png?v=615db9aa89a5" data-gui-dark="e8ce2449c273" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Experiments (213)"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Experiments (213)"><title>Experiments (213)</title><defs><clipPath id="gui-clip-scan-experiment-before-overview-scans-choose-a-dataset-0-group-experiments"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-experiment-before.png?v=615db9aa89a5" data-gui-dark="e8ce2449c273" width="1480" height="800" clip-path="url(#gui-clip-scan-experiment-before-overview-scans-choose-a-dataset-0-group-experiments)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-experiment-before-overview-scans-choose-a-dataset-0-group-experiments-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,509.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 623.500 Q1479.000 627.500 1475.000 627.500 L775.000 627.500 Q771.000 627.500 771.000 623.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Choose the starting-point rule

On **Analysis → Extra**, expand **Fitting mode**. **Sequential** starts each dataset from the preceding result; **Independent** starts each from the same template. **Single** fits only the shown dataset and makes that result the new template.

Check the template before running the full series. See [fitting modes](analysis/fitting-mode.md) for the starting-state rules.

<!-- gui-guide:choose-the-starting-point-rule -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose sequential, independent or single-dataset fitting.</p>
<a class="gui-image-link" href="../assets/gui/scan/scan-mode.png?v=f74f205d9807" data-gui-dark="ca404d6a2e13" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-scan-mode-overview-scans-choose-the-starting-point-rule-0-group-fitting_mode"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-mode.png?v=f74f205d9807" data-gui-dark="ca404d6a2e13" width="1480" height="800" clip-path="url(#gui-clip-scan-mode-overview-scans-choose-the-starting-point-rule-0-group-fitting_mode)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-mode-overview-scans-choose-the-starting-point-rule-0-group-fitting_mode-1" data-gui-area="sidebar" data-gui-parts="[[770,161.00000000000693,710,119]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 275.000 Q1479.000 279.000 1475.000 279.000 L775.000 279.000 Q771.000 279.000 771.000 275.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

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
    <a class="gui-image-link" href="../assets/gui/scan/scan-declaration.png?v=f12cc46ad7bd" data-gui-dark="0bfecb7c6c7f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan&#x27;s data directory, file pattern and order"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan&#x27;s data directory, file pattern and order"><title>Inspect the scan&#x27;s data directory, file pattern and order</title><defs><clipPath id="gui-clip-scan-declaration-overview-scans-inspect-the-scan-declaration-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-declaration.png?v=f12cc46ad7bd" data-gui-dark="0bfecb7c6c7f" width="1480" height="800" clip-path="url(#gui-clip-scan-declaration-overview-scans-inspect-the-scan-declaration-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-declaration-overview-scans-inspect-the-scan-declaration-0-1" data-gui-area="sidebar" data-gui-parts="[[770,287,710,119]]" d="M771.000 292.000 Q771.000 288.000 775.000 288.000 L1475.000 288.000 Q1479.000 288.000 1479.000 292.000 L1479.000 401.000 Q1479.000 405.000 1475.000 405.000 L775.000 405.000 Q771.000 405.000 771.000 401.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61616;</span>Scan extraction rules"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect values extracted from each dataset</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-extraction.png?v=b2149528519a" data-gui-dark="8c0987901cfd" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect values extracted from each dataset"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect values extracted from each dataset"><title>Inspect values extracted from each dataset</title><defs><clipPath id="gui-clip-scan-extraction-overview-scans-inspect-the-scan-declaration-1"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-extraction.png?v=b2149528519a" data-gui-dark="8c0987901cfd" width="1480" height="800" clip-path="url(#gui-clip-scan-extraction-overview-scans-inspect-the-scan-declaration-1)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-extraction-overview-scans-inspect-the-scan-declaration-1-1" data-gui-area="sidebar" data-gui-parts="[[770,329.00000000000244,710,141]]" d="M771.000 334.000 Q771.000 330.000 775.000 330.000 L1475.000 330.000 Q1479.000 330.000 1479.000 334.000 L1479.000 465.000 Q1479.000 469.000 1475.000 469.000 L775.000 469.000 Q771.000 469.000 771.000 465.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Run, stop and continue

Press **Fit** at the right of the status bar, on any page, and follow the dataset counts beside it. While a run is under way the button reads **Stop**; stopping keeps the completed results. It then reads **Continue**, which resumes from the first unfitted file, or **Refit** after a change to the template, which fits every file again. **Reset**, next to it, clears every dataset's result for another run, and **Undo** restores the preceding results.

**Follow**, also in the status bar, displays the dataset currently being fitted. Selecting another dataset turns it off; select Follow again to follow progress. [Display and updates](analysis/parameters-shown.md) controls redraw frequency.

<!-- gui-guide:run-stop-and-continue -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
<a class="gui-image-link" href="../assets/gui/scan/scan-progress-controls.png?v=2d671f86d8ef" data-gui-dark="b1eac4b4625c" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-scan-progress-controls-overview-scans-run-stop-and-continue-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-progress-controls.png?v=2d671f86d8ef" data-gui-dark="b1eac4b4625c" width="1480" height="800" clip-path="url(#gui-clip-scan-progress-controls-overview-scans-run-stop-and-continue-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-progress-controls-overview-scans-run-stop-and-continue-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M1.000 763.000 Q1.000 759.000 5.000 759.000 L1475.000 759.000 Q1479.000 759.000 1479.000 763.000 L1479.000 795.000 Q1479.000 799.000 1475.000 799.000 L5.000 799.000 Q1.000 799.000 1.000 795.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

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
    <a class="gui-image-link" href="../assets/gui/scan/scan-analysis-stacked.png?v=7807270ee52c" data-gui-dark="33e1a3d7df65" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan in the stacked view"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan in the stacked view"><title>Inspect the scan in the stacked view</title><defs><clipPath id="gui-clip-scan-analysis-stacked-overview-scans-inspect-the-scan-views-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-analysis-stacked.png?v=7807270ee52c" data-gui-dark="33e1a3d7df65" width="1480" height="800" clip-path="url(#gui-clip-scan-analysis-stacked-overview-scans-inspect-the-scan-views-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-analysis-stacked-overview-scans-inspect-the-scan-views-0-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Map"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the scan in the map view</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-analysis-map.png?v=84cb2ae0dfd7" data-gui-dark="dab89b3c0b6c" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan in the map view"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan in the map view"><title>Inspect the scan in the map view</title><defs><clipPath id="gui-clip-scan-analysis-map-overview-scans-inspect-the-scan-views-1"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-analysis-map.png?v=84cb2ae0dfd7" data-gui-dark="dab89b3c0b6c" width="1480" height="800" clip-path="url(#gui-clip-scan-analysis-map-overview-scans-inspect-the-scan-views-1)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-analysis-map-overview-scans-inspect-the-scan-views-1-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Evolution"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect a fitted parameter across the scan</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-evolution.png?v=0ea137e35090" data-gui-dark="103ed08c8ed6" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect a fitted parameter across the scan"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect a fitted parameter across the scan"><title>Inspect a fitted parameter across the scan</title><defs><clipPath id="gui-clip-scan-evolution-overview-scans-inspect-the-scan-views-2"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-evolution.png?v=0ea137e35090" data-gui-dark="103ed08c8ed6" width="1480" height="800" clip-path="url(#gui-clip-scan-evolution-overview-scans-inspect-the-scan-views-2)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-evolution-overview-scans-inspect-the-scan-views-2-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Correlations"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect correlations for the selected measurement</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-correlations.png?v=497b8d414a71" data-gui-dark="d3fde2941290" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect correlations for the selected measurement"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect correlations for the selected measurement"><title>Inspect correlations for the selected measurement</title><defs><clipPath id="gui-clip-scan-correlations-overview-scans-inspect-the-scan-views-3"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-correlations.png?v=497b8d414a71" data-gui-dark="d3fde2941290" width="1480" height="800" clip-path="url(#gui-clip-scan-correlations-overview-scans-inspect-the-scan-views-3)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-correlations-overview-scans-inspect-the-scan-views-3-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Save the scan

Use **Save project as…** to keep the example together with its data and results. The run writes a row per dataset to `analysis/results.csv` as it progresses. Inspect the scan's report on **Report** and choose [which sections to export](report/index.md).

<!-- gui-guide:save-the-scan -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the report view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-report-basic.png?v=51c45961f4ea" data-gui-dark="7fe9a8e12ad4" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-scan-report-basic-overview-scans-save-the-scan-0-workflow-report-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-report-basic.png?v=51c45961f4ea" data-gui-dark="7fe9a8e12ad4" width="1480" height="800" clip-path="url(#gui-clip-scan-report-basic-overview-scans-save-the-scan-0-workflow-report-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-report-basic-overview-scans-save-the-scan-0-workflow-report-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/scan/scan-report-basic.png?v=51c45961f4ea" data-gui-dark="7fe9a8e12ad4" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-scan-report-basic-overview-scans-save-the-scan-0-workflow-report-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-report-basic.png?v=51c45961f4ea" data-gui-dark="7fe9a8e12ad4" width="1480" height="800" clip-path="url(#gui-clip-scan-report-basic-overview-scans-save-the-scan-0-workflow-report-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-report-basic-overview-scans-save-the-scan-0-workflow-report-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M771.000 124.000 Q771.000 120.000 771.000 116.000 L771.000 82.000 Q771.000 78.000 775.000 78.000 L808.516 78.000 Q812.516 78.000 812.516 82.000 L812.516 116.000 Q812.516 120.000 816.516 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 753.000 Q1479.000 757.000 1475.000 757.000 L775.000 757.000 Q771.000 757.000 771.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
