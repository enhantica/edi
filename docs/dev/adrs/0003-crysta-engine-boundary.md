# 0003. crysta engine boundary (public API only)

- **Status:** Accepted
- **Date:** 2026-07-04
- **Implementation:** ⬜ Not implemented (bound in E02 when the product core — the engine-facing
  layer since ADR-0009; `edi/lib` binds the core — wraps the engine)
- **Priority:** High
- **Forward constraint (binding on new features):** edi calls crysta's **public API only** — no
  reaching into engine internals. Progress/cancel callbacks, the residual-only refinement API, and
  the undo/EditCommand primitive come from crysta; a new refinement or calculation flow binds
  through that public API, not a private symbol or a copied internal.

## Context

edi is the product; crysta is the engine (ADR-0001). If edi couples to crysta's internals, the two
repos become one tangled unit: crysta can't refactor without breaking edi, and edi inherits engine
build/version constraints it shouldn't care about. crysta already defines the seams edi needs —
EDI-driven refinement, multi-experiment joint refinement (ADR-0040), and an
`EditCommand`/transaction undo primitive (crysta's C07 goal) — as **public** API precisely so a
product layer can drive it.

## Decision

edi consumes crysta strictly through its **public API**:

1. **Calculation & refinement** go through crysta's documented public entry points
   (`free_from_model`, the residual providers, `crysta fit <project>` / its binding equivalent),
   with progress/cancel callbacks and a residual-only path for live plots. edi never re-implements
   engine physics.
2. **No internal reach-through.** edi does not import private headers/symbols, does not depend on
   engine-internal data layouts, and does not copy engine internals into `edi/lib`. If edi needs
   something the public API doesn't expose, that is a **crysta** feature request (logged, not
   worked around).
3. **The `.edi` project format is the data contract.** edi authors/saves the format; crysta reads
   it. Parity between edi's writer and crysta's loader is a tested invariant (ADR-0001 pt 4).
4. **Undo/redo uses crysta's primitive.** The `shared/` session layer's undo stack is built on
   crysta's `EditCommand`/transaction primitive when available (edi seed D3), not a parallel edi
   mechanism that could desync from engine state.
5. **Versioned dependency.** `edi/lib` depends on a pinned crysta version/API; a crysta API change
   that edi needs is coordinated as a version bump, not absorbed silently.

## Consequences

- crysta can refactor freely behind its public API; edi is insulated from engine internals.
- Some product needs will surface as crysta feature requests (a deliberate, healthy pressure that
  keeps the engine's public API complete) rather than edi hacks.
- The `.edi` writer/loader parity test is a standing obligation shared across the two repos.
- For WASM, edi consumes crysta's WASM build through the same public API (crysta C28), so the
  boundary holds on every surface.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Vendor/copy engine internals into edi for speed of delivery | Recreates the tangle ADR-0001 dissolves; every crysta change risks breaking edi. Rejected. |
| edi re-implements a thin calculator to avoid the crysta dependency | Duplicates physics that crysta exists to own; guarantees drift. Rejected. |
| Build the undo stack independently in edi | Risks desyncing from engine state; crysta's EditCommand is the source of truth for model edits. Deferred to the engine primitive (D3). |

## Published sources

- nonlinear least-squares minimization across the engine boundary — Donald W. Marquardt, *An Algorithm for Least-Squares Estimation of Nonlinear Parameters*, doi:10.1137/0111030 (physics:docs/dev/08-refinement-minimization.md).
