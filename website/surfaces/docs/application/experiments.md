---
template: gui.html
---

# :material-microscope: Experiments and measured data

## Select or create an experiment

On **Experiment → Main**, expand **Experiments** and select a row. **Load experiment** reads one or more experiments from CIF or `.edi` files, each with its type, settings and any measured data. **Create experiment** adds a starting experiment linked to the project's structures.

Use [experiment types and labels](../user-guide/experiment-types.md) to distinguish sample form, probe and beam mode. Choose the measurement type before importing measured data. Until data are loaded, the experiment uses a simulation range. A project can contain measured experiments and simulations; fitting uses the measured data.

<!-- gui-guide:select-or-create-an-experiment -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61587;</span>Load experiment"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Import the experiment file, including measured intensities and instrument settings.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-experiment-create.png?v=9423ec48bc92" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load experiment"><title>Load experiment</title><defs><clipPath id="gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-load"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-experiment-create.png?v=9423ec48bc92" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-load)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-load-1" data-gui-area="sidebar" data-gui-parts="[[784,400,218,39]]" d="M782.000 398.000 L1004.000 398.000 L1004.000 441.000 L782.000 441.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61525;</span>Create experiment"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Add an experiment and choose its measurement type.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-experiment-create.png?v=9423ec48bc92" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create experiment"><title>Create experiment</title><defs><clipPath id="gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-create"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-experiment-create.png?v=9423ec48bc92" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-create)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-create-1" data-gui-area="sidebar" data-gui-parts="[[1016,400,218,39]]" d="M1014.000 398.000 L1236.000 398.000 L1236.000 441.000 L1014.000 441.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Load a powder pattern

Create or select an experiment first. Open **Load ▾** and choose **From file…** under **Measured data**. Text files may contain `x y` or `x y sigma` columns separated by spaces, tabs or commas.

| Measurement | x axis |
| --- | --- |
| Constant wavelength | 2θ in degrees |
| Time of flight | Time in microseconds |

Check the import message for skipped or adjusted rows. After loading, the measured points define the range and the experiment type is fixed. Instrument, profile, background and exclusions are retained. Use the same **Load ▾ → Measured data → From file…** route to replace the data; **Undo** restores the preceding state.

<!-- gui-guide:load-a-powder-pattern -->
<div class="gui-viewer" markdown="1">


=== "Experiments"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select the measurement to inspect.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-experiment-data.png?v=9423ec48bc92" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Experiments"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Experiments"><title>Experiments</title><defs><clipPath id="gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-list"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-experiment-data.png?v=9423ec48bc92" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-list)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-list-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M782.000 166.000 L1468.000 166.000 L1468.000 248.000 L782.000 248.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "Measured-data file"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Load the observed intensities for this experiment.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-experiment-data.png?v=9423ec48bc92" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Measured-data file"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Measured-data file"><title>Measured-data file</title><defs><clipPath id="gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-loadData-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-experiment-data.png?v=9423ec48bc92" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-loadData-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-loadData-0-1" data-gui-area="sidebar" data-gui-parts="[[958,207,56.078125,39]]" d="M956.000 205.000 L1016.078 205.000 L1016.078 248.000 L956.000 248.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Inspect the range and points

On **Experiment → Extra**, expand **Measured data**. Inspect the range and point table, including measured intensities and uncertainties. These data are read-only here. For an experiment without measured data, the corresponding group sets the simulation range and step.

See [data formats](../user-guide/data-formats.md) for file conventions.

<!-- gui-guide:inspect-the-range-and-points -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Inspect the measured range, intensities and uncertainties.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-experiment-data-settings.png?v=c1fe9bc9ff76" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Measured data"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Measured data"><title>Measured data</title><defs><clipPath id="gui-clip-guide-experiment-data-settings-overview-experiments-inspect-the-range-and-points-0-group-data"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-experiment-data-settings.png?v=c1fe9bc9ff76" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-data-settings-overview-experiments-inspect-the-range-and-points-0-group-data)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-data-settings-overview-experiments-inspect-the-range-and-points-0-group-data-1" data-gui-area="sidebar" data-gui-parts="[[770,329,710,386.5]]" d="M768.000 327.000 L1482.000 327.000 L1482.000 717.500 L768.000 717.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Read the pattern

The main **Pattern** view compares measured and calculated intensities. Inspect the residual and Bragg marks as well as the total curve. Use the dataset selector above the plot to change the displayed measurement.

<!-- gui-guide:read-the-pattern -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-10-experiment-loaded-overview-experiments-read-the-pattern-0-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" width="1480" height="800" clip-path="url(#gui-clip-10-experiment-loaded-overview-experiments-read-the-pattern-0-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="10-experiment-loaded-overview-experiments-read-the-pattern-0-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-10-experiment-loaded-overview-experiments-read-the-pattern-0-workflow-experiment-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" width="1480" height="800" clip-path="url(#gui-clip-10-experiment-loaded-overview-experiments-read-the-pattern-0-workflow-experiment-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="10-experiment-loaded-overview-experiments-read-the-pattern-0-workflow-experiment-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
