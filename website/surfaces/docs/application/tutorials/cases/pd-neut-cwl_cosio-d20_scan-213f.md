---
template: gui.html
---

# Sequential magnetic fit: Co₂SiO₄, D20 scan from 2.3 K

The same staged fit as the Python and Command line tutorials, in the app. A scan's patterns come with its project, so open it from EasyDiffraction's collection with **Project → Examples**; each stage frees its parameters in the **Parameters** table on **Analysis** before the fit.

## Open the example

Press **Start** on Home, search **Examples** on **Project** for **pd-neut-cwl_cosio-d20_scan-213f** and open it.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/example-open.webp?v=53ca977fd567" data-gui-dark="65c5d25f2774" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Open the example from Examples"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Open the example from Examples"><title>Open the example from Examples</title><defs><clipPath id="gui-clip-example-open-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/example-open.webp?v=53ca977fd567" data-gui-dark="65c5d25f2774" width="1480" height="800" clip-path="url(#gui-clip-example-open-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="example-open-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

## Start with nothing free

Entries loaded from the database can come with parameters already free. On **Analysis**, open the **Free** column header of the **Parameters** table and fix every parameter, so the stages below free one group at a time.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/nothing-free.webp?v=23ca1459a060" data-gui-dark="10ac0e952cbd" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Start with every parameter fixed"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Start with every parameter fixed"><title>Start with every parameter fixed</title><defs><clipPath id="gui-clip-nothing-free-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/nothing-free.webp?v=23ca1459a060" data-gui-dark="10ac0e952cbd" width="1480" height="800" clip-path="url(#gui-clip-nothing-free-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="nothing-free-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path class="" data-gui-region="nothing-free-overview-2" data-gui-area="sidebar" data-gui-parts="[[1383,231,78,39]]" d="M1384.000 236.000 Q1384.000 232.000 1388.000 232.000 L1456.000 232.000 Q1460.000 232.000 1460.000 236.000 L1460.000 265.000 Q1460.000 269.000 1456.000 269.000 L1388.000 269.000 Q1384.000 269.000 1384.000 265.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Fit the template first

On **Analysis → Extra**, set the fitting mode to single, so the stages fit the template pattern alone.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/fitting-mode-single.webp?v=12e684cbf20e" data-gui-dark="c2dea3650d23" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit the template pattern alone first"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit the template pattern alone first"><title>Fit the template pattern alone first</title><defs><clipPath id="gui-clip-fitting-mode-single-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/fitting-mode-single.webp?v=12e684cbf20e" data-gui-dark="c2dea3650d23" width="1480" height="800" clip-path="url(#gui-clip-fitting-mode-single-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="fitting-mode-single-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 275.000 Q1479.000 279.000 1475.000 279.000 L775.000 279.000 Q771.000 279.000 771.000 275.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Set the minimizer

On **Analysis → Extra**, set the **Minimizer** as the case's project does: the **Shift/s.u.** stop rule and room for more iterations.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/minimizer.webp?v=75ae91f3e682" data-gui-dark="1a133ee2fe53" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Set the minimizer as the project does"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Set the minimizer as the project does"><title>Set the minimizer as the project does</title><defs><clipPath id="gui-clip-minimizer-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/minimizer.webp?v=75ae91f3e682" data-gui-dark="1a133ee2fe53" width="1480" height="800" clip-path="url(#gui-clip-minimizer-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="minimizer-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,329]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 443.000 Q1479.000 447.000 1475.000 447.000 L775.000 447.000 Q771.000 447.000 771.000 443.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Scale, 2θ zero and cell

Filter the **Cell** parameters using the category filter, click the **Free** column header and choose **Free · all**; then tick **Free** for the **Linked structures** rows the stage names; then tick **Free** for the **Instrument** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-1-fit.webp?v=0adf6dcec4a7" data-gui-dark="b3e3997aa99d" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Scale, 2θ zero and cell"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Scale, 2θ zero and cell"><title>Fit: Scale, 2θ zero and cell</title><defs><clipPath id="gui-clip-stage-1-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-1-fit.webp?v=0adf6dcec4a7" data-gui-dark="b3e3997aa99d" width="1480" height="800" clip-path="url(#gui-clip-stage-1-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-1-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-1-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Background

The sixteen background points follow the level between the peaks.

Filter the **Background** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-2-fit.webp?v=38d91aaf2cbf" data-gui-dark="65d45e933d3f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Background"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Background"><title>Fit: Background</title><defs><clipPath id="gui-clip-stage-2-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-2-fit.webp?v=38d91aaf2cbf" data-gui-dark="65d45e933d3f" width="1480" height="800" clip-path="url(#gui-clip-stage-2-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-2-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-2-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Peak widths

U, V and W only: across a temperature scan the Lorentzian term and the asymmetry stay at their 2.3 K values, as do the form factor's j2 term.

Tick **Free** for the **Peak broadening** rows the stage names, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-3-fit.webp?v=7b64f4802bfd" data-gui-dark="a33867c5e52d" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Peak widths"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Peak widths"><title>Fit: Peak widths</title><defs><clipPath id="gui-clip-stage-3-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-3-fit.webp?v=7b64f4802bfd" data-gui-dark="a33867c5e52d" width="1480" height="800" clip-path="url(#gui-clip-stage-3-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-3-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-3-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,395]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 509.000 Q1479.000 513.000 1475.000 513.000 L775.000 513.000 Q771.000 513.000 771.000 509.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Atom positions

Filter the **Atomic coordinates** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-4-fit.webp?v=d371659cf655" data-gui-dark="bfc5af102caa" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Atom positions"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Atom positions"><title>Fit: Atom positions</title><defs><clipPath id="gui-clip-stage-4-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-4-fit.webp?v=d371659cf655" data-gui-dark="bfc5af102caa" width="1480" height="800" clip-path="url(#gui-clip-stage-4-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-4-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-4-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Displacements

Co2's displacement follows Co1's by the project's constraint.

Filter the **Atomic displacement** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-5-fit.webp?v=45e6329c0d27" data-gui-dark="81f0a0067c9a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Displacements"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Displacements"><title>Fit: Displacements</title><defs><clipPath id="gui-clip-stage-5-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-5-fit.webp?v=45e6329c0d27" data-gui-dark="81f0a0067c9a" width="1480" height="800" clip-path="url(#gui-clip-stage-5-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-5-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-5-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Magnetic moments

Last, the moments: Co1 in any direction, Co2 along b.

Filter the **Magnetic moments** parameters using the category filter, click the **Free** column header and choose **Free · all**, then press **Fit** in the status bar.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-6-fit.webp?v=b9cb7794b843" data-gui-dark="7de9f11d2214" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit: Magnetic moments"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit: Magnetic moments"><title>Fit: Magnetic moments</title><defs><clipPath id="gui-clip-stage-6-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/stage-6-fit.webp?v=b9cb7794b843" data-gui-dark="7de9f11d2214" width="1480" height="800" clip-path="url(#gui-clip-stage-6-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="stage-6-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path class="" data-gui-region="stage-6-fit-overview-2" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Fit the scan

Back on **Analysis → Extra**, set the fitting mode to sequential and press **Fit**: every pattern is fitted in turn, each from the fit before it.

<div class="gui-viewer" markdown="1">


=== "Mode"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/scan-mode.webp?v=f7dac7a71fa4" data-gui-dark="d1c33281d247" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Back to the sequential mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Back to the sequential mode"><title>Back to the sequential mode</title><defs><clipPath id="gui-clip-scan-mode-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/scan-mode.webp?v=f7dac7a71fa4" data-gui-dark="d1c33281d247" width="1480" height="800" clip-path="url(#gui-clip-scan-mode-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-mode-overview-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 275.000 Q1479.000 279.000 1475.000 279.000 L775.000 279.000 Q771.000 279.000 771.000 275.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Fitted"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/scan-fit.webp?v=8d2c83037dd7" data-gui-dark="62c33291c38c" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fit the scan"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fit the scan"><title>Fit the scan</title><defs><clipPath id="gui-clip-scan-fit-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/scan-fit.webp?v=8d2c83037dd7" data-gui-dark="62c33291c38c" width="1480" height="800" clip-path="url(#gui-clip-scan-fit-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-fit-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>

<!-- scan-example -->
<!-- /scan-example -->

## Choose a dataset

On **Experiment**, use the selector above the pattern or the **Experiments** table to select a measurement. The selector supports searching in a long series.

Before fitting, the pattern uses the template settings. After fitting, selecting a dataset shows its fitted values and updates the relevant structure values too.

<!-- gui-guide:choose-a-dataset -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-experiment-before.webp?v=e90ec972f1e0" data-gui-dark="701f4f472517" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-experiment-before.webp?v=e90ec972f1e0" data-gui-dark="701f4f472517" width="1480" height="800" clip-path="url(#gui-clip-scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#62992;</span>Experiments (213)"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select an experiment or dataset.</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-experiment-before.webp?v=e90ec972f1e0" data-gui-dark="701f4f472517" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Experiments (213)"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Experiments (213)"><title>Experiments (213)</title><defs><clipPath id="gui-clip-scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-group-experiments"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-experiment-before.webp?v=e90ec972f1e0" data-gui-dark="701f4f472517" width="1480" height="800" clip-path="url(#gui-clip-scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-group-experiments)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-experiment-before-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-a-dataset-0-group-experiments-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,562.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 676.500 Q1479.000 680.500 1475.000 680.500 L775.000 680.500 Q771.000 680.500 771.000 676.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Choose the starting-point rule

On **Analysis → Extra**, expand **Fitting mode**. **Sequential** starts each dataset from the preceding result; **Independent** starts each from the same template. **Single** fits only the shown dataset and makes that result the new template.

Check the template before running the full series. See [fitting modes](../../analysis/fitting-mode.md) for the starting-state rules.

<!-- gui-guide:choose-the-starting-point-rule -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose sequential, independent or single-dataset fitting.</p>
<a class="gui-image-link" href="../../../assets/gui/scan/scan-mode.webp?v=0a2bf7bb231f" data-gui-dark="7b8b8ab43e01" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Fitting mode"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Fitting mode"><title>Fitting mode</title><defs><clipPath id="gui-clip-scan-mode-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-the-starting-point-rule-0-group-fitting_mode"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-mode.webp?v=0a2bf7bb231f" data-gui-dark="7b8b8ab43e01" width="1480" height="800" clip-path="url(#gui-clip-scan-mode-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-the-starting-point-rule-0-group-fitting_mode)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-mode-overview-pd-neut-cwl_cosio-d20_scan-213f-choose-the-starting-point-rule-0-group-fitting_mode-1" data-gui-area="sidebar" data-gui-parts="[[770,161,710,119]]" d="M771.000 166.000 Q771.000 162.000 775.000 162.000 L1475.000 162.000 Q1479.000 162.000 1479.000 166.000 L1479.000 275.000 Q1479.000 279.000 1475.000 279.000 L775.000 279.000 Q771.000 279.000 771.000 275.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Inspect the scan declaration

Expand **Sequential fit** and **Scan extraction rules** on the same tab. Inspect the data directory, file pattern, order and rules used to extract values such as temperature from the measurement files. These groups show the saved scan declaration.

<!-- gui-guide:inspect-the-scan-declaration -->
<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61643;</span>Sequential fit"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the scan&#x27;s data directory, file pattern and order</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-declaration.webp?v=b6e97a61dc2a" data-gui-dark="c6f2fa3e7105" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan&#x27;s data directory, file pattern and order"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan&#x27;s data directory, file pattern and order"><title>Inspect the scan&#x27;s data directory, file pattern and order</title><defs><clipPath id="gui-clip-scan-declaration-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-declaration.webp?v=b6e97a61dc2a" data-gui-dark="c6f2fa3e7105" width="1480" height="800" clip-path="url(#gui-clip-scan-declaration-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-declaration-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-0-1" data-gui-area="sidebar" data-gui-parts="[[770,287,710,119]]" d="M771.000 292.000 Q771.000 288.000 775.000 288.000 L1475.000 288.000 Q1479.000 288.000 1479.000 292.000 L1479.000 401.000 Q1479.000 405.000 1475.000 405.000 L775.000 405.000 Q771.000 405.000 771.000 401.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61616;</span>Scan extraction rules"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect values extracted from each dataset</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-extraction.webp?v=ef1dde1d52fd" data-gui-dark="6990d26aee89" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect values extracted from each dataset"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect values extracted from each dataset"><title>Inspect values extracted from each dataset</title><defs><clipPath id="gui-clip-scan-extraction-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-1"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-extraction.webp?v=ef1dde1d52fd" data-gui-dark="6990d26aee89" width="1480" height="800" clip-path="url(#gui-clip-scan-extraction-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-1)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-extraction-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-declaration-1-1" data-gui-area="sidebar" data-gui-parts="[[770,329,710,141]]" d="M771.000 334.000 Q771.000 330.000 775.000 330.000 L1475.000 330.000 Q1479.000 330.000 1479.000 334.000 L1479.000 465.000 Q1479.000 469.000 1475.000 469.000 L775.000 469.000 Q771.000 469.000 771.000 465.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Run, stop and continue

Press **Fit** at the right of the status bar, on any page, and follow the dataset counts beside it. While a run is under way the button reads **Stop**; stopping keeps the completed results. It then reads **Continue**, which resumes from the first unfitted file, or **Refit** after a change to the template, which fits every file again. **Reset**, next to it, clears every dataset's result for another run, and **Undo** restores the preceding results.

**Follow**, also in the status bar, displays the dataset currently being fitted. Selecting another dataset turns it off; select Follow again to follow progress. [Display and updates](../../analysis/parameters-shown.md) controls redraw frequency.

<!-- gui-guide:run-stop-and-continue -->
<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
<a class="gui-image-link" href="../../../assets/gui/scan/scan-progress-controls.webp?v=b5053bce1378" data-gui-dark="0ee9a99f069f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-scan-progress-controls-overview-pd-neut-cwl_cosio-d20_scan-213f-run-stop-and-continue-0-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-progress-controls.webp?v=b5053bce1378" data-gui-dark="0ee9a99f069f" width="1480" height="800" clip-path="url(#gui-clip-scan-progress-controls-overview-pd-neut-cwl_cosio-d20_scan-213f-run-stop-and-continue-0-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-progress-controls-overview-pd-neut-cwl_cosio-d20_scan-213f-run-stop-and-continue-0-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M1.000 763.000 Q1.000 759.000 5.000 759.000 L1475.000 759.000 Q1479.000 759.000 1479.000 763.000 L1479.000 795.000 Q1479.000 799.000 1475.000 799.000 L5.000 799.000 Q1.000 799.000 1.000 795.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

</div>
<!-- /gui-guide -->

## Inspect the scan views

Use **Stacked** to compare the patterns one above another or **Map** to inspect intensity across the series as rows of colour. On Stacked, **Spacing** runs from **Overlay**, every pattern on one baseline, through **Close**, **Medium** and **Wide**, the default, to **Separate**, each pattern in its own band. Its legend, turned on from the toolbar, lists the files; click an entry to hide that pattern. On Map, choose the colour map, **Blue-Red** by default or **Viridis**, **Batlow**, **Inferno**, **Lapaz** or **Greys**, and its **Direction**: **Auto**, **Normal** or **Inverted**. **Subtract background** draws each pattern less the project's background, here and on the pattern chart. **Evolution** plots a fitted parameter with its uncertainty against a selected dataset value or its place in the scan. Select a point to inspect that dataset elsewhere in the app.

**Correlations** shows the selected dataset's last fit. Only the template dataset's correlations are retained when saving and reopening the project. After editing the template, earlier results remain visible but are marked out of date until refitted.

<!-- gui-guide:inspect-the-scan-views -->
<div class="gui-viewer" markdown="1">


=== "Stacked"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the scan in the stacked view</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-analysis-stacked.webp?v=bba9cd8dfc9e" data-gui-dark="71a5420ca65f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan in the stacked view"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan in the stacked view"><title>Inspect the scan in the stacked view</title><defs><clipPath id="gui-clip-scan-analysis-stacked-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-analysis-stacked.webp?v=bba9cd8dfc9e" data-gui-dark="71a5420ca65f" width="1480" height="800" clip-path="url(#gui-clip-scan-analysis-stacked-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-analysis-stacked-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-0-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Map"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the scan in the map view</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-analysis-map.webp?v=f649b540618c" data-gui-dark="0dd8f85f8a48" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the scan in the map view"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the scan in the map view"><title>Inspect the scan in the map view</title><defs><clipPath id="gui-clip-scan-analysis-map-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-1"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-analysis-map.webp?v=f649b540618c" data-gui-dark="0dd8f85f8a48" width="1480" height="800" clip-path="url(#gui-clip-scan-analysis-map-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-1)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-analysis-map-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-1-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Evolution"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect a fitted parameter across the scan</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-evolution.webp?v=153be8b902b2" data-gui-dark="235f15c7f1aa" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect a fitted parameter across the scan"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect a fitted parameter across the scan"><title>Inspect a fitted parameter across the scan</title><defs><clipPath id="gui-clip-scan-evolution-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-2"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-evolution.webp?v=153be8b902b2" data-gui-dark="235f15c7f1aa" width="1480" height="800" clip-path="url(#gui-clip-scan-evolution-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-2)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-evolution-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-2-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Correlations"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect correlations for the selected measurement</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-correlations.webp?v=0ecfe268a616" data-gui-dark="e8defc6c850f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect correlations for the selected measurement"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect correlations for the selected measurement"><title>Inspect correlations for the selected measurement</title><defs><clipPath id="gui-clip-scan-correlations-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-3"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-correlations.webp?v=0ecfe268a616" data-gui-dark="e8defc6c850f" width="1480" height="800" clip-path="url(#gui-clip-scan-correlations-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-3)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-correlations-overview-pd-neut-cwl_cosio-d20_scan-213f-inspect-the-scan-views-3-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->

## Save the scan

Use **Save project as…** to keep the example together with its data and results. The run writes a row per dataset to `analysis/results.csv` as it progresses. Inspect the scan's report on **Report** and choose [which sections to export](../../report/index.md).

<!-- gui-guide:save-the-scan -->
<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the report view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-report-basic.webp?v=d281a7629cd9" data-gui-dark="80f0b5434eb6" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-report-basic.webp?v=d281a7629cd9" data-gui-dark="80f0b5434eb6" width="1480" height="800" clip-path="url(#gui-clip-scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../../../assets/gui/scan/scan-report-basic.webp?v=d281a7629cd9" data-gui-dark="80f0b5434eb6" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/scan/scan-report-basic.webp?v=d281a7629cd9" data-gui-dark="80f0b5434eb6" width="1480" height="800" clip-path="url(#gui-clip-scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="scan-report-basic-overview-pd-neut-cwl_cosio-d20_scan-213f-save-the-scan-0-workflow-report-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M771.000 124.000 Q771.000 120.000 771.000 116.000 L771.000 82.000 Q771.000 78.000 775.000 78.000 L808.516 78.000 Q812.516 78.000 812.516 82.000 L812.516 116.000 Q812.516 120.000 816.516 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 753.000 Q1479.000 757.000 1475.000 757.000 L775.000 757.000 Q771.000 757.000 771.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

</div>
<!-- /gui-guide -->


## Correlations

The **Correlations** view on **Analysis** shows which fitted parameters move together.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/correlations.webp?v=d8b403d00a58" data-gui-dark="88623c861c84" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Inspect the correlations"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Inspect the correlations"><title>Inspect the correlations</title><defs><clipPath id="gui-clip-correlations-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/correlations.webp?v=d8b403d00a58" data-gui-dark="88623c861c84" width="1480" height="800" clip-path="url(#gui-clip-correlations-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="correlations-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

## Report

The **Report** page collects the structure, the experiment and the fit.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/report.webp?v=8fd42e0c2147" data-gui-dark="da2636af4bbc" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Review the report"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Review the report"><title>Review the report</title><defs><clipPath id="gui-clip-report-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../../assets/gui/cases/pd-neut-cwl_cosio-d20_scan-213f/report.webp?v=8fd42e0c2147" data-gui-dark="da2636af4bbc" width="1480" height="800" clip-path="url(#gui-clip-report-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="report-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

</figure>
