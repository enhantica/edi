# :fa5-clipboard-list: Reports from Python

The project's report brings together structures, experiments, calculated patterns and fit information. The application, Python and Command Line use the same report model and saved settings.

The shared [Report](../user-guide/analysis-workflow/report.md) chapter explains the scientific model; the steps below describe this interface.

## Save interactive HTML

```python
html_path = project.report.save_html('refinement.html', offline=True)
print(html_path)
```

`offline=True` embeds the chart libraries, so the report does not need to fetch them when opened. With online libraries, a smaller report loads those libraries from the web. Charts remain interactive in HTML.

## Display in a notebook

```python
project.report
```

The report's notebook representation shows the document. To obtain its HTML text explicitly:

```python
html = project.report.as_html(offline=True)
```

## Choose contents for one call

```python
project.report.save_html(
    'refinement.html',
    offline=True,
    x_axis='d_spacing',
    excluded=['data'],
)
```

`native` and `d_spacing` select the pattern axis. Optional exclusions use `charts`, `correlations`, `reflections`, `data` and `evolution`. Keyword overrides affect that call; they do not overwrite the project's saved settings.

## Save the selected report formats

```python
written = project.report.save()
states = project.report.check()
print(written)
print(states)
```

`save()` writes the formats selected by the project except PDF, which is written by the application. `check()` returns saved report names with `current`, `out of date` or `missing` states.

Saving a project is separate from saving a report. A later model or report-settings change can make an existing report out of date.

## Supported outputs

HTML is available from Python, including self-contained offline HTML. PDF is written by the application.

```python
cif_path = project.report.save_cif()
```

`save_cif()` writes the CIF report, by default to `reports/<name>.cif` in the project folder. It holds the fit result, then one data block for each structure and each experiment. Every item is written under its official CIF name, or an `_edi_` name where CIF has none, with its standard uncertainty.

Keep the complete Edi project as the editable analysis record.
