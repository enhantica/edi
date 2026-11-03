---
category_glyph: "\uf1de"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="fitting-mode" aria-hidden="true">&#61918;</span> Choose a fitting mode

The fitting mode determines how the project's experiments or scan datasets are fitted. It changes the relationship between fits, not the meaning of the structures and experiments.

The shared [fitting-mode guide](../user-guide/fitting-modes.md) explains single, joint, sequential and independent fitting, including their starting-state policies. This page explains the application controls.

## Select the mode in the app

Open **Analysis** and use the fitting-mode control. The choices reflect the project: with only one applicable mode the selector is disabled and explains why.

A joint fit shows the experiment weights. A scan mode shows its scan declaration. The mode is saved as part of the project and is also read by Python and Command Line analysis.

<!-- gui-guide:select-the-mode-in-the-app -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">The available choices depend on the project.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-analysis-modes.png?v=0ee89cab5a74" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-guide-analysis-modes-overview-fitting-modes-select-the-mode-in-the-app-0-fittingMode-type"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-analysis-modes.png?v=0ee89cab5a74" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-modes-overview-fitting-modes-select-the-mode-in-the-app-0-fittingMode-type)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-modes-overview-fitting-modes-select-the-mode-in-the-app-0-fittingMode-type-1" data-gui-area="sidebar" data-gui-parts="[[784,210,682,56]]" d="M782.000 208.000 L1468.000 208.000 L1468.000 268.000 L782.000 268.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Fit several experiments jointly

<!-- joint-example -->
This example is **pd-neut-xray-cwl_pbso4-d1a-lab**: PbSO₄ [Pnma], D1A @ ILL and laboratory X-ray.
<!-- /joint-example -->

A joint fit uses all the project's experiments together. Shared structural parameters can be informed by more than one measurement, while each experiment keeps its own instrument, background and other settings.

Review the experiment weights and linked structures before running. A joint result should still be inspected experiment by experiment.

<!-- gui-guide:fit-several-experiments-jointly -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Set the relative weights of the experiments in the joint fit.</p>
<a class="gui-image-link" href="../assets/gui/joint/joint-weights.png?v=6037e5261d90" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Joint-fit weights (2)"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Joint-fit weights (2)"><title>Joint-fit weights (2)</title><defs><clipPath id="gui-clip-joint-weights-overview-fitting-modes-fit-several-experiments-jointly-0-group-joint_fit"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/joint/joint-weights.png?v=6037e5261d90" width="1480" height="800" clip-path="url(#gui-clip-joint-weights-overview-fitting-modes-fit-several-experiments-jointly-0-group-joint_fit)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="joint-weights-overview-fitting-modes-fit-several-experiments-jointly-0-group-joint_fit-1" data-gui-area="sidebar" data-gui-parts="[[770,287,710,180]]" d="M768.000 285.000 L1482.000 285.000 L1482.000 469.000 L768.000 469.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Fit a scan

Use **sequential** when each result should seed the next fit, or **independent** when you want each dataset to start from the same template. Follow the [scan guide](scans.md) for dataset selection, progress, continuation and evolution charts.

<!-- gui-guide:fit-a-scan -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose sequential, independent or single-dataset fitting.</p>
<a class="gui-image-link" href="../assets/gui/scan/scan-mode.png?v=3dae24f71fee" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-scan-mode-overview-fitting-modes-fit-a-scan-0-group-fitting_mode"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-mode.png?v=3dae24f71fee" width="1480" height="800" clip-path="url(#gui-clip-scan-mode-overview-fitting-modes-fit-a-scan-0-group-fitting_mode)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-mode-overview-fitting-modes-fit-a-scan-0-group-fitting_mode-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M768.000 159.000 L1482.000 159.000 L1482.000 282.000 L768.000 282.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Fit the shown scan dataset on its own

A scan can use `single` to fit the shown dataset. That result becomes the template, and the selected file becomes the template dataset. Check the template before starting a full scan.

<!-- gui-guide:fit-the-shown-scan-dataset-on-its-own -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose sequential, independent or single-dataset fitting.</p>
<a class="gui-image-link" href="../assets/gui/scan/scan-mode.png?v=3dae24f71fee" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-scan-mode-overview-fitting-modes-fit-the-shown-scan-dataset-on-its-own-0-group-fitting_mode"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/scan/scan-mode.png?v=3dae24f71fee" width="1480" height="800" clip-path="url(#gui-clip-scan-mode-overview-fitting-modes-fit-the-shown-scan-dataset-on-its-own-0-group-fitting_mode)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-mode-overview-fitting-modes-fit-the-shown-scan-dataset-on-its-own-0-group-fitting_mode-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M768.000 159.000 L1482.000 159.000 L1482.000 282.000 L768.000 282.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
