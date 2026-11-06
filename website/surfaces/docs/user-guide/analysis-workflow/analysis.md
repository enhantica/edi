# :fa5-calculator: Analysis

Analysis evaluates the combined structure and experiment model. A calculation predicts its pattern at the current values. Refinement changes selected independent parameters to improve agreement with measured observations.

## Calculate the starting model

Inspect the initial prediction before fitting. Check peak positions, widths, relative intensities and background against the measurement. A forward calculation can also explore a simulation with no observed data.

EasyDiffraction uses the crysta diffraction engine. The [Physics](../../physics/index.md) section explains the models and conventions behind its calculations.

## Select the independent parameters

Choose which [parameters](../parameters.md) may vary and which stay fixed. Respect symmetry and declared constraints. The fit begins from the current parameter values, so retain the starting state when comparing different refinements.

Refine a set that the observations can constrain. Strongly correlated quantities can trade off against each other, improving an agreement factor while leaving the scientific interpretation uncertain.

## How a refinement iterates

A refinement is an iterative loop. A minimizer repeats these steps, adjusting the free parameters each cycle to reduce the weighted difference between the calculated and measured pattern:

<ol class="ed-workflow-diagram ed-concept-flow" style="--ed-flow-columns:3" markdown="1" aria-label="Refinement iteration loop">
<li markdown="1">[:fa5-calculator: Set parameter values](#select-the-independent-parameters)</li>
<li markdown="1">[:fa5-chart-line: Calculate pattern](../../physics/rietveld.md#eq-rietveld-pattern)</li>
<li markdown="1">[:fa5-exchange-alt: Compare with data](#fit-quality)</li>
</ol>

The loop stops when the change falls below the convergence tolerance, or when the iteration budget is reached. Those limits are minimizer conditions, not part of the scientific model.

## Fitting modes {#fitting-modes}

A fitting mode sets how your observations share a model: fit one experiment, several jointly, or a scan sequentially or independently. The mode is part of the project, so the app, Python and Command Line run the same declared analysis.

| Mode | Use it for | How the analysis runs |
| --- | --- | --- |
| `single` | One experiment or the shown dataset of a scan | Fits that experiment's observations |
| `joint` | Several experiments describing a connected model | Fits their observations together |
| `sequential` | A scan whose neighbouring datasets should carry a starting model forward | Fits datasets in order, seeding each from the preceding result |
| `independent` | A scan whose datasets should share the same starting point | Fits every dataset from the template's starting values |

A calculation without observations is a different action: it evaluates the model over a declared range and does not optimise against measured data.

### Single and joint fits

Start with a single fit when learning an example or checking one measured pattern. Inspect the initial calculation, choose free parameters, then fit and review the [residual and agreement factors](#fit-quality).

A joint fit brings several experiments into one optimisation, with complementary information about the same structural model. Check which parameters are shared and which belong to individual experiments: a good result in one experiment can hide poor agreement in another, so inspect each experiment's pattern as well as the combined result.

### Sequential and independent scans

A scan is a series of measured datasets, often recorded while temperature or another condition changes. It uses a template experiment and a declared set of files. In **sequential** mode, each result becomes the starting model for the next dataset — useful when the sample evolves gradually, though an unsuitable fit can influence the next starting point. In **independent** mode, every dataset starts from the same template values, keeping the starting conditions consistent while each dataset still needs an adequate initial model. Both modes fit files serially; their distinction is the starting state, not parallel execution.

Inspect convergence and failures for individual datasets, then compare fitted patterns and parameter evolution. A smooth trend alone does not prove that every dataset was fitted adequately. Keep completed results tied to the template and conditions that produced them, since changes to a template can make earlier results out of date.

## Retain minimizer conditions

The project records the descent strategy, convergence tolerance and iteration budget. These conditions govern how a run proceeds and when it stops; they are separate from the scientific model and its free-parameter choices.

The current project format declares them in the `_minimizer` category of `analysis/analysis.edi`. Use the current interface instructions for access.

## Assess the fit {#fit-quality}

Judge a fit using the pattern, the residual, the fitted parameters and the agreement factors together. A successful optimisation is the beginning of that assessment, not the end.

### Inspect the pattern and residual

Compare the measured and calculated intensities over the full range, then inspect individual peaks and regions that disagree.

- Are peak positions aligned?
- Do widths and shapes agree across the range?
- Does the model account for the observed peaks?
- Is the baseline appropriate between and under peaks?
- Does the residual contain a repeated or systematic pattern?

| What you see | Check first | Learn more |
| --- | --- | --- |
| Peaks shifted across the pattern | Cell, wavelength and instrument calibration | [Cell and symmetry](../../physics/crystallography.md), [calibration](../../physics/calibration.md) |
| Widths or tails disagree | Profile function and its coefficients | [Peak profiles](../../physics/profiles.md) |
| Baseline follows the residual | Background model and excluded regions | [Background](../../physics/background.md) |
| Extra measured peaks | Missing phases, impurities or measurement artefacts | [Structure model](structure.md) |
| Unstable values or large uncertainties | Free parameters, bounds and correlations | [Minimization](../../physics/minimization.md) |

Reflection marks show where the structures predict Bragg positions. They help connect a profile disagreement to the contributing phases, but they do not explain every source of intensity.

### Read the agreement factors

R<sub>p</sub> and R<sub>wp</sub> summarise the powder-profile mismatch. R<sub>exp</sub> and reduced χ² connect that mismatch with the observation uncertainties and independent parameter count. The [refinement and statistics](../../physics/refinement.md) chapter gives their equations and conventions.

!!! note "A small R factor is only part of the assessment"

    There is no universal R-factor threshold that makes every model acceptable. Data range, exclusions, uncertainty estimates, background and the model affect the values. Inspect the curve, residual and physical parameters together.

### Check parameters and correlations

Inspect whether the result makes physical sense. Review free parameters, their uncertainties, correlations and any values that have reached their bounds. Strong correlations can mean that several parameter combinations explain similar changes in the observations, so treat individual uncertainties with care. Changing the data range or constraints changes the question the fit answers.

### Distinguish termination from correctness

Reaching an iteration limit is different from satisfying a convergence condition. A converged fit may still describe an unsuitable structure or an incorrect instrument setting. Keep the starting model and minimizer conditions with the result so another person can repeat the same optimisation.

### Compare results fairly

Fitting measured data tests how well the chosen model describes that measurement. Comparing a calculation with an independent reference program checks the implementation for that model and case. Both are useful; neither replaces inspection of the physical result. A meaningful comparison between programs needs matching observations, structures, background, profile, excluded regions, free parameters and starting conditions.

Single-crystal examples fit reflection observations rather than a powder profile; read their example-specific references instead of applying powder-profile factors without checking the observation model.

## Run the analysis

- [Application: free-parameter controls and refinement](../../application/refine.md), [mode selection](../../application/fitting-modes.md) and [scan controls](../../application/scans.md).
- [Python: calculation](../../python/calculate.md), [refinement](../../python/fit.md) and [result objects](../../python/results.md).
- [Command Line: calculation](../../cli/calculate.md) and [refinement commands](../../cli/fit.md).
