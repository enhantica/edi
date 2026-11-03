# Assessing a fit

Judge a fit using the pattern, the residual, the fitted parameters and the agreement factors together. A successful optimisation is the beginning of that assessment.

## Inspect the signal and residual

Compare the measured and calculated intensities over the full range, then inspect individual peaks and regions that disagree.

- Are peak positions aligned?
- Do widths and shapes agree across the range?
- Does the model account for the observed peaks?
- Is the baseline appropriate between and under peaks?
- Does the residual contain a repeated or systematic pattern?

| What you see | Check first | Learn more |
| --- | --- | --- |
| Peaks shifted across the pattern | Cell, wavelength and instrument calibration | [Cell and symmetry](../physics/crystallography.md), [calibration](../physics/calibration.md) |
| Widths or tails disagree | Profile function and its coefficients | [Peak profiles](../physics/profiles.md) |
| Baseline follows the residual | Background model and excluded regions | [Background](../physics/background.md) |
| Extra measured peaks | Missing phases, impurities or measurement artefacts | [Structure model](analysis-workflow/structure.md) |
| Unstable values or large uncertainties | Free parameters, bounds and correlations | [Minimization](../physics/minimization.md) |

Reflection marks show where the structures predict Bragg positions. They help connect a profile disagreement to the contributing phases, but they do not explain every source of intensity in the measurement.

## Read the agreement factors

R<sub>p</sub> and R<sub>wp</sub> summarise the powder-profile mismatch. R<sub>exp</sub> and reduced χ² connect that mismatch with the observation uncertainties and independent parameter count. The [refinement and statistics](../physics/refinement.md) chapter gives their equations and conventions.

!!! note "A small R factor is only part of the assessment"

    There is no universal R-factor threshold that makes every model acceptable. Data range, exclusions, uncertainty estimates, background and the model affect the values. Inspect the curve, residual and physical parameters together.

## Check parameters and correlations

Inspect whether the result makes physical sense. Review free parameters, their uncertainties, correlations and any values that have reached their bounds.

Strong correlations can mean that several parameter combinations explain similar changes in the observations. Treat individual uncertainties and changes with care in that situation. Changing the data range or constraints changes the question the fit answers.

## Distinguish termination from correctness

Read how the minimizer ended. Reaching an iteration limit is different from satisfying its convergence condition. A converged fit may still describe an unsuitable structure or an instrument setting incorrectly.

Keep the starting model and minimizer conditions with the result so another person can repeat the same optimisation.

## Compare results fairly

Fitting measured data tests how well the chosen model describes that measurement. Comparing a calculation with an independent reference program checks the implementation for that model and case. Both are useful; neither replaces inspection of the physical result.

A meaningful comparison between programs needs matching observations, structures, background, profile, excluded regions, free parameters and starting conditions.

The current [edi comparison tables](https://github.com/enhantica/edi/blob/main/docs/user/guides/fit-quality.md) recompute profile factors from saved observed and calculated curves on a common set of points. They also identify cases where the programs express different models. Those cases need their stated qualification rather than an unlabelled numerical ranking.

Single-crystal examples fit reflection observations rather than a powder profile. Read their example-specific references instead of applying powder-profile factors without checking the observation model.

## Keep an account of the analysis

Save both the project and an appropriate [report](analysis-workflow/report.md). Include enough information to identify the measured data, structure model, fitting mode, free set, excluded regions, software version and minimizer conditions.

For a scan, inspect failed datasets and out-of-date results before interpreting parameter evolution. See [fitting modes](fitting-modes.md).
