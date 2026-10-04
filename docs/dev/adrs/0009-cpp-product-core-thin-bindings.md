# 0009. One C++ product core; thin bindings and hosts

- **Status:** Accepted
- **Date:** 2026-07-04
- **Implementation:** 🟡 Partially implemented — E01 built the core library target (`edi_core`) + the thin CLI + one C++ host scaffold (option-gated); product logic in the core is E02, the nanobind bindings E02, the app host E04 (started: the host, its typed view-models over core calls and the pages — [ADR-0015](0015-edi-app-stack.md)).
- **Priority:** Highest
- **Forward constraint (binding on new features):** Product logic — the user-facing model, `.edi`/
  CIF I/O orchestration, analysis configuration, session/undo logic — is implemented **once, in the
  C++ product core (`core/`)**. The Python library, the QML app, and the CLI are **thin, logic-free
  consumers** (bindings / hosts / presentation). A feature implemented in a binding or host instead
  of the core is a defect; new product logic lands in the core first.

**Amended 2026-10-02 (owner decisions 2026-09-29, [ADR-0021](0021-pattern-presentation.md), [ADR-0022](0022-structure-scene.md)):** a *view description* —
what a viewer shows: the series, their decimation for the screen, the scales, the styles and the layout — is product logic and lives once in the core;
*drawing* it stays per surface. This sits beside the amendment (display metadata rides the parameter; presentation is per surface): a surface chooses how
it draws, never what is drawn.

## Context

Decisions D2 (desktop runtime) and D6 (CLI language) asked how the app and CLI are embodied. The
seed recommendation (inherited from the beta context) was PySide6 for the desktop app + a C++/CMake
host for WASM, and a Python CLI on `edi/lib` — both optimizing developer velocity in isolation.

The owner overrode both (2026-07-04), with the decisive argument: **PySide-desktop + C++-WASM means
the product layer exists twice.** Qt for Python has no WASM target, so the C++ host is required for
the browser regardless; a Python desktop app then forces two hosts and two backend wirings (Python
for lib+desktop, C++ for WASM). It also ships a bundled CPython+PySide6 runtime (a far larger,
slower-starting desktop app) and splits desktop from WASM behaviour — undermining the ADR-0006
parity goal. crysta's roadmap already points the C++ way: decision 20 specifies the CLI as
**`easydiffraction` (C++, Python-free)** (crysta C10) and plans the QML engine bindings as C++
milestones (C21 desktop, C28 WASM). And crysta itself is the pattern: a C++ core with thin,
logic-free bindings.

## Decision

**The user-facing product layer is implemented once, in C++, and every surface consumes it thinly.**

1. **`core/` — the C++ product core** (C++17/20, **Qt-free**): the user-facing model (`Project`,
   structure/experiment datablocks, analysis config), `.edi`/CIF I/O orchestration, and the crysta
   adapter. The core talks to crysta through its **public API only** (ADR-0003 unchanged).
2. **`app/` — one C++/CMake QML host** (`qt_add_qml_module`): **desktop and WASM are two build
   targets of the same host** — one codebase, cross-compiled. Thin QObject/view-model adapters over
   the core live in the app layer (or come from crysta's C21 QML adapter for engine state); the base
   is consumed per ADR-0005. No PySide host for edi's app.
3. **`cli/` — a C++, Python-free binary** (`easydiffraction`, per crysta decision 20 / C10): a thin
   `main()` over the core (ADR-0007). Directly executable, no runtime to install.
4. **`lib/` — thin Python bindings + pythonic sugar**: `import edi` / `pip install easydiffraction`
   are unchanged (ADR-0002), delivered as **nanobind** bindings over the core (matching crysta's
   binding stack) plus a small pure-Python sugar layer (notebook/plot/display helpers —
   presentation only, never product logic).
5. **`diffraction-lib`'s migration role shifts accordingly:** it defines the **API shape and the
   Python-surface ergonomics** the bindings must mirror; the implementation is the C++ core
   (MIGRATION-MAP amended). It is not ported as Python product code.

## Consequences

- **One implementation** of the product layer serves all four surfaces — no Python/C++ drift, no
  double maintenance; the app and CLI cannot disagree with the library because they are the same core.
- The desktop app is **much smaller and faster** (no bundled Python), and desktop↔WASM parity is
  structural (same host) rather than gated per feature.
- **C++ becomes the primary product-implementation language.** Slower per feature than Python —
  accepted; the app was gated on gui-components Phase I anyway, which is the runway the core needs.
- The **pythonic quality of `edi/lib` is now deliberate binding work**: mirroring diffraction-lib's
  notebook-friendly ergonomics at the binding surface is an explicit E02 design concern, not free.
- The GUI base's PySide-wheel path is **not consumed by edi's app** (it remains a base capability
  for other consumers); ADR-0002/0006 are amended accordingly.
- Where the core should **reuse crysta's I/O** (crysta reads `.edi` projects already, ADR-0012 there)
  vs. own the writer is an E02 design question — the parity invariant (ADR-0003 pt 3) holds either way.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| PySide6 desktop + C++/CMake WASM (the seed recommendation) | Two hosts, product layer implemented twice (Python + C++), bundled Python runtime, desktop/WASM divergence. Rejected by the owner (D2). |
| Pure-Python `edi/lib` as the product layer + a C++ app | Same duplication through the back door — the app re-implements the model in C++. Rejected. |
| Python everywhere (desktop PySide, WASM via a Python-in-browser stack) | Qt for Python has no WASM story; Python-in-browser stacks can't host Qt Quick. Not viable. |
| Embed a Python interpreter in the C++ app to reuse a Python core | Ships the runtime anyway, adds GIL/embedding complexity, still two languages in the hot path. Rejected. |
| C++ CLI generated separately from crysta only (no product core reuse) | Duplicates project/analysis handling between cli and app. Rejected — one core, thin `main()`. |

## Amendment: presentation is per-surface

The original premise that one shared rendering implementation in `edi::core` serves every surface
is revised: **there is no single shared visualisation implementation to protect.** The surfaces
render differently by design — the edi Python API uses the rich stack (plotting and tables, as
diffraction-lib does), the edi CLI renders ASCII (as diffraction-lib does), the QML GUI uses
native QML visualisation libraries, and crysta renders nothing at all.

What must be shared is the **data and the display metadata, never the renderer** — which is why
`display` (display/latex names and units) lives on the `Parameter` metadata substrate
(`edi/parameter_spec.hpp`) rather than inside any one rendering path. The core's forward
constraint is unchanged for product logic; rendering choices are per-surface concerns.
