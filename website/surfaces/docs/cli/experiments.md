# :material-microscope: Experiments in a saved project

The saved experiment supplies measured data or a calculation range, instrument settings, peak profile, background, exclusions and links to structures. Commands use these settings when loading the complete project.

## Prepare the experiment

Use the [application experiment controls](../application/experiments.md) or [Python experiment objects](../python/experiments.md) to import observations and configure the experiment, then save the project.

The command line operates on that saved experiment. It does not create an experiment from a raw pattern file or offer a second set of instrument and background options on the fit command.

## Choose the run

- [Calculate](calculate.md) evaluates the model, including experiments with simulation ranges.
- [Refine](fit.md) uses measured observations and the fitting mode saved in the project.

Use `--dry` when you want to calculate or fit without writing project changes. It still executes the calculation or refinement.

The shared [Experiment](../user-guide/analysis-workflow/experiment.md) stage explains the model, and [fitting modes](../user-guide/fitting-modes.md) explains single, joint and scan analyses.
