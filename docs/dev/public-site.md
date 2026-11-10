# Building the public site

`pixi run site-build` builds the public documentation site (`website/`) into `website/_build`, and
`pixi run site-serve` builds it and serves it at <http://127.0.0.1:8873/>. Both take the same options.

The Python tutorials' pages are made from the notebooks under `docs/user/tutorials/`, with their results when the
notebooks have been run (`pixi run notebooks-run`). Running them takes a while, so a local build has three ways to
treat them:

| Mode | Command | Tutorial pages |
| --- | --- | --- |
| Local, default | `pixi run site-build` | A run notebook shows its results; one that has not been run shows its code under a "Not run" note. |
| Quick | `pixi run site-serve --no-notebooks` | Each tutorial is a short placeholder page, so links and the menu stay valid. |
| Published | `pixi run site-build --require-outputs` | A notebook that has not been run stops the build. |

The repository keeps the notebooks without outputs: a run notebook can pass GitHub's 100 MB file limit, and
`pixi run notebook-outputs` (in CI's lint job) refuses a committed notebook with outputs. Strip a run notebook
with `pixi run notebook-strip` before committing it. The Pages workflow (`.github/workflows/pages.yml`) and CI's
docs job therefore run every notebook (`pixi run notebooks-run`) and then build with `--require-outputs`, so the
published site never shows a tutorial without its results. `--require-outputs` and `--no-notebooks` exclude each
other.

On the development machine (2026-11-09, other jobs running alongside), the full build with every notebook run
took 53 s and the quick build 36 s; the time saved is converting the notebooks and their report views, and grows
with them.
