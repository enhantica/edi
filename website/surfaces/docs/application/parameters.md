---
template: gui.html
---

# :fa5-calculator: Parameters and constraints

## Choose independent parameters

On **Analysis → Main**, use the table filters to find a parameter. Edit its value and use the **free** checkbox to choose whether it may vary. The checkbox is disabled when a fit cannot vary the value, because it describes the setup, symmetry or a constraint sets it, the fit's data cannot determine it, or the calculation has no derivative for it yet. Hover over it to see which.

The displayed minimum and maximum describe admissible model values. See [parameters](../user-guide/parameters.md) and [refine a pattern](refine.md#choose-free-parameters).

<!-- gui-guide:choose-independent-parameters -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-parameters-choose-independent-parameters-0-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-parameters-choose-independent-parameters-0-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-parameters-choose-independent-parameters-0-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-parameters-choose-independent-parameters-0-workflow-analysis-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-parameters-choose-independent-parameters-0-workflow-analysis-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-parameters-choose-independent-parameters-0-workflow-analysis-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-parameters-choose-independent-parameters-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-parameters-choose-independent-parameters-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-parameters-choose-independent-parameters-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M-2.000 756.000 L1482.000 756.000 L1482.000 802.000 L-2.000 802.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Name parameters with aliases

On **Analysis → Extra**, expand **Aliases** and choose **Append new alias**. Enter a short name and select its parameter. Use the searchable selector to find a parameter in a large project.

Aliases give parameters names for use in constraint expressions. Duplicate or remove rows with the corresponding controls.

<!-- gui-guide:name-parameters-with-aliases -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Give parameters short names for use in constraint expressions.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-analysis-aliases.png?v=d2e8be4f6b80" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Aliases"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Aliases"><title>Aliases</title><defs><clipPath id="gui-clip-guide-analysis-aliases-overview-parameters-name-parameters-with-aliases-0-group-alias"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-analysis-aliases.png?v=d2e8be4f6b80" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-aliases-overview-parameters-name-parameters-with-aliases-0-group-alias)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-aliases-overview-parameters-name-parameters-with-aliases-0-group-alias-1" data-gui-area="sidebar" data-gui-parts="[[770,203,710,194]]" d="M768.000 201.000 L1482.000 201.000 L1482.000 399.000 L768.000 399.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Define constraints

Expand **Constraints** and append a row. Set its target alias and expression, using the aliases you defined. Enable the row to apply the relation, or disable it to retain the definition without applying it.

Check the resulting parameter values before fitting. See [constraints and parameter dependencies](../physics/minimization.md).

<!-- gui-guide:define-constraints -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Define relations between aliased parameters and enable the relations to apply.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-analysis-constraints.png?v=7211b526ca67" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Constraints"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Constraints"><title>Constraints</title><defs><clipPath id="gui-clip-guide-analysis-constraints-overview-parameters-define-constraints-0-group-constraint"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-analysis-constraints.png?v=7211b526ca67" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-constraints-overview-parameters-define-constraints-0-group-constraint)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-constraints-overview-parameters-define-constraints-0-group-constraint-1" data-gui-area="sidebar" data-gui-parts="[[770,245,710,194]]" d="M768.000 243.000 L1482.000 243.000 L1482.000 441.000 L768.000 441.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Inspect the last starting values

On **Analysis → Extra**, expand **Fit start values**. The read-only table records the free parameters' values and uncertainties before the last fit. Use **Undo** to restore that preceding state when needed.

See [uncertainties and correlations](../physics/minimization.md#eq-covariance) when assessing a result.

<!-- gui-guide:inspect-the-last-starting-values -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Inspect the free parameters before the last fit; use Undo to restore that state.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-analysis-start-values.png?v=9b78ca639f61" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit start values"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit start values"><title>Fit start values</title><defs><clipPath id="gui-clip-guide-analysis-start-values-overview-parameters-inspect-the-last-starting-values-0-fitStart-list"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-analysis-start-values.png?v=9b78ca639f61" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-start-values-overview-parameters-inspect-the-last-starting-values-0-fitStart-list)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-start-values-overview-parameters-inspect-the-last-starting-values-0-fitStart-list-1" data-gui-area="sidebar" data-gui-parts="[[784,336,682,253.5]]" d="M782.000 334.000 L1468.000 334.000 L1468.000 591.500 L782.000 591.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
