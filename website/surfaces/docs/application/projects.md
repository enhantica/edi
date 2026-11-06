---
template: gui.html
---

# :fa5-archive: Projects and files

Use the application to open, save and export the complete analysis. The shared [Project](../user-guide/analysis-workflow/project.md) stage explains what belongs in a project; [data formats](../user-guide/data-formats.md) explains its folder and archive representations.

!!! note "Saving in the browser"

    Check the project location before closing the app. **In this browser only** means the project is in browser storage; use **Save project as…** to keep an external copy. [Browser-specific saving](browser.md#open-and-save-files) explains folders, archives and downloads.

## Open a project

Choose **Open project…**, then **Folder** or **Zip archive**. In the desktop app you can also drop a project folder, its `project.edi`, or a zip archive onto the window.

When a project opens, the app prepares its pages in turn. The status bar shows progress and a top-bar page becomes available when it is ready.

If your current project has unsaved changes when you open another, create one or quit, the application asks whether to save them.

<!-- gui-guide:open-a-project -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose a folder or a zip archive.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-project-open.png?v=3ffdc2d62c96" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Project source"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Project source"><title>Project source</title><defs><clipPath id="gui-clip-guide-project-open-overview-projects-open-a-project-0-project-openChoice"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-project-open.png?v=3ffdc2d62c96" width="1480" height="800" clip-path="url(#gui-clip-guide-project-open-overview-projects-open-a-project-0-project-openChoice)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-open-overview-projects-open-a-project-0-project-openChoice-1" data-gui-area="main" data-gui-parts="[[607,371,97.96562500000005,58]]" d="M605.000 369.000 L706.966 369.000 L706.966 431.000 L605.000 431.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Save or save a copy

**Save** writes to the project's current location when that is writable. **Save project as…** lets you choose a different location or format.

On the desktop, **Save project as…** offers **Folder**, **Zip archive**, and **Save a copy**. A copy records the current state without moving the project you continue to work on.

An archive opened on the desktop is unpacked into a working copy. Save writes the archive again. If it is not writable, or it is a bundled example, the application asks where to keep your work instead.

<!-- gui-guide:save-or-save-a-copy -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the output format and whether to save a copy.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-project-save.png?v=6668eba38bd5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save options"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save options"><title>Save options</title><defs><clipPath id="gui-clip-guide-project-save-overview-projects-save-or-save-a-copy-0-project-saveChoice"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-project-save.png?v=6668eba38bd5" width="1480" height="800" clip-path="url(#gui-clip-guide-project-save-overview-projects-save-or-save-a-copy-0-project-saveChoice)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-save-overview-projects-save-or-save-a-copy-0-project-saveChoice-1" data-gui-area="main" data-gui-parts="[[607,354,111.84375,93]]" d="M605.000 352.000 L720.844 352.000 L720.844 449.000 L605.000 449.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

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
<a class="gui-image-link" href="../assets/gui/y2o3/guide-project-open.png?v=3ffdc2d62c96" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Project source"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Project source"><title>Project source</title><defs><clipPath id="gui-clip-guide-project-open-overview-projects-browser-file-handling-0-project-openChoice"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-project-open.png?v=3ffdc2d62c96" width="1480" height="800" clip-path="url(#gui-clip-guide-project-open-overview-projects-browser-file-handling-0-project-openChoice)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-open-overview-projects-browser-file-handling-0-project-openChoice-1" data-gui-area="main" data-gui-parts="[[607,371,97.96562500000005,58]]" d="M605.000 369.000 L706.966 369.000 L706.966 431.000 L605.000 431.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Recent projects and recovery

The browser's **Recent projects** list includes projects it keeps. After a reload or closed tab it can offer **Continue where you left off**, including changes not explicitly saved before the interruption.

Recovery is useful, but it is not a substitute for keeping your own project copy.

<!-- gui-guide:recent-projects-and-recovery -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Find recent projects.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-project-recent.png?v=40b73ecd4e4d" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Recent projects"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Recent projects"><title>Recent projects</title><defs><clipPath id="gui-clip-guide-project-recent-overview-projects-recent-projects-and-recovery-0-group-recentProjects"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-project-recent.png?v=40b73ecd4e4d" width="1480" height="800" clip-path="url(#gui-clip-guide-project-recent-overview-projects-recent-projects-and-recovery-0-group-recentProjects)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-recent-overview-projects-recent-projects-and-recovery-0-group-recentProjects-1" data-gui-area="sidebar" data-gui-parts="[[770,203,710,258]]" d="M768.000 201.000 L1482.000 201.000 L1482.000 463.000 L768.000 463.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## What is saved

Saving writes the project state and measured data, including the selected analysis settings. Values are rounded according to the project's precision and uncertainty policy. The open project is updated to those saved values and its calculated pattern and agreement factors are recalculated from them.

A report is separate: saving a project does not create a fresh report. Use [Save report](reports.md) to update a document you intend to share.

<!-- gui-guide:what-is-saved -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61587;</span>Open project…"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Open or save the current project.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-project-actions.png?v=14ec62b49de2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Open project…"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Open project…"><title>Open project…</title><defs><clipPath id="gui-clip-guide-project-actions-overview-projects-what-is-saved-0-project-open"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-project-actions.png?v=14ec62b49de2" width="1480" height="800" clip-path="url(#gui-clip-guide-project-actions-overview-projects-what-is-saved-0-project-open)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-actions-overview-projects-what-is-saved-0-project-open-1" data-gui-area="sidebar" data-gui-parts="[[1132,168,334,39]]" d="M1130.000 166.000 L1468.000 166.000 L1468.000 209.000 L1130.000 209.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#62830;</span>Save project as…"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Open or save the current project.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-project-actions.png?v=14ec62b49de2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save project as…"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save project as…"><title>Save project as…</title><defs><clipPath id="gui-clip-guide-project-actions-overview-projects-what-is-saved-0-project-saveAs"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-project-actions.png?v=14ec62b49de2" width="1480" height="800" clip-path="url(#gui-clip-guide-project-actions-overview-projects-what-is-saved-0-project-saveAs)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-actions-overview-projects-what-is-saved-0-project-saveAs-1" data-gui-area="sidebar" data-gui-parts="[[784,221,334,39]]" d="M782.000 219.000 L1120.000 219.000 L1120.000 262.000 L782.000 262.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Move to another interface

Open the saved folder, `project.edi` or archive from [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../python/index.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:fa5-terminal:</span> <span class="ed-icon-text">the Command Line</span>](../cli/index.md){ .ed-interface-link .ed-icon-label }. The shared [project concepts](../user-guide/analysis-workflow/project.md) explain what those interfaces read.

<!-- gui-guide:move-to-another-interface -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the output format and whether to save a copy.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-project-save.png?v=6668eba38bd5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save options"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save options"><title>Save options</title><defs><clipPath id="gui-clip-guide-project-save-overview-projects-move-to-another-interface-0-project-saveChoice"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-project-save.png?v=6668eba38bd5" width="1480" height="800" clip-path="url(#gui-clip-guide-project-save-overview-projects-move-to-another-interface-0-project-saveChoice)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-save-overview-projects-move-to-another-interface-0-project-saveChoice-1" data-gui-area="main" data-gui-parts="[[607,354,111.84375,93]]" d="M605.000 352.000 L720.844 352.000 L720.844 449.000 L605.000 449.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
