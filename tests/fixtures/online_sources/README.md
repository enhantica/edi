# Online sources, offline

Two small collections for the Load ▾ From web… popup (ADR-0068), so a test or a capture runs with no network:

- `easydiffraction/`: a structure, a full experiment and a measured pattern, the tutorial's La0.5Ba0.5CoO3 at HRPT.
- `cod/`: one structure under a COD-like id; a COD source pointed at a folder is read as a collection.

Point the app at them for one run:

```
EDI_ONLINE_SOURCES="cod=file://$PWD/tests/fixtures/online_sources/cod;easydiffraction=file://$PWD/tests/fixtures/online_sources/easydiffraction"
```

or `--online-source cod=file://…` and `--online-source easydiffraction=file://…` on the command line. A source
that should be unreachable can point at a folder that does not exist.
