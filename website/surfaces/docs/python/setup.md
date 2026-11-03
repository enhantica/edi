# Set up Python

Use the same `edi` installation for your scripts, notebooks and `python -m edi` commands.

## Packages

Packages for installation with pip and Pixi are being prepared. The package names, channels and installation commands will be added here with the releases.

## From source

Until packages are published, use a [configured source checkout](https://enhantica.github.io/edi/dev/). Build the Python extension in that environment:

```console
pixi run core-build
pixi run python -c "import edi; print(edi.Project)"
```

## In a notebook

!!! tip "Use the matching notebook kernel"

    Select a kernel from the environment containing `edi`. A notebook and a terminal should import the same installation.

[Run an example](examples.md){ .md-button }
