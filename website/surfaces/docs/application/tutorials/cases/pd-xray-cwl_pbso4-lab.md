---
template: gui.html
---

# Rietveld fit: PbSO₄, laboratory X-ray

The same staged fit as the Python and Command line tutorials, in the app. Its structure and experiment come from EasyDiffraction's collection with **Load ▾ From web…**, and each stage frees its parameters in the **Parameters** table on **Analysis** before the fit.

Fit PbSO₄ to the Rietveld round robin's laboratory X-ray pattern, with the Cu K&alpha; doublet
and Bérar-Baldinozzi asymmetry.

The project is the catalogue case `pd-xray-cwl_pbso4-lab`, the one the command line and the
app's Examples open.

## Create a project

Press **Start** on Home, then **Create a new project**, and give it a name.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/project-created.webp?v=c99323780298" data-gui-dark="362ce1a34314" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create the project"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create the project"><title>Create the project</title><defs><clipPath id="gui-clip-project-created-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/project-created.webp?v=c99323780298" data-gui-dark="362ce1a34314" width="1480" height="800" clip-path="url(#gui-clip-project-created-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="project-created-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

</div>

## Load the structure

On **Structure**, choose **Load ▾ From web…**, search for each entry by its id and click it:

- `pd-xray-cwl_pbso4-lab-pbso4`

<div class="gui-viewer" markdown="1">


=== "Search"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/structure-web-0.webp?v=a432fbf639ae" data-gui-dark="575200fa1566" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Find the structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Find the structure"><title>Find the structure</title><defs><clipPath id="gui-clip-structure-web-0-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/structure-web-0.webp?v=a432fbf639ae" data-gui-dark="575200fa1566" width="1480" height="800" clip-path="url(#gui-clip-structure-web-0-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-web-0-overview-1" data-gui-area="main" data-gui-parts="[[532,276,416,35]]" d="M533.000 281.000 Q533.000 277.000 537.000 277.000 L943.000 277.000 Q947.000 277.000 947.000 281.000 L947.000 306.000 Q947.000 310.000 943.000 310.000 L537.000 310.000 Q533.000 310.000 533.000 306.000 Z" /><path class="" data-gui-region="structure-web-0-overview-2" data-gui-area="main" data-gui-parts="[[102,460,1276,78]]" d="M103.000 465.000 Q103.000 461.000 107.000 461.000 L1373.000 461.000 Q1377.000 461.000 1377.000 465.000 L1377.000 533.000 Q1377.000 537.000 1373.000 537.000 L107.000 537.000 Q103.000 537.000 103.000 533.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Loaded"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/structure-loaded-0.webp?v=b80d1d0b8897" data-gui-dark="f7e63bb287c7" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load the structure pbso4"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load the structure pbso4"><title>Load the structure pbso4</title><defs><clipPath id="gui-clip-structure-loaded-0-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/structure-loaded-0.webp?v=b80d1d0b8897" data-gui-dark="f7e63bb287c7" width="1480" height="800" clip-path="url(#gui-clip-structure-loaded-0-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-loaded-0-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 241.000 Q1465.000 245.000 1461.000 245.000 L789.000 245.000 Q785.000 245.000 785.000 241.000 Z" /><path class="" data-gui-region="structure-loaded-0-overview-2" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

</div>

## Load the experiment

On **Experiment**, choose **Load ▾ Full experiment From web…**, search for each entry by its id and click it:

- `pd-xray-cwl_pbso4-lab-lab`

<div class="gui-viewer" markdown="1">


=== "Search"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/experiment-web-0.webp?v=324a40209c51" data-gui-dark="6cd977971981" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Find the experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Find the experiment"><title>Find the experiment</title><defs><clipPath id="gui-clip-experiment-web-0-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/experiment-web-0.webp?v=324a40209c51" data-gui-dark="6cd977971981" width="1480" height="800" clip-path="url(#gui-clip-experiment-web-0-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-web-0-overview-1" data-gui-area="main" data-gui-parts="[[532,252,416,35]]" d="M533.000 257.000 Q533.000 253.000 537.000 253.000 L943.000 253.000 Q947.000 253.000 947.000 257.000 L947.000 282.000 Q947.000 286.000 943.000 286.000 L537.000 286.000 Q533.000 286.000 533.000 282.000 Z" /><path class="" data-gui-region="experiment-web-0-overview-2" data-gui-area="main" data-gui-parts="[[102,485,1276,78]]" d="M103.000 490.000 Q103.000 486.000 107.000 486.000 L1373.000 486.000 Q1377.000 486.000 1377.000 490.000 L1377.000 558.000 Q1377.000 562.000 1373.000 562.000 L107.000 562.000 Q103.000 562.000 103.000 558.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Loaded"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/experiment-loaded-0.webp?v=15f8d6479f27" data-gui-dark="e55d80f4206e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load the experiment lab"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load the experiment lab"><title>Load the experiment lab</title><defs><clipPath id="gui-clip-experiment-loaded-0-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/experiment-loaded-0.webp?v=15f8d6479f27" data-gui-dark="e55d80f4206e" width="1480" height="800" clip-path="url(#gui-clip-experiment-loaded-0-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-loaded-0-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 241.000 Q1465.000 245.000 1461.000 245.000 L789.000 245.000 Q785.000 245.000 785.000 241.000 Z" /><path class="" data-gui-region="experiment-loaded-0-overview-2" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>

## Start with nothing free

Entries loaded from the database can come with parameters already free. On **Analysis**, open the **Free** column header of the **Parameters** table and fix every parameter, so the stages below free one group at a time.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/nothing-free.webp?v=eb7439c35352" data-gui-dark="6ebe9e24f074" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Start with every parameter fixed"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Start with every parameter fixed"><title>Start with every parameter fixed</title><defs><clipPath id="gui-clip-nothing-free-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/nothing-free.webp?v=eb7439c35352" data-gui-dark="6ebe9e24f074" width="1480" height="800" clip-path="url(#gui-clip-nothing-free-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="nothing-free-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path class="" data-gui-region="nothing-free-overview-2" data-gui-area="sidebar" data-gui-parts="[[1383,231,78,39]]" d="M1384.000 236.000 Q1384.000 232.000 1388.000 232.000 L1456.000 232.000 Q1460.000 232.000 1460.000 236.000 L1460.000 265.000 Q1460.000 269.000 1456.000 269.000 L1388.000 269.000 Q1384.000 269.000 1384.000 265.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Set the minimizer

On **Analysis → Extra**, set the **Minimizer** as the case's project does: the **Shift/s.u.** stop rule and room for more iterations.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/minimizer.webp?v=09191292870c" data-gui-dark="3c155cfd0935" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Set the minimizer as the project does"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Set the minimizer as the project does"><title>Set the minimizer as the project does</title><defs><clipPath id="gui-clip-minimizer-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/minimizer.webp?v=09191292870c" data-gui-dark="3c155cfd0935" width="1480" height="800" clip-path="url(#gui-clip-minimizer-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="minimizer-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,259]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 373.000 Q1479.000 377.000 1475.000 377.000 L775.000 377.000 Q771.000 377.000 771.000 373.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Scale and 2θ zero

The 2θ zero first: freed together with the cell from the start, the two pull against each other and the fit cannot take a step.

Tick **Free** for the **Linked structures** rows the stage names; then tick **Free** for the **Instrument** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-1-fit.webp?v=4dd84e9e570b" data-gui-dark="67fe5c616e3c" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Scale and 2θ zero"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Scale and 2θ zero"><title>Fit: Scale and 2θ zero</title><defs><clipPath id="gui-clip-stage-1-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-1-fit.webp?v=4dd84e9e570b" data-gui-dark="67fe5c616e3c" width="1480" height="800" clip-path="url(#gui-clip-stage-1-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-1-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-1-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,240]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 354.000 Q1479.000 358.000 1475.000 358.000 L775.000 358.000 Q771.000 358.000 771.000 354.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Cell

Filter the **Cell** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-2-fit.webp?v=740cdb9d9b43" data-gui-dark="439a084adb9a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Cell"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Cell"><title>Fit: Cell</title><defs><clipPath id="gui-clip-stage-2-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-2-fit.webp?v=740cdb9d9b43" data-gui-dark="439a084adb9a" width="1480" height="800" clip-path="url(#gui-clip-stage-2-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-2-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-2-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Background

The six Chebyshev terms.

Filter the **Background** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-3-fit.webp?v=1953c5fc6f0c" data-gui-dark="00c5fbbb3ef4" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Background"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Background"><title>Fit: Background</title><defs><clipPath id="gui-clip-stage-3-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-3-fit.webp?v=1953c5fc6f0c" data-gui-dark="00c5fbbb3ef4" width="1480" height="800" clip-path="url(#gui-clip-stage-3-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-3-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-3-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Peak widths

Filter the **Peak broadening** parameters using the category filter, click the **Free** column header and choose **Free · all**; then tick **Free** for the **Peak mixing** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-4-fit.webp?v=6b888e90fc15" data-gui-dark="d0b0f5c67987" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Peak widths"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Peak widths"><title>Fit: Peak widths</title><defs><clipPath id="gui-clip-stage-4-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-4-fit.webp?v=6b888e90fc15" data-gui-dark="d0b0f5c67987" width="1480" height="800" clip-path="url(#gui-clip-stage-4-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-4-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-4-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,278]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 392.000 Q1479.000 396.000 1475.000 396.000 L775.000 396.000 Q771.000 396.000 771.000 392.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Peak asymmetry

Tick **Free** for the **Peak asymmetry** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-5-fit.webp?v=4524cba57b87" data-gui-dark="153144eb5e88" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Peak asymmetry"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Peak asymmetry"><title>Fit: Peak asymmetry</title><defs><clipPath id="gui-clip-stage-5-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-5-fit.webp?v=4524cba57b87" data-gui-dark="153144eb5e88" width="1480" height="800" clip-path="url(#gui-clip-stage-5-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-5-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-5-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,356]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 470.000 Q1479.000 474.000 1475.000 474.000 L775.000 474.000 Q771.000 474.000 771.000 470.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Lead and sulphur positions

X-rays see the heavy atoms first, so their coordinates come before the oxygens'.

Filter the **Atomic coordinates** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-6-fit.webp?v=2c89925d7034" data-gui-dark="eee73b54d538" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Lead and sulphur positions"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Lead and sulphur positions"><title>Fit: Lead and sulphur positions</title><defs><clipPath id="gui-clip-stage-6-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-6-fit.webp?v=2c89925d7034" data-gui-dark="eee73b54d538" width="1480" height="800" clip-path="url(#gui-clip-stage-6-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-6-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-6-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Oxygen positions

Filter the **Atomic coordinates** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-7-fit.webp?v=e91e5c6d07f5" data-gui-dark="89d0997147d8" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Oxygen positions"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Oxygen positions"><title>Fit: Oxygen positions</title><defs><clipPath id="gui-clip-stage-7-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-7-fit.webp?v=e91e5c6d07f5" data-gui-dark="89d0997147d8" width="1480" height="800" clip-path="url(#gui-clip-stage-7-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-7-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-7-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Displacements

The correlations after this stage show how far the oxygen displacements can be told apart; the case keeps them separate.

Filter the **Atomic displacement** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-8-fit.webp?v=ba54f7a98097" data-gui-dark="4e290b824d0b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Displacements"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Displacements"><title>Fit: Displacements</title><defs><clipPath id="gui-clip-stage-8-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/stage-8-fit.webp?v=ba54f7a98097" data-gui-dark="4e290b824d0b" width="1480" height="800" clip-path="url(#gui-clip-stage-8-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-8-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-8-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Correlations

The **Correlations** view on **Analysis** shows which fitted parameters move together.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/correlations.webp?v=4264913aa344" data-gui-dark="855f87cfedb7" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the correlations"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the correlations"><title>Inspect the correlations</title><defs><clipPath id="gui-clip-correlations-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/correlations.webp?v=4264913aa344" data-gui-dark="855f87cfedb7" width="1480" height="800" clip-path="url(#gui-clip-correlations-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="correlations-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Report

The **Report** page collects the structure, the experiment and the fit.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/report.webp?v=e0aad514fbf2" data-gui-dark="a1a1c2184e6e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Review the report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Review the report"><title>Review the report</title><defs><clipPath id="gui-clip-report-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-xray-cwl_pbso4-lab/report.webp?v=e0aad514fbf2" data-gui-dark="a1a1c2184e6e" width="1480" height="800" clip-path="url(#gui-clip-report-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="report-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

</figure>
