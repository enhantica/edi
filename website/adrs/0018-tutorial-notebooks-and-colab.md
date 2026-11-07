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

The setup installs `easydiffraction` from the preview index, as described
below, and prepares the project in a temporary workspace on Colab. Every generated notebook ends with the interactive
report, so the notebook Colab opens and the one in the download ZIP match.
The public docs build and `pixi run notebook-convert` use this converter.
The Examples table links to each notebook at the documentation's source
commit. Downloadable ZIPs carry the same tutorial with project-relative paths.

The setup cell (`website/notebook_install.py`, copied whole into each notebook)
keeps this contract and claims nothing beyond it:

1. It reads our index page, takes the newest wheel this interpreter supports
   with its SHA-256, and installs it by that URL and digest, with every pip
   environment setting and configuration file switched off. Another index,
   find-links entry or pip setting cannot supply the package, and an
   unreachable index or a wrong digest stops the cell. The wheel's declared
   dependencies are then installed by name with the user's usual pip settings,
   on every run, so an interrupted dependency install is completed next time.
2. If `edi` is already imported in the kernel, the cell installs what is needed
   and stops with "Restart the runtime, then run this cell again". It never
   vouches for a module already loaded.
3. Otherwise `import edi` is admitted only when the file it would load is one
   of the files the installed wheel's RECORD lists, and the installed
   distribution records that URL and digest.

An `edi` that no pip distribution owns is a source build and is used as it is,
with a message naming its path. The pip instructions give the same URL and
digest. The threat considered is an accident: a package of the same name on
another index, a missing index, or a kernel that imported `edi` before setup
ran again. A package deliberately planted on a prepended path is out of scope.
Published release wheels
must be publicly downloadable before the index can expose them; draft assets are
excluded.
