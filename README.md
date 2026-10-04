# edi

**edi** (EasyDiffraction) is software for diffraction data analysis: it calculates powder
diffraction patterns from structural models and refines their parameters against measured data. It
is delivered across **four surfaces** that share one API: a **Python library** (`import edi`), a
**command line** (`python -m edi`), a **desktop app**, and a **web app** — all thin consumers of
**one C++ product core** ([ADR-0009](docs/dev/adrs/0009-cpp-product-core-thin-bindings.md)).

edi builds on two upstreams:

| Upstream | Provides | edi consumes it as |
| --- | --- | --- |
| crysta | The diffraction **compute engine** (calculator and minimizer; reads `.edi` projects) | the calculation and refinement backend, through its **public API only** ([ADR-0003](docs/dev/adrs/0003-crysta-engine-boundary.md)), as a prebuilt SDK ([ADR-0017](docs/dev/adrs/0017-prebuilt-crysta-sdk.md)) |
| [`gui-components`](https://github.com/easyscience/gui-components) | The Qt/QML **GUI base** (elements, components, style) | the app's building blocks, through its **injection seams** ([ADR-0005](docs/dev/adrs/0005-gui-base-injection-seams.md)) |

crysta owns the physics; edi owns the product, the `.edi`/CIF format and the API
([ADR-0001](docs/dev/adrs/0001-product-scope-and-relation-to-crysta.md)). The documentation is
published at <https://enhantica.github.io/edi/>; its sources start at [`docs/index.md`](docs/index.md).

## Layout ([ADR-0002](docs/dev/adrs/0002-monorepo-layout.md))

```
edi/
├── core/      C++ product core — the user-facing model, .edi/CIF I/O, the crysta adapter; Qt-free
├── lib/       Python library — thin bindings and Python sugar over the core (import edi); Qt-free
├── app/       QML application — one C++/CMake host, desktop and WebAssembly builds, on the gui-components base
├── shared/    shared session layer
├── cli/       C++ command-line surface
├── docs/      the documentation — user/ (people who use edi) and dev/ (ADRs, design, requirements, verification)
├── examples/  runnable examples of the public `import edi` API
├── tests/     tests and their fixtures
└── knowledge/ the FullProf verification and fitting reference data
```

## Examples

Runnable demonstrations of the public `import edi` API live in [`examples/`](examples):

| Example | Shows |
| --- | --- |
| [`examples/fit_ncaf.py`](examples/fit_ncaf.py) | A whole-pattern refinement of a complete NCAF project directory, loaded in one call and refined with an optional progress subscriber |
| [`examples/fit_lbco_hrpt.py`](examples/fit_lbco_hrpt.py) | A constant-wavelength Rietveld refinement of LBCO measured on HRPT (PSI), built in code and refined in two stages |

Run them from a built environment:

```bash
pixi run core-build                                      # build the `edi._edi` extension once
pixi run -e default python examples/fit_ncaf.py          # the bundled NCAF fixture
pixi run -e default python examples/fit_lbco_hrpt.py     # the vendored LBCO CW measurement
```

## Running a fit from the command line

`python -m edi` is the supported entry point:

```bash
pixi run -e default python -m edi fit <project-dir>                          # compact human report
pixi run -e default python -m edi fit <project-dir> --verbosity full         # + per-bank R-factors, every iteration, every parameter
pixi run -e default python -m edi fit <project-dir> --report machine         # the versioned key=value record
```

The project directory is the whole input — there is no separate pattern file to pass and nothing to
assemble by hand. `Project.load_complete` either returns a project that is ready to fit or raises
`edi.IoError` naming what is wrong; it never returns a partially loaded one.

`import edi` itself stays **silent** — `project.fit()` prints nothing. Rendering is the caller's
decision, via `edi.machine_report` and the streaming formatters (`summary_line`,
`parameter_table`, …), or an optional `on_iteration=` subscriber for live progress.

## Running the app

The desktop app ([ADR-0015](docs/dev/adrs/0015-edi-app-stack.md)) is one C++/QML host over the
product core and the pinned [`gui-components`](https://github.com/easyscience/gui-components) base.
One command builds it and starts it, on macOS or Linux:

```bash
pixi run -e app app
```

The build downloads the pinned crysta SDK, then builds the app into `build/app` and starts it. The
first run takes several minutes; later runs rebuild only what changed. Prerequisites: pixi (the
version this workspace pins) and, on macOS, the Xcode command-line tools. Arguments after `app` go to
the app: `pixi run -e app app --demo <dir>` runs the scripted demo, which clicks through the pages and
saves one image per state into `<dir>`, then exits. `pixi run -e app app-build` only builds.

## Licence

edi's source code, the app's included, is licensed under the [BSD 3-Clause License](LICENSE). The
EasyDiffraction application built from it is distributed under the
[GNU General Public License version 3](COPYING), because it links Qt Graphs and Qt Quick 3D
([app/DISTRIBUTION-LICENSE.md](app/DISTRIBUTION-LICENSE.md)). The third-party components and their
licences are listed in [DEPENDENCIES.md](DEPENDENCIES.md), with their texts in
[THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES).
