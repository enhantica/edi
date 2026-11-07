---
category_glyph: "\uf61f"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="peak" aria-hidden="true">&#63007;</span> Peak profile

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a></p>
<!-- /group-tags -->

## Choose a profile

On **Experiment → Main**, expand **Peak profile**. Choose a profile appropriate to the experiment, then inspect or edit the displayed width, mixing and asymmetry parameters. The selector follows the experiment type.

The choices shown for this experiment link to their equations:

<!-- gui-options:guide-experiment-profile:peak.type:peak -->
- [Gaussian](../../physics/profiles/cw/#eq-cwl-pseudovoigt)
- [Lorentzian](../../physics/profiles/cw/#eq-cwl-pseudovoigt)
- [Pseudo-Voigt](../../physics/profiles/cw/#eq-caglioti)
- [Pseudo-Voigt + Bérar-Baldinozzi asymmetry](../../physics/profiles/cw/#eq-berar-baldinozzi)
- [Thompson-Cox-Hastings pseudo-Voigt (TCH)](../../physics/profiles/cw/#eq-tch)
- [Thompson-Cox-Hastings pseudo-Voigt (TCH) + Finger-Cox-Jephcoat asymmetry (FCJ)](../../physics/profiles/cw/#eq-fcj)
<!-- /gui-options -->

Compare peak widths and shapes across the pattern before choosing parameters to refine. See [peak profiles](../../physics/profiles/index.md) for the full models.

<!-- gui-guide:choose-a-profile -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the peak shape and edit its profile parameters.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-profile.png?v=023685c6be5d" data-gui-dark="b4cd9d28fc9e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Peak profile"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Peak profile"><title>Peak profile</title><defs><clipPath id="gui-clip-guide-experiment-profile-overview-peak-profile-choose-a-profile-0-group-peak"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-profile.png?v=023685c6be5d" data-gui-dark="b4cd9d28fc9e" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-profile-overview-peak-profile-choose-a-profile-0-group-peak)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-profile-overview-peak-profile-choose-a-profile-0-group-peak-1" data-gui-area="sidebar" data-gui-parts="[[770,245.00000000000472,710,189]]" d="M771.000 250.000 Q771.000 246.000 775.000 246.000 L1475.000 246.000 Q1479.000 246.000 1479.000 250.000 L1479.000 429.000 Q1479.000 433.000 1475.000 433.000 L775.000 433.000 Q771.000 433.000 771.000 429.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Set the calculation window

On **Experiment → Extra**, expand **Peak cutoff**. Set how far each peak is calculated, in multiples of its full width at half maximum. Check the pattern after changing the window, especially for broad tails.

This controls the calculation window; refine profile parameters on [Analysis](../analysis/index.md#choose-free-parameters).

<!-- gui-guide:set-the-calculation-window -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Set the peak calculation window in multiples of the full width at half maximum.</p>
<a class="gui-image-link" href="../../assets/gui/y2o3/guide-experiment-cutoff.png?v=802568146f86" data-gui-dark="0b0102a9f7a3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Peak cutoff"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Peak cutoff"><title>Peak cutoff</title><defs><clipPath id="gui-clip-guide-experiment-cutoff-overview-peak-profile-set-the-calculation-window-0-peak-cutoff_fwhm"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/guide-experiment-cutoff.png?v=802568146f86" data-gui-dark="0b0102a9f7a3" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-cutoff-overview-peak-profile-set-the-calculation-window-0-peak-cutoff_fwhm)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-cutoff-overview-peak-profile-set-the-calculation-window-0-peak-cutoff_fwhm-1" data-gui-area="sidebar" data-gui-parts="[[784,210,339.25,56]]" d="M785.000 215.000 Q785.000 211.000 789.000 211.000 L1118.250 211.000 Q1122.250 211.000 1122.250 215.000 L1122.250 261.000 Q1122.250 265.000 1118.250 265.000 L789.000 265.000 Q785.000 265.000 785.000 261.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
