# The app against a local crysta

edi normally links a released, pinned crysta SDK ([ADR-0017](adrs/0017-prebuilt-crysta-sdk.md)). When you
change crysta and edi together, one command builds crysta from your checkout, links the app to it and starts
the app:

```bash
cd edi
pixi run -e app app-with-crysta ../crysta
```

Here `../crysta` is a crysta checkout next to edi. When a change spans both, check out the same branch in each.

- crysta is built as it is in the checkout, uncommitted changes included, in crysta's own `cpp-toolchain`
  pixi environment, and installed under `<crysta>/build/edi-local`. This environment uses the shared native
  toolchain without installing crysta's Python package or its test extras. crysta's tests are not run.
  The crysta checkout must include this environment and its updated lock file; frozen installation refuses
  a missing or stale lock rather than falling back to a test environment.
- The app is built into `build/app` against that install. The next plain `pixi run -e app app` goes back
  to the pinned SDK and configures `build/app` afresh.
- Arguments after the checkout go to the app, for example `--demo <dir>`.
- The first run installs both pixi environments and takes several minutes; later runs rebuild only what
  changed. Set `CMAKE_BUILD_PARALLEL_LEVEL` to limit the crysta build's parallel jobs.
- On a Mac the command first checks that the selected macOS SDK and Apple's C++ tools work, and stops with
  Apple's message when they do not: finish Xcode's setup or install the Command Line Tools first. Both
  products build with Clang 23 on a Mac, which the macOS 27 SDK needs ([ADR-0017](adrs/0017-prebuilt-crysta-sdk.md)).

This is for local development only. CI and releases always link the pinned SDK, and the command refuses
to run in CI.

## The command line against a local crysta

The command line has the same four tasks as the app, in the default environment:

| task | does |
| --- | --- |
| `pixi run cli-build` | builds the command line into `build/cli` against the pinned SDK, as `app-build` |
| `pixi run cli <arguments>` | builds, then runs it, as `app` |
| `pixi run cli-run <arguments>` | runs the built command line without building, as `app-run`; it asks you to build first when there is none |
| `pixi run cli-with-crysta ../crysta <arguments>` | builds crysta from the checkout, builds the command line against it into `build/cli`, then runs it, as `app-with-crysta` |

```bash
cd edi
pixi run cli-with-crysta ../crysta fit docs/user/cli/pd-neut-cwl_lbco-hrpt/project
pixi run cli-run fit docs/user/cli/pd-neut-cwl_lbco-hrpt/project
```

The second command reruns the same build without building again. crysta is built exactly as for the app (the
same step and install under `<crysta>/build/edi-local`), and the next plain `pixi run cli` goes back to the
pinned SDK. `build/cli` is the command line's own tree, so a local crysta never reaches the build the Python
package and the tests use. As for the app, `cli-with-crysta` is for local development only and refuses to
run in CI.

## The tutorial notebooks against a local crysta

The same route runs the Python tutorials, for example to see them with a crysta change before it is published:

```bash
cd edi
pixi run notebooks-run-with-crysta ../crysta
```

- crysta is built exactly as for the app above, into `<crysta>/build/edi-local`; both commands share that step.
- edi's Python package is built against it into `build/local-crysta`. The pinned build in `build/ci` is left as
  it is, so a later `pixi run notebooks-run` or `pixi run core-build` still uses the pinned SDK.
- The example collection is built from this checkout into `build/collection`, so the tutorials find the
  structures and data they download even before the collection is published.
- The tutorials then run with that package and collection, and their outputs are written into the notebooks
  under `docs/user/tutorials/`, as `pixi run notebooks-run` writes them. Their install cell is skipped, as the
  package is the one just built. Name tutorials after the checkout to run only those, for example
  `pixi run notebooks-run-with-crysta ../crysta pd-neut-cwl_lbco-hrpt`.
- `pixi run site-build` then turns the run notebooks into the docs pages, and `pixi run site-serve` serves them;
  both refuse a tutorial that has not been run, so run them all (no tutorial names) before building the site.
- Do not commit the run notebooks: the repository keeps them without outputs (`python website/prepare_notebooks.py`
  writes them back so).

This too is for local development only and refuses to run in CI.
