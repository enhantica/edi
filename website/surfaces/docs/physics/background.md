---
template: physics.html
---

# Background models and estimation

A background contributes an additive baseline to a powder calculation. It is separate from excluded observations, peak-profile tails and the phase scale.

## Line-segment model {#eq-line-segment-background}

For anchors $(x_k,b_k)$ and $(x_{k+1},b_{k+1})$,

$$b(x)=b_k+(b_{k+1}-b_k)\frac{x-x_k}{x_{k+1}-x_k}.$$

Outside the anchor range the endpoint intensity is retained. Anchor positions are fixed nodes; the selected intensities can be fit parameters. This is not a linearly extrapolated edge.

## Polynomial model {#eq-polynomial-background}

$$b(x)=\sum_m c_m u^m,\qquad u=x/x_0-1.$$

`origin` is the nonzero normalisation coordinate $x_0$ in the pattern's axis units. It is not an intensity intercept. The currently admitted polynomial term orders are 0 through 5.

## Chebyshev model {#eq-chebyshev-background}

$$b(x)=\sum_m c_mT_m(u),\qquad u=\frac{2x-x_{\min}-x_{\max}}{x_{\max}-x_{\min}},$$

$$T_0=1,\quad T_1=u,\quad T_{m+1}=2uT_m-T_{m-1}.$$

`x_min` and `x_max` define the normalisation domain. The admitted Chebyshev term orders are 0 through 23. These are true Chebyshev coefficients, not powers of the unnormalised angle or time coordinate. Preserve the origin/domain when moving coefficients between projects.

## Automatic estimation {#background-estimation}

The estimator proposes a baseline and then editable anchors or series coefficients. The method is distinct from the final fitted background type. Supported method selectors are `auto`, `arpls`, `snip` and `fabc`; `auto` resolves to `arpls`.

### arPLS {#eq-arpls}

An iterated penalised smoothing solve uses

$$(W+\lambda D_2^{\mathsf T}D_2)\mathbf z=W\mathbf y,$$

$$w_i=\left[1+\exp\left(\frac{2}{s}[r_i-(2s-m)]\right)\right]^{-1},\qquad\mathbf r=\mathbf y-\mathbf z.$$

$m,s$ describe the negative residual subset; the reweighting suppresses peak contributions. Smoothness controls the penalty rather than a crystallographic parameter.

### SNIP {#eq-snip}

Peak clipping in log-log-square transformed intensity uses

$$v_i=\log[\log(\sqrt{y_i+1}+1)+1],\qquad v_i\leftarrow\min(v_i,(v_{i-w}+v_{i+w})/2).$$

The window and traversal settings determine the sequence of updates; the transform is inverted afterwards. This is an estimation algorithm, not an extra Bragg contribution.

### FABC and anchor reduction {#fabc}

FABC classifies baseline versus peak regions using a wavelet/noise criterion, then smooths through the baseline points. Anchor reduction converts the dense baseline to a smaller line-segment model using a noise-scaled vertical tolerance. `in_peaks` controls whether proposed anchors are moved out of or dropped from peak windows; `use_model` determines whether calculated peaks are subtracted before estimation.

Inspect the estimate. A missing phase or unsuitable calculated pattern can affect a model-assisted baseline proposal. Fitting the proposed background is a separate step.

## Excluded observations {#excluded-regions}

An excluded powder interval removes observations from the fitting objective and agreement-factor sums. It does not add a background component or change the definition of the calculated pattern. Retain excluded ranges with the experiment and justify them physically; masking a mismatch does not improve its model. Single-crystal reflection exclusion is a separate planned capability.

## References

1. Baek, S.-J., Park, A., Ahn, Y.-J. & Choo, J. (2015). *Baseline correction using asymmetrically reweighted penalized least squares smoothing*. **Analyst**, 140, 250–257. [DOI](https://doi.org/10.1039/C4AN01061B). arPLS baseline estimation.
2. Ryan, C. G., Clayton, E., Griffin, W. L., Sie, S. H. & Cousens, D. R. (1988). *SNIP, a statistics-sensitive background treatment for the quantitative analysis of PIXE spectra in geoscience applications*. **Nuclear Instruments and Methods in Physics Research B**, 34, 396–402. [DOI](https://doi.org/10.1016/0168-583X%2888%2990063-8). SNIP peak clipping.
3. Cobas, J. C., Bernstein, M. A., Martín-Pastor, M. & García Tahoces, P. (2006). *A new general-purpose fully automatic baseline-correction procedure for 1D and 2D NMR data*. **Journal of Magnetic Resonance**, 183, 145–151. [DOI](https://doi.org/10.1016/j.jmr.2006.07.013). FABC baseline classification.
