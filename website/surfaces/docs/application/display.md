---
template: gui.html
---

# :fa5-calculator: Display and updates

## Choose which parameters are shown

On **Analysis → Settings**, expand **Parameters shown**. The table always lists every value a fit can vary, free or fixed, and every value marked free. Four boxes add the values that cannot be fitted: **Not measured in this fit**, on by default, and **Fixed by symmetry**, **Set by a constraint** and **Setup values**, off by default.

This filters the table; it does not free parameters or change the fit. The selection is an application preference, separate from the saved project.

<!-- gui-guide:choose-which-parameters-are-shown -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose which additional parameter groups appear alongside free parameters.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-analysis-shown-parameters.png?v=4c3243f00b42" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Parameters shown"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Parameters shown"><title>Parameters shown</title><defs><clipPath id="gui-clip-guide-analysis-shown-parameters-overview-display-choose-which-parameters-are-shown-0-group-shownParameters"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-analysis-shown-parameters.png?v=4c3243f00b42" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-shown-parameters-overview-display-choose-which-parameters-are-shown-0-group-shownParameters)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-shown-parameters-overview-display-choose-which-parameters-are-shown-0-group-shownParameters-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,119]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 240.000 L768.000 240.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Choose updates during a scan

Expand **Pattern updates during a scan**. Use **Adaptive** for responsive updates, or choose a fixed update policy: about once a second, every pattern with fitting waiting for the display, every pattern with the display catching up, or only at the end.

Waiting for every redraw can slow a scan. This is a display preference and does not change the fitting mode. See [Work with a scan](scans.md).

<!-- gui-guide:choose-updates-during-a-scan -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose how often the display updates while a scan is fitted.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-analysis-pattern-updates.png?v=6adf1e03d52e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Pattern updates during a scan"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Pattern updates during a scan"><title>Pattern updates during a scan</title><defs><clipPath id="gui-clip-guide-analysis-pattern-updates-overview-display-choose-updates-during-a-scan-0-group-patternUpdates"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-analysis-pattern-updates.png?v=6adf1e03d52e" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-pattern-updates-overview-display-choose-updates-during-a-scan-0-group-patternUpdates)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-pattern-updates-overview-display-choose-updates-during-a-scan-0-group-patternUpdates-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,98]]" d="M768.000 159.000 L1482.000 159.000 L1482.000 261.000 L768.000 261.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
