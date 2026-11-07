---
template: gui.html
---

# :fa5-archive: Project

Use the application to open, save and export the complete analysis. The shared [Project](../../user-guide/analysis-workflow/project.md) stage explains what belongs in a project; [data formats](../../user-guide/data-formats.md) explains its folder and archive representations.

!!! note "Saving in the browser"

    Check the project location before closing the app. **In this browser only** means the project is in browser storage; use **Save project as…** to keep an external copy. [Browser-specific saving](../browser.md#open-and-save-files) explains folders, archives and downloads.

<!-- sidebar-groups -->
| Sidebar group | Tab | Experiment types |
| --- | --- | --- |
| <span class="ed-reference-icon" aria-hidden="true">&#61749;</span> [Get started](get-started.md) | Main | <a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> |
| <span class="ed-reference-icon" aria-hidden="true">&#61888;</span> [Examples](examples.md) | Main | <a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> |
| <span class="ed-reference-icon" aria-hidden="true">&#61831;</span> [Recent projects](recent-projects.md) | Main | <a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> |
| <span class="ed-reference-icon" aria-hidden="true">&#62791;</span> [Standard uncertainties](standard-uncertainties.md) | Extra | <a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> |
<!-- /sidebar-groups -->

## What is saved

Saving writes the project state and measured data, including the selected analysis settings. Values are rounded according to the project's precision and uncertainty policy. The open project is updated to those saved values and its calculated pattern and agreement factors are recalculated from them.

A report is separate: saving a project does not create a fresh report. Use [Save report](../report/index.md) to update a document you intend to share.

<!-- gui-guide:what-is-saved -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61587;</span>Open project…"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Open or save the current project.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-actions.png?v=9988750d8d39" data-gui-dark="9b69be99a0bd" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Open project…"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Open project…"><title>Open project…</title><defs><clipPath id="gui-clip-guide-project-actions-overview-index-what-is-saved-0-project-open"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-actions.png?v=9988750d8d39" data-gui-dark="9b69be99a0bd" width="1480" height="800" clip-path="url(#gui-clip-guide-project-actions-overview-index-what-is-saved-0-project-open)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-actions-overview-index-what-is-saved-0-project-open-1" data-gui-area="sidebar" data-gui-parts="[[1132,168,334,39]]" d="M1133.000 173.000 Q1133.000 169.000 1137.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 202.000 Q1465.000 206.000 1461.000 206.000 L1137.000 206.000 Q1133.000 206.000 1133.000 202.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#62830;</span>Save project as…"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Open or save the current project.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-actions.png?v=9988750d8d39" data-gui-dark="9b69be99a0bd" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save project as…"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save project as…"><title>Save project as…</title><defs><clipPath id="gui-clip-guide-project-actions-overview-index-what-is-saved-0-project-saveAs"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-actions.png?v=9988750d8d39" data-gui-dark="9b69be99a0bd" width="1480" height="800" clip-path="url(#gui-clip-guide-project-actions-overview-index-what-is-saved-0-project-saveAs)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-actions-overview-index-what-is-saved-0-project-saveAs-1" data-gui-area="sidebar" data-gui-parts="[[784,221,334,39]]" d="M785.000 226.000 Q785.000 222.000 789.000 222.000 L1113.000 222.000 Q1117.000 222.000 1117.000 226.000 L1117.000 255.000 Q1117.000 259.000 1113.000 259.000 L789.000 259.000 Q785.000 259.000 785.000 255.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Browser file handling

| Browser workflow | What Save does | How to keep a separate copy |
| --- | --- | --- |
| Chrome or Edge, project opened from a selected folder or archive | Writes back to that selected location when access is available | **Save project as…** chooses a folder or archive |
| Firefox or Safari | Saves the browser-held project | **Save project as…** downloads a zip copy |
| An example or new project in any browser | Initially keeps the project in browser storage | **Save project as…** exports a zip copy |
| A private window without persistent storage | The project may exist only in the current tab | Export with **Save project as…** before closing |

The location **In this browser only** means that browser storage is holding your project. Browsers can clear that storage; keep a copy on your computer for work you need to retain.

<!-- gui-guide:browser-file-handling -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose a folder or a zip archive.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-open.png?v=1fa458bd07c4" data-gui-dark="75f65a694507" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Project source"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Project source"><title>Project source</title><defs><clipPath id="gui-clip-guide-project-open-overview-index-browser-file-handling-0-project-openChoice"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-open.png?v=1fa458bd07c4" data-gui-dark="75f65a694507" width="1480" height="800" clip-path="url(#gui-clip-guide-project-open-overview-index-browser-file-handling-0-project-openChoice)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-open-overview-index-browser-file-handling-0-project-openChoice-1" data-gui-area="main" data-gui-parts="[[607,371,97.96562500000005,58]]" d="M608.000 376.000 Q608.000 372.000 612.000 372.000 L699.966 372.000 Q703.966 372.000 703.966 376.000 L703.966 424.000 Q703.966 428.000 699.966 428.000 L612.000 428.000 Q608.000 428.000 608.000 424.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Move to another interface

Open the saved folder, `project.edi` or archive from [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../../python/index.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:fa5-terminal:</span> <span class="ed-icon-text">the Command Line</span>](../../cli/index.md){ .ed-interface-link .ed-icon-label }. The shared [project concepts](../../user-guide/analysis-workflow/project.md) explain what those interfaces read.

<!-- gui-guide:move-to-another-interface -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the output format and whether to save a copy.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-save.png?v=65ead927e96b" data-gui-dark="100c21dceb0b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save options"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save options"><title>Save options</title><defs><clipPath id="gui-clip-guide-project-save-overview-index-move-to-another-interface-0-project-saveChoice"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-save.png?v=65ead927e96b" data-gui-dark="100c21dceb0b" width="1480" height="800" clip-path="url(#gui-clip-guide-project-save-overview-index-move-to-another-interface-0-project-saveChoice)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-save-overview-index-move-to-another-interface-0-project-saveChoice-1" data-gui-area="main" data-gui-parts="[[607,354,111.84375,93]]" d="M608.000 359.000 Q608.000 355.000 612.000 355.000 L713.844 355.000 Q717.844 355.000 717.844 359.000 L717.844 442.000 Q717.844 446.000 713.844 446.000 L612.000 446.000 Q608.000 446.000 608.000 442.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
