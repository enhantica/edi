# Download reference

`build.py` authors a local collection of two distinct measured files and a saved-project
archive. Its payloads and SHA-256 values come from Python's standard library, independently
of the collection implementation. The reversed insertion order distinguishes listing order
from index order. Tests must point every source at local files or recorded transports.

The public function names, signatures, one-based listing numbers, sorted data ids,
`destination` and `overwrite` options, and project ZIP extraction follow
[the reference CLI documentation](https://github.com/easyscience/diffraction-lib/blob/0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf/docs/docs/cli/index.md)
and its Python utility docstrings at the same revision, `src/easydiffraction/utils/utils.py`.
The app parser is checked against the authored entry, rather than used to author it.
