---
category_glyph: "\uf52c"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="constraint" aria-hidden="true">&#62764;</span> Constraints

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a></p>
<!-- /group-tags -->

## Define constraints

On **Analysis → Extra**, expand **Constraints** and append a row. Set its target alias and expression, using the aliases you defined. Enable the row to apply the relation, or disable it to retain the definition without applying it.

Check the resulting parameter values before fitting. See [constraints and parameter dependencies](../../physics/minimization.md).

<!-- gui-guide:define-constraints -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Define relations between aliased parameters and enable the relations to apply.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-analysis-constraints.png?v=3e323988e9bd" data-gui-dark="839893e68e79" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Constraints"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Constraints"><title>Constraints</title><defs><clipPath id="gui-clip-guide-analysis-constraints-overview-constraints-define-constraints-0-group-constraint"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-analysis-constraints.png?v=3e323988e9bd" data-gui-dark="839893e68e79" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-constraints-overview-constraints-define-constraints-0-group-constraint)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-constraints-overview-constraints-define-constraints-0-group-constraint-1" data-gui-area="sidebar" data-gui-parts="[[770,245.00000000000693,710,194]]" d="M771.000 250.000 Q771.000 246.000 775.000 246.000 L1475.000 246.000 Q1479.000 246.000 1479.000 250.000 L1479.000 434.000 Q1479.000 438.000 1475.000 438.000 L775.000 438.000 Q771.000 438.000 771.000 434.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
