---
category_glyph: "\uf1de"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="fitting-mode" aria-hidden="true">&#61918;</span> Fitting mode

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> <a class="ed-tag ed-tag--fitting" data-ed-tag="purpose" data-ed-token="refinement" href="../../user-guide/glossary/#fitting" title="Fitting measured data"><span class="ed-reference-icon" aria-hidden="true"></span>Fitting</a></p>

Shown: with measured data.
<!-- /group-tags -->

The fitting mode determines how the project's experiments or scan datasets are fitted. It changes the relationship between fits, not the meaning of the structures and experiments.

The shared [fitting-mode guide](../../user-guide/analysis-workflow/analysis.md#fitting-modes) explains single, joint, sequential and independent fitting, including their starting-state policies. This page explains the application controls.

## Select the mode in the app

Open **Analysis** and use the fitting-mode control. The choices reflect the project: with only one applicable mode the selector is disabled and explains why.

A joint fit shows the experiment weights. A scan mode shows its scan declaration. The mode is saved as part of the project and is also read by Python and Command Line analysis.

<!-- gui-guide:select-the-mode-in-the-app -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">The available choices depend on the project.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-analysis-modes.png?v=d6a80302d0b8" data-gui-dark="78f781883f90" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-guide-analysis-modes-overview-fitting-mode-select-the-mode-in-the-app-0-fittingMode-type"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-analysis-modes.png?v=d6a80302d0b8" data-gui-dark="78f781883f90" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-modes-overview-fitting-mode-select-the-mode-in-the-app-0-fittingMode-type)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-modes-overview-fitting-mode-select-the-mode-in-the-app-0-fittingMode-type-1" data-gui-area="sidebar" data-gui-parts="[[784,210,682,56]]" d="M785.000 215.000 Q785.000 211.000 789.000 211.000 L1461.000 211.000 Q1465.000 211.000 1465.000 215.000 L1465.000 261.000 Q1465.000 265.000 1461.000 265.000 L789.000 265.000 Q785.000 265.000 785.000 261.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Fit a scan

Use **sequential** when each result should seed the next fit, or **independent** when you want each dataset to start from the same template. Follow the [scan guide](../scans.md) for dataset selection, progress, continuation and evolution charts.

<!-- gui-guide:fit-a-scan -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose sequential, independent or single-dataset fitting.</p>
<a class="gui-image-link" href="../../assets/gui/scan/scan-mode.png?v=d995140cb703" data-gui-dark="0bd6df034e87" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-scan-mode-overview-fitting-mode-fit-a-scan-0-group-fitting_mode"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/scan/scan-mode.png?v=d995140cb703" data-gui-dark="0bd6df034e87" width="1480" height="800" clip-path="url(#gui-clip-scan-mode-overview-fitting-mode-fit-a-scan-0-group-fitting_mode)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-mode-overview-fitting-mode-fit-a-scan-0-group-fitting_mode-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 275.000 Q1479.000 279.000 1475.000 279.000 L775.000 279.000 Q771.000 279.000 771.000 275.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Fit the shown scan dataset on its own

A scan can use `single` to fit the shown dataset. That result becomes the template, and the selected file becomes the template dataset. Check the template before starting a full scan.

<!-- gui-guide:fit-the-shown-scan-dataset-on-its-own -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose sequential, independent or single-dataset fitting.</p>
<a class="gui-image-link" href="../../assets/gui/scan/scan-mode.png?v=d995140cb703" data-gui-dark="0bd6df034e87" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-scan-mode-overview-fitting-mode-fit-the-shown-scan-dataset-on-its-own-0-group-fitting_mode"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/scan/scan-mode.png?v=d995140cb703" data-gui-dark="0bd6df034e87" width="1480" height="800" clip-path="url(#gui-clip-scan-mode-overview-fitting-mode-fit-the-shown-scan-dataset-on-its-own-0-group-fitting_mode)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-mode-overview-fitting-mode-fit-the-shown-scan-dataset-on-its-own-0-group-fitting_mode-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 275.000 Q1479.000 279.000 1475.000 279.000 L775.000 279.000 Q771.000 279.000 771.000 275.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
