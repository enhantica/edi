# :fa5-archive: Files and output

The same complete project is used by the application, Python and Command Line. Commands make their output destination explicit so you can retain an initial model and its result separately.

## Accepted project inputs

`fit` and `calc` accept:

=== "Standalone executable"

    ```console
    edi fit path/to/project
    edi fit path/to/project/project.edi
    edi fit project.zip --output fitted-project
    ```

=== "Python package"

    ```console
    python -m edi fit path/to/project
    python -m edi fit path/to/project/project.edi
    python -m edi fit project.zip --output fitted-project
    ```

A folder holds `project.edi`, `structures/`, `experiments/`, `analysis/` and `reports/`. Its entry file opens that complete folder. A zip packages the project files together.

`structures/` and `experiments/` can hold CIF files as well as `.edi` ones. When both `lbco.edi` and `lbco.cif` are there, the `.edi` file is read and the `.cif` one is named in a warning on stderr. Items a CIF gives that EasyDiffraction does not read are reported the same way. Writing results back saves every member as `.edi`. See [CIF files](../user-guide/data-formats.md#cif-files).

## Where results are written

| Input and options | `fit` / `calc` behavior |
| --- | --- |
| Folder or `project.edi`, no output flag | Writes a successful result back to that folder. |
| `--output DIR` | Works from an output folder and keeps its results there. |
| `--dry` | Runs the computation without writing project changes. |
| Zip, no `--output` | Keeps the archive unchanged; warns that results are not written back. |
| Zip with `--output DIR` | Keeps the input archive unchanged and retains results in the folder. |

`--dry` takes precedence over writing an output folder. For scans it also prevents retaining progress files.

The zip rule differs from Python: `Project.save()` can rewrite an archive opened in Python, whereas these two commands do not overwrite their input archive.

## Export a project archive

```console
python -m edi export path/to/project --output shared-project.zip
```

The short spelling is `-o`. Export packages the project folder as last saved; it is not a fit or a substitute for saving in-memory Python edits. The archive can be opened by another edi interface.

## Keep logs separate from project output

=== "Standalone executable"

    ```console
    edi fit path/to/project --report machine > fit.txt 2> fit-errors.txt
    ```

=== "Python package"

    ```console
    python -m edi fit path/to/project --report machine > fit.txt 2> fit-errors.txt
    ```

The report channel goes to stdout. Warnings and errors go to stderr. Redirecting text output does not change where the project itself is saved.

## Output precision

Saving rounds values to the persisted precision, then recalculates the model from the saved values. Compare a reopened project with that saved model, rather than assuming every in-memory floating-point digit is written unchanged.
