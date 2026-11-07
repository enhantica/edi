---
category_glyph: "\uf545"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="scattering-length" aria-hidden="true">&#62789;</span> Scattering lengths

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a></p>
<!-- /group-tags -->

## Override a structure's scattering lengths

On **Structure → Extra**, expand **Scattering lengths**. An empty list uses the built-in table. To override it, choose **Append a scattering length**, enter the atom type and its coherent scattering length in femtometres. Remove a row to use the built-in value again.

Use an override when the atom type needs a value specific to your sample. See [neutron scattering and structure factors](../../physics/diffraction.md).

<!-- gui-guide:override-a-structure-s-scattering-lengths -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Set custom neutron scattering lengths for atom types in this structure.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-structure-scattering.png?v=6527c7950392" data-gui-dark="6aae494e57f5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Scattering lengths"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Scattering lengths"><title>Scattering lengths</title><defs><clipPath id="gui-clip-guide-structure-scattering-overview-scattering-lengths-override-a-structure-s-scattering-lengths-0-group-scattering_length"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-structure-scattering.png?v=6527c7950392" data-gui-dark="6aae494e57f5" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-scattering-overview-scattering-lengths-override-a-structure-s-scattering-lengths-0-group-scattering_length)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-scattering-overview-scattering-lengths-override-a-structure-s-scattering-lengths-0-group-scattering_length-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,194]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 308.000 Q1479.000 312.000 1475.000 312.000 L775.000 312.000 Q771.000 312.000 771.000 308.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
