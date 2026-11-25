---
category_glyph: "\uf3fd"
template: gui.html
---

# <span class="ed-reference-icon" aria-hidden="true">&#62461;</span> Performance

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a></p>
<!-- /group-tags -->

## Use this group

On **Experiment → Settings**, expand **Performance**. It shows the number of threads a calculation runs on. This value is read-only here; change it in the application preferences.

<!-- gui-guide:use-this-group -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/11-experiment-settings.webp?v=af3ff8002ca9" data-gui-dark="6cb065a2e349" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-11-experiment-settings-overview-performance-use-this-group-0-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/11-experiment-settings.webp?v=af3ff8002ca9" data-gui-dark="6cb065a2e349" width="1480" height="800" clip-path="url(#gui-clip-11-experiment-settings-overview-performance-use-this-group-0-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="11-experiment-settings-overview-performance-use-this-group-0-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,799,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L794.000 78.000 Q798.000 78.000 798.000 82.000 L798.000 753.000 Q798.000 757.000 794.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/11-experiment-settings.webp?v=af3ff8002ca9" data-gui-dark="6cb065a2e349" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-11-experiment-settings-overview-performance-use-this-group-0-workflow-experiment-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/11-experiment-settings.webp?v=af3ff8002ca9" data-gui-dark="6cb065a2e349" width="1480" height="800" clip-path="url(#gui-clip-11-experiment-settings-overview-performance-use-this-group-0-workflow-experiment-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="11-experiment-settings-overview-performance-use-this-group-0-workflow-experiment-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[799,119,681,639],[926.21875,77,62.96875,42]]" d="M800.000 124.000 Q800.000 120.000 804.000 120.000 L923.219 120.000 Q927.219 120.000 927.219 116.000 L927.219 82.000 Q927.219 78.000 931.219 78.000 L984.188 78.000 Q988.188 78.000 988.188 82.000 L988.188 116.000 Q988.188 120.000 992.188 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 753.000 Q1479.000 757.000 1475.000 757.000 L804.000 757.000 Q800.000 757.000 800.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../../assets/gui/y2o3/11-experiment-settings.webp?v=af3ff8002ca9" data-gui-dark="6cb065a2e349" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-11-experiment-settings-overview-performance-use-this-group-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/y2o3/11-experiment-settings.webp?v=af3ff8002ca9" data-gui-dark="6cb065a2e349" width="1480" height="800" clip-path="url(#gui-clip-11-experiment-settings-overview-performance-use-this-group-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="11-experiment-settings-overview-performance-use-this-group-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M1.000 763.000 Q1.000 759.000 5.000 759.000 L1475.000 759.000 Q1479.000 759.000 1479.000 763.000 L1479.000 795.000 Q1479.000 799.000 1475.000 799.000 L5.000 799.000 Q1.000 799.000 1.000 795.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->
