---
template: gui.html
---

# Single-crystal fit: Co₂SiO₄ at three temperatures, HEiDi

The same staged fit as the Python and Command line tutorials, in the app. Its structure and experiment come from EasyDiffraction's collection with **Load ▾ From web…**, and each stage frees its parameters in the **Parameters** table on **Analysis** before the fit.

## Create a project

Press **Start** on Home, then **Create a new project**, and give it a name.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/project-created.webp?v=1bc9d95ffa72" data-gui-dark="1b1f5237fff8" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create the project"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create the project"><title>Create the project</title><defs><clipPath id="gui-clip-project-created-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/project-created.webp?v=1bc9d95ffa72" data-gui-dark="1b1f5237fff8" width="1480" height="800" clip-path="url(#gui-clip-project-created-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="project-created-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

</div>

## Load the structures

On **Structure**, choose **Load ▾ From web…**, search for each entry by its id and click it:

- `sc-neut-cwl_cosio-heidi-cosio_300k`
- `sc-neut-cwl_cosio-heidi-cosio_55k`
- `sc-neut-cwl_cosio-heidi-cosio_2k5`

<div class="gui-viewer" markdown="1">


=== "Search"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/structure-web-0.webp?v=fd91392a8398" data-gui-dark="7ac29e591424" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Find the structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Find the structure"><title>Find the structure</title><defs><clipPath id="gui-clip-structure-web-0-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/structure-web-0.webp?v=fd91392a8398" data-gui-dark="7ac29e591424" width="1480" height="800" clip-path="url(#gui-clip-structure-web-0-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-web-0-overview-1" data-gui-area="main" data-gui-parts="[[532,276,416,35]]" d="M533.000 281.000 Q533.000 277.000 537.000 277.000 L943.000 277.000 Q947.000 277.000 947.000 281.000 L947.000 306.000 Q947.000 310.000 943.000 310.000 L537.000 310.000 Q533.000 310.000 533.000 306.000 Z" /><path class="" data-gui-region="structure-web-0-overview-2" data-gui-area="main" data-gui-parts="[[102,460,1276,78]]" d="M103.000 465.000 Q103.000 461.000 107.000 461.000 L1373.000 461.000 Q1377.000 461.000 1377.000 465.000 L1377.000 533.000 Q1377.000 537.000 1373.000 537.000 L107.000 537.000 Q103.000 537.000 103.000 533.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Loaded"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/structure-loaded-2.webp?v=0f311734e97d" data-gui-dark="1cecc8b4642f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load the structure cosio_2k5"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load the structure cosio_2k5"><title>Load the structure cosio_2k5</title><defs><clipPath id="gui-clip-structure-loaded-2-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/structure-loaded-2.webp?v=0f311734e97d" data-gui-dark="1cecc8b4642f" width="1480" height="800" clip-path="url(#gui-clip-structure-loaded-2-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-loaded-2-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,156]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 319.000 Q1465.000 323.000 1461.000 323.000 L789.000 323.000 Q785.000 323.000 785.000 319.000 Z" /><path class="" data-gui-region="structure-loaded-2-overview-2" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

</div>

## Load the experiments

On **Experiment**, choose **Load ▾ Full experiment From web…**, search for each entry by its id and click it:

- `sc-neut-cwl_cosio-heidi-heidi_300k`
- `sc-neut-cwl_cosio-heidi-heidi_55k`
- `sc-neut-cwl_cosio-heidi-heidi_2k5`

<div class="gui-viewer" markdown="1">


=== "Search"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/experiment-web-0.webp?v=e5c365aaee49" data-gui-dark="a355df7105ed" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Find the experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Find the experiment"><title>Find the experiment</title><defs><clipPath id="gui-clip-experiment-web-0-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/experiment-web-0.webp?v=e5c365aaee49" data-gui-dark="a355df7105ed" width="1480" height="800" clip-path="url(#gui-clip-experiment-web-0-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-web-0-overview-1" data-gui-area="main" data-gui-parts="[[532,252,416,35]]" d="M533.000 257.000 Q533.000 253.000 537.000 253.000 L943.000 253.000 Q947.000 253.000 947.000 257.000 L947.000 282.000 Q947.000 286.000 943.000 286.000 L537.000 286.000 Q533.000 286.000 533.000 282.000 Z" /><path class="" data-gui-region="experiment-web-0-overview-2" data-gui-area="main" data-gui-parts="[[102,485,1276,78]]" d="M103.000 490.000 Q103.000 486.000 107.000 486.000 L1373.000 486.000 Q1377.000 486.000 1377.000 490.000 L1377.000 558.000 Q1377.000 562.000 1373.000 562.000 L107.000 562.000 Q103.000 562.000 103.000 558.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Loaded"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/experiment-loaded-2.webp?v=a3e83d372be1" data-gui-dark="9ac00e2919b4" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load the experiment heidi_2k5"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load the experiment heidi_2k5"><title>Load the experiment heidi_2k5</title><defs><clipPath id="gui-clip-experiment-loaded-2-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/experiment-loaded-2.webp?v=a3e83d372be1" data-gui-dark="9ac00e2919b4" width="1480" height="800" clip-path="url(#gui-clip-experiment-loaded-2-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-loaded-2-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,156]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 319.000 Q1465.000 323.000 1461.000 323.000 L789.000 323.000 Q785.000 323.000 785.000 319.000 Z" /><path class="" data-gui-region="experiment-loaded-2-overview-2" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>

## Start with nothing free

Entries loaded from the database can come with parameters already free. On **Analysis**, open the **Free** column header of the **Parameters** table and fix every parameter, so the stages below free one group at a time.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/nothing-free.webp?v=662c14014414" data-gui-dark="5bac5915065b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Start with every parameter fixed"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Start with every parameter fixed"><title>Start with every parameter fixed</title><defs><clipPath id="gui-clip-nothing-free-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/nothing-free.webp?v=662c14014414" data-gui-dark="5bac5915065b" width="1480" height="800" clip-path="url(#gui-clip-nothing-free-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="nothing-free-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path class="" data-gui-region="nothing-free-overview-2" data-gui-area="sidebar" data-gui-parts="[[1383,231,78,39]]" d="M1384.000 236.000 Q1384.000 232.000 1388.000 232.000 L1456.000 232.000 Q1460.000 232.000 1460.000 236.000 L1460.000 265.000 Q1460.000 269.000 1456.000 269.000 L1388.000 269.000 Q1384.000 269.000 1384.000 265.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Fit each experiment on its own

On **Analysis → Extra**, set the fitting mode to independent, so each experiment is fitted alone against its structure, with its own goodness of fit.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/fitting-mode-independent.webp?v=feb135647355" data-gui-dark="6490ac5da684" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit each experiment on its own"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit each experiment on its own"><title>Fit each experiment on its own</title><defs><clipPath id="gui-clip-fitting-mode-independent-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/fitting-mode-independent.webp?v=feb135647355" data-gui-dark="6490ac5da684" width="1480" height="800" clip-path="url(#gui-clip-fitting-mode-independent-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="fitting-mode-independent-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 275.000 Q1479.000 279.000 1475.000 279.000 L775.000 279.000 Q771.000 279.000 771.000 275.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 300 K: scale

The scale brings the calculated intensities to the measured ones.

Choose **heidi_300k** in the datablock filter, then tick **Free** for the **Linked structures** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-1-fit.webp?v=d10e60c00fc4" data-gui-dark="7475525eb800" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 300 K: scale"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 300 K: scale"><title>Fit: 300 K: scale</title><defs><clipPath id="gui-clip-stage-1-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-1-fit.webp?v=d10e60c00fc4" data-gui-dark="7475525eb800" width="1480" height="800" clip-path="url(#gui-clip-stage-1-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-1-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-1-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 300 K: coordinates

Choose **cosio_300k** in the datablock filter, then filter the **Atomic coordinates** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-2-fit.webp?v=511aeb4c71eb" data-gui-dark="c3ae7dd6160e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 300 K: coordinates"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 300 K: coordinates"><title>Fit: 300 K: coordinates</title><defs><clipPath id="gui-clip-stage-2-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-2-fit.webp?v=511aeb4c71eb" data-gui-dark="c3ae7dd6160e" width="1480" height="800" clip-path="url(#gui-clip-stage-2-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-2-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-2-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 300 K: displacements

Choose **cosio_300k** in the datablock filter, then filter the **Atomic displacement** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-3-fit.webp?v=d3f70cdf831f" data-gui-dark="f25637a54616" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 300 K: displacements"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 300 K: displacements"><title>Fit: 300 K: displacements</title><defs><clipPath id="gui-clip-stage-3-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-3-fit.webp?v=d3f70cdf831f" data-gui-dark="f25637a54616" width="1480" height="800" clip-path="url(#gui-clip-stage-3-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-3-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-3-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 300 K: extinction

Larson's anisotropic extinction, its six coefficients starting at zero.

Choose **heidi_300k** in the datablock filter, then filter the **Extinction** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-4-fit.webp?v=0a0e6150c972" data-gui-dark="e3c3756f4fc5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 300 K: extinction"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 300 K: extinction"><title>Fit: 300 K: extinction</title><defs><clipPath id="gui-clip-stage-4-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-4-fit.webp?v=0a0e6150c972" data-gui-dark="e3c3756f4fc5" width="1480" height="800" clip-path="url(#gui-clip-stage-4-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-4-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-4-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 55 K: scale

The 300 K parameters stay free, so the 300 K experiment is fitted again from where it ended.

Choose **heidi_55k** in the datablock filter, then tick **Free** for the **Linked structures** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-5-fit.webp?v=811e0bc686d2" data-gui-dark="4146318b5df7" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 55 K: scale"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 55 K: scale"><title>Fit: 55 K: scale</title><defs><clipPath id="gui-clip-stage-5-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-5-fit.webp?v=811e0bc686d2" data-gui-dark="4146318b5df7" width="1480" height="800" clip-path="url(#gui-clip-stage-5-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-5-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-5-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 55 K: coordinates

Choose **cosio_55k** in the datablock filter, then filter the **Atomic coordinates** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-6-fit.webp?v=71b63eb91a32" data-gui-dark="c82edb7920f2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 55 K: coordinates"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 55 K: coordinates"><title>Fit: 55 K: coordinates</title><defs><clipPath id="gui-clip-stage-6-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-6-fit.webp?v=71b63eb91a32" data-gui-dark="c82edb7920f2" width="1480" height="800" clip-path="url(#gui-clip-stage-6-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-6-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-6-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 55 K: extinction

At 55 K the displacements are small. Freed before the extinction, they would take its place and Co1's tensor would stop being positive definite, so the extinction comes before them here.

Choose **heidi_55k** in the datablock filter, then filter the **Extinction** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-7-fit.webp?v=ea3ec47e31b1" data-gui-dark="6b7178f1fb6e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 55 K: extinction"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 55 K: extinction"><title>Fit: 55 K: extinction</title><defs><clipPath id="gui-clip-stage-7-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-7-fit.webp?v=ea3ec47e31b1" data-gui-dark="6b7178f1fb6e" width="1480" height="800" clip-path="url(#gui-clip-stage-7-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-7-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-7-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 55 K: displacements

Choose **cosio_55k** in the datablock filter, then filter the **Atomic displacement** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-8-fit.webp?v=ed4bfc612a4e" data-gui-dark="744828122801" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 55 K: displacements"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 55 K: displacements"><title>Fit: 55 K: displacements</title><defs><clipPath id="gui-clip-stage-8-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-8-fit.webp?v=ed4bfc612a4e" data-gui-dark="744828122801" width="1480" height="800" clip-path="url(#gui-clip-stage-8-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-8-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-8-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 2.5 K: scale

The nuclear structure first, with every moment still at zero, in the order 55 K needed.

Choose **heidi_2k5** in the datablock filter, then tick **Free** for the **Linked structures** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-9-fit.webp?v=48b0bf4f7888" data-gui-dark="55fc6d88ccde" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 2.5 K: scale"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 2.5 K: scale"><title>Fit: 2.5 K: scale</title><defs><clipPath id="gui-clip-stage-9-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-9-fit.webp?v=48b0bf4f7888" data-gui-dark="55fc6d88ccde" width="1480" height="800" clip-path="url(#gui-clip-stage-9-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-9-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-9-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 2.5 K: coordinates

Choose **cosio_2k5** in the datablock filter, then filter the **Atomic coordinates** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-10-fit.webp?v=da9649fbfd1c" data-gui-dark="a4db3dae6e3c" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 2.5 K: coordinates"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 2.5 K: coordinates"><title>Fit: 2.5 K: coordinates</title><defs><clipPath id="gui-clip-stage-10-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-10-fit.webp?v=da9649fbfd1c" data-gui-dark="a4db3dae6e3c" width="1480" height="800" clip-path="url(#gui-clip-stage-10-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-10-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-10-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 2.5 K: extinction

Choose **heidi_2k5** in the datablock filter, then filter the **Extinction** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-11-fit.webp?v=8bad70dc287f" data-gui-dark="8a1b4dc77171" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 2.5 K: extinction"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 2.5 K: extinction"><title>Fit: 2.5 K: extinction</title><defs><clipPath id="gui-clip-stage-11-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-11-fit.webp?v=8bad70dc287f" data-gui-dark="8a1b4dc77171" width="1480" height="800" clip-path="url(#gui-clip-stage-11-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-11-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-11-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 2.5 K: displacements

Choose **cosio_2k5** in the datablock filter, then filter the **Atomic displacement** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-12-fit.webp?v=d6bec59cdc1b" data-gui-dark="0812f7ed7b7f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 2.5 K: displacements"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 2.5 K: displacements"><title>Fit: 2.5 K: displacements</title><defs><clipPath id="gui-clip-stage-12-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-12-fit.webp?v=d6bec59cdc1b" data-gui-dark="0812f7ed7b7f" width="1480" height="800" clip-path="url(#gui-clip-stage-12-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-12-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-12-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## 2.5 K: the magnetic moments

Free the moment components the magnetic space group allows. They start at zero, where the magnetic intensity has no slope, so the fit starts them at 1 μB and says so.

Choose **cosio_2k5** in the datablock filter, then filter the **Magnetic moments** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-13-fit.webp?v=9ed663bc673b" data-gui-dark="bf03e838e5ab" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: 2.5 K: the magnetic moments"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: 2.5 K: the magnetic moments"><title>Fit: 2.5 K: the magnetic moments</title><defs><clipPath id="gui-clip-stage-13-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/stage-13-fit.webp?v=9ed663bc673b" data-gui-dark="bf03e838e5ab" width="1480" height="800" clip-path="url(#gui-clip-stage-13-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-13-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-13-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Correlations

The **Correlations** view on **Analysis** shows which fitted parameters move together.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/correlations.webp?v=f36d365b2186" data-gui-dark="ed4f42509434" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the correlations"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the correlations"><title>Inspect the correlations</title><defs><clipPath id="gui-clip-correlations-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/correlations.webp?v=f36d365b2186" data-gui-dark="ed4f42509434" width="1480" height="800" clip-path="url(#gui-clip-correlations-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="correlations-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Report

The **Report** page collects the structure, the experiment and the fit.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/report.webp?v=c91b2e57f9b8" data-gui-dark="23ffa0bb8a22" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Review the report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Review the report"><title>Review the report</title><defs><clipPath id="gui-clip-report-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/sc-neut-cwl_cosio-heidi/report.webp?v=c91b2e57f9b8" data-gui-dark="23ffa0bb8a22" width="1480" height="800" clip-path="url(#gui-clip-report-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="report-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

</figure>
