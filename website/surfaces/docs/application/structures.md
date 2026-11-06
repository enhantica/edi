---
template: gui.html
---

# :fa5-layer-group: Load and display structures

## Load, create or duplicate

On **Structure → Main**, expand **Structures** and select a row to make it current.

- **Load ▾ → From file…** imports a CIF or `.edi` structure file.
- **Create structure** adds a starting model. Replace its initial symmetry, cell and atom sites with those of your sample.
- **Duplicate structure** copies the selected model. Link the copy to an experiment when you want it to contribute.

Edit the name in the list or use the row's remove control. Removing a structure also removes its experiment links; **Undo** restores the change.

<!-- gui-guide:load-create-or-duplicate -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61587;</span>Load structure"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Import the structure file for this example.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-structure-create.png?v=2ea790acda14" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load structure"><title>Load structure</title><defs><clipPath id="gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-load"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-structure-create.png?v=2ea790acda14" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-load)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-load-1" data-gui-area="sidebar" data-gui-parts="[[784,260,334,39]]" d="M782.000 258.000 L1120.000 258.000 L1120.000 301.000 L782.000 301.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61525;</span>Create structure"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Add a starting structure to edit.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-structure-create.png?v=2ea790acda14" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create structure"><title>Create structure</title><defs><clipPath id="gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-create"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-structure-create.png?v=2ea790acda14" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-create)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-create-1" data-gui-area="sidebar" data-gui-parts="[[1132,260,334,39]]" d="M1130.000 258.000 L1468.000 258.000 L1468.000 301.000 L1130.000 301.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#62029;</span>Duplicate structure"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Copy the selected structure.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-structure-create.png?v=2ea790acda14" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Duplicate structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Duplicate structure"><title>Duplicate structure</title><defs><clipPath id="gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-duplicate"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-structure-create.png?v=2ea790acda14" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-duplicate)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-duplicate-1" data-gui-area="sidebar" data-gui-parts="[[784,313,334,39]]" d="M782.000 311.000 L1120.000 311.000 L1120.000 354.000 L782.000 354.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Change the structure display

### Structure viewer controls {#structure-viewer-controls}

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

### Appearance

On **Structure → Extra**, expand **Appearance**. Choose how atom sizes are drawn, adjust the display scale or use displacement ellipsoids. For ellipsoids, set the probability level.

These controls change the picture. Edit the scientific model in [Symmetry and cell](symmetry.md), [Atom sites](atoms.md) and [Atomic displacement](displacement.md). [Scattering lengths](scattering.md) and [experiment links](linked-structures.md) have their own controls.

<!-- gui-guide:change-the-structure-display -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose atom sizes, display scale and displacement ellipsoids.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-structure-appearance.png?v=851520244ea3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Appearance"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Appearance"><title>Appearance</title><defs><clipPath id="gui-clip-guide-structure-appearance-overview-structures-change-the-structure-display-0-group-appearance"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-structure-appearance.png?v=851520244ea3" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-appearance-overview-structures-change-the-structure-display-0-group-appearance)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-appearance-overview-structures-change-the-structure-display-0-group-appearance-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M768.000 159.000 L1482.000 159.000 L1482.000 282.000 L768.000 282.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
