# 0007. CLI surface (C++, Python-free)

- **Status:** Accepted
- **Date:** 2026-07-04 (D6 ratified by the owner the same day)
- **Implementation:** 🟡 Partially implemented — E01 built the `easydiffraction` CLI stub (a thin `main()` over the core, Qt-free); v1 load/calculate/fit/round-trip is E03.
- **Priority:** Medium

**Amended 2026-07-04 (D8 — shipping embodiment):** the CLI is a **tiny Qt-free console binary**
built from the same tree and shipped **in the same QtIFW installer as the app** (a selectable
"Command-line tools" component) — no separate CLI product or installer. See Decision pts 5–6 for
why a single dual-mode GUI binary was rejected.

## Context

edi ships a command-line surface as one of its four delivery targets (ADR-0001/0002). crysta's
roadmap decision 20 already specifies it: **"CLI `easydiffraction` (C++, Python-free)"**, bound at
crysta **C10**. The earlier draft of this ADR floated a Python CLI on `edi/lib` as the fast v1 path —
that made sense only under a Python-native `edi/lib`; with the product core in C++ (ADR-0009) the
Python CLI loses its one advantage and adds a runtime for nothing. The owner ratified the C++ CLI
(D6, 2026-07-04).

crysta's own `crysta fit <project-dir>` (its ADR-0040) remains the *engine's* CLI; the product CLI
here drives the user-facing API and is what end users script.

## Decision

1. **The product CLI is C++ and Python-free**, lives in `edi/cli`, and is a **thin `main()` over the
   C++ product core** (ADR-0009) — no product logic of its own, no Python runtime. Distributed as
   the **`easydiffraction`** binary (crysta decision 20 naming).
2. **It drives the same user-facing API** as the other surfaces (ADR-0001): no CLI-only
   reimplementation of project/model logic.
3. **v1 scope:** load an `.edi`/project, run a calculation and a refinement via crysta (progress to
   stdout, results to stdout/JSON), and round-trip the project — the same operations the app drives,
   scriptable and CI-friendly.
4. A `python -m edi …` convenience entry over the `lib` bindings **may** exist later for pip users;
   it is a shim, not the product CLI, and is explicitly out of v1 scope.
5. **Shipping: one installer, two thin entry points (D8).** The **QtIFW installer** ships the GUI
   host and the `easydiffraction` console binary together (the CLI as a selectable component, put on
   PATH where the platform allows); there is no separate CLI product to version/sign/distribute. An
   optional **lean CLI-only archive** (core + CLI, no Qt) for clusters/CI may be produced later from
   the same tree.
6. **The CLI binary is Qt-free** — it links the product core (+ crysta) and a minimal argument
   parser only. This, rather than a dual-mode GUI binary, because of two platform traps:
   (a) **Windows console semantics** — a GUI-subsystem executable invoked from cmd/PowerShell does
   not attach to the console and the shell does not wait for it (no stdout, broken `&&`/exit-code
   contract); the standard fix is exactly a console-subsystem companion binary. (b) **GPU-less
   Linux nodes** — a GUI-linked binary carries Qt Gui/Quick/GL **load-time** deps that can fail
   before `main()` runs on headless clusters; the Qt-free CLI has none. Complementary, not a
   substitute: the GUI host also supports `-platform offscreen` for headless **rendering** (future
   batch report/chart export) — that path is for rendering tasks, the console binary for compute.

## Consequences

- A single, small, directly-executable binary — no interpreter to install; ideal for CI, clusters,
  and scripted pipelines. Its behaviour cannot drift from the app/lib because all three consume the
  same core (ADR-0009).
- The CLI depends on the core (E02) and crysta's C++ API; it is scheduled after the core exists
  (E03, gated on E02) and aligns with crysta C10.
- Headless testing of the product layer becomes cheap: the CLI is the natural harness for
  round-trip/parity fixtures.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Single dual-mode binary (GUI + `--no-gui` in one executable) | Viable on Linux/macOS (choose `QCoreApplication` vs `QGuiApplication` from argv), but on Windows a GUI-subsystem exe breaks console scripting (cmd doesn't wait, no stdout/exit codes — needs a console shim, i.e. a second binary anyway), and Qt Gui/GL link-time deps can fail to load on GPU-less cluster nodes. Rejected (D8) for two thin binaries in one installer. |
| Fully separate CLI deliverable (own installer/archive) | Two artifacts to version/sign/distribute for no user gain; the lean CLI-only archive remains an optional later add from the same tree. Rejected (D8). |
| Python CLI on `edi/lib` (the earlier draft recommendation) | Only advantageous if the product layer were Python; under ADR-0009 it adds a runtime + a second wiring for nothing. Rejected (D6). |
| Reuse crysta's `crysta fit` as the product CLI | That is the engine's CLI over `.edi` dirs, not the product API surface. Complementary, not a replacement. |
| Both CLIs as co-equal products | Two behaviours to keep in parity for no user gain; the optional `python -m edi` shim covers pip users later. Rejected for v1. |
| No CLI (app + lib only) | The owner explicitly wants a CLI surface. Rejected. |
