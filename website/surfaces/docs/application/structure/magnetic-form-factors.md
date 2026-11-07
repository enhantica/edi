---
category_glyph: "\uf5d2"
template: gui.html
---

# <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> Magnetic form factors

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a></p>

Shown: magnetic structure.
<!-- /group-tags -->

## Use this group

On **Structure → Extra**, expand **Magnetic form factors**. The table has one row per magnetic atom type. The type and its ion are read-only; choose the ion in [Magnetic moments](magnetic-moments.md). The approximation picks which radial integrals the form factor sums. Edit and fit the coefficients it uses: C2 in the dipole approximation, and C2, C4 and C6 beyond it. A coefficient that the approximation does not use, or whose term the ion's table lacks, is greyed out.

<!-- gui-guide:use-this-group -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Set the magnetic form factors.</p>
<a class="gui-image-link" href="../../assets/gui/magnetic/group-form-factors.png?v=e189e0590197" data-gui-dark="e872c0d81111" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Magnetic form factors (1)"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Magnetic form factors (1)"><title>Magnetic form factors (1)</title><defs><clipPath id="gui-clip-group-form-factors-overview-magnetic-form-factors-use-this-group-0-group-magnetic_form_factor"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/magnetic/group-form-factors.png?v=e189e0590197" data-gui-dark="e872c0d81111" width="1480" height="800" clip-path="url(#gui-clip-group-form-factors-overview-magnetic-form-factors-use-this-group-0-group-magnetic_form_factor)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="group-form-factors-overview-magnetic-form-factors-use-this-group-0-group-magnetic_form_factor-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,141]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 297.000 Q1479.000 301.000 1475.000 301.000 L775.000 301.000 Q771.000 301.000 771.000 297.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
