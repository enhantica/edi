# edi — architecture & upstream contracts

## What edi is

edi is the **product**: a diffraction-data-analysis application (crystal structure refinement,
pattern simulation, CIF/`.edi` I/O, reporting) delivered as a **desktop app** and a **web app
(WASM)** with the same QML front-end. It owns no compute physics and no generic GUI toolkit — it
**binds** two upstreams into a shippable product.

```
        crysta (engine)                     gui-components (GUI base)
   C++/Python calculator+minimizer      EasyApplication QML: Elements/Components/Style/Charts
                 │                                        │
                 └──────────────┬─────────────────────────┘
                                ▼
                              edi
        core/ (C++ product core → crysta; ADR-0009)   app/ (QML, one C++ host: desktop+wasm)
        lib/ (import edi — thin bindings)   cli/ (C++, Python-free)   shared/ (session)   docs/
```

## Upstream 1 — crysta (compute engine)

- Provides the calculator + minimizer with a stable API and cross-surface parity (see crysta's
  roadmap: the calculator α is crysta **C08**, minimizer + default-engine flip **C09**; the desktop
  QML binding is crysta **C21**, the WASM binding **C28**).
- edi consumes it as the backend of `edi/lib` (`import edi`, dist `easydiffraction`) and — for the
  browser — via crysta's WASM build.
- **Contract:** edi calls the engine's public API only; no reaching into engine internals. Progress/
  cancel callbacks, residual-only API, and the EditCommand/undo primitive come from crysta.

## Upstream 2 — gui-components (GUI base)

- Provides `EasyApplication.Gui.*`: `Style` design tokens, `Elements` primitives, `Components`
  composed furniture, a native **charting façade**, animations.
- edi consumes it as the building blocks of `edi/app`, supplying its own **pages**, its own
  **`ApplicationInfo`**, and its **shared session layer** through the base's injection seams.
- **Contract (after the base's decoupling):** edi injects app specifics; the base contains none. edi
  styles via `Style` tokens, uses `Components.ApplicationWindow` + a host-supplied page model, and
  never imports the base's internals.

## The hard prerequisite: gui-components Phase I

The GUI base is, as of 2026-07, **broken on WASM and entangled with EasyDiffraction** (see its
[audit](https://github.com/easyscience/gui-components/tree/master/audit/issues/index.md)). edi's
app surface must not begin until the base clears **Phase I**:

| Base milestone | What it unblocks for edi |
| --- | --- |
| **G01** (CMake `qt_add_qml_module`, WASM builds, CI-gated) | edi's WASM app can build at all |
| **G02** (native charts + WASM-safe settings, no QtWebEngine) | edi's plots/reports/persistence work in the browser |
| **G03** (decoupled: page model, `ApplicationInfo`, updater/QtTest lifted out) | edi can adopt the base without inheriting EasyDiffraction |
| G04 (qmllint/qmlformat/Qt Quick Test gated) | edi builds on a base that won't silently regress |

**Ratified base decisions edi inherits** (from the base's ratified decisions):
**QtGraphs** for charts, and a **dual build** capability in the base (CMake `qt_add_qml_module` for
C++/WASM + a PySide wheel for desktop-Python consumers). edi's app consumes **only the CMake half**:
per D2/[ADR-0009](../adrs/0009-cpp-product-core-thin-bindings.md) one C++/CMake host builds
both the desktop and WASM targets; the base's PySide-wheel path is not used by edi's app.

## Reference material to build from

- The GUI base's **target architecture** — the injection seams (`ApplicationInfo`, page model,
  optional services), the façade pattern (settings/charts), and the dual-build model — is the design
  edi's `app/` and `shared/` should consume:
  [architecture-target.md](https://github.com/easyscience/gui-components/tree/master/audit/design/architecture-target.md).
- **Modern-Qt/QML guidelines** ([synced here](modern-qt-guidelines.md)) — the rules edi's QML must
  follow (unversioned imports, no private `.impl`, qsTr, WASM façades, testing).
- **crysta ↔ edi bindings** — crysta's roadmap already lists the edi monorepo layout and the four
  binding milestones (lib/CLI/desktop/WASM); align edi's structure with it.
- The **reference app** [`easydiffractionbeta`](https://github.com/easyscience/easydiffractionbeta)
  shows the look-and-feel to keep and the flows to reproduce (project/sample/experiment/analysis/
  summary), but on the hardened base rather than its classic stack. A beta→edi migration guide is a
  planned edi task.
