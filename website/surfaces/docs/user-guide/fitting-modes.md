# Fitting modes

Choose a fitting mode according to how your observations should share a model. The mode is part of the project, so the app, Python and Command Line can run the same declared analysis.

## The available modes

| Mode | Use it for | How the analysis runs |
| --- | --- | --- |
| `single` | One experiment or the shown dataset of a scan | Fits that experiment's observations |
| `joint` | Several experiments describing a connected model | Fits their observations together |
| `sequential` | A scan whose neighbouring datasets should carry a starting model forward | Fits datasets in order, seeding each from the preceding result |
| `independent` | A scan whose datasets should share the same starting point | Fits every dataset from the template's starting values |

A calculation without observations is a different action: it evaluates the model over a declared range and does not optimise against measured data.

## A single fit

Start with a single fit when learning an example or checking one measured pattern. Inspect the initial calculation, choose free parameters, then fit and review the [residual and agreement factors](fit-quality.md).

When working with a scan, a single fit on the shown dataset can establish the template dataset. That template supplies the structure and experiment settings used by the scan.

## A joint fit

A joint fit brings several experiments into one optimisation. The experiments may contain complementary information about the same structural model, with their own measurement and instrument settings.

Check which parameters are shared and which belong to individual experiments. A visually good result in one experiment can hide poor agreement in another, so inspect each experiment's pattern as well as the combined result.

## Sequential and independent scans

A scan is a series of measured datasets, often recorded while temperature or another condition changes. It uses a template experiment and a declared set of files.

In **sequential** mode, each result becomes the starting model for the next dataset. This is useful when the sample evolves gradually, but an unsuitable fit can influence the next starting point.

In **independent** mode, every dataset starts from the same template values. This makes the starting conditions consistent across the scan, while each dataset still needs an adequate initial model.

Both modes fit files serially. Their distinction is the starting state, rather than parallel execution.

## Review a scan

Inspect convergence and failures for individual datasets, then compare fitted patterns and parameter evolution. A smooth trend alone does not prove that every dataset was fitted adequately.

Keep completed results tied to the template and conditions that produced them. Changes to a template can make earlier results out of date. Scan output and resume behaviour depend on how the run is invoked, so use the interface instructions when continuing or cancelling a run.

## Apply the mode in your interface

- [Application: mode selector](../application/fitting-modes.md) and [scan controls](../application/scans.md).
- [Python: mode dispatch and callbacks](../python/fit.md).
- [Command Line: saved mode, progress and output behaviour](../cli/fit.md).

Keep the mode, free-parameter choices and minimizer conditions with the saved project when sharing a result.
