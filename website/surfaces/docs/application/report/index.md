---
template: gui.html
---

# :fa5-clipboard-list: Report

The **Report** page presents structures, experiments, fit information and correlations as one document. The shared [Report](../../user-guide/analysis-workflow/report.md) stage explains the document and its relationship to the saved project. This page covers the application controls.

<!-- sidebar-groups -->
| Sidebar group | Tab | Experiment types |
| --- | --- | --- |
| <span class="ed-reference-icon" aria-hidden="true">&#61465;</span> [Export](export.md) | Main | <a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> |
| <span class="ed-reference-icon" aria-hidden="true">&#61498;</span> [Contents](contents.md) | Main | <a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> |
| <span class="ed-reference-icon" aria-hidden="true">&#61787;</span> [Saved reports](saved-reports.md) | Main | <a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> |
<!-- /sidebar-groups -->

## Review the document

The main view shows the report with its figures and structure views. Inspect it after a fit, particularly the selected experiment, model values and charts. Each pattern chart has its hover, pan, zoom and reset buttons, and each structure view its camera buttons, as on the other pages; the exported HTML report's charts carry the same buttons.

The sidebar has **Export** and **Contents** groups.

<!-- gui-guide:review-the-document -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the report view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/14-report-basic.webp?v=0ac0de8754a3" data-gui-dark="750aeac2ad97" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-14-report-basic-overview-index-review-the-document-0-workflow-report-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/14-report-basic.webp?v=0ac0de8754a3" data-gui-dark="750aeac2ad97" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-index-review-the-document-0-workflow-report-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-index-review-the-document-0-workflow-report-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,799,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L794.000 78.000 Q798.000 78.000 798.000 82.000 L798.000 753.000 Q798.000 757.000 794.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/14-report-basic.webp?v=0ac0de8754a3" data-gui-dark="750aeac2ad97" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-14-report-basic-overview-index-review-the-document-0-workflow-report-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/14-report-basic.webp?v=0ac0de8754a3" data-gui-dark="750aeac2ad97" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-index-review-the-document-0-workflow-report-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-index-review-the-document-0-workflow-report-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[799,119,681,639],[799,77,43.515625,42]]" d="M800.000 124.000 Q800.000 120.000 800.000 116.000 L800.000 82.000 Q800.000 78.000 804.000 78.000 L837.516 78.000 Q841.516 78.000 841.516 82.000 L841.516 116.000 Q841.516 120.000 845.516 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 753.000 Q1479.000 757.000 1475.000 757.000 L804.000 757.000 Q800.000 757.000 800.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/14-report-basic.webp?v=0ac0de8754a3" data-gui-dark="750aeac2ad97" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-14-report-basic-overview-index-review-the-document-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/14-report-basic.webp?v=0ac0de8754a3" data-gui-dark="750aeac2ad97" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-index-review-the-document-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-index-review-the-document-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M1.000 763.000 Q1.000 759.000 5.000 759.000 L1475.000 759.000 Q1479.000 759.000 1479.000 763.000 L1479.000 795.000 Q1479.000 799.000 1475.000 799.000 L5.000 799.000 Q1.000 799.000 1.000 795.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Save the project too

Saving a project keeps the working model and report settings, but does not generate a new report. Save each for its purpose: the project for continuing the analysis, the report for communicating it.

The same report settings can be used from [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../../python/reports.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:fa5-terminal:</span> <span class="ed-icon-text">the Command line</span>](../../cli/reports.md){ .ed-interface-link .ed-icon-label }.

<!-- gui-guide:save-the-project-too -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Save as an EasyDiffraction folder or .zip, or export a copy.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-save.webp?v=55b6c6804c6c" data-gui-dark="bedb76a3fa7e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: project.saveAs.menu"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="project.saveAs.menu"><title>project.saveAs.menu</title><defs><clipPath id="gui-clip-guide-project-save-overview-index-save-the-project-too-0-project-saveAs-menu"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-save.webp?v=55b6c6804c6c" data-gui-dark="bedb76a3fa7e" width="1480" height="800" clip-path="url(#gui-clip-guide-project-save-overview-index-save-the-project-too-0-project-saveAs-menu)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-save-overview-index-save-the-project-too-0-project-saveAs-menu-1" data-gui-area="sidebar" data-gui-parts="[[1188.28125,215,284.71875,250.10000000000002]]" d="M1189.281 220.000 Q1189.281 216.000 1193.281 216.000 L1468.000 216.000 Q1472.000 216.000 1472.000 220.000 L1472.000 460.100 Q1472.000 464.100 1468.000 464.100 L1193.281 464.100 Q1189.281 464.100 1189.281 460.100 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
