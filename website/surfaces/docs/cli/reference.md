---
icon: fa5/book-open
---

# Command reference

The standalone executable supports `fit`. The Python CLI supports `fit`, `calc`, `report`, `export`, `undo`, and `collection`. Use your installed version's help to see its options.

=== "Standalone executable"

    ```console
    edi --help
    edi fit --help
    ```

=== "Python package"

    ```console
    python -m edi --help
    python -m edi fit --help
    ```

## Fit

The standalone executable accepts:

```text
edi fit PROJECT [--dry | --output DIRECTORY]
    [--verbosity off|compact|full] [--report human|machine]
```

The Python CLI accepts:

```text
python -m edi fit PROJECT [--output DIR] [--dry]
    [--verbosity off|compact|full] [--report human|machine] [--stream]
```

Default output is the human report at compact verbosity. A successful fit normally saves its folder. `--dry` executes without writing; a zip requires `--output DIR` to retain results. [Full guide](fit.md).

## Calculate

```text
python -m edi calc PROJECT [--output DIR] [--dry]
    [--verbosity off|compact|full] [--report machine|human]
```

Default output is the machine report at compact verbosity. The project supplies its grid and model. [Full guide](calculate.md).

## Report

```text
python -m edi report PROJECT [--check] [--output PATH]
    [--offline|--online] [--x-axis native|d_spacing]
    [--correlation-threshold X] [--correlation-experiment NAME]
    [--exclude KEY ...|--include-all] [--colour-scheme NAME]
```

`--check` checks saved-report freshness without writing. `--output PATH` writes an HTML document instead of updating the saved-report list. [Full guide](reports.md).

## Export

```text
python -m edi export PROJECT --output FILE.zip
```

`-o` is the short output spelling. This packages the project folder as last saved. [Files and output](files.md).

## Undo the last saved fit

```console
python -m edi undo path/to/project --dry
python -m edi undo path/to/project --report human
```

The first command previews what would be restored. The second restores the persisted pre-fit state and saves it back when a snapshot exists. `undo --dry` is a preview, unlike `fit --dry` and `calc --dry`, which run their computations.

Undo supports `--verbosity off|compact|full` and `--report machine|human`; it defaults to a compact machine report. If no fit state is recorded, it reports that there is nothing to undo.

## Output and exit status

For fit, calc and undo, the selected report is stdout, while warnings and errors are stderr. A failed run exits nonzero. A clean cancellation in the Python CLI uses status `130`. Report freshness checking uses status `1` when a listed saved report is not current.
