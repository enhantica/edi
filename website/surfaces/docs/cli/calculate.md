# :material-calculator: Calculate a project

`calc` predicts the data from the current model. It does not optimize parameters, and it can run a complete simulation project without measured observations.

## Run a calculation

=== "Standalone executable"

    ```console
    edi calc path/to/project
    ```

=== "Python package"

    ```console
    python -m edi calc path/to/project
    ```

The project's structures, experiments, data grids and calculation settings supply the inputs. For powder data, the command writes calculated series into the experiment files, replacing the previous generated calculated block while preserving the measured columns. Reflection data is saved through the corresponding project model.

## Calculate without writing

=== "Standalone executable"

    ```console
    edi calc path/to/project --dry
    ```

=== "Python package"

    ```console
    python -m edi calc path/to/project --dry
    ```

The calculation still runs and reports its result. The project's files stay unchanged. This is useful when inspecting a saved model without replacing its calculated series.

## Keep a separate result

=== "Standalone executable"

    ```console
    edi calc path/to/project --output calculated-project
    edi calc project.zip --output calculated-project
    ```

=== "Python package"

    ```console
    python -m edi calc path/to/project --output calculated-project
    python -m edi calc project.zip --output calculated-project
    ```

A zip input is never rewritten by the calculation command. Without `--output`, it runs without retaining its changes and warns accordingly. [Files and output](files.md) describes the input forms.

## Select the report channel

Unlike `fit`, `calc` defaults to machine output. Ask for a readable summary with:

=== "Standalone executable"

    ```console
    edi calc path/to/project --report human --dry
    ```

=== "Python package"

    ```console
    python -m edi calc path/to/project --report human --dry
    ```

`--verbosity off` suppresses the report. For calculation, `compact` and `full` carry the same detail because there are no refinement iterations or fitted-parameter table.

## Prepare a document

After keeping the calculated project, use [the report command](reports.md) to save an HTML report. Calculating a project and rendering its report are separate actions.
