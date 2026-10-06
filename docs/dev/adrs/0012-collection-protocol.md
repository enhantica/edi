# ADR-0012 — The R15 collection protocol: live keyed views over shared-item storage

- **Status:** Accepted
- **Date:** 2026-09-22

**Amended ([ADR-0016](0016-collection-owned-loop-ids.md)):** an item belongs to at most one collection — adding
an item another live collection holds is refused, so §1's reference identity holds inside ONE collection; `add`
keeps its upsert semantics.

**Amended:** a detached item is observably detached. Its parameters'
`is_attached()` is false and their Python handles refuse writes, as crysta's row handles do (§1).

**Amended:** an optional parameter of a one-row category (a peak profile slot, an instrument shift, an absorption
coefficient) has the same lifetime. It lives in its own cell (`OptionalParameter`), and clearing it, by a profile
switch or by assigning `None`, keeps the cell detached for as long as its category lives: a handle to it keeps its
last values and refuses writes, and never reaches a parameter engaged later in the same field.

**Amended ([ADR-0018](0018-one-column-table-for-every-category.md)):** a collection is a table. A collection
stores the cells of its items in typed value columns (ADR-0018 §1), and an item keeps a read image of its cells,
which a reference to a cell names. While a collection holds the item, each write to one of its cells also writes
that collection's column and raises its generation; an item that several unkeyed collections hold writes and
raises each. A removed item keeps its values, and its row token is not reused (§1). The item objects, their
addresses, their shared ownership and every reference to a cell of theirs are unchanged.

## Context

edi's model collections were bound as `def_rw` over `std::vector`, so every Python read
materialised a detached list of copied elements: `project.structures.append(...)` mutated a copy
and vanished, and so did every mutation through a copied element, including the ported
tutorials' own
`for point in experiment.background: point.intensity.free = True`. The measured class boundary
was exactly five sites — `structures`, `experiments`, `atom_sites`, `background`,
`excluded_regions`; everything below them was already live (the S13 write-through convention).
Upstream diffraction-lib at anchor `0ffba46f` defines the collection contract this repo mirrors.
Prior art brought to one design: crysta's pointer-list `structures` view, edi's `model_views.hpp`
lens plane, and upstream R15.

## Decision

1. **Item storage is shared, copies are deep.** The four item vectors hold
   `std::shared_ptr` items through `ItemVec<T>` (`core/include/edi/model.hpp`): reference
   identity *inside* one live collection (a stored item IS the caller's object; a removed item
   survives while held, detached), value semantics at every *native copy seam* (`ItemVec`'s copy
   operations deep-clone, so `Project probe = model` — the committed
   `adapter.cpp::validate_index` consumer — keeps its isolation). The item types inherit
   `std::enable_shared_from_this` so the binding's shared_ptr casts co-own the object instead of
   pinning its Python wrapper inside the collection. *(Amended, crysta: a removed item survives while held,
   **detached**, and says so. Its parameters keep their last values; `is_attached()` is false; their Python
   handles refuse writes, both a parameter's own setters and assignment into its slot. The collection sets and
   clears a row link beside the ADR-0016 membership record, and a Python handle reads it through the parameter's
   category, so a parameter engaged after insertion answers too. An item no collection ever held is not detached
   and stays writable. A removed item added back is attached again: edi items are shared objects (above), where a
   crysta row is a value with a fresh anchor.)*
2. **The keyed categories carry the R15 protocol as upstream spells it.** `structures` (key
   `name`), `experiments` (key `name`), `atom_sites` (key `id`) are live keyed views
   (`lib/src/collection_views.hpp`, registered in `bindings.cpp` as `Structures`,
   `Experiments`, `AtomSites`) with `add`, `create`, `remove`, `clear`, `keys`, `values`,
   `items`, `names`, `[]`, iteration, `in` and `len` — anchor-exact semantics: string lookup
   resolves the **last** duplicate, `add`-replacement and `remove` act on the **first**; missing
   keys raise `KeyError`, out-of-range ints `IndexError`, other key types `TypeError`; mutation
   verbs return `None`; `keys`/`values`/`items` are lazy iterators over live storage; `names` is
   the anchor's **list** — `list(self.keys())`, a fresh projected snapshot of immutable keys on
   every read, so mutating a snapshot never reaches live storage and a fresh projection ignores
   it. `Experiments.create` delegates to the committed Python
   `ExperimentFactory.from_scratch`.
3. **The unkeyed vectors stop being copies without becoming keyed.** `background` is a live
   positional view (R12: the upstream id is adapted to list position) with its replacement
   setter kept as the population verb until; `excluded_regions` reads as an immutable tuple
   of pairs with its replacement setter (item form is deviation D8's own task).
4. **`append`, every Python-list mutator, and wholesale assignment to a keyed collection are
   unspellable** — `AttributeError`, asserted by gate, not assumed.
5. **Lifetime is a decidable two-direction rule.** Every borrowed object keeps its immediate
   lender's wrapper alive (`nb::keep_alive<0,1>`: owner→view, view→iterator; items and
   `Parameter` leaves ride shared ownership / `reference_internal`), and no lender retains a
   borrower — falsified per edge by dead-`weakref` (collection→item) or lender-refcount-delta
   restoration (every edge with a retention backedge), per ADR-0013's instrumentation bounds.

## Consequences

- The construction path `Project(structure, experiment)` is RETIRED: construction is
  `Project(name=…)` on top of this protocol, and population goes through the collections (whose
  singular
  `structure`/`experiment` setters keep the copy-in value isolation).
- A collection mutation never invalidates a held item or leaf; a long-lived view keeps its owner
  alive — retained-reference semantics, not dangling pointers.
- The copy-out/mutate/write-back idiom (`examples/fit_lbco_hrpt.py`) is retired: mutations
  through views reach the model directly.
