---
icon: fa5/download
---

# Set up Python

Install the `easydiffraction` distribution and import it as `edi`. The same
installation works in scripts, notebooks, and with `python -m edi`.

## Install a preview

The [preview package index](https://enhantica.github.io/edi/pypi/simple/easydiffraction/) lists the
published wheels. Choose a version listed there and replace `VERSION` below.
Use CPython 3.12 or newer on macOS with Apple Silicon, Windows x86-64, or
Linux x86-64. The wheels are attached to the matching GitHub release.

=== "Pixi"

    Create a project and install Python:

    ```console
    pixi init edi-python
    cd edi-python
    pixi add "python>=3.12"
    ```

    In `pixi.toml`, add the preview index and the version you want:

    ```toml
    [pypi-options]
    index-url = "https://enhantica.github.io/edi/pypi/simple/"

    [pypi-dependencies]
    easydiffraction = "==VERSION"
    ```

    ```console
    pixi install
    pixi run python -c "import edi; print(edi.Project)"
    pixi run python -m edi --help
    ```

    To upgrade, update the version in `pixi.toml` and run `pixi install` again.

=== "Python + pip"

    Create a virtual environment:

    ```console
    python -m venv .venv
    ```

    Activate it with `source .venv/bin/activate` on macOS or Linux, or
    `.\.venv\Scripts\Activate.ps1` in Windows PowerShell. Then install and verify:

    ```console
    python -m pip install --isolated --no-deps --force-reinstall --index-url https://enhantica.github.io/edi/pypi/simple/ "easydiffraction==VERSION"
    python -m pip install "easydiffraction==VERSION"
    python -c "import edi; print(edi.Project)"
    python -m edi --help
    ```

    The first command takes `easydiffraction` only from the preview index, so a
    package of the same name on PyPI is never installed instead. The second adds
    its dependencies from PyPI. To upgrade, run both with the new version.

## From source

For development, use a [configured source checkout](https://enhantica.github.io/edi/dev/):

```console
pixi run core-build
pixi run python -c "import edi; print(edi.Project)"
```

## In a notebook

Install and launch JupyterLab from the environment where you installed edi.

=== "Pixi"

    ```console
    pixi add jupyterlab
    pixi run jupyter lab
    ```

=== "Python + pip"

    ```console
    python -m pip install jupyterlab
    python -m jupyterlab
    ```

Select the kernel for that environment when you open a notebook.

[Run an example](examples/index.md){ .md-button }
