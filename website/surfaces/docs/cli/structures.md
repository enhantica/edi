# :material-puzzle: Structures in a saved project

Commands calculate from the structures stored in your project and linked by its experiments. They retain the same unit cell, symmetry, atom sites and parameter choices as the application and Python.

## Prepare the structural model

Use the [application structure controls](../application/structures.md) or [Python structure objects](../python/structures.md) to prepare and inspect the structure, then save the complete project.

The command-line interface does not provide a separate structure editor. Its `fit` and `calc` commands load the model from the project rather than taking cell and atom-site definitions as command options.

## Check a calculation

=== "Standalone executable"

    ```console
    edi calc path/to/project --dry
    ```

=== "Python package"

    ```console
    python -m edi calc path/to/project --dry
    ```

This evaluates the saved model without writing changes. Inspect the output and any errors before starting a refinement. See [calculate a pattern](calculate.md) for output options.

For the common scientific model, read [Structure](../user-guide/analysis-workflow/structure.md). Continue with [Experiments](experiments.md).
