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

A project can read measured data from files outside its folder. On **Project → Extra**, expand **Data on save** to choose what a save does with them: copy every file into the project, keep linked files linked, or ask on every save. The choice is kept for this project's folder. Until you choose, a save copies the data when it is small (up to 20 files and 50 MB) and keeps larger data linked.

<!-- gui-guide:what-is-saved -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61525;</span>Create a new project"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Open the project-details form.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-actions.webp?v=0e3ba78e1258" data-gui-dark="b842554ecf8d" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create a new project"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create a new project"><title>Create a new project</title><defs><clipPath id="gui-clip-guide-project-actions-overview-index-what-is-saved-0-project-create"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-actions.webp?v=0e3ba78e1258" data-gui-dark="b842554ecf8d" width="1480" height="800" clip-path="url(#gui-clip-guide-project-actions-overview-index-what-is-saved-0-project-create)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-actions-overview-index-what-is-saved-0-project-create-1" data-gui-area="sidebar" data-gui-parts="[[813,168,208.33333333333337,39]]" d="M814.000 173.000 Q814.000 169.000 818.000 169.000 L1016.333 169.000 Q1020.333 169.000 1020.333 173.000 L1020.333 202.000 Q1020.333 206.000 1016.333 206.000 L818.000 206.000 Q814.000 206.000 814.000 202.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61587;</span>Load project"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Create, load or save a project.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-actions.webp?v=0e3ba78e1258" data-gui-dark="b842554ecf8d" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load project"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load project"><title>Load project</title><defs><clipPath id="gui-clip-guide-project-actions-overview-index-what-is-saved-0-project-load"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-actions.webp?v=0e3ba78e1258" data-gui-dark="b842554ecf8d" width="1480" height="800" clip-path="url(#gui-clip-guide-project-actions-overview-index-what-is-saved-0-project-load)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-actions-overview-index-what-is-saved-0-project-load-1" data-gui-area="sidebar" data-gui-parts="[[1035.3333333333333,168,208.33333333333326,39]]" d="M1036.333 173.000 Q1036.333 169.000 1040.333 169.000 L1238.667 169.000 Q1242.667 169.000 1242.667 173.000 L1242.667 202.000 Q1242.667 206.000 1238.667 206.000 L1040.333 206.000 Q1036.333 206.000 1036.333 202.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#62830;</span>Save project as"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Create, load or save a project.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-actions.webp?v=0e3ba78e1258" data-gui-dark="b842554ecf8d" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save project as"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save project as"><title>Save project as</title><defs><clipPath id="gui-clip-guide-project-actions-overview-index-what-is-saved-0-project-saveAs"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-actions.webp?v=0e3ba78e1258" data-gui-dark="b842554ecf8d" width="1480" height="800" clip-path="url(#gui-clip-guide-project-actions-overview-index-what-is-saved-0-project-saveAs)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-actions-overview-index-what-is-saved-0-project-saveAs-1" data-gui-area="sidebar" data-gui-parts="[[1257.6666666666667,168,208.33333333333326,39]]" d="M1258.667 173.000 Q1258.667 169.000 1262.667 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 202.000 Q1465.000 206.000 1461.000 206.000 L1262.667 206.000 Q1258.667 206.000 1258.667 202.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

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
<p class="gui-view-description">Open a project folder or archive, or import one from another program.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-open.webp?v=1fa1b1688db7" data-gui-dark="469cac9a501b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: project.load.menu"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="project.load.menu"><title>project.load.menu</title><defs><clipPath id="gui-clip-guide-project-open-overview-index-browser-file-handling-0-project-load-menu"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-open.webp?v=1fa1b1688db7" data-gui-dark="469cac9a501b" width="1480" height="800" clip-path="url(#gui-clip-guide-project-open-overview-index-browser-file-handling-0-project-load-menu)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-open-overview-index-browser-file-handling-0-project-load-menu-1" data-gui-area="sidebar" data-gui-parts="[[1035.3333333333333,215,315.3125,250.10000000000002]]" d="M1036.333 220.000 Q1036.333 216.000 1040.333 216.000 L1345.646 216.000 Q1349.646 216.000 1349.646 220.000 L1349.646 460.100 Q1349.646 464.100 1345.646 464.100 L1040.333 464.100 Q1036.333 464.100 1036.333 460.100 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Move to another interface

Open the saved folder, `project.edi` or archive from [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../../python/index.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:fa5-terminal:</span> <span class="ed-icon-text">the Command line</span>](../../cli/index.md){ .ed-interface-link .ed-icon-label }. The shared [project concepts](../../user-guide/analysis-workflow/project.md) explain what those interfaces read.

<!-- gui-guide:move-to-another-interface -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Save as an EasyDiffraction folder or .zip, or export a copy.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-project-save.webp?v=55b6c6804c6c" data-gui-dark="bedb76a3fa7e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: project.saveAs.menu"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="project.saveAs.menu"><title>project.saveAs.menu</title><defs><clipPath id="gui-clip-guide-project-save-overview-index-move-to-another-interface-0-project-saveAs-menu"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-project-save.webp?v=55b6c6804c6c" data-gui-dark="bedb76a3fa7e" width="1480" height="800" clip-path="url(#gui-clip-guide-project-save-overview-index-move-to-another-interface-0-project-saveAs-menu)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-save-overview-index-move-to-another-interface-0-project-saveAs-menu-1" data-gui-area="sidebar" data-gui-parts="[[1188.28125,215,284.71875,250.10000000000002]]" d="M1189.281 220.000 Q1189.281 216.000 1193.281 216.000 L1468.000 216.000 Q1472.000 216.000 1472.000 220.000 L1472.000 460.100 Q1472.000 464.100 1468.000 464.100 L1193.281 464.100 Q1189.281 464.100 1189.281 460.100 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
