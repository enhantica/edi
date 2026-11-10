# Web archive owner permissions

`generate.py` writes the independent opaque inputs, including nested paths,
Unicode text, a hidden binary file and an empty file. These are the expected
bytes; no ZIP reader or product output generates them.

The hidden Qt support calls the actual `WebFiles::pack` and `packFiles`.
Python's standard-library `zipfile` reads their Unix external attributes,
then extracts the archives and applies the stored modes. `stat.S_IRUSR`
requires the owner's read bit on every member; `stat.S_IXUSR` also requires
search permission on directory members. Actual listing and reading is
attempted after applying those modes, including each implicit parent folder.
No Qt ZIP reader is used to judge Qt ZIP output.
