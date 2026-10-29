# Diffraction analysis from the command line

Run a saved EasyDiffraction project from a terminal. The project keeps the structural model and analysis settings together, so a command names the input rather than rebuilding it.

```console
python -m edi fit path/to/project
```

## Refine a project

[Run a refinement](fit.md) covers loading a project, choosing output and preparing a report.

## Keep your analysis reproducible

Store the project alongside your analysis. Its declared fitting mode determines whether the run fits one experiment, several experiments jointly, or a scan.

## Use the same model

The CLI shares [projects and experiments](../learn/projects.md) with Python and the application. Use whichever interface fits the next step in your work.
