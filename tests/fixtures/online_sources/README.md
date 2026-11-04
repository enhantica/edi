# Online sources, offline

Two small collections for the Load ▸ From web… popup, the CLI and Python (ADR-0068), so a test or a capture runs
with no network:

- `easydiffraction/`: a structure, a full experiment, a measured pattern and a zipped project, the tutorial's
  La0.5Ba0.5CoO3 at HRPT.
- `cod/`: one structure under a COD-like id; a COD source pointed at a folder is read as a collection.

Each file has a sidecar `<file>.meta.json` with what the file does not say about itself; the index is generated:

```
python tools/data/build_collection.py index tests/fixtures/online_sources/easydiffraction
python tools/data/build_collection.py check tests/fixtures/online_sources/easydiffraction
```

Point the app at them for one run:

```
EDI_ONLINE_SOURCES="cod=file://$PWD/tests/fixtures/online_sources/cod;easydiffraction=file://$PWD/tests/fixtures/online_sources/easydiffraction"
```

or `--online-source cod=file://…` and `--online-source easydiffraction=file://…` on the command line. A source
that should be unreachable can point at a folder that does not exist. The full collection, the bundled examples
and the tutorial files, is generated into `build/collection` by `python tools/data/build_collection.py populate
build/collection` followed by `index`.
