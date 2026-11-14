---
template: gui.html
---

# Magnetic structure fit: Co₂SiO₄ at 2.3 K, D20

The same staged fit as the Python and Command line tutorials, in the app. Its structure and experiment come from EasyDiffraction's collection with **Load ▾ From web…**, and each stage frees its parameters in the **Parameters** table on **Analysis** before the fit.

## Create a project

Press **Start** on Home, then **Create a new project**, and give it a name.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/project-created.webp?v=2a87f8882ab6" data-gui-dark="994bb411c36a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create the project"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create the project"><title>Create the project</title><defs><clipPath id="gui-clip-project-created-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/project-created.webp?v=2a87f8882ab6" data-gui-dark="994bb411c36a" width="1480" height="800" clip-path="url(#gui-clip-project-created-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="project-created-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

</div>

## Load the structure

On **Structure**, choose **Load ▾ From web…**, search for each entry by its id and click it:

- `pd-neut-cwl_cosio-d20_2k-cosio`

<div class="gui-viewer" markdown="1">


=== "Search"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/structure-web-0.webp?v=efac1230b392" data-gui-dark="c2015fa2f1d2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Find the structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Find the structure"><title>Find the structure</title><defs><clipPath id="gui-clip-structure-web-0-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/structure-web-0.webp?v=efac1230b392" data-gui-dark="c2015fa2f1d2" width="1480" height="800" clip-path="url(#gui-clip-structure-web-0-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-web-0-overview-1" data-gui-area="main" data-gui-parts="[[532,276,416,35]]" d="M533.000 281.000 Q533.000 277.000 537.000 277.000 L943.000 277.000 Q947.000 277.000 947.000 281.000 L947.000 306.000 Q947.000 310.000 943.000 310.000 L537.000 310.000 Q533.000 310.000 533.000 306.000 Z" /><path class="" data-gui-region="structure-web-0-overview-2" data-gui-area="main" data-gui-parts="[[102,460,1276,78]]" d="M103.000 465.000 Q103.000 461.000 107.000 461.000 L1373.000 461.000 Q1377.000 461.000 1377.000 465.000 L1377.000 533.000 Q1377.000 537.000 1373.000 537.000 L107.000 537.000 Q103.000 537.000 103.000 533.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Loaded"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/structure-loaded-0.webp?v=1b0acc907271" data-gui-dark="0141f0552d0d" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load the structure cosio"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load the structure cosio"><title>Load the structure cosio</title><defs><clipPath id="gui-clip-structure-loaded-0-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/structure-loaded-0.webp?v=1b0acc907271" data-gui-dark="0141f0552d0d" width="1480" height="800" clip-path="url(#gui-clip-structure-loaded-0-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="structure-loaded-0-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 241.000 Q1465.000 245.000 1461.000 245.000 L789.000 245.000 Q785.000 245.000 785.000 241.000 Z" /><path class="" data-gui-region="structure-loaded-0-overview-2" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

</div>

## Load the experiment

On **Experiment**, choose **Load ▾ Full experiment From web…**, search for each entry by its id and click it:

- `pd-neut-cwl_cosio-d20_2k-d20`

<div class="gui-viewer" markdown="1">


=== "Search"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/experiment-web-0.webp?v=da3e4605b5ee" data-gui-dark="3195429ad31b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Find the experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Find the experiment"><title>Find the experiment</title><defs><clipPath id="gui-clip-experiment-web-0-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/experiment-web-0.webp?v=da3e4605b5ee" data-gui-dark="3195429ad31b" width="1480" height="800" clip-path="url(#gui-clip-experiment-web-0-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-web-0-overview-1" data-gui-area="main" data-gui-parts="[[532,252,416,35]]" d="M533.000 257.000 Q533.000 253.000 537.000 253.000 L943.000 253.000 Q947.000 253.000 947.000 257.000 L947.000 282.000 Q947.000 286.000 943.000 286.000 L537.000 286.000 Q533.000 286.000 533.000 282.000 Z" /><path class="" data-gui-region="experiment-web-0-overview-2" data-gui-area="main" data-gui-parts="[[102,485,1276,78]]" d="M103.000 490.000 Q103.000 486.000 107.000 486.000 L1373.000 486.000 Q1377.000 486.000 1377.000 490.000 L1377.000 558.000 Q1377.000 562.000 1373.000 562.000 L107.000 562.000 Q103.000 562.000 103.000 558.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Loaded"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/experiment-loaded-0.webp?v=a129a1d1348d" data-gui-dark="a79845f56a87" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load the experiment d20"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load the experiment d20"><title>Load the experiment d20</title><defs><clipPath id="gui-clip-experiment-loaded-0-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/experiment-loaded-0.webp?v=a129a1d1348d" data-gui-dark="a79845f56a87" width="1480" height="800" clip-path="url(#gui-clip-experiment-loaded-0-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="experiment-loaded-0-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 241.000 Q1465.000 245.000 1461.000 245.000 L789.000 245.000 Q785.000 245.000 785.000 241.000 Z" /><path class="" data-gui-region="experiment-loaded-0-overview-2" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>

## Start with nothing free

Entries loaded from the database can come with parameters already free. On **Analysis**, open the **Free** column header of the **Parameters** table and fix every parameter, so the stages below free one group at a time.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/nothing-free.webp?v=4c14a56e3247" data-gui-dark="09d0dccad09f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Start with every parameter fixed"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Start with every parameter fixed"><title>Start with every parameter fixed</title><defs><clipPath id="gui-clip-nothing-free-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/nothing-free.webp?v=4c14a56e3247" data-gui-dark="09d0dccad09f" width="1480" height="800" clip-path="url(#gui-clip-nothing-free-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="nothing-free-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path class="" data-gui-region="nothing-free-overview-2" data-gui-area="sidebar" data-gui-parts="[[1383,231,78,39]]" d="M1384.000 236.000 Q1384.000 232.000 1388.000 232.000 L1456.000 232.000 Q1460.000 232.000 1460.000 236.000 L1460.000 265.000 Q1460.000 269.000 1456.000 269.000 L1388.000 269.000 Q1384.000 269.000 1384.000 265.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Add the relations

The project ties some parameters together from the start. On **Analysis → Extra**, add the aliases and constraints.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/relations-start.webp?v=f41e54011cdd" data-gui-dark="2ac75ccc2425" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Add the relations"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Add the relations"><title>Add the relations</title><defs><clipPath id="gui-clip-relations-start-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/relations-start.webp?v=f41e54011cdd" data-gui-dark="2ac75ccc2425" width="1480" height="800" clip-path="url(#gui-clip-relations-start-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="relations-start-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,245,710,233]]" d="M771.000 250.000 Q771.000 246.000 775.000 246.000 L1475.000 246.000 Q1479.000 246.000 1479.000 250.000 L1479.000 473.000 Q1479.000 477.000 1475.000 477.000 L775.000 477.000 Q771.000 477.000 771.000 473.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Set the minimizer

On **Analysis → Extra**, set the **Minimizer** as the case's project does: the **Shift/s.u.** stop rule and room for more iterations.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/minimizer.webp?v=644c6182af96" data-gui-dark="f2744f6ecbea" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Set the minimizer as the project does"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Set the minimizer as the project does"><title>Set the minimizer as the project does</title><defs><clipPath id="gui-clip-minimizer-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/minimizer.webp?v=644c6182af96" data-gui-dark="f2744f6ecbea" width="1480" height="800" clip-path="url(#gui-clip-minimizer-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="minimizer-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,329]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 443.000 Q1479.000 447.000 1475.000 447.000 L775.000 447.000 Q771.000 447.000 771.000 443.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Scale, 2θ zero, cell and magnetic moments

The first stage frees the phase scale, the 2θ zero shift, the three cell lengths and the magnetic model: the moment components the magnetic space group allows (Co1 in any direction, Co2 only along b) and the j2 term of the Co²⁺ form factor, which sets how the magnetic intensities fall with angle.

Filter the **Cell** and **Magnetic moments** parameters, one category at a time, using the category filter, click the **Free** column header and choose **Free · all**; then tick **Free** for the **Linked structures** rows the stage names; then tick **Free** for the **Instrument** rows the stage names; then tick **Free** for the **Magnetic form factors** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/stage-1-fit.webp?v=6501f4097fad" data-gui-dark="23149e12e09b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Scale, 2θ zero, cell and magnetic moments"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Scale, 2θ zero, cell and magnetic moments"><title>Fit: Scale, 2θ zero, cell and magnetic moments</title><defs><clipPath id="gui-clip-stage-1-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/stage-1-fit.webp?v=6501f4097fad" data-gui-dark="23149e12e09b" width="1480" height="800" clip-path="url(#gui-clip-stage-1-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-1-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-1-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,317]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 431.000 Q1479.000 435.000 1475.000 435.000 L775.000 435.000 Q771.000 435.000 771.000 431.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Background

The second stage frees the sixteen background points, which follow the level between the peaks.

Filter the **Background** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/stage-2-fit.webp?v=d5ff3070bbbc" data-gui-dark="850e1084d182" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Background"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Background"><title>Fit: Background</title><defs><clipPath id="gui-clip-stage-2-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/stage-2-fit.webp?v=d5ff3070bbbc" data-gui-dark="850e1084d182" width="1480" height="800" clip-path="url(#gui-clip-stage-2-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-2-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-2-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Atomic displacements and positions

The third stage frees the atoms: each site's isotropic displacement (Co2's follows Co1's by the project's constraint) and the coordinates the symmetry leaves free. Co1 sits on a centre of symmetry, so it has none; the other sites lie on the mirror plane, except O3.

Filter the **Atomic displacement** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/stage-3-fit.webp?v=eba03bef0b84" data-gui-dark="8fa600f02379" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Atomic displacements and positions"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Atomic displacements and positions"><title>Fit: Atomic displacements and positions</title><defs><clipPath id="gui-clip-stage-3-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/stage-3-fit.webp?v=eba03bef0b84" data-gui-dark="8fa600f02379" width="1480" height="800" clip-path="url(#gui-clip-stage-3-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-3-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-3-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Peak widths

The fourth stage frees the peak profile: the Gaussian widths U, V and W and the Lorentzian Y.

Tick **Free** for the **Peak broadening** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/stage-4-fit.webp?v=df5d05bd0e40" data-gui-dark="0b49f978dfb5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Peak widths"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Peak widths"><title>Fit: Peak widths</title><defs><clipPath id="gui-clip-stage-4-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/stage-4-fit.webp?v=df5d05bd0e40" data-gui-dark="0b49f978dfb5" width="1480" height="800" clip-path="url(#gui-clip-stage-4-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-4-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-4-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,395]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 509.000 Q1479.000 513.000 1475.000 513.000 L775.000 513.000 Q771.000 513.000 771.000 509.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Peak asymmetry

The last stage frees the asymmetry: the low-angle peaks lean towards low angle. One FCJ term is freed; the other follows it by the project's constraint.

Tick **Free** for the **Peak asymmetry** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/stage-5-fit.webp?v=7519dbe89fba" data-gui-dark="c38d96b55c36" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Peak asymmetry"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Peak asymmetry"><title>Fit: Peak asymmetry</title><defs><clipPath id="gui-clip-stage-5-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/stage-5-fit.webp?v=7519dbe89fba" data-gui-dark="c38d96b55c36" width="1480" height="800" clip-path="url(#gui-clip-stage-5-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-5-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-5-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,239]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 353.000 Q1479.000 357.000 1475.000 357.000 L775.000 357.000 Q771.000 357.000 771.000 353.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Correlations

The **Correlations** view on **Analysis** shows which fitted parameters move together.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/correlations.webp?v=757b559f291a" data-gui-dark="f44694da240a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the correlations"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the correlations"><title>Inspect the correlations</title><defs><clipPath id="gui-clip-correlations-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/correlations.webp?v=757b559f291a" data-gui-dark="f44694da240a" width="1480" height="800" clip-path="url(#gui-clip-correlations-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="correlations-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Report

The **Report** page collects the structure, the experiment and the fit.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/report.webp?v=1aaea7fff250" data-gui-dark="625e1fd53d32" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Review the report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Review the report"><title>Review the report</title><defs><clipPath id="gui-clip-report-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_2k/report.webp?v=1aaea7fff250" data-gui-dark="625e1fd53d32" width="1480" height="800" clip-path="url(#gui-clip-report-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="report-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

</figure>
