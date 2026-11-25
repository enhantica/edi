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
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-structure-cell.webp?v=1200bd6049f0" data-gui-dark="8a4a65e7d316" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Cell length a"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Cell length a"><title>Cell length a</title><defs><clipPath id="gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_a"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-structure-cell.webp?v=1200bd6049f0" data-gui-dark="8a4a65e7d316" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_a)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_a-1" data-gui-area="sidebar" data-gui-parts="[[813,252,105.91666666666663,56]]" d="M814.000 257.000 Q814.000 253.000 818.000 253.000 L913.917 253.000 Q917.917 253.000 917.917 257.000 L917.917 303.000 Q917.917 307.000 913.917 307.000 L818.000 307.000 Q814.000 307.000 814.000 303.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Cell length b"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Values controlled by symmetry are linked.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-structure-cell.webp?v=1200bd6049f0" data-gui-dark="8a4a65e7d316" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Cell length b"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Cell length b"><title>Cell length b</title><defs><clipPath id="gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_b"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-structure-cell.webp?v=1200bd6049f0" data-gui-dark="8a4a65e7d316" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_b)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_b-1" data-gui-area="sidebar" data-gui-parts="[[922.4166666666666,252,105.91666666666663,56]]" d="M923.417 257.000 Q923.417 253.000 927.417 253.000 L1023.333 253.000 Q1027.333 253.000 1027.333 257.000 L1027.333 303.000 Q1027.333 307.000 1023.333 307.000 L927.417 307.000 Q923.417 307.000 923.417 303.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Cell length c"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the cell convention of the selected space group.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-structure-cell.webp?v=1200bd6049f0" data-gui-dark="8a4a65e7d316" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Cell length c"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Cell length c"><title>Cell length c</title><defs><clipPath id="gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_c"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-structure-cell.webp?v=1200bd6049f0" data-gui-dark="8a4a65e7d316" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_c)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-cell-overview-cell-enter-the-unit-cell-0-cell-length_c-1" data-gui-area="sidebar" data-gui-parts="[[1031.8333333333333,252,105.91666666666674,56]]" d="M1032.833 257.000 Q1032.833 253.000 1036.833 253.000 L1132.750 253.000 Q1136.750 253.000 1136.750 257.000 L1136.750 303.000 Q1136.750 307.000 1132.750 307.000 L1036.833 307.000 Q1032.833 307.000 1032.833 303.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
