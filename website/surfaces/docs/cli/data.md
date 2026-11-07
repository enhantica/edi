# :fa5-download: Get data and tutorials

The Python package's command line lists EasyDiffraction's collection and downloads from it, the
same collection the application's **Load ▾ From web…** reads.

```console
python -m edi list-data
python -m edi list-data --kind project
python -m edi download-data pd-neut-cwl_lbco-hrpt -d data
python -m edi list-tutorials
python -m edi download-tutorial pd-neut-cwl_lbco-hrpt -d tutorials
python -m edi download-tutorial 1 --py
python -m edi download-all-tutorials -d tutorials
```

A name is an entry's id or its number in the listing; use the id in scripts. A project archive is
unpacked into its own folder, and the command prints where. Sizes and SHA-256 digests are checked,
and `-o`/`--overwrite` replaces what is already there. `--source` reads another collection; so does
`EDI_COLLECTION`.

The standalone executable does not offer these commands yet.
