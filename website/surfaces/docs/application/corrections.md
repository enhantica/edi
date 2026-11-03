---
template: gui.html
---

# :material-microscope: Intensity corrections

## Set absorption

On **Experiment → Extra**, expand **Absorption**. Choose the model that matches the sample geometry and enter its physical parameters in the units shown. Leave **None** selected when no absorption correction is required.

<!-- gui-options:guide-experiment-absorption:absorption.type:absorption -->
- [None](../physics/corrections/absorption/#absorption-types)
- [Cylinder (Hewat)](../physics/corrections/absorption/#eq-hewat)
- [Cylinder (Lobanov)](../physics/corrections/absorption/#eq-lobanov)
<!-- /gui-options -->

See [absorption](../physics/corrections/absorption.md) for the models and their assumptions.

<!-- gui-guide:set-absorption -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the sample absorption model and its physical parameters.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-experiment-absorption.png?v=bdb7c9703bfa" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Absorption"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Absorption"><title>Absorption</title><defs><clipPath id="gui-clip-guide-experiment-absorption-overview-corrections-set-absorption-0-group-absorption"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-experiment-absorption.png?v=bdb7c9703bfa" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-absorption-overview-corrections-set-absorption-0-group-absorption)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-absorption-overview-corrections-set-absorption-0-group-absorption-1" data-gui-area="sidebar" data-gui-parts="[[770,203,710,119]]" d="M768.000 201.000 L1482.000 201.000 L1482.000 324.000 L768.000 324.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Set preferred orientation

Expand **Preferred orientations** on the same sidebar tab. Choose **Add preferred orientation**, identify the linked structure and preferred hkl direction, then set the March parameter and random fraction. Remove a row to remove that correction.

Use a correction supported by the sample preparation and diffraction evidence. See [preferred orientation](../physics/corrections/orientation.md) for the parameter meanings.

<!-- gui-guide:set-preferred-orientation -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Set preferred directions and March parameters for linked structures.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-experiment-orientation.png?v=cd5de98d4204" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Preferred orientations"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Preferred orientations"><title>Preferred orientations</title><defs><clipPath id="gui-clip-guide-experiment-orientation-overview-corrections-set-preferred-orientation-0-group-preferred_orientation"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-experiment-orientation.png?v=cd5de98d4204" width="1480" height="800" clip-path="url(#gui-clip-guide-experiment-orientation-overview-corrections-set-preferred-orientation-0-group-preferred_orientation)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-experiment-orientation-overview-corrections-set-preferred-orientation-0-group-preferred_orientation-1" data-gui-area="sidebar" data-gui-parts="[[770,245,710,194]]" d="M768.000 243.000 L1482.000 243.000 L1482.000 441.000 L768.000 441.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->
