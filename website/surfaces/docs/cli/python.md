# Command Line from the Python package

The Python package includes the command-line interface. You do not need to write a Python script or use a notebook.

## Install the package

Follow [Python setup](../python/setup.md) for the package and environment. The same installation provides both `import edi` and `python -m edi`.

## Run a command

Activate the environment containing the package, then check the command:

```console
python -m edi --help
```

Pass a saved project directly:

```console
python -m edi fit path/to/project --output refined-project
```

All arguments after `python -m edi` match the [standalone executable](standalone.md). Use [Run a refinement](fit.md) for the options, or [Run an example](examples.md) to try a complete case.
