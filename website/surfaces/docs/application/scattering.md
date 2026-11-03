---
template: gui.html
---

# :material-puzzle: Neutron scattering lengths

## Override a structure's scattering lengths

On **Structure → Extra**, expand **Scattering lengths**. An empty list uses the built-in table. To override it, choose **Append a scattering length**, enter the atom type and its coherent scattering length in femtometres. Remove a row to use the built-in value again.

Use an override when the atom type needs a value specific to your sample. See [neutron scattering and structure factors](../physics/diffraction.md).

<!-- gui-guide:override-a-structure-s-scattering-lengths -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Set custom neutron scattering lengths for atom types in this structure.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-structure-scattering.png?v=829fae8d8e9e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Scattering lengths"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Scattering lengths"><title>Scattering lengths</title><defs><clipPath id="gui-clip-guide-structure-scattering-overview-scattering-override-a-structure-s-scattering-lengths-0-group-scattering_length"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-structure-scattering.png?v=829fae8d8e9e" width="1480" height="800" clip-path="url(#gui-clip-guide-structure-scattering-overview-scattering-override-a-structure-s-scattering-lengths-0-group-scattering_length)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-structure-scattering-overview-scattering-override-a-structure-s-scattering-lengths-0-group-scattering_length-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,194]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 315.000 L768.000 315.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Choose the experiment's reference table

On **Experiment → Extra**, expand **Scattering source** and choose the neutron scattering-length reference. Structure overrides take precedence for the types you explicitly entered.

<!-- gui-options:guide-experiment-scattering:scatteringSource.neutron_scattering_length: -->
- Rauch &amp; Waschkowski (2003)
- Sears (1992)
<!-- /gui-options -->

<!-- gui-guide:choose-the-experiment-s-reference-table -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the neutron scattering-length reference used by the experiment.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-experiment-scattering.png?v=643c8595cabf" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Scattering source"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Scattering source"><title>Scattering source</title><defs><clipPath id="gui-clip-guide-experiment-scattering-overview-scattering-choose-the-experiment-s-reference-table-0-group-scattering_source"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-experiment-scattering.png?v=643c8595cabf" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-scattering-overview-scattering-choose-the-experiment-s-reference-table-0-group-scattering_source)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-scattering-overview-scattering-choose-the-experiment-s-reference-table-0-group-scattering_source-1" data-gui-area="sidebar" data-gui-parts="[[770,287,710,119]]" d="M768.000 285.000 L1482.000 285.000 L1482.000 408.000 L768.000 408.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
