# 0006. WASM/web parity (build & render everywhere)

- **Status:** Accepted
- **Date:** 2026-07-04
- **Implementation:** 🟡 Partially implemented — E01 laid the single-host CMake baseline (one option-gated `qt_add_qml_module` host, desktop + WASM from one tree); the WASM build/render and the per-feature parity gate land with the app surface (E04 desktop · E07 WASM).

**Amended 2026-07-04 (D2 → [ADR-0009](0009-cpp-product-core-thin-bindings.md)):** edi's app uses a **single C++/CMake host for
desktop and WASM** — parity becomes structural (same host, cross-compiled), and the base's PySide-wheel path is not consumed by
edi's app. The per-feature "builds & renders on WASM" gate below remains (it still catches WASM-unsafe deps/APIs). **Amended
2026-09-27 ([ADR-0015](0015-edi-app-stack.md) §5–§6):** the desktop app starts with three recorded web gaps — the base's `Settings {
location: … }` sites, file and folder dialogs on the web, and the Text tab's scratch-directory save (MEMFS in the browser) — each to
be proven at E07. Charts and 3D are an open owner question: the Qt Graphs / Quick 3D / Charts packages are GPL-3.0-only on
conda-forge, so links none of them and shows placeholders. **Amended 2026-10-02 ([ADR-0015](0015-edi-app-stack.md) §6,
[ADR-0020](0020-calculation-worker-and-publication.md)):** the owner decided the licensing question: the app links Qt Graphs, and
the pattern chart is edi's own, on Qt Graphs directly (decision 1's "base's charting façade" does not exist at the pinned base). One
more recorded web gap: the calculation worker runs one thread on the desktop, and its executor in the browser is chosen at E07,
behind the same contract. **Amended 2026-10-02 ([ADR-0022](0022-structure-scene.md), ADR-0017 §16):** the structure view is built on
Qt Quick 3D. One more recorded web gap: Qt Quick 3D on WebGL — the view, its instancing fed from C++ and its custom camera — is
neither built nor tested for the browser here; E07 proves it or records the exception. **Amended 2026-10-03 ([ADR-0023](0023-web-build.md)):** the WebAssembly build exists: both Qt wasm
kits, a start page that picks the multithreaded build in a cross-origin-isolated page and the single-thread build elsewhere,
and one site archive built by CI. The recorded web gaps are closed there: settings persist in the browser's local storage, a
project opens from a folder the browser uploads and saves as a `.zip` download (and the Text tab's scratch files live in the
page's memory), and the calculation worker runs its jobs on the owner thread in the single-thread build. The Quick 3D structure
view builds into both kits. crysta compiles for the browser from the pinned SDK's source (amends decision 3's "crysta C28").
- **Priority:** High
- **Forward constraint (binding on new features):** A new app feature must **build and render on the
  WASM target** — no QtWebEngine, a WASM-safe settings/persistence façade, GPU-capable charts. A
  "desktop-only" feature is an explicit, feature-gated exception recorded in the task packet, never
  a silent default.

## Context

edi ships the **same** QML app as a desktop app **and** a web app (WASM) from one source tree
(ADR-0001/0002). The gui-components audit found the base **broken on WASM**: charts/reports require
**QtWebEngine**, `Settings{location}` breaks WASM, and there is no CMake `qt_add_qml_module` build.
The base's Phase I fixes this (G01 CMake/WASM revival, G02 native charts + WASM-safe settings). edi
must not add features that only work on desktop, or the web app silently rots. `Covid19`
(`knowledge/libraries/Covid19/`) is our reference for a C++ backend shipped as both desktop and WASM.

## Decision

**WASM parity is a first-class, gated property of the app surface.**

1. **Charts = QtGraphs** (GPU, WASM-capable) via the base's charting façade — **never QtWebEngine**,
   never a browser-embedded chart. (Ratified base decision, inherited.)
2. **WASM-safe persistence.** Settings/recent-files/project persistence go through a façade with a
   WASM-safe backend (no raw `Settings{location}`); the desktop and WASM backends sit behind one
   interface in `edi/shared`.
3. **One host, one source** (amended by ADR-0009). A single C++/CMake QML host
   (`qt_add_qml_module`) builds **both** the desktop and WASM targets from one QML tree (ADR-0002).
   In the browser, compute uses crysta's **WASM** build (crysta C28) through the public API
   (ADR-0003). The GUI base's PySide-wheel path is a base capability edi's app does not use.
4. **Parity gate in CI.** Web-affecting tasks must pass "**WASM example builds and renders**" as an
   acceptance gate (the operator playbook lists it). A feature that cannot meet parity is
   feature-gated and the gap is recorded in the packet — it does not silently ship desktop-only.
5. **Gated on the base.** The WASM surface starts only after the base's G01 (builds at all) + G02
   (renders + WASM-safe settings) land (ADR-0005).

## Consequences

- The web app stays a real, tested target rather than an afterthought that decays.
- Some desktop-native conveniences need a WASM-safe design or an explicit feature gate — a
  deliberate constraint that keeps one codebase serving both.
- edi depends on crysta's WASM build for browser compute; that dependency is tracked (crysta C28).

## Alternatives considered

| Alternative | Verdict |
|---|---|
| QtWebEngine for charts/reports (the classic stack) | Unavailable on WASM — the exact break the audit found. Rejected for QtGraphs. |
| Desktop-first, port to WASM later | "Later" never comes; features accumulate desktop-only assumptions. Rejected — parity is gated per task. |
| Separate web and desktop codebases | Doubles the app surface and desyncs behaviour; ADR-0002 mandates one source tree. Rejected. |
