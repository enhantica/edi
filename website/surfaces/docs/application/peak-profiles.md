---
category_glyph: "\uf61f"
template: gui.html
---

# <span class="ed-reference-icon" data-reference-category="peak" aria-hidden="true">&#63007;</span> Peak profiles

## Choose a profile

On **Experiment → Main**, expand **Peak profile**. Choose a profile appropriate to the experiment, then inspect or edit the displayed width, mixing and asymmetry parameters. The selector follows the experiment type.

The choices shown for this experiment link to their equations:

<!-- gui-options:guide-experiment-profile:peak.type:peak -->
- [Gaussian](../physics/profiles/cw/#eq-cwl-pseudovoigt)
- [Lorentzian](../physics/profiles/cw/#eq-cwl-pseudovoigt)
- [Pseudo-Voigt](../physics/profiles/cw/#eq-caglioti)
- [Pseudo-Voigt + Bérar-Baldinozzi asymmetry](../physics/profiles/cw/#eq-berar-baldinozzi)
- [Thompson-Cox-Hastings pseudo-Voigt (TCH)](../physics/profiles/cw/#eq-tch)
- [Thompson-Cox-Hastings pseudo-Voigt (TCH) + Finger-Cox-Jephcoat asymmetry (FCJ)](../physics/profiles/cw/#eq-fcj)
<!-- /gui-options -->

Compare peak widths and shapes across the pattern before choosing parameters to refine. See [peak profiles](../physics/profiles.md) for the full models.

<!-- gui-guide:choose-a-profile -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the peak shape and edit its profile parameters.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-experiment-profile.png?v=63f7e181d863" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Peak profile"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Peak profile"><title>Peak profile</title><defs><clipPath id="gui-clip-guide-experiment-profile-overview-peak-profiles-choose-a-profile-0-group-peak"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-experiment-profile.png?v=63f7e181d863" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-profile-overview-peak-profiles-choose-a-profile-0-group-peak)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-profile-overview-peak-profiles-choose-a-profile-0-group-peak-1" data-gui-area="sidebar" data-gui-parts="[[770,245,710,189]]" d="M768.000 243.000 L1482.000 243.000 L1482.000 436.000 L768.000 436.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Set the calculation window

On **Experiment → Extra**, expand **Peak cutoff**. Set how far each peak is calculated, in multiples of its full width at half maximum. Check the pattern after changing the window, especially for broad tails.

This controls the calculation window; refine profile parameters on [Analysis](refine.md#choose-free-parameters).

<!-- gui-guide:set-the-calculation-window -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Set the peak calculation window in multiples of the full width at half maximum.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-experiment-cutoff.png?v=2e6d848e5236" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Peak cutoff"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Peak cutoff"><title>Peak cutoff</title><defs><clipPath id="gui-clip-guide-experiment-cutoff-overview-peak-profiles-set-the-calculation-window-0-peak-cutoff_fwhm"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-experiment-cutoff.png?v=2e6d848e5236" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-cutoff-overview-peak-profiles-set-the-calculation-window-0-peak-cutoff_fwhm)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-cutoff-overview-peak-profiles-set-the-calculation-window-0-peak-cutoff_fwhm-1" data-gui-area="sidebar" data-gui-parts="[[784,210,339.25,56]]" d="M782.000 208.000 L1125.250 208.000 L1125.250 268.000 L782.000 268.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
