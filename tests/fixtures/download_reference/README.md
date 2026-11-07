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

`recorded_transport.py` maps the documented data and documentation locations to this one
fixture root. It records every request, injects a primary outage and refuses every unrecorded
location. `sitecustomize.py` installs that transport in a child Python interpreter only when
its explicit reference environment is set; no socket is opened. The parent Python interface
uses the same reply object and files.

`tutorials.py` adds two independently authored notebook/script pairs and their standard-library
SHA-256 values. Its learning order differs from insertion order. The same collection-index
schema carries tutorial entries and both formats, following the one-parser contract. Format
flags, one-based row handles, explicit overwrite and batch notebook defaults follow the
reference function docstrings and CLI documentation cited above.
