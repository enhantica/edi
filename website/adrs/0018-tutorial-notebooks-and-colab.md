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

The package itself comes only from our index. Pip never chooses it: the setup
cell (`website/notebook_install.py`, copied whole into each notebook) reads our
index page, takes the newest wheel this interpreter supports with its SHA-256,
and installs it as a direct reference without dependencies, with every pip
environment setting and configuration file switched off. It then installs the
wheel's declared dependencies by name with the user's usual pip settings, which
cannot reselect the package itself, and finally proves the result: the installed
distribution's `direct_url.json` names that URL and digest, and `import edi`
loads its files. The pip instructions give the same direct reference. Pip pools
all configured indexes and find-links and prefers the highest version, and
`--isolated` still reads global and per-environment configuration files, so no
index option can bind the package.

An `edi` already imported from another distribution cannot be replaced in a
running kernel; the cell refuses and asks for a restart. An `edi` no pip
distribution owns is a source build and is used as it is, with a message naming
its path.
Published release wheels
must be publicly downloadable before the index can expose them; draft assets are
excluded.
