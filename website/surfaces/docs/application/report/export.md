---
category_glyph: "\uf019"
template: gui.html
---

# <span class="ed-reference-icon" aria-hidden="true">&#61465;</span> Export

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
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: HTML report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="HTML report"><title>HTML report</title><defs><clipPath id="gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesHtml"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesHtml)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-export-choose-output-formats-0-report-writesHtml-1" data-gui-area="sidebar" data-gui-parts="[[784,175,70.46875,21]]" d="M782.000 173.000 L856.469 173.000 L856.469 198.000 L782.000 198.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "PDF report"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select a PDF document.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: PDF report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="PDF report"><title>PDF report</title><defs><clipPath id="gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesPdf"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesPdf)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-export-choose-output-formats-0-report-writesPdf-1" data-gui-area="sidebar" data-gui-parts="[[784,224,70.46875,21]]" d="M782.000 222.000 L856.469 222.000 L856.469 247.000 L782.000 247.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "CIF report"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select a crystallographic report.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: CIF report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="CIF report"><title>CIF report</title><defs><clipPath id="gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesCif"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesCif)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-export-choose-output-formats-0-report-writesCif-1" data-gui-area="sidebar" data-gui-parts="[[784,273,70.46875,21]]" d="M782.000 271.000 L856.469 271.000 L856.469 296.000 L782.000 296.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61465;</span>Save report"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Write the selected report formats.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save report"><title>Save report</title><defs><clipPath id="gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-save"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-export.png?v=6390470b7488" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-save)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-export-choose-output-formats-0-report-save-1" data-gui-area="sidebar" data-gui-parts="[[784,315,682,39]]" d="M782.000 313.000 L1468.000 313.000 L1468.000 356.000 L782.000 356.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

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
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-saved.png?v=832096e9743b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Export"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Export"><title>Export</title><defs><clipPath id="gui-clip-guide-report-saved-overview-export-save-the-report-0-group-reportExport"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-saved.png?v=832096e9743b" width="1480" height="800" clip-path="url(#gui-clip-guide-report-saved-overview-export-save-the-report-0-group-reportExport)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-saved-overview-export-save-the-report-0-group-reportExport-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,249]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 370.000 L768.000 370.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
