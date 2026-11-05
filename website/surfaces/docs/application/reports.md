---
template: gui.html
---

# :material-clipboard-text: Review and save a report

The **Report** page presents structures, experiments, fit information and correlations as one document. The shared [Report](../user-guide/analysis-workflow/report.md) stage explains the document and its relationship to the saved project. This page covers the application controls.

## Review the document

The main view shows the report with its figures and structure views. Inspect it after a fit, particularly the selected experiment, model values and charts.

The sidebar has **Export** and **Contents** groups.

<!-- gui-guide:review-the-document -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the report view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-14-report-basic-overview-reports-review-the-document-0-workflow-report-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-reports-review-the-document-0-workflow-report-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-reports-review-the-document-0-workflow-report-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-14-report-basic-overview-reports-review-the-document-0-workflow-report-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-reports-review-the-document-0-workflow-report-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-reports-review-the-document-0-workflow-report-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-14-report-basic-overview-reports-review-the-document-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-reports-review-the-document-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-reports-review-the-document-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M-2.000 756.000 L1482.000 756.000 L1482.000 802.000 L-2.000 802.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Choose the contents

**Contents** controls the optional parts of the document: charts, correlations, reflections, measured data points and, for a scan, parameter evolution. Data tables can be long, so data points are initially left out.

These choices are saved with the project. They do not change which data were fitted.

<!-- gui-guide:choose-the-contents -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose which sections appear in the report.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-report-contents.png?v=0c3218636110" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Contents"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Contents"><title>Contents</title><defs><clipPath id="gui-clip-guide-report-contents-overview-reports-choose-the-contents-0-group-reportContents"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-report-contents.png?v=0c3218636110" width="1480" height="800" clip-path="url(#gui-clip-guide-report-contents-overview-reports-choose-the-contents-0-group-reportContents)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-contents-overview-reports-choose-the-contents-0-group-reportContents-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,189]]" d="M768.000 159.000 L1482.000 159.000 L1482.000 352.000 L768.000 352.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Choose output formats

| Format | Use it for |
| --- | --- |
| HTML | An interactive document with pattern zoom, hover and structure controls |
| PDF | A paginated document with static figures |
| CIF | A crystallographic report with the fit result and a data block for each structure and experiment, every item under its official CIF name |

The HTML export option can embed the chart libraries for offline use. Without embedding, the document loads those libraries from the web when opened.

The PDF uses A4 pages and light-colour figures. The application writes PDF; Python and Command Line report generation share the report model and settings but do not write that application PDF.

<!-- gui-guide:choose-output-formats -->
<div class="gui-viewer" markdown="1">


=== "HTML report"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select an HTML document.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: HTML report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="HTML report"><title>HTML report</title><defs><clipPath id="gui-clip-guide-report-export-overview-reports-choose-output-formats-0-report-writesHtml"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-reports-choose-output-formats-0-report-writesHtml)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-reports-choose-output-formats-0-report-writesHtml-1" data-gui-area="sidebar" data-gui-parts="[[784,175,70.46875,21]]" d="M782.000 173.000 L856.469 173.000 L856.469 198.000 L782.000 198.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "PDF report"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select a PDF document.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: PDF report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="PDF report"><title>PDF report</title><defs><clipPath id="gui-clip-guide-report-export-overview-reports-choose-output-formats-0-report-writesPdf"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-reports-choose-output-formats-0-report-writesPdf)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-reports-choose-output-formats-0-report-writesPdf-1" data-gui-area="sidebar" data-gui-parts="[[784,224,70.46875,21]]" d="M782.000 222.000 L856.469 222.000 L856.469 247.000 L782.000 247.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "CIF report"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select a crystallographic report.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: CIF report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="CIF report"><title>CIF report</title><defs><clipPath id="gui-clip-guide-report-export-overview-reports-choose-output-formats-0-report-writesCif"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-reports-choose-output-formats-0-report-writesCif)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-reports-choose-output-formats-0-report-writesCif-1" data-gui-area="sidebar" data-gui-parts="[[784,273,70.46875,21]]" d="M782.000 271.000 L856.469 271.000 L856.469 296.000 L782.000 296.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61465;</span>Save report"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Write the selected report formats.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save report"><title>Save report</title><defs><clipPath id="gui-clip-guide-report-export-overview-reports-choose-output-formats-0-report-save"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-reports-choose-output-formats-0-report-save)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-reports-choose-output-formats-0-report-save-1" data-gui-area="sidebar" data-gui-parts="[[784,315,682,39]]" d="M782.000 313.000 L1468.000 313.000 L1468.000 356.000 L782.000 356.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Save the report

Select the desired formats in **Export**, then choose **Save report**. The files are written to the project's `reports/` folder, inside the zip when the project is a zip archive. An example or a read-only archive cannot be written back, so the desktop app first asks where to save the project, then saves the report there. The web app also downloads the report files, as one file or one zip of them.

Turning off a format leaves any previously saved file in place; it does not delete it.

<!-- gui-guide:save-the-report -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Review the saved report status.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-report-saved.png?v=832096e9743b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Export"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Export"><title>Export</title><defs><clipPath id="gui-clip-guide-report-saved-overview-reports-save-the-report-0-group-reportExport"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-report-saved.png?v=832096e9743b" width="1480" height="800" clip-path="url(#gui-clip-guide-report-saved-overview-reports-save-the-report-0-group-reportExport)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-saved-overview-reports-save-the-report-0-group-reportExport-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,249]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 370.000 L768.000 370.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Keep saved reports current

Saved reports are listed with their saved time. A report is marked **out of date** when the document the project would produce now differs from it, for example after a fit or a change to Contents. **Missing** means the saved file is no longer present.

Use **Save report** again to bring the selected formats up to date. The status survives reopening the project.

<!-- gui-guide:keep-saved-reports-current -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Review the saved report status.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-report-saved.png?v=832096e9743b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Export"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Export"><title>Export</title><defs><clipPath id="gui-clip-guide-report-saved-overview-reports-keep-saved-reports-current-0-group-reportExport"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-report-saved.png?v=832096e9743b" width="1480" height="800" clip-path="url(#gui-clip-guide-report-saved-overview-reports-keep-saved-reports-current-0-group-reportExport)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-saved-overview-reports-keep-saved-reports-current-0-group-reportExport-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,249]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 370.000 L768.000 370.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Save the project too

Saving a project keeps the working model and report settings, but does not generate a new report. Save each for its purpose: the project for continuing the analysis, the report for communicating it.

The same report settings can be used from [<span class="ed-interface-icons" aria-hidden="true">:simple-python: :simple-jupyter:</span> <span class="ed-icon-text">Python</span>](../python/reports.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:lucide-square-terminal: :simple-python:</span> <span class="ed-icon-text">the Command Line</span>](../cli/reports.md){ .ed-interface-link .ed-icon-label }.

<!-- gui-guide:save-the-project-too -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the output format and whether to save a copy.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-project-save.png?v=6668eba38bd5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save options"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save options"><title>Save options</title><defs><clipPath id="gui-clip-guide-project-save-overview-reports-save-the-project-too-0-project-saveChoice"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-project-save.png?v=6668eba38bd5" width="1480" height="800" clip-path="url(#gui-clip-guide-project-save-overview-reports-save-the-project-too-0-project-saveChoice)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-save-overview-reports-save-the-project-too-0-project-saveChoice-1" data-gui-area="main" data-gui-parts="[[607,354,111.84375,93]]" d="M605.000 352.000 L720.844 352.000 L720.844 449.000 L605.000 449.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
