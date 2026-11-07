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

The setup installs `easydiffraction` from the preview index unless `edi` is
already imported or comes from a source build, and prepares the project in a
temporary workspace on Colab. Every generated notebook ends with the interactive
report, so the notebook Colab opens and the one in the download ZIP match.
The public docs build and `pixi run notebook-convert` use this converter.
The Examples table links to each notebook at the documentation's source
commit. Downloadable ZIPs carry the same tutorial with project-relative paths.

The package itself comes only from our index. Setup and the pip instructions
install it with `--index-url` set to our index, `--no-deps` and `--force-reinstall`,
with `--isolated` in notebooks so pip configuration cannot add an index, then run a
second install of the same version to resolve dependencies from PyPI. Pip treats all
configured indexes as one pool and prefers the highest version, so
`--extra-index-url` would let PyPI or another index supply a package of the same
name, and would fall back to it when our index is unreachable. A pip-installed `edi`
is replaced, since its origin cannot be told from its metadata; an `edi` imported
from a source build is the developer's own and is kept. Published release wheels
must be publicly downloadable before the index can expose them; draft assets are
excluded.
