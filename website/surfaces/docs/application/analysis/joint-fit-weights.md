---
category_glyph: "\uf0c1"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="joint-fit" aria-hidden="true">&#61633;</span> Joint-fit weights

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> <a class="ed-tag ed-tag--fitting" data-ed-tag="purpose" data-ed-token="refinement" href="../../user-guide/glossary/#fitting" title="Fitting measured data"><span class="ed-reference-icon" aria-hidden="true"></span>Fitting</a> <a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="joint" href="../../user-guide/glossary/#joint-fit" title="Fit several experiments together"><span class="ed-reference-icon" aria-hidden="true"></span>Joint</a></p>

Shown: joint fit.
<!-- /group-tags -->

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
<a class="gui-image-link" href="../../assets/gui/joint/joint-weights.png?v=4c4c88eeb4f7" data-gui-dark="bcd7b02fa789" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Joint-fit weights (2)"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Joint-fit weights (2)"><title>Joint-fit weights (2)</title><defs><clipPath id="gui-clip-joint-weights-overview-joint-fit-weights-fit-several-experiments-jointly-0-group-joint_fit"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/joint/joint-weights.png?v=4c4c88eeb4f7" data-gui-dark="bcd7b02fa789" width="1480" height="800" clip-path="url(#gui-clip-joint-weights-overview-joint-fit-weights-fit-several-experiments-jointly-0-group-joint_fit)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="joint-weights-overview-joint-fit-weights-fit-several-experiments-jointly-0-group-joint_fit-1" data-gui-area="sidebar" data-gui-parts="[[770,287.00000000000244,710,180]]" d="M771.000 292.000 Q771.000 288.000 775.000 288.000 L1475.000 288.000 Q1479.000 288.000 1479.000 292.000 L1479.000 462.000 Q1479.000 466.000 1475.000 466.000 L775.000 466.000 Q771.000 466.000 771.000 462.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
