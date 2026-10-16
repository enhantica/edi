# 0024. Parameter aliases and constraints: crysta decides, edi keeps the text

- **Status:** Accepted
- **Date:** 2026-10-05
- **Implementation:** ✅ Implemented — the rows, the loader, the conversion to crysta, load-time checking,
  dependence marks, the free-flag rule, the fit write-back and undo of dependents, the Python surface, and the app's
  display of constrained parameters (ADR-0019's amendment)
- **Priority:** High
- **Forward constraint (binding on new features):**
  - edi never parses an expression and never decides whether a parameter is dependent: crysta's public API answers
    both, and a refusal carries crysta's code.
  - A new place that converts the model for crysta carries the aliases and constraints with it.

## Context

diffraction-lib names a parameter with `analysis.aliases.create(id=, param=)` and ties parameters with an expression,
`analysis.constraints.create(expression='biso_Co2 = biso_Co1')`. The CoSiO tutorial needs that tie. Its own
evaluation runs the text through an interpreter.

crysta now holds every relation between parameters in one graph: the space group's ties, the cell's, and the user's
constraints. It reads and writes the `_alias` and `_constraint` loops, parses each expression into a typed tree with a
closed grammar, orders the relations, refuses a cycle or a parameter set twice, applies the values, keeps dependents
out of the fit's free set and gives each dependent an e.s.d. from the fit's covariance. edi saves, calculates and fits
through crysta (ADR-0019 already reads crysta for the symmetry ties).

## Decision

1. **Rows.** A project keeps `aliases` (`id`, `parameter_unique_name`) and `constraints` (`id`, `expression`,
   `enabled`) as text. An omitted constraint id is the alias left of the `=`, as diffraction-lib reads it.
2. **Conversion.** Every conversion of the model for crysta carries the rows: calculation, fit (single, joint and
   scan) and save. crysta writes the loops.
3. **Checking and marks.** The loader, and every edit of the relations, asks crysta to check them. A refusal is a
   `DomainValidationError` carrying crysta's code (`crysta.domain.constraint_*`). Each `Parameter` carries a
   `Dependence` mark from crysta's graph: independent, fixed or tied by symmetry, or constrained.
4. **Free flag.** A dependent stays dependent. A loaded free flag on one is cleared with crysta's warning
   `crysta.domain.dependent_free_ignored`; setting one free warns the same way and changes nothing. crysta saves a
   constrained dependent holding a nonzero s.u. as `v(su)`, so a load reads that bracket as its s.u. and
   clears the flag without the warning.
5. **Values and e.s.d.s.** After any edit the app runs crysta's applier (`apply_relations`). A Python edit of the
   relations writes no value: it leaves the computed categories stale, and the next read or calculation applies the
   relations before it computes anything, the geometry included, and a value its range refuses refuses the read. A
   structure or parameter reaches its project through a link every collection holds: the project makes it in every
   constructor and sets it on every collection after a build or an assignment, a collection passes it to the
   structures and experiments it admits and takes it back from one that leaves, and destroying the project clears it.
   A reader checks that the project still holds what it reached. One no live project holds is set by no relation: its
   former mark is cleared and it can be freed. After a fit, the dependents' values and e.s.d.s are
   copied back from crysta by unique name, each dependent's previous e.s.d. kept in memory so undo restores it.
6. **Python.** diffraction-lib's names: `Alias` (`id`, `parameter_unique_name`, `param`), `Aliases.create(id=,
   param=)`, `Constraint` (`id`, `expression`, `lhs_alias`, `rhs_expr`), `Constraints.create(expression=, id=None)`,
   `enabled`, `enable()`, `disable()`, `show()`, and `Parameter.user_constrained` / `.symmetry_constrained`. Two
   differences: a taken id is refused (diffraction-lib replaces the row), and `Constraint.enabled` is per row, so
   `enable()` and `disable()` set every row. `create` asks crysta first; a refused row is not added. `Alias.param`
   returns the parameter as the ordinary field getters do: attached to its row and keeping its owner alive.
7. **Currentness.** The alias and constraint rows are inputs of every computed category and of stored geometry: a
   declaration write, an equal rewrite included, makes them stale, and a calculation or fit result taken before it is
   not published (`relation_inputs` in the canonical encoding, beside the calculation and geometry inputs). The
   parameters the aliases name are an expression's only sources, so their values are inputs too, and a site's Wyckoff
   letter is a geometry input because a geometry read applies the symmetry relations. The project is an input as
   well: stored geometry, a geometry window and the computed categories stay current only while their structure or
   experiment has the same owning project (or none, both times) and that project has the same alias and constraint
   lists. A first row in a list that never held one is a change, so a project that gains its first declarations, a
   structure moved to another project, and one whose project was removed or destroyed all read as stale. A
   calculation's result carries each dependent's value as its relations gave it, and publication writes those values
   with the computed categories.
8. **Undo.** Each app edit of the relations records the rows before it and every parameter state it changed. The app
   bar's Undo restores the newest recorded change, so relation edits and fits undo in the order they were made. A
   relation undo is an `Edit` built from that record (`restore_relations`), as a fit's is built from its start state
   (`undo_fit`); a parameter removed since refuses it with nothing written. A record is dropped only when its restore
   succeeds, so a refused undo keeps it, and Undo is disabled while a fit runs.

## Consequences

- One parser and one rule set serve the engine, the CLI, edi's Python surface and the app.
- The loader now refuses a project whose relations cannot hold, with the same code crysta's own loader gives.
- A project file that flags a symmetry follower free loads with a warning and saves the flag bare.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
| --- | --- |
| Parse or evaluate expressions in edi or Python | Rejected: a second parser drifts from crysta's, and an interpreter runs arbitrary text. |
| Keep edi's own cell and position completion beside crysta's applier | Rejected: two rules for the same dependents. |
| Replace a row on a taken id, as diffraction-lib does | Rejected: ids are unique within a collection everywhere else in edi. |


## Prepared bulk restore and recorded edit ownership

The prior implementations are `Edit::restore_relations`, the manual alias and constraint list editors, `ProjectViewModel::apply_relation_edit`, and the parameter table's free-flag batch. The restore prepares both complete ItemVec tables before either live move commit; resolution and all fallible membership/table admission precede the scalar and collection commit. A copied validation model is not a reservation for live table allocation.

The shared recorded-edit entrance owns the complete before declaration, parameter states, resolved parameter pointers and reserved history slot before a relation/value/free batch writes. These closed edits preserve parameter membership and names. After actual relation completion, and before presentation can signal other editors, an allocation-free pass retains exactly states whose values, uncertainty or free flag changed. A completion exception uses the same pass on the actual reached state. No post-write named-slot traversal or history growth is needed; a genuinely refused operation drops its provisional slot. Scalar assignments follow the existing RowHold numeric/optional/flag no-failure contract. This is not a promise to display diagnostics through permanent allocator exhaustion.

A true core refusal and a successful core write followed by failed presentation are distinct. The latter retains Undo, leaves an explicit applied/unconfirmed outcome and fences further edits/fits until a genuine Undo or reopening. The legacy manual editor returns empty for an actual write, with the app warning retained; the native route receives both applied and published explicitly. Undo consumes an actually applied reversal once even if its later presentation fails. It does not repeat that reversal as if nothing had happened. Existing manual alias/constraint append, duplicate, rename, target/expression change, enable/disable and removal all use this shared entrance. Native value/free batches use it too; a native batch is one normal Undo step.

Native affine declaration registration and its model-admission helper are outside this six-tool unit. Deliberately disabled manual drafts keep the ordinary editor behavior. Shared-ADP accepted-best trials, checkpoint isolation and physical site identification remain separate capabilities; none is implied by recorded parameter editing.


### Shared critical admission and explicit recovery siblings

The publication/reentrancy fence applies to every actual sibling admission, not only scalar/relation edits: report settings and their Undo, scan prepare/reset/restore and genuine fit start, data restoration, fit Undo, and save/write/readback. Critical admission is separate from displayed-dataset readiness, so scans still run from their template and save/reset policy is preserved. Only the private actual Undo entrances may recover a held publication failure; a public setting or Save cannot silently clear it. Report and scan reset/preparation own their normal Undo metadata/capacity before their existing closed file/model write doors. A completed file reversal is not repeated as a no-write refusal when its later presentation fails. Deferred same-dataset refresh revalidates the surviving owner/index and reads its latest template, never old captured model values.

A failure in Undo-availability publication retains the already prepared warning in the normal app error channel as well as the native result. Successful complete recovery clears the held cause; failed or retired presentation does not erase it. Actual UI/worker lifetime and preview pre-admission semantics are specified at the shared ADR0020 seam.


The existing scan file set-aside helper reserves its bounded moved-file ledger and recovery-path string before renaming. Recording a successful move or retaining its path therefore cannot introduce a new allocation after that move. Existing filesystem refusal/kept-aside diagnostics and restore policy are preserved; no global directory mutation or new filesystem transaction route is added.


### Native affine append through the shared editor

The app-only add_relations action uses the existing AliasListModel/ConstraintListModel representation, Edit::restore_relations, complete_relations and preowned ProjectViewModel::applyRecordedEdit/RelationsUndo. It appends actual parameter-path aliases and explicit id/expression/enabled constraints to a complete copied declaration; existing rows and composition are not replaced. The actual SDK parser/graph validates before returning the live Edit. The shared joint relation replacement and exact changed-parameter Undo remain unchanged; no rollback with guessed values or second expression parser exists. Structureless projects refuse because that existing completion seam cannot validate them. Unsupported/invalid batches refuse before mutation; postwrite presentation uncertainty keeps real Undo and the recovery fence.

This supplies a relationship mechanism for a justified same-phase co-occupied-site ADP/coordinate model. It does not decide scientific equivalence, create an automatic equality from high uncertainty, run a fit or implement accepted-best/checkpoint restoration. Explicit user no-sharing instructions and known occupancy/composition remain authoritative.
