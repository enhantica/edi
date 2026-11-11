---
icon: fa5/download
---

# Set up Python

Install the `easydiffraction` distribution and import it as `edi`. The same
installation works in scripts, notebooks, and with `python -m edi`.

## Install

Use CPython 3.12 or newer on macOS with Apple Silicon or Linux x86-64; Windows follows in a later
release. The package comes from the [v2026.11.10 release](https://github.com/enhantica/edi/releases/tag/v2026.11.10)
on GitHub; its dependencies come from PyPI.

=== "Pixi"

    Create a project and install Python:

    ```console
    pixi init edi-python
    cd edi-python
    pixi add "python>=3.12"
    ```

    In `pixi.toml`, add the EasyDiffraction package index:

    ```toml
    [pypi-options]
    extra-index-urls = ["https://download.easydiffraction.org/pypi/simple/"]
    ```

    Then add the package and check it:

    ```console
    pixi add --pypi "easydiffraction==2026.11.10"
    pixi run python -c "import easydiffraction as edi; print(edi.Project)"
    pixi run python -m edi --help
    ```

    To upgrade, run the same `pixi add` with the new release's version.

=== "Python + pip"

    Create a virtual environment:

    ```console
    python -m venv .venv
    ```

    Activate it with `source .venv/bin/activate` on macOS or Linux, or
    `.\.venv\Scripts\Activate.ps1` in Windows PowerShell. Then install and check:

    ```console
    python -m pip install "easydiffraction==2026.11.10" --extra-index-url https://download.easydiffraction.org/pypi/simple/
    python -c "import easydiffraction as edi; print(edi.Project)"
    python -m edi --help
    ```

    To upgrade, run the install command again with the new release's version.


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

[Run an example](tutorials/index.md){ .md-button }
