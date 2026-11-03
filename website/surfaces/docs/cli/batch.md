# :material-calculator: Repeat an analysis

Use ordinary shell or workflow tools to run several complete projects. There is no additional batch command to learn: each project declares the model and analysis it needs.

## Separate output folders

For a shell with the input folders `projects/sample-a` and `projects/sample-b`:

=== "Standalone executable"

    ```bash
    set -e
    mkdir -p logs runs

    for project in projects/sample-a projects/sample-b; do
        case_name=$(basename "$project")
        edi fit "$project" \
            --output "runs/$case_name" \
            --report machine \
            > "logs/$case_name.txt" \
            2> "logs/$case_name-errors.txt"
    done
    ```

=== "Python package"

    ```bash
    set -e
    mkdir -p logs runs

    for project in projects/sample-a projects/sample-b; do
        case_name=$(basename "$project")
        python -m edi fit "$project" \
            --output "runs/$case_name" \
            --report machine \
            > "logs/$case_name.txt" \
            2> "logs/$case_name-errors.txt"
    done
    ```

This loop is a shell example, not a new edi API. It stops on a failed command and keeps reports separate from project output. Give each input a distinct output name and retain its original files.

## Run without keeping model changes

Add `--dry` to execute refinements without writing project changes. A dry run does real numerical work. In scan mode it keeps no resumable progress, so use an ordinary output folder for a scan you intend to continue.

## A scan is a project workflow

If the measured files belong to one sequential or independent scan, declare that scan in the project instead of treating every pattern as an unrelated batch project.

- **Sequential:** the previous fit supplies the next pattern's initial parameters.
- **Independent:** every pattern starts from the same initial parameters.

Both process files serially. See [shared fitting modes](../user-guide/fitting-modes.md).

## Keep failure information

Check the process exit status and retain stderr. A machine report is a versioned record; scripts that parse it should handle its schema and failed-run records explicitly. Do not treat the existence of a redirected output file as proof of a successful fit.

## Save reports after fitting

=== "Standalone executable"

    ```console
    edi report runs/sample-a
    edi report runs/sample-a --check
    ```

=== "Python package"

    ```console
    python -m edi report runs/sample-a
    python -m edi report runs/sample-a --check
    ```

Use the [report guide](reports.md) to choose contents and check freshness.
