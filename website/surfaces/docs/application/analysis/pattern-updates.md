---
category_glyph: "\uf201"
template: gui.html
---

# <span class="ed-reference-icon" aria-hidden="true">&#61953;</span> Pattern updates during a scan

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> <a class="ed-tag ed-tag--fitting" data-ed-tag="purpose" data-ed-token="refinement" href="../../user-guide/glossary/#fitting" title="Fitting measured data"><span class="ed-reference-icon" aria-hidden="true"></span>Fitting</a> <a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="sequential" href="../../user-guide/glossary/#sequential-fit" title="Fit a scan using the preceding result"><span class="ed-reference-icon" aria-hidden="true"></span>Sequential</a> <a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="independent" href="../../user-guide/glossary/#independent-fit" title="Fit a scan from common starting values"><span class="ed-reference-icon" aria-hidden="true"></span>Independent</a></p>

Shown: with measured data.
<!-- /group-tags -->

## Choose updates during a scan

On **Analysis → Settings**, expand **Pattern updates during a scan**. Use **Adaptive** for responsive updates, or choose a fixed update policy: about once a second, every pattern with fitting waiting for the display, every pattern with the display catching up, or only at the end.

Waiting for every redraw can slow a scan. This is a display preference and does not change the fitting mode. See [Work with a scan](../scans.md).

<!-- gui-guide:choose-updates-during-a-scan -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose how often the display updates while a scan is fitted.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-analysis-pattern-updates.png?v=f8237b84fd3e" data-gui-dark="059dda233ea6" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Pattern updates during a scan"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Pattern updates during a scan"><title>Pattern updates during a scan</title><defs><clipPath id="gui-clip-guide-analysis-pattern-updates-overview-pattern-updates-choose-updates-during-a-scan-0-group-patternUpdates"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-analysis-pattern-updates.png?v=f8237b84fd3e" data-gui-dark="059dda233ea6" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-pattern-updates-overview-pattern-updates-choose-updates-during-a-scan-0-group-patternUpdates)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-pattern-updates-overview-pattern-updates-choose-updates-during-a-scan-0-group-patternUpdates-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,98]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 254.000 Q1479.000 258.000 1475.000 258.000 L775.000 258.000 Q771.000 258.000 771.000 254.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
