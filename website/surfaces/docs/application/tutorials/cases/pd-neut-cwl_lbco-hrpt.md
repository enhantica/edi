---
template: gui.html
---

# La₀.₅Ba₀.₅CoO₃ on HRPT

The same staged fit as the Python and Command line tutorials, in the app. Its structure and experiment come from EasyDiffraction's collection with **Load ▾ From web…**, and each stage frees its parameters in the **Parameters** table on **Analysis** before the fit.

## Create a project

Press **Start** on Home, then **Create a new project**, and give it a name.

<div class="gui-viewer" markdown="1">


=== "Start"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/home.webp?v=5709a75ad843" data-gui-dark="a567f191fe25" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Start a new analysis"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Start a new analysis"><title>Start a new analysis</title><defs><clipPath id="gui-clip-home-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/home.webp?v=5709a75ad843" data-gui-dark="a567f191fe25" width="1480" height="800" clip-path="url(#gui-clip-home-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="home-overview-1" data-gui-area="main" data-gui-parts="[[573,404,334,39]]" d="M574.000 409.000 Q574.000 405.000 578.000 405.000 L902.000 405.000 Q906.000 405.000 906.000 409.000 L906.000 438.000 Q906.000 442.000 902.000 442.000 L578.000 442.000 Q574.000 442.000 574.000 438.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[542,0,53.46875,77]]" d="M543.000 5.000 Q543.000 1.000 547.000 1.000 L590.469 1.000 Q594.469 1.000 594.469 5.000 L594.469 72.000 Q594.469 76.000 590.469 76.000 L547.000 76.000 Q543.000 76.000 543.000 72.000 Z" /></svg></a>

    </figure>

=== "Details"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/project-details.webp?v=0fcfbbf35c64" data-gui-dark="36a682c31e09" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Enter the project details"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Enter the project details"><title>Enter the project details</title><defs><clipPath id="gui-clip-project-details-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/project-details.webp?v=0fcfbbf35c64" data-gui-dark="36a682c31e09" width="1480" height="800" clip-path="url(#gui-clip-project-details-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="project-details-overview-1" data-gui-area="main" data-gui-parts="[[495,238,490,35]]" d="M496.000 243.000 Q496.000 239.000 500.000 239.000 L980.000 239.000 Q984.000 239.000 984.000 243.000 L984.000 268.000 Q984.000 272.000 980.000 272.000 L500.000 272.000 Q496.000 272.000 496.000 268.000 Z" /><path class="" data-gui-region="project-details-overview-2" data-gui-area="main" data-gui-parts="[[495,306,490,36]]" d="M496.000 311.000 Q496.000 307.000 500.000 307.000 L980.000 307.000 Q984.000 307.000 984.000 311.000 L984.000 337.000 Q984.000 341.000 980.000 341.000 L500.000 341.000 Q496.000 341.000 496.000 337.000 Z" /><path class="" data-gui-region="project-details-overview-3" data-gui-area="main" data-gui-parts="[[495,547,490,35]]" d="M496.000 552.000 Q496.000 548.000 500.000 548.000 L980.000 548.000 Q984.000 548.000 984.000 552.000 L984.000 577.000 Q984.000 581.000 980.000 581.000 L500.000 581.000 Q496.000 581.000 496.000 577.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "Created"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/project-created.webp?v=caf3d1ca0a3a" data-gui-dark="746feecc302d" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create the project"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create the project"><title>Create the project</title><defs><clipPath id="gui-clip-project-created-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/project-created.webp?v=caf3d1ca0a3a" data-gui-dark="746feecc302d" width="1480" height="800" clip-path="url(#gui-clip-project-created-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="project-created-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

</div>

## Build the structure

On **Structure**, choose **Create structure** and name it, then set its space group and cell, add the atom sites and give each its displacement.

<div class="gui-viewer" markdown="1">


=== "Structure"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-created.webp?v=0f3fdd194c3e" data-gui-dark="80240b15dc72" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create the structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create the structure"><title>Create the structure</title><defs><clipPath id="gui-clip-structure-created-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-created.webp?v=0f3fdd194c3e" data-gui-dark="80240b15dc72" width="1480" height="800" clip-path="url(#gui-clip-structure-created-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-created-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 241.000 Q1465.000 245.000 1461.000 245.000 L789.000 245.000 Q785.000 245.000 785.000 241.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Space group and cell"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-cell.webp?v=a93f1b498b6f" data-gui-dark="24521555f71d" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Set the space group and the cell"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Set the space group and the cell"><title>Set the space group and the cell</title><defs><clipPath id="gui-clip-structure-cell-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-cell.webp?v=a93f1b498b6f" data-gui-dark="24521555f71d" width="1480" height="800" clip-path="url(#gui-clip-structure-cell-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-cell-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,42]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 198.000 Q1479.000 202.000 1475.000 202.000 L775.000 202.000 Q771.000 202.000 771.000 198.000 Z" /><path class="" data-gui-region="structure-cell-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,203,710,119]]" d="M771.000 208.000 Q771.000 204.000 775.000 204.000 L1475.000 204.000 Q1479.000 204.000 1479.000 208.000 L1479.000 317.000 Q1479.000 321.000 1475.000 321.000 L775.000 321.000 Q771.000 321.000 771.000 317.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Atom sites"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-sites.webp?v=e733ecc4d4c5" data-gui-dark="14f6a3173f1a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Add the atom sites"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Add the atom sites"><title>Add the atom sites</title><defs><clipPath id="gui-clip-structure-sites-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-sites.webp?v=e733ecc4d4c5" data-gui-dark="14f6a3173f1a" width="1480" height="800" clip-path="url(#gui-clip-structure-sites-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-sites-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,294,682,234]]" d="M785.000 299.000 Q785.000 295.000 789.000 295.000 L1461.000 295.000 Q1465.000 295.000 1465.000 299.000 L1465.000 523.000 Q1465.000 527.000 1461.000 527.000 L789.000 527.000 Q785.000 527.000 785.000 523.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Displacements"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-adp.webp?v=3d18fc98e579" data-gui-dark="c30be9bf4019" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Set the displacements"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Set the displacements"><title>Set the displacements</title><defs><clipPath id="gui-clip-structure-adp-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/structure-adp.webp?v=3d18fc98e579" data-gui-dark="c30be9bf4019" width="1480" height="800" clip-path="url(#gui-clip-structure-adp-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-adp-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,336,682,234]]" d="M785.000 341.000 Q785.000 337.000 789.000 337.000 L1461.000 337.000 Q1465.000 337.000 1465.000 341.000 L1465.000 565.000 Q1465.000 569.000 1461.000 569.000 L789.000 569.000 Q785.000 569.000 785.000 565.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

</div>

## Create the experiment

On **Experiment**, choose **Create experiment** and its type, load the measured data with **Load ▾ Measured data From web…** from EasyDiffraction's collection, then set the instrument, the peak widths, the background points and the excluded regions, and link the structure.

<div class="gui-viewer" markdown="1">


=== "Experiment"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-created.webp?v=32149afb617b" data-gui-dark="93cba952a1ff" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create the experiment and choose its type"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create the experiment and choose its type"><title>Create the experiment and choose its type</title><defs><clipPath id="gui-clip-experiment-created-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-created.webp?v=32149afb617b" data-gui-dark="93cba952a1ff" width="1480" height="800" clip-path="url(#gui-clip-experiment-created-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-created-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,260,682,126]]" d="M785.000 265.000 Q785.000 261.000 789.000 261.000 L1461.000 261.000 Q1465.000 261.000 1465.000 265.000 L1465.000 381.000 Q1465.000 385.000 1461.000 385.000 L789.000 385.000 Q785.000 385.000 785.000 381.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Search"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/data-web.webp?v=b356b82ead80" data-gui-dark="b649659d8ee0" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Find the measured data in the EasyDiffraction collection"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Find the measured data in the EasyDiffraction collection"><title>Find the measured data in the EasyDiffraction collection</title><defs><clipPath id="gui-clip-data-web-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/data-web.webp?v=b356b82ead80" data-gui-dark="b649659d8ee0" width="1480" height="800" clip-path="url(#gui-clip-data-web-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="data-web-overview-1" data-gui-area="main" data-gui-parts="[[601,252,279,35]]" d="M602.000 257.000 Q602.000 253.000 606.000 253.000 L875.000 253.000 Q879.000 253.000 879.000 257.000 L879.000 282.000 Q879.000 286.000 875.000 286.000 L606.000 286.000 Q602.000 286.000 602.000 282.000 Z" /><path class="" data-gui-region="data-web-overview-2" data-gui-area="main" data-gui-parts="[[308,485,865,78]]" d="M309.000 490.000 Q309.000 486.000 313.000 486.000 L1168.000 486.000 Q1172.000 486.000 1172.000 490.000 L1172.000 558.000 Q1172.000 562.000 1168.000 562.000 L313.000 562.000 Q309.000 562.000 309.000 558.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Measured data"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/data-loaded.webp?v=23cbf85aa0ce" data-gui-dark="1176c6e9eb2e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load the measured data"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load the measured data"><title>Load the measured data</title><defs><clipPath id="gui-clip-data-loaded-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/data-loaded.webp?v=23cbf85aa0ce" data-gui-dark="1176c6e9eb2e" width="1480" height="800" clip-path="url(#gui-clip-data-loaded-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="data-loaded-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Instrument and profile"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-instrument.webp?v=f8178468e3ac" data-gui-dark="b4d4f615872a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Set the wavelength, 2θ zero and peak widths"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Set the wavelength, 2θ zero and peak widths"><title>Set the wavelength, 2θ zero and peak widths</title><defs><clipPath id="gui-clip-experiment-instrument-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-instrument.webp?v=f8178468e3ac" data-gui-dark="b4d4f615872a" width="1480" height="800" clip-path="url(#gui-clip-experiment-instrument-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-instrument-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,203,710,42]]" d="M771.000 208.000 Q771.000 204.000 775.000 204.000 L1475.000 204.000 Q1479.000 204.000 1479.000 208.000 L1479.000 240.000 Q1479.000 244.000 1475.000 244.000 L775.000 244.000 Q771.000 244.000 771.000 240.000 Z" /><path class="" data-gui-region="experiment-instrument-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,245,710,189]]" d="M771.000 250.000 Q771.000 246.000 775.000 246.000 L1475.000 246.000 Q1479.000 246.000 1479.000 250.000 L1479.000 429.000 Q1479.000 433.000 1475.000 433.000 L775.000 433.000 Q771.000 433.000 771.000 429.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Background"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-background.webp?v=ea025123887a" data-gui-dark="a545720f42a0" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Add the background points and excluded regions"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Add the background points and excluded regions"><title>Add the background points and excluded regions</title><defs><clipPath id="gui-clip-experiment-background-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-background.webp?v=ea025123887a" data-gui-dark="a545720f42a0" width="1480" height="800" clip-path="url(#gui-clip-experiment-background-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-background-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,336,682,117]]" d="M785.000 341.000 Q785.000 337.000 789.000 337.000 L1461.000 337.000 Q1465.000 337.000 1465.000 341.000 L1465.000 448.000 Q1465.000 452.000 1461.000 452.000 L789.000 452.000 Q785.000 452.000 785.000 448.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Linked structure"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-linked.webp?v=5745caaf5905" data-gui-dark="7026345e1fcf" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Link the structure to the experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Link the structure to the experiment"><title>Link the structure to the experiment</title><defs><clipPath id="gui-clip-experiment-linked-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/experiment-linked.webp?v=5745caaf5905" data-gui-dark="7026345e1fcf" width="1480" height="800" clip-path="url(#gui-clip-experiment-linked-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-linked-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,378,682,78]]" d="M785.000 383.000 Q785.000 379.000 789.000 379.000 L1461.000 379.000 Q1465.000 379.000 1465.000 383.000 L1465.000 451.000 Q1465.000 455.000 1461.000 455.000 L789.000 455.000 Q785.000 455.000 785.000 451.000 Z" /><path class="" data-gui-region="experiment-linked-overview-2" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>

## Set the minimizer

On **Analysis → Extra**, set the **Minimizer** as the case's project does: the **Shift/s.u.** stop rule and room for more iterations.

<figure class="gui-figure gui-placeholder"><div class="gui-placeholder-box">Screenshot coming soon</div></figure>

## Start with nothing free

On **Analysis**, open the **Free** column header of the **Parameters** table and fix every parameter, so the stages below free one group at a time.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/nothing-free.webp?v=857fa2cb3447" data-gui-dark="e6210ef7295e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Start with every parameter fixed"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Start with every parameter fixed"><title>Start with every parameter fixed</title><defs><clipPath id="gui-clip-nothing-free-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/nothing-free.webp?v=857fa2cb3447" data-gui-dark="e6210ef7295e" width="1480" height="800" clip-path="url(#gui-clip-nothing-free-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="nothing-free-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path class="" data-gui-region="nothing-free-overview-2" data-gui-area="sidebar" data-gui-parts="[[1383,231,78,39]]" d="M1384.000 236.000 Q1384.000 232.000 1388.000 232.000 L1456.000 232.000 Q1460.000 232.000 1460.000 236.000 L1460.000 265.000 Q1460.000 269.000 1456.000 269.000 L1388.000 269.000 Q1384.000 269.000 1384.000 265.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Scale, 2θ zero and cell

The scale sets the overall height of the pattern, and the zero shift and the cell length put the peaks where they are measured, so they come first.

A group is freed in one action: choose it in the category filter above the table, then click the **Free** column header and choose **Free · all**.

<div class="gui-viewer" markdown="1">


=== "Filter"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/group-filter.webp?v=8d0069eea659" data-gui-dark="1e52c7a7b35f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Filter the table to Background"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Filter the table to Background"><title>Filter the table to Background</title><defs><clipPath id="gui-clip-group-filter-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/group-filter.webp?v=8d0069eea659" data-gui-dark="1e52c7a7b35f" width="1480" height="800" clip-path="url(#gui-clip-group-filter-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="group-filter-overview-1" data-gui-area="sidebar" data-gui-parts="[[1012.5,133,225,35]]" d="M1013.500 138.000 Q1013.500 134.000 1017.500 134.000 L1232.500 134.000 Q1236.500 134.000 1236.500 138.000 L1236.500 163.000 Q1236.500 167.000 1232.500 167.000 L1017.500 167.000 Q1013.500 167.000 1013.500 163.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Free · all"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/group-free-all.webp?v=799ed12594e7" data-gui-dark="113fbfc0f7eb" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Free all from the Free column header"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Free all from the Free column header"><title>Free all from the Free column header</title><defs><clipPath id="gui-clip-group-free-all-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/group-free-all.webp?v=799ed12594e7" data-gui-dark="113fbfc0f7eb" width="1480" height="800" clip-path="url(#gui-clip-group-free-all-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="group-free-all-overview-1" data-gui-area="sidebar" data-gui-parts="[[1383,231,78,39]]" d="M1384.000 236.000 Q1384.000 232.000 1388.000 232.000 L1456.000 232.000 Q1460.000 232.000 1460.000 236.000 L1460.000 265.000 Q1460.000 269.000 1456.000 269.000 L1388.000 269.000 Q1384.000 269.000 1384.000 265.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>

Filter the **Linked structures** and **Cell** parameters, one category at a time, using the category filter and the **Instrument** parameters with **calib** in their name using the category filter and the name filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-1-fit.webp?v=960454cda813" data-gui-dark="c0c7cd2fb44a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Scale, 2θ zero and cell"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Scale, 2θ zero and cell"><title>Fit: Scale, 2θ zero and cell</title><defs><clipPath id="gui-clip-stage-1-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-1-fit.webp?v=960454cda813" data-gui-dark="c0c7cd2fb44a" width="1480" height="800" clip-path="url(#gui-clip-stage-1-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-1-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-1-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Background

With the peaks in place, the five background points follow the level between them.

Filter the **Background** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-2-fit.webp?v=65de65f7bf84" data-gui-dark="28452584e72a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Background"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Background"><title>Fit: Background</title><defs><clipPath id="gui-clip-stage-2-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-2-fit.webp?v=65de65f7bf84" data-gui-dark="28452584e72a" width="1480" height="800" clip-path="url(#gui-clip-stage-2-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-2-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-2-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Peak widths

The profile terms now fit the widths and shapes of the peaks.

Filter the **Peak profile** parameters using the category filter, click the **Free** column header and choose **Free · all**; then type **lorentz_x** in the name filter and choose **Fixed · all** in the same menu, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-3-fit.webp?v=913509a2090b" data-gui-dark="a867a2731bba" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Peak widths"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Peak widths"><title>Fit: Peak widths</title><defs><clipPath id="gui-clip-stage-3-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-3-fit.webp?v=913509a2090b" data-gui-dark="a867a2731bba" width="1480" height="800" clip-path="url(#gui-clip-stage-3-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-3-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-3-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Displacements

Every atom sits on a special position of P m -3 m, so there are no coordinates to fit. The displacements change the peak intensities with angle and come last.

Filter the **Atomic displacement** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-4-fit.webp?v=d4957e742b78" data-gui-dark="864a6fbfddba" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Displacements"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Displacements"><title>Fit: Displacements</title><defs><clipPath id="gui-clip-stage-4-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-4-fit.webp?v=d4957e742b78" data-gui-dark="864a6fbfddba" width="1480" height="800" clip-path="url(#gui-clip-stage-4-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-4-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-4-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Constrain La and Ba

The correlations show the displacements of La and Ba moving together almost exactly, with opposite signs: they share one site and scatter neutrons similarly, so the pattern cannot tell them apart, and their s.u. are large. Give each an alias and constrain Ba's to follow La's, then fit again. Ba's displacement is no longer fitted on its own.

Filter the **Atomic displacement** parameters with **[Ba]** in their name using the category filter and the name filter, click the **Free** column header and choose **Fixed · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-5-fit.webp?v=0ec18b8da950" data-gui-dark="1cfa2fe240d0" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Constrain La and Ba"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Constrain La and Ba"><title>Fit: Constrain La and Ba</title><defs><clipPath id="gui-clip-stage-5-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/stage-5-fit.webp?v=0ec18b8da950" data-gui-dark="1cfa2fe240d0" width="1480" height="800" clip-path="url(#gui-clip-stage-5-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-5-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-5-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Correlations

The **Correlations** view on **Analysis** shows which fitted parameters move together.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/correlations.webp?v=52743e219295" data-gui-dark="9feb2785b0f3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the correlations"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the correlations"><title>Inspect the correlations</title><defs><clipPath id="gui-clip-correlations-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/correlations.webp?v=52743e219295" data-gui-dark="9feb2785b0f3" width="1480" height="800" clip-path="url(#gui-clip-correlations-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="correlations-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Report

The **Report** page collects the structure, the experiment and the fit.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/report.webp?v=e6fe14b91608" data-gui-dark="132ab819989b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Review the report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Review the report"><title>Review the report</title><defs><clipPath id="gui-clip-report-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_lbco-hrpt/report.webp?v=e6fe14b91608" data-gui-dark="132ab819989b" width="1480" height="800" clip-path="url(#gui-clip-report-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="report-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

</figure>
