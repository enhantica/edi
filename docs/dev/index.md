# Developer documentation

edi's **specification** corpus — the binding, reviewed record of *what edi is and how it
is built*. This is a **product & architecture** spec: the compute physics lives in the
org-private physics knowledge book, consumed through the crysta
engine boundary (ADR-0003).

## Contents

- **[Feature catalog](features.md)** — the capability record per surface
  (LIB · CLI · APP · WEB — the diffraction-lib layout), each row tied to its milestone.
  The user-facing [Features](../user/features.md) page is generated from this record at
  build time.
- **[Architecture Decision Records](adrs/index.md)** — the binding decisions, each a
  `NNNN-slug.md` with Status · Date · Implementation · Priority. This is where edi's
  architecture is actually fixed; read the relevant ADR before a structural change.
- **Architecture & design** — the narrative rationale:
  [architecture & upstreams](design/architecture-and-upstreams.md), the
  [user-facing API design](design/api-types.md), and the
  [modern-Qt guidelines](design/modern-qt-guidelines.md).
- **[Requirements coverage](requirements/rwg-edi-coverage.md)** — the RWG requirements
  split by owner (edi vs crysta).
- **[Verification notebooks](verification/index.md)** — executable FullProf-parity
  pages; they live beside their reference data and the tests that assert on them
  (their FullProf reference data stays at `knowledge/verification/fullprof`, beside the tests that assert on it).

## What this spec is *not*

It does not re-document diffraction physics, profiles, structure factors, or minimizer
math — those are the physics book's. When edi needs to reason about a physical quantity
that crosses the engine boundary (e.g. the `.edi` format, a parameter's unit/convention),
it does so in a **conventions/format seam table** in the relevant ADR or task packet,
cross-referenced to the spec it rests on — not by re-deriving the physics here.

## Growth

The spec grows as the product design firms up: new binding decisions become ADRs; a
capability that sequences several ADRs becomes a milestone.
