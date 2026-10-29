# Python and command line

<p class="ed-doc-lead">Use edi in a script, a notebook, or a repeatable terminal run.</p>

## Current setup

These examples use a configured edi source checkout. A public package-install command will be added when the current edi package is released; the earlier EasyDiffraction package does not represent this API.

The [repository](https://github.com/enhantica/edi) records the current source-build requirements. Once the environment is ready, both interfaces read the same project files.

## Python

```python
import edi

project = edi.Project.load('path/to/project')
result = project.analysis.fit()
print(result.rwp, result.reduced_chi_square)
```

## Command line

```bash
python -m edi fit path/to/project
```

The project's analysis settings choose how the fit runs. Use `--dry` to run the refinement without writing changes back to the project.

## Continue

Read [load a project](../guides/load.md), then [refine a model](../guides/refine.md). For individual calls and options, use [Python](../reference/python.md) and [command line](../reference/cli.md).
