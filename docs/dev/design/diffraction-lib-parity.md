# diffraction-lib parity — the argued divergence list

> **Historical record (2026-08-31):** several rows below name surfaces later retired under
> the necessity rule — `CachedModel`, `Project.structure_factors`, `human_report`,
> `parameter_specs`, `covered_tag_categories`, `StructureFactory`/`ExperimentFactory`. The live
> authority is `data/python-surface.json` + the deviation register; this table stays as the
> argument as made.

**Declared upstream pin: diffraction-lib `origin/master` `0ffba46f`
(`0ffba46f4b501066a73e77f00fa29fa13519b417`, v0.20.1)** — and since (2026-08-28) the oracle pin
is the same commit. The oracle used to be frozen at a branch-only commit of
`origin/fullprof-occupancy-notation` that `master` cannot reach (such an
anchor is forbidden: a squash merge strands it, so a gate built on it dies at its own merge). The two trees were
measured name-equivalent before the move — the identical set of 475 `'_<category>.<name>'`
literals under `src/easydiffraction/**` (zero-entry diff, verified 2026-08-21 and re-verified at the
re-anchor) and the identical **qualified set** from the full property scan below — 40 categories /
306 attributes, zero symmetric difference over `<category>.<attribute>` (re-measured 2026-08-22
under the current method; the earlier revision of this sentence claimed 39/296 and compared counts
rather than sets) — so the oracle's content is unchanged by the re-anchor. The machine-derived
reference corpus is `tests/fixtures/c11_t40_diffraction_lib_reference/oracle.json`, generated from
upstream source at that pin.

**The oracle scans the WHOLE upstream tree, and classifies edi presence CATEGORY BY CATEGORY.**
The upstream side enumerates every public `@property` under every
`src/easydiffraction/**/categories/<name>/` directory at the pin, plus the public selectors a
category inherits from a cross-cutting base — **40 categories, 306 attributes, 206 descriptor
rows**. The edi side introspects the **built module's object graph**: each upstream category names
the edi accessor that exposes it, and the attributes are read from the live element object, so
`(category, attribute)` membership is qualified by construction. **58 present, 248 absent.**

Both halves of that sentence are corrections, each from its own rejected revision:

- The universe was once 12 hand-picked source files, so table (c) had 30 rows and the gate could
  not notice a name outside them.
- edi presence was then decided by collecting every quoted lowercase token in `bindings.cpp` and
  asking whether the **unqualified** attribute occurred anywhere. That discards the category, so a
  leaf belonging to some other edi type marked the attribute present under every category sharing
  it — `aliases.id`, `atom_site_aniso.id`, `constraints.id`, `refln.id`, `space_group_wyckoff.id`,
  `metadata.name`, `software.name` and `excluded_regions.start` were all called present though edi
  binds none of those categories, and so landed in neither table. It also let the canonical
  document claim all ten inherited `type` selectors were present when only two are.

The second failure is why presence is no longer derived from C++ text at all. A regex over
`bindings.cpp` cannot carry a category through the membership test, so every refinement of it is a
better guess at a question it cannot ask; the built module can be asked directly. The category map
is a declaration rather than a heuristic, and generation **fails closed** if it is wrong: every
`parameter_specs()` row must resolve into the derived surface and every `covered_tag_categories()`
entry must be mapped, so a category edi really exposes but the map forgets fails generation instead
of silently becoming *absent*. A category that introspects to nothing must be declared empty for
the same reason.

Regenerate the oracle, and table (c) with it:

```bash
pixi run python tests/fixtures/c11_t40_diffraction_lib_reference/generate.py <dl-checkout>
pixi run python tests/fixtures/c11_t40_diffraction_lib_reference/generate.py <dl-checkout> \
    --markdown            # parity table (c) below, one row per absent name
pixi run python tests/fixtures/c11_t40_diffraction_lib_reference/generate.py <dl-checkout> \
    --canonical-table     # the canonical vocabulary table body
```

**Verify the totals move together** — if the attribute count changes without the table changing,
the scan did not run. Generation fails closed on an absent name with no note, on a name recorded as
implemented that the qualified surface does not expose, on a name recorded as implemented that is
not an upstream name at the pin, on an unmapped edi category, and on a category that introspects to
nothing without being declared empty. It imports the built `edi` module, so run it after
`core-build`.

This document is the deliverable the owner framing requires: **every remaining divergence from
diffraction-lib, argued** — so divergence stays a short, explicit list rather than an
accumulation of independent choices. The three tables below are machine-readable (one row per
name); the parity gate cross-checks them against upstream source and edi's live surface.

**The comparison key is the Python ATTRIBUTE — the name a user types — never upstream's internal
`name=` label.** Upstream declares each parameter as a member `self._<attribute>` carrying an
internal label `name='<label>'` and exposes `@property <attribute>`; in the `instrument` category
(and only there — exactly 13 of the 206 descriptor rows the full scan derives, all 13 in
`instrument/cwl.py` + `instrument/tof.py`) the attribute carries a `setup_`/`calib_` prefix the
internal label drops. The attribute equals the leaf of upstream's own `.edi` serialization tag
(`edi_names[0]` — verified for all 206 oracle descriptor rows, zero mismatches), so keying on the
attribute is also what keeps `.edi` files interoperable. Both counts are measured over the whole
tree rather than over the retired 12-file subset, which is what makes "and only there" a claim
about upstream rather than about a sample of it. An earlier revision of this document keyed the instrument
rows on `name=` and therefore missed the prefixes; found in-cycle (2026-08-21) and corrected —
edi adopted the prefixed attributes on every surface.

## (a) Argued divergences

Names both libraries expose for the same quantity, deliberately spelled or shaped differently in
edi. Anything NOT in this table is either identical (the aligned vocabulary) or absent from one
side (tables (b)/(c)).

| edi name | diffraction-lib name | surface | justification |
| --- | --- | --- | --- |
| `absorption.abscor1` / `absorption.abscor2` | *(no TOF absorption category upstream)* | Python attribute, identity path, `.edi` item | The FullProf `Iabscor=2` pair, kept as FullProf spells it. ABSCOR1 is kernel-proven (`muR = ABSCOR1 * lambda`, crysta `tof_profile.hpp`), but ABSCOR2's lambda-power is unpinned in the engine — a physical name for it would be a guess, and naming one half of a FullProf-defined pair alone would split the pair. Upstream's `cylinder_hewat` absorption is CW-only by its own `Compatibility` declaration, so there is no upstream TOF name to converge to. |
| `experiment_type.beam_mode` default `time-of-flight` | default `constant wavelength` | declared default (values and tokens are identical) | edi's entire pre-CW project corpus is TOF, and the loader derives the mode from the `_peak.type` family when the tag is absent. Adopting upstream's CW default would silently re-mode every legacy model. |
| `Parameter.esd` | `Parameter.uncertainty` | Python attribute | `esd` is the IUCr/CIF vocabulary (the bracketed *standard uncertainty* every `.edi` value carries) and predates this task across edi's whole surface; the semantics are identical. Recorded rather than renamed: the packet's ruled rename table does not include it, and the CIF-anchored spelling has independent standing. |
| `SampleFormEnum`, `BeamModeEnum`, `RadiationProbeEnum`, `ScatteringTypeEnum`, `PeakProfileTypeEnum` | `SampleFormEnum`, `BeamModeEnum`, `RadiationProbeEnum`, `ScatteringTypeEnum`, `PeakProfileTypeEnum` | Python/C++ type names | Values, field names and verbatim tokens match upstream exactly; only the type-name `…Enum` suffix is dropped (C++ house style — an enum's kind is carried by its type, not its name). |
| `PdDataBase` | `PdCwlData` / `PdTofData` | Python/C++ type name | One value type with mode-named presence-tracked axes (`two_theta` / `time_of_flight`, exactly one engaged) instead of upstream's two classes; the FIELD names match upstream exactly and `axis()` is the mode-agnostic accessor. |
| `excluded_regions` items as `(start, end)` tuples | `excluded_regions[i].start` / `.end` item objects | Python attribute shape | The category and the words `start`/`end` agree; edi keeps the plain-pair representation (a structured region item is a feature, not a rename). |
| `AtomSite.adp_type` as a string (`Biso`, `Uiso`, `Bani`, `Uani`, `beta`) | `atom_site.adp_type` (`AdpTypeEnum`) | Python attribute type | edi holds the declared type as its file token rather than an enum; the five values are upstream's. A site keeps the type its file declares (`Biso` when none), and setting it converts the site's values through crysta (ADR-0027). |
| `experiment.dataset_weight` | `joint_fit.weight` | Python attribute, `.edi` item | The per-experiment joint-fit weight. edi carries it on the experiment itself (and reads it from `analysis.edi`) rather than as a separate `joint_fit` collection keyed by experiment id, because edi's joint fit weights the experiments it already holds; the quantity, units and default (1.0) are upstream's. Recorded here rather than in table (b): edi implements the quantity under a different spelling, which is a divergence by this document's own rule. Surfaced by the full-scan oracle — the retired 12-file subset did not scan `analysis/categories/joint_fit/`. |
| `atom_site.adp_iso` displayed as `B_iso` | displayed as `U_iso` | display metadata only | edi's stored value IS B, and display metadata must describe the value it labels. Name, tag and units match upstream. |

## (b) edi-only names

Public names edi exposes with no upstream counterpart (capabilities upstream lacks, result/report
surface, and seams). Not divergences — listed so the parity gate can prove the enumeration is
complete rather than silently partial.

| edi name | surface | note |
| --- | --- | --- |
| `structure.scattering_lengths_fm` | Python attribute | per-element coherent-scattering-length override for crysta's neutron table (units stated in the name predates this task and the map is not a `Parameter`; a spec-carried units field does not apply) |
| `Project.calculate` / `fit` / `fit_joint` | Python method | the ruled direct shortcuts beside `project.analysis` |
| `Project.load` / `save` | Python method | project I/O entry points (upstream: `save_as`/`load`, aligned where shared) |
| `CachedModel` (+ `set` / `get` / `set_free` / `paths` / `rebuilds` / `project`) | Python type | the persistent cached surface |
| `FitResultBase`, `IterationRecord`, `FitPreamble`, `FitStatus`, `BankMetric` | Python types | edi's engine-free result surface. The TYPE names are edi-only; `FitResultBase` is also the surface the parity scan maps upstream's `fit_result` category onto, so two of its attributes are shared names and appear as present in table (c)'s counterpart — the type being edi-only and its attributes being partly shared are not in tension |
| `VerbosityEnum`, `machine_report`, `human_report`, `error_report`, `parameter_table`, `summary_line`, `stream_header`, `pre_fit_line`, `iteration_line`, `progress_report`, `format_change` | Python functions/types | the output contract |
| `Project.structure_factors` / `CachedModel.structure_factors` | Python method | the reflection read-out |
| `parameter_specs` | Python function | the committed parameter-metadata table |
| `StructureFactory` / `ExperimentFactory` | Python types | dict-based constructors (upstream constructs through datablock collections) |
| `PdDataBase.axis` | Python method | the ruled mode-agnostic accessor over the mode-named axes |
| `ExperimentBase.name` / `Structure.name` | Python attribute | datablock ids (upstream: collection keys) |

## (c) diffraction-lib names edi does not implement

Upstream public parameter names with no edi feature behind them — listed so absence is never
mistaken for a rename. **Machine-derived: one row for every upstream attribute the full scan finds
that edi's category-qualified surface does not expose — 243 of the 306, across 37 of the 40
categories.** Regenerate with `generate.py --markdown` (see the header); do not hand-edit.

Rows are keyed by upstream's own category directory name, which is the scan's key — so `atom_sites`
and `excluded_regions` are spelled as upstream's directories spell them, while edi's corresponding
`.edi` tags stay singular (`_atom_site.*`, `_excluded_region.*`) exactly as before. A `—` here is
not automatically a defect: most of these are features edi has not implemented. It IS a defect when
edi implements the quantity under a different spelling, and those rows say so and point at table
(a) — `atom_sites.adp_iso_as_b` and `joint_fit.weight` are the two the widened scan surfaced.

**The count grew by 34 when presence became category-qualified, and every one of those is a row
that previously existed in no table at all.** They are not newly unimplemented; they were
misclassified as present by a leaf token belonging to some other edi type. The largest groups are
`refln.*` (edi returns `structure_factors` as a structured array whose fields are `h`/`k`/`l`/`d`/
`f_squared`, not upstream's `index_h`/`intensity_meas` spellings), `metadata.*` and `software.*`
(no edi surface at all), the eight inherited `type` selectors edi does not expose, and
`linked_structures.*` (upstream's collection category; edi exposes the singular one).

Two upstream surface FAMILIES that a previous revision described only in prose now appear as ordinary
rows, which is what the one-row-per-name contract requires: the Chebyshev background implementation
(`background.coef`, `background.order` — `background/chebyshev.py` at the pin; the generated rows'
note is the committed oracle's) and the `analysis.*` category surface (fit parameters, constraints,
aliases, minimizer selection, …), which arrives incrementally behind
`project.analysis` (ruled C) — the facade exists, the surface is not yet ported.

| diffraction-lib name | note |
| --- | --- |
| `absorption.mu_r` | upstream's CW cylinder absorption surface; edi's TOF `abscor1`/`abscor2` pair is a declared divergence — see table (a) |
| `aliases.id` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `aliases.param` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `aliases.parameter_unique_name` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `aliases.parameters` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `atom_site_aniso.adp_11` | anisotropic ADP storage, not modelled — edi stores isotropic B only and refuses a declared anisotropic `_atom_site.adp_type` at load |
| `atom_site_aniso.adp_12` | anisotropic ADP storage, not modelled — edi stores isotropic B only and refuses a declared anisotropic `_atom_site.adp_type` at load |
| `atom_site_aniso.adp_13` | anisotropic ADP storage, not modelled — edi stores isotropic B only and refuses a declared anisotropic `_atom_site.adp_type` at load |
| `atom_site_aniso.adp_22` | anisotropic ADP storage, not modelled — edi stores isotropic B only and refuses a declared anisotropic `_atom_site.adp_type` at load |
| `atom_site_aniso.adp_23` | anisotropic ADP storage, not modelled — edi stores isotropic B only and refuses a declared anisotropic `_atom_site.adp_type` at load |
| `atom_site_aniso.adp_33` | anisotropic ADP storage, not modelled — edi stores isotropic B only and refuses a declared anisotropic `_atom_site.adp_type` at load |
| `atom_site_aniso.id` | anisotropic ADP storage, not modelled — edi stores isotropic B only and refuses a declared anisotropic `_atom_site.adp_type` at load |
| `atom_sites.adp_iso_as_b` | upstream's B-valued view of the isotropic ADP; edi stores it as B natively, so edi's `adp_iso` already IS this value — see table (a) |
| `atom_sites.multiplicity` | tolerated on read, not modelled |
| `background.coef` | Chebyshev-polynomial background implementation (`background/chebyshev.py` at the pin); edi implements line-segment backgrounds only |
| `background.id` | row ordinal, read past |
| `background.order` | Chebyshev-polynomial background implementation (`background/chebyshev.py` at the pin); edi implements line-segment backgrounds only |
| `background.type` | the `_background.type` tag is read at load, but edi exposes no `type` attribute on a background point |
| `calculator.calculator` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `calculator.type` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `constraints.enabled` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `constraints.expression` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `constraints.id` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `constraints.lhs_alias` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `constraints.rhs_expr` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `data.calc_status` | calculated-pattern or PDF column edi does not persist |
| `data.d_spacing` | calculated-pattern or PDF column edi does not persist |
| `data.g_r_calc` | calculated-pattern or PDF column edi does not persist |
| `data.g_r_meas` | calculated-pattern or PDF column edi does not persist |
| `data.g_r_meas_su` | calculated-pattern or PDF column edi does not persist |
| `data.id` | row ordinal, read past |
| `data.intensity_bkg` | calculated-pattern or PDF column edi does not persist |
| `data.intensity_calc` | calculated-pattern or PDF column edi does not persist |
| `data.r` | calculated-pattern or PDF column edi does not persist |
| `data.unfiltered_x` | pre-exclusion axis copy edi does not retain |
| `data.x` | see table (a): edi names the axis by mode and reads it through `MeasuredPattern.axis` |
| `data.x_descriptor` | see table (a): edi names the axis by mode, so no descriptor selects between axes |
| `data_range.d_spacing_max` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.d_spacing_min` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.sin_theta_over_lambda_max` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.sin_theta_over_lambda_min` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.time_of_flight_inc` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.time_of_flight_max` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.time_of_flight_min` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.two_theta_inc` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.two_theta_max` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.two_theta_min` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.x_max` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.x_min` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `data_range.x_step` | upstream range/step metadata; edi derives its range from the measured pattern rather than storing it |
| `diffrn.ambient_electric_field` | ambient-condition metadata, not modelled |
| `diffrn.ambient_magnetic_field` | ambient-condition metadata, not modelled |
| `diffrn.ambient_pressure` | ambient-condition metadata, not modelled |
| `diffrn.ambient_temperature` | ambient-condition metadata, not modelled |
| `excluded_regions.end` | see table (a): edi keeps excluded regions as plain `(start, end)` pairs, so neither element is a named attribute |
| `excluded_regions.id` | row ordinal, read past |
| `excluded_regions.start` | see table (a): edi keeps excluded regions as plain `(start, end)` pairs, so neither element is a named attribute |
| `extinction.model` | extinction correction, not implemented |
| `extinction.mosaicity` | extinction correction, not implemented |
| `extinction.radius` | extinction correction, not implemented |
| `extinction.type` | extinction correction, not implemented |
| `fit_parameter_correlations.correlation` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameter_correlations.id` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameter_correlations.parameter_unique_name_i` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameter_correlations.parameter_unique_name_j` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameter_correlations.source_kind` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.bounds_uncertainty_multiplier` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.fit_max` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.fit_min` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.parameter_unique_name` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.posterior_best_sample_value` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.posterior_effective_sample_size_bulk` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.posterior_gelman_rubin` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.posterior_interval_68_high` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.posterior_interval_68_low` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.posterior_interval_95_high` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.posterior_interval_95_low` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.posterior_median` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.posterior_uncertainty` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.start_uncertainty` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_parameters.start_value` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `fit_result.acceptance_rate_mean` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.background_function` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.best_log_posterior` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.correlation_available` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.covariance_available` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.credible_interval_inner` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.credible_interval_outer` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.degrees_of_freedom` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.effective_sample_size_min` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.exit_reason` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.gelman_rubin_max` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.message` | edi reports terminal state as the `FitOutcome.status` enum plus `FitStatus`, not a free-text message |
| `fit_result.n_data_points` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.n_free_parameters` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.n_parameters` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.number_constraints` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.number_reflns_gt` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.number_reflns_total` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.number_restraints` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.objective_name` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.objective_value` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.point_estimate_name` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.prof_r_factor` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.prof_wr_expected` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.prof_wr_factor` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.profile_function` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.r_factor_all` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.r_factor_gt` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.resolved_random_seed` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.sampler_completed` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.shift_over_su_max` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.shift_over_su_mean` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.threshold_expression` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.wr_factor_all` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fit_result.wr_factor_gt` | richer fit statistics than edi reports — edi exposes `fitting_time`, `iterations`, `reduced_chi_square`, `result_kind` and `success`; the rest arrive with the `analysis.*` surface (ruled C) |
| `fitting_mode.type` | upstream's switchable fitting-mode category; edi's `analysis.fitting_mode` is a plain string selector with no category object behind it |
| `geom.as_cif` | upstream's per-category CIF accessor; edi serialises through its own `.edi` writer |
| `geom.bond_distance_inc` | geometry/bond-distance analysis, not implemented |
| `geom.min_bond_distance_cutoff` | geometry/bond-distance analysis, not implemented |
| `instrument.calib_sample_displacement` | CW instrument feature edi has not implemented |
| `instrument.calib_sample_transparency` | CW instrument feature edi has not implemented |
| `instrument.setup_monochromator_twotheta` | CW instrument feature edi has not implemented |
| `instrument.setup_polarization_coefficient` | CW instrument feature edi has not implemented |
| `instrument.setup_wavelength_2` | CW instrument feature edi has not implemented |
| `instrument.setup_wavelength_2_to_1_ratio` | CW instrument feature edi has not implemented |
| `joint_fit.experiment_id` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `joint_fit.weight` | edi spells this `experiment.dataset_weight` — see table (a) |
| `linked_structures.scale` | upstream's linked-structure COLLECTION category; the parity verdict for this quantity is carried by the singular `linked_structure` rows, so these names are absent under this spelling |
| `linked_structures.structure_id` | upstream's linked-structure COLLECTION category; the parity verdict for this quantity is carried by the singular `linked_structure` rows, so these names are absent under this spelling |
| `metadata.as_cif` | upstream's per-category CIF accessor; edi serialises through its own `.edi` writer |
| `metadata.created` | project metadata edi does not record |
| `metadata.description` | project metadata edi does not record |
| `metadata.last_modified` | project metadata edi does not record |
| `metadata.name` | project metadata edi does not record |
| `metadata.path` | project metadata edi does not record |
| `metadata.timestamp` | project metadata edi does not record |
| `metadata.title` | project metadata edi does not record |
| `metadata.unique_name` | project metadata edi does not record |
| `minimizer.burn_in_steps` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `minimizer.chains` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `minimizer.initialization_method` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `minimizer.max_iterations` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `minimizer.parallel_workers` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `minimizer.population_size` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `minimizer.proposal_moves` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `minimizer.random_seed` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `minimizer.sampling_steps` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `minimizer.thinning_interval` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `minimizer.type` | the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — the facade exists, this category is not yet ported |
| `peak.asym_beba_a0` | reserved rung 2 (Berar-Baldinozzi, ) — the token is refused by name |
| `peak.asym_beba_a1` | reserved rung 2 (Berar-Baldinozzi, ) — the token is refused by name |
| `peak.asym_beba_b0` | reserved rung 2 (Berar-Baldinozzi, ) — the token is refused by name |
| `peak.asym_beba_b1` | reserved rung 2 (Berar-Baldinozzi, ) — the token is refused by name |
| `peak.asym_fcj_1` | reserved rung 1 (Finger-Cox-Jephcoat, ) — the token is refused by name |
| `peak.asym_fcj_2` | reserved rung 1 (Finger-Cox-Jephcoat, ) — the token is refused by name |
| `peak.broad_q` | PDF/pair-distribution damping-broadening term, not implemented |
| `peak.cutoff_q` | PDF/pair-distribution damping-broadening term, not implemented |
| `peak.damp_particle_diameter` | PDF/pair-distribution damping term, not implemented |
| `peak.damp_q` | PDF/pair-distribution damping term, not implemented |
| `peak.dexp_decay_beta_00` | double-Jorgensen-von-Dreele profile, not implemented |
| `peak.dexp_decay_beta_01` | double-Jorgensen-von-Dreele profile, not implemented |
| `peak.dexp_decay_beta_10` | double-Jorgensen-von-Dreele profile, not implemented |
| `peak.dexp_rise_alpha_1` | double-Jorgensen-von-Dreele profile, not implemented |
| `peak.dexp_rise_alpha_2` | double-Jorgensen-von-Dreele profile, not implemented |
| `peak.dexp_switch_r_01` | double-Jorgensen-von-Dreele profile, not implemented |
| `peak.dexp_switch_r_02` | double-Jorgensen-von-Dreele profile, not implemented |
| `peak.dexp_switch_r_03` | double-Jorgensen-von-Dreele profile, not implemented |
| `peak.sharp_delta_1` | PDF/pair-distribution peak-sharpening term, not implemented |
| `peak.sharp_delta_2` | PDF/pair-distribution peak-sharpening term, not implemented |
| `pref_orient.index_h` | preferred-orientation correction, not implemented |
| `pref_orient.index_k` | preferred-orientation correction, not implemented |
| `pref_orient.index_l` | preferred-orientation correction, not implemented |
| `pref_orient.march_r` | preferred-orientation correction, not implemented |
| `pref_orient.march_random_fract` | preferred-orientation correction, not implemented |
| `pref_orient.structure_id` | preferred-orientation correction, not implemented |
| `refln.d_spacing` | reflection column edi does not expose on its read-out |
| `refln.f_calc` | reflection column edi does not expose on its read-out |
| `refln.f_squared_calc` | reflection column edi does not expose on its read-out |
| `refln.id` | reflection column edi does not expose on its read-out |
| `refln.index_h` | reflection column edi does not expose on its read-out |
| `refln.index_k` | reflection column edi does not expose on its read-out |
| `refln.index_l` | reflection column edi does not expose on its read-out |
| `refln.intensity_calc` | reflection column edi does not expose on its read-out |
| `refln.intensity_meas` | reflection column edi does not expose on its read-out |
| `refln.intensity_meas_su` | reflection column edi does not expose on its read-out |
| `refln.parameters` | reflection column edi does not expose on its read-out |
| `refln.sin_theta_over_lambda` | reflection column edi does not expose on its read-out |
| `refln.structure_id` | reflection column edi does not expose on its read-out |
| `refln.time_of_flight` | reflection column edi does not expose on its read-out |
| `refln.two_theta` | reflection column edi does not expose on its read-out |
| `refln.wavelength` | reflection column edi does not expose on its read-out |
| `rendering_plot.plotter` | display/rendering subsystem, not ported |
| `rendering_plot.type` | display/rendering subsystem, not ported |
| `rendering_structure.as_cif` | upstream's per-category CIF accessor; edi serialises through its own `.edi` writer |
| `rendering_structure.type` | display/rendering subsystem, not ported |
| `rendering_structure.viewer` | display/rendering subsystem, not ported |
| `rendering_table.tabler` | display/rendering subsystem, not ported |
| `rendering_table.type` | display/rendering subsystem, not ported |
| `report.cif` | report renderer edi does not provide |
| `report.html` | report renderer edi does not provide |
| `report.html_offline` | report renderer edi does not provide |
| `report.pdf` | report renderer edi does not provide |
| `report.project` | report renderer edi does not provide |
| `report.tex` | report renderer edi does not provide |
| `sequential_fit.as_cif` | upstream's per-category CIF accessor; edi serialises through its own `.edi` writer |
| `sequential_fit.chunk_size` | sequential/batch fitting over a data directory, not implemented |
| `sequential_fit.copy_data` | sequential/batch fitting over a data directory, not implemented |
| `sequential_fit.data_dir` | sequential/batch fitting over a data directory, not implemented |
| `sequential_fit.file_pattern` | sequential/batch fitting over a data directory, not implemented |
| `sequential_fit.max_workers` | sequential/batch fitting over a data directory, not implemented |
| `sequential_fit.reverse` | sequential/batch fitting over a data directory, not implemented |
| `sequential_fit_extract.id` | sequential/batch fitting over a data directory, not implemented |
| `sequential_fit_extract.pattern` | sequential/batch fitting over a data directory, not implemented |
| `sequential_fit_extract.required` | sequential/batch fitting over a data directory, not implemented |
| `sequential_fit_extract.target` | sequential/batch fitting over a data directory, not implemented |
| `software.id` | software provenance field edi does not record |
| `software.name` | software provenance field edi does not record |
| `software.parameters` | software provenance field edi does not record |
| `software.url` | software provenance field edi does not record |
| `software.version` | software provenance field edi does not record |
| `space_group.crystal_system` | derived classification edi does not store — the space-group name and coordinate-system code carry it |
| `space_group_wyckoff.coords_xyz` | upstream per-Wyckoff-position table; edi carries only `_atom_site.wyckoff_letter` on the site itself |
| `space_group_wyckoff.id` | upstream per-Wyckoff-position table; edi carries only `_atom_site.wyckoff_letter` on the site itself |
| `space_group_wyckoff.letter` | upstream per-Wyckoff-position table; edi carries only `_atom_site.wyckoff_letter` on the site itself |
| `space_group_wyckoff.multiplicity` | upstream per-Wyckoff-position table; edi carries only `_atom_site.wyckoff_letter` on the site itself |
| `space_group_wyckoff.site_symmetry` | upstream per-Wyckoff-position table; edi carries only `_atom_site.wyckoff_letter` on the site itself |
| `structure_style.adp_probability` | display/rendering subsystem, not ported |
| `structure_style.as_cif` | upstream's per-category CIF accessor; edi serialises through its own `.edi` writer |
| `structure_style.atom_scale` | display/rendering subsystem, not ported |
| `structure_style.atom_view` | display/rendering subsystem, not ported |
| `structure_style.color_scheme` | display/rendering subsystem, not ported |
| `structure_view.as_cif` | upstream's per-category CIF accessor; edi serialises through its own `.edi` writer |
| `structure_view.range_a_max` | display/rendering subsystem, not ported |
| `structure_view.range_a_min` | display/rendering subsystem, not ported |
| `structure_view.range_b_max` | display/rendering subsystem, not ported |
| `structure_view.range_b_min` | display/rendering subsystem, not ported |
| `structure_view.range_c_max` | display/rendering subsystem, not ported |
| `structure_view.range_c_min` | display/rendering subsystem, not ported |
| `structure_view.show_labels` | display/rendering subsystem, not ported |
| `structure_view.show_moments` | display/rendering subsystem, not ported |
| `verbosity.as_cif` | upstream's per-category CIF accessor; edi serialises through its own `.edi` writer |
| `verbosity.fit` | upstream's verbosity category; edi's `Verbosity` is the  output-contract type, not this category — see table (b) |
