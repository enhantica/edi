# Run a refinement

The command line loads a complete project and runs its declared analysis.

## Run the project

```console
python -m edi fit path/to/project
```

## Inspect more detail

```console
python -m edi fit path/to/project --verbosity full
```

Full output includes per-bank agreement factors and the refined parameter table.

## Read machine output

```console
python -m edi fit path/to/project --report machine
```

The machine report uses a versioned `key=value` record suitable for comparing runs.

## Prepare a report

```console
python -m edi report path/to/project
python -m edi report path/to/project --check
```

The first command writes the selected report formats except PDF. The second checks whether saved reports are current without writing them.

## Continue visually

Open the saved project in [the application](../application/index.md). Its structures and experiments are the same ones the command line reads.
