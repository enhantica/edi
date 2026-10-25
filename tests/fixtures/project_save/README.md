# Project saves and archives

`reference.py` uses decimal arithmetic, independent of the engine, for the
project's default two-digit standard uncertainty, its declared IUCr choice,
and six significant digits without an uncertainty. The constant-background
case independently predicts every calculated point. Its saved-fit companion
checks weighted residuals against the written rounded model.

`generate_inputs.py` records changed and newly added committed project inputs.
`input-transitions.json` labels these as regression pins and retains each
complete historical witness. The hidden gate still compares every source byte
and the complete first/second-save inventories. Run it in edi's environment,
with the source belonging to its pinned SDK at `build/crysta-src`.

`generate_membership.py` retains the historical output-operation catalogue and
adds exactly four bounded single-crystal row-membership contexts. The existing
escape cases still add an actual writer and repeat a permitted operation past
its occurrence limit.

The archive inputs are made by `../project_archive/generate.py`, using Python's
standard ZIP writer. `test_project_archive.py` checks the real Python and CLI
routes. `test_project_archive_app.py` drives the built application test host.
The browser gate runs against the packed production application:

```sh
pixi run wasm-check build/project-archive-browser \
  tests/system/manual/project_archive_browser.mjs \
  tests/system/py/test_project_archive.py
```

The browser gate supplies the user's folder choice using a real Chromium OPFS
directory handle. All file reads and writes use Chromium's actual File System
Access API. A second context removes the picker APIs and exercises real archive
upload and download. The driver reads the independent ZIP with Python's
`zipfile`; it never substitutes a project writer.

The opening reference is `../project_opening/baseline.json`, generated from the
committed measurement rows by `../project_opening/generate.py`. It retains the
named machine and display, every cold/warm route, the original marks and their
published targets. The timed app acceptance run must use that same machine and
display after implementation; the reference-data check does not claim that the
current app meets its targets.
