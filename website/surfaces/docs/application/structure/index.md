---
template: gui.html
---

# :fa5-layer-group: Structure

The **Structure** page holds the crystal models of your project: the viewer on the left, and on the right the groups that define the current structure.

<!-- sidebar-groups -->
| Sidebar group | Tab | Shown |
| --- | --- | --- |
| <span class="ed-reference-icon" aria-hidden="true">&#62973;</span> [Structures](structures.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#63423;</span> [Space group](space-group.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#61874;</span> [Cell](cell.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> [Atom sites](atom-sites.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> [Atomic displacement](atomic-displacement.md) | Main | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#62789;</span> [Scattering lengths](scattering-lengths.md) | Extra | Always |
| <span class="ed-reference-icon" aria-hidden="true">&#62783;</span> [Appearance](appearance.md) | Extra | Always |
<!-- /sidebar-groups -->

## Structure viewer controls

Drag to rotate, use the wheel to zoom, and drag with the right mouse button to pan.

| Control | What it changes |
| --- | --- |
| <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> Atoms | Show all symmetry copies, the asymmetric unit only, or no atoms |
| <span class="ed-reference-icon" aria-hidden="true">&#61483;</span> Labels | Show or hide atom names |
| <span class="ed-reference-icon" aria-hidden="true">&#61633;</span> Bonds | Show or hide bonds when the structure has them |
| <span class="ed-reference-icon" aria-hidden="true">&#62923;</span> Cell | Show or hide the unit-cell outline |
| <span class="ed-reference-icon" aria-hidden="true">&#61732;</span> Axes | Show or hide crystallographic directions |
| <span class="ed-reference-icon" aria-hidden="true">&#61874;</span> Camera | Switch parallel/perspective projection, look along **a**, **b** or **c**, or reset the view |
| Colour scheme | Choose the element colours used by the view and its legend |

These controls change the picture; they do not change the crystallographic model.

<span id="magnetic-moments"></span>

!!! info "Planned: magnetic moments"

    Magnetic-moment arrows in the structure viewer are planned. They are not available in the current viewer.

<!-- gui-guide:structure-viewer-controls -->
<div class="gui-viewer" markdown="1">


=== "Structures"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select the structure whose cell and atom sites you want to inspect.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/07-structure-loaded.png?v=e86feaa85788" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Structures"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Structures"><title>Structures</title><defs><clipPath id="gui-clip-07-structure-loaded-overview-index-structure-viewer-controls-0-structures-list"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/07-structure-loaded.png?v=e86feaa85788" width="1480" height="800" clip-path="url(#gui-clip-07-structure-loaded-overview-index-structure-viewer-controls-0-structures-list)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="07-structure-loaded-overview-index-structure-viewer-controls-0-structures-list-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M782.000 166.000 L1468.000 166.000 L1468.000 248.000 L782.000 248.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the structure view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/07-structure-loaded.png?v=e86feaa85788" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-07-structure-loaded-overview-index-structure-viewer-controls-0-workflow-structure-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/07-structure-loaded.png?v=e86feaa85788" width="1480" height="800" clip-path="url(#gui-clip-07-structure-loaded-overview-index-structure-viewer-controls-0-workflow-structure-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="07-structure-loaded-overview-index-structure-viewer-controls-0-workflow-structure-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
