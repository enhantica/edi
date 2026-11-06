---
category_glyph: "\uf610"
template: gui.html
---

# <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> Experiments

## Select or create an experiment

On **Experiment → Main**, expand **Experiments** and select a row. **Load experiment** reads one or more experiments from CIF or `.edi` files, each with its type, settings and any measured data. **Create experiment** adds a starting experiment linked to the project's structures.

Use [experiment types and labels](../../user-guide/glossary.md#experiment-types-and-labels) to distinguish sample form, probe and beam mode. Choose the measurement type before importing measured data. Until data are loaded, the experiment uses a simulation range. A project can contain measured experiments and simulations; fitting uses the measured data.

<!-- gui-guide:select-or-create-an-experiment -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61587;</span>Load experiment"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Import the experiment file, including measured intensities and instrument settings.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-create.png?v=9423ec48bc92" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load experiment"><title>Load experiment</title><defs><clipPath id="gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-load"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-create.png?v=9423ec48bc92" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-load)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-load-1" data-gui-area="sidebar" data-gui-parts="[[784,400,218,39]]" d="M782.000 398.000 L1004.000 398.000 L1004.000 441.000 L782.000 441.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61525;</span>Create experiment"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Add an experiment and choose its measurement type.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-create.png?v=9423ec48bc92" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create experiment"><title>Create experiment</title><defs><clipPath id="gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-create"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-create.png?v=9423ec48bc92" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-create)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-create-1" data-gui-area="sidebar" data-gui-parts="[[1016,400,218,39]]" d="M1014.000 398.000 L1236.000 398.000 L1236.000 441.000 L1014.000 441.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

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
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-data.png?v=9423ec48bc92" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Experiments"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Experiments"><title>Experiments</title><defs><clipPath id="gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-list"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-data.png?v=9423ec48bc92" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-list)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-list-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M782.000 166.000 L1468.000 166.000 L1468.000 248.000 L782.000 248.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "Measured-data file"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Load the observed intensities for this experiment.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-data.png?v=9423ec48bc92" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Measured-data file"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Measured-data file"><title>Measured-data file</title><defs><clipPath id="gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-loadData-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-data.png?v=9423ec48bc92" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-loadData-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-loadData-0-1" data-gui-area="sidebar" data-gui-parts="[[958,207,56.078125,39]]" d="M956.000 205.000 L1016.078 205.000 L1016.078 248.000 L956.000 248.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
