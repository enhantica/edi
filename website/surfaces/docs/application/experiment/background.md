---
category_glyph: "\uf83e"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="background" aria-hidden="true">&#63550;</span> Background

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a></p>
<!-- /group-tags -->

A background describes the smooth intensity beneath the diffraction peaks.

## Choose a background representation

The application supports line-segment backgrounds, represented by points, and polynomial or Chebyshev backgrounds, represented by terms. The **Background** group shows the values for the current experiment.

Changing the background type replaces its representation; review the confirmation before removing points or terms you want to keep.

<!-- gui-guide:choose-a-background-representation -->
<div class="gui-viewer" markdown="1">


=== "Background model"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Choose the background representation.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-background.png?v=b80de18fa10c" data-gui-dark="633db13f34e8" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background model"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background model"><title>Background model</title><defs><clipPath id="gui-clip-guide-experiment-background-overview-background-choose-a-background-representation-0-background-type"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-background.png?v=b80de18fa10c" data-gui-dark="633db13f34e8" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-background-overview-background-choose-a-background-representation-0-background-type)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-background-overview-background-choose-a-background-representation-0-background-type-1" data-gui-area="sidebar" data-gui-parts="[[784,210.00000000000932,339.25,56]]" d="M785.000 215.000 Q785.000 211.000 789.000 211.000 L1118.250 211.000 Q1122.250 211.000 1122.250 215.000 L1122.250 261.000 Q1122.250 265.000 1118.250 265.000 L789.000 265.000 Q785.000 265.000 785.000 261.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Background values"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect or edit the values in the selected representation.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-background.png?v=b80de18fa10c" data-gui-dark="633db13f34e8" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background values"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background values"><title>Background values</title><defs><clipPath id="gui-clip-guide-experiment-background-overview-background-choose-a-background-representation-0-background-rows"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-background.png?v=b80de18fa10c" data-gui-dark="633db13f34e8" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-background-overview-background-choose-a-background-representation-0-background-rows)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-background-overview-background-choose-a-background-representation-0-background-rows-1" data-gui-area="sidebar" data-gui-parts="[[784,210.00000000000932,682,337.5]]" d="M785.000 215.000 Q785.000 211.000 789.000 211.000 L1461.000 211.000 Q1465.000 211.000 1465.000 215.000 L1465.000 542.500 Q1465.000 546.500 1461.000 546.500 L789.000 546.500 Q785.000 546.500 785.000 542.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

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
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-background.png?v=b80de18fa10c" data-gui-dark="633db13f34e8" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background model"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background model"><title>Background model</title><defs><clipPath id="gui-clip-guide-experiment-background-overview-background-estimate-the-background-0-background-type"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-background.png?v=b80de18fa10c" data-gui-dark="633db13f34e8" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-background-overview-background-estimate-the-background-0-background-type)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-background-overview-background-estimate-the-background-0-background-type-1" data-gui-area="sidebar" data-gui-parts="[[784,210.00000000000932,339.25,56]]" d="M785.000 215.000 Q785.000 211.000 789.000 211.000 L1118.250 211.000 Q1122.250 211.000 1122.250 215.000 L1122.250 261.000 Q1122.250 265.000 1118.250 265.000 L789.000 265.000 Q785.000 265.000 785.000 261.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Background values"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect or edit the values in the selected representation.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-background.png?v=b80de18fa10c" data-gui-dark="633db13f34e8" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background values"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background values"><title>Background values</title><defs><clipPath id="gui-clip-guide-experiment-background-overview-background-estimate-the-background-0-background-rows"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-background.png?v=b80de18fa10c" data-gui-dark="633db13f34e8" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-background-overview-background-estimate-the-background-0-background-rows)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-background-overview-background-estimate-the-background-0-background-rows-1" data-gui-area="sidebar" data-gui-parts="[[784,210.00000000000932,682,337.5]]" d="M785.000 215.000 Q785.000 211.000 789.000 211.000 L1461.000 211.000 Q1465.000 211.000 1465.000 215.000 L1465.000 542.500 Q1465.000 546.500 1461.000 546.500 L789.000 546.500 Q785.000 546.500 785.000 542.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

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
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-background-a-practical-sequence-0-workflow-analysis-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M771.000 124.000 Q771.000 120.000 771.000 116.000 L771.000 82.000 Q771.000 78.000 775.000 78.000 L808.516 78.000 Q812.516 78.000 812.516 82.000 L812.516 116.000 Q812.516 120.000 816.516 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 753.000 Q1479.000 757.000 1475.000 757.000 L775.000 757.000 Q771.000 757.000 771.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-background-a-practical-sequence-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-background-a-practical-sequence-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M1.000 763.000 Q1.000 759.000 5.000 759.000 L1475.000 759.000 Q1479.000 759.000 1479.000 763.000 L1479.000 795.000 Q1479.000 799.000 1475.000 799.000 L5.000 799.000 Q1.000 799.000 1.000 795.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
