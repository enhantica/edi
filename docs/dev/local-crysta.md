# The app against a local crysta

edi normally links a released, pinned crysta SDK ([ADR-0017](adrs/0017-prebuilt-crysta-sdk.md)). When you
change crysta and edi together, one command builds crysta from your checkout, links the app to it and starts
the app:

```bash
git clone https://github.com/enhantica/crysta.git
git clone https://github.com/enhantica/edi.git
cd edi
pixi run -e app app-with-crysta ../crysta
```

Use the same branch in both clones when the change spans them (`git clone --branch <branch> ...`).

- crysta is built as it is in the checkout, uncommitted changes included, in crysta's own `cpp-ci` pixi
  environment, and installed under `<crysta>/build/edi-local`. crysta's tests are not run.
- The app is built into `build/app` against that install. The next plain `pixi run -e app app` goes back
  to the pinned SDK and configures `build/app` afresh.
- Arguments after the checkout go to the app, for example `--demo <dir>`.
- The first run installs both pixi environments and takes several minutes; later runs rebuild only what
  changed. Set `CMAKE_BUILD_PARALLEL_LEVEL` to limit the crysta build's parallel jobs.

This is for local development only. CI and releases always link the pinned SDK, and the command refuses
to run in CI.
