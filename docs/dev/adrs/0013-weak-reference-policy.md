# ADR-0013 — Production weak references are prohibited; the flag is test instrumentation

- **Status:** Accepted (*"weak references are TEST INSTRUMENTATION ONLY, prohibited in
  production, and the prohibition gets an ADR"*)
- **Date:** 2026-09-22

## Context

Neither edi nor crysta has ever needed a weak reference: before the collection protocol,
`is_weak_referenceable`, `weak_ptr` and production `weakref` counts were zero in both repos'
sources. The collection protocol's lifetime rule (ADR-0012 §5) needs one falsifying
observation that a lender never retains its borrower — and for exactly one ownership edge,
`collection→item`, the borrower carries no retention backedge, so a dead-`weakref` check is the
only instrument in the reconsidered inventory that observes its release (plan reviews 5–6:
every other edge is falsified by lender-refcount-delta restoration at **zero** production cost,
so no other class carries the flag). The owner's question — *"if we did not use weak references
until now, why can it be needed in future?"* — makes the honest position prohibition, not
documentation.

## Decision

1. **Production weak references are prohibited** in edi (and, as the shared policy, in crysta):
   production ownership is `shared_ptr` + `keep_alive`. Any future production need argues its
   own ADR — never a precedent read off this one.
2. **The enumerated test-instrumentation classes, with per-class necessity** —
   `nb::is_weak_referenceable()` appears on exactly these `nb::class_` registrations in
   `lib/src/bindings.cpp` and nowhere else:
   - `Structure`, `BraggPdExperiment`, `AtomSite`, `LineSegment` — the four collection item
     classes: the `collection→item` edge's borrower holds no lender reference by design
     (shared_ptr lifetime independence), so refcount restoration is blind there, the C++ object
     rightly survives wrapper release (destructor counters blind), and a static shape rule
     cannot observe runtime retention — dead-`weakref` is the only falsifier.
   - **No other class**: `Parameter` (the hottest wrapper class), `Cell`, the family lens
     nodes, the views and the iterators all carry retention backedges, so the zero-cost
     refcount-delta instrument falsifies them and the flag would be pure overbreadth.
3. **The true cost, stated at the pin** (nanobind 2.13.0, read from its source): a flagged
   class's wrappers gain a weak-list pointer **and** GC-managed allocation with per-lifetime
   tracking — `nb_type_new()` installs `tp_traverse`/`tp_clear` and sets `Py_TPFLAGS_HAVE_GC`
   (`nb_type.cpp:1501-1557`), `inst_new_int()` selects `PyType_GenericAlloc` over the non-GC
   path (`:79-122`), `inst_dealloc()` untracks and clears weakrefs (`:378-403`). The C++ object
   layout and ABI do not change; the cost is per on-demand Python wrapper, accepted consciously
   for the four warm item classes only.
4. **The prohibition is gated, not conventional** (`tools/checks/weakref_policy.py`, in
   `verify-quick` and `verify-full`): one parsed capability class — the Python family closed
   over the `weakref` module's import graph (any import, alias, re-export or literal dynamic
   import on a production path is red), the C++/binding family as a declared spelling table
   (`std::weak_ptr`/`boost::weak_ptr`, `weak_from_this`, `PyWeakref_NewRef`/`NewProxy`,
   `tp_weaklistoffset`, `nb::weakref`), dependency closure over the test exclusion (a
   production import/include resolving into a test path is itself red), and set equality
   between the flag registrations and §2's classes, so overbreadth is unspellable. The
   capability table is declared separately from edi's path sets, as the seam the admitted
   org-wide test-only-capability registry absorbs.
5. **Structural defence-in-depth** (not the falsifier): views and iterators hold no
   `nb::object` members and cache no wrappers. Its limit is named: a strong reference laundered
   through opaque C++ storage is syntactically unbounded, which is why the runtime falsifiers
   carry acceptance.

## Consequences

- A production feature wanting cache/observer semantics must argue its own ADR and move the
  gate deliberately — it cannot arrive by spelling.
- Test code may use `weakref` freely; the four flagged classes make the lifetime property
  falsifiable at the cost stated in §3 and no wider.
