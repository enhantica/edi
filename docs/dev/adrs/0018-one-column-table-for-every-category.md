# 0018. One column table for every category

- **Status:** Accepted
- **Date:** 2026-10-02
- **Implementation:** ✅ Implemented (the item tables on crysta's columns and anchors, the cell views, the tables
  behind the aggregate cells, the measured columns, the schema of every category with its one-row table view, and
  the census)
- **Priority:** High
- **Forward constraint (binding on new features):**
  - A new category gets one schema in `core/include/edi/model.hpp`, and `tools/checks/category_census.py` must
    find it. A loop of items is an `ItemVec<Row>` whose row type has a `crysta::RowSchema<Row>`.
  - A cell of a loop row is a cell view: `ItemKey`, `detail::Written<T>`, `detail::WrittenText` or `Parameter`. A
    plain member is a cell of a non-loop category only.
  - edi builds its tables from crysta's `detail::AnchorList`, `RowSchema<Row>`, `Column<T>` and
    `detail::AggregateTable<T>`. It adds no second column or anchor implementation.
  - A loop table stores every cell of its rows in a typed value column, `crysta::Column<V>`, and the census
    reads that from the table class. A row's item keeps a read image of its cells, and every write keeps the image
    and the row's column cells equal.

## Context

The owner decided on 2026-09-30 that every category is a table (the visualisation plan's data-contract points
01–05). crysta decides the form in its ADR-0075, "One column table for every category". This ADR is edi's side
of that decision, built.

Before it, edi stored a loop category as a vector of shared item objects, each with its values in place, and four
other loop categories in standard containers: a map, a vector of pairs, plain vectors and string rows. A non-loop
category was a set of plain members with no name in code.

Two earlier decisions bound the form. review 1 required that `ItemVec<T>` stays the class it is. review 2
required that a native contract which can be preserved is preserved; the conductor's record of 2026-10-01 allows
a member's C++ type to change where a plain member becomes a cell of a loop table, with every in-repo caller, and
no Python name, value or setter behaviour changes.

## Decision

The five parts of the data contract (the visualisation plan's points 01–05) are §1–§5. §6–§9 are what follows
from them in edi.

### 1. One storage form (point 01)

Every category is a table: a schema that names its columns, a token for each row, a generation, and cells with
stamps. A non-loop category is a table of one row, whose cells stand in the object that owns it (§7).

**Where the cells of a loop row are.** In the table's columns. A loop table has one typed value column,
`crysta::Column<V>`, for each column of its schema: numbers, optional numbers, flags (as bytes), integers and
strings; a parameter is five columns. A column holds its cells in one contiguous array, in row order
(`ItemVec::column`).

**What the row's item is.** An edi row is a shared item object (ADR-0012 §1): the row's handle. It keeps a read
image of the row's cells, and a read by reference returns the image. A write to a cell writes the image and the
cell's column in every table that holds the row, in one step, so the two never differ. The image is to a row what
`get()`'s image is to a cell that holds a whole loop (below): the table is the storage, and the
image is what a held reference names.

The image is there because two contracts that this ADR keeps need it. A caller may hold a `const T&` that a cell's
read returned for as long as it holds the item: before a collection takes the item, while it holds it, and after
it removes it. And an unkeyed collection admits an item that another collection holds, and the same item twice
(ADR-0012 §1). A value that lived only in a table's column would move when its row is taken or let go, and it
could be in one table only. With the image, a row's cells are in the columns of every table that holds the row,
and a reference to the image outlives them all. crysta's loop rows live and die with their table, so its row
objects keep no image.

**What is crysta's, and what is edi's.**

- From crysta, in the SDK's headers: `crysta::detail::AnchorList` gives each row its token and anchor;
  `crysta::RowSchema<Row>` names a row type's columns; `crysta::detail::AggregateTable<T>` and `crysta::Column<T>`
  are the table behind a cell that holds a whole loop.
- From crysta too: `crysta::Column<V>` is every value column of a loop of items, with its copy-on-write buffer.
- edi's own: the row types, the cell view `detail::Written<T>`, the stamp policy, which columns a cell field has
  (`detail::FieldColumns`), and how a row's cells reach the columns of the tables that hold it (`detail::RowHold`,
  `detail::TableNotes`).

**The cell views.**

`detail::Written<T>`, `detail::WrittenText` and `ItemKey` are cell views, and a `Parameter` is five of them:
`value`, `uncertainty`, `free`, `start_value` and `start_uncertainty`.

- **A view of its column cell, with an image in place.** A view holds a read image of its value and the identity
  of its last write in place. While a table holds the view's row, each write also writes the view's column in that
  table at the row's position, and raises that column's stamp and the table's generation. Only a table binds a
  view to its columns. A view no table holds stands alone with its value. A copy of a held view stands alone and
  has the same value.
- **Reads.** A view offers the reads a plain member took: the conversion to `const T&`, `get()`, `->` and `*`; for
  an optional, the test in a condition, `has_value()`, `value()` and `value_or()`; for a container, `begin`, `end`,
  `size`, `empty`, `[]`, `at`, `find`, `count`, `front` and `back`; comparison and streaming. A read site compiles
  unchanged.
- **Writes.** A write is an assignment, a compound assignment, `set`, `modify`, or an optional's `reset` and
  `emplace`. Each takes a new write identity, also when the value is equal. No non-const reference to the value
  exists. `modify` hands its callback a working copy (§5). A move that takes a cell's content is a write of that
  cell too: the source of a move of a text or a container that is not empty, or of an optional that holds one, has
  a new write identity. A move copies a number, a flag or an optional number, and takes nothing from an empty text
  or container, so those sources stay unwritten. An `emplace` whose construction throws leaves the optional empty,
  and records that.
- **Stamps.** A stamp is a `detail::Epoch` value: process-wide, never reused, and new on every copy.

**A loop of items.**

`ItemVec<T>` is the table class of `_atom_site`, `_background` (a type-switched category with two
row tables — `background`'s `LineSegment` points and `background_terms`' `PolynomialTerm` terms — and one selector
schema, `BackgroundCategory`; crysta), `_preferred_orientation`,
`_sequential_fit_extract` and the structures and experiments collections. Its public interface is unchanged: `Ptr`,
`const_iterator`, `const Ptr&` access, the constructors, copy and move, every mutator, `record()`, `generation()`
and the `KeyedBase` base.

- **The table.** A collection holds its value columns, its anchors, the stamp of each column and a hold record for
  each row in one heap object, which does not move when the collection does. It is the owner crysta's anchors
  name, and its columns are what its rows' cells write.
- **Taking and letting go.** A change of the rows gathers the value columns of the result from the rows' images
  before anything changes, and installs them at its commit, which cannot fail. A taken row's cells write to the
  table from then on, and a row the table lets go no longer does. Neither moves an image or is a write of a cell.
  A removed item is a standalone row with its last values (ADR-0012 §1), and its token is not reused.
- **A row that several tables hold.** An unkeyed collection admits an item that another collection holds, and the
  same item twice, as before. The row is then in the columns of each of them, once for each time it is held: a
  write to one of its cells writes every one of those positions and raises the generation of every table that
  holds it, for as long as that table holds it. A keyed collection still refuses an item another collection holds
  (ADR-0016).
- **Generation.** The table's generation is the newer of its structural identity (`ItemVec::generation()`, renewed
  by every mutator) and the newest write identity of any cell of a row it holds.

**A loop that one cell holds.**

`Structure::scattering_lengths_fm`, `ExperimentBase::excluded_regions` and a carried loop's `columns` and `rows`
are `detail::Written` cells that hold a whole loop. Each has that loop's table behind it (`table()`): crysta's
`AggregateTable` for the map and the vector of pairs, and string columns for the carried loop (`CarriedNames`,
`CarriedCells`). `get()` returns a read image, which the write that changes the table rebuilds. A write is an
assignment or one `modify`.

### 2. Two ways in (point 02)

- **By row.** The API hands out the item and parameter objects it handed out before. In a loop table they are
  views of the table's cells. A Python handle and the app's models reach a row as before.
- **By column.** `collection.column(&Row::field)` is the typed value column of that field for every row, in row
  order: one `crysta::Column<V>`, or a parameter's five (`value`, `uncertainty`, `free`, `start_value`,
  `start_uncertainty`). It is read-only; a write goes through the row's cell. The measured columns (§6) and the
  computed ones, which are crysta's published buffers behind `ComputedColumn<T>`, are read whole as before.

### 3. Row identity (point 03)

- Each row of a loop has a token from crysta's process-wide counter, never reused, and an anchor. A handle
  resolves its row in constant time.
- A keyed table admits an id only when the result is unique (ADR-0016). A reused id is a new row with a new
  token.
- A removed row is in no table's columns: its item is a standalone row with the row's last values, and says that
  it is detached (ADR-0012 §1).
- The one row of a non-loop category has the token of the object that owns the category (§7).

### 4. Snapshots never change, and held references stay valid (point 04)

- **A held reference.** A `const T&` that a cell's read returned names the row's image in its item, which never
  moves. So it stays valid and current for as long as the caller holds the item: across the item's admission to a
  table, a growth of the table, an erase of this row or of another, a clear, a replacement, a move of the
  collection and its destruction, and across a write to any cell.
- **A held column of a loop of items.** A reader that keeps a value column's buffer keeps those values. The
  buffer is never changed while a reader holds it: a write moves the live column to another buffer first
  (`crysta::Column<V>`), and a change of the rows installs new columns.
- **A held column.** A computed column is an immutable buffer that crysta published; `ComputedColumn<T>` shares it,
  and a recalculation publishes a new buffer and never changes one that is held. A data or reflection object that a
  Python getter handed out holds what it read and reads its experiment's current columns only while they are
  current (ADR-0016). A measured column belongs to one data node and is written in place (§6).
- **A snapshot of the model.** A copy of a collection is deep (ADR-0012 §1): its items are new objects in a table of
  its own, so a copied project never changes under its holder. Every stamp of the copy is new.
- **Currency.** A table's generation moves on every structural change and every cell write, so a holder can tell
  whether what it read is still what the table holds.

### 5. One write boundary (point 05)

A cell of a loop table changes only through its view's routes or its table's mutators, and each records the write.
A view's write is the one place where a row's image and its column cells change, together. A table's mutators
install whole columns gathered from the rows. For the plain members of non-loop categories nothing changes: a
native write through a retained reference goes through no route and renews no stamp, as before this ADR. edi's
freshness for them is unchanged: a Python setter and the app's write door renew the owning object's identity
(ADR-0016), and a category's generation still sees every changed value. Retyping them is not part of this
decision.

### 6. The measured columns

`PdDataBase::intensity_meas` and `intensity_meas_su` are `detail::Written<std::vector<double>>`, and `two_theta`
and `time_of_flight` are `detail::Written<std::optional<std::vector<double>>>`. Each is a recording cell that
holds its column's values in place, in the node. The computed columns stay `ComputedColumn<T>`, which shares the
buffer crysta published.

The vector that a read returns is one object for as long as the node lives, as the plain vector member was. So a
`const std::vector<double>&` to a column's values, `axis()` included, stays valid and current:

- through the first write to a column that was empty, and every later write;
- through `write_column`, `write_axis` and an assignment of a vector to the member;
- through a copy and an assignment of the node;
- through a move of the node, whose source keeps its own vector objects, emptied.

A disengaged axis has no vector to refer to, as an empty optional had none. A write is an assignment,
`write_column` or `write_axis`, and each records itself. The adapter hands crysta the values.

An earlier form of this decision held the measured columns as `crysta::Column<double>`. It was withdrawn: a
crysta column keeps its values in a heap buffer that does not exist before the first write and that a move
hands to the destination, so a held reference stayed empty, followed another node or dangled.

### 7. A non-loop category

A non-loop category is a table of one row. Its cells stand in the object that owns the category, so a plain
member keeps its type, its member pointer and its writable reference. Three things make it a table:

- **The schema.** A `…Category` struct names the category, its `Owner`, the members that hold its columns and the
  file item of each.
- **The token.** Each owner holds a `detail::CategoryRow` in the member `table_row`. The non-loop categories of
  one object are one row, split by category, and the token names that row in each. A copy is a new row with a new
  token. An assignment keeps the target's token.
- **The generation.** `OneRow<Category>(owner).generation()` is the canonical encoding of exactly the schema's
  columns. A cell that records its writes contributes the identity of its last write, so an equal-value write
  changes the generation. A plain member contributes its value.

A parameter block is a non-loop category with one column per parameter.

### 8. What changes for a native caller

The members below were plain and are now cells or columns of a loop table. Python is unchanged for every one of
them.

| Member | Type before | Type after |
| --- | --- | --- |
| `Parameter::uncertainty`, `start_value`, `start_uncertainty` | `std::optional<double>` | `detail::Written<std::optional<double>>` |
| `Parameter::free` | `bool` | `detail::Written<bool>` |
| `AtomSite::wyckoff_letter` | `std::string` | `detail::WrittenText` |
| `LineSegment::position` | `double` | `detail::Written<double>` |
| `PrefOrient::index_h`, `index_k`, `index_l` | `int` | `detail::Written<int>` |
| `SequentialExtractRule::target`, `pattern`; `required` | `std::string`; `bool` | `detail::WrittenText`; `detail::Written<bool>` |
| `PdDataBase::intensity_meas`, `intensity_meas_su` | `std::vector<double>` | `detail::Written<std::vector<double>>` |
| `PdDataBase::two_theta`, `time_of_flight` | `std::optional<std::vector<double>>` | `detail::Written<std::optional<std::vector<double>>>` |
| `Structure::scattering_lengths_fm` | `std::map<std::string, double>` | `detail::Written<std::map<std::string, double>>` |
| `ExperimentBase::excluded_regions` | `std::vector<std::pair<double, double>>` | `detail::Written<std::vector<std::pair<double, double>>>` |
| `CarriedLoop::columns`, `rows` | `std::vector<std::string>`, `std::vector<std::vector<std::string>>` | `detail::Written<…>` of the same two types |

`PdDataBase::write_column` and `write_axis` take pointers to the two new member types; the values are still
passed as vectors.

Four forms no longer compile on these members: a non-const reference or pointer to the plain value; an in-place
mutation of a container; an assignment through a dereferenced optional; and the old type spelled out, as in a
typed pointer to member. Every other read and write compiles as it did.

That covers the value expressions a caller wrote on the plain member. A cell forwards the const reads of the
value it holds: a container's size, element access, iteration, lookup and `data`; a string's whole const
interface, its conversion to `std::string_view` and `npos`. It compares and orders with another cell and with
whatever its value compares with. A braced list assigns as it did: a list of elements to a container
(`values = {1, 2.0}`, `values = {}`), `{}` as a new value elsewhere, and one braced value as that value. `->` on
an axis reaches its vector, as the optional's arrow did; on a cell of any other type it reaches the value the
cell holds, as before. The tests compile these expressions for every retyped member against the headers before
the move and against these.

Every class keeps its copy, move and default-construction traits, and `PdDataBase` is an aggregate as before. A
cell of a number, a flag or an optional of one copies and moves `noexcept`, as the plain member did. A cell's
default state allocates nothing, so a class that was `noexcept` to default-construct still is. The traits are
compared with the headers before the move for every class of the model.

Two forms compile and mean something else, so the compiler does not report them.

- **A cell handed to a context that needs a second conversion.** A cell converts to its value, and the value then
  no longer converts on. A braced `QList<QVariant>{row.position, …}` made a list of variants from a `double`; from
  a cell it selects the list's `(size, value)` constructor. Such a site reads the cell with `get()`. The same holds
  for a Python getter that returns a member with a deduced type, and for `def_rw` on one. The in-repo sites were
  found with a probe build whose conversions are `explicit`, and each reads `get()` now.
- **An optional cell compared with an optional.** For `cell != optional` the standard library's comparison of a
  value with an optional is the better match, and it takes the cell as the value: an empty cell compared unequal to
  an empty optional. `Written<T>` therefore defines `==` and `!=` with an optional on either side, as the
  comparison of the optional it holds. No caller changes.

### 9. The census

Each category has one schema in `model.hpp`: a `crysta::RowSchema<edi::Row>` for a loop of items and a
`…Category` struct for every other category. A schema names the category on file, its columns, the file item or
items of each, the older spellings the loader reads into it (`legacy`) and the CIF tags it is read from (`cif`).

`tools/checks/category_census.py` reads the schemas and the model classes from the source and generates
`data/category-census.json`. It refuses a model member that no schema names; a class that is neither a model
class nor listed with its reason; a schema whose storage is not a table; a category or a CIF tag in the sources
that no schema has; a non-loop category without its token or its table view; and a committed census that differs
from the generated one. It runs in `verify-quick`, `verify-full` and CI.

`_fit_parameter`, `_atom_site_aniso`, `_edi`, `_calculator` and `_rendering_plot` are categories on file that
the model does not store, and the census records each as derived, with the reason.

## Consequences

- A category has a name, a row identity and a generation in code, whatever its shape.
- An id lookup, a row handle and a table's generation do not scan the rows.
- A read of a cell is a read of the item. A write to a cell of a held row also visits each table that holds the
  row.
- Inserting or removing an item moves no value. Taking an item allocates one hold record the first time a table
  holds it.
- The SDK's headers are part of edi's build: `model.hpp` includes crysta's column, anchor and schema headers.
- A native caller of the members in §8 that used one of the four removed forms must change; no in-repo caller is
  left that does.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| A second column and anchor implementation in edi | Rejected: two implementations of one storage decision drift. |
| The cells of a loop row in the table's columns only, the item a view without an image, as in crysta | Built first, and withdrawn. A reference to a cell died when its item left the table or the table was destroyed, and went stale when the item was admitted; a row that two unkeyed tables held was in the columns of one of them only, so the other's generation missed its writes. |
| The cells of a loop row in the item only, the table holding stamps and no value | Built second, and withdrawn: a table without value columns is not the one storage form of §1. |
| Columns of handles to cells that live in the items | Rejected: the values would still be stored in the items and reached through pointers, with no contiguous column to read whole or to snapshot. |
| `ItemVec<T>` as an alias of a new table class | Rejected: an alias cannot be forward-declared, and the API tests name the class. |
| Rows by position, as crysta's row objects are | Rejected for edi: an item is a shared object that callers hold, so a cell reference would stop following its item after an erase. |
| Buffers of length one for a non-loop category | Rejected: they cannot keep the reference, `noexcept` and moved-from contracts of the members in place. |
| Retyping the plain members of non-loop categories | Not done: the record of 2026-10-01 asks for a type change only where a member becomes a cell of a loop table. |
| Sharing a measured column's buffer with crysta's project | Rejected: a shared buffer is not written in place, so a held reference would stop following the column. |
