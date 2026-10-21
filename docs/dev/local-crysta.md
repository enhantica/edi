# The app against a local crysta

edi normally links a released, pinned crysta SDK ([ADR-0017](adrs/0017-prebuilt-crysta-sdk.md)). When you
change crysta and edi together, one command builds crysta from your checkout, links the app to it and starts
the app:

```bash
cd edi
pixi run -e app app-with-crysta ../crysta
```

Here `../crysta` is a crysta checkout next to edi. When a change spans both, check out the same branch in each.

On macOS, the selected Apple developer tools must already be ready. Before Git metadata, Pixi installation
or either build, the launcher checks the selected macOS SDK and Apple C++ tool in the same clean environment
used for crysta. Ready Command Line Tools-only setups are supported; full Xcode is not required. A failed
check keeps Apple's original error and stops. Complete the indicated setup or license review yourself:
open Xcode when using Xcode, or install/select the Command Line Tools. If Apple specifically requests
`sudo xcodebuild -license`, review that license manually in Terminal; the launcher never runs it for you.

This is a prerequisite check, not a compiler/header diagnosis. Resolve the first developer-tools error
before investigating later `NAN`/`INFINITY` or other compilation failures; this check does not prove their
cause or guarantee that they disappear. Linux and the original local/CI separation are unchanged.

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


For the SDK27/older-Clang header incompatibility, prerequisite readiness alone is
insufficient. Both crysta's `default`/`cpp`/`cpp-ci`/`oracle` and edi's `default`/`app`
Mac dependencies must resolve the coordinated Clang/libc++23 family; see
[ADR-0017](adrs/0017-prebuilt-crysta-sdk.md#selected-macos-sdk-compatibility-and-coupled-compiler-family).
Use reviewed matching lockfiles and a fresh isolated local build. Do not patch
`NAN`/`INFINITY`, mix an old SDK archive with new headers, or infer a successful
Mac build from dependency declarations. The actual selected SDK and resolved
compiler/header/ABI identities still require a genuine build check.
