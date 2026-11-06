---
template: gui.html
---

# :fa5-calculator: Analysis

Refinement adjusts the parameters you choose to bring the calculated result closer to the measured data. Begin with a structural model and experiment that plausibly describe the measurement; refinement is not a substitute for checking those choices.

The shared [Analysis](../../user-guide/analysis-workflow/analysis.md) chapter explains the scientific model; the steps below describe this interface.

<!-- sidebar-groups -->
| Sidebar group | Tab | Shown |
| --- | --- | --- |
| <span class="ed-reference-icon" aria-hidden="true">&#61451;</span> [Parameters](parameters.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#62398;</span> [Minimizer](minimizer.md) | Extra | With measured data |
| <span class="ed-reference-icon" aria-hidden="true">&#61918;</span> [Fitting mode](fitting-mode.md) | Extra | With measured data |
| <span class="ed-reference-icon" aria-hidden="true">&#61636;</span> [Fitted reflections](fitted-reflections.md) | Extra | Single crystal |
| <span class="ed-reference-icon" aria-hidden="true">&#61483;</span> [Aliases](aliases.md) | Extra | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#62764;</span> [Constraints](constraints.md) | Extra | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#61633;</span> [Joint-fit weights](joint-fit-weights.md) | Extra | Joint fit |
| <span class="ed-reference-icon" aria-hidden="true">&#61643;</span> [Sequential fit](sequential-fit.md) | Extra | Scan |
| <span class="ed-reference-icon" aria-hidden="true">&#61616;</span> [Scan extraction rules](scan-extraction-rules.md) | Extra | Scan |
| <span class="ed-reference-icon" aria-hidden="true">&#61914;</span> [Fit start values](fit-start-values.md) | Extra | After a fit |
| <span class="ed-reference-icon" aria-hidden="true">&#61528;</span> [Fit result](fit-result.md) | Extra | Recorded fit |
| <span class="ed-reference-icon" aria-hidden="true">&#61452;</span> [Experiment fit result](experiment-fit-result.md) | Extra | Recorded fit |
| <span class="ed-reference-icon" aria-hidden="true">&#61452;</span> [Structure fit result](structure-fit-result.md) | Extra | Recorded fit |
| <span class="ed-reference-icon" aria-hidden="true">&#61616;</span> [Parameters shown](parameters-shown.md) | Settings | With measured data |
| <span class="ed-reference-icon" aria-hidden="true">&#61953;</span> [Pattern updates during a scan](pattern-updates.md) | Settings | With measured data |
| <span class="ed-reference-icon" aria-hidden="true">&#62461;</span> [Performance](performance.md) | Settings | Scan |
<!-- /sidebar-groups -->

## Load or prepare the project

Open an existing project or an included example on **Project**. To analyse your own measurement, follow [create a project](../project/get-started.md).

On **Structure**, check symmetry, cell and atom sites. On **Experiment**, check the data, instrument, peak profile, [background](../experiment/background.md), excluded regions and linked structures.

<!-- gui-guide:load-or-prepare-the-project -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61587;</span>Open project…"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Open or save the current project.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-actions.png?v=14ec62b49de2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Open project…"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Open project…"><title>Open project…</title><defs><clipPath id="gui-clip-guide-project-actions-overview-index-load-or-prepare-the-project-0-project-open"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-actions.png?v=14ec62b49de2" width="1480" height="800" clip-path="url(#gui-clip-guide-project-actions-overview-index-load-or-prepare-the-project-0-project-open)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-actions-overview-index-load-or-prepare-the-project-0-project-open-1" data-gui-area="sidebar" data-gui-parts="[[1132,168,334,39]]" d="M1130.000 166.000 L1468.000 166.000 L1468.000 209.000 L1130.000 209.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#62830;</span>Save project as…"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Open or save the current project.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-actions.png?v=14ec62b49de2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save project as…"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save project as…"><title>Save project as…</title><defs><clipPath id="gui-clip-guide-project-actions-overview-index-load-or-prepare-the-project-0-project-saveAs"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-actions.png?v=14ec62b49de2" width="1480" height="800" clip-path="url(#gui-clip-guide-project-actions-overview-index-load-or-prepare-the-project-0-project-saveAs)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-actions-overview-index-load-or-prepare-the-project-0-project-saveAs-1" data-gui-area="sidebar" data-gui-parts="[[784,221,334,39]]" d="M782.000 219.000 L1120.000 219.000 L1120.000 262.000 L782.000 262.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Compare the starting pattern

Look at peak positions, widths, intensities and the background before fitting. An incorrect wavelength or calibration can shift peaks; a missing phase can leave intensity the model cannot explain.

<!-- gui-guide:compare-the-starting-pattern -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-10-experiment-loaded-overview-index-compare-the-starting-pattern-0-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" width="1480" height="800" clip-path="url(#gui-clip-10-experiment-loaded-overview-index-compare-the-starting-pattern-0-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="10-experiment-loaded-overview-index-compare-the-starting-pattern-0-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-10-experiment-loaded-overview-index-compare-the-starting-pattern-0-workflow-experiment-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" width="1480" height="800" clip-path="url(#gui-clip-10-experiment-loaded-overview-index-compare-the-starting-pattern-0-workflow-experiment-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="10-experiment-loaded-overview-index-compare-the-starting-pattern-0-workflow-experiment-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Choose free parameters

On **Analysis**, the parameter table lists every numerical input of the structures and experiments. Use the **free** column to choose which parameters may vary. When a fit cannot vary a value, its checkbox is disabled and hovering over it shows the reason. The name and variability filters help you find them.

A value cannot be fitted when it describes the setup, symmetry or a constraint sets it, the fit's data cannot determine it, or the calculation has no derivative for it yet. A value saved as free that cannot be fitted opens as fixed, and **Messages** says so. The minimum and maximum displayed in the table describe admissible model values; they are not a separate set of user-defined optimizer bounds.

Free parameters deliberately, checking the effect of each stage. Starting with every parameter free can hide an unsuitable model behind strongly correlated values.

<!-- gui-guide:choose-free-parameters -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-index-choose-free-parameters-0-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-index-choose-free-parameters-0-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-index-choose-free-parameters-0-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-index-choose-free-parameters-0-workflow-analysis-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-index-choose-free-parameters-0-workflow-analysis-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-index-choose-free-parameters-0-workflow-analysis-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-index-choose-free-parameters-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-index-choose-free-parameters-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-index-choose-free-parameters-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M-2.000 756.000 L1482.000 756.000 L1482.000 802.000 L-2.000 802.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Select a fitting mode

The available mode depends on the project. One experiment is fitted on its own; several experiments can be fitted jointly. A scan can run sequentially or independently across its datasets. See [fitting modes](fitting-mode.md).

<!-- gui-guide:select-a-fitting-mode -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">The available choices depend on the project.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-analysis-modes.png?v=0ee89cab5a74" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-guide-analysis-modes-overview-index-select-a-fitting-mode-0-fittingMode-type"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-analysis-modes.png?v=0ee89cab5a74" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-modes-overview-index-select-a-fitting-mode-0-fittingMode-type)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-modes-overview-index-select-a-fitting-mode-0-fittingMode-type-1" data-gui-area="sidebar" data-gui-parts="[[784,210,682,56]]" d="M782.000 208.000 L1468.000 208.000 L1468.000 268.000 L782.000 268.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Start and inspect the fit

Press **Fit** at the right of the status bar. Review the calculated curve and residual as well as the reported agreement factors. Parameter uncertainties and correlations help you understand what the data constrain.

A small agreement factor alone does not establish that the structural model is correct. Inspect unmodelled features and physically implausible values before accepting the result.

<!-- gui-guide:start-and-inspect-the-fit -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-index-start-and-inspect-the-fit-0-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-index-start-and-inspect-the-fit-0-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-index-start-and-inspect-the-fit-0-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-index-start-and-inspect-the-fit-0-workflow-analysis-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-index-start-and-inspect-the-fit-0-workflow-analysis-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-index-start-and-inspect-the-fit-0-workflow-analysis-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-index-start-and-inspect-the-fit-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-index-start-and-inspect-the-fit-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-index-start-and-inspect-the-fit-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M-2.000 756.000 L1482.000 756.000 L1482.000 802.000 L-2.000 802.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Inspect parameter correlations

Open **Correlations** in the Analysis main view after fitting. Inspect strongly related free parameters alongside their uncertainties and the residual. A correlation can reveal that the data do not determine two values independently; see [covariance and correlations](../../physics/minimization.md#eq-covariance).

<!-- gui-guide:inspect-parameter-correlations -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-analysis-correlations.png?v=5c1b491fd083" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-guide-analysis-correlations-overview-index-inspect-parameter-correlations-0-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-analysis-correlations.png?v=5c1b491fd083" width="1480" height="800" clip-path="url(#gui-clip-guide-analysis-correlations-overview-index-inspect-parameter-correlations-0-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-analysis-correlations-overview-index-inspect-parameter-correlations-0-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Read recorded fit statistics

Open a fitted project and select **Analysis → Extra** to inspect its recorded results. **Fit result** holds the overall outcome and statistics; **Experiment fit result** separates the measurements; **Structure fit result** reports the structure's reflection agreement for each experiment.

These groups are read-only. Assess the [agreement factors](../../physics/reliability.md) alongside the pattern, uncertainties and parameter correlations.

<!-- gui-guide:read-recorded-fit-statistics -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61528;</span>Fit result"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the overall outcome and statistics of the completed fit</p>
    <a class="gui-image-link" href="../../assets/gui/joint/joint-result.png?v=4be3b4572054" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the overall outcome and statistics of the completed fit"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the overall outcome and statistics of the completed fit"><title>Inspect the overall outcome and statistics of the completed fit</title><defs><clipPath id="gui-clip-joint-result-overview-index-read-recorded-fit-statistics-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/joint/joint-result.png?v=4be3b4572054" width="1480" height="800" clip-path="url(#gui-clip-joint-result-overview-index-read-recorded-fit-statistics-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="joint-result-overview-index-read-recorded-fit-statistics-0-1" data-gui-area="sidebar" data-gui-parts="[[770,371,710,373]]" d="M768.000 369.000 L1482.000 369.000 L1482.000 746.000 L768.000 746.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61452;</span>Experiment fit result"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Compare fit statistics for the individual experiments</p>
    <a class="gui-image-link" href="../../assets/gui/joint/joint-experiment-results.png?v=bd0f8a2cf32b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Compare fit statistics for the individual experiments"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Compare fit statistics for the individual experiments"><title>Compare fit statistics for the individual experiments</title><defs><clipPath id="gui-clip-joint-experiment-results-overview-index-read-recorded-fit-statistics-1"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/joint/joint-experiment-results.png?v=bd0f8a2cf32b" width="1480" height="800" clip-path="url(#gui-clip-joint-experiment-results-overview-index-read-recorded-fit-statistics-1)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="joint-experiment-results-overview-index-read-recorded-fit-statistics-1-1" data-gui-area="sidebar" data-gui-parts="[[770,413,710,180]]" d="M768.000 411.000 L1482.000 411.000 L1482.000 595.000 L768.000 595.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61452;</span>Structure fit result"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the structure contributions recorded for each experiment</p>
    <a class="gui-image-link" href="../../assets/gui/joint/joint-structure-results.png?v=d7f7ef9560b8" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the structure contributions recorded for each experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the structure contributions recorded for each experiment"><title>Inspect the structure contributions recorded for each experiment</title><defs><clipPath id="gui-clip-joint-structure-results-overview-index-read-recorded-fit-statistics-2"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/joint/joint-structure-results.png?v=d7f7ef9560b8" width="1480" height="800" clip-path="url(#gui-clip-joint-structure-results-overview-index-read-recorded-fit-statistics-2)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="joint-structure-results-overview-index-read-recorded-fit-statistics-2-1" data-gui-area="sidebar" data-gui-parts="[[770,455,710,180]]" d="M768.000 453.000 L1482.000 453.000 L1482.000 637.000 L768.000 637.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Save the project and report

Save the updated project if you want to keep working from its refined values. Use the **Report** page to prepare a separate document containing the selected model, results and figures.

The same project can be opened in [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../../python/fit.md){ .ed-interface-link .ed-icon-label } or run with [<span class="ed-interface-icons" aria-hidden="true">:fa5-terminal:</span> <span class="ed-icon-text">the Command Line</span>](../../cli/fit.md){ .ed-interface-link .ed-icon-label }.

<!-- gui-guide:save-the-project-and-report -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Review the saved report status.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-saved.png?v=832096e9743b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Export"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Export"><title>Export</title><defs><clipPath id="gui-clip-guide-report-saved-overview-index-save-the-project-and-report-0-group-reportExport"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-saved.png?v=832096e9743b" width="1480" height="800" clip-path="url(#gui-clip-guide-report-saved-overview-index-save-the-project-and-report-0-group-reportExport)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-saved-overview-index-save-the-project-and-report-0-group-reportExport-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,249]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 370.000 L768.000 370.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
