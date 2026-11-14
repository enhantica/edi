---
template: gui.html
---

# La₀.₅Ba₀.₅CoO₃ on HRPT

The same staged fit as the Python and Command line tutorials, in the app. Its structure and experiment come from EasyDiffraction's collection with **Load ▾ From web…**, and each stage frees its parameters in the **Parameters** table on **Analysis** before the fit.

This tutorial fits the cubic perovskite La₀.₅Ba₀.₅CoO₃ to constant-wavelength neutron powder data
measured on HRPT at PSI. It builds the structure by hand, loads the measured pattern from
EasyDiffraction's collection, describes the experiment, links the two and fits them, showing the
pattern and the parameters after each step. The other tutorials load their structures from a CIF.

## Create a project

Press **Start** on Home, then **Create a new project**, and give it a name.

<div class="gui-viewer" markdown="1">


=== "Start"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/home.webp?v=15b79eec4750" data-gui-dark="1bf82db6b035" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Start a new analysis"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Start a new analysis"><title>Start a new analysis</title><defs><clipPath id="gui-clip-home-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/home.webp?v=15b79eec4750" data-gui-dark="1bf82db6b035" width="1480" height="800" clip-path="url(#gui-clip-home-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="home-overview-1" data-gui-area="main" data-gui-parts="[[573,404,334,39]]" d="M574.000 409.000 Q574.000 405.000 578.000 405.000 L902.000 405.000 Q906.000 405.000 906.000 409.000 L906.000 438.000 Q906.000 442.000 902.000 442.000 L578.000 442.000 Q574.000 442.000 574.000 438.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[542,0,53.46875,77]]" d="M543.000 5.000 Q543.000 1.000 547.000 1.000 L590.469 1.000 Q594.469 1.000 594.469 5.000 L594.469 72.000 Q594.469 76.000 590.469 76.000 L547.000 76.000 Q543.000 76.000 543.000 72.000 Z" /></svg></a>

    </figure>

=== "Details"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/project-details.webp?v=32de253a0987" data-gui-dark="85394efe0dff" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Enter the project details"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Enter the project details"><title>Enter the project details</title><defs><clipPath id="gui-clip-project-details-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/project-details.webp?v=32de253a0987" data-gui-dark="85394efe0dff" width="1480" height="800" clip-path="url(#gui-clip-project-details-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="project-details-overview-1" data-gui-area="main" data-gui-parts="[[495,238,490,35]]" d="M496.000 243.000 Q496.000 239.000 500.000 239.000 L980.000 239.000 Q984.000 239.000 984.000 243.000 L984.000 268.000 Q984.000 272.000 980.000 272.000 L500.000 272.000 Q496.000 272.000 496.000 268.000 Z" /><path class="" data-gui-region="project-details-overview-2" data-gui-area="main" data-gui-parts="[[495,306,490,36]]" d="M496.000 311.000 Q496.000 307.000 500.000 307.000 L980.000 307.000 Q984.000 307.000 984.000 311.000 L984.000 337.000 Q984.000 341.000 980.000 341.000 L500.000 341.000 Q496.000 341.000 496.000 337.000 Z" /><path class="" data-gui-region="project-details-overview-3" data-gui-area="main" data-gui-parts="[[495,547,490,35]]" d="M496.000 552.000 Q496.000 548.000 500.000 548.000 L980.000 548.000 Q984.000 548.000 984.000 552.000 L984.000 577.000 Q984.000 581.000 980.000 581.000 L500.000 581.000 Q496.000 581.000 496.000 577.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "Created"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/project-created.webp?v=687c97af63e8" data-gui-dark="d62fb1bdf165" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create the project"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create the project"><title>Create the project</title><defs><clipPath id="gui-clip-project-created-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/project-created.webp?v=687c97af63e8" data-gui-dark="d62fb1bdf165" width="1480" height="800" clip-path="url(#gui-clip-project-created-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="project-created-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

</div>

## Build the structure

On **Structure**, choose **Create structure** and name it, then set its space group and cell, add the atom sites and give each its displacement.

<div class="gui-viewer" markdown="1">


=== "Structure"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-created.webp?v=cdec3e21d743" data-gui-dark="878a1a760a21" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create the structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create the structure"><title>Create the structure</title><defs><clipPath id="gui-clip-structure-created-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-created.webp?v=cdec3e21d743" data-gui-dark="878a1a760a21" width="1480" height="800" clip-path="url(#gui-clip-structure-created-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-created-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 241.000 Q1465.000 245.000 1461.000 245.000 L789.000 245.000 Q785.000 245.000 785.000 241.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Space group and cell"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-cell.webp?v=01a21056a30e" data-gui-dark="1fc386b1a12f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Space group and cell"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Space group and cell"><title>Space group and cell</title><defs><clipPath id="gui-clip-structure-cell-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-cell.webp?v=01a21056a30e" data-gui-dark="1fc386b1a12f" width="1480" height="800" clip-path="url(#gui-clip-structure-cell-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-cell-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,42]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 198.000 Q1479.000 202.000 1475.000 202.000 L775.000 202.000 Q771.000 202.000 771.000 198.000 Z" /><path class="" data-gui-region="structure-cell-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,203,710,119]]" d="M771.000 208.000 Q771.000 204.000 775.000 204.000 L1475.000 204.000 Q1479.000 204.000 1479.000 208.000 L1479.000 317.000 Q1479.000 321.000 1475.000 321.000 L775.000 321.000 Q771.000 321.000 771.000 317.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Atom sites"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-sites.webp?v=a5bb97fa6e61" data-gui-dark="a653a2166c0f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Add the atom sites"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Add the atom sites"><title>Add the atom sites</title><defs><clipPath id="gui-clip-structure-sites-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-sites.webp?v=a5bb97fa6e61" data-gui-dark="a653a2166c0f" width="1480" height="800" clip-path="url(#gui-clip-structure-sites-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-sites-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,294,682,195]]" d="M785.000 299.000 Q785.000 295.000 789.000 295.000 L1461.000 295.000 Q1465.000 295.000 1465.000 299.000 L1465.000 484.000 Q1465.000 488.000 1461.000 488.000 L789.000 488.000 Q785.000 488.000 785.000 484.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Displacements"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-adp.webp?v=128ea176a065" data-gui-dark="8c525ff0a5fd" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Set the displacements"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Set the displacements"><title>Set the displacements</title><defs><clipPath id="gui-clip-structure-adp-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-adp.webp?v=128ea176a065" data-gui-dark="8c525ff0a5fd" width="1480" height="800" clip-path="url(#gui-clip-structure-adp-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-adp-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,336,682,195]]" d="M785.000 341.000 Q785.000 337.000 789.000 337.000 L1461.000 337.000 Q1465.000 337.000 1465.000 341.000 L1465.000 526.000 Q1465.000 530.000 1461.000 530.000 L789.000 530.000 Q785.000 530.000 785.000 526.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

</div>

## Create the experiment

On **Experiment**, choose **Create experiment** and its type, load the measured data with **Load ▾ Measured data From web…** from EasyDiffraction's collection, then set the instrument, the peak widths, the background points and the excluded regions, and link the structure.

<div class="gui-viewer" markdown="1">


=== "Experiment"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-created.webp?v=e109a8703c1a" data-gui-dark="ebb35237d017" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create the experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create the experiment"><title>Create the experiment</title><defs><clipPath id="gui-clip-experiment-created-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-created.webp?v=e109a8703c1a" data-gui-dark="ebb35237d017" width="1480" height="800" clip-path="url(#gui-clip-experiment-created-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-created-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,260,682,126]]" d="M785.000 265.000 Q785.000 261.000 789.000 261.000 L1461.000 261.000 Q1465.000 261.000 1465.000 265.000 L1465.000 381.000 Q1465.000 385.000 1461.000 385.000 L789.000 385.000 Q785.000 385.000 785.000 381.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Search"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/data-web.webp?v=749deac8b1e9" data-gui-dark="befa91ff1f0d" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Find the measured data"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Find the measured data"><title>Find the measured data</title><defs><clipPath id="gui-clip-data-web-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/data-web.webp?v=749deac8b1e9" data-gui-dark="befa91ff1f0d" width="1480" height="800" clip-path="url(#gui-clip-data-web-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="data-web-overview-1" data-gui-area="main" data-gui-parts="[[532,252,416,35]]" d="M533.000 257.000 Q533.000 253.000 537.000 253.000 L943.000 253.000 Q947.000 253.000 947.000 257.000 L947.000 282.000 Q947.000 286.000 943.000 286.000 L537.000 286.000 Q533.000 286.000 533.000 282.000 Z" /><path class="" data-gui-region="data-web-overview-2" data-gui-area="main" data-gui-parts="[[102,485,1276,78]]" d="M103.000 490.000 Q103.000 486.000 107.000 486.000 L1373.000 486.000 Q1377.000 486.000 1377.000 490.000 L1377.000 558.000 Q1377.000 562.000 1373.000 562.000 L107.000 562.000 Q103.000 562.000 103.000 558.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Measured data"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/data-loaded.webp?v=96914d2e9633" data-gui-dark="da2d2121a6ba" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load the measured data"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load the measured data"><title>Load the measured data</title><defs><clipPath id="gui-clip-data-loaded-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/data-loaded.webp?v=96914d2e9633" data-gui-dark="da2d2121a6ba" width="1480" height="800" clip-path="url(#gui-clip-data-loaded-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="data-loaded-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Instrument and profile"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-instrument.webp?v=6c7f79b5ad2b" data-gui-dark="d7246a1f8b16" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Instrument and peak widths"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Instrument and peak widths"><title>Instrument and peak widths</title><defs><clipPath id="gui-clip-experiment-instrument-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-instrument.webp?v=6c7f79b5ad2b" data-gui-dark="d7246a1f8b16" width="1480" height="800" clip-path="url(#gui-clip-experiment-instrument-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-instrument-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,203,710,42]]" d="M771.000 208.000 Q771.000 204.000 775.000 204.000 L1475.000 204.000 Q1479.000 204.000 1479.000 208.000 L1479.000 240.000 Q1479.000 244.000 1475.000 244.000 L775.000 244.000 Q771.000 244.000 771.000 240.000 Z" /><path class="" data-gui-region="experiment-instrument-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,245,710,189]]" d="M771.000 250.000 Q771.000 246.000 775.000 246.000 L1475.000 246.000 Q1479.000 246.000 1479.000 250.000 L1479.000 429.000 Q1479.000 433.000 1475.000 433.000 L775.000 433.000 Q771.000 433.000 771.000 429.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Background"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-background.webp?v=202bfd02d6d7" data-gui-dark="c8f9b78152a2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background and excluded regions"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background and excluded regions"><title>Background and excluded regions</title><defs><clipPath id="gui-clip-experiment-background-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-background.webp?v=202bfd02d6d7" data-gui-dark="c8f9b78152a2" width="1480" height="800" clip-path="url(#gui-clip-experiment-background-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-background-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,336,682,117]]" d="M785.000 341.000 Q785.000 337.000 789.000 337.000 L1461.000 337.000 Q1465.000 337.000 1465.000 341.000 L1465.000 448.000 Q1465.000 452.000 1461.000 452.000 L789.000 452.000 Q785.000 452.000 785.000 448.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Linked structure"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-linked.webp?v=89e38f295d7d" data-gui-dark="13b4905c220e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Link the structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Link the structure"><title>Link the structure</title><defs><clipPath id="gui-clip-experiment-linked-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-linked.webp?v=89e38f295d7d" data-gui-dark="13b4905c220e" width="1480" height="800" clip-path="url(#gui-clip-experiment-linked-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-linked-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,378,682,78]]" d="M785.000 383.000 Q785.000 379.000 789.000 379.000 L1461.000 379.000 Q1465.000 379.000 1465.000 383.000 L1465.000 451.000 Q1465.000 455.000 1461.000 455.000 L789.000 455.000 Q785.000 455.000 785.000 451.000 Z" /><path class="" data-gui-region="experiment-linked-overview-2" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>

## Start with nothing free

Entries loaded from the database can come with parameters already free. On **Analysis**, open the **Free** column header of the **Parameters** table and fix every parameter, so the stages below free one group at a time.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/nothing-free.webp?v=4b5bb0733fdb" data-gui-dark="07e1472ee12e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Start with every parameter fixed"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Start with every parameter fixed"><title>Start with every parameter fixed</title><defs><clipPath id="gui-clip-nothing-free-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/nothing-free.webp?v=4b5bb0733fdb" data-gui-dark="07e1472ee12e" width="1480" height="800" clip-path="url(#gui-clip-nothing-free-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="nothing-free-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path class="" data-gui-region="nothing-free-overview-2" data-gui-area="sidebar" data-gui-parts="[[1383,231,78,39]]" d="M1384.000 236.000 Q1384.000 232.000 1388.000 232.000 L1456.000 232.000 Q1460.000 232.000 1460.000 236.000 L1460.000 265.000 Q1460.000 269.000 1456.000 269.000 L1388.000 269.000 Q1384.000 269.000 1384.000 265.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Set the minimizer

On **Analysis → Extra**, set the **Minimizer** as the case's project does: the **Shift/s.u.** stop rule and room for more iterations.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/minimizer.webp?v=62c8f1163f69" data-gui-dark="47c1371e9ae1" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Set the minimizer as the project does"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Set the minimizer as the project does"><title>Set the minimizer as the project does</title><defs><clipPath id="gui-clip-minimizer-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/minimizer.webp?v=62c8f1163f69" data-gui-dark="47c1371e9ae1" width="1480" height="800" clip-path="url(#gui-clip-minimizer-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="minimizer-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,259]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 373.000 Q1479.000 377.000 1475.000 377.000 L775.000 377.000 Q771.000 377.000 771.000 373.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Scale, 2θ zero and cell

The scale sets the overall height of the pattern, and the zero shift and the cell length put the peaks where they are measured, so they come first.

Tick **Free** for the **Linked structures** rows the stage names; then tick **Free** for the **Instrument** rows the stage names; then tick **Free** for the **Cell** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-1-fit.webp?v=0e8465fafe9d" data-gui-dark="169e0374fa0b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Scale, 2θ zero and cell"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Scale, 2θ zero and cell"><title>Fit: Scale, 2θ zero and cell</title><defs><clipPath id="gui-clip-stage-1-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-1-fit.webp?v=0e8465fafe9d" data-gui-dark="169e0374fa0b" width="1480" height="800" clip-path="url(#gui-clip-stage-1-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-1-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-1-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,239]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 353.000 Q1479.000 357.000 1475.000 357.000 L775.000 357.000 Q771.000 357.000 771.000 353.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Background

With the peaks in place, the five background points follow the level between them.

A group is freed in one action: choose it in the category filter above the table, then click the **Free** column header and choose **Free · all**.

<div class="gui-viewer" markdown="1">


=== "Filter"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/group-filter.webp?v=584e0f868c21" data-gui-dark="f2123cc6dc94" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Filter the table to Background"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Filter the table to Background"><title>Filter the table to Background</title><defs><clipPath id="gui-clip-group-filter-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/group-filter.webp?v=584e0f868c21" data-gui-dark="f2123cc6dc94" width="1480" height="800" clip-path="url(#gui-clip-group-filter-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="group-filter-overview-1" data-gui-area="sidebar" data-gui-parts="[[1012.5,133,225,35]]" d="M1013.500 138.000 Q1013.500 134.000 1017.500 134.000 L1232.500 134.000 Q1236.500 134.000 1236.500 138.000 L1236.500 163.000 Q1236.500 167.000 1232.500 167.000 L1017.500 167.000 Q1013.500 167.000 1013.500 163.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Free · all"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/group-free-all.webp?v=ac98d92d1b2f" data-gui-dark="ac2a27d62b14" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Free all from the header"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Free all from the header"><title>Free all from the header</title><defs><clipPath id="gui-clip-group-free-all-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/group-free-all.webp?v=ac98d92d1b2f" data-gui-dark="ac2a27d62b14" width="1480" height="800" clip-path="url(#gui-clip-group-free-all-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="group-free-all-overview-1" data-gui-area="sidebar" data-gui-parts="[[1383,231,78,39]]" d="M1384.000 236.000 Q1384.000 232.000 1388.000 232.000 L1456.000 232.000 Q1460.000 232.000 1460.000 236.000 L1460.000 265.000 Q1460.000 269.000 1456.000 269.000 L1388.000 269.000 Q1384.000 269.000 1384.000 265.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>

Filter the **Background** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-2-fit.webp?v=8866fefe1f4c" data-gui-dark="13451141630f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Background"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Background"><title>Fit: Background</title><defs><clipPath id="gui-clip-stage-2-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-2-fit.webp?v=8866fefe1f4c" data-gui-dark="13451141630f" width="1480" height="800" clip-path="url(#gui-clip-stage-2-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-2-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-2-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Peak widths

The profile terms now fit the widths and shapes of the peaks.

Tick **Free** for the **Peak profile** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-3-fit.webp?v=7a79b4d1f360" data-gui-dark="b12df586891b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Peak widths"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Peak widths"><title>Fit: Peak widths</title><defs><clipPath id="gui-clip-stage-3-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-3-fit.webp?v=7a79b4d1f360" data-gui-dark="b12df586891b" width="1480" height="800" clip-path="url(#gui-clip-stage-3-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-3-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-3-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,395]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 509.000 Q1479.000 513.000 1475.000 513.000 L775.000 513.000 Q771.000 513.000 771.000 509.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Displacements

Every atom sits on a special position of P m -3 m, so there are no coordinates to fit. The displacements change the peak intensities with angle and come last.

Tick **Free** for the **Atomic displacement** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-4-fit.webp?v=9ba9a266d169" data-gui-dark="c53f376325bc" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Displacements"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Displacements"><title>Fit: Displacements</title><defs><clipPath id="gui-clip-stage-4-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-4-fit.webp?v=9ba9a266d169" data-gui-dark="c53f376325bc" width="1480" height="800" clip-path="url(#gui-clip-stage-4-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-4-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-4-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,356]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 470.000 Q1479.000 474.000 1475.000 474.000 L775.000 474.000 Q771.000 474.000 771.000 470.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Constrain La and Ba

The correlations show the displacements of La and Ba moving together almost exactly, with opposite signs: they share one site and scatter neutrons similarly, so the pattern cannot tell them apart, and their s.u. are large. Give each an alias and constrain Ba's to follow La's, then fit again. Ba's displacement is no longer fitted on its own.

Tick **Free** for the **Atomic displacement** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-5-fit.webp?v=b1f395accf19" data-gui-dark="2ce0f85fc869" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Constrain La and Ba"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Constrain La and Ba"><title>Fit: Constrain La and Ba</title><defs><clipPath id="gui-clip-stage-5-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-5-fit.webp?v=b1f395accf19" data-gui-dark="2ce0f85fc869" width="1480" height="800" clip-path="url(#gui-clip-stage-5-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-5-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-5-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,317]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 431.000 Q1479.000 435.000 1475.000 435.000 L775.000 435.000 Q771.000 435.000 771.000 431.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Correlations

The **Correlations** view on **Analysis** shows which fitted parameters move together.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/correlations.webp?v=e2d8f0040eea" data-gui-dark="761568843f9b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the correlations"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the correlations"><title>Inspect the correlations</title><defs><clipPath id="gui-clip-correlations-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/correlations.webp?v=e2d8f0040eea" data-gui-dark="761568843f9b" width="1480" height="800" clip-path="url(#gui-clip-correlations-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="correlations-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Report

The **Report** page collects the structure, the experiment and the fit.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/report.webp?v=c3705a53a79a" data-gui-dark="6b05d2f112fa" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Review the report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Review the report"><title>Review the report</title><defs><clipPath id="gui-clip-report-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/report.webp?v=c3705a53a79a" data-gui-dark="6b05d2f112fa" width="1480" height="800" clip-path="url(#gui-clip-report-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="report-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

</figure>
