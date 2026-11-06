---
template: gui.html
---

# :fa5-microscope: Experiment

The **Experiment** page holds your measurements and how they are calculated: the pattern on the left, and on the right the groups for the current experiment. Which groups appear depends on the experiment.

<!-- sidebar-groups -->
| Sidebar group | Tab | Shown |
| --- | --- | --- |
| <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> [Experiments](experiments.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#62263;</span> [Calculation range](calculation-range.md) | Main | Without measured data |
| <span class="ed-reference-icon" aria-hidden="true">&#63550;</span> [Background](background.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> [Instrument](instrument.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> [Peak profile](peak-profile.md) | Main and Extra | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#61741;</span> [Excluded regions](excluded-regions.md) | Main | With measured data |
| <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> [Extinction](extinction.md) | Main | Single crystal |
| <span class="ed-reference-icon" aria-hidden="true">&#62973;</span> [Linked structures](linked-structures.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#61648;</span> [Background estimation](background-estimation.md) | Extra | With measured data |
| <span class="ed-reference-icon" aria-hidden="true">&#61507;</span> [Absorption](absorption.md) | Extra | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#61774;</span> [Preferred orientations](preferred-orientations.md) | Extra | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#61616;</span> [Observed reflections](observed-reflections.md) | Extra | Single crystal |
| <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> [Scattering source](scattering-source.md) | Extra | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#62831;</span> [Data source](data-source.md) | Extra | With measured data |
| <span class="ed-reference-icon" aria-hidden="true">&#62263;</span> [Measured data](measured-data.md) | Extra | With measured data |
| <span class="ed-reference-icon" aria-hidden="true">&#62461;</span> [Performance](performance.md) | Settings | Always |
<!-- /sidebar-groups -->

## Read the pattern

The main **Pattern** view compares measured and calculated intensities. Inspect the residual and Bragg marks as well as the total curve. Use the dataset selector above the plot to change the displayed measurement.

<!-- gui-guide:read-the-pattern -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-10-experiment-loaded-overview-index-read-the-pattern-0-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" width="1480" height="800" clip-path="url(#gui-clip-10-experiment-loaded-overview-index-read-the-pattern-0-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="10-experiment-loaded-overview-index-read-the-pattern-0-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-10-experiment-loaded-overview-index-read-the-pattern-0-workflow-experiment-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" width="1480" height="800" clip-path="url(#gui-clip-10-experiment-loaded-overview-index-read-the-pattern-0-workflow-experiment-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="10-experiment-loaded-overview-index-read-the-pattern-0-workflow-experiment-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
