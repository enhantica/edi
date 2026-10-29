# Diffraction analysis in Python

Use `edi` to bring EasyDiffraction projects into a script or notebook. The library exposes the same project model used by the application and command line.

```python
import edi

project = edi.Project.load('path/to/project')
result = project.analysis.fit()
print(result.rwp, result.reduced_chi_square)
```

## Start with a complete project

Load a project with its structures, experiments and measured data in one call. [Load and fit a project](fit.md) explains the workflow.

## Work alongside your analysis

Inspect the returned values, prepare a report, and save the project. Use Python to connect these steps to the rest of your scientific workflow.

## Setup

The current library is part of the [edi repository](https://github.com/enhantica/edi). Its Python import name is `edi`. For development setup, see the repository's [contributor documentation](https://enhantica.github.io/edi/dev/).

## Learn the common model

[Projects and experiments](../learn/projects.md) explains the shared concepts without requiring you to learn the application first.
