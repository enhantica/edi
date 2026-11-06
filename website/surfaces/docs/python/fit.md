# :fa5-calculator: Load and fit a project

Start from a complete project with measured data. It contains the structures, experiments, free parameters and analysis settings that determine the refinement.

## Load

```python
import edi

project = edi.Project.load('path/to/project')
```

The input may be a project folder, its `project.edi`, or a project `.zip`. Invalid or incomplete input raises `edi.IoError` rather than returning a partially loaded project. [Project loading](projects.md) explains what the loader checks.

## Inspect the free parameters

```python
for parameter in project.free_parameters:
    print(parameter.name, parameter.value, parameter.units)
```

The project already declares which parameters may vary. Review that choice before fitting; [structures and parameters](structures.md) shows how a model parameter exposes its value and `free` flag.

## Fit

```python
result = project.analysis.fit()
print(result.rwp)
print(result.reduced_chi_square)
```

`analysis.fit()` dispatches according to the fitting mode saved in the project. The shared [fitting-mode guide](../user-guide/analysis-workflow/analysis.md#fitting-modes) explains the modes and their starting-state policies; the same method runs each declared mode. Scan results have a different shape from single or joint outcomes: use [result handling](results.md).

## Follow progress

For a single or joint fit, an optional callback receives each iteration record:

```python
def show_iteration(record):
    print(record)


result = project.analysis.fit(on_iteration=show_iteration)
```

The facade also supports `on_start`, scan-specific `on_scan_start` and `on_file_complete`, and a `should_cancel` predicate. Scan callbacks are accepted only for a scan-mode project. These hooks report progress; the model and measured data remain in the project.

## Read the result

For a powder single or joint fit, inspect Rwp and reduced χ² alongside the pattern, uncertainties and correlations. [Read the result](results.md) explains the returned values. A finished minimization alone does not establish that the structural model is appropriate.

## Prepare a report

```python
project.report.save_html('result.html')
```

## Save the updated project

```python
project.save_as('refined-project')
```

`save_as()` puts the project in the new folder and makes that its location for later saves. A Python single or joint fit does not automatically save your project. Scan analysis also writes its progress results during the run; retain the input project separately when you need its initial state.

Open the saved result in [the application](../application/index.md) to inspect it visually, or run the project through [<span class="ed-interface-icons" aria-hidden="true">:fa5-terminal:</span> <span class="ed-icon-text">the Command Line</span>](../cli/fit.md){ .ed-interface-link .ed-icon-label }.
