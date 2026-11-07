---
category_glyph: "\uf0d0"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="background-estimate" aria-hidden="true">&#61648;</span> Background estimation

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> <a class="ed-tag ed-tag--fitting" data-ed-tag="purpose" data-ed-token="refinement" href="../../user-guide/glossary/#fitting" title="Fitting measured data"><span class="ed-reference-icon" aria-hidden="true"></span>Fitting</a></p>

Shown: with measured data.
<!-- /group-tags -->

## Estimation settings

The **Extra** tab's **Background** group holds the estimation settings. It appears once the experiment has measured data. Leave a field empty to let the estimator choose where that option supports automatic selection.

| Setting | Purpose |
| --- | --- |
| Calculated peaks | Use `auto`, subtract the model's calculated peaks, or ignore them. |
| Anchor points | Control the number of points in a line-segment background. |
| Max terms | Limit the number of polynomial or Chebyshev terms. |
| Baseline method | Select the method used to find the curve under the peaks. |
| Peak width and smoothness | Control the scale on which the baseline is estimated. |
| Noise tolerance | Control how closely the points or terms follow the estimated curve. |

Subtracting calculated peaks can help where peaks overlap and the measured intensity never reaches the background. A poor model can make subtraction misleading. The default `auto` choice checks whether the model is suitable and reports its choice below the settings.

<!-- gui-guide:estimation-settings -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Inspect background estimation settings.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-estimation.png?v=bf532cb63b55" data-gui-dark="1e8cec8cdf50" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background estimation"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background estimation"><title>Background estimation</title><defs><clipPath id="gui-clip-guide-experiment-estimation-overview-background-estimation-estimation-settings-0-group-background_estimate"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-estimation.png?v=bf532cb63b55" data-gui-dark="1e8cec8cdf50" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-estimation-overview-background-estimation-estimation-settings-0-group-background_estimate)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-estimation-overview-background-estimation-estimation-settings-0-group-background_estimate-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,259]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 373.000 Q1479.000 377.000 1475.000 377.000 L775.000 377.000 Q771.000 377.000 771.000 373.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
