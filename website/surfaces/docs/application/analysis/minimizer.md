---
category_glyph: "\uf3be"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="minimizer" aria-hidden="true">&#62398;</span> Minimizer

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> <a class="ed-tag ed-tag--fitting" data-ed-tag="purpose" data-ed-token="refinement" href="../../user-guide/glossary/#fitting" title="Fitting measured data"><span class="ed-reference-icon" aria-hidden="true"></span>Fitting</a></p>

Shown: with measured data.
<!-- /group-tags -->

## Choose the search settings

On **Analysis → Extra**, expand **Minimizer**. Choose the descent strategy, then set the maximum iterations and chi-square tolerance. These settings control the **crysta** minimizer.

<!-- gui-options:guide-analysis-minimizer:minimizer.descent: -->
- Ladder
- Fast descent
- Fast descent with linear snap
- Fast descent with guarded linear snap
- Multi-start with pruning
<!-- /gui-options -->

Keep the default strategy for a first fit. Before changing search settings, check the starting model, free parameters and residual. See [minimization and uncertainty](../../physics/minimization.md) for the objective and interpretation of results.

<!-- gui-guide:choose-the-search-settings -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the descent strategy and convergence settings.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-analysis-minimizer.png?v=b32020e388cb" data-gui-dark="c0c19522ea78" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Minimizer"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Minimizer"><title>Minimizer</title><defs><clipPath id="gui-clip-guide-analysis-minimizer-overview-minimizer-choose-the-search-settings-0-group-minimizer"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-analysis-minimizer.png?v=b32020e388cb" data-gui-dark="c0c19522ea78" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-minimizer-overview-minimizer-choose-the-search-settings-0-group-minimizer)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-minimizer-overview-minimizer-choose-the-search-settings-0-group-minimizer-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,259]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 373.000 Q1479.000 377.000 1475.000 377.000 L775.000 377.000 Q771.000 377.000 771.000 373.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
