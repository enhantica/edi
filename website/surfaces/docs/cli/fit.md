# :material-calculator: Run a refinement

The command line loads a complete project and runs the analysis its settings declare. Use it for a single pattern, joint experiments, or a scan.

## Run the project

=== "Standalone executable"

    ```console
    edi fit path/to/project
    ```

=== "Python package"

    ```console
    python -m edi fit path/to/project
    ```

For a folder or its `project.edi`, this command refines **and saves** the project back to that folder when the run succeeds. Keep the initial model separately when you want to compare it with the result.

## Choose the output

=== "Standalone executable"

    ```console
    edi fit path/to/project --output refined-project
    edi fit path/to/project --dry
    ```

=== "Python package"

    ```console
    python -m edi fit path/to/project --output refined-project
    python -m edi fit path/to/project --dry
    ```

`--output DIR` keeps the result in another folder. `--dry` still performs the refinement; it leaves the input project's files unchanged and keeps no scan progress. When `--dry` is set, it also prevents output writes requested with `--output`.

For an archive:

=== "Standalone executable"

    ```console
    edi fit project.zip --output refined-project
    ```

=== "Python package"

    ```console
    python -m edi fit project.zip --output refined-project
    ```

Without an output folder, `fit` leaves the input archive unchanged and warns that the results are not written back. See [files and output](files.md).

## Inspect more detail

=== "Standalone executable"

    ```console
    edi fit path/to/project --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit path/to/project --verbosity full
    ```

Full output includes per-bank agreement factors and the refined parameter table.

## Follow progress

The human channel reports progress during a single fit. A scan reports progress per measured file; full verbosity adds its iteration detail. To request live progress records on the machine channel for a single or joint fit:

=== "Standalone executable"

    ```console
    edi fit path/to/project --report machine --stream
    ```

=== "Python package"

    ```console
    python -m edi fit path/to/project --report machine --stream
    ```

Machine streaming is not emitted for scans, whose independent per-file iterations are a different progression.

## Read machine output

=== "Standalone executable"

    ```console
    edi fit path/to/project --report machine
    ```

=== "Python package"

    ```console
    python -m edi fit path/to/project --report machine
    ```

The machine report uses a versioned `key=value` record suitable for comparing runs.

The chosen report goes to standard output; warnings and errors go to standard error. Preserve both when you need a record of an unattended run.

## Fitting mode and minimizer

The project declares `single`, `joint`, `sequential` or `independent` mode. Its `_minimizer` settings choose the descent strategy, tolerance and iteration budget. They are project data, not extra fit flags. See [fitting modes](../user-guide/fitting-modes.md).

## Stop and resume

Ctrl+C requests a clean cancellation. The command exits with status `130`. A cancelled single or joint fit leaves the project unchanged; a scan retains completed file results so running the same command can resume. A dry run retains no scan progress. A second Ctrl+C terminates immediately.

## Prepare a report

=== "Standalone executable"

    ```console
    edi report path/to/project
    edi report path/to/project --check
    ```

=== "Python package"

    ```console
    python -m edi report path/to/project
    python -m edi report path/to/project --check
    ```

The first command writes the selected report formats except PDF. The second checks whether saved reports are current without writing them.

## Continue visually

Open the saved project in [the application](../application/index.md). Its structures and experiments are the same ones the command line reads.
