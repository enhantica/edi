---
category_glyph: "\uf3be"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="minimizer" aria-hidden="true">&#62398;</span> Minimizer

## Choose the search settings

On **Analysis → Extra**, expand **Minimizer**. Choose the descent strategy, then set the maximum iterations and chi-square tolerance. These settings control the **crysta** minimizer.

<!-- gui-options:guide-analysis-minimizer:minimizer.descent: -->
- Ladder
- Fast descent
- Fast descent with linear snap
- Fast descent with guarded linear snap
- Multi-start with pruning
<!-- /gui-options -->

Keep the default strategy for a first fit. Before changing search settings, check the starting model, free parameters and residual. See [minimization and uncertainty](../physics/minimization.md) for the objective and interpretation of results.

<!-- gui-guide:choose-the-search-settings -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the descent strategy and convergence settings.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-analysis-minimizer.png?v=b02f14557929" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Minimizer"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Minimizer"><title>Minimizer</title><defs><clipPath id="gui-clip-guide-analysis-minimizer-overview-minimizer-choose-the-search-settings-0-group-minimizer"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-analysis-minimizer.png?v=b02f14557929" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-minimizer-overview-minimizer-choose-the-search-settings-0-group-minimizer)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-minimizer-overview-minimizer-choose-the-search-settings-0-group-minimizer-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,189]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 310.000 L768.000 310.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
