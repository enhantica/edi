---
category_glyph: "\uf12d"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="excluded-region" aria-hidden="true">&#61741;</span> Excluded regions

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> <a class="ed-tag ed-tag--fitting" data-ed-tag="purpose" data-ed-token="refinement" href="../../user-guide/glossary/#fitting" title="Fitting measured data"><span class="ed-reference-icon" aria-hidden="true"></span>Fitting</a></p>

Shown: with measured data.
<!-- /group-tags -->

An excluded region removes a measurement interval from the fit, which is a different choice from modelling it with a [background](background.md).

## Exclude an interval

Use **Excluded regions** on the Experiment page to declare intervals that should not be fitted. The group appears once the experiment has measured data. Check the boundaries against the pattern. An excluded region remains a deliberate omission from the analysis; it does not repair the model of that interval.

Save the project to keep its background settings and excluded regions.

<!-- gui-guide:exclude-an-interval -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Set the boundaries of regions omitted from fitting.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-exclusions.png?v=4d3412650381" data-gui-dark="85ef523cf83b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Excluded intervals"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Excluded intervals"><title>Excluded intervals</title><defs><clipPath id="gui-clip-guide-experiment-exclusions-overview-excluded-regions-exclude-an-interval-0-excludedRegions-list"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-exclusions.png?v=4d3412650381" data-gui-dark="85ef523cf83b" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-exclusions-overview-excluded-regions-exclude-an-interval-0-excludedRegions-list)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-exclusions-overview-excluded-regions-exclude-an-interval-0-excludedRegions-list-1" data-gui-area="sidebar" data-gui-parts="[[784,336,682,117]]" d="M785.000 341.000 Q785.000 337.000 789.000 337.000 L1461.000 337.000 Q1465.000 337.000 1465.000 341.000 L1465.000 448.000 Q1465.000 452.000 1461.000 452.000 L789.000 452.000 Q785.000 452.000 785.000 448.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
