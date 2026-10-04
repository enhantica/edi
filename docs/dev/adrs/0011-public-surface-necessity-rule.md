# ADR-0011 — Every public Python member resolves to diffraction-lib or to a justified deviation

- **Status:** Accepted
- **Date:** 2026-08-30

## Context

edi-py is public and pre-1.0, and crysta-py is its declared subset (ADR-0009). A member could enter
either surface because it was convenient to bind and stay because a test then existed for it. Three
review rounds showed that *necessity* cannot be established from consumers: every mechanical "who
calls this?" witness certified a shape a later round could defeat. The matured API the products mirror
— diffraction-lib at its anchored commit — is the base that can be resolved against.

## Decision

1. **Every non-underscore module name and every member of every class-like name carries a necessity
   verdict**, committed in `data/python-surface.json` (schema 4) beside its audience verdict:
   - `keep by=counterpart` — the diffraction-lib entity it implements (anchor `0ffba46f`), tied to
     this exact class or member by the committed entity map or the anchor's inheritance table;
   - `keep by=deviation` — a row of the deviation register that exists, is well-formed, covers
     edi and **names the member**; the packet's *defer* is such a row whose
     `closes` names a consuming task;
   - `keep by=owner` — derived, never free-standing: an enum's values and members inherited from a
     base outside the product follow their owner's verdict;
   - `remove` — deleted in the same change set, the name recorded under `removed` and asserted
     unreachable; no alias, no shim (pre-1.0);
   - `undecided` — transient: routed to the owner, red at every check until replaced.
2. **A test is not a consumer.** Nothing in the verdict machinery reads a test tier; a member kept only
   by its tests is removed with them.
3. **The gates prove resolution, not need** (`NECESSITY_LIMIT`, printed by every check): edi's
   `python_surface.py --check` proves totality; the necessity register's check proves each
   citation resolves. Whether a member is needed is the register row's judgement, written by a human
   and reviewed; whether a counterpart means the same thing is, kept by review.
4. **The validation taxonomy**: `ValidationError` and its
   `Syntax` / `Schema` / `Domain` subclasses are edi's own core types, raised by tier from the `.edi`
   loader, refining `IoError` (so is-a `ValueError`), carrying `.diagnostics` of `Diagnostic`
   (`code`, `severity`, `path`, `message`, `params`, `source`). The codes are edi's
   (`edi.<tier>.<kind>`) until the engine validator is reachable through the floated crysta
   build (`tools/ci/build-crysta.sh`); `IoError` itself remains the file-level and complete-project failure.

## Consequences

- A member added without a verdict is red at `python-surface-check` in both verify chains; a citation
  that stops resolving is red at the hub.
- `Cell.cubic` is gone; `parameters` / `free_parameters` exist on every node, `AtomSite.adp_type` and
  `SpaceGroup.it_number` round-trip, and crysta may declare the shared names.
- The record is one place: the necessity register's rows are the judgements, its generated section the
  per-member index — no parallel register.

## Alternatives rejected

- **Consumer-based necessity** (a cited path, a task id, an ast use): each certified a shape, not a
  need, as its reviews found.
- **A fourth verdict state to park removals** (`executes:`): deferred execution relabelled; refused.
- **Keeping the surface as it was and documenting it**: the owner's directive was that an unjustified
  member is removed, not described.
