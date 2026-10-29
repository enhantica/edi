# Load a project

<p class="ed-doc-lead">A project brings together the structure, experiments, observed data and analysis settings needed for a calculation or fit.</p>

## Start with a complete project

A project can contain several structures and experiments. Each experiment declares the structures it uses and its own instrument, peak profile, background and exclusions.

## Open your workspace

=== "Application"

    Open a project on the Project page, or choose an example. In the browser, the file chooser and downloads take the place of unrestricted local-folder access.

=== "Python"

    ```python
    import edi

    project = edi.Project.load('path/to/project')
    ```

    A successful load returns a complete project. Invalid or incomplete input raises `edi.IoError`.

=== "Command line"

    ```bash
    python -m edi fit path/to/project --dry
    ```

    This runs the fit without writing changes back to the project.

## Data or simulation

An experiment with observed intensities and their uncertainties can be fitted. A calculation-only experiment declares a range and has no observation. A project can contain both; fitting uses the experiments with measured data.

## Next step

[Inspect the structure →](structure.md)
