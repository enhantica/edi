---
category_glyph: "\uf0d0"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="background-estimate" aria-hidden="true">&#61648;</span> Background estimation

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
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-estimation.png?v=03a760d36d3e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background estimation"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background estimation"><title>Background estimation</title><defs><clipPath id="gui-clip-guide-experiment-estimation-overview-background-estimation-estimation-settings-0-group-background_estimate"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-estimation.png?v=03a760d36d3e" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-estimation-overview-background-estimation-estimation-settings-0-group-background_estimate)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-estimation-overview-background-estimation-estimation-settings-0-group-background_estimate-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,259]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 380.000 L768.000 380.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
