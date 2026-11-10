---
category_glyph: "\uf1b2"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="cell" aria-hidden="true">&#61874;</span> Cell

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a></p>
<!-- /group-tags -->

## Enter the unit cell

On **Structure → Main**, expand **Cell** and edit the independent lengths and angles in the units shown. Values fixed or related by symmetry are controlled by the selected space group.

Inspect the structure view after editing. See [cell geometry](../../physics/crystallography.md#eq-cell-metric) for the conventions.

<!-- gui-guide:enter-the-unit-cell -->
<div class="gui-viewer" markdown="1">


=== "Cell length a"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the cell length and its uncertainty.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-structure-cell.png?v=12657c7059c5" data-gui-dark="10d12bc22697" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Cell length a"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Cell length a"><title>Cell length a</title><defs><clipPath id="gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_a"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-structure-cell.png?v=12657c7059c5" data-gui-dark="10d12bc22697" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_a)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_a-1" data-gui-area="sidebar" data-gui-parts="[[784,252.00000000000244,110.75,56]]" d="M785.000 257.000 Q785.000 253.000 789.000 253.000 L889.750 253.000 Q893.750 253.000 893.750 257.000 L893.750 303.000 Q893.750 307.000 889.750 307.000 L789.000 307.000 Q785.000 307.000 785.000 303.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Cell length b"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Values controlled by symmetry are linked.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-structure-cell.png?v=12657c7059c5" data-gui-dark="10d12bc22697" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Cell length b"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Cell length b"><title>Cell length b</title><defs><clipPath id="gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_b"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-structure-cell.png?v=12657c7059c5" data-gui-dark="10d12bc22697" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_b)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_b-1" data-gui-area="sidebar" data-gui-parts="[[898.25,252.00000000000244,110.75,56]]" d="M899.250 257.000 Q899.250 253.000 903.250 253.000 L1004.000 253.000 Q1008.000 253.000 1008.000 257.000 L1008.000 303.000 Q1008.000 307.000 1004.000 307.000 L903.250 307.000 Q899.250 307.000 899.250 303.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Cell length c"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the cell convention of the selected space group.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-structure-cell.png?v=12657c7059c5" data-gui-dark="10d12bc22697" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Cell length c"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Cell length c"><title>Cell length c</title><defs><clipPath id="gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_c"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-structure-cell.png?v=12657c7059c5" data-gui-dark="10d12bc22697" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_c)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_c-1" data-gui-area="sidebar" data-gui-parts="[[1012.5,252.00000000000244,110.75,56]]" d="M1013.500 257.000 Q1013.500 253.000 1017.500 253.000 L1118.250 253.000 Q1122.250 253.000 1122.250 257.000 L1122.250 303.000 Q1122.250 307.000 1118.250 307.000 L1017.500 307.000 Q1013.500 307.000 1013.500 303.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
