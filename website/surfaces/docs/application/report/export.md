---
category_glyph: "\uf019"
template: gui.html
---

# <span class="ed-reference-icon" aria-hidden="true">&#61465;</span> Export

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a></p>
<!-- /group-tags -->

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
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-export.png?v=7977cfedbbdb" data-gui-dark="40fe15d27d0a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: HTML report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="HTML report"><title>HTML report</title><defs><clipPath id="gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesHtml"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-export.png?v=7977cfedbbdb" data-gui-dark="40fe15d27d0a" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesHtml)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-export-choose-output-formats-0-report-writesHtml-1" data-gui-area="sidebar" data-gui-parts="[[784,175,70.46875,21]]" d="M785.000 180.000 Q785.000 176.000 789.000 176.000 L849.469 176.000 Q853.469 176.000 853.469 180.000 L853.469 191.000 Q853.469 195.000 849.469 195.000 L789.000 195.000 Q785.000 195.000 785.000 191.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

=== "PDF report"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select a PDF document.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-export.png?v=7977cfedbbdb" data-gui-dark="40fe15d27d0a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: PDF report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="PDF report"><title>PDF report</title><defs><clipPath id="gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesPdf"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-export.png?v=7977cfedbbdb" data-gui-dark="40fe15d27d0a" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesPdf)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-export-choose-output-formats-0-report-writesPdf-1" data-gui-area="sidebar" data-gui-parts="[[784,224,70.46875,21]]" d="M785.000 229.000 Q785.000 225.000 789.000 225.000 L849.469 225.000 Q853.469 225.000 853.469 229.000 L853.469 240.000 Q853.469 244.000 849.469 244.000 L789.000 244.000 Q785.000 244.000 785.000 240.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

=== "CIF report"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select a crystallographic report.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-export.png?v=7977cfedbbdb" data-gui-dark="40fe15d27d0a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: CIF report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="CIF report"><title>CIF report</title><defs><clipPath id="gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesCif"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-export.png?v=7977cfedbbdb" data-gui-dark="40fe15d27d0a" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-writesCif)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-export-choose-output-formats-0-report-writesCif-1" data-gui-area="sidebar" data-gui-parts="[[784,273,70.46875,21]]" d="M785.000 278.000 Q785.000 274.000 789.000 274.000 L849.469 274.000 Q853.469 274.000 853.469 278.000 L853.469 289.000 Q853.469 293.000 849.469 293.000 L789.000 293.000 Q785.000 293.000 785.000 289.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61465;</span>Save report"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Write the selected report formats.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-export.png?v=7977cfedbbdb" data-gui-dark="40fe15d27d0a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save report"><title>Save report</title><defs><clipPath id="gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-save"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-export.png?v=7977cfedbbdb" data-gui-dark="40fe15d27d0a" width="1480" height="800" clip-path="url(#gui-clip-guide-report-export-overview-export-choose-output-formats-0-report-save)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-export-overview-export-choose-output-formats-0-report-save-1" data-gui-area="sidebar" data-gui-parts="[[784,315,682,39]]" d="M785.000 320.000 Q785.000 316.000 789.000 316.000 L1461.000 316.000 Q1465.000 316.000 1465.000 320.000 L1465.000 349.000 Q1465.000 353.000 1461.000 353.000 L789.000 353.000 Q785.000 353.000 785.000 349.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

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
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-report-saved.png?v=2671e453bc93" data-gui-dark="5da28dc0df22" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Export"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Export"><title>Export</title><defs><clipPath id="gui-clip-guide-report-saved-overview-export-save-the-report-0-group-reportExport"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-report-saved.png?v=2671e453bc93" data-gui-dark="5da28dc0df22" width="1480" height="800" clip-path="url(#gui-clip-guide-report-saved-overview-export-save-the-report-0-group-reportExport)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-report-saved-overview-export-save-the-report-0-group-reportExport-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,249]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 363.000 Q1479.000 367.000 1475.000 367.000 L775.000 367.000 Q771.000 367.000 771.000 363.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
