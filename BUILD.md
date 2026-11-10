# Building edi

edi is one C++/CMake project plus a Python package, built through [pixi](https://pixi.sh) (the
reproducible dev environment). This covers the E01 scaffold; each surface gains real behaviour in
later milestones.

## Prerequisites

Install pixi; the C++ toolchain, CMake, Ninja, and Python all come from the environment:

```
pixi install
```

## The C++ core and CLI — `pixi run core-build`

`core/` (the product core, ADR-0009) and `cli/` (the `easydiffraction` console binary, ADR-0007)
are **Qt-free** and build in the default environment:

```
pixi run core-build     # configures + builds build/ci with core + cli
```

Products: `build/ci/core/libedi_core.a` and `build/ci/cli/easydiffraction`. `core-build` is part of
the full local gate (`pixi run verify`), so a green gate implies the C++ tree compiled.

## The QML app host (`app/`) — option-gated, not built in E01

The app is one C++/CMake `qt_add_qml_module` host (ADR-0009) that targets **both** desktop and WASM
from one QML source tree (ADR-0006). It needs Qt6 and is **off by default**:

```
cmake -S . -B build/app -G Ninja -DEDI_BUILD_APP=ON     # requires a Qt6 install
```

E01 does not add Qt to the environment (dependency minimalism, ADR-0008) — the app surface is gated
on the gui-components base clearing **G01–G04** (ADR-0005 / D4). The first real desktop build+render
lands at **E04**, the WASM target at **E07**. E01 ships the reviewable host scaffold, not a built app.

## Python — `import edi`

The `easydiffraction` distribution installs the `edi` package into the pixi environment, so:

```
python -c "import edi"      # empty placeholder until the binding surface lands in E02
```

## The full local gate

```
pixi run verify     # ruff + core-build + pytest + strict docs — the gate the reviewer closes on
```

CI mirrors these per surface on the org self-hosted runners (`.github/workflows/ci.yml`),
path-filtered so a change only triggers its surface's jobs (a `cli/**` change builds via `core · Linux|macOS`).
Each platform-specific job is named `<area> · <platform>` from one platform matrix per area: `core`,
`cli-python`, `cli-native` (a dispatch-only placeholder), `app` (plus the dispatch-only `app · WebAssembly`);
`changes`, `lint`, `audit`, `notebooks` and `docs` run once.
