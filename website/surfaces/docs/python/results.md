# :material-calculator: Read the result

Inspect the pattern, parameter values and uncertainties together. Agreement factors summarize a fit; they do not replace a scientific assessment of the model.

## Summary and status

For a single or joint powder refinement:

```python
result = project.analysis.fit()

print(result.status.name)
print(result.iterations)
print(result.rwp)
print(result.reduced_chi_square)
```

Check the status before interpreting a result as converged. Rwp and reduced χ² depend on the data, uncertainties, fitted range and free parameters. See [fit quality](../user-guide/fit-quality.md) for the shared interpretation.

## Values and uncertainties

The single/joint fit result exposes labelled parameter values and their uncertainties:

```python
for label, value in result.values.items():
    uncertainty = result.uncertainty.get(label)
    print(label, value, uncertainty)
```

An absent uncertainty is kept as `None` in this example; it is not replaced with zero. A small numerical uncertainty should still be considered alongside the model's assumptions and parameter correlations.

## Several banks

```python
for bank in result.banks:
    print(bank.name, bank.rwp)
```

Per-bank information helps identify a mismatch hidden by a combined summary.

## Scan results

Sequential and independent modes produce one record per measured file and keep scan progress under `analysis/`. Use the scan's result table and the report's evolution view to follow changing parameters. The single/joint snippets above are not a complete scan-result reference.

## Save evidence with the model

Prepare an [interactive report](reports.md) for inspection and save the project when you want the refined values to persist. Reopening the project provides the editable model behind the report.
