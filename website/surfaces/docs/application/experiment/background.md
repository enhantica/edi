---
category_glyph: "\uf83e"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="background" aria-hidden="true">&#63550;</span> Background

A background describes the smooth intensity beneath the diffraction peaks.

## Choose a background representation

The application supports line-segment backgrounds, represented by points, and polynomial or Chebyshev backgrounds, represented by terms. The **Background** group shows the values for the current experiment.

Changing the background type replaces its representation; review the confirmation before removing points or terms you want to keep.

<!-- gui-guide:choose-a-background-representation -->
<div class="gui-viewer" markdown="1">


=== "Background model"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Choose the background representation.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-background.png?v=e184f981fe99" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background model"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background model"><title>Background model</title><defs><clipPath id="gui-clip-guide-experiment-background-overview-background-choose-a-background-representation-0-background-type"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-background.png?v=e184f981fe99" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-background-overview-background-choose-a-background-representation-0-background-type)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-background-overview-background-choose-a-background-representation-0-background-type-1" data-gui-area="sidebar" data-gui-parts="[[784,210,339.25,56]]" d="M782.000 208.000 L1125.250 208.000 L1125.250 268.000 L782.000 268.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "Background values"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect or edit the values in the selected representation.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-background.png?v=e184f981fe99" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background values"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background values"><title>Background values</title><defs><clipPath id="gui-clip-guide-experiment-background-overview-background-choose-a-background-representation-0-background-rows"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-background.png?v=e184f981fe99" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-background-overview-background-choose-a-background-representation-0-background-rows)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-background-overview-background-choose-a-background-representation-0-background-rows-1" data-gui-area="sidebar" data-gui-parts="[[784,210,682,337.5]]" d="M782.000 208.000 L1468.000 208.000 L1468.000 549.500 L782.000 549.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Estimate the background

On **Experiment**, choose **Estimate** in the **Background** group. The estimate replaces the current points or terms. Undo brings the previous values back. Estimate needs measured data: until data are loaded into the experiment, the button is disabled and its tooltip says why.

The **estimation mode** controls what happens next:

- **Manual** keeps the current values for editing. Estimate runs when you ask for it.
- **Auto** estimates again when the measured data or estimation settings change. The table shows the estimated values; choose manual to edit them.

You can still free or fix a value through its context menu.

<!-- gui-guide:estimate-the-background -->
<div class="gui-viewer" markdown="1">


=== "Background model"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Choose the background representation.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-background.png?v=e184f981fe99" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background model"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background model"><title>Background model</title><defs><clipPath id="gui-clip-guide-experiment-background-overview-background-estimate-the-background-0-background-type"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-background.png?v=e184f981fe99" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-background-overview-background-estimate-the-background-0-background-type)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-background-overview-background-estimate-the-background-0-background-type-1" data-gui-area="sidebar" data-gui-parts="[[784,210,339.25,56]]" d="M782.000 208.000 L1125.250 208.000 L1125.250 268.000 L782.000 268.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "Background values"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect or edit the values in the selected representation.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-background.png?v=e184f981fe99" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background values"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background values"><title>Background values</title><defs><clipPath id="gui-clip-guide-experiment-background-overview-background-estimate-the-background-0-background-rows"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-background.png?v=e184f981fe99" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-background-overview-background-estimate-the-background-0-background-rows)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-background-overview-background-estimate-the-background-0-background-rows-1" data-gui-area="sidebar" data-gui-parts="[[784,210,682,337.5]]" d="M782.000 208.000 L1468.000 208.000 L1468.000 549.500 L782.000 549.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## A practical sequence

1. Load the data and estimate the background while the model is still rough.
2. Fit the structure and profile, keeping the background fixed or freeing selected background values.
3. Inspect the residual and estimate again if the improved model makes the background clearer.

<!-- gui-guide:a-practical-sequence -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-background-a-practical-sequence-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M-2.000 756.000 L1482.000 756.000 L1482.000 802.000 L-2.000 802.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
