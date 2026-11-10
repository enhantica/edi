---
category_glyph: "\uf043"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="absorption" aria-hidden="true">&#61507;</span> Absorption

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a></p>
<!-- /group-tags -->

## Set absorption

On **Experiment → Extra**, expand **Absorption**. Choose the model that matches the sample geometry and enter its physical parameters in the units shown. Leave **None** selected when no absorption correction is required.

<!-- gui-options:guide-experiment-absorption:absorption.type:absorption -->
- [None](../../physics/corrections/absorption/#absorption-types)
- [Cylinder (Hewat)](../../physics/corrections/absorption/#eq-hewat)
- [Cylinder (Lobanov)](../../physics/corrections/absorption/#eq-lobanov)
<!-- /gui-options -->

See [absorption](../../physics/corrections/absorption.md) for the models and their assumptions.

<!-- gui-guide:set-absorption -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the sample absorption model and its physical parameters.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-absorption.png?v=53339a7cd2f9" data-gui-dark="cf84476882c7" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Absorption"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Absorption"><title>Absorption</title><defs><clipPath id="gui-clip-guide-experiment-absorption-overview-absorption-set-absorption-0-group-absorption"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-absorption.png?v=53339a7cd2f9" data-gui-dark="cf84476882c7" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-absorption-overview-absorption-set-absorption-0-group-absorption)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-absorption-overview-absorption-set-absorption-0-group-absorption-1" data-gui-area="sidebar" data-gui-parts="[[770,203.00000000000693,710,119]]" d="M771.000 208.000 Q771.000 204.000 775.000 204.000 L1475.000 204.000 Q1479.000 204.000 1479.000 208.000 L1479.000 317.000 Q1479.000 321.000 1475.000 321.000 L775.000 321.000 Q771.000 321.000 771.000 317.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
