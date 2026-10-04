# 0019. Symmetry-tied parameters: disabled on the pages, absent from the Analysis table

- **Status:** Accepted
- **Date:** 2026-10-02
- **Implementation:** ✅ Implemented —: the core query (`edi/symmetry.hpp`), the `refinable` mark on category
  fields and parameter entries, the app's disabled fields and the Analysis table's rows
- **Priority:** Medium
- **Forward constraint (binding on new features):**
  - A new kind of dependent parameter (a user constraint, an ADP or occupancy tie) is marked not refinable through
    the same `CategoryField::refinable` flag, and the pages and the Analysis table follow it without a second rule.
  - What is refinable is read from crysta's public API, never decided in edi.

## Context

The owner's feedback on the first GUI (2026-09-29): *"Symmetry fixed parameters should be disabled on
Structure/Experiment pages. And they should not appear on the Analysis page table - it only shows those which can be
refined!"* The example was NaCaAlF (I 2₁3): b, c, α, β and γ were editable and listed as refinable.

crysta already knows what a space group leaves free: `crysta::cell_freedom` for the six cell parameters and
`crysta::Structure::positional_constraints` for each site's coordinates. edi's adapter used both only to complete
values (`complete_model_cell`, `complete_model_positions`). Nothing told the app which parameter is independent. A
tied parameter could be set to vary, and crysta's free-set builder then refused the fit.

The owner's rule for every dependent parameter: in the GUI its field is disabled on the Structure and Experiment
pages and its row is absent from the Analysis table. A second decision of the same day: the Analysis table's rows
follow the fitting mode.

## Decision

1. **One core query.** `edi::structure_ties(const Structure&)` (`core/include/edi/symmetry.hpp`, implemented in the
   adapter, an edi-only signature per ADR-0003) returns one row per cell parameter and per site coordinate: the
   parameter, whether it is independent, follows another or is fixed, the parameter it follows, and the constant it
   is fixed to. It reads the two crysta calls above. For a coordinate, the first axis that names a free coordinate
   of the special position is the independent one and a later axis of the same one follows it, which is the rule
   `complete_model_positions` already applies. Occupancy and the ADP have no row: they are not symmetry
   quantities in edi today.
2. **A part crysta cannot resolve is reported independent.** An unknown space group, or a site crysta cannot place,
   leaves every field of that part editable. The calculation refuses such a structure with its own message, and a
   page that disabled the fields could not be used to repair it.
3. **Categories carry the mark.** `CategoryField` and `ParameterEntry` gain `refinable`. `structure_categories`
   sets it from the query; every other field is refinable. `parameter_entries` still returns every shown parameter,
   because the pages bind them all; a listing of what a fit can vary takes the entries that carry the mark.
4. **The pages show a tied parameter disabled, with the value symmetry implies.** `ParameterItem.refinable` is false
   for it. `ParameterField` and `ParameterCell` are then disabled: no typing and no vary toggle. A write that
   arrives anyway is refused with a message. The value shown is the model's: after a project opens and after every
   edit the app completes each structure through `complete_model_cell` and `complete_model_positions`, so a tied
   cell length shows its leader's value, a fixed angle its constant and a tied coordinate its special-position
   value. A space-group edit changes the marks and the values in the same step.
5. **The Analysis table lists what a fit can vary.** A parameter whose mark is false has no row. The counts in
   the status bar and in the report are the table's, and both change in the same step as its rows: the status bar
   binds the table, and the report, which keeps its composed text, is refreshed whenever the rows are re-derived.
6. **The Analysis table follows the fitting mode.** In a joint fit it lists every experiment's parameters. In a
   sequential or an independent fit it lists the structures' parameters and those of the experiment selected in the
   shared experiment selector, and follows the selector. A single fit lists everything. The mode is the project's
   (`_fitting_mode.type`).

## Consequences

- The refinable set a user sees equals crysta's independent set, so a fit started from the GUI no longer refuses a
  free flag the GUI offered.
- A project whose file carries a tied value that differs from the implied one (a coordinate written `0.3333`) shows
  the implied value once opened, and a save writes it.
- A free flag a file sets on a tied parameter stays in the model; the field shows the parameter disabled and not
  varied. Warning about that flag and ignoring it in a fit is work.
- In a sequential or independent project the status bar's parameter count changes with the selected experiment.
- User constraints and ADP or occupancy ties reuse the mark.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Remove tied parameters from `parameter_entries` | Rejected: the pages bind one item per shown parameter, and a tied field is shown. |
| Compute the implied value in the app from the leader | Rejected: a tied coordinate can be a signed or offset image of its leader; the completion helpers already hold that rule. |
| Disable every cell and coordinate field when the space group does not resolve | Rejected: the user could not repair the structure. |
| Keep the scope filter in the table's name filter (the proxy) | Rejected: the status bar and the report would count rows the table does not show. |
