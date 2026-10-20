# ADR-0025 — Several structures and linked structures

- **Status:** Proposed
- **Date:** 2026-10-05
- **Implementation:** 🟡 Partially implemented — the model, files, Python views and app pages for several
  structures and linked structures are built; the BEER two-phase fit agrees with CrySPY only once its reference is
  fitted without the cross-bank constraints
- **Priority:** High
- **Forward constraint (binding on new features):** a project with one structure looks, loads, saves and fits as
  before. A quantity that belongs to one phase lives on the experiment's linked-structure row or on a row keyed by
  `structure_id`. A page that shows one block of several (a structure, an experiment) uses the shared
  `BlockSelector`, and its groups keep their open or closed state when the block changes.

## Context

A multiphase sample needs one pattern per phase, each with its own scale, summed over one background. Until now a
project held one structure and each experiment linked it once. crysta calculates and fits several linked
structures (phases) by summing one single-structure calculation per phase; edi has to carry the same model in its
core, its files, its Python library and its app.

## Decision

1. **Model and files.** `Project` holds several structures, keyed by name, one `structures/<name>.edi` file each.
   An experiment's `_linked_structure` loop holds one row per linked structure: `structure_id`, `scale`, and
   `enabled` (written only when some row is disabled). A disabled row is kept and saved but neither calculated nor
   fitted, and its parameters leave the free set. Texture rows are keyed by `structure_id`, one per phase.
2. **Names.** With more than one structure, a structural parameter's path and label carry the structure
   (`<structure>.<path>`), and a phase's scale is `linked_structures[<id>].scale`. Sites with the same id in
   different structures stay apart.
3. **Python.** `project.structures` and `project.experiments` are keyed collections (keys, names, item by name or
   position, `len`, `in`, iteration). `experiment.linked_structures` is the keyed loop, with `create` and `remove`.
4. **App.**
   - The Structure, Experiment and Analysis pages pick their block with the shared `BlockSelector`: each entry
     reads `name · file`, and two square buttons with up and down arrows step to the previous or next block,
     disabled at either end. The buttons sit at the group fields' spacing.
   - Changing the shown block keeps every group open or closed as it was (`SideBarGroups`).
   - The chart draws one row of Bragg ticks per phase, in its structure's colour, with its own legend entry. Each
     phase's scale is a row of the parameter table.
   - The Experiment page's Linked structures group has the constraints table's row controls: a structure-name
     combo box, a toggle that disables the row, remove, and add.
5. **The BEER example.** The ferrite and austenite project (two phases, two banks) is a CLI project under
   `docs/user/cli/`, shown in the app's Examples list and verified against CrySPY's pattern on its own page.

## Consequences

- Single-structure projects are unchanged in every surface.
- Every phase costs a full single-structure calculation in crysta.
- A sequential or independent fit of a project with several phases is refused until it is supported.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| A separate phases collection beside one structure | Rejected: structures and experiments would follow different collection rules. |
| Dropping a disabled linked structure from the file | Rejected: disabling and enabling again would lose its scale. |
| One selector per page | Rejected: the three pages would drift apart; one component keeps them alike. |


## Ordinary phase-link edits and Undo

The FIRST Linked structures table and single-link convenience setter use the same
finite CreationAction/ProjectViewModel history seam as the original profile,
exclusion and scalar controls. Live collection membership precedes cached-row
use or equality. Retargeting requires an enabled row and an actual offered
structure, preserves its forward row/scale identity and obeys canonical duplicate
keys; removing requires another stored row. Append keeps the original first
currently unlinked structure, scale 1 and enabled defaults. Actual initial links
are intended links, never placeholders.

Every changed ordinary action prepares one narrow ExperimentControlsUndo before
the first live Edit. It owns complete linked-row images (including scale state
and per-phase fit factors), related aliases/constraints and non-replaced parameter
states, and the fit result. Restore prebuilds rows, validates related live targets,
and owns all fallible aliases/constraints/result allocation before original
no-throw collection transfers or numeric assignments. It never writes through a
scale handle that the row replacement retires. Undo may retire row/Qt parameter
handles; callers reacquire them. No-op/refusal adds no history. The core append
result's trailing linked_structure pointer identifies the actual inserted row
before publication callbacks; it is not permission to use a retired owner.
