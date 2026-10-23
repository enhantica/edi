# Distribution licence inputs

The application workflow stages each surface where it is built. The Linux leg
of `app` stages and checks desktop, Python and CLI outputs. `app-wasm` stages and
checks the web site. System partitions delegate this module to those jobs.
`job.yml` preserves the original standalone-job design for reference; the
installed workflow is the source of the current build and check commands.

| Variable exported through `GITHUB_ENV` | Actual input |
| --- | --- |
| `EDI_DESKTOP_BUNDLE` | `cmake --install build/app --prefix build/distribution-licences/desktop` |
| `EDI_WEB_BUNDLE` | `build/wasm/site`, copied to `build/distribution-licences/web` |
| `EDI_PYTHON_BUNDLE` | A real Hatchling wheel, unpacked into `build/distribution-licences/python` |
| `EDI_CLI_BUNDLE` | `build/ci/cli/easydiffraction` and only the licence sidecars actually emitted beside it, collected into `build/distribution-licences/cli` |

Run `stage.py --surfaces desktop,python,cli` after `core-build` and `app-build`,
or `stage.py --surfaces web` after `wasm-build`. Only the requested inputs are
read and only their bundle variables are exported. Omitting `--surfaces` stages
all four. Each invocation needs a fresh output directory; use `--output` to choose
one. An old package must never contribute a component left over from another
build. An explicit bundle variable can instead point at an independently unpacked
release artifact.

The fixture never creates licence lists from expected columns. In particular, if
the CLI build emits no component notices while its column declares a component,
the CLI case remains red and names the missing component. The common desktop/web
notices document contains legal texts for multiple surfaces; that is not the
About display list. The rendered About actor checks the desktop list separately.
Both app columns include plotly.js and three.js because both ship report assets.
The Python wheel carries individual `licenses/*-LICENSE` files, not a synthetic
`THIRD-PARTY-NOTICES` bullet format.

A design fragment alone does not constitute CI evidence. Web About still needs a browser observation of its
component rows before that part of acceptance can count.

The production-inclusion ceiling in `production_components.json` is reviewed
independently of `DEPENDENCIES.md`. It records inclusion witnesses, not a copy of
that file's marks. New components need their own witness before appearing in any
component list; falsely marking a development tool "compiled in" does not admit
it. This ceiling does not prove a component is present in a particular package;
the delivered-file checks still apply. Design and porting projects, including
easydiffractionbeta and diffraction-lib, are excluded. The element data's original
licence obligations are assessed separately; a porting project's name is not a
substitute for an original data source. Plotly and three remain included in both
app surfaces.

The focused popup actor uses the actual About dialog and pointer-operated link,
then checks every source-model row against that independent ceiling. The width
oracle measures all values (including virtualised rows) with Qt FontMetrics,
adds `AppSizes.fieldSpacing` on both sides of each column, the shared inter-column
spacing, outer row margins and borders, and permits only pixel rounding. It does
not call the production column-width helper. The margin actor scrolls every real
delegate and checks both text insets in every header and row cell, in both themes.
`fieldSpacing` is the documented common table-column padding in AppSizes; matching
zero header and row padding is not sufficient. Run only these actors with
`pytest --noconftest tests/integration/app/test_about_components.py`.
