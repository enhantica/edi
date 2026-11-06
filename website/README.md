# The EasyDiffraction website

The public site at <https://enhantica.github.io/edi/>, built with [Zensical](https://zensical.org). EasyDiffraction is
the public name; `edi` is the package and code name. The site has Home, User guide, Application, Python, Command
Line, Physics and About. Each interface has the same menu as the User guide: Start here, then an Analysis workflow with
Project, Structure, Experiment, Analysis and Report, then Examples at the bottom. In Application, each stage's entries repeat the app's
sidebar groups ([ADR-0015](adrs/0015-application-menu-follows-the-sidebar.md)).

The Pages workflow publishes three things together: this site at the root, the contributor documentation (`mkdocs.yml`
and `docs/` at the repository root) under `/dev/`, and the web application under `/webapp/`.

## Build and preview

```sh
pixi run site-build
python -m http.server 8873 --bind 127.0.0.1 --directory website/_build
```

Then open <http://127.0.0.1:8873/>. `site-build` renders the generated pages, builds `surfaces/` with
`zensical build --strict`, writes plain Markdown under `reference/` and a root `llms.txt`, and checks the generated
links, the Physics catalogue headings and the parameter reference. Pages passes
`--base-url https://enhantica.github.io/edi/`.

## Layout

- `surfaces/`: the site itself: `mkdocs.yml`, the pages in `docs/` and the theme overrides in `overrides/`.
- `render_*.py`: generators the build runs. They write the interface pages, the experiment tags, the workflow pages,
  the parameter reference and the learning comparisons from committed snapshots.
- `import_gui_captures.py`, `capture_interfaces.py`, `capture_learning.py`: import the app's documentation captures
  (`tools/docs/capture-gui.sh`, see `app/docs/README.md`) and make the comparison figures.
- `checks/`: the capture validator and browser checks.
- `adrs/`: the site's design decisions. `DESIGN.md`, `CONTENT-SOURCES.md` and the other notes record where the
  content and the design came from.

## Native reference and teaching assets

The project's documentation architecture decision governs the site; the ADRs in `adrs/` record the implementation detail.

Build the native app's optional `edi_doc_metadata` target and save its stdout as dictionary JSON. In the same edi Python
environment, run `tools/docs/python-reference.py --output python-paths.json`. Import those files with
`render_parameter_reference.py --import-native . --dictionary dictionary.json --python-paths python-paths.json
--sdk-library SDK_LIBRARY`. This keeps the SDK and source hashes and the Python binding commit. The app's example and
tag snapshot is imported with `render_experiments.py --import-native .`. Ordinary builds render the committed
snapshots and check every native documentation target.

`capture_learning.py --edi-root .` uses the example the GUI manifest selects, calculates and fits a copy of it, and
exports Plotly SVGs on matching axes and a terminal transcript. It needs an installed Chromium browser; set
`BROWSER_EXECUTABLE` if it is not `chromium`. For the Application tutorial, pass `--gui-capture BUNDLE` to use the
saved starting and fitted projects of a completed native run.

## Browser checks

`capture.py surfaces`, `checks/math_browser.py` and `checks/network_browser.py` drive a browser over a built site with
Playwright, which the pixi environment does not install. They write their reports to `_build-checks/`.

## Icons

The site's symbols are Font Awesome 5.15.4, the same set as the application, as `:fa5-name:` in text and `fa5/name` in
front matter and `mkdocs.yml`. Add a new one with `render_fa5_icons.py`; the build refuses other sets. See
[ADR-0014](adrs/0014-font-awesome-icons.md).
