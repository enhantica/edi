# The app against a local crysta

edi normally links a released, pinned crysta SDK ([ADR-0017](adrs/0017-prebuilt-crysta-sdk.md)). When you
change crysta and edi together, one command builds crysta from your checkout, links the app to it and starts
the app:

```bash
cd edi
pixi run -e app app-with-crysta ../crysta
```

Here `../crysta` is a crysta checkout next to edi. When a change spans both, check out the same branch in each.

- crysta is built as it is in the checkout, uncommitted changes included, in crysta's own `cpp-ci` pixi
  environment, and installed under `<crysta>/build/edi-local`. crysta's tests are not run.
- The app is built into `build/app` against that install. The next plain `pixi run -e app app` goes back
  to the pinned SDK and configures `build/app` afresh.
- Arguments after the checkout go to the app, for example `--demo <dir>`.
- Run this task in edi's `app` environment; the command installs crysta's declared `cpp-ci` environment.
  The first build can take several minutes; later runs rebuild only what changed. Set
  `CMAKE_BUILD_PARALLEL_LEVEL` to limit the crysta build's parallel jobs.

This is for local development only. CI and releases always link the pinned SDK, and the command refuses
to run in CI.

The app and its assistant execute the native C++/QML bridge. This launcher does not build/import an edi Python
extension, install edi's default binding environment, or export a Python interpreter/module path to runtime
children. The app build's metadata tooling may use the development environment's Python; that is a build-time
tool, not a shipped application runtime.

For explicit Python API development/tests, build bindings separately with the declared default environment and
an explicit local prefix, for example:

```bash
EDI_CRYSTA_PREFIX="$(cd ../crysta/build/edi-local/prefix && pwd)" pixi run -e default core-build
```

That separate binding command does not enable bindings in the app graph or change the app's native tool catalog.
A local crysta checkout is required only by this development launcher; the normal packaged app uses its pinned
native SDK and bundled helper resources. This note does not claim a packaged installer/platform runtime proof.
