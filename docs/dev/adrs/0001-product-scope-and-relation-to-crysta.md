# 0001. Product scope & relation to crysta (edi owns the user-facing API)

- **Status:** Accepted
- **Date:** 2026-07-04
- **Implementation:** ⬜ Not implemented (scaffolding phase; this ADR fixes scope, not code)
- **Priority:** Highest

## Context

The diffraction-analysis product spans two repositories by design (crysta roadmap "decision 20"):
[`crysta`] is the **compute engine** (C++ calculator +
minimizer, with a Python prototype), and it deliberately contains **no user-facing API** — it reads
`.edi` EasyDiffraction project directories and exposes a public calculation/refinement API
(ADR-0040). The **user-facing surface** — the classes a scientist actually touches (`Project`,
sample model, experiment, analysis), the `.edi`/CIF I/O, the app, the CLI — has no home yet.
Historically these lived in the EasyDiffraction ecosystem split across `diffraction-lib` (the
Python library) and
`easydiffractionbeta`/`diffraction-app` (the GUI). We are consolidating that user-facing surface
into **one product repo, edi**, on top of the crysta engine.

## Decision

**edi is the product repo and the single home of all user-facing API types.** Its responsibilities
and boundaries:

1. **edi owns the user-facing API.** The Python API types (`import edi`), the `.edi`/CIF project
   I/O, project/sample/experiment/analysis/summary flows, reporting, and the app/CLI presentation
   all live here. crysta owns none of it.
2. **crysta owns compute physics.** edi calls crysta's **public API only** for calculation and
   refinement (ADR-0003); it never re-implements engine physics and never reaches into engine
   internals.
3. **One synced API across four surfaces.** The same user-facing API is delivered as a Python
   library (`edi/lib`), a CLI (`edi/cli`), a desktop QML app, and a WASM web app
   (`edi/app` + `edi/shared`) — see ADR-0002. A change to a user-facing type is a change to the
   contract for all four surfaces at once.
4. **The `.edi` project format is edi's user-facing contract; crysta is a consumer of it.** edi
   defines and evolves the EasyDiffraction project format that users author and save; crysta reads
   the same format (its ADR-0040). The two must not diverge — the format is specified on the edi
   side and cross-checked against crysta's loader.
5. **edi is a fresh, improved implementation, not a lift-and-shift.** `diffraction-lib`,
   `easydiffractionbeta`, and `gui-components` are migration **sources** to extract ideas and
   patterns from (`knowledge/libraries/`), producing improved in-repo versions with a minimized
   dependency set (ADR-0008) — not verbatim ports.

## Consequences

- There is exactly one place to change a user-facing type, and one contract to keep in sync across
  surfaces — at the cost of edi being a monorepo that must build a Python lib, a QML app, and a CLI
  (ADR-0002 accepts this).
- crysta stays a clean, reusable engine with no product entanglement; the coupling is a documented
  public API (ADR-0003), so either side can evolve behind it.
- The `.edi` format becomes a first-class, specified artifact of edi with a parity obligation
  against crysta's loader — a new field is added on the edi side and verified to round-trip.
- edi inherits the upstream gating: the app surface waits on the gui-components Phase-I hardening
  (ADR-0005/0006); `edi/lib` can proceed earlier against crysta's calculator α (crysta C08).

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Put the user-facing API types in crysta | Pollutes the engine with product concerns and Qt/CLI presentation; crysta decision 20 explicitly keeps the engine API-free. Rejected. |
| Keep the historical 3-repo split (lib + app + umbrella) | Triples the release/sync surface and the cross-repo URL juggling for one product; a monorepo gives one synced API and one answers file (ADR-0002). Rejected. |
| Verbatim-port diffraction-lib / easydiffractionbeta | Carries the classic stack and its coupling/branding debt (the gui-components audit exists because of exactly this); we want improved versions with minimized deps. Rejected in favour of guided fresh implementation. |

## Published sources

- Rietveld refinement workflow the product delivers — P. Thompson, D. E. Cox, and J. B. Hastings, *Rietveld refinement of Debye-Scherrer synchrotron X-ray data from Al2O3*, doi:10.1107/S0021889887087090 (physics:docs/dev/index.md).
