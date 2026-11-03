# :material-calculator: Analysis

Analysis evaluates the combined structure and experiment model. A calculation predicts its signal at the current values. Refinement changes selected independent parameters to improve agreement with measured observations.

## Calculate the starting model

Inspect the initial prediction before fitting. Check peak positions, widths, relative intensities and background against the measurement. A forward calculation can also explore a simulation with no observed data.

EasyDiffraction uses the crysta diffraction engine. The [Physics](../../physics/index.md) section explains the models and conventions behind its calculations.

## Select the independent parameters

Choose which [parameters](../parameters.md) may vary and which stay fixed. Respect symmetry and declared constraints. The fit begins from the current parameter values, so retain the starting state when comparing different refinements.

Refine a set that the observations can constrain. Strongly correlated quantities can trade off against each other, improving an agreement factor while leaving the scientific interpretation uncertain.

## Choose how observations are combined

A [fitting mode](../fitting-modes.md) determines whether you fit one experiment, several experiments jointly, or a scan sequentially or independently. The mode and its inputs are saved with the project.

For a joint fit, inspect both shared and experiment-specific parameters and review every experiment's pattern. For a scan, retain the template, file order and starting-state policy.

## Retain minimizer conditions

The project records the descent strategy, convergence tolerance and iteration budget. These conditions govern how a run proceeds and when it stops; they are separate from the scientific model and its free-parameter choices.

The current project format declares them in the `_minimizer` category of `analysis/analysis.edi`. Use the current interface instructions for access.

## Assess the outcome

Read the termination state, then examine the observed and calculated signals, residual, fitted values, uncertainties and correlations. A converged fit can still describe an unsuitable model. Use [fit quality](../fit-quality.md) for the scientific assessment.

For a scan, inspect individual failed or out-of-date results before interpreting a parameter trend. Keep the model and conditions associated with each result.

## Run the analysis

- [Application: free-parameter controls and refinement](../../application/refine.md), [mode selection](../../application/fitting-modes.md) and [scan controls](../../application/scans.md).
- [Python: calculation](../../python/calculate.md), [refinement](../../python/fit.md) and [result objects](../../python/results.md).
- [Command Line: calculation](../../cli/calculate.md) and [refinement commands](../../cli/fit.md).
