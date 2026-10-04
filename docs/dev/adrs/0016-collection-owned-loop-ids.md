# 0016. Collection-owned loop ids: every loop category's ids are unique by construction

- **Status:** Accepted
- **Date:** 2026-09-29
- **Implementation:** ✅ Implemented
- **Priority:** High
- **Forward constraint (binding on new features):**
  - A new loop category declares its identity column in the loader's identity table.
  - If a category's ids are stored, its items carry an `ItemKey` inside an `ItemVec`. The id is a cell of the
    table's id column (ADR-0018), and the row type has a `crysta::RowSchema` whose first field is the id.
  - Any file named from an id is composed only by `entity_path`: crysta's decision, reached through the adapter.

**Amended by (the edi side of its ADR-0071 amendments):**

- **Row links (item 4).** Beside the membership record, each collection sets a row link on every row it holds and
  clears it on removal. The background is included: every collection now has a record, keyed or not. A removed row
  is detached, and its parameters' Python handles refuse writes (ADR-0012 §1 as amended).
- **Writes (item 2).** crysta makes every model field writable only through a stamped mutator. edi builds a fresh
  engine project from its items for every calculation, fit and save, so each edi write reaches crysta's write
  boundary by construction. *(ADR-0018)*
- **Currentness of the computed categories.** A calculation records, per experiment, what it was calculated from:
  the injective encoding of every calculation input (every structure, the experiment's parameter values, settings,
  background and excluded regions, and its data node's grid and measured columns; never a parameter's uncertainty
  or free flag, as crysta's computed-input table rules), the identity of every object among them, and the
  collections that held the experiment and the structures. Each row, category, structure, experiment and data node
  carries an identity (`detail::Epoch`) that a copy does not share and an assignment renews, so replacing one, or
  assigning it whole, is a write even when every value is equal. A data object the Python `data` getter hands out
  writes through to the experiment node it came from, while that node is still in place, as diffraction-lib's live
  `data` category does; a written data object drops its own computed columns.
- **Every admitted write, and every retained view.** An admitted write to an input stales the categories it feeds
  whatever value it leaves: a Python write to an input attribute of a model object,
  `assign_value`, and a measured or axis column write each renew the written object's identity (its parameter, row,
  category or data node), so only the banks that read that object go stale. A write to a non-input (a parameter's
  uncertainty, free flag or fit start, a bank's joint-fit weight) renews nothing. A data or reflection object the
  Python getters handed out reads its computed columns only while they are still its experiment's current ones, so
  a retained object never presents an earlier result after an edit, a refusal or a recalculation. A save writes a
  bank's computed categories exactly when that bank's live ones are current.
- **The app's one write door.** Every edit the app admits runs through `ProjectEditor::apply`, which calls
  `Project::note_edit()` after the change succeeds. That renews the project's edit record, which every calculation
  records, so any GUI edit — any field, equal value or not — stales every bank's computed categories until the
  recalculation the editor then queues. No per-setter renewal exists to forget. A model write that bypassed the door
  would also skip the editor's publish and recalculation, which is the D4-D5 contract; the value record still
  catches any value it changed. The computed `data` columns and `refln` are read only while that record still
  matches (`ExperimentBase::computed_current()`): the Python `data` and `refln` getters, the app's pattern and save
  all read through it. A write by any route therefore never leaves an old result readable, and needs no hook of its
  own. A refused calculation clears every experiment's computed categories.
- **`_refln` (item 6).** The reflections are a computed category edi carries from crysta as `experiment.refln`.
  Their ids are positional, the row ordinal, as crysta writes `_refln.id`. An imported file's own loop stays read-only
  carriage.

Ids, the uniqueness predicate and the file plane are unchanged.

**Amended, unit 0:**

- **A Python read of a computed column calculates.** Reading a computed `data` column or a `refln` column is a value
  read. When the experiment's computed categories are not current, the read calculates them through the project that
  holds the experiment (`ExperimentBase::ensure_computed`) and returns the current columns. It no longer reads empty.
  A failed calculation raises and returns no earlier numbers. An experiment no project holds raises, since it can
  neither prove its categories current nor calculate them.
- **How an experiment reaches its project.** The project marks its `experiments` collection as its own
  (`Project::adopt_experiments`; `calculate()` and the Python accessors call it). The mark belongs to the collection
  object: a copied or moved project's collection starts without one, so it is never a dangling pointer.
- **The app is unchanged.** It reads through `computed_current()`, which never calculates, and recalculates on open
  and after each edit through its one write door.
- **No file records provenance.** crysta no longer writes `_edi.calc_fingerprint` or `_edi.calc_version`, so no edi
  file or Text view carries them. A saved computed column that edi loads is never current.

**Amended: edi reads the computed structure categories and computes none.**

- **One read.** `structure_geometry(structure, window)` in the adapter hands crysta the structure and a view window
  and shares crysta's buffers for the four categories: the operator list, the symmetry-expanded atoms, the bonds and
  the cell's Cartesian frame. edi contains no expansion, bond, distance or Cartesian arithmetic. The view window is
  edi's view state; crysta stores none.
- **The stored result and its currentness.** A structure keeps its unit-cell result with a record of what it was
  computed from: the encoding of every geometry input and of the identity of each object among them, the mechanism
  this ADR's amendment set for the pattern categories. The inputs are crysta's (ADR-0074 §7): the space group, the
  six cell values, the site rows with each site's id, type symbol, ADP type, coordinates, occupancy and ADP, and
  `geom`. The structure's name, its scattering lengths, a site's Wyckoff letter and every experiment field are not
  among them, so a write to one leaves the geometry current and a save still writes it. For that reason the
  project's editor transaction record is not part of the geometry's record: it renews on every app edit, whichever
  field it writes. `Project::calculate()` fills the result. A Python read of a category calculates when it is not
  current. A copy is never current.
- **Every geometry input records its own writes.** A parameter's value (`detail::Written<double>`), the space
  group's name and code and a site's type symbol and ADP type (`detail::WrittenText`), a site's id (`ItemKey`),
  `geom`'s two values, and the site collection (`ItemVec::generation`, renewed by every mutator) each take a new
  write identity on every assignment or mutation, and the geometry's record encodes those identities. So an
  equal-value write, a self-assignment, a whole-object assignment, removing a row and adding the same object back,
  and assigning the same pointers in the same order all stale the geometry, from native code, from Python and from
  the app alike: an input has no write that leaves its identity. The fields read as their plain types.
  The collection keeps its items and that identity in one private store whose only non-const access renews the
  identity, so a mutator cannot change the items without recording it; a collection assigned to itself, by copy
  or by move, changes nothing and records the write explicitly.
- **A held category.** In Python the object a `Structure.<category>` read returns holds the geometry it read. It
  never changes under its holder; the next read of the property returns the then-current one. The loops' `id` and
  the bond loop's two `expanded_atom_site_id` columns are integer arrays, as in crysta.
- **`geom`.** `Structure::geom` holds the two bond cutoffs, presence-tracked. It is an input of the structure
  categories and of nothing else, so a cutoff edit stales no pattern.
- **Saving.** The delegated save writes the structure's computed categories exactly when edi's are current, as it
  does for a bank's.
- **Loading.** A structure file with the computed loops loads; the loops are not read and are never current.

**Amended by ([ADR-0018](0018-one-column-table-for-every-category.md); crysta):**

- **Item 2, and the statement that edi's items are plain value types.** An `ItemVec` is a column table: it stores
  the cells of its rows in typed value columns. An item is a row's handle, a set of cell views that keep a read
  image of the row's cells and write each change to the columns of every table that holds the item. Its id is the
  cell of the id column. Access, the checked mutators and their guarantees are as item 2 states them.
- **Writes.** A cell of a loop row changes only through its view's routes, and each records the write. edi still
  builds a fresh engine project for every calculation, fit and save. The plain members of non-loop categories are
  as they were (ADR-0018 §5).
- **The identities of the amendment are stamps.** A geometry input's write identity is the stamp of its cell, and
  the site collection's is the table's generation: the newer of `ItemVec::generation()` and the newest stamp of
  any cell the table holds. The geometry's record reads the same identities from those stamps, and every write
  that staled the geometry still does.

## Context

The owner ruled on 2026-09-28 that *"every loop category has id field with unique IDs"*. The first attempt gave `ItemVec` a raw sibling back-pointer
(`SiblingLink`), set on insertion, and checked keys in the parser and the id setters. Its round-5 review found:

- the link dangled after a remove, a clear, the owner's destruction or a failed assignment, and described only one of
  several collections holding a shared item;
- uniqueness was bypassed by the singular setters, native copies, counted construction and the mutable `Ptr&`
  slots;
- quoted ids were decoded twice.

The breaker reverted it. designs ownership as one mechanism shared with crysta.

## Decision

1. **Ownership.** *An item's id belongs to the collection that holds it: a detached item's id is free, an attached
   item's id changes only through its collection, and the collection admits an insertion, replacement,
   whole-collection assignment, copy or rename only if every id in the result is unique — otherwise it refuses by
   name and changes nothing.*

2. **`ItemVec<T>` is the keyed collection.** It stores `structures` (key `name`), `experiments` (key `name`),
   `atom_sites` (key `id`), `preferred_orientation` (key `structure_id`) and the extract rules (key `id`).
   - **Private storage.** Access hands out `const Ptr&` and const pointer iterators, so a slot cannot be reseated
     from outside.
   - **Checked mutators.** `add`/upsert, `replace_at`, `assign`, `erase_at`, `clear` and the copy and move
     operations each validate the candidate result before they commit.
   - **A mutator that throws changes nothing** — a refusal or an allocation failure alike. The clones, the
     candidate storage and the membership record are prepared before the commit, and neither the commit nor the
     attachment can throw.
   - **No counted constructor for keyed types.** `Project()` builds one explicit default item per collection
     instead.

3. **The item's id — `ItemKey`.** It is the item's first data member.
   - It reads as a `const std::string&`.
   - Assigning a string or another `ItemKey` is a rename, checked while the item is attached. So the Python setters,
     the singular `project.structure` / `project.experiment` setters and a C++ whole-item assignment all reach the
     check.
   - A copy of an `ItemKey` is detached. It has no move operations, so moving a keyed item copies it: an operation
     built from moves (`std::swap`, a moved argument) that is refused never drains the item it moved from.

4. **Membership without a weak reference (ADR-0013).**
   - **The record.** Each `ItemVec` owns a membership record that points back at the collection. Each attached item
     holds a strong share of it. The collection re-points the record when it moves and revokes it — sets the pointer
     to null — in its destructor.
   - **Lifetime.** A removed or retained item (ADR-0012 §1) can therefore outlive its collection without reaching
     it.
   - **Renames.** A rename is verified against the collection's storage. The record is a hint; the storage is the
     authority.
   - **The gate stays green.** No `std::weak_ptr` or `weak_from_this` enters production, so ADR-0013's gate is
     unchanged.

5. **One collection per item — amends ADR-0012 §1.** An item that another live collection holds is refused at
   admission. The same object can no longer sit in two collections, or twice in one: a shared item's rename could
   not be checked against both.
   - The keyed view's `add` keeps ADR-0012's upsert semantics: an item with an existing id replaces that item, which
     is detached.
   - `StructureFactory.from_dict` and every other "these are the items" path go through the collection's bulk
     assignment, which refuses an internal duplicate.

6. **The file plane.**
   - The loader's `Loop` has private fields, and its constructor checks each category's identity column(s) from one
     identity table, CIF spellings included.
   - The tokenizer decodes each token exactly once and keeps a `quoted` bit, so a quoted `'data_x'`, `'_x'` or
     `'loop_'` id is not misread as a control token.
   - A decoded identity value outside the single-line printable-ASCII domain is refused at load.
   - edi's writer is crysta's (the delegated save). Its encoding, its save preflight and its create-new entity
     writes cover edi's projects.

7. **One naming policy for files.**
   - **Core.** edi core's `entity_path` is defined in `adapter.cpp`, the one crysta contact, as a call into crysta's
     `datablock_key` and `entity_path`. edi's saved-text reader uses it.
   - **The Python CLI.** edi's calc writer (`lib/edi/__main__.py`) uses it through the private binding
     `edi._entity_path`. There is no Python re-implementation and no public name. It resolves every experiment's
     target before writing any.
   - **The save shell** keeps its multi-structure and `.[]` refusals, which serve edi's identity-path grammar.

8. **Prior art subsumed.**
   - The dead `validate_identities` is deleted.
   - These helpers delegate their duplicate refusal to the collection: `rename_atom_site`,
     `rename_scattering_length` and `rename_experiment`, and `load_experiment_edi_files` and
     `add_loaded_experiment`.
   - So does the duplicate-name clause of `validate_joint_request`. Its other refusals stay.

## Consequences

- **The compiler enumerates native bypasses.** A new native way to write an id either reaches the collection's check
  or does not compile.
- **A behaviour change:** adding an item another collection already holds now refuses; add a copy instead.
- **The app compiles unchanged, with two exceptions.** Two Text-tab lines compose saved-file paths themselves and
  must call the core path function. They are coordinated with.
- **Saves of a redundantly quoted id** re-spell it canonically, with its value unchanged, as edi already did. This is
  reported against gate 6, not waived.

## Alternatives considered

- **The reverted `SiblingLink` raw back-pointer** — rejected: it dangled and could not describe shared
  membership.
- **A `weak_ptr` membership handle** — rejected by ADR-0013; the revocable strong record gives the same lifetime
  property.
- **Keep shared membership and link every owner** — rejected: several owners' uniqueness would need every owner
  consulted, and admission by copy was never the caller's intent. Refusal is explicit.
- **A Python copy of crysta's naming allow-list** — rejected: two naming policies drift apart. The private binding
  bridges to the one native decision.

## Published sources

- *CIF 1.1 file syntax*, International Union of Crystallography, paragraphs 14–18 and 22–25
  (https://www.iucr.org/what-we-do/digital-standards/cif/cif1/file-syntax).
- Python documentation, *pathlib — operators* (https://docs.python.org/3/library/pathlib.html#operators): an absolute
  right operand replaces the left, which is the CLI escape the one path decision closes.
