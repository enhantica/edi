# Command line

<p class="ed-doc-lead">Run the analysis a project declares, with commands suitable for repeatable workflows.</p>

## Fit without saving

```bash
python -m edi fit path/to/project --dry
```

This runs the refinement while leaving the project's files unchanged. Minimizer conditions and the fitting mode belong to the project.

## Calculate

```bash
python -m edi calc path/to/project
```

## Fit

```bash
python -m edi fit path/to/project
python -m edi fit path/to/project --verbosity full
python -m edi fit path/to/project --report machine
```

`--verbosity` selects the amount of detail: `off`, `compact`, or `full`. `--report` selects readable output or a machine-oriented record.

## Use an example

In a configured edi checkout:

```bash
python -m edi fit docs/user/cli/pd-neut-cwl_lbco-hrpt/project
```

The same project can be opened in the application or loaded by [Python](python.md).
