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
   `crysta.domain.dependent_free_ignored`; setting one free warns the same way and changes nothing.
5. **Values and e.s.d.s.** After any edit the app runs crysta's applier (`apply_relations`). After a fit, the
   dependents' values and e.s.d.s are copied back from crysta by unique name, each dependent's previous e.s.d. kept in
   memory so undo restores it.
6. **Python.** diffraction-lib's names: `Alias` (`id`, `parameter_unique_name`, `param`), `Aliases.create(id=,
   param=)`, `Constraint` (`id`, `expression`, `lhs_alias`, `rhs_expr`), `Constraints.create(expression=, id=None)`,
   `enabled`, `enable()`, `disable()`, `show()`, and `Parameter.user_constrained` / `.symmetry_constrained`. Two
   differences: a taken id is refused (diffraction-lib replaces the row), and `Constraint.enabled` is per row, so
   `enable()` and `disable()` set every row. `create` asks crysta first; a refused row is not added.

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
