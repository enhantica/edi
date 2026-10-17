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

**Amended 2026-10-05 (ADR-0024):** a parameter a declared constraint sets is the first new kind of dependent. crysta's
relation graph marks every parameter with its dependence (`Parameter::dependence`), and a category field is refinable
only when its mark is independent, structure and experiment alike, so a constrained parameter is disabled on its page
with its implied value and has no Analysis row, through the same flag. The completion the app runs after every edit is
crysta's applier (`edi::apply_relations`), which replaced the cell and position helpers.

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


## Amendment: missing classic-CIF Wyckoff letters (E11-T5)

Classic CIF permits an absent `_atom_site_Wyckoff_symbol`. Previously the reader
returned empty letters and the first project save failed in engine constraints.
The shared classic reader now asks a core-private adapter helper to normalize
only absent, `?` and `.` letters before ADP completion. Explicit literals remain
unchanged, including invalid author declarations; existing validation still
owns their refusal. The dot-vocabulary project reader is unchanged.

The helper resolves the actual setting through crysta's existing resolver and
reads its public operators/table. It constructs the fractional site's complete
periodic orbit, filters table positions by that observed orbit size, then uses
`SpecialPosition::axis_basic/evaluate` against every equivalent image. A match
must also reproduce the entire orbit. Exactly one supported position must match;
zero, multiple, unsupported representative evaluation, or incomplete periodic
inverse coverage refuses. Multiplicity alone never selects a letter. Inverse
coverage is proved only for unit-sign basic axes and integral follower factors;
nonintegral followers need additional lattice branches and are refused rather
than tested incompletely. No new parser, public API, dependency or SDK is used.

Periodic comparison uses 64 times `numeric_limits<double>::epsilon()` after
reduction to a cell: a conservative short-affine-chain roundoff allowance, not
the geometry renderer's `1e-4` identity tolerance, coordinate uncertainty, or a
physical snapping distance. Independent membership and near-special controls
must qualify this new import policy. Source coordinates, SU/free/start metadata,
occupancy, ADP and space-group identity are never written by inference; only
missing letters are staged and assigned after all sites have qualified. Site
multiplicity remains engine-derived from the accepted letter/group, as before.


### WYC1: downstream representative compatibility

Orbit membership alone is insufficient: the engine uses the stored first basic
coordinates when applying the selected representative's fixed/follower axes.
Before accepting a missing letter, inference evaluates that actual parameterization
using those stored basics (first-axis sign one and offset zero, matching crysta's
`add_structure_positions`). Its result must be the same fractional point modulo
lattice translation AND have the same complete orbit. Merely reaching another
symmetry-equivalent point is insufficient: no tensor-frame transformation has
been performed. A mismatch refuses clearly as an unsupported parameterization;
the original point and all metadata remain untouched. This deliberately stages a
supported subset rather than silently canonicalizing coordinates.

For a supplied anisotropic tensor, the same existing public
`crysta::tied_components` used by ordinary ADP completion must return exactly
those components under a temporary proposed letter. A change refuses; inference
never rotates, projects or repairs a tensor. The temporary one-site engine
composition reuses `one_site_engine`, and does not mutate the imported model.
Thus ordinary completion/save/calculate/fit begin from a compatible site/frame;
future intentional refinement still follows the model's ordinary symmetry rules.
Independent canonical, equivalent-image, periodic-lift, tied/rank-reduced and
ADP-bearing acceptance/refusal gates remain necessary. The broader arbitrary-CIF
representative transformation capability remains open.


## Assistant native-result loader admission

The app-private saved-result path uses a core-private `load_assistant_project` entry in `core/src/assistant_project_io.hpp`. It reuses `io.cpp`'s actual grammar and model builders, requires embedded measured data before generated-axis allocation, and refuses external scan/report declarations before materialization. Public factory/directory-loader behavior and scientific values remain unchanged. The caller first bounds and seals the exact native file set; this entry adds no independent parser, science inference, public Python API or new engine dependency.


## CIF punctuation is not an Edi schema declaration (2026-10-16)

The native create helper uses the shared structure-from-text API. Genuine upstream LBCO487B CIF uses dotted cell, space-group and atom-site dictionary names without an Edi schema. The old dot-cell predicate selected the strict Edi builder and refused the schema before reading scientific input. Supported CIF aliases now normalize in the existing parsed Block and reuse the classic structure builder, including its B/U/aniso handling and supported Wyckoff inference. No schema tag, parser, scientific literal or Python path is invented. Explicit Edi schema/native-only identities still select the strict native builder, preserving missing/unsupported-schema refusal. Repeated aliases refuse across scalar and loop declarations rather than choosing one value. The supplied coordinate-system code/IT number remain declared metadata.

This extends shared factory prior art. The Edi-only file loader remains Edi-only. Qualification must reach the original487B input through native creation and cover classic/schema/alias/setting siblings; source preparation does not establish runtime or arbitrary-CIF support.


The structure-from-text CIF normalization also owns CIF data-name case: [IUCr CIF1.1 file syntax, section26](https://www.iucr.org/what-we-do/digital-standards/cif/cif1/file-syntax) specifies case-independent identifiers while requiring value case preservation. Supported classic and dotted names now share ASCII-folded lookup keys and return the existing reader's exact canonical spelling, including mixed-case H-M, Wyckoff and ADP columns. Existing optional geom aliases use the same path. Every declaration's folded canonical identity is checked across scalar/loop boundaries before selection; case or punctuation aliases cannot silently choose a value. Unknown names are not promoted to supported fields, though repeated case variants still refuse. Block name, raw values, labels, symbols, literals, row order and uncertainties are copied unchanged. Reconstructed immutable Loops still execute their one actual identity-validation constructor.

Explicit native/schema-only markers are detected regardless of tag case and sent unchanged to the strict native builder, so alternate casing cannot downgrade a malformed native file to CIF. This does not make the native file/directory grammar case permissive, rewrite tokenizer/reserved words, broaden experiment import, or invent chemical metadata. Original owner bytes remain untouched; genuine original/native creation plus scalar/loop/ADP/geometry/duplicate/strict-schema siblings require independent qualification.


### CIF alias identity includes supported legacy replacements (2026-10-16)

The existing structure CIF vocabulary owns both punctuation variants and legacy
replacement names. IUCr's [archived H-M definition](https://www.iucr.org/__data/iucr/cifdic_html/1/cif_core.dic/Isymmetry_space_group_name_H-M.html)
identifies [the replacement H-M item](https://www.iucr.org/__data/iucr/cifdic_html/1/cif_core.dic/Ispace_group_name_H-M_alt.html).
The dotted/classic legacy symmetry H-M names now normalize to the same canonical
replacement field as dotted/classic space-group H-M. The classic builder reads
that sole normalized field, rather than preferring the replacement over an
independently retained legacy value. A second supported declaration refuses,
even if its value matches or is unknown: duplicate refusal is the existing
structure-import policy, not a new semantic comparison of space-group strings.

This uses the existing case-folded scalar/loop-wide declaration set and immutable
Loop reconstruction. The audit covers cell, geometry, H-M, IT-number, setting,
site, isotropic ADP and anisotropic column spellings. IT-number legacy aliases
already share one key; the others already share their supported punctuation/case
key. U versus B values/tensors are distinct physical representations, not aliases
to collapse; existing conversion/selection/validation remains unchanged. Native
schema/native-only markers still dispatch unchanged to the strict native reader
before CIF normalization. No value, label, case-sensitive literal, symmetry
setting, uncertainty, coordinate, ADP or original source byte is rewritten.

Qualification must retain genuine standalone legacy/replacement imports and
exercise case/punctuation/scalar/loop alias collisions through the real reader.
Private source-table inspection is not an actual importer runtime claim.
