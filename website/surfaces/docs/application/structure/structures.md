---
category_glyph: "\uf5fd"
template: gui.html
---

# <span class="ed-reference-icon" aria-hidden="true">&#62973;</span> Structures

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a></p>
<!-- /group-tags -->

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
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-structure-create.png?v=db957c7f32f3" data-gui-dark="f9671a761a51" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load structure"><title>Load structure</title><defs><clipPath id="gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-load"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-structure-create.png?v=db957c7f32f3" data-gui-dark="f9671a761a51" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-load)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-load-1" data-gui-area="sidebar" data-gui-parts="[[784,260,218,39]]" d="M785.000 265.000 Q785.000 261.000 789.000 261.000 L997.000 261.000 Q1001.000 261.000 1001.000 265.000 L1001.000 294.000 Q1001.000 298.000 997.000 298.000 L789.000 298.000 Q785.000 298.000 785.000 294.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61525;</span>Create structure"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Add a starting structure to edit.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-structure-create.png?v=db957c7f32f3" data-gui-dark="f9671a761a51" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create structure"><title>Create structure</title><defs><clipPath id="gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-create"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-structure-create.png?v=db957c7f32f3" data-gui-dark="f9671a761a51" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-create)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-create-1" data-gui-area="sidebar" data-gui-parts="[[1016,260,218,39]]" d="M1017.000 265.000 Q1017.000 261.000 1021.000 261.000 L1229.000 261.000 Q1233.000 261.000 1233.000 265.000 L1233.000 294.000 Q1233.000 298.000 1229.000 298.000 L1021.000 298.000 Q1017.000 298.000 1017.000 294.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#62029;</span>Duplicate structure"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Copy the selected structure.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/guide-structure-create.png?v=db957c7f32f3" data-gui-dark="f9671a761a51" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Duplicate structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Duplicate structure"><title>Duplicate structure</title><defs><clipPath id="gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-duplicate"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-structure-create.png?v=db957c7f32f3" data-gui-dark="f9671a761a51" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-duplicate)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-create-overview-structures-load-create-or-duplicate-0-structures-duplicate-1" data-gui-area="sidebar" data-gui-parts="[[1248,260,218,39]]" d="M1249.000 265.000 Q1249.000 261.000 1253.000 261.000 L1461.000 261.000 Q1465.000 261.000 1465.000 265.000 L1465.000 294.000 Q1465.000 298.000 1461.000 298.000 L1253.000 298.000 Q1249.000 298.000 1249.000 294.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
