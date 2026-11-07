---
category_glyph: "\uf610"
template: gui.html
---

# <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> Experiments

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a></p>
<!-- /group-tags -->

## Select or create an experiment

On **Experiment → Main**, expand **Experiments** and select a row. **Load experiment** reads one or more experiments from CIF or `.edi` files, each with its type, settings and any measured data. **Create experiment** adds a starting experiment linked to the project's structures.

Use [experiment types and labels](../../user-guide/glossary.md#experiment-types-and-labels) to distinguish sample form, probe and beam mode. Choose the measurement type before importing measured data. Until data are loaded, the experiment uses a simulation range. A project can contain measured experiments and simulations; fitting uses the measured data.

<!-- gui-guide:select-or-create-an-experiment -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61587;</span>Load experiment"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Import the experiment file, including measured intensities and instrument settings.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-create.png?v=41e42772b908" data-gui-dark="f0df0c4c6d8a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load experiment"><title>Load experiment</title><defs><clipPath id="gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-load"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-create.png?v=41e42772b908" data-gui-dark="f0df0c4c6d8a" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-load)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-load-1" data-gui-area="sidebar" data-gui-parts="[[784,400,218,39]]" d="M785.000 405.000 Q785.000 401.000 789.000 401.000 L997.000 401.000 Q1001.000 401.000 1001.000 405.000 L1001.000 434.000 Q1001.000 438.000 997.000 438.000 L789.000 438.000 Q785.000 438.000 785.000 434.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61525;</span>Create experiment"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Add an experiment and choose its measurement type.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-create.png?v=41e42772b908" data-gui-dark="f0df0c4c6d8a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create experiment"><title>Create experiment</title><defs><clipPath id="gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-create"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-create.png?v=41e42772b908" data-gui-dark="f0df0c4c6d8a" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-create)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-create-overview-experiments-select-or-create-an-experiment-0-experiments-create-1" data-gui-area="sidebar" data-gui-parts="[[1016,400,218,39]]" d="M1017.000 405.000 Q1017.000 401.000 1021.000 401.000 L1229.000 401.000 Q1233.000 401.000 1233.000 405.000 L1233.000 434.000 Q1233.000 438.000 1229.000 438.000 L1021.000 438.000 Q1017.000 438.000 1017.000 434.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

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
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-data.png?v=41e42772b908" data-gui-dark="f0df0c4c6d8a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Experiments"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Experiments"><title>Experiments</title><defs><clipPath id="gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-list"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-data.png?v=41e42772b908" data-gui-dark="f0df0c4c6d8a" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-list)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-list-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 241.000 Q1465.000 245.000 1461.000 245.000 L789.000 245.000 Q785.000 245.000 785.000 241.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "spodi.xye"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select an experiment or load measured data.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-data.png?v=41e42772b908" data-gui-dark="f0df0c4c6d8a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: spodi.xye"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="spodi.xye"><title>spodi.xye</title><defs><clipPath id="gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-file-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-data.png?v=41e42772b908" data-gui-dark="f0df0c4c6d8a" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-file-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-data-overview-experiments-load-a-powder-pattern-0-experiments-file-0-1" data-gui-area="sidebar" data-gui-parts="[[954,207,56.078125,39]]" d="M955.000 212.000 Q955.000 208.000 959.000 208.000 L1005.078 208.000 Q1009.078 208.000 1009.078 212.000 L1009.078 241.000 Q1009.078 245.000 1005.078 245.000 L959.000 245.000 Q955.000 245.000 955.000 241.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
