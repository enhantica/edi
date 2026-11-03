---
category_glyph: "\uf1b2"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="cell" aria-hidden="true">&#61874;</span> Symmetry and cell

## Choose the space-group setting

Select a structure on **Structure → Main**, then expand **Space group**. Choose the space-group number, symbol and setting used by the structural model. These controls describe the same setting and update together.

Check the setting before entering atom coordinates. Symmetry determines which cell values and coordinates are independent. See [space groups and coordinates](../physics/crystallography.md).

<!-- gui-guide:choose-the-space-group-setting -->
<div class="gui-viewer" markdown="1">


=== "Space-group number"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select the symmetry of your model.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-structure-symmetry.png?v=4a2774a7ca45" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Space-group number"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Space-group number"><title>Space-group number</title><defs><clipPath id="gui-clip-guide-structure-symmetry-overview-symmetry-choose-the-space-group-setting-0-spaceGroup-itNumber"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-structure-symmetry.png?v=4a2774a7ca45" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-symmetry-overview-symmetry-choose-the-space-group-setting-0-spaceGroup-itNumber)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-symmetry-overview-symmetry-choose-the-space-group-setting-0-spaceGroup-itNumber-1" data-gui-area="sidebar" data-gui-parts="[[955.375,210,167.875,56]]" d="M953.375 208.000 L1125.250 208.000 L1125.250 268.000 L953.375 268.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

=== "Space-group symbol"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Check the Hermann-Mauguin symbol and setting.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-structure-symmetry.png?v=4a2774a7ca45" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Space-group symbol"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Space-group symbol"><title>Space-group symbol</title><defs><clipPath id="gui-clip-guide-structure-symmetry-overview-symmetry-choose-the-space-group-setting-0-spaceGroup-nameHM"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-structure-symmetry.png?v=4a2774a7ca45" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-symmetry-overview-symmetry-choose-the-space-group-setting-0-spaceGroup-nameHM)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-symmetry-overview-symmetry-choose-the-space-group-setting-0-spaceGroup-nameHM-1" data-gui-area="sidebar" data-gui-parts="[[1126.75,210,167.875,56]]" d="M1124.750 208.000 L1296.625 208.000 L1296.625 268.000 L1124.750 268.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Enter the unit cell

Expand **Cell** and edit the independent lengths and angles in the units shown. Values fixed or related by symmetry are controlled by the selected space group.

Inspect the structure view after editing. See [cell geometry](../physics/crystallography.md#eq-cell-metric) for the conventions.

<!-- gui-guide:enter-the-unit-cell -->
<div class="gui-viewer" markdown="1">


=== "Cell length a"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the cell length and its uncertainty.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-structure-cell.png?v=d1eaca5787d6" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Cell length a"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Cell length a"><title>Cell length a</title><defs><clipPath id="gui-clip-guide-structure-cell-overview-symmetry-enter-the-unit-cell-0-cell-length_a"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-structure-cell.png?v=d1eaca5787d6" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-cell-overview-symmetry-enter-the-unit-cell-0-cell-length_a)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-cell-overview-symmetry-enter-the-unit-cell-0-cell-length_a-1" data-gui-area="sidebar" data-gui-parts="[[784,252,110.75,56]]" d="M782.000 250.000 L896.750 250.000 L896.750 310.000 L782.000 310.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

=== "Cell length b"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Values controlled by symmetry are linked.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-structure-cell.png?v=d1eaca5787d6" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Cell length b"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Cell length b"><title>Cell length b</title><defs><clipPath id="gui-clip-guide-structure-cell-overview-symmetry-enter-the-unit-cell-0-cell-length_b"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-structure-cell.png?v=d1eaca5787d6" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-cell-overview-symmetry-enter-the-unit-cell-0-cell-length_b)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-cell-overview-symmetry-enter-the-unit-cell-0-cell-length_b-1" data-gui-area="sidebar" data-gui-parts="[[898.25,252,110.75,56]]" d="M896.250 250.000 L1011.000 250.000 L1011.000 310.000 L896.250 310.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

=== "Cell length c"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the cell convention of the selected space group.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/guide-structure-cell.png?v=d1eaca5787d6" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Cell length c"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Cell length c"><title>Cell length c</title><defs><clipPath id="gui-clip-guide-structure-cell-overview-symmetry-enter-the-unit-cell-0-cell-length_c"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-structure-cell.png?v=d1eaca5787d6" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-cell-overview-symmetry-enter-the-unit-cell-0-cell-length_c)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-cell-overview-symmetry-enter-the-unit-cell-0-cell-length_c-1" data-gui-area="sidebar" data-gui-parts="[[1012.5,252,110.75,56]]" d="M1010.500 250.000 L1125.250 250.000 L1125.250 310.000 L1010.500 310.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
