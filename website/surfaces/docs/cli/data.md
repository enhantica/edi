---
icon: fa5/database
---

# Get data and tutorials

Both command lines list EasyDiffraction's collection and download from it, the same collection the
application's **Load ▾ From web…** reads. The commands are the same with `edi` (the standalone
executable) and `python -m edi`.

=== "Standalone executable"

    ```console
    edi list-data
    edi list-data --kind project
    edi download-data pd-neut-cwl_lbco-hrpt -d data
    edi list-tutorials
    edi download-tutorial pd-neut-cwl_lbco-hrpt -d tutorials
    edi download-tutorial 1 --py
    edi download-all-tutorials -d tutorials
    ```

=== "Python package"

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

The standalone executable uses the operating system's secure connections: built in on Windows and
macOS, and the libcurl library on Linux, which most systems have. Without it, the download commands
say so, and `--source` with a local folder still works.
