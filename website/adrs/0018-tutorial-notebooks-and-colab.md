# Tutorial notebook generation and Colab links

## Status

Accepted, 7 Nov 2026.

## Context

The Python examples already paired `.py` tutorial sources with committed
`.ipynb` files. Downloadable bundles used those notebooks with their matching
projects. Colab needs a notebook available from GitHub and a setup cell that
installs the package and provides the project files.

## Decision

Edit `.py` sources and generate their `.ipynb` counterparts with
`website/prepare_notebooks.py`. Commit the generated notebooks beside the
sources on the same branch. Generation clears outputs and execution counts
and numbers cell IDs from zero. It adds one setup cell with the `hide-in-docs`
tag, following diffraction-lib's notebook preparation convention.

The setup checks for `edi`, installs `easydiffraction` from the preview index
when needed, and prepares the project in a temporary workspace on Colab.
The public docs build and `pixi run notebook-convert` use this converter.
The Examples table links to each notebook at the documentation's source
commit. Downloadable ZIPs carry the same tutorial with project-relative paths.

Use pip’s `--extra-index-url` for notebook setup and pip installation instructions.
Keep PyPI available for Python dependencies while selecting the higher calendar
version of `easydiffraction` from our index. Published release wheels must be
publicly downloadable before the index can expose them; draft assets are excluded.
