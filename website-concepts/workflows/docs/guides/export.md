# Save and share

<p class="ed-doc-lead">Keep the project for reproducibility and the report for communication.</p>

## Save the project

The project keeps its structures, experiments, observations and analysis settings. Use a new location when you want to retain both a starting model and its refined result.

=== "Application"

    Use Save or Save as. On the desktop, choose a local location. In the browser, save the downloaded project archive somewhere you can find it again.

=== "Python"

    ```python
    project.save_as('refined-project')
    ```

=== "Command line"

    Keep the project files and the run's output together. Read the command-line help for the output options supported by your configured edi build.

## Prepare a report

The Report page brings the model, pattern and fit information together. Python can save the same project's HTML report:

```python
project.report.save_html('refinement.html')
```

## Reopen and review

Reopen the saved project when you want to continue. A report is a view of the analysis; the project is the editable record behind it.
