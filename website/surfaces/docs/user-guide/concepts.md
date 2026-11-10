---
icon: fa5/lightbulb
---

# From measurement to analysis

EasyDiffraction compares a crystallographic model with diffraction measurements. Understanding where that comparison begins helps you choose suitable inputs and recognise what a fit can establish.

## Acquisition, reduction and analysis

<ol class="ed-workflow-diagram ed-concept-flow" style="--ed-flow-columns:3" markdown="1" aria-label="From detector measurements to analysis">
<li markdown="1">[:fa5-microscope: Acquisition](#acquisition)</li>
<li markdown="1">[:fa5-filter: Reduction](#reduction)</li>
<li markdown="1">[:fa5-calculator: Analysis](#analysis)</li>
</ol>

### :fa5-microscope: Acquisition

Record the detector response while the sample scatters the incident beam. This example uses a two-dimensional detector.

<div class="ed-concept-figures">
<figure><figcaption>Beam, sample and detector: the three cones are the (100) and (001) magnetic and the (221) nuclear reflections of Co₂SiO₄ at λ = 1.87 Å</figcaption><img src="../assets/concepts/data-acquisition_instrument.svg#only-light" alt="A beam from the source passes a slit to a powder sample, which scatters it into Debye–Scherrer cones at the measured 2θ of three Co₂SiO₄ reflections; each cone leaves a ring on a flat area detector" width="800" height="460" loading="lazy"><img src="../assets/concepts/dark/data-acquisition_instrument.svg#only-dark" alt="A beam from the source passes a slit to a powder sample, which scatters it into Debye–Scherrer cones at the measured 2θ of three Co₂SiO₄ reflections; each cone leaves a ring on a flat area detector" width="800" height="460" loading="lazy"></figure>
<figure><figcaption>Raw detector image, computed from the D20 pattern measured at 2.3 K</figcaption><img class="ed-image-full" src="../assets/concepts/data-acquisition_2d-raw-data.webp#only-light" alt="Rings on a flat area detector computed from the Co₂SiO₄ powder pattern measured on D20 at 2.3 K, with the (001) and (100) magnetic and the (221) nuclear rings labelled" width="1000" height="560" loading="lazy"><img class="ed-image-full" src="../assets/concepts/dark/data-acquisition_2d-raw-data.webp#only-dark" alt="Rings on a flat area detector computed from the Co₂SiO₄ powder pattern measured on D20 at 2.3 K, with the (001) and (100) magnetic and the (221) nuclear rings labelled" width="1000" height="560" loading="lazy"></figure>
</div>

### :fa5-filter: Reduction

Apply the relevant corrections and turn detector measurements into observations with uncertainties. For powder diffraction, these are often a one-dimensional intensity profile.

<div class="ed-concept-figures ed-concept-figures--single">
<figure><figcaption>Reduced diffraction pattern of Co₂SiO₄ at 2.3 K</figcaption><img src="../assets/concepts/data-reduction_1d-pattern.png#only-light" alt="The measured neutron powder pattern of Co₂SiO₄ at 2.3 K from D20, intensity against 2θ, as EasyDiffraction draws it" width="892" height="728" loading="lazy"><img src="../assets/concepts/dark/data-reduction_1d-pattern.png#only-dark" alt="The measured neutron powder pattern of Co₂SiO₄ at 2.3 K from D20, intensity against 2θ, as EasyDiffraction draws it" width="892" height="728" loading="lazy"></figure>
</div>

### :fa5-calculator: Analysis

Compare a calculated pattern with the observations, fit the model and inspect the result. **EasyDiffraction focuses on this stage.**

<div class="ed-concept-figures">
<figure><figcaption>Measured, calculated and residual patterns of Co₂SiO₄ at 2.3 K</figcaption><img src="../assets/concepts/data-analysis_refinement.png#only-light" alt="The Co₂SiO₄ pattern at 2.3 K fitted in EasyDiffraction: measured and calculated intensities with the background, Bragg ticks of the nuclear and the magnetic phase, and the residual below" width="895" height="728" loading="lazy"><img src="../assets/concepts/dark/data-analysis_refinement.png#only-dark" alt="The Co₂SiO₄ pattern at 2.3 K fitted in EasyDiffraction: measured and calculated intensities with the background, Bragg ticks of the nuclear and the magnetic phase, and the residual below" width="895" height="728" loading="lazy"></figure>
<figure><figcaption>Magnetic structure model of Co₂SiO₄</figcaption><img src="../assets/concepts/data-analysis_model.png#only-light" alt="The Co₂SiO₄ unit cell in the EasyDiffraction structure view: cobalt, silicon and oxygen atoms with bonds, arrows for the magnetic moments on the cobalt atoms, and the atom legend" width="705" height="496" loading="lazy"><img src="../assets/concepts/dark/data-analysis_model.png#only-dark" alt="The Co₂SiO₄ unit cell in the EasyDiffraction structure view: cobalt, silicon and oxygen atoms with bonds, arrows for the magnetic moments on the cobalt atoms, and the atom legend" width="705" height="496" loading="lazy"></figure>
</div>

??? info "Illustration credits"

    Every figure on this page shows EasyDiffraction's Co₂SiO₄ example: neutron powder data at 2.3 K from D20 at the ILL. The instrument is drawn from that geometry; the raw detector image is computed from the measured pattern; the reduced pattern, the fitted pattern and the structure model are rendered by EasyDiffraction itself.

Keep the reduction history and experimental context with the project: they affect how uncertainties and agreement factors should be interpreted.

## A model of the sample and the experiment

The calculated intensity depends on more than atom positions. EasyDiffraction separates the model into two connected parts:

| Part | Describes | Examples |
| --- | --- | --- |
| [<span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true">:fa5-layer-group:</span><span class="ed-icon-text">Structure</span></span>](analysis-workflow/structure.md) | The crystalline sample | Unit cell, symmetry, atom sites, occupancies, displacement parameters |
| [<span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true">:fa5-microscope:</span><span class="ed-icon-text">Experiment</span></span>](analysis-workflow/experiment.md) | How it is observed | Wavelength or time-of-flight calibration, peak profile, background, scale and excluded regions |

A disagreement between measured and calculated patterns can therefore have several causes. A peak-position error may come from the cell or calibration; a broad mismatch underneath peaks may come from the background; an intensity mismatch can involve the structure as well as experiment settings.

## Calculation and fitting

<ol class="ed-workflow-diagram ed-concept-flow" style="--ed-flow-columns:3" markdown="1" aria-label="Model calculation and comparison">
<li markdown="1">[:fa5-layer-group: Structure + experiment](#a-model-of-the-sample-and-the-experiment)</li>
<li markdown="1">[:fa5-chart-line: Calculated pattern](../physics/rietveld.md#eq-rietveld-pattern)</li>
<li markdown="1">[:fa5-exchange-alt: Compare with observations](#calculation-and-fitting)</li>
</ol>

A calculation predicts the diffraction pattern from the current structure and experiment. It does not need measured intensities. Use it to inspect peak positions and the influence of the model before fitting.

A fit needs observations to compare against. A least-squares fit reduces the weighted difference between observations and calculations: it changes the parameters marked as free, while fixed parameters still contribute to the calculated pattern. The starting model, free-parameter set, constraints, excluded regions and minimizer conditions all influence the result.

Start from a physically meaningful model. Inspect the initial pattern, allow parameters to vary deliberately, and review the result after each meaningful change. Adding more free parameters may reduce a residual without making the model more informative.

## Least squares and Bayesian analysis {#least-squares-and-bayesian-analysis}

Both compare a model with observations, but summarise parameter uncertainty differently.

| Approach | What it reports |
| --- | --- |
| Least squares | A best-fit parameter set and, when the covariance can be estimated, standard uncertainties and correlations |
| Bayesian sampling | A posterior distribution combining a likelihood with prior information, from which credible intervals and correlations can be summarised |

The fitting instructions in this documentation use **least squares**. Its [objective and covariance conventions](../physics/minimization.md) explain the reported uncertainties. Bayesian sampling is a separate workflow; the older library's sampler choices should not be assumed to be available in this application.

## Interpreting the result

Convergence describes how the optimisation ended. It does not by itself establish that the sample model is correct or that all uncertainty sources have been captured.

Inspect the observed and calculated pattern, the residual, parameter uncertainties and correlations, and the physical plausibility of the result. [Fit quality](analysis-workflow/analysis.md#fit-quality) explains these checks in more detail.

## The same ideas in every interface

The app makes these relationships visible. Python lets you express them in a script or notebook. The Command line runs the analysis already declared by a saved project. All use the same [project model](analysis-workflow/project.md).
