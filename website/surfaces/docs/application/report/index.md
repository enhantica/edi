---
template: gui.html
---

# :fa5-clipboard-list: Report

The **Report** page presents structures, experiments, fit information and correlations as one document. The shared [Report](../../user-guide/analysis-workflow/report.md) stage explains the document and its relationship to the saved project. This page covers the application controls.

<!-- sidebar-groups -->
| Sidebar group | Tab | Shown |
| --- | --- | --- |
| <span class="ed-reference-icon" aria-hidden="true">&#61465;</span> [Export](export.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#61498;</span> [Contents](contents.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#61787;</span> [Saved reports](saved-reports.md) | Main | After saving a report |
<!-- /sidebar-groups -->

## Review the document

The main view shows the report with its figures and structure views. Inspect it after a fit, particularly the selected experiment, model values and charts.

The sidebar has **Export** and **Contents** groups.

<!-- gui-guide:review-the-document -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the report view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-14-report-basic-overview-index-review-the-document-0-workflow-report-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-index-review-the-document-0-workflow-report-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-index-review-the-document-0-workflow-report-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-14-report-basic-overview-index-review-the-document-0-workflow-report-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-index-review-the-document-0-workflow-report-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-index-review-the-document-0-workflow-report-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-14-report-basic-overview-index-review-the-document-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-index-review-the-document-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-index-review-the-document-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M-2.000 756.000 L1482.000 756.000 L1482.000 802.000 L-2.000 802.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Save the project too

Saving a project keeps the working model and report settings, but does not generate a new report. Save each for its purpose: the project for continuing the analysis, the report for communicating it.

The same report settings can be used from [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../../python/reports.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:fa5-terminal:</span> <span class="ed-icon-text">the Command Line</span>](../../cli/reports.md){ .ed-interface-link .ed-icon-label }.

<!-- gui-guide:save-the-project-too -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the output format and whether to save a copy.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-save.png?v=6668eba38bd5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save options"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save options"><title>Save options</title><defs><clipPath id="gui-clip-guide-project-save-overview-index-save-the-project-too-0-project-saveChoice"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-save.png?v=6668eba38bd5" width="1480" height="800" clip-path="url(#gui-clip-guide-project-save-overview-index-save-the-project-too-0-project-saveChoice)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-save-overview-index-save-the-project-too-0-project-saveChoice-1" data-gui-area="main" data-gui-parts="[[607,354,111.84375,93]]" d="M605.000 352.000 L720.844 352.000 L720.844 449.000 L605.000 449.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
