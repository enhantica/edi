# Load and fit a project

Start from a saved project directory. It contains the structural model, experiments and the settings that determine the analysis.

## Load

```python
import edi

project = edi.Project.load('path/to/project')
```

The loader checks the project as a whole. Invalid or incomplete input raises an error rather than returning a partially loaded project.

## Fit

```python
result = project.analysis.fit()
print(result.rwp)
print(result.reduced_chi_square)
```

The analysis reads the fitting mode declared by the project, including single, joint and scan workflows.

## Prepare a report

```python
project.report.save_html('result.html')
```

## Save the updated project

```python
project.save_as('refined-project')
```

Open the saved result in [the application](../application/index.md) to inspect it visually, or run the project through [the CLI](../cli/fit.md).
