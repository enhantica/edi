---
template: gui.html
---

# Sequential magnetic fit: Co₂SiO₄, D20 scan from 2.3 K

The same staged fit as the Python and Command line tutorials, in the app. A scan's patterns come with its project, so open it from EasyDiffraction's collection with **Project → Examples**; each stage frees its parameters in the **Parameters** table on **Analysis** before the fit.

## Open the example

Press **Start** on Home, search **Examples** on **Project** for **pd-neut-cwl_cosio-d20_scan-213f** and open it.


## Fit the template first

On **Analysis → Extra**, set the fitting mode to single, so the stages fit the template pattern alone.


## Set the minimizer

On **Analysis → Extra**, set the **Minimizer** as the case's project does: the **Shift/s.u.** stop rule and room for more iterations.

<figure class="gui-figure gui-placeholder"><div class="gui-placeholder-box">Screenshot coming soon</div></figure>

## Start with nothing free

On **Analysis**, open the **Free** column header of the **Parameters** table and fix every parameter, so the stages below free one group at a time.


## Scale, 2θ zero and cell

Filter the **Linked structures** and **Cell** parameters, one category at a time, using the category filter and the **Instrument** parameters with **calib** in their name using the category filter and the name filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.


## Background

The sixteen background points follow the level between the peaks.

Filter the **Background** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.


## Peak widths

U, V and W only: across a temperature scan the Lorentzian term and the asymmetry stay at their 2.3 K values, as do the form factor's j2 term.

Filter the **Peak broadening** parameters with **gauss** in their name using the category filter and the name filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.


## Atom positions

Filter the **Atomic coordinates** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.


## Displacements

Co2's displacement follows Co1's by the project's constraint.

Filter the **Atomic displacement** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.


## Magnetic moments

Last, the moments: Co1 in any direction, Co2 along b.

Filter the **Magnetic moments** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.


## Fit the scan

Back on **Analysis → Extra**, set the fitting mode to sequential and press **Fit**: every pattern is fitted in turn, each from the fit before it.

<div class="gui-viewer" markdown="1">


=== "Mode"

    
=== "Fitted"

    
</div>

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
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-experiment-before.webp?v=e90ec972f1e0" data-gui-dark="701f4f472517" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-experiment-before.webp?v=e90ec972f1e0" data-gui-dark="701f4f472517" width="1480" height="800" clip-path="url(#gui-clip-scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#62992;</span>Experiments (213)"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select an experiment or dataset.</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-experiment-before.webp?v=e90ec972f1e0" data-gui-dark="701f4f472517" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Experiments (213)"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Experiments (213)"><title>Experiments (213)</title><defs><clipPath id="gui-clip-scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-group-experiments"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-experiment-before.webp?v=e90ec972f1e0" data-gui-dark="701f4f472517" width="1480" height="800" clip-path="url(#gui-clip-scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-group-experiments)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-group-experiments-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,562.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 676.500 Q1479.000 680.500 1475.000 680.500 L775.000 680.500 Q771.000 680.500 771.000 676.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Choose the starting-point rule

On **Analysis → Extra**, expand **Fitting mode**. **Sequential** starts each dataset from the preceding result; **Independent** starts each from the same template. **Single** fits only the shown dataset and makes that result the new template.

Check the template before running the full series. See [fitting modes](../../analysis/fitting-mode.md) for the starting-state rules.

<!-- gui-guide:choose-the-starting-point-rule -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose sequential, independent or single-dataset fitting.</p>
<a class="gui-image-link" href="../../../assets/gui/scan/scan-mode.webp?v=0a2bf7bb231f" data-gui-dark="7b8b8ab43e01" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-scan-mode-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-the-starting-point-rule-0-group-fitting_mode"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-mode.webp?v=0a2bf7bb231f" data-gui-dark="7b8b8ab43e01" width="1480" height="800" clip-path="url(#gui-clip-scan-mode-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-the-starting-point-rule-0-group-fitting_mode)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-mode-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-the-starting-point-rule-0-group-fitting_mode-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 275.000 Q1479.000 279.000 1475.000 279.000 L775.000 279.000 Q771.000 279.000 771.000 275.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

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
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-declaration.webp?v=b6e97a61dc2a" data-gui-dark="c6f2fa3e7105" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan&#x27;s data directory, file pattern and order"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan&#x27;s data directory, file pattern and order"><title>Inspect the scan&#x27;s data directory, file pattern and order</title><defs><clipPath id="gui-clip-scan-declaration-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-declaration.webp?v=b6e97a61dc2a" data-gui-dark="c6f2fa3e7105" width="1480" height="800" clip-path="url(#gui-clip-scan-declaration-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-declaration-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-0-1" data-gui-area="sidebar" data-gui-parts="[[770,287,710,119]]" d="M771.000 292.000 Q771.000 288.000 775.000 288.000 L1475.000 288.000 Q1479.000 288.000 1479.000 292.000 L1479.000 401.000 Q1479.000 405.000 1475.000 405.000 L775.000 405.000 Q771.000 405.000 771.000 401.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61616;</span>Scan extraction rules"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect values extracted from each dataset</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-extraction.webp?v=ef1dde1d52fd" data-gui-dark="6990d26aee89" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect values extracted from each dataset"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect values extracted from each dataset"><title>Inspect values extracted from each dataset</title><defs><clipPath id="gui-clip-scan-extraction-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-1"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-extraction.webp?v=ef1dde1d52fd" data-gui-dark="6990d26aee89" width="1480" height="800" clip-path="url(#gui-clip-scan-extraction-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-1)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-extraction-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-1-1" data-gui-area="sidebar" data-gui-parts="[[770,329,710,141]]" d="M771.000 334.000 Q771.000 330.000 775.000 330.000 L1475.000 330.000 Q1479.000 330.000 1479.000 334.000 L1479.000 465.000 Q1479.000 469.000 1475.000 469.000 L775.000 469.000 Q771.000 469.000 771.000 465.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Run, stop and continue

Press **Fit** at the right of the status bar, on any page, and follow the dataset counts beside it. While a run is under way the button reads **Stop**; stopping keeps the completed results. It then reads **Continue**, which resumes from the first unfitted file, or **Refit** after a change to the template, which fits every file again. **Reset**, next to it, clears every dataset's result for another run, and **Undo** restores the preceding results.

**Follow**, also in the status bar, displays the dataset currently being fitted. Selecting another dataset turns it off; select Follow again to follow progress. [Display and updates](../../analysis/parameters-shown.md) controls redraw frequency.

<!-- gui-guide:run-stop-and-continue -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
<a class="gui-image-link" href="../../../assets/gui/scan/scan-progress-controls.webp?v=b5053bce1378" data-gui-dark="0ee9a99f069f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-scan-progress-controls-overview-pd-neut-cwl_cosio-d20_scan-213f-run-stop-and-continue-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-progress-controls.webp?v=b5053bce1378" data-gui-dark="0ee9a99f069f" width="1480" height="800" clip-path="url(#gui-clip-scan-progress-controls-overview-pd-neut-cwl_cosio-d20_scan-213f-run-stop-and-continue-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-progress-controls-overview-pd-neut-cwl_cosio-d20_scan-213f-run-stop-and-continue-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M1.000 763.000 Q1.000 759.000 5.000 759.000 L1475.000 759.000 Q1479.000 759.000 1479.000 763.000 L1479.000 795.000 Q1479.000 799.000 1475.000 799.000 L5.000 799.000 Q1.000 799.000 1.000 795.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

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
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-analysis-stacked.webp?v=bba9cd8dfc9e" data-gui-dark="71a5420ca65f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan in the stacked view"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan in the stacked view"><title>Inspect the scan in the stacked view</title><defs><clipPath id="gui-clip-scan-analysis-stacked-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-analysis-stacked.webp?v=bba9cd8dfc9e" data-gui-dark="71a5420ca65f" width="1480" height="800" clip-path="url(#gui-clip-scan-analysis-stacked-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-analysis-stacked-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-0-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Map"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the scan in the map view</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-analysis-map.webp?v=f649b540618c" data-gui-dark="0dd8f85f8a48" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan in the map view"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan in the map view"><title>Inspect the scan in the map view</title><defs><clipPath id="gui-clip-scan-analysis-map-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-1"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-analysis-map.webp?v=f649b540618c" data-gui-dark="0dd8f85f8a48" width="1480" height="800" clip-path="url(#gui-clip-scan-analysis-map-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-1)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-analysis-map-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-1-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Evolution"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect a fitted parameter across the scan</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-evolution.webp?v=153be8b902b2" data-gui-dark="235f15c7f1aa" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect a fitted parameter across the scan"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect a fitted parameter across the scan"><title>Inspect a fitted parameter across the scan</title><defs><clipPath id="gui-clip-scan-evolution-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-2"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-evolution.webp?v=153be8b902b2" data-gui-dark="235f15c7f1aa" width="1480" height="800" clip-path="url(#gui-clip-scan-evolution-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-2)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-evolution-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-2-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Correlations"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect correlations for the selected measurement</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-correlations.webp?v=0ecfe268a616" data-gui-dark="e8defc6c850f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect correlations for the selected measurement"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect correlations for the selected measurement"><title>Inspect correlations for the selected measurement</title><defs><clipPath id="gui-clip-scan-correlations-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-3"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-correlations.webp?v=0ecfe268a616" data-gui-dark="e8defc6c850f" width="1480" height="800" clip-path="url(#gui-clip-scan-correlations-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-3)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-correlations-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-3-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Save the scan

Use **Save project as…** to keep the example together with its data and results. The run writes a row per dataset to `analysis/results.csv` as it progresses. Inspect the scan's report on **Report** and choose [which sections to export](../../report/index.md).

<!-- gui-guide:save-the-scan -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the report view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-report-basic.webp?v=d281a7629cd9" data-gui-dark="80f0b5434eb6" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-report-basic.webp?v=d281a7629cd9" data-gui-dark="80f0b5434eb6" width="1480" height="800" clip-path="url(#gui-clip-scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-report-basic.webp?v=d281a7629cd9" data-gui-dark="80f0b5434eb6" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-report-basic.webp?v=d281a7629cd9" data-gui-dark="80f0b5434eb6" width="1480" height="800" clip-path="url(#gui-clip-scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M771.000 124.000 Q771.000 120.000 771.000 116.000 L771.000 82.000 Q771.000 78.000 775.000 78.000 L808.516 78.000 Q812.516 78.000 812.516 82.000 L812.516 116.000 Q812.516 120.000 816.516 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 753.000 Q1479.000 757.000 1475.000 757.000 L775.000 757.000 Q771.000 757.000 771.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Correlations

The **Correlations** view on **Analysis** shows which fitted parameters move together.


## Report

The **Report** page collects the structure, the experiment and the fit.
