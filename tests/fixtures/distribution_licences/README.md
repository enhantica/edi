# Distribution licence inputs

`job.yml` is the complete job fragment to add to the application workflow. Existing
CI does not produce a desktop install package or a CLI package. Its `app-wasm`
job does upload `edi-webapp`, directly from `build/wasm/site`; that artifact is a
directory of files, not an archive containing `edi-webapp.zip`.

The proposed `licence-surfaces` job builds the pinned native core and desktop app,
downloads that same run's web artifact, then runs `stage.py`. It produces:

| Variable exported through `GITHUB_ENV` | Actual input |
| --- | --- |
| `EDI_DESKTOP_BUNDLE` | `cmake --install build/app --prefix build/distribution-licences/desktop` |
| `EDI_WEB_BUNDLE` | The downloaded `app-wasm` site's files, copied to `build/distribution-licences/web` |
| `EDI_PYTHON_BUNDLE` | A real Hatchling wheel, unpacked into `build/distribution-licences/python` |
| `EDI_CLI_BUNDLE` | `build/ci/cli/easydiffraction` and only the licence sidecars actually emitted beside it, collected into `build/distribution-licences/cli` |

Locally, run `stage.py` with the project's default Python environment after
`core-build`, `app-build` and `wasm-build`. The gates find those conventional paths
without environment variables. Use a fresh output directory; an old package must
never contribute a component left over from another build. An explicit variable
can instead point at an independently unpacked release artifact.

The fixture never creates licence lists from expected columns. In particular, if
the CLI build emits no component notices while its column declares a component,
the CLI case remains red and names the missing component. The common desktop/web
notices document contains legal texts for multiple surfaces; that is not the
About display list. The rendered About actor checks the desktop list separately.
Both app columns include plotly.js and three.js because both ship report assets.
The Python wheel carries individual `licenses/*-LICENSE` files, not a synthetic
`THIRD-PARTY-NOTICES` bullet format.

This job is a design fragment until installed in the required workflow. Its
producer commands and environment handoff are explicit; a fragment alone does
not constitute CI evidence. Web About still needs a browser observation of its
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
